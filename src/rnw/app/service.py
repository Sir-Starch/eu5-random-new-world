"""Generating a world for a player: export, install, and remember what happened.

``generate`` is what the window's Generate button calls (and the command line could): it
runs the export for a world code into the application's own folder, installs the finished
mod into the profile when asked, and writes the outcome to the history, also when it was
cancelled or failed. Progress and cancel come from ``rnw.progress``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Protocol

from rnw.app import history, install
from rnw.app.paths import workspace
from rnw.app.worldcode import encode
from rnw.eu5_export import MOD_NAME
from rnw.eu5_nw_export import export_new_world
from rnw.progress import Cancelled, active, checkpoint, running

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.app.discovery import GameInstall, Profile
    from rnw.app.worldcode import WorldCode
    from rnw.progress import Progress

MOD_FOLDER: Final[str] = "rnw_exp_new_world"
BUNDLE_FOLDER: Final[str] = MOD_FOLDER
WAIT_PAUSE: Final[float] = 2.0


class Exporter(Protocol):
    """The export function, so tests can stand in for the real one."""

    def __call__(  # noqa: PLR0913 - the export's own signature
        self,
        game_dir: Path,
        output: Path,
        *,
        seed: int,
        settings: object,
        accept_build: str | None = None,
        settings_file: str | None = None,
        replace: bool = False,
        check_memory: bool = True,
        progress: Progress | None = None,
    ) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class Request:
    """What to generate and where it goes."""

    game: GameInstall
    code: WorldCode
    data: Path
    profile: Profile | None = None
    install: bool = True
    accept_build: str | None = None
    check_memory: bool = True


@dataclass(frozen=True, slots=True)
class Result:
    """What a finished generation produced."""

    code: str
    bundle: Path
    installed: Path | None
    seconds: float
    summary: dict[str, object]


def _install(bundle: Path, profile: Path, progress: Progress | None) -> Path:
    """Install the finished world; while the game holds the old one, wait until it lets go.

    Without a progress to cancel by (the command line), a world in use is an error at once.
    """
    with active(progress), running("install"):
        incoming = install.stage(bundle, profile, replace=True)
        try:
            return install.put_in_place(incoming)
        except install.WorldInUseError:
            if progress is None:
                install.discard(incoming)
                raise
        try:
            with running("waiting for the game"):
                while True:
                    time.sleep(WAIT_PAUSE)
                    checkpoint()
                    try:
                        return install.put_in_place(incoming)
                    except install.WorldInUseError:
                        continue
        except Cancelled:
            install.discard(incoming)
            raise


def _require_profile(request: Request) -> None:
    if request.install and request.profile is None:
        message = "There is no profile to install into; choose one or turn installing off"
        raise install.InstallError(message)


def generate(
    request: Request, progress: Progress | None = None, exporter: Exporter | None = None
) -> Result:
    """Generate (and install) the world of ``request``; the history records the outcome.

    Raises what the export raises, ``Cancelled`` when ``progress`` was cancelled and
    ``InstallError`` when the mod cannot be put into the profile; a failure after the
    export leaves the finished bundle in the application's folder.
    """
    run = export_new_world if exporter is None else exporter
    text = encode(request.code)
    started = time.monotonic()
    output = workspace(request.data) / MOD_FOLDER
    build = request.game.build_id
    try:
        _require_profile(request)
        output.parent.mkdir(parents=True, exist_ok=True)
        report = run(
            request.game.directory,
            output,
            seed=request.code.seed,
            settings=request.code.settings(),
            accept_build=request.accept_build,
            replace=True,
            check_memory=request.check_memory,
            progress=progress,
        )
        installed = None
        if request.install and request.profile is not None:
            installed = _install(output / BUNDLE_FOLDER, request.profile.directory, progress)
    except Cancelled:
        _ = history.record(request.data, history.Entry(text, history.now(), build, "cancelled"))
        raise
    except Exception as error:
        note = f"{type(error).__name__}: {error}"
        _ = history.record(request.data, history.Entry(text, history.now(), build, "failed", note))
        raise
    outcome = "installed" if installed is not None else "generated"
    _ = history.record(request.data, history.Entry(text, history.now(), build, outcome))
    keys = ("status", "canvas", "generated", "invariants")
    summary = {key: report[key] for key in keys if key in report}
    return Result(text, output, installed, time.monotonic() - started, summary)


assert MOD_NAME.fullmatch(MOD_FOLDER)  # noqa: S101 - the folder name must satisfy the export's rule
