"""Build the Tauri window for a package (ADR 0011) and the notices of what it is made of.

``build`` runs ``npm ci`` and ``tauri build --no-bundle`` in ``desktop/`` (the Tauri command
line builds the interface into the program; a plain ``cargo build`` would make a development
program that looks for the dev server) and copies the program, and on Windows the WebView2 loader
it links, into a package's ``window`` folder. ``write_notices`` lists every crate linked into the
program and every npm package whose code or fonts the interface carries, with their licence
files (each distinct text once) under ``licenses/window``; a Windows window carries Microsoft's
WebView2 loader (as a DLL with the GNU toolchain, linked in with MSVC) and its notice.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Final, cast

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DESKTOP: Final[Path] = ROOT / "desktop"
NAME: Final[str] = "random-new-world"
LOADER: Final[str] = "WebView2Loader.dll"
LOADER_NOTICE: Final[Path] = ROOT / "packaging" / "licenses" / "WebView2Loader.txt"
# npm packages compiled into the interface although they are development dependencies: Svelte's
# runtime is part of every component.
BUNDLED_DEVELOPMENT: Final[tuple[str, ...]] = ("svelte",)
LICENCE_WORDS: Final[tuple[str, ...]] = ("license", "licence", "copying", "notice", "copyright")


class WindowError(RuntimeError):
    """A step of building the window that cannot go on."""


def program(target: str | None = None) -> str:
    """The window's file name for a Rust ``target`` (the build machine's when None)."""
    windows = "windows" in (target or "") or (target is None and os.name == "nt")
    return f"{NAME}.exe" if windows else NAME


def loader_beside(target: str | None) -> bool:
    """Whether the program needs the WebView2 loader beside it: the GNU toolchain links the
    DLL, MSVC links Microsoft's static loader into the program (same SDK, same licence)."""
    return (target or "").endswith("windows-gnu")


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    if shutil.which(command[0]) is None:
        message = f"{command[0]} is not installed"
        raise WindowError(message)
    _ = subprocess.run(command, check=True, cwd=cwd, env=env)  # noqa: S603 - fixed tools, our arguments


def build(destination: Path, work: Path, *, target: str | None = None) -> Path:
    """Build the window into ``destination`` (a package's ``window`` folder); its program."""
    env = dict(os.environ)
    env["CARGO_TARGET_DIR"] = str(work)
    if target is not None:
        env["RUSTFLAGS"] = "-C link-arg=-Wl,--no-insert-timestamp"
    _run(["npm", "ci", "--prefer-offline", "--no-audit", "--no-fund"], cwd=DESKTOP)
    command = ["npx", "tauri", "build", "--no-bundle", "--ci"]
    if target is not None:
        command += ["--target", target]
    _run(command, cwd=DESKTOP, env=env)
    built = work / target / "release" if target is not None else work / "release"
    destination.mkdir(parents=True, exist_ok=True)
    names = [program(target)] + ([LOADER] if loader_beside(target) else [])
    for name in names:
        if not (built / name).is_file():
            message = f"The window build made no {name} in {built}"
            raise WindowError(message)
        _ = shutil.copy2(built / name, destination / name)
    return destination / program(target)


def _licence_files(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and any(word in path.name.lower() for word in LICENCE_WORDS)
    )


def crates(target: str | None = None) -> list[dict[str, object]]:
    """The crates linked into the window: its normal dependencies, transitively, for ``target``."""
    command = ["cargo", "metadata", "--format-version", "1", "--locked"]
    if target is not None:
        command += ["--filter-platform", target]
    found = subprocess.run(  # noqa: S603 - fixed tool, our arguments
        command, check=True, cwd=DESKTOP / "src-tauri", capture_output=True, text=True
    )
    metadata = cast("dict[str, object]", json.loads(found.stdout))
    packages = {
        str(item["id"]): item for item in cast("list[dict[str, object]]", metadata["packages"])
    }
    resolve = cast("dict[str, object]", metadata["resolve"])
    nodes = {str(node["id"]): node for node in cast("list[dict[str, object]]", resolve["nodes"])}
    root = str(resolve["root"])
    linked: set[str] = set()
    pending = [root]
    while pending:
        node = nodes[pending.pop()]
        for dependency in cast("list[dict[str, object]]", node["deps"]):
            kinds = cast("list[dict[str, object]]", dependency["dep_kinds"])
            if any(kind.get("kind") is None for kind in kinds):
                identifier = str(dependency["pkg"])
                if identifier not in linked:
                    linked.add(identifier)
                    pending.append(identifier)
    return sorted((packages[identifier] for identifier in linked), key=lambda p: str(p["name"]))


def npm_packages() -> list[tuple[str, str, str, Path]]:
    """The npm packages the interface carries: name, version, licence and folder."""
    lock = cast(
        "dict[str, dict[str, dict[str, object]]]",
        json.loads((DESKTOP / "package-lock.json").read_text(encoding="utf-8")),
    )
    found: list[tuple[str, str, str, Path]] = []
    for key, entry in lock["packages"].items():
        if not key.startswith("node_modules/"):
            continue
        name = key.removeprefix("node_modules/")
        if entry.get("dev") is True and name not in BUNDLED_DEVELOPMENT:
            continue
        if "node_modules/" in name:
            continue
        found.append(
            (name, str(entry.get("version", "")), str(entry.get("license", "")), DESKTOP / key)
        )
    return sorted(found)


def write_notices(folder: Path, target: str | None = None) -> None:
    """``licenses/window`` in a package: lists of crates and npm packages, and their licence
    files; the WebView2 loader's notice for a Windows window."""
    notices = folder / "licenses" / "window"
    texts = notices / "texts"
    shutil.rmtree(notices, ignore_errors=True)
    texts.mkdir(parents=True)

    def keep(files: list[Path]) -> str:
        names: list[str] = []
        for path in files:
            data = path.read_bytes()
            name = f"{hashlib.sha256(data).hexdigest()[:16]}.txt"
            if not (texts / name).is_file():
                _ = (texts / name).write_bytes(data)
            names.append(f"texts/{name}")
        return " ".join(names) or "(no licence file in the package; see its licence and source)"

    lines = ["Crates linked into the window: name version licence source licence-files"]
    for item in crates(target):
        manifest = Path(str(item["manifest_path"]))
        source = str(item.get("repository") or item.get("source") or "")
        licence = item.get("license") or "?"
        files = keep(_licence_files(manifest.parent))
        lines.append(f"{item['name']} {item['version']} {licence} {source} {files}")
    _ = (notices / "crates.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lines = ["npm packages in the interface: name version licence licence-files"]
    for name, version, licence, path in npm_packages():
        lines.append(f"{name} {version} {licence or '?'} {keep(_licence_files(path))}")
    _ = (notices / "npm.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if program(target).endswith(".exe"):
        _ = shutil.copyfile(LOADER_NOTICE, notices / LOADER_NOTICE.name)
