"""What the window knows and does, without drawing anything.

The controller holds the player's choices for a new world (type, seed, the changed
settings), the library of worlds made before, which entry is selected and whether its New
World is shown, and it runs the long work (making a world, adding one to the game, taking
one out, deleting one) on a thread of its own. It tells observers when something changed,
from whichever thread changed it; the window turns that into a signal for its own thread.
Nothing here imports Qt, so it is tested without a display.
"""

from __future__ import annotations

import json
import threading
import traceback
from enum import Enum
from typing import TYPE_CHECKING, Final, Protocol, cast

from rnw import __version__
from rnw.app import controls, discovery, install, library, paths, preferences, service, session
from rnw.app.discovery import GameInstall, Profile
from rnw.app.session import GameState
from rnw.app.worldcode import WorldCode, WorldCodeError, decode, encode, random_seed, reproduces
from rnw.gui.text import text
from rnw.progress import STAGES, Cancelled, Progress, Update
from rnw.settings import PRESETS, WORLD_TYPES, SettingsError, build_settings

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from rnw.app.library import Placement, World

SEED_MAX: Final[int] = (1 << 64) - 1
ERROR_LOG: Final[str] = "last-error.log"
NEW: Final[str] = "new"
STRAY: Final[str] = "stray:"
SEED_DIGITS: Final[int] = 6


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


class Generator(Protocol):
    """``service.generate``, so tests can stand in for it."""

    def __call__(
        self, request: service.Request, progress: Progress | None = None
    ) -> service.Result: ...


def _generate(request: service.Request, progress: Progress | None = None) -> service.Result:
    return service.generate(request, progress)


class Controller:
    """The window's state and the actions the buttons call."""

    def __init__(
        self,
        data: Path | None = None,
        environment: discovery.Environment | None = None,
        generator: Generator = _generate,
        program_folder: Path | None = None,
    ) -> None:
        self.data: Path = paths.data_directory() if data is None else data
        self.environment: discovery.Environment = environment or discovery.Environment()
        self.generator: Generator = generator
        self.program_folder: Path | None = program_folder
        self.games: list[GameInstall] = []
        self.profiles: list[Profile] = []
        self.game: GameInstall | None = None
        self.profile: Profile | None = None
        self.preset: str = "continents"
        self.seed: int = random_seed()
        self.changes: dict[str, int] = {}
        self.other_changes: dict[str, object] = {}
        self.install: bool = True
        self.notice: str = ""
        self.phase: Phase = Phase.IDLE
        self.task: Task | None = None
        self.task_target: str = ""
        self.fraction: float = 0.0
        self.running: tuple[str, ...] = ()
        self.finished: frozenset[str] = frozenset()
        self.message: str = ""
        self.result: service.Result | None = None
        self.worlds: list[World] = []
        self.strays: list[Path] = []
        self.selection: str = NEW
        self.revealed: bool = False
        self.preferences: preferences.Preferences = preferences.load(self.data)
        self._observers: list[Callable[[], None]] = []
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
        self.profiles = discovery.find_profiles(self.environment, self.games)
        self.game = self.games[0] if self.games else None
        self.profile = self.profiles[0] if self.profiles else None
        if self.profile is not None:
            _ = install.sweep(self.profile.directory)
        self.refresh_library()

    def choose_game(self, directory: Path) -> str | None:
        """Take ``directory`` as the installation; returns the problem, or None."""
        if not discovery.is_game(directory):
            return text("not_a_game")
        self.game = GameInstall(directory, None, "")
        self.games = [self.game, *(item for item in self.games if item.directory != directory)]
        self._changed()
        return None

    def choose_profile(self, directory: Path) -> str | None:
        """Take ``directory`` as the profile; returns the problem, or None."""
        if not directory.is_dir():
            return text("not_a_profile")
        self.profile = Profile(directory, "chosen", (directory / "mod").is_dir())
        self.profiles = [self.profile, *(p for p in self.profiles if p.directory != directory)]
        self.refresh_library()
        return None

    # -- the new world's choices ---------------------------------------------------------------

    def set_preset(self, name: str) -> None:
        """Choose a world type; the changed values go back to the type's own."""
        if name in PRESETS and name in WORLD_TYPES and name != self.preset:
            self.preset = name
            self.changes, self.other_changes = {}, {}
            self.notice = ""
            self._changed()

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
        self.notice = ""
        self._changed()
        return None

    def randomize(self) -> None:
        """A new random seed."""
        self.seed = random_seed()
        self.notice = ""
        self._changed()

    def use_code(self, value: str) -> str | None:
        """Take the type, seed and settings of a pasted code; returns the problem, or None."""
        try:
            code = decode(value)
        except WorldCodeError as error:
            return str(error)
        shown, other = controls.flat(code.changes)
        outside = [key for key, number in shown.items() if not controls.BY_KEY[key].allows(number)]
        if code.preset not in WORLD_TYPES or outside:
            names = ", ".join(text(f"control.{key}") for key in outside) or code.preset
            return text("outside_range", names=names)
        self.preset, self.seed = code.preset, code.seed
        self.changes = {
            key: number
            for key, number in shown.items()
            if number != controls.BY_KEY[key].default(code.preset)
        }
        self.other_changes = other
        notices: list[str] = []
        if not reproduces(code):
            notices.append(text("other_version", made=code.generator, current=__version__))
        if other:
            notices.append(text("other_changes"))
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
        self.worlds = library.load(self.data)
        self.strays = library.strays(self._profile_dir(), self.worlds)
        known = self.selected_world() is not None or self.selected_stray() is not None
        if self.selection != NEW and not known:
            self.selection = NEW
        self._changed()

    def select(self, selection: str) -> None:
        """Show the new-world page (``NEW``), a world (its id) or a stray (``STRAY`` + folder)."""
        if selection != self.selection:
            self.selection = selection
            self.revealed = False
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

    def set_revealed(self, revealed: bool) -> None:  # noqa: FBT001 - the window's toggle
        """Show or hide the selected world's New World."""
        if revealed != self.revealed:
            self.revealed = revealed
            self._changed()

    def picture(self, world: World) -> Path | None:
        """The selected world's picture: covered unless the player asked to see it."""
        return library.picture(self.data, world, revealed=self.revealed)

    def covered_picture(self, world: World) -> Path | None:
        """A world's covered picture, for the list."""
        return library.picture(self.data, world, revealed=False)

    def placement(self, world: World) -> Placement:
        """Where the world's mod is."""
        return library.placement(self.data, self._profile_dir(), world)

    def name(self, world: World) -> str:
        """The player's name for the world, or one made of its type and seed."""
        if world.name:
            return world.name
        seed = str(world.seed)[:SEED_DIGITS]
        return text("default_name", type=text(f"type.{world.preset}"), seed=seed)

    def rename(self, world: World, name: str) -> None:
        """Give the world a name of the player's (blank: the default)."""
        if name.strip() != world.name:
            _ = library.rename(self.data, world, name)
            self.refresh_library()

    def changed_count(self, world: World) -> int:
        """How many settings the world's code changes."""
        try:
            shown, other = controls.flat(decode(world.code).changes)
        except WorldCodeError:
            return 0
        extra = sum(
            len(cast("dict[str, object]", fields)) if isinstance(fields, dict) else 1
            for fields in other.values()
        )
        return len(shown) + extra

    def like(self, world: World) -> None:
        """A new world with the type and settings of ``world`` and a fresh seed."""
        try:
            code = decode(world.code)
        except WorldCodeError:
            return
        shown, other = controls.flat(code.changes)
        self.preset = code.preset
        self.changes = {k: v for k, v in shown.items() if controls.BY_KEY[k].allows(v)}
        self.other_changes = other
        self.seed = random_seed()
        self.notice = ""
        self.selection = NEW
        self.revealed = False
        self._changed()

    def set_reveal_thumbnails(self, reveal: bool) -> None:  # noqa: FBT001 - the dialog's box
        """Remember the choice and redraw the mod-list pictures of every world with a mod."""
        self.preferences = preferences.Preferences(reveal_thumbnails=reveal)
        preferences.save(self.data, self.preferences)
        for world in self.worlds:
            mod = library.installed(self._profile_dir(), world) or library.kept(self.data, world)
            if mod is not None:
                _ = library.write_thumbnail(self.data, world, mod, revealed=reveal)
        self._changed()

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
        try:
            estimate = self.estimated_locations()
        except SettingsError as error:
            return str(error)
        if estimate > controls.LOCATION_BUDGET:
            return text("too_many_locations", count=estimate, budget=controls.LOCATION_BUDGET)
        return None

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
                if info.label in self.running
                else "waiting"
            )
            rows.append((info.label, state))
        return rows

    # -- the work ------------------------------------------------------------------------------

    def start(self) -> str | None:
        """Start making the new world; returns why it cannot, or None."""
        reason = self.problem()
        if reason is not None or self.game is None:
            return reason
        request = service.Request(
            game=self.game,
            code=self.world_code(),
            data=self.data,
            profile=self.profile,
            install=self.install,
            reveal_thumbnail=self.preferences.reveal_thumbnails,
        )
        generator = self.generator

        def work(progress: Progress) -> service.Result:
            return generator(request, progress)

        return self._run(Task.GENERATE, NEW, work)

    def add_selected(self) -> str | None:
        """Put the selected world into the game; returns why it cannot, or None."""
        world = self.selected_world()
        reason = self.world_problem()
        if reason is not None or world is None or self.game is None or self.profile is None:
            return reason
        game, profile, data = self.game, self.profile, self.data
        reveal = self.preferences.reveal_thumbnails
        generator = self.generator

        def work(progress: Progress) -> service.Result:
            if library.kept(data, world) is not None and world.game_build == game.build_id:
                return service.add_to_game(
                    world, game=game, data=data, profile=profile, progress=progress
                )
            request = service.Request(
                game=game,
                code=decode(world.code),
                data=data,
                profile=profile,
                reveal_thumbnail=reveal,
            )
            result = generator(request, progress)
            if world.name and result.world.id == world.id:
                _ = library.rename(data, result.world, world.name)
            return result

        return self._run(Task.ADD, world.id, work)

    def remove_selected(self) -> str | None:
        """Take the selected world, or stray, out of the game; returns why not, or None."""
        world, stray = self.selected_world(), self.selected_stray()
        reason = self.world_problem()
        profile = self.profile
        if reason is not None or profile is None:
            return reason
        if world is not None:
            folder = world.folder
        elif stray is not None:
            folder = stray.name
        else:
            return None

        def work(_progress: Progress) -> None:
            service.remove_from_game(folder, profile)

        return self._run(Task.REMOVE, self.selection, work)

    def delete_selected(self) -> str | None:
        """Take the selected world out of the game and forget it; returns why not, or None."""
        world = self.selected_world()
        reason = self.world_problem()
        if reason is not None or world is None:
            return reason
        data, profile = self.data, self.profile

        def work(_progress: Progress) -> None:
            service.delete(world, data, profile)

        return self._run(Task.DELETE, world.id, work)

    def _run(
        self, task: Task, target: str, work: Callable[[Progress], service.Result | None]
    ) -> str | None:
        progress = Progress(self._on_update)
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
        self._changed()

    def _work(self, work: Callable[[Progress], service.Result | None], progress: Progress) -> None:
        outcome = Phase.FINISHED
        message = ""
        result: service.Result | None = None
        try:
            result = work(progress)
        except Cancelled:
            outcome = Phase.CANCELLED
        except Exception as error:  # noqa: BLE001 - whatever failed is shown to the player
            outcome, message = Phase.FAILED, self._explain(error)
        with self._lock:
            self.phase, self.result, self.message = outcome, result, message
            self.running = ()
            if outcome is Phase.FINISHED:
                self.fraction = 1.0
            if result is not None:
                self.selection, self.revealed = result.world.id, False
        self.refresh_library()

    def _explain(self, error: Exception) -> str:
        """The error for the player; the traceback goes to a file for a bug report."""
        try:
            self.data.mkdir(parents=True, exist_ok=True)
            _ = (self.data / ERROR_LOG).write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        return str(error) or type(error).__name__

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
