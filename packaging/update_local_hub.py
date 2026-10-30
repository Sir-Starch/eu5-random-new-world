"""Build and install the current development hub in an existing EU5 profile.

Run from the project environment: ``python packaging/update_local_hub.py --profile PATH``.
The previous hub is retained under the profile's .rnw-hub-backups directory. The game,
world mods, playsets and saves are never changed. The isolated Wine prefix and build
files stay under local_data. A failed build, self-test or copy leaves the hub in place.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import cast

import hub

from rnw import __version__

ROOT = Path(__file__).resolve().parent.parent


def manifest(folder: Path) -> dict[str, str]:
    """Hash every file so a partial or changed copy cannot be installed silently."""
    return {
        path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in folder.rglob("*")
        if path.is_file()
    }


def check_candidate(candidate: Path, version: str) -> None:
    """Require the current metadata, installed sources and package safety checks."""
    metadata = cast(
        "dict[str, object]",
        json.loads((candidate / ".metadata/metadata.json").read_text(encoding="utf-8-sig")),
    )
    if (
        metadata.get("id") != hub.MOD_ID
        or metadata.get("name") != hub.MOD_NAME
        or metadata.get("version") != version
    ):
        msg = "Hub metadata does not match the current product version"
        raise ValueError(msg)
    site = candidate / "generator/site"
    if not (site / f"eu5_random_new_world-{version}.dist-info/METADATA").is_file():
        msg = "The installed package version does not match the current product"
        raise ValueError(msg)
    for path in (ROOT / "src/rnw").rglob("*"):
        if path.is_file() and path.suffix in {".py", ".toml", ".json"}:
            installed = site / "rnw" / path.relative_to(ROOT / "src/rnw")
            if not installed.is_file() or installed.read_bytes() != path.read_bytes():
                msg = f"Hub source differs from the checkout: {path}"
                raise ValueError(msg)
    hub.check_programs(candidate)
    hub.check_no_game_files(candidate)


def self_test(candidate: Path, prefix: Path, version: str) -> None:
    """Run the real Windows generator offscreen in a dedicated Wine prefix: the classic window
    and the Tauri window's shell with its bridge (it opens no window)."""
    env = os.environ.copy()
    env.update(WINEPREFIX=str(prefix.resolve()), WINEDEBUG="-all", QT_QPA_PLATFORM="offscreen")
    wine = shutil.which("wine")
    if wine is None:
        msg = "Wine is required for the hub self-test"
        raise ValueError(msg)
    result = subprocess.run(  # noqa: S603 - fixed executable and arguments
        [
            wine,
            str(candidate / "generator/python/python.exe"),
            "-B",
            "-m",
            "rnw.gui",
            "--self-test",
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=180,
    )
    lines = (f"Random New World {version}: window,", f"Random New World {version}: window shell")
    if not all(line in result.stdout for line in lines):
        msg = f"Unexpected self-test result: {result.stdout} {result.stderr}"
        raise ValueError(msg)
    print(result.stdout.strip())


def verify_copy(folder: Path, wanted: dict[str, str]) -> None:
    """Stop installation when even one file differs."""
    if manifest(folder) != wanted:
        msg = f"Hub copy failed verification: {folder}"
        raise ValueError(msg)


def check_eu5_not_running() -> None:
    """Ensure EU5 is not running before modifying the profile's hub."""
    if sys.platform == "win32":
        tasklist = shutil.which("tasklist")
        if tasklist is None:
            msg = "Cannot check whether EU5 is running"
            raise ValueError(msg)
        found = subprocess.run(  # noqa: S603 - fixed executable and arguments
            [tasklist, "/fi", "IMAGENAME eq eu5.exe", "/nh", "/fo", "csv"],
            check=False,
            capture_output=True,
            text=True,
        )
        output = (found.stdout or "") + (found.stderr or "")
        if found.returncode != 0 or "eu5.exe" in output.lower():
            msg = "EU5 is running, or its process state could not be checked"
            raise ValueError(msg)
        return
    pgrep = shutil.which("pgrep")
    if pgrep is None:
        msg = "Cannot check whether EU5 is running"
        raise ValueError(msg)
    found = subprocess.run(  # noqa: S603 - fixed executable and arguments
        [pgrep, "-if", r"[\\/]eu5[.]exe([[:space:]]|$)"], check=False, capture_output=True
    )
    if found.returncode != 1:
        msg = "EU5 is running, or its process state could not be checked"
        raise ValueError(msg)


def install(candidate: Path, profile: Path, version: str) -> Path:
    """Stage and verify a new hub; keep the former hub intact and roll back on failure."""
    target = profile / "mod" / hub.MOD_FOLDER
    if not target.is_dir():
        msg = f"No existing development hub at {target}"
        raise ValueError(msg)
    old = cast(
        "dict[str, object]",
        json.loads((target / ".metadata/metadata.json").read_text(encoding="utf-8-sig")),
    )
    if old.get("id") not in {hub.MOD_ID, hub.LEGACY_MOD_ID}:
        msg = "The installed mod is not the development hub"
        raise ValueError(msg)
    old_version = old.get("version")
    if not isinstance(old_version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", old_version):
        msg = "The installed hub has no valid version"
        raise ValueError(msg)
    check_eu5_not_running()
    stamp = f"{time.time_ns()}"
    incoming = profile / "mod" / f".rnw-hub-incoming-{stamp}"
    backup = profile / ".rnw-hub-backups" / f"{old_version}-{stamp}"
    wanted = manifest(candidate)
    _ = shutil.copytree(candidate, incoming)
    verify_copy(incoming, wanted)
    backup.parent.mkdir(parents=True, exist_ok=True)
    _ = target.rename(backup)
    try:
        _ = incoming.rename(target)
        verify_copy(target, wanted)
    except Exception:
        if target.exists():
            _ = target.rename(incoming)
        _ = backup.rename(target)
        raise
    print(f"Installed {version} at {target}; previous hub retained at {backup}")
    return backup


class Options(argparse.Namespace):
    """Profile to update and, optionally, an already built candidate."""

    profile: Path = Path()
    candidate: Path | None = None


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and install the local development hub")
    _ = parser.add_argument("--profile", type=Path, required=True)
    _ = parser.add_argument("--candidate", type=Path, help="Use an already built current hub")
    args = parser.parse_args(namespace=Options())
    data = cast("dict[str, dict[str, str]]", tomllib.loads((ROOT / "pyproject.toml").read_text()))
    version = data["project"]["version"]
    if version != __version__:
        msg = "Sync the project environment before building the hub"
        raise ValueError(msg)
    if args.candidate:
        candidate = args.candidate.resolve()
    else:
        # Building from the local cache cannot silently start a large download.
        _ = os.environ.setdefault("UV_OFFLINE", "1")
        work = ROOT / "local_data/hub-updates" / f"{version}-{time.time_ns()}"
        work.mkdir(parents=True)
        hub.WORK = work / "build"
        cache = hub.WORK / "cache"
        cache.mkdir(parents=True)
        embedded = ROOT / "build/windows/cache" / hub.EMBEDDED_PYTHON.name
        if not embedded.is_file():
            msg = f"Pinned embedded Python is not cached: {embedded}"
            raise ValueError(msg)
        _ = shutil.copy2(embedded, cache / embedded.name)
        existing_cargo = ROOT / "build/windows/cargo"
        if existing_cargo.is_dir():
            (hub.WORK / "cargo").symlink_to(existing_cargo, target_is_directory=True)
        candidate = hub.build(work / hub.MOD_FOLDER, replace=False)
    check_candidate(candidate, version)
    prefix = ROOT / "local_data/hub-updates/wine-prefix"
    self_test(candidate, prefix, version)
    _ = install(candidate, args.profile.resolve(), version)


if __name__ == "__main__":
    main()
