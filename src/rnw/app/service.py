"""Making worlds for a player, and adding them to the game or taking them out again.

``generate`` is what the window's Generate button calls (and ``rnw world``): it runs the
export for a world code into the world's own folder in the generator's data, records the
world in the library and, when asked, adds it to the game. Every world is a mod of its own
(``rnw.app.library``), so a new world never replaces another; what to keep is the
player's choice. Progress and cancel come from ``rnw.progress``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final, Protocol

from rnw import __version__
from rnw.app import install, library
from rnw.app.worldcode import decode, encode
from rnw.eu5_nw_export import export_new_world
from rnw.progress import Cancelled, active, checkpoint, running

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.app.discovery import GameInstall, Profile
    from rnw.app.library import World
    from rnw.app.worldcode import WorldCode
    from rnw.progress import Progress

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
        world_code: str | None = None,
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
    reveal_thumbnail: bool = False


@dataclass(frozen=True, slots=True)
class Result:
    """What a finished generation produced."""

    world: World
    bundle: Path
    installed: Path | None
    seconds: float
    summary: dict[str, object]

    @property
    def code(self) -> str:
        """The world code."""
        return self.world.code


def _install(mod: Path, profile: Path, progress: Progress | None) -> Path:
    """Move a finished world into the game; while the game holds a mod of that name, wait.

    Without a progress to cancel by (the command line), a mod in use is an error at once.
    """
    with active(progress), running("install"):
        incoming = install.stage(mod, profile, replace=True, move=True)
        try:
            return install.put_in_place(incoming)
        except install.WorldInUseError:
            if progress is None:
                _ = incoming.rename(mod)
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
            _ = incoming.rename(mod)
            raise


def _require_profile(request: Request) -> None:
    if request.install and request.profile is None:
        message = "There is no profile to install into; choose one or turn installing off"
        raise install.InstallError(message)


def generate(
    request: Request, progress: Progress | None = None, exporter: Exporter | None = None
) -> Result:
    """Make the world of ``request`` as a mod of its own, record it, and add it if asked.

    Raises what the export raises and ``Cancelled`` when ``progress`` was cancelled; then
    nothing is recorded. A world that was made but could not be added is recorded and kept
    beside the generator, so ``add_to_game`` can try again without making it anew.
    """
    run = export_new_world if exporter is None else exporter
    _require_profile(request)
    started = time.monotonic()
    text = encode(request.code)
    build = request.game.build_id
    world = library.World(
        id=library.world_id(text, build),
        code=text,
        preset=request.code.preset,
        seed=request.code.seed,
        generator=__version__,
        game_build=build,
        created=library.now(),
        seconds=0.0,
    )
    output = library.folder(request.data, world)
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
        world_code=text,
    )
    world = replace(world, seconds=round(time.monotonic() - started, 1))
    library.save(request.data, world)
    installed = None
    mod = output / world.folder
    if request.reveal_thumbnail:
        _ = library.write_thumbnail(request.data, world, mod, revealed=True)
    if request.install and request.profile is not None:
        installed = _install(mod, request.profile.directory, progress)
    keys = ("status", "canvas", "generated", "invariants")
    summary = {key: report[key] for key in keys if key in report}
    return Result(world, output, installed, time.monotonic() - started, summary)


def add_to_game(  # noqa: PLR0913 - a world, where it goes and how the work is shown
    world: World,
    *,
    game: GameInstall,
    data: Path,
    profile: Profile,
    progress: Progress | None = None,
    exporter: Exporter | None = None,
    reveal_thumbnail: bool = False,
) -> Result:
    """Put a recorded world into the game: its kept mod, or the world made again from its code.

    A world made for another game build is made again for this one, which is a world of its
    own (the code is the same, the vanilla map it is cut from is not).
    """
    kept = library.kept(data, world)
    if kept is not None and world.game_build == game.build_id:
        started = time.monotonic()
        installed = _install(kept, profile.directory, progress)
        return Result(world, library.folder(data, world), installed, time.monotonic() - started, {})
    request = Request(
        game=game,
        code=decode(world.code),
        data=data,
        profile=profile,
        reveal_thumbnail=reveal_thumbnail,
    )
    result = generate(request, progress, exporter)
    if world.name and result.world.id == world.id:
        renamed = library.rename(data, result.world, world.name)
        return Result(renamed, result.bundle, result.installed, result.seconds, result.summary)
    return result


def remove_from_game(world_folder: str, profile: Profile) -> None:
    """Take a world's mod out of the game (its record and pictures stay in the library)."""
    _ = install.uninstall([world_folder], profile.directory)


def delete(world: World, data: Path, profile: Profile | None) -> None:
    """Take the world out of the game if it is there, then forget it."""
    if profile is not None and library.installed(profile.directory, world) is not None:
        remove_from_game(world.folder, profile)
    library.forget(data, world)
