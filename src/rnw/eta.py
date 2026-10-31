"""Predict the remaining critical path, independently of the completed-stage progress bar.

Stages can start before their inputs are ready. Their measured cost excludes that wait,
so parallel work and nested diagnostic stages are never added twice. Only stage events or
an overdue-stage review can move the deadline; polling simply counts down to it.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

# Topological order; these are the data dependencies in eu5_nw_export._export. The two
# long branches (terrain and scripts) join at write files. Keep this beside its regression.
DEPENDENCIES: Final[dict[str, tuple[str, ...]]] = {
    "load map": (),
    "select canvas": ("load map",),
    "vanilla reads": ("select canvas",),
    "vanilla geometry": ("select canvas",),
    "vanilla localization keys": ("select canvas",),
    "vanilla climate": ("vanilla reads",),
    "vanilla material levels": ("vanilla reads",),
    "vanilla natives": ("vanilla reads", "vanilla geometry"),
    "generate world": ("select canvas",),
    "settle coasts": ("generate world",),
    "water shapes": ("settle coasts",),
    "water textures": ("water shapes",),
    "world checks": ("water shapes",),
    "biomes and rivers": ("water shapes", "vanilla climate"),
    "identities": ("biomes and rivers", "vanilla geometry", "vanilla localization keys"),
    "slot tables": ("identities", "vanilla material levels"),
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
REVIEW_SECONDS: Final[float] = 10.0
MIN_CALIBRATION_WEIGHT: Final[float] = 2.0


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
        self.reviewed: float = now
        self.changed: bool = True

    def configure(self, learned: Mapping[str, float], *, install: bool) -> None:
        self.learned = dict(learned)
        self.install = install
        self.changed = True

    def begin(self, name: str, now: float) -> None:
        if name == "waiting for the game":
            self.waited_for_game = True
        if name == "land cells":
            self.fresh_world = True
        if name in DEPENDENCIES:
            self.begins[name] = now
            self.changed = True

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
        self.changed = True

    def _scale(self) -> float:
        # Short cached reads and a cached physical world say nothing about the speed of
        # the remaining CPU work. Use substantial, uncached observations and a robust
        # centre, with two reference observations to temper cold-start noise.
        ratios = [
            cost / self.learned.get(name, self.priors[name])
            for name, cost in self.costs.items()
            if self.priors[name] >= MIN_CALIBRATION_WEIGHT
            and cost >= max(1.0, self.priors[name] * 0.25)
        ]
        return max(0.25, min(8.0, statistics.median([1.0, 1.0, *ratios])))

    def _forecast(self, now: float) -> float:
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
            if name in self.begins:
                # A running stage may still be waiting for an input. Once ready, allow a
                # diminishing but nonzero tail when overdue; revise at most every ten seconds.
                start = ready
                spent = max(0.0, now - start)
                tail = expected * 0.5 / (1.0 + spent / max(expected, 0.01))
                ends[name] = (
                    now + max(1.0, tail) if spent > expected + 2.0 else max(start + expected, now)
                )
            else:
                # Never predict that work which has not even started finished in the past.
                ends[name] = max(now, ready) + expected
        return ends["install" if self.install else "write files"]

    def remaining(self, now: float) -> float:
        if ("install" if self.install else "write files") in self.ends:
            return 0.0
        if self.changed or now - self.reviewed >= REVIEW_SECONDS:
            target = self._forecast(now)
            if self.deadline is None:
                self.deadline = target
            else:
                difference = target - self.deadline
                left = max(0.0, self.deadline - now)
                # Small changes are noise; a meaningful correction is blended into the
                # deadline. Do not turn each tick of an overdue stage into a stopwatch.
                if abs(difference) >= max(4.0, left * 0.08):
                    self.deadline += difference * 0.5
            self.changed = False
            self.reviewed = now
        return max(1.0, (self.deadline or now) - now)
