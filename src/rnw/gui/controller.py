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
import time
import traceback
from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol, cast

from rnw import __version__, atlas, epoch, history_presenter, landmask, worldfile, worldname
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
    playset,
    preferences,
    quick,
    random_types,
    recovery,
    service,
    session,
    surroundings,
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
from rnw.eu5_map import DEFINITIONS
from rnw.geography import read_locations
from rnw.gui import mapstyle, phases
from rnw.gui.text import (
    ERROR,
    JOINING,
    PHASE,
    choose_language,
    explain,
    grouped,
    language,
    stage_text,
    system_language,
    text,
)
from rnw.landarea import EDITOR_STEP
from rnw.layers import PARTS, rolls_of
from rnw.messages import Said, say
from rnw.png import COLOR_RGB, encode_png
from rnw.pngread import read_rgb
from rnw.progress import Cancelled, Progress, Update, active
from rnw.record import Verdict, verdict
from rnw.settings import (
    AMERICA,
    PRESETS,
    REGIONAL_PRESETS,
    WORLD_TYPES,
    MamlukPolicy,
    MoroccoPolicy,
    SettingsError,
    build_settings,
    drawn_ids,
)
from rnw.wording import render

if TYPE_CHECKING:
    from collections.abc import Callable, Collection

    from rnw.app.library import World
    from rnw.atlas import Atlas
    from rnw.landarea import AreaInputs, LandArea
    from rnw.landmask import LandMask
    from rnw.settings import RegionalSettings, Settings

SEED_MAX: Final[int] = (1 << 64) - 1
ERROR_LOG: Final[str] = "last-error.log"
NEW: Final[str] = "new"
# The target of the task that cuts the editor's area (the template's target is its file).
EDITOR: Final[str] = "editor"
STRAY: Final[str] = "stray:"
# Atlases whose map words are kept (the window asks at every refresh).
WORDS_KEPT: Final[int] = 4
# How long the check of the playset is kept; it reads other mods' folders.
PLAYSET_SECONDS: Final[float] = 5.0
# What the record alone says (ADR 0010, G): the algorithm; anything else is "not checked yet".
REPRODUCTION: Final[dict[Verdict, str]] = {
    Verdict.OTHER_ALGORITHM: "repro.other_algorithm",
    Verdict.NEWER_FORMAT: "repro.newer_format",
}


# A continent's settings in its ``new_world`` that the World tab holds, not the Advanced tab.
REGION_KEPT: Final[frozenset[str]] = frozenset({"reveal_at_start"})


@dataclass(frozen=True, slots=True)
class PhaseRow:
    """A phase of the world being made as both windows list it: its name and state
    (``rnw.gui.phases.Row``), the names of its stages that run now and how many of its stages
    this world runs and has done."""

    label: str
    state: str
    steps: tuple[str, ...]
    done: int
    total: int


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


# The work that makes a world, whose failures are told in the generator's own words.
MAKING: Final[frozenset[Task]] = frozenset({Task.GENERATE, Task.QUEUE, Task.REROLL})


class _QueueFailed(Exception):  # noqa: N818 - the end of a run in which no world could be made
    """Every world of a queue run failed. Each was explained and logged when it failed; this
    carries the words the run ends with."""


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
        algorithms: Collection[int] | None = None,
    ) -> service.Check: ...


def _generate(request: service.Request, progress: Progress | None = None) -> service.Result:
    return service.generate(request, progress)


def _check(
    world: World,
    *,
    game: GameInstall,
    data: Path,
    progress: Progress | None = None,
    algorithms: Collection[int] | None = None,
) -> service.Check:
    return service.check(world, game=game, data=data, progress=progress, algorithms=algorithms)


class Controller:
    """The window's state and the actions the buttons call."""

    # The queued world the thread is making now.
    _queue_current: service.Request | None = None
    # Set by a world added while the thread is making another: the queue goes on by itself when
    # that one is finished. A failure, a cancellation or an empty queue clears it.
    queue_follows: bool = False
    # The code the new-world page held when the thread started, so that a finished world does not
    # take the player away from the next one they are preparing.
    _launched_with: str = ""

    def __init__(  # noqa: PLR0915 - one attribute for each piece of window state.
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
        self.origin: str = ""
        self.seed: int = random_seed()
        # The algorithm epoch the new world is made by (``rnw.epoch``); only the experimental
        # features move it off the current one, and unticking them puts it back.
        self.algorithm: int = epoch.CURRENT
        self._generation_seed: int | None = None
        self.changes: dict[str, int] = {}
        self.other_changes: dict[str, object] = {}
        self._regional_drafts: dict[str, object] = {}
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
        # The world the thread makes now (its settings and whether it goes into the profile), for
        # the phases its progress lists.
        self._making: tuple[Settings, bool] | None = None
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
        self._comparing: set[tuple[str, str]] = set()
        self._playset: dict[tuple[str, str], tuple[float, playset.Check | None]] = {}
        self.runs: int = 0
        self.land_mask: LandMask | None = None
        # The images the other continents' lands are drawn from, by the continent's key.
        self.regional_masks: dict[str, LandMask] = {}
        # The area each continent can fill at the land editor's step, and what it was cut for.
        self._sheets: dict[str, tuple[AreaInputs, LandArea]] = {}
        self.last_import: exchange.Imported | None = None
        self._history_readers: dict[int, history_presenter.Reader] = {}
        # The installed game's continent of each region, by the game's folder and build.
        self._regions: tuple[tuple[Path, str], dict[str, str]] | None = None
        self._words: dict[int, tuple[Atlas, tuple[str, Path | None], atlas.Words]] = {}
        self.candidates: list[candidates.Candidate] = []
        self.candidate_code: WorldCode | None = None
        # The worlds waiting for the thread, the first of them the one it is making now during a
        # queue run. Both the window's thread and the worker change it, always under the lock.
        self.queue: list[service.Request] = []
        self.queue_done: int = 0
        # Why a queued world could not be made, by its code. A failed world stays in ``queue``
        # beside this note; a run skips it, and *Run queue* tries it again.
        self.queue_errors: dict[str, str] = {}
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

    def continent_selection(self) -> dict[str, bool]:
        """The switches for the current composition, including an empty draft."""
        raw = self._continent_document()
        return {
            "america": raw.get("america", True) is True,
            **{key: raw.get(key, False) is not False for key in REGIONAL_PRESETS},
        }

    def _continent_document(self) -> dict[str, object]:
        raw = self.other_changes.get("continents")
        return dict(cast("dict[str, object]", raw)) if isinstance(raw, dict) else {}

    def sea_circumnavigation(self) -> bool | None:
        """The regional option is available when the world has no Wall."""
        selection = self.continent_selection()
        if not any(selection[key] for key in REGIONAL_PRESETS) or (
            selection["america"] and self.preset == "wall"
        ):
            return None
        return self._continent_document().get("sea_circumnavigation", True) is True

    def set_sea_circumnavigation(self, *, enabled: bool) -> None:
        if self.sea_circumnavigation() in (None, enabled):
            return
        raw = self._continent_document()
        if enabled:
            _ = raw.pop("sea_circumnavigation", None)
        else:
            raw["sea_circumnavigation"] = False
        self.other_changes["continents"] = raw
        self._changed()

    def set_continent(self, key: str, *, enabled: bool) -> None:
        """Change one continent's switch without resetting the others' settings."""
        if key not in {"america", *REGIONAL_PRESETS}:
            return
        current = self.continent_selection()
        if current[key] == enabled:
            return
        raw = self._continent_document()
        if key == "america" and not enabled:
            raw[key] = False
        elif key == "america":
            _ = raw.pop(key, None)
        elif enabled:
            raw[key] = self._regional_drafts.pop(key, True)
        else:
            self._regional_drafts[key] = raw.pop(key)
        if raw:
            self.other_changes["continents"] = raw
        else:
            _ = self.other_changes.pop("continents", None)
        self._changed()

    def region_settings(self, key: str, *, defaults: bool = False) -> RegionalSettings:
        """Resolved controls of a regional preset, with defaults even when switched off."""
        raw = self._continent_document().get(key, True)
        if defaults and isinstance(raw, dict):
            raw = {"preset": cast("dict[str, object]", raw).get("preset", REGIONAL_PRESETS[key][0])}
        return build_settings(
            self.preset, {"continents": {key: raw if raw is not False else True}}
        ).continents.regions[0]

    def _edit_region(self, key: str, changes: dict[str, object]) -> None:
        raw = self._continent_document()
        configured = raw.get(key, False)
        if configured is False:
            return
        region = dict(cast("dict[str, object]", configured)) if isinstance(configured, dict) else {}
        region.update(changes)
        _ = build_settings(self.preset, {"continents": {key: region}})
        raw[key] = region
        self.other_changes["continents"] = raw
        self._changed()

    def set_region_preset(self, key: str, preset: str) -> None:
        """Choose a continent's type; its exact values go back to the type's own, and its reveal,
        a choice of the World tab, stays."""
        if key in REGIONAL_PRESETS and preset in controls.REGION_TYPES:
            self._edit_region(
                key,
                {
                    "preset": preset,
                    "new_world": self._region_kept(key),
                    "natives": {},
                    "resources": {},
                },
            )

    def _region_kept(self, key: str) -> dict[str, object]:
        """The continent's own settings that its type and the Advanced tab leave alone."""
        return {"reveal_at_start": 1} if self.region_settings(key).new_world.reveal_at_start else {}

    def _region_customised(self, key: str) -> bool:
        configured = self._continent_document().get(key)
        if not isinstance(configured, dict):
            return False
        region = cast("dict[str, object]", configured)
        world = region.get("new_world")
        own: set[str] = set(cast("dict[str, object]", world)) if isinstance(world, dict) else set()
        return bool(region.get("natives") or region.get("resources") or own - REGION_KEPT)

    def changed_values(self) -> dict[str, int]:
        """How many exact values (those of the Advanced tab) differ from the type's, for each
        continent switched on."""
        selection = self.continent_selection()
        found: dict[str, int] = {}
        if selection["america"]:
            found["america"] = sum(
                1 for key in self.changes if controls.BY_KEY[key].field not in controls.PAGE_OPTIONS
            )
        for key in REGIONAL_PRESETS:
            if not selection[key]:
                continue
            settings, defaults = self.region_settings(key), self.region_settings(key, defaults=True)
            found[key] = sum(
                1
                for control in controls.regional_controls(key)
                if control.field not in controls.PAGE_OPTIONS
                and controls.region_value(control, settings)
                != controls.region_value(control, defaults)
            )
        return found

    def set_morocco(self, policy: str) -> None:
        if policy in {mode.value for mode in MoroccoPolicy}:
            self._edit_region("africa", {"morocco": policy})

    def set_mamluks(self, policy: str) -> None:
        if policy in {mode.value for mode in MamlukPolicy}:
            self._edit_region("africa", {"mamluks": policy})

    def set_asia_connection(self, *, required: bool) -> None:
        self._edit_region("africa", {"require_asia_connection": required})

    def set_region_value(self, region: str, key: str, number: int | None) -> None:
        control = controls.REGION_BY_KEY.get(key)
        if (
            region not in REGIONAL_PRESETS
            or control is None
            or control not in controls.regional_controls(region)
        ):
            return
        raw = self._continent_document().get(region)
        previous = (
            cast("dict[str, object]", raw).get(control.section) if isinstance(raw, dict) else None
        )
        section = dict(cast("dict[str, object]", previous)) if isinstance(previous, dict) else {}
        if number is None:
            _ = section.pop(control.field, None)
        else:
            section[control.field] = min(control.high, max(control.low, number))
        self._edit_region(region, {control.section: section})

    def set_preset(self, name: str) -> None:
        """Choose a world type; the changed values go back to the type's own."""
        if name in PRESETS and name in WORLD_TYPES and (name != self.preset or self.mode):
            self.mode = None
            self.origin = ""
            self.preset = name
            continents = self._continent_document()
            self.changes, self.other_changes = {}, {"continents": continents} if continents else {}
            self._forget_drawings()
            self.notice = ""
            self._changed()

    def set_mode(self, mode: str) -> None:
        """Choose Random or Total Chaos: a world type is drawn now and with each new seed."""
        if mode in random_types.MODES:
            self.mode = mode
            self.other_changes, self.notice = self._keep_continents(), ""
            self._forget_drawings()
            self._draw()
            self._changed()

    def _draw(self) -> None:
        """Draw the world type, and for Total Chaos the Advanced values, of the random mode."""
        if self.mode is not None:
            self.preset, self.changes = random_types.draw(self.mode)
            self.origin = "chaos" if self.mode == random_types.CHAOS else ""

    def randomize_settings(self) -> None:
        """Draw Total Chaos again, keeping the seed; a manual edit no longer names this draw."""
        if self.mode != random_types.CHAOS or (self.busy and not self.can_prepare):
            return
        self.other_changes, self.notice = self._keep_continents(), ""
        self._forget_drawings()
        self._draw()
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
        self._use_origin(code)
        self.changes = {
            key: number
            for key, number in shown.items()
            if number != controls.BY_KEY[key].default(code.preset)
        }
        self.other_changes = other
        self._regional_drafts.clear()
        notices: list[str] = []
        self.algorithm = epoch.CURRENT
        if reproduces(code):
            pass
        elif reproduces(code, self.algorithms()):
            # An older epoch this generator still makes (the experimental features): the page
            # makes the world by it, as the release in the code did.
            self.algorithm = epoch.epoch_of(code.generator)
            notices.append(text("epoch.followed", release=code.generator, epoch=self.algorithm))
        else:
            notices.append(text("other_version", made=code.generator, current=__version__))
        if set(other) - {"rolls", "mask", "continents"}:
            notices.append(text("other_changes"))
        if not self._keep_drawings_of(code.settings()):
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
        if number != self.value(key):
            self._custom_origin()
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
            if number != self.value(key):
                self._custom_origin()
            if number == controls.BY_KEY[key].default(self.preset):
                _ = self.changes.pop(key, None)
            else:
                self.changes[key] = number
        self._changed()

    def reset_value(self, key: str) -> None:
        """Give one setting back the world type's value."""
        if self.changes.pop(key, None) is not None:
            self._custom_origin()
            self._changed()

    def reset_values(self) -> None:
        """Give every exact value of every continent back to its type's (and drop the drawn
        land). The World tab's choices stay: the continents, their types and policies, the
        oceans, the real Americas and each continent's reveal."""
        kept = {
            key: number
            for key, number in self.changes.items()
            if controls.BY_KEY[key].field in controls.PAGE_OPTIONS
        }
        customised = [key for key in REGIONAL_PRESETS if self._region_customised(key)]
        if self.changes != kept or self.other_changes.keys() - {"continents"} or customised:
            self.origin = "chaos_custom" if self.mode == random_types.CHAOS else ""
            self.changes, self.other_changes = kept, self._keep_continents()
            self._forget_drawings()
            for key in customised:
                self._edit_region(
                    key, {"new_world": self._region_kept(key), "natives": {}, "resources": {}}
                )
            self._changed()

    def _keep_continents(self) -> dict[str, object]:
        selected = self._continent_document()
        return {"continents": selected} if selected else {}

    def _change_document(self) -> dict[str, object] | None:
        document = controls.nested(self.changes) or {}
        for section, fields in self.other_changes.items():
            merged = cast("dict[str, object]", document.setdefault(section, {}))
            if isinstance(fields, dict):
                merged.update(cast("dict[str, object]", fields))
        if not self.continent_selection()["america"]:
            _ = document.pop("mask", None)
        return document or None

    def world_code(self) -> WorldCode:
        """The code of the new world as chosen now."""
        return WorldCode(
            self.preset,
            self.seed,
            epoch.stamp_of(self.algorithm),
            self._change_document(),
            self.origin,
        )

    def algorithms(self) -> tuple[int, ...]:
        """The epochs this generator makes a world by now: the current one, and with the
        experimental features the older ones it keeps (ADR 0013)."""
        return epoch.available(experimental=self.preferences.experimental)

    def epoch_choices(self) -> list[tuple[int, str]]:
        """The epochs the new world can be made by, newest first, each with its label; none unless
        the experimental features are on."""
        if not self.preferences.experimental:
            return []
        return [
            (
                number,
                text(
                    "epoch.choice.current" if number == epoch.CURRENT else "epoch.choice",
                    epoch=number,
                    release=epoch.stamp_of(number),
                ),
            )
            for number in reversed(self.algorithms())
        ]

    def set_experimental(self, on: bool) -> None:  # noqa: FBT001 - the settings' box
        """Tick or untick the experimental features; unticking makes new worlds of the current
        epoch again."""
        self.preferences = replace(self.preferences, experimental=on)
        preferences.save(self.data, self.preferences)
        if not on:
            self.algorithm = epoch.CURRENT
        self._changed()

    def set_algorithm(self, number: int) -> str | None:
        """Choose the epoch the new world is made by; returns why not, or None."""
        if number not in self.algorithms():
            first, last = epoch.OLDEST_SELECTABLE, epoch.CURRENT
            return text("epoch.unavailable", epoch=number, first=first, last=last)
        if number != self.algorithm:
            self.algorithm = number
            self._changed()
        return None

    def _in_epoch(self, code: WorldCode, number: int | None = None) -> WorldCode:
        """``code`` stamped as the release that made epoch ``number`` (by default the chosen one)
        would stamp it: a code names the release that made its world."""
        return replace(code, generator=epoch.stamp_of(self.algorithm if number is None else number))

    def world_epoch(self, world: World) -> int | None:
        """The epoch that made ``world``: its record says, else its code's stamp; None when the
        code cannot be read or predates the epochs."""
        if world.record is not None:
            return world.record.algorithm
        try:
            made = epoch.epoch_of(decode(world.code).generator)
        except (WorldCodeError, epoch.ReleaseError):
            return None
        return made or None

    def _custom_origin(self) -> None:
        self.origin = "chaos_custom" if self.mode == random_types.CHAOS else "custom"

    def _use_origin(self, code: WorldCode) -> None:
        self.origin = code.origin
        if code.origin in {"chaos", "chaos_custom"}:
            self.mode = random_types.CHAOS

    @property
    def code(self) -> str:
        """The world code of the current choices."""
        return encode(self.world_code()) if any(self.continent_selection().values()) else ""

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
        return library.display_name(world)

    def rename(self, world: World, name: str) -> str | None:
        """Give the world a name of the player's (blank or the default: none); returns what
        could not be done, or None.

        The name goes into the metadata of the world's mod, in the game or kept, so the game's
        list shows it; while the game holds the file that has to wait until the world is added
        again.
        """
        cleaned = worldname.clean_name(name)
        if cleaned == library.display_name(world, name=""):
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
        self._use_origin(code)
        self.changes = {k: v for k, v in shown.items() if controls.BY_KEY[k].allows(v)}
        self.other_changes = other
        _ = self.other_changes.pop("rolls", None)
        self.land_mask = library.land_mask(self.data, world)
        self.regional_masks = library.regional_masks(self.data, world)
        self.seed = random_seed()
        self.notice = ""
        self.selection = NEW
        self._changed()

    def version_problem(self, world: World) -> str | None:
        """Why no version of ``world`` can be made here, or None.

        A version keeps the world's land, which this generator makes only for a world of its own
        algorithm epoch. The world's record says which epoch made its files, and the record
        decides: the release stamped in a code is only what the code was copied from (a world
        made here from an old code has the old stamp). Without a record the code's stamp has to
        do (``reproduces``). A world of another epoch is refused in words, and a code
        that cannot be read with its own message.
        """
        try:
            code = decode(world.code)
            record = world.record
            wanted = self.algorithms()
            if record is None:
                if not reproduces(code, wanted):
                    message = say("version.other_algorithm", release=code.generator)
                    raise WorldCodeError(message)  # noqa: TRY301 - one place makes the words
            elif verdict(record, algorithms=wanted) is not Verdict.SAME_ALGORITHM:
                message = say("version.other_algorithm", release=record.release)
                raise WorldCodeError(message)  # noqa: TRY301 - one place makes the refusal's words
        except WorldCodeError as error:
            return explain(error)
        return None

    def resources_problem(self, world: World) -> str | None:
        """The resources can be rolled when the world has any generated geography."""
        try:
            settings = decode(world.code).settings()
        except (WorldCodeError, SettingsError):
            return None
        if settings.new_world.keep_geography and not settings.continents.regions:
            return text("part.resources.real")
        return None

    def edit_selected(self) -> str | None:
        """Load the selected world's type, seed and settings into the new-world page, to change
        the settings of its peoples or resources on the same land (a version of it); returns why
        not, or None."""
        world = self.selected_world()
        if world is None:
            return None
        problem = self.version_problem(world)
        if problem is not None:
            return problem
        code = decode(world.code)
        shown, other = controls.flat(code.resolved_changes())
        self.mode, self.preset, self.seed = None, code.preset, code.seed
        # A version is made by the epoch that made the world, which ``version_problem`` allowed.
        self.algorithm = self.world_epoch(world) or epoch.CURRENT
        self._use_origin(code)
        self.changes = {k: v for k, v in shown.items() if controls.BY_KEY[k].allows(v)}
        self.other_changes = other
        self._regional_drafts.clear()
        self.land_mask = library.land_mask(self.data, world)
        self.regional_masks = library.regional_masks(self.data, world)
        self.notice = ""
        self.selection = NEW
        self._changed()
        return None

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
        problem = self.version_problem(world)
        if problem is not None:
            return problem
        made = self.world_epoch(world) or epoch.CURRENT
        try:
            code = self._in_epoch(rolled(decode(world.code), part), made)
            drawn = service.required_land_mask(self.data, world)
            regional = service.required_regional_masks(self.data, world)
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
            regional_masks=regional,
            algorithm=made,
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

    @property
    def can_prepare(self) -> bool:
        """Whether the next world can be chosen and queued now: unless the thread is at other
        work, also while it makes a world, which has its own copy of the choices."""
        return not self.busy or self.task in {Task.GENERATE, Task.QUEUE}

    def problem(self) -> str | None:
        """Why Generate cannot start now, or None when it can."""
        if self.busy:
            return text("ready_busy")
        return self.setup_problem()

    def setup_problem(self, code: WorldCode | None = None) -> str | None:
        """Why the world of ``code`` (the one chosen now) could not be made, whatever the
        thread is doing: the game, the profile, the locations or a missing land image."""
        if self.game is None:
            return text("ready_no_game")
        if self.install and self.profile is None:
            return text("ready_no_profile")
        return self._choices_problem(code)

    def _choices_problem(self, code: WorldCode | None = None) -> str | None:
        """What is wrong with the choices: too many locations, or a land image that is missing."""
        if code is None and not any(self.continent_selection().values()):
            return text("continent.choose")
        code = code or self.world_code()
        try:
            estimate = controls.estimated_locations(code.settings())
        except SettingsError as error:
            return explain(error)
        if estimate > controls.LOCATION_BUDGET:
            return text(
                "too_many_locations",
                count=grouped(estimate),
                budget=grouped(controls.LOCATION_BUDGET),
            )
        if self._missing_drawing(code.settings()):
            return text("needs_land_image")
        return None

    def choose_land_image(self, path: Path, continent: str = AMERICA) -> str | None:
        """Make the land of ``continent`` (America's by default) the picture at ``path`` (white is
        land, black is sea); returns what is wrong with the picture, or None."""
        try:
            return self._use_land(landmask.read(path), continent)
        except landmask.LandMaskError as error:
            return explain(error)

    def use_land_picture(self, data: bytes, continent: str = AMERICA) -> str | None:
        """Make the land of ``continent`` (America's by default) the picture the editor drew (the
        bytes of a PNG); returns what is wrong with it, or None."""
        try:
            return self._use_land(landmask.from_bytes(data), continent)
        except landmask.LandMaskError as error:
            return explain(error)

    def _use_land(self, mask: LandMask, continent: str = AMERICA) -> None:
        if continent == AMERICA:
            self.land_mask = mask
            self.other_changes["mask"] = {"id": mask.id}
        else:
            if not self.continent_selection().get(continent):
                return
            self.regional_masks[continent] = mask
            self._edit_region(continent, {"mask": {"id": mask.id}})
        self._custom_origin()
        self.notice = ""
        self._changed()

    def drawings(self) -> dict[str, LandMask]:
        """The images the continents' lands are drawn from, by the continent's key."""
        found = dict(self.regional_masks)
        if self.land_mask is not None:
            found[AMERICA] = self.land_mask
        return found

    def _missing_drawing(self, settings: Settings, *, sketch: bool = False) -> bool:
        """Whether a continent of ``settings`` is drawn from an image the window does not hold;
        a sketch ignores America's when America is switched off."""
        held = self.drawings()
        return any(
            key not in held or held[key].id != wanted
            for key, wanted in drawn_ids(settings).items()
            if not (sketch and key == AMERICA and not settings.continents.america)
        )

    def _keep_drawings_of(self, settings: Settings) -> bool:
        """Keep only the images ``settings`` name; whether it names no other."""
        wanted = drawn_ids(settings)
        kept = {key: mask for key, mask in self.drawings().items() if wanted.get(key) == mask.id}
        self.land_mask = kept.pop(AMERICA, None)
        self.regional_masks = kept
        return all(key in self.drawings() for key in wanted)

    def _forget_drawings(self) -> None:
        """Go back to land the generator draws, for every continent."""
        self.land_mask, self.regional_masks = None, {}
        raw = self._continent_document()
        for key in REGIONAL_PRESETS:
            region = raw.get(key)
            if isinstance(region, dict) and "mask" in region:
                raw[key] = {
                    k: v for k, v in cast("dict[str, object]", region).items() if k != "mask"
                }
        if raw:
            self.other_changes["continents"] = raw
        for key, draft in list(self._regional_drafts.items()):
            if isinstance(draft, dict):
                self._regional_drafts[key] = {
                    k: v for k, v in cast("dict[str, object]", draft).items() if k != "mask"
                }

    def drawable_continents(self) -> list[str]:
        """The continents the world generates, whose land can be drawn: America unless it keeps
        the game's own, and the others when switched on."""
        selected = self.continent_selection()
        keeps = bool(self.value("new_world.keep_geography"))
        return [
            key
            for key in (AMERICA, *REGIONAL_PRESETS)
            if selected[key] and not (key == AMERICA and keeps)
        ]

    def land_sheet(self, continent: str = AMERICA) -> LandArea | None:
        """The area the editor draws ``continent`` on, when it was cut for the choices made now;
        else None."""
        held = self._sheets.get(continent)
        if self.game is None or held is None or continent not in self.drawable_continents():
            return None
        return held[1] if held[0] == self._area_inputs(continent) else None

    def _area_inputs(self, continent: str) -> AreaInputs:
        assert self.game is not None  # noqa: S101 - the callers have checked the game
        return service.area_inputs(self.game, self._area_settings(), continent, self.seed)

    def _area_settings(self) -> Settings:
        return build_settings(self.preset, self._change_document())

    def prepare_land_area(self, continent: str = AMERICA) -> str | None:
        """Cut the area the editor draws ``continent`` on from the installed game's map, as a task
        (a second or two from the land cache, else several); returns why not, or None. When the
        area is ready already nothing is started."""
        if self.busy:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        if continent not in self.drawable_continents():
            return text("editor.not_drawn", continent=text(f"continent.{continent}"))
        game, settings, seed = self.game, self._area_settings(), self.seed
        if self.land_sheet(continent) is not None:
            return None
        inputs = self._area_inputs(continent)

        def work(_progress: Progress) -> None:
            area = service.land_area(
                game, settings, data=self.data, continent=continent, seed=seed
            ).at(EDITOR_STEP)
            with self._lock:
                self._sheets[continent] = inputs, area

        return self._run(Task.TEMPLATE, EDITOR, work)

    def save_land_template(self, output: Path, continent: str = AMERICA) -> str | None:
        """Write the picture of the area ``continent`` can fill, to draw land on, as a task;
        returns why not, or None."""
        if self.busy:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        game, seed = self.game, self.seed

        def work(_progress: Progress) -> None:
            _ = service.land_template(
                game,
                output,
                build_settings(self.preset, self._change_document()),
                data=self.data,
                continent=continent,
                seed=seed,
            )

        return self._run(Task.TEMPLATE, str(output), work)

    def clear_land_image(self, continent: str = AMERICA) -> None:
        """Go back to land the generator draws, for ``continent`` (America by default)."""
        if continent == AMERICA:
            if self.land_mask is not None or "mask" in self.other_changes:
                self._custom_origin()
            self.land_mask = None
            _ = self.other_changes.pop("mask", None)
        else:
            if continent in self.regional_masks:
                self._custom_origin()
            _ = self.regional_masks.pop(continent, None)
            self._drop_region_mask(continent)
        self._changed()

    def _drop_region_mask(self, continent: str) -> None:
        raw = self._continent_document()
        region = raw.get(continent)
        if isinstance(region, dict) and "mask" in region:
            raw[continent] = {
                k: v for k, v in cast("dict[str, object]", region).items() if k != "mask"
            }
            self.other_changes["continents"] = raw

    def world_problem(self) -> str | None:
        """Why the world actions cannot run now, or None when they can."""
        if self.busy:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        if self.profile is None:
            return text("ready_no_profile")
        return None

    def phase_rows(self) -> list[PhaseRow]:
        """The phases of the world being made, in order, with their state and what runs now; the
        stages it does not run are left out (``rnw.gui.phases``)."""
        with self._lock:
            making, running, finished = self._making, self.running, self.finished
        if making is None:
            return []
        settings, install = making
        kind = phases.kind_of(settings)
        return [
            PhaseRow(
                text(PHASE + row.phase),
                row.state,
                tuple(self.step_text(name, kind) for name in row.steps),
                row.done,
                row.total,
            )
            for row in phases.rows(settings, install=install, running=running, finished=finished)
        ]

    def making_text(self) -> str:
        """The continents of the world being made, for the title of its progress."""
        making = self._making
        if making is None:
            return ""
        continents = making[0].continents
        names = (
            [
                text(
                    "continent.america_real"
                    if making[0].new_world.keep_geography
                    else "continent.america"
                )
            ]
            if continents.america
            else []
        )
        names.extend(text(f"continent.{region.key}") for region in continents.regions)
        return ", ".join(names)

    def step_text(self, name: str, kind: phases.Kind | None = None) -> str:
        """What the window calls the stage ``name`` of the world being made."""
        if kind is None and self.task in {Task.GENERATE, Task.QUEUE}:
            making = self._making
            kind = None if making is None else phases.kind_of(making[0])
        if name == "select canvas" and kind is phases.Kind.COMPOSED:
            return text(JOINING)
        return stage_text(name)

    def running_text(self) -> str:
        """The stages that run now, in the window's language."""
        return ", ".join(self.step_text(name) for name in self.running)

    def finished_line(self) -> str:
        """The status line of finished work; after a queue run it counts the worlds that stay in
        the queue because they could not be made."""
        seconds = round(self.result.seconds) if self.result else 0
        failed = self.queue_failed if self.task is Task.QUEUE else 0
        if failed:
            return text("finished_queue_failed", seconds=seconds, count=failed)
        return text("finished", seconds=seconds)

    def estimated_remaining(self) -> float | None:
        """Estimated seconds left in the active weighted generation."""
        with self._lock:
            if (
                self.phase is not Phase.RUNNING
                or self.task not in {Task.GENERATE, Task.QUEUE}
                or "waiting for the game" in self.running
            ):
                return None
            progress = self._progress
        return progress.estimated_remaining() if progress is not None else None

    # -- the work ------------------------------------------------------------------------------

    def sketch_problem(self) -> str | None:
        """Why the continents switched on cannot be sketched now (other work aside); None when
        they can. A world of several continents is sketched whole, a drawn America on it."""
        if self.game is None:
            return text("ready_no_game")
        if not any(self.continent_selection().values()):
            return text("continent.choose")
        settings = self.world_code().settings()
        if settings.continents.regions:
            return (
                text("needs_land_image") if self._missing_drawing(settings, sketch=True) else None
            )
        if settings.new_world.keep_geography:
            return text(ERROR + "candidates.real")
        if settings.mask.id:
            return text(ERROR + "candidates.drawn")
        return None

    def editor_problem(self) -> str | None:
        """Why the land editor cannot open now (other work aside); None when it can. It draws the
        land of any continent the world generates."""
        if self.game is None:
            return text("ready_no_game")
        if not self.drawable_continents():
            return text("editor.real_americas")
        return None

    def sketch_candidates(self, count: int = 6) -> str | None:
        if self.busy:
            return text("ready_busy")
        problem = self.sketch_problem()
        if problem is not None or self.game is None:
            return problem
        code, game, cache = self.world_code(), self.game, service.land_cache(self.data)
        drawn = self.drawings()
        try:
            seeds = candidates.roll(count)
        except candidates.CandidateError as error:
            return explain(error)
        self.candidates, self.candidate_code = [], None

        def work(_progress: Progress) -> None:
            found = candidates.sketch(
                game.directory, code.settings(), seeds, cache=cache, drawings=drawn
            )
            with self._lock:
                self.candidates, self.candidate_code = found, code

        return self._run(Task.CANDIDATES, NEW, work)

    def choose_candidate(self, index: int) -> None:
        if self.busy or self.candidate_code is None or not 0 <= index < len(self.candidates):
            return
        code = self._in_epoch(with_new_seed(self.candidate_code, self.candidates[index].seed))
        _ = self.use_code(encode(code))
        self.selection = NEW
        self._changed()

    def enqueue(self) -> str | None:
        """Keep the world chosen now, with its destination, to be made after the ones before it;
        returns why not, or None. Works while the thread makes another world."""
        return self._enqueue(self.world_code())

    def enqueue_candidate(self, index: int) -> str | None:
        """Queue the continent sketched as number ``index`` with the settings it was sketched
        with, without choosing it; returns why not, or None."""
        if self.candidate_code is None or not 0 <= index < len(self.candidates):
            return None
        return self._enqueue(
            self._in_epoch(with_new_seed(self.candidate_code, self.candidates[index].seed))
        )

    def _enqueue(self, code: WorldCode) -> str | None:
        reason = text("ready_busy") if not self.can_prepare else self.setup_problem(code)
        if reason is not None or self.game is None:
            return reason
        name = encode(code)
        with self._lock:
            making = self.busy and self.task is Task.GENERATE and name == self._launched_with
            if making or any(encode(job.code) == name for job in self.queue):
                return text("queue_duplicate")
            self.queue.append(self._request(code))
            # The world goes on the queue of a thread already at work: no second button to press.
            self.queue_follows = self.queue_follows or (
                self.busy and self.task in {Task.GENERATE, Task.QUEUE}
            )
        self._changed()
        return None

    def queued_candidates(self) -> set[int]:
        """The numbers (from 0) of the sketched continents whose worlds wait in the queue."""
        code = self.candidate_code
        if code is None:
            return set()
        with self._lock:
            waiting = {encode(job.code) for job in self.queue}
        return {
            index
            for index, found in enumerate(self.candidates)
            if encode(self._in_epoch(with_new_seed(code, found.seed))) in waiting
        }

    def dequeue(self, code: str) -> None:
        """Take the waiting world with this code out of the queue, a failed one too; the one
        being made stays."""
        with self._lock:
            self.queue = [
                job for job in self.queue if job is self._queue_current or encode(job.code) != code
            ]
            _ = self.queue_errors.pop(code, None)
            self.queue_follows = self.queue_follows and self._next_job() is not None
        self._changed()

    def clear_queue(self) -> None:
        """Forget the waiting worlds and the failed ones; the one being made stays until it is
        done."""
        with self._lock:
            self.queue = [job for job in self.queue if job is self._queue_current]
            self.queue_errors.clear()
            self.queue_follows = False
        self._changed()

    def _next_job(self) -> service.Request | None:
        """The first queued world that has not failed (call with the lock held)."""
        return next((job for job in self.queue if encode(job.code) not in self.queue_errors), None)

    def queue_entries(self) -> list[tuple[service.Request, bool, str]]:
        """The queue in order: each world, whether the thread makes it now, and why it could not
        be made (empty when it did not fail)."""
        with self._lock:
            return [
                (job, job is self._queue_current, self.queue_errors.get(encode(job.code), ""))
                for job in self.queue
            ]

    @property
    def queue_failed(self) -> int:
        """How many worlds of the queue could not be made."""
        with self._lock:
            return len(self.queue_errors)

    def start_queue(self) -> str | None:
        """Make the queued worlds in order, those added meanwhile too, and those that failed
        before. A world that cannot be made stays in the queue with its error and the next one
        starts; a cancellation stops the queue and leaves the rest waiting."""
        if self.busy:
            return text("ready_busy")
        if not self.queue:
            return text("queue_empty")
        self.queue_done = 0
        self.queue_follows = False
        with self._lock:
            self.queue_errors.clear()
        self._launched_with = self.code
        return self._run(Task.QUEUE, NEW, self._queue_work())

    def _queue_work(self) -> Callable[[Progress], service.Result | None]:
        generator = self.generator

        def work(progress: Progress) -> service.Result | None:
            result = None
            failed: str | None = None
            failures = 0
            while True:
                with self._lock:
                    job = self._next_job()
                    self._queue_current = job
                    if job is not None:
                        self._making = (job.code.settings(), job.install)
                if job is None:
                    break
                try:
                    progress.checkpoint()
                    progress.reset_stages()
                    made = generator(job, progress)
                except Cancelled:
                    raise
                except Exception as error:  # noqa: BLE001 - this world failed, the queue goes on
                    failed = self._explain(error)
                    failures += 1
                    with self._lock:
                        self.queue_errors[encode(job.code)] = failed
                        self.finished, self.fraction, self.running = frozenset(), 0.0, ()
                else:
                    result = made
                    with self._lock:
                        self.queue = [item for item in self.queue if item is not job]
                        self.queue_done += 1
                        self.finished, self.fraction = frozenset(), 0.0
                    # Publish this world's library entry before starting the next one.
                    # External library polling stays suspended while the worker is busy.
                    self.refresh_library()
                finally:
                    with self._lock:
                        self._queue_current = None
                self._changed()
            if failed is not None and result is None:
                message = (
                    failed
                    if failures == 1
                    else text("queue_all_failed", count=failures, message=failed)
                )
                raise _QueueFailed(message)
            return result

        return work

    def _request(self, code: WorldCode | None = None) -> service.Request:
        if self.game is None:
            message = "Choose the game before generating"
            raise SettingsError(message)
        code = code or self.world_code()
        # The images the code names; a drawn continent the window no longer holds is left out,
        # and the export says so.
        wanted = drawn_ids(code.settings())
        drawn = {key: mask for key, mask in self.drawings().items() if wanted.get(key) == mask.id}
        return service.Request(
            game=self.game,
            code=code,
            data=self.data,
            profile=self.profile,
            install=self.install,
            show_new_world=self.preferences.show_new_world,
            land_mask=drawn.get(AMERICA),
            regional_masks={key: mask for key, mask in drawn.items() if key != AMERICA},
            output_folder=self.output_folder,
            world_file=self.world_file,
            algorithm=self.algorithm,
        )

    def start(self) -> str | None:
        """Start making the new world; returns why it cannot, or None."""
        reason = self.problem()
        if reason is not None or self.game is None:
            return reason
        request = self._request()
        self._generation_seed = request.code.seed
        self._launched_with = self.code
        self._making = (request.code.settings(), request.install)
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
        key = REPRODUCTION.get(
            verdict(record, algorithms=self.algorithms()), "repro.same_algorithm"
        )
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

    def surroundings(self, world: World, found: Atlas) -> surroundings.Surroundings:
        """What surrounds the world's generated lands on the map (``rnw.app.surroundings``): the
        lands it keeps from the game, from its picture when it has one, and the continent of each
        of its locations, from the installed game's regions."""
        picture = library.picture(self.data, world, revealed=True)
        preview = None
        if picture is not None:
            try:
                preview = read_rgb(picture)
            except (OSError, ValueError):
                preview = None
        return surroundings.surroundings(found, preview, self.game_regions())

    def game_regions(self) -> dict[str, str]:
        """The installed game's continent of each region; empty without a game or its file."""
        game = self.game
        if game is None:
            return {}
        key = (game.directory, game.build_id)
        known = self._regions
        if known is not None and known[0] == key:
            return known[1]
        found: dict[str, str] = {}
        try:
            for location in read_locations(game.directory / DEFINITIONS):
                _ = found.setdefault(location.region, location.continent)
        except (OSError, ValueError):
            found = {}
        self._regions = (key, found)
        return found

    def history_reader(self, world: World) -> history_presenter.Reader | None:
        """Facts for either window, available only after the existing reveal action."""
        if not self.revealed(world):
            return None
        found = self.atlas(world)
        if found is None:
            return None
        known = self._history_readers.get(id(found))
        if known is None or known.language != language():
            known = history_presenter.Reader(found, language(), self.words(found).key)
            while len(self._history_readers) >= WORDS_KEPT:
                del self._history_readers[next(iter(self._history_readers))]
            self._history_readers[id(found)] = known
        return known

    def words(self, found: Atlas) -> atlas.Words:
        """How the window writes an atlas: its own legend words, the game's names of the
        identifiers when the game is here (else the identifiers made readable), the world's
        names in the window's language. Kept for the atlas, the language and the game, since
        the window asks at every refresh and the game's names take a while to read."""
        speaking = language()
        game = self.game.directory if self.game is not None else None
        known = self._words.get(id(found))
        if known is not None and known[0] is found and known[1] == (speaking, game):
            return known[2]
        names: dict[str, str] = {}
        if game is not None:
            names = gamenames.game_names(game, speaking, mapstyle.identifiers(found))
        words = atlas.Words(
            label=lambda key: text(f"legend.{key}"),
            key=lambda key: names.get(key) or atlas.pretty(key),
            name=lambda name: render(name, speaking),
        )
        while len(self._words) >= WORDS_KEPT:
            del self._words[next(iter(self._words))]
        self._words[id(found)] = (found, (speaking, game), words)
        return words

    def revealed(self, world: World) -> bool:
        """Whether the world's New World may be shown here."""
        return self.shown(world) or world.revealed

    def reveal_world(self, world: World) -> None:
        """Show this world's maps (the player's choice, kept with the world)."""
        _ = library.reveal(self.data, world)
        self.refresh_library()

    def summary(self, world: World) -> str:
        """One line on what the world holds, from its atlas ('' without one)."""
        if not self.revealed(world):
            return ""
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

    def build_note(self, world: World) -> str:
        """What a world page says of a world made for another game build: whether it works as
        it is, or ``checking`` while its files are compared on a thread of their own (a second or
        a few the first time), after which the window is told to look again."""
        game = self.game
        if game is None or not world.game_build or world.game_build == game.build_id:
            return ""
        key = (world.id, game.build_id)
        if key not in self._compatible:
            # Finish the current read before starting another. Its notification refreshes
            # the selected page, which then checks the world the player still wants.
            if not self._comparing:
                self._comparing.add(key)

                def compare() -> None:
                    try:
                        found = service.compatible(world, game=game, data=self.data, workers=1)
                    except Exception:  # noqa: BLE001 - record failed background checks, leave no stuck notice
                        logs.get().exception("comparing game inputs for %s failed", world.id)
                        found = None
                    with self._lock:
                        self._compatible[key] = found
                        self._comparing.discard(key)
                    self._changed()

                threading.Thread(target=compare, name="compare-inputs", daemon=True).start()
            kind = "other_build_checking"
        else:
            kind = "other_build_same" if self._compatible[key] else "other_build"
        return text(kind, made=world.game_build, current=game.build_id)

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
        algorithms = self.algorithms()

        def work(progress: Progress) -> None:
            checks[world.id] = checker(
                world, game=game, data=data, progress=progress, algorithms=algorithms
            )

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
        """Block until the work ends (for tests and for closing the window), the queue's
        following worlds included."""
        deadline = None if timeout is None else time.monotonic() + timeout
        while (thread := self._thread) is not None:
            thread.join(None if deadline is None else max(0.0, deadline - time.monotonic()))
            if self._thread is thread or (deadline is not None and time.monotonic() >= deadline):
                return

    def _on_update(self, update: Update) -> None:
        with self._lock:
            self.fraction = update.fraction
            self.running = update.running
            if update.finished:
                self.finished = self.finished | {update.stage}
                logs.get().info(
                    "stage %s %s, %.0f%% of the work",
                    update.stage,
                    "skipped" if update.skipped else "done",
                    update.fraction * 100,
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
        except _QueueFailed as stop:
            # Each world was explained and logged as it failed; the run ends with their words.
            outcome, message = Phase.FAILED, str(stop)
        except Exception as error:  # noqa: BLE001 - whatever failed is shown to the player
            outcome, message = Phase.FAILED, self._explain(error)
        logs.get().info(
            "task %s ended: %s %s", self.task.value if self.task else "?", outcome.value, message
        )
        # Publish a terminal phase only when the library already contains the result. The
        # window may react to FINISHED before the worker returns from this method.
        self.refresh_library()
        with self._lock:
            follow = (
                outcome is Phase.FINISHED
                and self.queue_follows
                and self._next_job() is not None
                and self.task in {Task.GENERATE, Task.QUEUE}
            )
            if outcome is not Phase.FINISHED or self._next_job() is None:
                self.queue_follows = False
            if not follow:
                self.phase, self.result, self.message = outcome, result, message
                self.running = ()
                if outcome is Phase.FINISHED:
                    self.fraction = 1.0
                if result is not None and not self._prepared_another():
                    self.selection = result.world.id
        if follow:
            # Worlds were added while this one was made: go on with them, with no stop between.
            self.queue_done = 0
            self.queue_follows = False
            _ = self._run(Task.QUEUE, NEW, self._queue_work())
        else:
            self._changed()

    def _prepared_another(self) -> bool:
        """Whether the player is on the new-world page with choices other than the ones the
        work started from: a finished world must not take them away from it."""
        return self.selection == NEW and self.code != self._launched_with

    def _explain(self, error: Exception) -> str:
        """The error for the player; the traceback goes to the log and to a file for a report."""
        logs.get().exception("task failed: %s", error)
        self._write_error_log(error)
        from rnw.currents import CurrentError  # noqa: PLC0415 - load generation code only on failure
        from rnw.eu5_export import UnsupportedBuildError  # noqa: PLC0415
        from rnw.eu5_nw_export import LocationLimitError  # noqa: PLC0415
        from rnw.eu5_rivers import RiverRasterError  # noqa: PLC0415
        from rnw.eu5_seas import SeaError  # noqa: PLC0415
        from rnw.ports import PortError  # noqa: PLC0415
        from rnw.sea_routes import LaneError  # noqa: PLC0415

        making = self.task in MAKING
        cause: BaseException | None = error
        while cause is not None:
            if making and isinstance(cause, UnsupportedBuildError):
                return text("generation_unsupported_build")
            if making and isinstance(cause, LocationLimitError):
                return text(
                    "generation_location_limit",
                    count=grouped(cause.count),
                    limit=grouped(cause.limit),
                )
            if making and isinstance(cause, (CurrentError, LaneError, PortError, SeaError)):
                return text("generation_sea_error", detail=str(cause))
            if making and isinstance(cause, RiverRasterError):
                return text("generation_river_error", detail=str(cause))
            if making and isinstance(cause, OSError):
                return text("generation_file_error", detail=str(cause))
            cause = cause.__cause__
        detail = explain(error)
        if (
            making
            and not isinstance(error, (SettingsError, worldfile.WorldFileError))
            and not (error.args and isinstance(error.args[0], Said))
        ):
            detail = text("generation_unexpected_error", detail=detail)
        return detail

    def record_fault(self, error: BaseException, what: str) -> None:
        """Keep a failure that is no task's result, so the player is not told of it: the traceback
        goes to the log and to the last-error file, which a diagnostics report carries."""
        logs.get().error("%s: %s", what, error, exc_info=error)
        self._write_error_log(error)

    def _write_error_log(self, error: BaseException) -> None:
        try:
            self.data.mkdir(parents=True, exist_ok=True)
            trace = "".join(traceback.format_exception(error))
            _ = (self.data / ERROR_LOG).write_text(trace, encoding="utf-8")
        except OSError:
            pass

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

    def playset_check(self, world: World) -> playset.Check | None:
        """What in the active playset can hide the installed ``world``'s files, or None when
        the world is not ticked or the playset cannot be read.

        Reading the other mods' folders takes a moment, and the window asks at every redraw,
        so an answer is kept for a few seconds.
        """
        directory = self._profile_dir()
        if directory is None:
            return None
        key = (str(directory), world.folder)
        kept = self._playset.get(key)
        if kept is not None and time.monotonic() - kept[0] < PLAYSET_SECONDS:
            return kept[1]
        found = playset.check(directory, world.folder, workshop=playset.workshop_root(self.game))
        self._playset[key] = (time.monotonic(), found)
        return found

    def playset_warnings(self, world: World) -> list[str]:
        """What a world page tells of mods that hide the world's files, one text each: a mod
        after the world that has files at the same paths, and other ticked RNW worlds."""
        found = self.playset_check(world)
        if found is None:
            return []
        warnings = [
            text(
                "playset_replaced",
                mod=item.title,
                files=", ".join(item.files[: playset.SAMPLE]),
            )
            for item in found.replacements
        ]
        if found.other_worlds:
            warnings.append(text("playset_worlds", names=", ".join(found.other_worlds)))
        return warnings

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
