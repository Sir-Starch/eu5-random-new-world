"""Build the hub mod: the data mod, the launcher and the Windows generator (ADR 0009).

Run ``uv run python packaging/hub.py [--replace]`` on Linux with MinGW, ``uv`` and the Rust
target ``x86_64-pc-windows-gnu`` installed. It writes ``dist/rnw_exp_hub`` (ignored by git):

- ``.metadata/metadata.json`` and ``LICENSE``;
- ``Random New World Generator.exe``, the launcher from ``packaging/launcher``;
- ``generator/python``: the official embeddable CPython, pinned by SHA-256, whose ``._pth``
  names ``../site`` as the only place to import from;
- ``generator/site``: the locked Windows wheels, installed with their hashes, Qt cut down to
  the modules the window imports, and our own wheel, built by maturin for Windows (with
  ``_native.pyd``, the package metadata, the licence and the Rust SBOM).

Every module is compiled to ``.pyc`` with unchecked hashes, so Python never needs to write
into the mod folder (the launcher passes ``-B`` as well). The only programs in the hub are the
launcher and the interpreter's ``python.exe`` and ``pythonw.exe``. Nothing is signed or
published. maturin comes from the range in ``build-system.requires``, not from the lock.
Until the hub carries an in-game window it is a development stand-in for the Workshop item.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

if TYPE_CHECKING:
    from http.client import HTTPResponse

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
WORK: Final[Path] = ROOT / "build" / "windows"
MOD_ID: Final[str] = "rnw_exp_hub"
LAUNCHER: Final[str] = "Random New World Generator.exe"
PYTHON_VERSION: Final[tuple[int, int]] = (3, 12)
RUST_TARGET: Final[str] = "x86_64-pc-windows-gnu"
MINGW: Final[str] = "x86_64-w64-mingw32"


@dataclass(frozen=True, slots=True)
class Download:
    """A file fetched once into the cache and checked against its published digest."""

    url: str
    sha256: str

    @property
    def name(self) -> str:
        """The file name at the end of the URL."""
        return self.url.rsplit("/", 1)[-1]


# MD5 fe8ef205f2e9c3ba44d0cf9954e1abd3 as listed on python.org's 3.12.10 release page.
EMBEDDED_PYTHON: Final[Download] = Download(
    "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip",
    "4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3",
)
PATH_FILE: Final[str] = "python312._pth"
PATH_LINES: Final[tuple[str, ...]] = ("python312.zip", ".", "../site", "import site")
PROGRAMS: Final[tuple[str, ...]] = (
    LAUNCHER,
    "generator/python/python.exe",
    "generator/python/pythonw.exe",
)
# Command-line entry points the wheels install; a Windows package has no use for them.
SCRIPT_FOLDERS: Final[tuple[str, ...]] = ("bin", "Scripts")

# What the window needs of PySide6 (it imports QtCore, QtGui and QtWidgets only), relative to
# the PySide6 folder; everything else in it is left out. The Windows platform plugin draws the
# window, the offscreen one runs ``--self-test`` without a display.
QT_KEPT: Final[tuple[str, ...]] = (
    "__init__.py",
    "_config.py",
    "_git_pyside_version.py",
    "Qt6Core.dll",
    "Qt6Gui.dll",
    "Qt6Widgets.dll",
    "QtCore.pyd",
    "QtGui.pyd",
    "QtWidgets.pyd",
    "pyside6.abi3.dll",
    "msvcp140*.dll",
    "vcruntime140*.dll",
    "support/*",
    "plugins/platforms/qwindows.dll",
    "plugins/platforms/qoffscreen.dll",
    "plugins/styles/qmodernwindowsstyle.dll",
)


class BuildError(RuntimeError):
    """A step of the build that cannot go on."""


def keeps_qt(relative: str) -> bool:
    """Whether the file at ``relative`` (inside the PySide6 folder, ``/``-separated) stays."""
    return any(fnmatch.fnmatchcase(relative, pattern) for pattern in QT_KEPT)


def version_fields(version: str) -> tuple[int, int, int, int]:
    """The four numbers Windows resources take for ``MAJOR.MINOR.PATCH``."""
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):  # noqa: PLR2004 - SemVer core
        message = f"Not a MAJOR.MINOR.PATCH version: {version!r}"
        raise BuildError(message)
    major, minor, patch = (int(part) for part in parts)
    return major, minor, patch, 0


def metadata(version: str) -> bytes:
    """The hub's ``metadata.json``, in the form the game reads (UTF-8 with BOM)."""
    payload: dict[str, object] = {
        "name": "RNW hub with generator (test, NOT GAME VALIDATED)",
        "id": MOD_ID,
        "version": version,
        "supported_game_version": "1.4.*",
        "short_description": (
            "Development stand-in for the Workshop item: the generator and its launcher; "
            "no game content"
        ),
        "tags": ["Map"],
        "relationships": [],
        "game_custom_data": {},
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8-sig")


def _run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    if shutil.which(command[0]) is None:
        message = f"{command[0]} is not installed"
        raise BuildError(message)
    _ = subprocess.run(command, check=True, cwd=cwd, env=env)  # noqa: S603 - fixed tools, our arguments


def fetch(download: Download, cache: Path) -> Path:
    """The cached file of ``download``, fetched if missing; a wrong digest is an error."""
    path = cache / download.name
    if not path.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".part")
        opened = urllib.request.urlopen(download.url, timeout=120)  # pyright: ignore[reportAny]  # noqa: S310 - pinned https URL
        with cast("HTTPResponse", opened) as response:
            _ = partial.write_bytes(response.read())
        _ = partial.replace(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != download.sha256:
        message = f"{path} has SHA-256 {digest}, expected {download.sha256}"
        raise BuildError(message)
    return path


def unpack_python(archive: Path, target: Path) -> None:
    """The embeddable Python, with a ``._pth`` that imports only from ``site``."""
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(target)
    if not (target / PATH_FILE).is_file():
        message = f"{archive.name} has no {PATH_FILE}; is it the 3.12 embeddable package?"
        raise BuildError(message)
    _ = (target / PATH_FILE).write_text("\n".join(PATH_LINES) + "\n", encoding="utf-8")


def install_wheels(site: Path) -> None:
    """The locked runtime dependencies as Windows wheels, each checked against its hash."""
    requirements = WORK / "requirements.txt"
    _run([
        "uv", "export", "--frozen", "--no-emit-project", "--no-dev", "--group", "gui",
        "--format", "requirements-txt", "--output-file", str(requirements),
    ])  # fmt: skip
    _run([
        "uv", "pip", "install", "--python-platform", "x86_64-pc-windows-msvc",
        "--python-version", ".".join(map(str, PYTHON_VERSION)), "--target", str(site),
        "--require-hashes", "--no-deps", "--no-build", "--requirements", str(requirements),
    ])  # fmt: skip


def prune_qt(site: Path) -> int:
    """Remove what the window does not use from PySide6; returns the bytes removed."""
    folder = site / "PySide6"
    if not (folder / "Qt6Core.dll").is_file():
        message = f"{folder} holds no Windows Qt"
        raise BuildError(message)
    removed = 0
    for path in sorted(folder.rglob("*"), reverse=True):
        relative = path.relative_to(folder).as_posix()
        if path.is_file() and not keeps_qt(relative):
            removed += path.stat().st_size
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    for name in QT_KEPT:
        if "*" not in name and not (folder / name).is_file():
            message = f"PySide6 lacks {name}, which the window needs"
            raise BuildError(message)
    return removed


def build_wheel() -> Path:
    """Our package as a Windows wheel: maturin cross-builds ``_native.pyd`` for it."""
    folder = WORK / "wheel"
    shutil.rmtree(folder, ignore_errors=True)
    env = dict(os.environ)
    env |= {
        "MATURIN_PEP517_ARGS": f"--target {RUST_TARGET} --locked",
        "CARGO_TARGET_DIR": str(WORK / "cargo"),
        "RUSTFLAGS": "-C link-arg=-Wl,--no-insert-timestamp",
    }
    _run(["uv", "build", "--wheel", "--out-dir", str(folder)], env=env)
    wheels = sorted(folder.glob("*-win_amd64.whl"))
    if len(wheels) != 1:
        message = f"Expected one Windows wheel in {folder}, found {[path.name for path in wheels]}"
        raise BuildError(message)
    return wheels[0]


def install_own_wheel(wheel: Path, site: Path) -> None:
    """Install our wheel beside the dependencies (they are already there)."""
    _run([
        "uv", "pip", "install", "--python-platform", "x86_64-pc-windows-msvc",
        "--python-version", ".".join(map(str, PYTHON_VERSION)), "--target", str(site),
        "--no-deps", str(wheel),
    ])  # fmt: skip


def remove_scripts(site: Path) -> None:
    """Drop the entry-point scripts the installer wrote for this machine."""
    for name in SCRIPT_FOLDERS:
        shutil.rmtree(site / name, ignore_errors=True)


def check_programs(root: Path) -> None:
    """The hub's programs are exactly the launcher and the interpreter's two."""
    found = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".exe", ".com", ".bat", ".cmd", ".ps1"}
    )
    if found != sorted(PROGRAMS):
        message = f"Programs in the hub are {found}, expected {sorted(PROGRAMS)}"
        raise BuildError(message)


def compile_modules(*folders: Path) -> None:
    """Byte-code for every module, valid whatever the file times are after a download."""
    if sys.version_info[:2] != PYTHON_VERSION:
        message = f"Run the build with Python {'.'.join(map(str, PYTHON_VERSION))}"
        raise BuildError(message)
    for folder in folders:
        _run([
            sys.executable, "-m", "compileall", "-q", "-j", "0",
            "--invalidation-mode", "unchecked-hash", str(folder),
        ])  # fmt: skip


def build_launcher(target: Path, version: str) -> None:
    """The launcher with its manifest (``asInvoker``) and version information."""
    numbers = version_fields(version)
    source = ROOT / "packaging" / "launcher"
    work = WORK / "launcher"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    replacements = {
        "@VERSION_COMMAS@": ",".join(map(str, numbers)),
        "@VERSION_DOTS@": ".".join(map(str, numbers)),
        "@VERSION@": version,
    }
    for name in ("launcher.rc", "launcher.manifest"):
        text = (source / name).read_text(encoding="utf-8")
        for key, value in replacements.items():
            text = text.replace(key, value)
        _ = (work / name).write_text(text, encoding="utf-8")
    _run([f"{MINGW}-windres", "launcher.rc", "-O", "coff", "-o", "launcher.res"], cwd=work)
    _run([
        f"{MINGW}-gcc", "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Wconversion", "-Werror",
        "-O2", "-s", "-municode", "-mwindows", "-Wl,--no-insert-timestamp",
        "-o", str(target / LAUNCHER), str(source / "launcher.c"), str(work / "launcher.res"),
        "-lshell32", "-lole32", "-luuid",
    ])  # fmt: skip


def size(folder: Path) -> int:
    """Bytes of all files under ``folder``."""
    return sum(path.stat().st_size for path in folder.rglob("*") if path.is_file())


def build(output: Path, *, replace: bool) -> Path:
    """Assemble the hub in a staging folder and move it to ``output`` whole."""
    from rnw import __version__  # noqa: PLC0415 - the version of the package being built

    if output.exists() and not replace:
        message = f"{output} exists; pass --replace to rebuild it"
        raise BuildError(message)
    stage = WORK / "stage" / MOD_ID
    shutil.rmtree(stage, ignore_errors=True)
    generator = stage / "generator"
    python, site = generator / "python", generator / "site"
    for folder in (stage / ".metadata", python, site):
        folder.mkdir(parents=True)
    _ = (stage / ".metadata" / "metadata.json").write_bytes(metadata(__version__))
    _ = shutil.copyfile(ROOT / "LICENSE", stage / "LICENSE")
    unpack_python(fetch(EMBEDDED_PYTHON, WORK / "cache"), python)
    install_wheels(site)
    removed = prune_qt(site)
    wheel = build_wheel()
    install_own_wheel(wheel, site)
    remove_scripts(site)
    compile_modules(site)
    build_launcher(stage, __version__)
    check_programs(stage)
    if output.exists():
        shutil.rmtree(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = shutil.move(stage, output)
    mib = 1 << 20
    print(f"{output}: {size(output) / mib:.0f} MiB ({removed / mib:.0f} MiB of Qt left out)")
    for path in (wheel, output / LAUNCHER):
        print(f"sha256 {hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    return output


class Options(argparse.Namespace):
    """The command line of the build."""

    output: Path = ROOT / "dist" / MOD_ID
    replace: bool = False


def main() -> int:
    """Parse the command line and build."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    _ = parser.add_argument("--output", type=Path, default=Options.output)
    _ = parser.add_argument("--replace", action="store_true", help="rebuild an existing output")
    options = parser.parse_args(namespace=Options())
    try:
        _ = build(options.output.resolve(), replace=options.replace)
    except (BuildError, subprocess.CalledProcessError) as error:
        print(f"hub build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
