"""Which window opens (ADR 0011): the Tauri window, or the classic Qt window.

The Tauri window is a program of its own, ``random-new-world``, that starts the generator as its
bridge. It lies in ``window`` beside the packaged application or in the hub's
``generator/window``; a source checkout's build of it is used when there is one. The classic
window opens instead when it is asked for (``--classic``, ``RNW_WINDOW=classic`` or the setting
in either window) or when the Tauri window cannot open: it is missing, cannot start (no
WebKitGTK on Linux), says it could not make its window (no WebView2 on Windows or in a Proton
prefix) or stops with an error within its first seconds. Nothing here imports Qt, so the Tauri
window costs the starting process only a small interpreter.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from rnw.app import paths, preferences

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

CLASSIC: Final[str] = "--classic"
ENV_WINDOW: Final[str] = "RNW_WINDOW"
CLASSIC_WINDOW: Final[str] = "classic"
FOLDER: Final[str] = "window"
PROGRAM: Final[str] = "random-new-world"
# The window's exit code when it could not make its window (desktop/src-tauri/src/main.rs).
NO_WINDOW: Final[int] = 3
# A window that stops with an error sooner than this did not open: the classic one takes over.
STARTUP: Final[float] = 20.0
# The window's own self-test: it starts the bridge and asks for the first state.
SELF_TEST_PATIENCE: Final[float] = 150.0
# What the window's self-test prints when the window shell and the bridge work.
SELF_TEST_LINE: Final[str] = "window shell and bridge work"


@dataclass(frozen=True, slots=True)
class Choice:
    """The Tauri window's program, or None and why the classic window opens instead."""

    program: Path | None
    reason: str


@dataclass(frozen=True, slots=True)
class Outcome:
    """How a run of the Tauri window ended: its exit code, and whether it opened at all."""

    code: int
    opened: bool
    reason: str = ""


def program_name(system: str | None = None) -> str:
    """The window's file name on ``system`` (``sys.platform`` by default)."""
    return f"{PROGRAM}.exe" if (system or sys.platform) == "win32" else PROGRAM


def checkout_build(package: Path | None = None) -> Path | None:
    """A source checkout's release build of the window, when the package runs from one."""
    root = (package or Path(__file__).resolve().parent.parent).parent.parent
    build = root / "desktop" / "src-tauri" / "target" / "release" / program_name()
    return build if (root / "pyproject.toml").is_file() and build.is_file() else None


def find_window(program_folder: Path, package: Path | None = None) -> Path | None:
    """The Tauri window that belongs to this generator: packaged beside it, else built in the
    source checkout it runs from."""
    for folder in (program_folder / FOLDER, program_folder / "generator" / FOLDER):
        candidate = folder / program_name()
        if candidate.is_file():
            return candidate
    return checkout_build(package)


def packaged(program_folder: Path) -> bool:
    """Whether this generator is a package (frozen, or the hub's interpreter), which must carry
    its Tauri window; a source checkout need not have built one."""
    return bool(getattr(sys, "frozen", False)) or (program_folder / "generator").is_dir()


def choose(
    arguments: Sequence[str],
    *,
    program_folder: Path | None = None,
    variables: Mapping[str, str] | None = None,
    data: Path | None = None,
) -> Choice:
    """Which window to open for ``arguments``, the environment and the saved choice."""
    folder = paths.program_directory() if program_folder is None else program_folder
    environment = os.environ if variables is None else variables
    if CLASSIC in arguments:
        return Choice(None, f"{CLASSIC} was given")
    if environment.get(ENV_WINDOW, "").strip().lower() == CLASSIC_WINDOW:
        return Choice(None, f"{ENV_WINDOW}={CLASSIC_WINDOW}")
    if data is None:
        data = paths.data_directory(variables=environment, program=folder)
    if preferences.load(data).window == CLASSIC_WINDOW:
        return Choice(None, "the classic window is chosen in Settings")
    window = find_window(folder)
    if window is None:
        return Choice(None, "the window program is not in this package")
    return Choice(window, "")


def window_environment(window: Path, variables: Mapping[str, str] | None = None) -> dict[str, str]:
    """The window's environment: a checkout's build runs the bridge on this interpreter."""
    environment = dict(os.environ if variables is None else variables)
    if window == checkout_build() and not environment.get("RNW_PYTHON"):
        environment["RNW_PYTHON"] = sys.executable
    return environment


def run_window(
    window: Path,
    arguments: Sequence[str] = (),
    *,
    clock: Callable[[], float] = time.monotonic,
    variables: Mapping[str, str] | None = None,
) -> Outcome:
    """Run the Tauri window until it closes; ``opened`` is False when it never did."""
    began = clock()
    try:
        process = subprocess.Popen(  # noqa: S603 - our own window program
            [str(window), *arguments], env=window_environment(window, variables)
        )
    except OSError as error:
        return Outcome(-1, opened=False, reason=f"the window could not start: {error}")
    code = process.wait()
    if code == 0:
        return Outcome(0, opened=True)
    if code == NO_WINDOW:
        return Outcome(code, opened=False, reason="the window could not make its web view")
    if clock() - began < STARTUP:
        return Outcome(code, opened=False, reason=f"the window stopped at once (exit code {code})")
    return Outcome(code, opened=True)


def self_test(window: Path, data: Path) -> tuple[int, str]:
    """Run the window's self-test with the bridge on ``data``; its exit code and output."""
    variables = {**os.environ, "RNW_DATA": str(data)}
    try:
        result = subprocess.run(  # noqa: S603 - our own window program
            [str(window), "--self-test"],
            env=window_environment(window, variables),
            check=False,
            capture_output=True,
            text=True,
            timeout=SELF_TEST_PATIENCE,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return result.returncode, (result.stdout + result.stderr).strip()
