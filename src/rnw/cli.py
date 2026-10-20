"""Commands that produce evidence or prepare isolated test mods."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Annotated, Final

import typer

from rnw import __version__
from rnw.artifacts import OutputPathError, check_new_output, swap_in, write_synthetic_bundle
from rnw.contract import MissingContractFileError, fingerprint_document
from rnw.contract import fingerprint as game_fingerprint
from rnw.eu5_canvas import CanvasError
from rnw.eu5_export import ExportError, export_candidate
from rnw.eu5_map import Eu5ContractError
from rnw.eu5_nw_export import NewWorldExportError, export_new_world
from rnw.eu5_objects import ObjectBudgetError
from rnw.eu5_remap import RemapError
from rnw.geography import GeographyError, color_summary, read_locations, summary
from rnw.parallel import ResourceError
from rnw.png import PngFormatError
from rnw.settings import SettingsError, load_settings, run_spec
from rnw.synth import generate_world, synthetic_base
from rnw.validate import ValidationError, topology_metrics, validate_world

app: Final[typer.Typer] = typer.Typer(no_args_is_help=True)
STAMP: Final[re.Pattern[str]] = re.compile(r"^\[[^]]+\]\[[^]]+\]:\s*")
MAX_EXAMPLES: Final[int] = 3
SYNTH_NAME: Final[re.Pattern[str]] = re.compile(r"rnw_synth_[a-z0-9_]{1,48}")
ISLAND_PX: Final[int] = 400
SEED_MAX: Final[int] = (1 << 64) - 1
FAILURES: Final[tuple[type[Exception], ...]] = (
    CanvasError,
    Eu5ContractError,
    ExportError,
    NewWorldExportError,
    GeographyError,
    MissingContractFileError,
    ObjectBudgetError,
    OutputPathError,
    PngFormatError,
    RemapError,
    ResourceError,
    SettingsError,
    ValidationError,
)
SeedOption = Annotated[int, typer.Option(min=0, max=SEED_MAX, help="Unsigned 64-bit seed.")]
PresetOption = Annotated[str, typer.Option(help="continents or archipelago.")]
SettingsOption = Annotated[
    Path | None,
    typer.Option(exists=True, dir_okay=False, help="JSON overrides; schema 1."),
]


def _check_output_outside_game(game_dir: Path, output: Path) -> None:
    if output.resolve().is_relative_to(game_dir.resolve()):
        message = "Output path must be outside the game installation"
        raise typer.BadParameter(message)


@app.command()
def inspect(game_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    """Report counts from the installed game without copying its data."""
    map_dir = game_dir / "game/in_game/map_data"
    locations = read_locations(map_dir / "definitions.txt")
    result = summary(locations) | color_summary(
        locations, map_dir / "named_locations/00_default.txt"
    )
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command()
def coupling(
    game_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    output: Annotated[Path, typer.Argument()],
) -> None:
    """Count script references to American location keys by directory."""
    _check_output_outside_game(game_dir, output)
    locations = read_locations(game_dir / "game/in_game/map_data/definitions.txt")
    keys = {item.key for item in locations if item.continent == "america"}
    counts: Counter[str] = Counter()
    files: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    for root in (game_dir / "game/in_game", game_dir / "game/main_menu"):
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".txt", ".gui", ".csv", ".json", ".yml"} or not path.is_file():
                continue
            relative = path.relative_to(game_dir / "game")
            if str(relative).startswith("in_game/map_data/"):
                continue
            category = "/".join(relative.parts[:3])
            content = path.read_text(encoding="utf-8-sig", errors="replace")
            hits = keys.intersection(re.findall(r"\b[a-z][a-z0-9_]*\b", content))
            if hits:
                counts[category] += len(hits)
                files[category] += 1
                _ = examples.setdefault(category, [])
                if len(examples[category]) < MAX_EXAMPLES:
                    examples[category].append(str(relative))
    result = {
        category: {
            "distinct_key_hits": counts[category],
            "files": files[category],
            "examples": examples[category],
        }
        for category in sorted(counts)
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    typer.echo(f"Wrote aggregate references: {output}")


@app.command()
def fingerprint(
    game_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    output: Annotated[Path, typer.Argument()],
) -> None:
    """Write a stable, read-only fingerprint of the current map contract."""
    _check_output_outside_game(game_dir, output)
    document = fingerprint_document(game_fingerprint(game_dir))
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_text(document, encoding="utf-8")
    typer.echo(f"Wrote map-contract fingerprint: {output}")


@app.command()
def prepare_mod(output: Annotated[Path, typer.Argument()]) -> None:
    """Prepare a metadata-only experiment in an empty project output path."""
    if output.name != "rnw_exp_001_metadata" or output.exists():
        message = "Output must be a new rnw_exp_001_metadata directory"
        raise typer.BadParameter(message)
    metadata = output / ".metadata"
    metadata.mkdir(parents=True)
    payload: dict[str, str | list[str] | dict[str, str]] = {
        "name": "RNW experiment 001 - metadata",
        "id": "rnw_exp_001_metadata",
        "version": __version__,
        "supported_game_version": "1.4.*",
        "short_description": "Local RNW loading experiment",
        "tags": ["Map"],
        "relationships": [],
        "game_custom_data": {},
    }
    _ = (metadata / "metadata.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8-sig"
    )
    typer.echo(f"Prepared {output}")


@app.command()
def install_mod(
    prepared: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    user_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    *,
    replace: Annotated[
        bool, typer.Option(help="Replace an installed rnw_exp_* mod of the same name.")
    ] = False,
) -> None:
    """Install one rnw_exp_* mod; never touches other mods or playsets."""
    if not _is_rnw_mod(prepared):
        message = "Prepared directory must be a valid rnw_exp_* mod"
        raise typer.BadParameter(message)
    target = user_dir / "mod" / prepared.name
    if target.exists() and not (replace and _is_rnw_mod(target)):
        message = f"Destination already exists (use --replace for an rnw_exp_* mod): {target}"
        raise typer.BadParameter(message)
    target.parent.mkdir(exist_ok=True)
    incoming = target.parent / f".{target.name}.partial"
    if incoming.exists():
        shutil.rmtree(incoming)
    _ = shutil.copytree(prepared, incoming)
    swap_in(incoming, target)
    typer.echo(f"Installed {target}")


@app.command()
def uninstall_mod(
    names: Annotated[list[str], typer.Argument(help="rnw_exp_* folder names to remove.")],
    user_dir: Annotated[Path, typer.Option(exists=True, file_okay=False)],
) -> None:
    """Remove installed rnw_exp_* mods; refuses any other folder."""
    targets = [user_dir / "mod" / name for name in names]
    bad = [str(target) for target in targets if not _is_rnw_mod(target)]
    if bad:
        message = f"Not installed rnw_exp_* mods: {', '.join(bad)}"
        raise typer.BadParameter(message)
    for target in targets:
        shutil.rmtree(target)
        typer.echo(f"Removed {target}")


def _is_rnw_mod(path: Path) -> bool:
    return (
        path.is_dir()
        and path.name.startswith("rnw_exp_")
        and (path / ".metadata/metadata.json").is_file()
    )


@app.command()
def logdiff(
    baseline: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    current: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
) -> None:
    """Show new error lines after stripping volatile timestamps and counts."""
    old = Counter(
        STAMP.sub("", line.rstrip()) for line in baseline.read_text(errors="replace").splitlines()
    )
    new = Counter(
        STAMP.sub("", line.rstrip()) for line in current.read_text(errors="replace").splitlines()
    )
    delta = new - old
    typer.echo(
        json.dumps({"new_lines": sum(delta.values()), "examples": sorted(delta)[:30]}, indent=2)
    )


@app.command()
def synth(
    *,
    output: Annotated[Path, typer.Option(help="New generated/rnw_synth_* directory.")],
    seed: SeedOption,
    preset: PresetOption = "continents",
    settings: SettingsOption = None,
) -> None:
    """Generate a synthetic world from a seed; outputs are byte-deterministic."""
    try:
        check_new_output(output, SYNTH_NAME)
        chosen = load_settings(preset, settings)
        world = generate_world(seed, chosen)
        validate_world(world, base=synthetic_base(chosen.synthetic))
        metrics = topology_metrics(world, ISLAND_PX)
        manifest = write_synthetic_bundle(world, run_spec(seed, chosen), metrics, output)
    except FAILURES as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(json.dumps({"output": str(output), "metrics": metrics, "files": manifest["files"]}))


@app.command()
def generate(  # noqa: PLR0913 - mirrors the documented CLI contract.
    *,
    game_dir: Annotated[
        Path, typer.Option(exists=True, file_okay=False, help="Read-only EU5 installation.")
    ],
    output: Annotated[Path, typer.Option(help="New generated/rnw_exp_* directory.")],
    seed: SeedOption,
    preset: PresetOption = "continents",
    settings: SettingsOption = None,
    accept_build: Annotated[
        str | None, typer.Option(help="Explicitly select an untested fingerprint digest.")
    ] = None,
    replace: Annotated[
        bool, typer.Option(help="Replace an existing generated/rnw_exp_* bundle.")
    ] = False,
) -> None:
    """Stage a NOT GAME VALIDATED coastline mod candidate from the local installation."""
    try:
        chosen = load_settings(preset, settings)
        report = export_candidate(
            game_dir,
            output,
            seed=seed,
            settings=chosen,
            accept_build=accept_build,
            settings_file=None if settings is None else settings.name,
            replace=replace,
        )
    except FAILURES as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(
        json.dumps(
            {
                "status": report["status"],
                "output": str(output),
                "changes": report["changes"],
                "files": report["files"],
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command()
def newworld(  # noqa: PLR0913 - mirrors the generate command.
    *,
    game_dir: Annotated[
        Path, typer.Option(exists=True, file_okay=False, help="Read-only EU5 installation.")
    ],
    output: Annotated[Path, typer.Option(help="New generated/rnw_exp_* directory.")],
    seed: SeedOption,
    preset: PresetOption = "continents",
    settings: SettingsOption = None,
    accept_build: Annotated[
        str | None, typer.Option(help="Explicitly select an untested fingerprint digest.")
    ] = None,
    replace: Annotated[
        bool, typer.Option(help="Replace an existing generated/rnw_exp_* bundle.")
    ] = False,
    ignore_memory: Annotated[
        bool, typer.Option(help="Start although the free memory is below what the export needs.")
    ] = False,
) -> None:
    """Stage a NOT GAME VALIDATED mod that replaces the New World with generated land."""
    try:
        chosen = load_settings(preset, settings)
        report = export_new_world(
            game_dir,
            output,
            seed=seed,
            settings=chosen,
            accept_build=accept_build,
            settings_file=None if settings is None else settings.name,
            replace=replace,
            check_memory=not ignore_memory,
        )
    except FAILURES as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    summary = {key: report[key] for key in ("status", "canvas", "generated", "invariants")}
    typer.echo(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    app()
