"""What the window knows and does, without drawing anything.

The controller holds the player's choices for a new world (type, seed, the changed
settings), the library of worlds made before and which entry is selected, and it runs the
long work (making a world, adding one to the game, taking one out, deleting one) on a thread
of its own. It tells observers when something changed,
from whichever thread changed it; the window turns that into a signal for its own thread.
Nothing here imports Qt, so it is tested without a display.
"""

from __future__ import annotations

import json
import threading
import traceback
from dataclasses import replace
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol, cast

from rnw import __version__, atlas, landmask, worldfile, worldname
from rnw.app import (
    candidates,
    controls,
    diagnostics,
    discovery,
    exchange,
    gamenames,
    install,
    library,
    logs,
    paths,
    preferences,
    quick,
    random_types,
    recovery,
    service,
    session,
    transfer,
)
from rnw.app.discovery import GameInstall, Profile
from rnw.app.library import Placement
from rnw.app.session import GameState
from rnw.app.worldcode import (
    WorldCode,
    WorldCodeError,
    decode,
    encode,
    random_seed,
    reproduces,
    rolled,
    with_new_seed,
)
from rnw.gui import mapstyle
from rnw.gui.text import (
    choose_language,
    explain,
    grouped,
    language,
    stage_text,
    system_language,
    text,
)
from rnw.layers import PARTS, rolls_of
from rnw.messages import Said
from rnw.png import COLOR_RGB, encode_png
from rnw.progress import STAGES, Cancelled, Progress, Update, active
from rnw.record import Verdict, verdict
from rnw.settings import PRESETS, WORLD_TYPES, SettingsError, build_settings
from rnw.wording import render

if TYPE_CHECKING:
    from collections.abc import Callable

    from rnw.app.library import World
    from rnw.atlas import Atlas
    from rnw.landmask import LandMask

SEED_MAX: Final[int] = (1 << 64) - 1
ERROR_LOG: Final[str] = "last-error.log"
NEW: Final[str] = "new"
STRAY: Final[str] = "stray:"
# What the record alone says (ADR 0010, G): the algorithm; anything else is "not checked yet".
REPRODUCTION: Final[dict[Verdict, str]] = {
    Verdict.OTHER_ALGORITHM: "repro.other_algorithm",
    Verdict.NEWER_FORMAT: "repro.newer_format",
}


class Phase(Enum):
    """Where the controller's work stands."""

    IDLE = "idle"
    RUNNING = "running"
    CANCELLING = "cancelling"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(Enum):
    """The kind of work the thread does."""

    GENERATE = "generate"
    ADD = "add"
    REMOVE = "remove"
    DELETE = "delete"
    CHECK = "check"
    REROLL = "reroll"
    RECEIVE = "receive"
    SEND = "send"
    COPY = "copy"
    TEMPLATE = "template"
    CANDIDATES = "candidates"
    QUEUE = "queue"
    UNDO = "undo"


class Generator(Protocol):
    """``service.generate``, so tests can stand in for it."""

    def __call__(
        self, request: service.Request, progress: Progress | None = None
    ) -> service.Result: ...


class Checker(Protocol):
    """``service.check``, so tests can stand in for it."""

    def __call__(
        self,
        world: World,
        *,
        game: GameInstall,
        data: Path,
        progress: Progress | None = None,
    ) -> service.Check: ...


def _generate(request: service.Request, progress: Progress | None = None) -> service.Result:
    return service.generate(request, progress)


def _check(
    world: World, *, game: GameInstall, data: Path, progress: Progress | None = None
) -> service.Check:
    return service.check(world, game=game, data=data, progress=progress)


class Controller:
    """The window's state and the actions the buttons call."""

    def __init__(
        self,
        data: Path | None = None,
        environment: discovery.Environment | None = None,
        generator: Generator = _generate,
        program_folder: Path | None = None,
        checker: Checker = _check,
    ) -> None:
        self.data: Path = paths.data_directory(program=program_folder) if data is None else data
        self.environment: discovery.Environment = environment or discovery.Environment()
        self.generator: Generator = generator
        self.checker: Checker = checker
        self.program_folder: Path | None = program_folder
        self.games: list[GameInstall] = []
        self.profiles: list[Profile] = []
        self.game: GameInstall | None = None
        self.profile: Profile | None = None
        self.preset: str = "continents"
        # The random world type chosen in the window (``random_types``), None for a world type.
        self.mode: str | None = None
        self.seed: int = random_seed()
        self._generation_seed: int | None = None
        self.changes: dict[str, int] = {}
        self.other_changes: dict[str, object] = {}
        self.install: bool = True
        self.output_folder: Path | None = None
        self.world_file: Path | None = None
        self.notice: str = ""
        self.phase: Phase = Phase.IDLE
        self.task: Task | None = None
        self.task_target: str = ""
        self.fraction: float = 0.0
        self.running: tuple[str, ...] = ()
        self.finished: frozenset[str] = frozenset()
        self.message: str = ""
        self.result: service.Result | None = None
        self.checks: dict[str, service.Check] = {}
        self.worlds: list[World] = []
        self._library_signature: recovery.Signature = ()
        self.strays: list[Path] = []
        self.selection: str = NEW
        self.preferences: preferences.Preferences = preferences.load(self.data)
        _ = library.migrate_visibility(self.data, default=self.preferences.show_new_world)
        logs.start(self.data)
        self._observers: list[Callable[[], None]] = []
        self._compatible: dict[tuple[str, str], bool | None] = {}
        self.runs: int = 0
        self.land_mask: LandMask | None = None
        self.last_import: exchange.Imported | None = None
        self.candidates: list[candidates.Candidate] = []
        self.candidate_code: WorldCode | None = None
        self.queue: list[service.Request] = []
        self.queue_done: int = 0
        self._lock: threading.Lock = threading.Lock()
        self._progress: Progress | None = None
        self._thread: threading.Thread | None = None

    # -- observers -----------------------------------------------------------------------------

    def subscribe(self, observer: Callable[[], None]) -> None:
        """Call ``observer`` after every change, from the thread that changed it."""
        self._observers.append(observer)

    def _changed(self) -> None:
        for observer in list(self._observers):
            observer()

    # -- the game and the profile --------------------------------------------------------------

    def _profile_dir(self) -> Path | None:
        return self.profile.directory if self.profile is not None else None

    def discover(self) -> None:
        """Look for the game and the profile again, take the first of each, read the library.

        Worlds retired by an earlier install that the game held then are deleted now if it
        has let go of them.
        """
        self.games = discovery.find_games(self.environment, self.program_folder)
        chosen = Path(self.preferences.game_dir) if self.preferences.game_dir else None
        if chosen is not None and discovery.is_game(chosen):
            # A folder the player chose that discovery found too keeps what discovery knows of
            # it (its build); one it did not find is taken as it is.
            known = next((item for item in self.games if item.directory == chosen), None)
            self.games = [
                known or GameInstall(chosen, None, ""),
                *(item for item in self.games if item.directory != chosen),
            ]
        self.profiles = discovery.find_profiles(self.environment, self.games)
        picked = Path(self.preferences.profile_dir) if self.preferences.profile_dir else None
        if picked is not None and picked.is_dir():
            self.profiles = [
                Profile(picked, "chosen", (picked / "mod").is_dir()),
                *(item for item in self.profiles if item.directory != picked),
            ]
        self.game = self.games[0] if self.games else None
        self.profile = self.profiles[0] if self.profiles else None
        logs.get().info(
            "found %d game(s), used %s (build %s); %d profile(s), used %s",
            len(self.games),
            self.game.directory.name if self.game else "none",
            self.game.build_id if self.game else "-",
            len(self.profiles),
            self.profile.kind if self.profile else "none",
        )
        if self.profile is not None:
            _ = install.sweep(self.profile.directory)
        self.refresh_library()

    def choose_game(self, directory: Path) -> str | None:
        """Take ``directory`` as the installation; returns the problem, or None."""
        if not discovery.is_game(directory):
            return text("not_a_game")
        self.game = GameInstall(directory, None, "")
        self.games = [self.game, *(item for item in self.games if item.directory != directory)]
        self._remember(game_dir=str(directory))
        self._changed()
        return None

    def choose_profile(self, directory: Path) -> str | None:
        """Take ``directory`` as the profile; returns the problem, or None."""
        if not directory.is_dir():
            return text("not_a_profile")
        self.profile = Profile(directory, "chosen", (directory / "mod").is_dir())
        self.profiles = [self.profile, *(p for p in self.profiles if p.directory != directory)]
        self._remember(profile_dir=str(directory))
        self.refresh_library()
        return None

    def window_language(self) -> str:
        """The language the window should speak: the player's choice, the game's, the system's.

        Read before the window is built, so the game is looked for once on its own here.
        """
        games = discovery.find_games(self.environment, self.program_folder)
        game = discovery.game_language(games[0]) if games else None
        return choose_language(self.preferences.language, game, system_language())

    def set_language(self, language: str) -> None:
        """Remember the window's language (empty: follow the game); it applies at the next start."""
        self._remember(language=language)
        self._changed()

    def set_window(self, classic: bool) -> None:  # noqa: FBT001 - the dialog's box
        """Remember which window opens at the next start: the classic one, or the Tauri one."""
        self._remember(window="classic" if classic else "")
        self._changed()

    def _remember(self, **chosen: str) -> None:
        """Keep a folder the player chose by hand, so that the generator is not asked again."""
        self.preferences = replace(self.preferences, **chosen)
        preferences.save(self.data, self.preferences)

    # -- the new world's choices ---------------------------------------------------------------

    def set_preset(self, name: str) -> None:
        """Choose a world type; the changed values go back to the type's own."""
        if name in PRESETS and name in WORLD_TYPES and (name != self.preset or self.mode):
            self.mode = None
            self.preset = name
            self.changes, self.other_changes = {}, {}
            self.notice = ""
            self._changed()

    def set_mode(self, mode: str) -> None:
        """Choose Random or Total Chaos: a world type is drawn now and with each new seed."""
        if mode in random_types.MODES:
            self.mode = mode
            self.other_changes, self.notice = {}, ""
            self._draw()
            self._changed()

    def _draw(self) -> None:
        """Draw the world type, and for Total Chaos the Advanced values, of the random mode."""
        if self.mode is not None:
            self.preset, self.changes = random_types.draw(self.mode)

    def set_seed(self, value: str) -> str | None:
        """Take a seed typed as a number, or a world code pasted in its place."""
        cleaned = value.strip()
        if cleaned.upper().startswith("RNW"):
            return self.use_code(cleaned)
        try:
            seed = int(cleaned)
        except ValueError:
            return text("bad_seed")
        if not 0 <= seed <= SEED_MAX:
            return text("bad_seed")
        self.seed = seed
        _ = self.other_changes.pop("rolls", None)
        self.notice = ""
        self._changed()
        return None

    def randomize(self) -> None:
        """A new random seed, on a land of its own: every roll goes back to 0. Random draws its
        world type again; Total Chaos keeps its values, which it draws only when chosen."""
        self.seed = random_seed()
        _ = self.other_changes.pop("rolls", None)
        self.notice = ""
        if self.mode == random_types.RANDOM:
            self._draw()
        self._changed()

    def retry_new_seed(self) -> str | None:
        """Retry a failed generation with the same settings and a different seed."""
        if self.task is not Task.GENERATE or self.phase is not Phase.FAILED:
            return text("ready_busy")
        reason = self.problem()
        if reason is not None:
            return reason
        previous = {self.seed, self._generation_seed}
        seed = random_seed()
        # A random collision must not repeat the failed world.
        while seed in previous:
            seed = (seed + 1) % (SEED_MAX + 1)
        self.seed = seed
        _ = self.other_changes.pop("rolls", None)
        self.notice = ""
        self._changed()
        return self.start()

    def use_code(self, value: str) -> str | None:
        """Take the type, seed and settings of a pasted code; returns the problem, or None."""
        try:
            code = decode(value)
        except WorldCodeError as error:
            return explain(error)
        shown, other = controls.flat(code.resolved_changes())
        outside = [key for key, number in shown.items() if not controls.BY_KEY[key].allows(number)]
        if code.preset not in WORLD_TYPES or outside:
            names = ", ".join(text(f"control.{key}") for key in outside) or code.preset
            return text("outside_range", names=names)
        self.mode, self.preset, self.seed = None, code.preset, code.seed
        self.changes = {
            key: number
            for key, number in shown.items()
            if number != controls.BY_KEY[key].default(code.preset)
        }
        self.other_changes = other
        notices: list[str] = []
        if not reproduces(code):
            notices.append(text("other_version", made=code.generator, current=__version__))
        if set(other) - {"rolls", "mask"}:
            notices.append(text("other_changes"))
        wanted = code.settings().mask.id
        self.land_mask = self.land_mask if self.land_mask and self.land_mask.id == wanted else None
        if wanted and self.land_mask is None:
            notices.append(text("needs_land_image"))
        rolls = {part: number for part, number in rolls_of(code.settings()).items() if number}
        if rolls:
            notices.append(
                text("rolled_code", parts=", ".join(f"{p} {n}" for p, n in rolls.items()))
            )
        self.notice = " ".join(notices)
        self._changed()
        return None

    def value(self, key: str) -> int:
        """The current value of a control: the changed one, or the world type's."""
        return self.changes.get(key, controls.BY_KEY[key].default(self.preset))

    def set_value(self, key: str, number: int) -> None:
        """Change one setting, kept inside its playable range."""
        control = controls.BY_KEY[key]
        number = min(control.high, max(control.low, number))
        if number == control.default(self.preset):
            _ = self.changes.pop(key, None)
        else:
            self.changes[key] = number
        self._changed()

    def quick_level(self, name: str) -> str | None:
        """The level of a quick setting that the controls hold now; None: a custom mix."""
        values = {control.key: self.value(control.key) for control in controls.CONTROLS}
        return quick.BY_NAME[name].current(self.preset, values)

    def set_quick(self, name: str, level: str) -> None:
        """Set the controls of one answer of a quick setting."""
        for key, number in quick.BY_NAME[name].level(level).values(self.preset).items():
            if number == controls.BY_KEY[key].default(self.preset):
                _ = self.changes.pop(key, None)
            else:
                self.changes[key] = number
        self._changed()

    def reset_value(self, key: str) -> None:
        """Give one setting back the world type's value."""
        if self.changes.pop(key, None) is not None:
            self._changed()

    def reset_values(self) -> None:
        """Give every setting back the world type's value."""
        if self.changes or self.other_changes:
            self.changes, self.other_changes = {}, {}
            self._changed()

    def _change_document(self) -> dict[str, object] | None:
        document = controls.nested(self.changes) or {}
        for section, fields in self.other_changes.items():
            merged = cast("dict[str, object]", document.setdefault(section, {}))
            if isinstance(fields, dict):
                merged.update(cast("dict[str, object]", fields))
        return document or None

    def world_code(self) -> WorldCode:
        """The code of the new world as chosen now."""
        return WorldCode(self.preset, self.seed, __version__, self._change_document())

    @property
    def code(self) -> str:
        """The world code of the current choices."""
        return encode(self.world_code())

    def estimated_locations(self) -> int:
        """Locations the chosen world will have, roughly."""
        return controls.estimated_locations(build_settings(self.preset, self._change_document()))

    # -- the library ---------------------------------------------------------------------------

    def refresh_library(self) -> None:
        """Read the worlds and the strays in the game again."""
        previous_stray = self.selected_stray()
        _ = recovery.adopt(self.data, self._profile_dir())
        self.worlds = library.load(self.data)
        self.strays = library.strays(self._profile_dir(), self.worlds)
        if previous_stray is not None:
            adopted = next((w for w in self.worlds if w.folder == previous_stray.name), None)
            if adopted is not None:
                self.selection = adopted.id
        known = self.selected_world() is not None or self.selected_stray() is not None
        if self.selection != NEW and not known:
            self.selection = NEW
        self._library_signature = recovery.signature(self.data, self._profile_dir())
        self._changed()

    def poll_library(self) -> None:
        """Notice externally added worlds without interrupting generation or editing the list."""
        if (
            not self.busy
            and recovery.signature(self.data, self._profile_dir()) != self._library_signature
        ):
            self.refresh_library()

    def select(self, selection: str) -> None:
        """Show the new-world page (``NEW``), a world (its id) or a stray (``STRAY`` + folder)."""
        if selection != self.selection:
            self.selection = selection
            self._changed()

    def selected_world(self) -> World | None:
        """The world selected, if one is."""
        return next((world for world in self.worlds if world.id == self.selection), None)

    def selected_stray(self) -> Path | None:
        """The stray selected, if one is."""
        if not self.selection.startswith(STRAY):
            return None
        name = self.selection.removeprefix(STRAY)
        return next((stray for stray in self.strays if stray.name == name), None)

    def picture(self, world: World) -> Path | None:
        """A world's picture: covered unless the player chose to see the New World."""
        return library.picture(self.data, world, revealed=self.shown(world))

    def shown(self, world: World) -> bool:
        """Whether this world's New World is shown in the generator and in EU5."""
        return library.world_shown(world, default=self.preferences.show_new_world)

    def placement(self, world: World) -> Placement:
        """Where the world's mod is."""
        return library.placement(self.data, self._profile_dir(), world)

    def name(self, world: World) -> str:
        """The player's name for the world, or its type and tag (ADR 0010)."""
        return worldname.display_name(world.preset, worldname.tag_of(world.id), world.name)

    def rename(self, world: World, name: str) -> str | None:
        """Give the world a name of the player's (blank or the default: none); returns what
        could not be done, or None.

        The name goes into the metadata of the world's mod, in the game or kept, so the game's
        list shows it; while the game holds the file that has to wait until the world is added
        again.
        """
        cleaned = worldname.clean_name(name)
        if cleaned == worldname.display_name(world.preset, worldname.tag_of(world.id)):
            cleaned = ""
        if cleaned == world.name:
            return None
        renamed = library.rename(self.data, world, cleaned)
        mods = (library.installed(self._profile_dir(), renamed), library.kept(self.data, renamed))
        held = [mod for mod in mods if mod is not None and not library.retitle(renamed, mod)]
        self.refresh_library()
        return text("retitle_later") if held else None

    def changed_count(self, world: World) -> int:
        """How many settings the world's code changes."""
        try:
            shown, other = controls.flat(decode(world.code).changes)
        except WorldCodeError:
            return 0
        extra = sum(
            len(cast("dict[str, object]", fields)) if isinstance(fields, dict) else 1
            for section, fields in other.items()
            if section not in {"rolls", "mask"}
        )
        return len(shown) + extra

    def like(self, world: World) -> None:
        """A new world with the type and settings of ``world`` and a fresh seed."""
        try:
            code = decode(world.code)
        except WorldCodeError:
            return
        shown, other = controls.flat(code.resolved_changes())
        self.mode, self.preset = None, code.preset
        self.changes = {k: v for k, v in shown.items() if controls.BY_KEY[k].allows(v)}
        self.other_changes = other
        _ = self.other_changes.pop("rolls", None)
        self.land_mask = library.land_mask(self.data, world)
        self.seed = random_seed()
        self.notice = ""
        self.selection = NEW
        self._changed()

    def edit_selected(self) -> None:
        """Load the selected world's type, seed and settings into the new-world page, to change
        the settings of its peoples or resources on the same land (a version of it)."""
        world = self.selected_world()
        if world is None:
            return
        try:
            code = decode(world.code)
        except WorldCodeError:
            return
        shown, other = controls.flat(code.resolved_changes())
        self.mode, self.preset, self.seed = None, code.preset, code.seed
        self.changes = {k: v for k, v in shown.items() if controls.BY_KEY[k].allows(v)}
        self.other_changes = other
        self.land_mask = library.land_mask(self.data, world)
        self.notice = ""
        self.selection = NEW
        self._changed()

    # -- versions of a world -------------------------------------------------------------------

    def listed(self) -> list[tuple[World, int]]:
        """The worlds as the window lists them: versions of one continent together."""
        return library.grouped(self.worlds)

    def annotate(self, world: World, notes: str, user_tag: str, *, starred: bool) -> None:
        updated = replace(
            world, notes=notes[:16384], user_tag=user_tag.strip()[:64], starred=starred
        )
        library.save(self.data, updated)
        self.refresh_library()

    def parent_of(self, world: World) -> World | None:
        """The world this one is a version of, if the library still has it."""
        return next((item for item in self.worlds if item.id == world.parent), None)

    def undo_selected(self) -> str | None:
        if self.busy:
            return text("ready_busy")
        world = self.selected_world()
        parent = self.parent_of(world) if world is not None else None
        if world is None or parent is None:
            return None
        if self.placement(world) is not Placement.IN_GAME:
            self.select(parent.id)
            return None
        if self.game is None or self.profile is None:
            return text("ready_no_game")
        game, profile, data = self.game, self.profile, self.data
        generator, show = self.generator, self.shown(parent)

        def work(progress: Progress) -> service.Result:
            return service.undo_roll(
                world,
                parent,
                game=game,
                profile=profile,
                data=data,
                progress=progress,
                show_new_world=show,
                make=generator,
            )

        return self._run(Task.UNDO, world.id, work)

    def reroll_selected(self, part: str, *, keep_both: bool = False) -> str | None:
        """Make one part (``rnw.layers``) of the selected world again on the same land, as a
        version of it; returns why not, or None.

        A world in the game is replaced in the game by its new version unless ``keep_both``; one
        that is not in the game is made beside the generator and the profile is not touched.
        """
        world = self.selected_world()
        if self.busy:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        if world is None or part not in PARTS:
            return None
        try:
            code = rolled(decode(world.code), part)
            drawn = service.required_land_mask(self.data, world)
        except (WorldCodeError, service.LandImageError) as error:
            return explain(error)
        game, data, generator = self.game, self.data, self.generator
        profile = self.profile if self.placement(world) is Placement.IN_GAME else None
        request = service.Request(
            game=game,
            code=code,
            data=data,
            profile=profile,
            install=profile is not None,
            show_new_world=self.shown(world),
            parent=world.id,
            part=part,
            land_mask=drawn,
        )

        def work(progress: Progress) -> service.Result:
            result = generator(request, progress)
            if profile is not None and not keep_both and result.world.id != world.id:
                service.remove_from_game(world.folder, profile)
            return result

        return self._run(Task.REROLL, world.id, work)

    def set_show_new_world(self, show: bool) -> None:  # noqa: FBT001 - the dialog's box
        """Remember the visibility choice for worlds made from now on."""
        self.preferences = replace(self.preferences, show_new_world=show)
        preferences.save(self.data, self.preferences)
        self._changed()

    def set_world_visibility(
        self,
        world: World,
        show: bool,  # noqa: FBT001 - the world's checkbox value
    ) -> str | None:
        """Change one world's saved visibility and its existing mod presentation."""
        if self.busy:
            return text("ready_busy")
        if self.shown(world) == show and world.show_new_world is not None:
            return None
        changed = replace(world, show_new_world=show)
        mods = (
            library.installed(self._profile_dir(), world),
            library.kept(self.data, world),
        )
        try:
            for mod in mods:
                if mod is not None:
                    library.show(self.data, changed, mod, shown=show)
            library.save(self.data, changed)
        except OSError as error:
            return explain(error)
        self.refresh_library()
        return None

    # -- what can run now ----------------------------------------------------------------------

    @property
    def busy(self) -> bool:
        """Whether the thread is at work."""
        return self.phase in {Phase.RUNNING, Phase.CANCELLING}

    def problem(self) -> str | None:
        """Why Generate cannot start now, or None when it can."""
        if self.busy:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        if self.install and self.profile is None:
            return text("ready_no_profile")
        return self._choices_problem()

    def _choices_problem(self) -> str | None:
        """What is wrong with the choices: too many locations, or a land image that is missing."""
        try:
            estimate = self.estimated_locations()
        except SettingsError as error:
            return explain(error)
        if estimate > controls.LOCATION_BUDGET:
            return text(
                "too_many_locations",
                count=grouped(estimate),
                budget=grouped(controls.LOCATION_BUDGET),
            )
        wanted = self.world_code().settings().mask.id
        if wanted and (self.land_mask is None or self.land_mask.id != wanted):
            return text("needs_land_image")
        return None

    def choose_land_image(self, path: Path) -> str | None:
        """Make the land of the new world the picture at ``path`` (white is land, black is sea);
        returns what is wrong with the picture, or None."""
        try:
            mask = landmask.read(path)
        except landmask.LandMaskError as error:
            return explain(error)
        self.land_mask = mask
        self.other_changes["mask"] = {"id": mask.id}
        self.notice = ""
        self._changed()
        return None

    def save_land_template(self, output: Path) -> str | None:
        """Write the picture of the area the New World can fill, to draw land on, as a task;
        returns why not, or None."""
        if self.busy:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        game = self.game

        def work(_progress: Progress) -> None:
            _ = service.land_template(
                game, output, build_settings(self.preset, self._change_document())
            )

        return self._run(Task.TEMPLATE, str(output), work)

    def clear_land_image(self) -> None:
        """Go back to land the generator draws."""
        self.land_mask = None
        _ = self.other_changes.pop("mask", None)
        self._changed()

    def world_problem(self) -> str | None:
        """Why the world actions cannot run now, or None when they can."""
        if self.busy:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        if self.profile is None:
            return text("ready_no_profile")
        return None

    def stage_rows(self) -> list[tuple[str, str]]:
        """(label, state) of every weighted stage in order: waiting, running or done."""
        rows: list[tuple[str, str]] = []
        for name, info in STAGES.items():
            if info.weight == 0:
                continue
            state = (
                "done"
                if name in self.finished
                else "running"
                if name in self.running
                else "waiting"
            )
            rows.append((stage_text(name), state))
        return rows

    def running_text(self) -> str:
        """The stages that run now, in the window's language."""
        return ", ".join(stage_text(name) for name in self.running)

    def estimated_remaining(self) -> float | None:
        """Estimated seconds left in the active weighted generation."""
        with self._lock:
            if (
                self.phase is not Phase.RUNNING
                or self.task is not Task.GENERATE
                or "waiting for the game" in self.running
            ):
                return None
            progress = self._progress
        return progress.estimated_remaining() if progress is not None else None

    # -- the work ------------------------------------------------------------------------------

    def sketch_candidates(self, count: int = 6) -> str | None:
        if self.busy:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        code, game = self.world_code(), self.game
        try:
            seeds = candidates.roll(count)
        except candidates.CandidateError as error:
            return explain(error)
        self.candidates, self.candidate_code = [], None

        def work(_progress: Progress) -> None:
            found = candidates.sketch(game.directory, code.settings(), seeds)
            with self._lock:
                self.candidates, self.candidate_code = found, code

        return self._run(Task.CANDIDATES, NEW, work)

    def choose_candidate(self, index: int) -> None:
        if self.busy or self.candidate_code is None or not 0 <= index < len(self.candidates):
            return
        code = with_new_seed(self.candidate_code, self.candidates[index].seed)
        _ = self.use_code(encode(code))
        self.selection = NEW
        self._changed()

    def enqueue(self) -> str | None:
        reason = self.problem()
        if reason is not None or self.game is None:
            return reason
        self.queue.append(self._request())
        self._changed()
        return None

    def clear_queue(self) -> None:
        if not self.busy:
            self.queue.clear()
            self._changed()

    def start_queue(self) -> str | None:
        """Generate snapshots in order; a cancellation or failure leaves the rest pending."""
        if self.busy:
            return text("ready_busy")
        if not self.queue:
            return text("queue_empty")
        self.queue_done = 0
        generator = self.generator

        def work(progress: Progress) -> service.Result | None:
            result = None
            while self.queue:
                progress.checkpoint()
                progress.reset_stages()
                result = generator(self.queue[0], progress)
                with self._lock:
                    _ = self.queue.pop(0)
                    self.queue_done += 1
                    self.finished, self.fraction = frozenset(), 0.0
                self._changed()
            return result

        return self._run(Task.QUEUE, NEW, work)

    def _request(self) -> service.Request:
        if self.game is None:
            message = "Choose the game before generating"
            raise SettingsError(message)
        return service.Request(
            game=self.game,
            code=self.world_code(),
            data=self.data,
            profile=self.profile,
            install=self.install,
            show_new_world=self.preferences.show_new_world,
            land_mask=self.land_mask,
            output_folder=self.output_folder,
            world_file=self.world_file,
        )

    def start(self) -> str | None:
        """Start making the new world; returns why it cannot, or None."""
        reason = self.problem()
        if reason is not None or self.game is None:
            return reason
        request = self._request()
        self._generation_seed = request.code.seed
        generator = self.generator

        def work(progress: Progress) -> service.Result:
            return generator(request, progress)

        return self._run(Task.GENERATE, NEW, work)

    def reproduction(self, world: World) -> str:
        """What is known of whether this generator makes ``world`` again, in a sentence.

        The record decides what it can without the game's files; a check, once it has run,
        settles the rest (ADR 0010).
        """
        record = world.record
        if record is None:
            return text("repro.none")
        found = self.checks.get(world.id)
        if found is not None and found.reproduced is not None:
            first = found.differing[0] if found.differing else "?"
            return (
                text("repro.identical", count=record.output_count)
                if found.reproduced
                else text("repro.differs", count=len(found.differing), first=first)
            )
        if found is not None and found.verdict is Verdict.OTHER_INPUTS:
            return text("repro.other_inputs", count=len(found.changed_inputs))
        key = REPRODUCTION.get(verdict(record), "repro.same_algorithm")
        return text(key, release=record.release)

    # -- world files ---------------------------------------------------------------------------

    def import_file(self, path: Path) -> str | None:
        """Take a world file into the library; returns what went wrong, or None.

        A compact ``.rnworld`` is taken at once. A transferred built world (``.rnworld-mod``) is
        a gigabyte and runs as a task; it needs the game, to check that it is the one the world
        was made from.
        """
        if not worldfile.is_world_file(path):
            return text("not_world_file")
        if path.name.lower().endswith(worldfile.MOD_EXTENSION):
            return self._receive(path)
        try:
            taken = exchange.import_world(self.data, path)
        except (exchange.ExchangeError, worldfile.WorldFileError, OSError) as error:
            logs.get().warning("world file %s refused: %s", path.name, error)
            return explain(error)
        self.selection = taken.world.id
        self.last_import = taken
        self.refresh_library()
        return None

    def _receive(self, path: Path) -> str | None:
        if self.busy:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        game, data = self.game, self.data

        def work(_progress: Progress) -> None:
            taken = transfer.receive_mod(data, path, game)
            with self._lock:
                self.selection = taken.world.id

        return self._run(Task.RECEIVE, path.name, work)

    def copy_mod_to(self, world: World, destination: Path) -> str | None:
        """Copy the world's mod into a folder of the player's choice, as a task; returns why not."""
        if self.busy:
            return text("ready_busy")
        mod = library.installed(self._profile_dir(), world) or library.kept(self.data, world)
        if mod is None:
            return text("no_mod_to_send")

        def work(_progress: Progress) -> None:
            _ = exchange.copy_mod(mod, destination)

        return self._run(Task.COPY, world.id, work)

    def export_file(self, world: World, output: Path) -> str | None:
        """Write the world's compact world file; returns what went wrong, or None."""
        try:
            _ = exchange.export_world(self.data, world, output)
        except (worldfile.WorldFileError, OSError) as error:
            return explain(error)
        return None

    def send_built(self, world: World, output: Path) -> str | None:
        """Write the built world, its mod included, as a file to carry to another machine of
        the player's; returns why not, or None. Runs as a task."""
        if self.busy:
            return text("ready_busy")
        mod = library.installed(self._profile_dir(), world) or library.kept(self.data, world)
        if mod is None:
            return text("no_mod_to_send")
        data = self.data

        def work(_progress: Progress) -> None:
            _ = transfer.send_mod(data, world, mod, output)

        return self._run(Task.SEND, world.id, work)

    # -- the atlas and its maps ----------------------------------------------------------------

    def atlas(self, world: World) -> Atlas | None:
        """The world's atlas, or None when it has none."""
        return library.atlas(self.data, world)

    def words(self, found: Atlas) -> atlas.Words:
        """How the window writes an atlas: its own legend words, the game's names of the
        identifiers when the game is here (else the identifiers made readable), the world's
        names in the window's language."""
        speaking = language()
        names: dict[str, str] = {}
        if self.game is not None:
            names = gamenames.game_names(self.game.directory, speaking, mapstyle.identifiers(found))
        return atlas.Words(
            label=lambda key: text(f"legend.{key}"),
            key=lambda key: names.get(key) or atlas.pretty(key),
            name=lambda name: render(name, speaking),
        )

    def revealed(self, world: World) -> bool:
        """Whether the world's New World may be shown here."""
        return self.shown(world) or world.revealed

    def reveal_world(self, world: World) -> None:
        """Show this world's maps (the player's choice, kept with the world)."""
        _ = library.reveal(self.data, world)
        self.refresh_library()

    def summary(self, world: World) -> str:
        """One line on what the world holds, from its atlas ('' without one)."""
        found = self.atlas(world)
        if found is None:
            return ""
        return text(
            "summary", **{key: grouped(value) for key, value in atlas.totals(found).items()}
        )

    def maps_to_compare(self) -> list[tuple[World, Atlas]]:
        """The worlds whose maps may be shown and that have an atlas."""
        pairs = ((world, self.atlas(world)) for world in self.worlds if self.revealed(world))
        return [(world, found) for world, found in pairs if found is not None]

    def save_map(self, world: World, layer: str, output: Path) -> str | None:
        """Write the picture of ``layer`` of a revealed world as a PNG; returns why not, or None."""
        found = self.atlas(world)
        if found is None or not self.revealed(world):
            return text("covered_maps")
        try:
            data = encode_png(atlas.render(found, layer), color_type=COLOR_RGB, compression="zlib")
            _ = output.write_bytes(data)
        except (OSError, atlas.AtlasError) as error:
            return explain(error)
        return None

    def save_preview(self, world: World, output: Path) -> str | None:
        """Copy the world's overview picture, covered unless it may be shown; returns why not."""
        source = self.picture(world)
        if source is None:
            return text("preview_missing")
        try:
            _ = output.write_bytes(source.read_bytes())
        except OSError as error:
            return explain(error)
        return None

    def compatibility(self, world: World) -> bool | None:
        """Whether ``world`` is still valid for the game's build: the same build, or another
        whose files the world read are all unchanged; None when that cannot be known.

        Hashing the files takes a second or so, so the answer is kept for the build.
        """
        game = self.game
        if game is None:
            return None
        key = (world.id, game.build_id)
        if key not in self._compatible:
            self._compatible[key] = service.compatible(world, game=game, data=self.data)
        return self._compatible[key]

    def check_selected(self) -> str | None:
        """Make the selected world again and compare it with the first time; returns why it
        cannot, or None. Needs the game's files, not the profile."""
        world = self.selected_world()
        if self.busy:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        if world is None:
            return None
        if world.record is None:
            return text("repro.none")
        game, data, checks, checker = self.game, self.data, self.checks, self.checker

        def work(progress: Progress) -> None:
            checks[world.id] = checker(world, game=game, data=data, progress=progress)

        return self._run(Task.CHECK, world.id, work)

    def add_selected(self) -> str | None:
        """Put the selected world into the game; returns why it cannot, or None."""
        world = self.selected_world()
        reason = self.world_problem()
        if reason is not None or world is None or self.game is None or self.profile is None:
            return reason
        game, profile, data = self.game, self.profile, self.data
        show = self.shown(world)
        generator = self.generator

        def work(progress: Progress) -> service.Result:
            return service.add_to_game(
                world,
                game=game,
                data=data,
                profile=profile,
                progress=progress,
                show_new_world=show,
                make=generator,
            )

        return self._run(Task.ADD, world.id, work)

    def remove_selected(self) -> str | None:
        """Take the selected world, or stray, out of the game; returns why not, or None."""
        return self.remove_entries((self.selection,))

    def removal_problem(self) -> str | None:
        """Removing a mod needs its profile, but never the game installation."""
        if self.busy:
            return text("ready_busy")
        if self.profile is None:
            return text("remove_no_profile")
        return None

    def removable_entries(self, selections: tuple[str, ...]) -> tuple[str, ...]:
        """Installed folders among known library entries and strays, in selection order."""
        folders = {
            world.id: world.folder
            for world in self.worlds
            if self.placement(world) is Placement.IN_GAME
        }
        folders.update((f"{STRAY}{path.name}", path.name) for path in self.strays)
        return tuple(dict.fromkeys(folders[key] for key in selections if key in folders))

    def remove_entries(self, selections: tuple[str, ...]) -> str | None:
        """Remove a snapshot of installed entries, keeping their library records."""
        reason = self.removal_problem()
        profile = self.profile
        if reason is not None or profile is None:
            return reason
        folders = self.removable_entries(selections)
        if not folders:
            return None

        def work(progress: Progress) -> None:
            progress.checkpoint()
            # The installer validates every target before removing the first folder.
            _ = install.uninstall(folders, profile.directory)

        return self._run(Task.REMOVE, ", ".join(selections), work)

    def delete_selected(self) -> str | None:
        """Take the selected world out of the game and forget it; returns why not, or None."""
        return self.delete_entries((self.selection,))

    def delete_entries(self, selections: tuple[str, ...]) -> str | None:
        """Forget the selected library worlds; strays and unknown IDs are never deleted."""
        if self.busy:
            return text("ready_busy")
        worlds = tuple(world for world in self.worlds if world.id in selections)
        if not worlds:
            return None
        data, profile = self.data, self.profile

        def work(progress: Progress) -> None:
            for count, world in enumerate(worlds):
                progress.checkpoint()
                try:
                    service.delete(world, data, profile)
                except (OSError, install.InstallError) as error:
                    message = text(
                        "batch_delete_failed", name=self.name(world), done=count, message=error
                    )
                    raise RuntimeError(message) from error

        return self._run(Task.DELETE, ", ".join(world.id for world in worlds), work)

    def _run(
        self, task: Task, target: str, work: Callable[[Progress], service.Result | None]
    ) -> str | None:
        progress = Progress(self._on_update)
        self.runs += 1
        logs.get().info("task %s started, target %s", task.value, target)
        with self._lock:
            self.phase, self.task, self.task_target = Phase.RUNNING, task, target
            self.fraction, self.running, self.finished = 0.0, (), frozenset()
            self.message, self.result = "", None
            self._progress = progress
        self._changed()
        self._thread = threading.Thread(
            target=self._work, args=(work, progress), name=task.value, daemon=True
        )
        self._thread.start()
        return None

    def cancel(self) -> None:
        """Ask the running work to stop; the window shows 'cancelling' until it has."""
        with self._lock:
            progress = self._progress
            if self.phase is not Phase.RUNNING or progress is None:
                return
            self.phase = Phase.CANCELLING
        progress.cancel()
        self._changed()

    def wait(self, timeout: float | None = None) -> None:
        """Block until the work ends (for tests and for closing the window)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def _on_update(self, update: Update) -> None:
        with self._lock:
            self.fraction = update.fraction
            self.running = update.running
            if update.finished:
                self.finished = self.finished | {update.stage}
                logs.get().info(
                    "stage %s done, %.0f%% of the work", update.stage, update.fraction * 100
                )
        self._changed()

    def _work(self, work: Callable[[Progress], service.Result | None], progress: Progress) -> None:
        outcome = Phase.FINISHED
        message = ""
        result: service.Result | None = None
        try:
            with active(progress):
                result = work(progress)
        except Cancelled:
            outcome = Phase.CANCELLED
        except Exception as error:  # noqa: BLE001 - whatever failed is shown to the player
            outcome, message = Phase.FAILED, self._explain(error)
        logs.get().info(
            "task %s ended: %s %s", self.task.value if self.task else "?", outcome.value, message
        )
        # Publish a terminal phase only when the library already contains the result. The
        # window may react to FINISHED before the worker returns from this method.
        self.refresh_library()
        with self._lock:
            self.phase, self.result, self.message = outcome, result, message
            self.running = ()
            if outcome is Phase.FINISHED:
                self.fraction = 1.0
            if result is not None:
                self.selection = result.world.id
        self._changed()

    def _explain(self, error: Exception) -> str:
        """The error for the player; the traceback goes to the log and to a file for a report."""
        logs.get().exception("task failed: %s", error)
        try:
            self.data.mkdir(parents=True, exist_ok=True)
            _ = (self.data / ERROR_LOG).write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        from rnw.currents import CurrentError  # noqa: PLC0415 - load generation code only on failure
        from rnw.eu5_nw_export import LocationLimitError  # noqa: PLC0415
        from rnw.eu5_rivers import RiverRasterError  # noqa: PLC0415
        from rnw.eu5_seas import SeaError  # noqa: PLC0415
        from rnw.ports import PortError  # noqa: PLC0415
        from rnw.sea_routes import LaneError  # noqa: PLC0415

        cause: BaseException | None = error
        while cause is not None:
            if self.task is Task.GENERATE and isinstance(cause, LocationLimitError):
                return text(
                    "generation_location_limit",
                    count=grouped(cause.count),
                    limit=grouped(cause.limit),
                )
            if self.task is Task.GENERATE and isinstance(
                cause, (CurrentError, LaneError, PortError, SeaError)
            ):
                return text("generation_sea_error", detail=str(cause))
            if self.task is Task.GENERATE and isinstance(cause, RiverRasterError):
                return text("generation_river_error", detail=str(cause))
            if self.task is Task.GENERATE and isinstance(cause, OSError):
                return text("generation_file_error", detail=str(cause))
            cause = cause.__cause__
        detail = explain(error)
        if (
            self.task is Task.GENERATE
            and not isinstance(error, (SettingsError, worldfile.WorldFileError))
            and not (error.args and isinstance(error.args[0], Said))
        ):
            return text("generation_unexpected_error", detail=detail)
        return detail

    # -- bug reports ---------------------------------------------------------------------------

    def snapshot(self) -> diagnostics.Snapshot:
        """What a diagnostics file reports of this session."""
        return diagnostics.Snapshot(
            data=self.data,
            games=tuple(self.games),
            game=self.game,
            profiles=tuple(self.profiles),
            profile=self.profile,
            worlds=tuple(self.worlds),
            strays=tuple(self.strays),
            show_new_world=self.preferences.show_new_world,
            program_folder=self.program_folder,
        )

    def save_diagnostics(self, output: Path) -> str | None:
        """Write the file for a bug report; returns what went wrong, or None."""
        try:
            _ = diagnostics.write(output, self.snapshot())
        except OSError as error:
            logs.get().exception("diagnostics could not be written")
            return text("diagnostics_failed", problem=explain(error))
        return None

    # -- what to do in EU5 next ----------------------------------------------------------------

    def _mod_title(self, mod: Path) -> str:
        try:
            row = cast(
                "dict[str, object]",
                json.loads((mod / install.METADATA).read_text(encoding="utf-8-sig")),
            )
        except (OSError, ValueError):
            return mod.name
        name = row.get("name")
        return name if isinstance(name, str) else mod.name

    def next_step(self, world: World) -> str:
        """What to do in EU5 to play ``world``, from the game's log and playsets.

        A different world starts without a restart only while no game was built since EU5
        was launched, and only after a real reload of the mods (experiment 021); only one
        world may be ticked at a time.
        """
        directory = self._profile_dir()
        mod = library.installed(directory, world) if directory is not None else None
        if directory is None or mod is None:
            return ""
        name = self._mod_title(mod)
        enabled = session.enabled_mods(directory)
        worlds = {item.folder for item in self.worlds} | {stray.name for stray in self.strays}
        if enabled is None:
            tick = text("tick_unknown", name=name)
        else:
            mine = world.folder in enabled
            others = [folder for folder in enabled if folder in worlds and folder != world.folder]
            if mine:
                tick = text("untick_others") if others else ""
            else:
                tick = text("tick_self_untick" if others else "tick_self", name=name)
        state = session.game_state(directory)
        if state is GameState.FRESH:
            return text("next_fresh", tick=tick) if tick else text("next_fresh_switch")
        key = {
            GameState.PLAYED: "next_played",
            GameState.CLOSED: "next_start",
            GameState.UNKNOWN: "next_unknown",
        }[state]
        return " ".join(text(key, tick=tick).split())
