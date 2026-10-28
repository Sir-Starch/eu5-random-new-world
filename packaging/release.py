from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Annotated, Final

import allowlist
import typer
from hub import LAUNCHER, check_no_game_files, check_programs

from rnw import __version__

app: Final[typer.Typer] = typer.Typer(no_args_is_help=True)


def check_tag(tag: str) -> None:
    if re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag) is None:
        message = f"Tag {tag!r} must be vMAJOR.MINOR.PATCH without leading zeroes or suffixes"
        raise ValueError(message)
    if tag != f"v{__version__}":
        message = f"Tag {tag!r} does not match pyproject.toml version {__version__}"
        raise ValueError(message)


def check_source_ref(tag: str, root: Path, *, candidate_commit: str = "") -> None:
    """Require clean exact sources for a pre-tag candidate or frozen release."""
    check_tag(tag)
    if candidate_commit and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", candidate_commit) is None:
        message = "Candidate commit must be a full lowercase Git SHA"
        raise ValueError(message)

    def git(*args: str) -> str:
        return subprocess.check_output(  # noqa: S603 - fixed git commands, tag is validated
            ["git", *args],  # noqa: S607 - git is provided by the build environment
            cwd=root,
            text=True,
        ).strip()

    expected = candidate_commit or git("rev-parse", f"refs/tags/{tag}^{{commit}}")
    if git("rev-parse", "HEAD") != expected:
        message = f"HEAD is not the commit named by {candidate_commit or tag}"
        raise ValueError(message)
    if git("status", "--porcelain", "--untracked-files=normal"):
        message = "Release source must be a clean checkout, including untracked files"
        raise ValueError(message)


@app.command()
def check_ref(
    tag: Annotated[str, typer.Option()],
    commit: Annotated[
        str, typer.Option(help="Full pre-tag candidate SHA; empty requires the tag")
    ] = "",
) -> None:
    check_source_ref(tag, Path.cwd(), candidate_commit=commit)


def check_archive(path: Path) -> None:
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    else:
        with tarfile.open(path) as archive:
            names = archive.getnames()
    problems = allowlist.problems(names, ignore=allowlist.REPOSITORY_NOTES)
    if problems:
        message = f"Archive contains files of the game: {problems[:5]}"
        raise ValueError(message)


def checksums(folder: Path) -> Path:
    target = folder / "SHA256SUMS"
    lines: list[str] = []
    for file in sorted(folder.iterdir()):
        if not file.is_file() or file == target:
            continue
        with file.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        lines.append(f"{digest}  {file.name}\n")
    _ = target.write_text("".join(lines), encoding="ascii")
    return target


@app.command()
def native(
    folder: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    output: Annotated[Path, typer.Argument(file_okay=False)],
    tag: Annotated[str, typer.Option()],
) -> None:
    check_tag(tag)
    issues = allowlist.problems_in_folder(folder, vendored=("_internal/",))
    if issues:
        raise ValueError(issues)
    output.mkdir(parents=True, exist_ok=True)
    name = f"RandomNewWorld-{__version__}-{sys.platform}"
    extension = "zip" if sys.platform == "win32" else "gztar"
    archive = Path(shutil.make_archive(str(output / name), extension, folder.parent, folder.name))
    typer.echo(archive)
    typer.echo(checksums(output))


@app.command()
def windows(
    hub: Annotated[Path, typer.Argument(exists=True, file_okay=False)],
    output: Annotated[Path, typer.Argument(file_okay=False)],
    tag: Annotated[str, typer.Option()],
) -> None:
    check_tag(tag)
    check_programs(hub)
    check_no_game_files(hub)
    output.mkdir(parents=True, exist_ok=True)
    standalone = output / "RandomNewWorld-Windows"
    _ = shutil.copytree(hub, standalone, ignore=shutil.ignore_patterns(".metadata"))
    command = '"%~dp0generator\\python\\python.exe" -B -I -X utf8 -m rnw.cli %*\r\n'
    _ = (standalone / "rnw.cmd").write_bytes(("@echo off\r\n" + command).encode("ascii"))
    _ = (standalone / "README.txt").write_text(
        "\n".join(
            (
                f"Random New World {__version__}",
                "",
                f"Open {LAUNCHER} for the window.",
                "Use rnw.cmd --help for the command line.",
                "Add portable.txt beside the launcher to keep data in a data/ folder there.",
                "EU5 is required to generate; world files and their maps open without it.",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    for name, folder in (("Windows", standalone), ("Workshop-Windows-Proton", hub)):
        archive = Path(
            shutil.make_archive(
                str(output / f"RandomNewWorld-{__version__}-{name}"),
                "zip",
                folder.parent,
                folder.name,
            )
        )
        typer.echo(archive)
    typer.echo(checksums(output))


@app.command()
def audit(path: Path) -> None:
    check_archive(path)


@app.command()
def checksum(folder: Annotated[Path, typer.Argument(exists=True, file_okay=False)]) -> None:
    typer.echo(checksums(folder))


if __name__ == "__main__":
    app()
