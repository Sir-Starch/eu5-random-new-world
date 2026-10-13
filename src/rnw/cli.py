"""Commands that produce evidence or prepare isolated test mods."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from pathlib import Path  # noqa: TC003 - Typer resolves Path annotations at runtime.
from typing import Annotated, Final

import typer

from rnw.geography import color_summary, read_locations, summary

app: Final[typer.Typer] = typer.Typer(no_args_is_help=True)
STAMP: Final[re.Pattern[str]] = re.compile(r"^\[[^]]+\]\[[^]]+\]:\s*")
MAX_EXAMPLES: Final[int] = 3


@app.command()
def inspect(game_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    """Report counts from the installed game without copying its data."""
    map_dir = game_dir / "game/in_game/map_data"
    locations = read_locations(map_dir / "definitions.txt")
    result = summary(locations) | color_summary(map_dir / "named_locations/00_default.txt")
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command()
def coupling(
    game_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    output: Annotated[Path, typer.Argument()],
) -> None:
    """Count script references to American location keys by directory."""
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
        "version": "0.1.0",
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
) -> None:
    """Install one new experiment without touching existing mods or playsets."""
    if (
        not prepared.name.startswith("rnw_exp_")
        or not (prepared / ".metadata/metadata.json").is_file()
    ):
        message = "Prepared directory must be a valid rnw_exp_* mod"
        raise typer.BadParameter(message)
    target = user_dir / "mod" / prepared.name
    if target.exists():
        message = f"Destination already exists: {target}"
        raise typer.BadParameter(message)
    target.parent.mkdir(exist_ok=True)
    _ = shutil.copytree(prepared, target)
    typer.echo(f"Installed {target}")


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


if __name__ == "__main__":
    app()
