"""What the window knows and does, without drawing anything.

The controller holds the player's choices (game, profile, preset, seed), runs the
generation on a thread of its own and keeps the state the window draws: the phase, the
share done, the stages running and finished, the result or the error. It tells observers
when something changed, from whichever thread changed it; the window turns that into a
signal for its own thread. Nothing here imports Qt, so it is tested without a display.
"""

from __future__ import annotations

import threading
import traceback
from enum import Enum
from typing import TYPE_CHECKING, Final, Protocol

from rnw import __version__
from rnw.app import discovery, history, install, paths, service, session
from rnw.app.discovery import GameInstall, Profile
from rnw.app.session import GameState
from rnw.app.worldcode import (
    WorldCode,
    WorldCodeError,
    decode,
    encode,
    new_code,
    random_seed,
    reproduces,
)
from rnw.gui.text import text
from rnw.progress import STAGES, Cancelled, Progress, Update
from rnw.settings import PRESETS

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

SEED_MAX: Final[int] = (1 << 64) - 1
ERROR_LOG: Final[str] = "last-error.log"


class Phase(Enum):
    """Where the window is in making a world."""

    IDLE = "idle"
    RUNNING = "running"
    CANCELLING = "cancelling"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
        self.install: bool = True
        self.phase: Phase = Phase.IDLE
        self.fraction: float = 0.0
        self.running: tuple[str, ...] = ()
        self.finished: frozenset[str] = frozenset()
        self.message: str = ""
        self.result: service.Result | None = None
        self.advice: str = ""
        self.notice: str = ""
        self._observers: list[Callable[[], None]] = []
        self._lock: threading.Lock = threading.Lock()
        self._progress: Progress | None = None
        self._thread: threading.Thread | None = None

    def subscribe(self, observer: Callable[[], None]) -> None:
        """Call ``observer`` after every change, from the thread that changed it."""
        self._observers.append(observer)

    def _changed(self) -> None:
        for observer in list(self._observers):
            observer()

    def discover(self) -> None:
        """Look for the game and the profile again and take the first of each.

        Worlds retired by an earlier install that the game held then are deleted now if it
        has let go of them.
        """
        self.games = discovery.find_games(self.environment, self.program_folder)
        self.profiles = discovery.find_profiles(self.environment, self.games)
        self.game = self.games[0] if self.games else None
        self.profile = self.profiles[0] if self.profiles else None
        if self.profile is not None:
            _ = install.sweep(self.profile.directory)
        self._changed()

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
        self._changed()
        return None

    def set_preset(self, name: str) -> None:
        """Choose a preset by name."""
        if name in PRESETS and name != self.preset:
            self.preset = name
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
        """Take the preset and seed of a pasted world code; returns the problem, or None."""
        try:
            code = decode(value)
        except WorldCodeError as error:
            return str(error)
        if code.changes:
            return "This code changes settings that the window does not offer yet."
        self.preset, self.seed = code.preset, code.seed
        self.notice = (
            ""
            if reproduces(code)
            else text("other_version", made=code.generator, current=__version__)
        )
        self._changed()
        return None

    @property
    def code(self) -> str:
        """The world code of the current preset and seed."""
        return encode(new_code(self.preset, self.seed))

    def history(self) -> list[history.Entry]:
        """The worlds made before, newest first."""
        return history.load(self.data)

    def problem(self) -> str | None:
        """Why Generate cannot start now, or None when it can."""
        if self.phase in {Phase.RUNNING, Phase.CANCELLING}:
            return text("ready_busy")
        if self.game is None:
            return text("ready_no_game")
        if self.install and self.profile is None:
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

    def start(self) -> str | None:
        """Start making the world; returns why it cannot, or None."""
        reason = self.problem()
        if reason is not None or self.game is None:
            return reason
        request = service.Request(
            game=self.game,
            code=WorldCode(self.preset, self.seed, __version__),
            data=self.data,
            profile=self.profile,
            install=self.install,
        )
        progress = Progress(self._on_update)
        with self._lock:
            self.phase = Phase.RUNNING
            self.fraction, self.running, self.finished = 0.0, (), frozenset()
            self.message, self.result, self.advice = "", None, ""
            self._progress = progress
        self._changed()
        self._thread = threading.Thread(
            target=self._work, args=(request, progress), name="generation", daemon=True
        )
        self._thread.start()
        return None

    def cancel(self) -> None:
        """Ask the running generation to stop; the window shows 'cancelling' until it has."""
        with self._lock:
            progress = self._progress
            if self.phase is not Phase.RUNNING or progress is None:
                return
            self.phase = Phase.CANCELLING
        progress.cancel()
        self._changed()

    def wait(self, timeout: float | None = None) -> None:
        """Block until the generation thread ends (for tests and for closing the window)."""
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

    def _work(self, request: service.Request, progress: Progress) -> None:
        outcome = Phase.FINISHED
        message = ""
        result: service.Result | None = None
        try:
            result = self.generator(request, progress)
        except Cancelled:
            outcome = Phase.CANCELLED
        except Exception as error:  # noqa: BLE001 - whatever failed is shown to the player
            outcome, message = Phase.FAILED, self._explain(error)
        advice = self.next_step(result) if result is not None else ""
        with self._lock:
            self.phase, self.result, self.message = outcome, result, message
            self.advice = advice
            self.running = ()
            if outcome is Phase.FINISHED:
                self.fraction = 1.0
        self._changed()

    def next_step(self, result: service.Result) -> str:
        """What to do in EU5 for the installed world, from the game's log and playsets.

        A different world starts without a restart only while no game was built since EU5
        was launched, and only after a real reload of the mods (experiment 021).
        """
        if result.installed is None or self.profile is None:
            return ""
        state = session.game_state(self.profile.directory)
        enabled = session.world_enabled(self.profile.directory, result.installed.name)
        if state is GameState.FRESH:
            return text("next_fresh" if enabled is not False else "next_fresh_tick") + (
                "" if enabled is not None else " " + text("next_check_tick")
            )
        tick = {True: "", False: text("next_tick") + " ", None: text("next_check_tick") + " "}
        steps = {
            GameState.PLAYED: "next_played",
            GameState.CLOSED: "next_start",
            GameState.UNKNOWN: "next_unknown",
        }
        return tick[enabled] + text(steps[state])

    def _explain(self, error: Exception) -> str:
        """The error for the player; the traceback goes to a file for a bug report."""
        try:
            self.data.mkdir(parents=True, exist_ok=True)
            _ = (self.data / ERROR_LOG).write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
        return str(error) or type(error).__name__
