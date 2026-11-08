"""Predict the remaining critical path, independently of the completed-stage progress bar.

Stages can start before their inputs are ready. Their measured cost excludes that wait,
so parallel work and nested diagnostic stages are never added twice. Each poll forecasts
the completion again; the shown deadline only follows it. A small difference changes the
pace of the countdown (it pauses for a later forecast and runs at double speed toward an
earlier one), so an overdue stage holds the time still instead of resetting it upward
every few seconds. Only a substantial revision moves the shown time at once.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

# Topological order; these are the data dependencies in eu5_nw_export._export_new_world.
# The vanilla reads need the moved island groups, so they are submitted only after the world
# is generated; the main thread waits for the world checks, which read the identities, before
# the slot tables. The two long branches (terrain and scripts) join at write files. Keep
# this beside its regression.
DEPENDENCIES: Final[dict[str, tuple[str, ...]]] = {
    "load map": (),
    "select canvas": ("load map",),
    "generate world": ("select canvas",),
    "vanilla reads": ("generate world",),
    "vanilla geometry": ("generate world",),
    "vanilla localization keys": ("generate world",),
    "vanilla climate": ("vanilla reads",),
    "vanilla material levels": ("vanilla reads",),
    "vanilla natives": ("vanilla reads", "vanilla geometry"),
    "settle coasts": ("generate world",),
    "water shapes": ("settle coasts",),
    "water textures": ("water shapes",),
    "biomes and rivers": ("water shapes", "vanilla climate"),
    "identities": ("biomes and rivers", "vanilla geometry", "vanilla localization keys"),
    "world checks": ("identities",),
    "slot tables": ("world checks", "vanilla material levels"),
    "location rasters": ("slot tables",),
    "png encoding": ("location rasters",),
    "terrain decals": ("location rasters",),
    "vegetation instances": ("terrain decals", "water textures"),
    "natives": ("slot tables", "vanilla natives"),
    "atlas": ("natives",),
    "texts": ("atlas",),
    "stories": ("texts",),
    "spline network": ("stories",),
    "script remap": ("spline network",),
    "selection cover": ("script remap", "world checks"),
    "write files": ("selection cover", "vegetation instances", "png encoding"),
    "install": ("write files",),
}
# Reference costs include the unlabelled work between stages, not just the timed
# functions. Calibrated against the owner's successful epoch-60 Linux run on 2026-10-31
# (230.9 s, build 26300913); the old 120 s prior predated the current terrain pipeline.
REFERENCE_SECONDS: Final[dict[str, float]] = {
    "load map": 3.0,
    "select canvas": 6.0,
    "vanilla reads": 2.0,
    "vanilla geometry": 2.0,
    "vanilla localization keys": 11.0,
    "vanilla climate": 23.0,
    "vanilla material levels": 18.0,
    "vanilla natives": 8.0,
    "generate world": 69.0,
    "settle coasts": 9.0,
    "water shapes": 5.0,
    "water textures": 16.0,
    "world checks": 4.0,
    "biomes and rivers": 26.0,
    "identities": 7.0,
    "slot tables": 1.0,
    "location rasters": 2.0,
    "png encoding": 2.0,
    "terrain decals": 62.0,
    "vegetation instances": 32.0,
    "natives": 4.0,
    "atlas": 1.0,
    "texts": 35.0,
    "stories": 3.0,
    "spline network": 15.0,
    "script remap": 5.0,
    "selection cover": 23.0,
    "write files": 9.0,
    "install": 1.0,
}
# A forecast that differs from the shown deadline by less than this changes only the pace of
# the countdown; a larger revision is shown at once.
REVISION_SECONDS: Final[float] = 15.0
REVISION_SHARE: Final[float] = 0.1
# Seconds past its expected cost before a stage counts as overdue.
OVERDUE_GRACE: Final[float] = 2.0
MIN_CALIBRATION_WEIGHT: Final[float] = 2.0
# Not a measure of the machine: reading the map waits for the disk, and the canvas's cost
# depends on the preset (a few seconds, or half a minute with expanded oceans).
UNCALIBRATED: Final[frozenset[str]] = frozenset({"load map", "select canvas"})


class Estimate:
    """A job-local clock and stage observations. All calls hold Progress's lock."""

    def __init__(self, now: float) -> None:
        self.started: float = now
        self.priors: dict[str, float] = dict(REFERENCE_SECONDS)
        self.learned: dict[str, float] = {}
        self.begins: dict[str, float] = {}
        self.ends: dict[str, float] = {}
        self.costs: dict[str, float] = {}
        self.fresh_world: bool = False
        self.waited_for_game: bool = False
        self.install: bool = False
        self.deadline: float | None = None
        self.polled: float = now

    def configure(self, learned: Mapping[str, float], *, install: bool) -> None:
        self.learned = dict(learned)
        self.install = install

    def begin(self, name: str, now: float) -> None:
        if name == "waiting for the game":
            self.waited_for_game = True
        if name == "land cells":
            self.fresh_world = True
        if name in DEPENDENCIES:
            self.begins[name] = now

    def finish(self, name: str, now: float, *, completed: bool) -> None:
        if name not in DEPENDENCIES or name not in self.begins or not completed:
            return
        dependencies = DEPENDENCIES[name]
        # Include uninstrumented work between dependencies and this stage. For a stage
        # submitted early, exclude its wait for inputs. Pending inputs mean invalid training.
        if (
            all(dep in self.ends for dep in dependencies)
            and (name != "generate world" or self.fresh_world)
            and (name != "install" or not self.waited_for_game)
        ):
            ready = max((self.ends[dep] for dep in dependencies), default=self.started)
            self.costs[name] = max(0.01, now - ready)
        self.ends[name] = now

    def _scale(self) -> float:
        # Short cached reads and a cached physical world say nothing about the speed of
        # the remaining CPU work. Use substantial, uncached observations and a robust
        # centre, with two reference observations to temper cold-start noise.
        ratios = [
            cost / self.learned.get(name, self.priors[name])
            for name, cost in self.costs.items()
            if name not in UNCALIBRATED
            and self.priors[name] >= MIN_CALIBRATION_WEIGHT
            and cost >= max(1.0, self.priors[name] * 0.25)
        ]
        return max(0.25, min(8.0, statistics.median([1.0, 1.0, *ratios])))

    def forecast(self, now: float) -> float:
        scale = self._scale()
        ends: dict[str, float] = {}
        for name, dependencies in DEPENDENCIES.items():
            if name == "install" and not self.install:
                continue
            if name in self.ends:
                ends[name] = self.ends[name]
                continue
            ready = max((ends[dep] for dep in dependencies), default=self.started)
            expected = self.learned.get(name, self.priors[name]) * scale
            # A cost runs from the moment the inputs are ready and includes the unnamed work
            # before the stage announces itself, so its forecast does too, begun or not. A
            # stage still waiting for predicted inputs has ``ready`` in the future. An
            # overdue stage gets a diminishing but nonzero tail.
            spent = max(0.0, now - ready)
            if spent > expected + OVERDUE_GRACE:
                tail = expected * 0.5 / (1.0 + spent / max(expected, 0.01))
                ends[name] = now + max(1.0, tail)
            else:
                ends[name] = max(ready + expected, now)
        return ends["install" if self.install else "write files"]

    def remaining(self, now: float) -> float:
        if ("install" if self.install else "write files") in self.ends:
            return 0.0
        target = self.forecast(now)
        if self.deadline is None:
            self.deadline = target
        else:
            difference = target - self.deadline
            elapsed = max(0.0, now - self.polled)
            revision = max(REVISION_SECONDS, max(0.0, self.deadline - now) * REVISION_SHARE)
            if abs(difference) >= revision:
                self.deadline = target
            elif difference > 0:
                # Later: hold the shown time still until the deadline meets the forecast.
                self.deadline += min(difference, elapsed)
            else:
                # Earlier: count down at double speed until it meets the forecast.
                self.deadline -= min(-difference, elapsed)
        self.polled = now
        return max(1.0, self.deadline - now)
