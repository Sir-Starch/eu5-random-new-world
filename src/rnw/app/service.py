"""Making worlds for a player, and adding them to the game or taking them out again.

``generate`` is what the window's Generate button calls (and ``rnw world``): it runs the
export for a world code into the world's own folder in the generator's data, records the
world in the library and, when asked, adds it to the game. Every world is a mod of its own
(``rnw.app.library``), so a new world never replaces another; what to keep is the
player's choice. Progress and cancel come from ``rnw.progress``.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final, Protocol, cast

import numpy as np

from rnw import __version__, worldname
from rnw.app import exchange, install, library, logs, recovery
from rnw.app.paths import workspace
from rnw.app.worldcode import decode, encode
from rnw.eu5_canvas import select_canvas
from rnw.eu5_map import load_map
from rnw.eu5_nw_export import export_new_world
from rnw.inputs import compare
from rnw.messages import say
from rnw.parallel import cores
from rnw.png import COLOR_GRAY, encode_png
from rnw.progress import Cancelled, active, checkpoint, running
from rnw.record import Record, RecordError, Verdict, manifest_digest, output_entries, verdict
from rnw.settings import PRESETS

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.app.discovery import GameInstall, Profile
    from rnw.app.library import World
    from rnw.app.worldcode import WorldCode
    from rnw.landmask import LandMask
    from rnw.progress import Progress
    from rnw.settings import Settings
    from rnw.worldname import Label

WAIT_PAUSE: Final[float] = 2.0
CHECK_PREFIX: Final[str] = "rnw_exp_check_"


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
        world_label: Label | None = None,
        land_mask: LandMask | None = None,
        cache_dir: Path | None = None,
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
    show_new_world: bool = False
    name: str = ""
    parent: str = ""
    part: str = ""
    land_mask: LandMask | None = None
    output_folder: Path | None = None
    world_file: Path | None = None


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
    destinations = [
        path for path in (request.output_folder, request.world_file) if path is not None
    ]
    if len(destinations) > 1 or (request.world_file is not None and request.install):
        message = say("destination.one")
        raise install.InstallError(message)
    for destination in destinations:
        if destination.resolve().is_relative_to(request.game.directory.resolve()):
            message = say("destination.outside")
            raise install.InstallError(message)
    if request.output_folder is not None and not request.output_folder.is_dir():
        message = say("destination.folder")
        raise install.InstallError(message)
    if request.world_file is not None and request.world_file.exists():
        message = say("destination.exists", file=request.world_file)
        raise install.InstallError(message)
    if request.install and request.profile is None:
        message = say("destination.profile")
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
    logs.get().info(
        "generate %s on build %s, install=%s, show=%s",
        text,
        build,
        request.install,
        request.show_new_world,
    )
    world = library.World(
        id=library.world_id(text, build),
        code=text,
        preset=request.code.preset,
        seed=request.code.seed,
        generator=__version__,
        game_build=build,
        created=library.now(),
        seconds=0.0,
        name=worldname.clean_name(request.name),
        parent=request.parent,
        part=request.part,
        show_new_world=request.show_new_world,
    )
    output = library.folder(request.data, world)
    previous = library.load_one(output)
    if previous is not None:
        world = replace(
            world,
            name=request.name or previous.name,
            notes=previous.notes,
            starred=previous.starred,
            user_tag=previous.user_tag,
            revealed=previous.revealed,
            show_new_world=request.show_new_world,
        )
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
        world_label=worldname.label(world.preset, worldname.tag_of(world.id), world.name),
        land_mask=request.land_mask,
        cache_dir=request.data / "cache" / "land",
    )
    world = replace(
        world,
        seconds=round(time.monotonic() - started, 1),
        record=Record.from_json(report["record"]) if "record" in report else None,
    )
    library.save(request.data, world)
    installed = None
    mod = output / world.folder
    recovery.write(request.data, world, mod)
    if request.show_new_world:
        library.show(request.data, world, mod, shown=True)
    if request.output_folder is not None:
        _ = exchange.copy_mod(mod, request.output_folder)
    if request.world_file is not None:
        _ = exchange.export_world(request.data, world, request.world_file)
        shutil.rmtree(mod)
    if request.install and request.profile is not None:
        installed = _install(mod, request.profile.directory, progress)
    keys = ("status", "canvas", "generated", "invariants")
    summary = {key: report[key] for key in keys if key in report}
    logs.get().info(
        "generated %s in %.1f s, installed=%s",
        world.id,
        time.monotonic() - started,
        installed is not None,
    )
    return Result(world, output, installed, time.monotonic() - started, summary)


class Maker(Protocol):
    """``generate``, so that the window's tests can stand in for it."""

    def __call__(self, request: Request, progress: Progress | None = None) -> Result: ...


def compatible(
    world: World, *, game: GameInstall, data: Path, workers: int | None = None
) -> bool | None:
    """Whether the world made for one game build is still valid for this one.

    True for the same build, and for another build when none of the game files the world's
    export read has changed (a patch that touched nothing it read; ADR 0010, G). False when one
    has; None when the bundle no longer lists them, so that nothing can be said.
    """
    if world.game_build == game.build_id:
        return True
    changed = inputs_changed(world, game=game, data=data, workers=workers)
    return None if changed is None else not changed


def add_to_game(  # noqa: PLR0913 - a world, where it goes and how the work is shown
    world: World,
    *,
    game: GameInstall,
    data: Path,
    profile: Profile,
    progress: Progress | None = None,
    exporter: Exporter | None = None,
    show_new_world: bool | None = None,
    make: Maker | None = None,
) -> Result:
    """Put a recorded world into the game: its kept mod, or the world made again from its code.

    The kept mod goes in as it is when it is valid for this game: made for this build, or for
    another whose files it read are all the same. Otherwise the world is made again for this
    build, which is a world of its own (the code is the same, the vanilla map it is cut from is
    not) and has no name yet; the same world made again keeps the player's name.
    """
    kept = library.kept(data, world)
    shown = library.world_shown(world) if show_new_world is None else show_new_world
    selected = replace(world, show_new_world=shown)
    if kept is not None and compatible(world, game=game, data=data):
        started = time.monotonic()
        if show_new_world is not None and show_new_world != world.show_new_world:
            library.show(data, selected, kept, shown=shown)
        if selected != world:
            library.save(data, selected)
        recovery.write(data, selected, kept)
        installed = _install(kept, profile.directory, progress)
        return Result(
            selected, library.folder(data, selected), installed, time.monotonic() - started, {}
        )
    request = Request(
        game=game,
        code=decode(world.code),
        data=data,
        profile=profile,
        show_new_world=shown,
        name=world.name if world.game_build == game.build_id else "",
        land_mask=required_land_mask(data, world),
    )
    return make(request, progress) if make is not None else generate(request, progress, exporter)


def remove_from_game(world_folder: str, profile: Profile) -> None:
    """Take a world's mod out of the game (its record and pictures stay in the library)."""
    _ = install.uninstall([world_folder], profile.directory)


def undo_roll(  # noqa: PLR0913
    world: World,
    parent: World,
    *,
    game: GameInstall,
    profile: Profile,
    data: Path,
    progress: Progress | None = None,
    show_new_world: bool | None = None,
    make: Maker | None = None,
) -> Result:
    present = library.installed(profile.directory, parent)
    if present is None:
        result = add_to_game(
            parent,
            game=game,
            profile=profile,
            data=data,
            progress=progress,
            show_new_world=show_new_world,
            make=make,
        )
    else:
        restored = replace(
            parent,
            show_new_world=(parent.show_new_world if show_new_world is None else show_new_world),
        )
        if restored != parent:
            library.show(data, restored, present, shown=library.world_shown(restored))
            library.save(data, restored)
        result = Result(restored, library.folder(data, restored), present, 0.0, {})
    remove_from_game(world.folder, profile)
    return result


def delete(world: World, data: Path, profile: Profile | None) -> None:
    """Take the world out of the game if it is there, then forget it."""
    if profile is not None and library.installed(profile.directory, world) is not None:
        remove_from_game(world.folder, profile)
    library.forget(data, world)


class LandImageError(RuntimeError):
    """A world drawn on an image the library no longer has."""


def required_land_mask(data: Path, world: World) -> LandMask | None:
    """The land image the world is made on: None for land the generator draws.

    Raises ``LandImageError`` when the world's code names an image and the world's folder no
    longer holds it, since the world cannot be made again without it.
    """
    wanted = decode(world.code).settings().mask.id
    if not wanted:
        return None
    found = library.land_mask(data, world)
    if found is None or found.id != wanted:
        message = say("land_image.gone")
        raise LandImageError(message)
    return found


TEMPLATE_STEP: Final[int] = 4
TEMPLATE_AREA: Final[int] = 90
TEMPLATE_OUTSIDE: Final[int] = 20


def land_template(
    game: GameInstall, output: Path, settings: Settings = PRESETS["continents"]
) -> tuple[int, int]:
    """Write a picture of the area the New World can fill, to draw land on; returns its size.

    Dark grey is the area, black is outside it. The player paints land in white (any program),
    and ``Land from an image`` builds the world on it. The picture shows the area at a quarter
    of the map's size and is for the player's own use: it is cut from the installed game's map.
    """
    game_map = load_map(game.directory)
    canvas = select_canvas(
        game_map,
        settings.new_world.ocean_band_px,
        expanded=bool(settings.new_world.expand_oceans or settings.new_world.landform),
    )
    shrunk = canvas.mask[::TEMPLATE_STEP, ::TEMPLATE_STEP]
    grey = np.where(shrunk, TEMPLATE_AREA, TEMPLATE_OUTSIDE).astype(np.uint8)
    output.parent.mkdir(parents=True, exist_ok=True)
    _ = output.write_bytes(encode_png(grey, color_type=COLOR_GRAY, compression="zlib"))
    height, width = cast("tuple[int, int]", grey.shape)
    return width, height


class CheckError(RuntimeError):
    """A world that cannot be checked, and why."""


@dataclass(frozen=True, slots=True)
class Check:
    """What checking a world found: the verdict, and what differs when it is not identical."""

    verdict: Verdict
    reproduced: bool | None
    changed_inputs: list[str]
    differing: list[str]
    seconds: float


def inputs_changed(
    world: World, *, game: GameInstall, data: Path, workers: int | None = None
) -> list[str] | None:
    """The game files the world's export read that are gone or different now; None when the
    bundle no longer has the list, so the files cannot be compared. Hashes about fourteen thousand
    files, a second or a few."""
    manifest = library.inputs_manifest(data, world)
    if manifest is None:
        return None
    found = compare(game.directory, manifest, workers=cores() if workers is None else workers)
    return [*found.missing, *found.changed]


def check(  # noqa: PLR0913 - a world, the game and where the work is shown
    world: World,
    *,
    game: GameInstall,
    data: Path,
    progress: Progress | None = None,
    exporter: Exporter | None = None,
    check_memory: bool = True,
) -> Check:
    """Find out whether this generator makes the world again, byte for byte (ADR 0010, G).

    The record decides first: a world of another algorithm epoch is made differently by this
    generator, and the game's files the world read are compared with the ones now; both are
    answered without making anything. Otherwise the world is made again from the record's own
    settings into a folder of its own, which is deleted, and every file of the mod but its
    ``.metadata`` is compared with what the world's export wrote. Raises ``CheckError`` for a
    world made before records.
    """
    record = world.record
    if record is None:
        message = say("check.no_record")
        raise CheckError(message)
    started = time.monotonic()
    logs.get().info(
        "check %s: record of epoch %d, release %s", world.id, record.algorithm, record.release
    )
    early = verdict(record)
    if early in {Verdict.OTHER_ALGORITHM, Verdict.NEWER_FORMAT}:
        return Check(early, None, [], [], time.monotonic() - started)
    with active(progress), running("compare inputs"):
        changed = inputs_changed(world, game=game, data=data)
    if changed:
        return Check(Verdict.OTHER_INPUTS, None, changed, [], time.monotonic() - started)
    expected = library.exported_outputs(data, world)
    if expected is None or manifest_digest(expected) != record.output_sha256:
        message = say("check.bundle")
        raise CheckError(message)
    run = export_new_world if exporter is None else exporter
    scratch = workspace(data) / f"{CHECK_PREFIX}{world.id}"
    try:
        report = run(
            game.directory,
            scratch,
            seed=record.seed,
            settings=record.resolved_settings(),
            accept_build=None,
            replace=True,
            check_memory=check_memory,
            progress=progress,
            world_code=record.code,
            world_label=None,
            land_mask=required_land_mask(data, world),
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    try:
        made = Record.from_json(report["record"])
    except (KeyError, RecordError) as error:
        message = f"The rebuild returned no record: {error}"
        raise CheckError(message) from error
    reproduced = made.output_sha256 == record.output_sha256
    logs.get().info("check %s: reproduced=%s", world.id, reproduced)
    differing: list[str] = []
    if not reproduced:
        again = output_entries(cast("list[dict[str, object]]", report["files"]), scratch.name)
        differing = sorted(
            path for path in expected.keys() | again.keys() if expected.get(path) != again.get(path)
        )
    return Check(
        Verdict.IDENTICAL if reproduced else Verdict.OTHER_INPUTS,
        reproduced,
        [],
        differing,
        time.monotonic() - started,
    )
