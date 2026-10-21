"""Commands that produce evidence or prepare isolated test mods."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Annotated, Final, cast

import typer

from rnw import __version__
from rnw.app import discovery, install, paths, service, worldcode
from rnw.app.discovery import GameInstall
from rnw.app.install import InstallError
from rnw.artifacts import OutputPathError, check_new_output, write_synthetic_bundle
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
from rnw.progress import Cancelled, Progress, Update
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
    Cancelled,
    InstallError,
    worldcode.WorldCodeError,
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
    try:
        target = install.install(prepared, user_dir, replace=replace)
    except InstallError as error:
        raise typer.BadParameter(str(error)) from error
    typer.echo(f"Installed {target}")


@app.command()
def uninstall_mod(
    names: Annotated[list[str], typer.Argument(help="rnw_exp_* folder names to remove.")],
    user_dir: Annotated[Path, typer.Option(exists=True, file_okay=False)],
) -> None:
    """Remove installed rnw_exp_* mods; refuses any other folder."""
    try:
        removed = install.uninstall(names, user_dir)
    except InstallError as error:
        raise typer.BadParameter(str(error)) from error
    for target in removed:
        typer.echo(f"Removed {target}")


@app.command()
def find_game() -> None:
    """List the EU5 installations and profiles this machine has (read-only)."""
    games = discovery.find_games()
    profiles = discovery.find_profiles(games=games)
    typer.echo(
        json.dumps(
            {
                "games": [
                    {"directory": str(game.directory), "build_id": game.build_id} for game in games
                ],
                "profiles": [
                    {"directory": str(item.directory), "kind": item.kind, "has_mods": item.has_mods}
                    for item in profiles
                ],
                "data_directory": str(paths.data_directory()),
            },
            indent=2,
        )
    )


@app.command()
def world_code(
    text: Annotated[str | None, typer.Argument(help="A world code to read.")] = None,
    *,
    preset: PresetOption = "continents",
    seed: Annotated[int | None, typer.Option(min=0, max=SEED_MAX, help="Default: random.")] = None,
    settings: SettingsOption = None,
) -> None:
    """Print a world code for a preset and seed, or read the one given."""
    try:
        if text is not None:
            code = worldcode.decode(text)
        else:
            changes = None if settings is None else _read_changes(settings)
            code = worldcode.new_code(preset, seed, changes)
    except (worldcode.WorldCodeError, SettingsError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(
        json.dumps(
            {
                "code": worldcode.encode(code),
                "preset": code.preset,
                "seed": code.seed,
                "generator": code.generator,
                "reproduced_by_this_generator": worldcode.reproduces(code),
                "changes": code.changes,
            },
            indent=2,
        )
    )


def _read_changes(path: Path) -> dict[str, object]:
    data = cast("object", json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(data, dict):
        message = "The settings file must hold a JSON object"
        raise SettingsError(message)
    changes = cast("dict[str, object]", data)
    _ = changes.pop("schema", None)
    _ = changes.pop("preset", None)
    return changes


@app.command()
def world(
    code: Annotated[str, typer.Argument(help="A world code (see world-code).")],
    *,
    install_into_profile: Annotated[
        bool, typer.Option("--install", help="Install the mod into the profile found.")
    ] = False,
    game_dir: Annotated[
        Path | None, typer.Option(exists=True, file_okay=False, help="Default: search Steam.")
    ] = None,
    data_dir: Annotated[
        Path | None, typer.Option(file_okay=False, help="Default: the application's folder.")
    ] = None,
    ignore_memory: Annotated[bool, typer.Option(help="Start with too little free memory.")] = False,
) -> None:
    """Generate the world of a code the way the application does; install only on request."""
    try:
        decoded = worldcode.decode(code)
        games = discovery.find_games()
        game = (
            GameInstall(game_dir, None, "")
            if game_dir is not None
            else (games[0] if games else None)
        )
        if game is None:
            message = "No EU5 installation found; pass --game-dir"
            raise typer.BadParameter(message)
        profiles = discovery.find_profiles(games=games) if install_into_profile else []
        result = service.generate(
            service.Request(
                game=game,
                code=decoded,
                data=data_dir or paths.data_directory(),
                profile=profiles[0] if profiles else None,
                install=install_into_profile,
                check_memory=not ignore_memory,
            ),
            Progress(_print_update),
        )
    except FAILURES as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    typer.echo(
        json.dumps(
            {
                "code": result.code,
                "bundle": str(result.bundle),
                "installed": None if result.installed is None else str(result.installed),
                "seconds": round(result.seconds, 1),
                "summary": result.summary,
            },
            indent=2,
            sort_keys=True,
        )
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


def _print_update(update: Update) -> None:
    """One line per stage that starts or ends, with the share of the work that is done."""
    state = "done " if update.finished else "start"
    typer.echo(f"[{update.fraction:4.0%}] {state} {update.label}", err=True)


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
    progress: Annotated[
        bool, typer.Option(help="Print each stage and the share of the work done to stderr.")
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
            progress=Progress(_print_update) if progress else None,
        )
    except FAILURES as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=2) from error
    summary = {key: report[key] for key in ("status", "canvas", "generated", "invariants")}
    typer.echo(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    app()
