"""Progress and cancellation of a long job, so an application never looks frozen.

The export is a set of named stages, some of them running beside each other. Each stage
announces itself here when it starts and ends; a listener (the application's window)
receives the stages that run now and the share of the work that is done, weighted by the
time each stage takes. Long loops call ``checkpoint`` so that a cancel is felt within a
second or two instead of at the end of a stage.

Nothing here reaches the generated files. One job runs at a time per process: the active
progress is a module-level value that stage threads read.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.timing import timed

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


class Cancelled(Exception):  # noqa: N818 - a cancel is not an error, and "Cancelled" reads best
    """The job was cancelled; whatever it had written is removed."""


@dataclass(frozen=True, slots=True)
class StageInfo:
    """What the window shows for a stage and how much of the work it is."""

    label: str
    weight: int


# Weights are the seconds a stage takes on the reference machine (continents preset); the
# bar moves by their share, whatever runs beside what.
STAGES: Final[dict[str, StageInfo]] = {
    "load map": StageInfo("Reading the world map", 2),
    "select canvas": StageInfo("Choosing the area to replace", 4),
    "vanilla reads": StageInfo("Reading the game's data", 2),
    "vanilla geometry": StageInfo("Measuring the old locations", 2),
    "vanilla localization keys": StageInfo("Collecting the game's text keys", 8),
    "vanilla climate": StageInfo("Measuring the old climate", 12),
    "vanilla material levels": StageInfo("Measuring the old terrain materials", 8),
    "vanilla natives": StageInfo("Reading the old native peoples", 4),
    "generate world": StageInfo("Generating continents, seas and relief", 26),
    "identities": StageInfo("Naming locations, areas and regions", 9),
    "world checks": StageInfo("Checking the new world", 2),
    "water textures": StageInfo("Painting water and coasts", 14),
    "biomes and rivers": StageInfo("Growing climate, biomes and rivers", 16),
    "slot tables": StageInfo("Preparing terrain materials", 1),
    "location rasters": StageInfo("Drawing the location map", 1),
    "png encoding": StageInfo("Compressing the maps", 3),
    "terrain decals": StageInfo("Sculpting the terrain", 28),
    "vegetation instances": StageInfo("Planting trees and grass", 12),
    "natives": StageInfo("Founding native societies", 3),
    "atlas": StageInfo("Drawing the atlas of the world", 2),
    "texts": StageInfo("Writing names, setup and scripts", 10),
    "script remap": StageInfo("Rewriting game scripts", 4),
    "selection cover": StageInfo("Covering the New World until it is played", 1),
    "write files": StageInfo("Writing the mod", 4),
    # Parts of the stages above: they show in the list while they run and add no weight.
    "land cells": StageInfo("Growing land locations", 0),
    "sea cells": StageInfo("Growing sea zones", 0),
    "relief": StageInfo("Raising mountains and valleys", 0),
    "terrain": StageInfo("Building the terrain", 0),
    # Parts of installing, after the export (``rnw.app.service``).
    "candidates": StageInfo("Sketching continents", 0),
    "install": StageInfo("Installing the world into your profile", 0),
    "compare inputs": StageInfo("Comparing the game's files with the ones this world read", 0),
    "waiting for the game": StageInfo(
        (
            "Waiting for the game to let go of the previous world: untick it in the game's "
            "playset and apply the playset, or close the game"
        ),
        0,
    ),
}
TOTAL_WEIGHT: Final[int] = sum(info.weight for info in STAGES.values())


@dataclass(frozen=True, slots=True)
class Update:
    """One change of the job: the stage that moved, what runs now and how far along it is."""

    stage: str
    label: str
    finished: bool
    fraction: float
    running: tuple[str, ...]


class Progress:
    """Receives the stages of one job, tells a listener, and carries the cancel flag."""

    def __init__(self, listener: Callable[[Update], None] | None = None) -> None:
        self._listener: Callable[[Update], None] | None = listener
        self._lock: threading.Lock = threading.Lock()
        self._running: list[str] = []
        self._done: set[str] = set()
        self._cancelled: threading.Event = threading.Event()

    @property
    def cancelled(self) -> bool:
        """Whether a cancel was asked for."""
        return self._cancelled.is_set()

    @property
    def fraction(self) -> float:
        """The share of the weighted work that is finished."""
        with self._lock:
            return self._share()

    def cancel(self) -> None:
        """Ask the job to stop at its next checkpoint."""
        self._cancelled.set()

    def reset_stages(self) -> None:
        with self._lock:
            self._running.clear()
            self._done.clear()

    def checkpoint(self) -> None:
        """Raise ``Cancelled`` if a cancel was asked for."""
        if self._cancelled.is_set():
            raise Cancelled

    def begin(self, name: str) -> None:
        """A stage starts."""
        self.checkpoint()
        self._move(name, finished=False)

    def finish(self, name: str, *, completed: bool = True) -> None:
        """A stage ends; one that ended by an error or a cancel leaves the running list only."""
        self._move(name, finished=True, completed=completed)

    def _share(self) -> float:
        done = sum(STAGES[name].weight for name in self._done if name in STAGES)
        return min(1.0, done / TOTAL_WEIGHT)

    def _move(self, name: str, *, finished: bool, completed: bool = True) -> None:
        with self._lock:
            if finished:
                if name in self._running:
                    self._running.remove(name)
                if completed:
                    self._done.add(name)
            else:
                self._running.append(name)
            update = Update(
                stage=name,
                label=STAGES[name].label if name in STAGES else name,
                finished=finished,
                fraction=self._share(),
                running=tuple(STAGES[n].label if n in STAGES else n for n in self._running),
            )
        if self._listener is not None:
            self._listener(update)


_active: Progress | None = None


@contextmanager
def active(progress: Progress | None) -> Generator[None]:
    """Make ``progress`` the job that stages and checkpoints report to."""
    global _active  # noqa: PLW0603 - one job at a time per process, read by stage threads
    previous, _active = _active, progress
    try:
        yield
    finally:
        _active = previous


def checkpoint() -> None:
    """Raise ``Cancelled`` if the active job was cancelled; do nothing when there is none."""
    progress = _active
    if progress is not None:
        progress.checkpoint()


def run_stage[T](name: str, work: Callable[[], T]) -> T:
    """Run ``work`` as the stage ``name``: announced, timed and cancellable at its start."""
    with running(name):
        return timed(name, work)


@contextmanager
def running(name: str) -> Generator[None]:
    """Announce the stage ``name`` for the length of a ``with`` block."""
    progress = _active
    if progress is None:
        yield
        return
    progress.begin(name)
    try:
        yield
    except BaseException:
        progress.finish(name, completed=False)
        raise
    progress.finish(name)
