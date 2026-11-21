"""What the windows show while a world is made: the export's stages in a few phases.

The export announces some thirty stages (``rnw.progress``), many of them beside each other. The
windows group them by what they do, in the order they begin, and show only the stages that the
world being made runs: a world of several continents joins them into one map after generating
them, a world that keeps the real Americas generates no land at all, and installing is a phase
only when the world goes into the profile. A stage this world does not run is not counted, so a
phase is done when all of its stages that run are, and the numbers beside it are true.

Stage keys stay those of ``rnw.progress``: the time estimate, its stored measurements and the log
are keyed on them. Only what the window says changes here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from rnw.eta import DEPENDENCIES, MILESTONES
from rnw.export_stages import SKIPPED

if TYPE_CHECKING:
    from collections.abc import Collection

    from rnw.settings import Settings


class Kind(StrEnum):
    """How a world is made, as far as its stages go."""

    # The Americas generated on their own canvas.
    AMERICA = "america"
    # Several continents (or one other than America) generated and joined into one map.
    COMPOSED = "composed"
    # The real Americas kept; only their societies are generated.
    REAL = "real"


@dataclass(frozen=True, slots=True)
class PhaseInfo:
    """One line of the progress: what the window calls it and the stages it holds."""

    label: str
    stages: tuple[str, ...]


# In the order the phases begin. The parts of the world's geography share its line.
PHASES: Final[dict[str, PhaseInfo]] = {
    "map": PhaseInfo("Reading the game's map", ("load map", "select canvas")),
    "land": PhaseInfo(
        "Generating land and seas", ("generate world", "relief", "sea cells", "land cells")
    ),
    "game": PhaseInfo(
        "Learning from the game's own lands",
        (
            "vanilla localization keys",
            "vanilla reads",
            "vanilla geometry",
            "vanilla climate",
            "vanilla material levels",
            "vanilla natives",
            "vanilla Americas",
        ),
    ),
    "nature": PhaseInfo(
        "Climate, coasts and rivers",
        ("land character", "biomes and rivers", "settle coasts", "water shapes"),
    ),
    "names": PhaseInfo("Naming and checking the map", ("identities", "world checks")),
    "terrain": PhaseInfo(
        "Painting the terrain",
        (
            "water textures",
            "slot tables",
            "location rasters",
            "png encoding",
            "terrain decals",
            "vegetation instances",
        ),
    ),
    "peoples": PhaseInfo("Founding peoples and their history", ("natives",)),
    "mod": PhaseInfo(
        "Writing the mod",
        (
            "atlas",
            "texts",
            "stories",
            "spline network",
            "script remap",
            "selection cover",
            "write files",
        ),
    ),
    "install": PhaseInfo("Installing into your profile", ("install", "waiting for the game")),
}
# Stages that the windows never list: a wrapper whose parts are listed, the work of other tasks.
UNLISTED: Final[frozenset[str]] = frozenset({"terrain", "candidates", "compare inputs"})
# Stages that run only sometimes and are listed while they run, but are not counted.
OPTIONAL: Final[frozenset[str]] = frozenset({"waiting for the game"})
# The parts of the world's geography: announced inside ``generate world``.
GEOGRAPHY_PARTS: Final[tuple[str, ...]] = ("relief", "sea cells", "land cells")
# Every stage the export of generated geography announces, in the time estimate's order.
EXPORT: Final[tuple[str, ...]] = tuple(
    name for name in DEPENDENCIES if name not in MILESTONES and name != "install"
)


def kind_of(settings: Settings) -> Kind:
    """How the world of ``settings`` is made."""
    if settings.continents.regions:
        return Kind.COMPOSED
    return Kind.REAL if settings.new_world.keep_geography else Kind.AMERICA


def expected(settings: Settings, *, install: bool) -> frozenset[str]:
    """The stages the world of ``settings`` runs and the window counts: neither the optional
    ones nor the parts of the geography, which a world whose land the cache holds skips."""
    kind = kind_of(settings)
    if kind is Kind.REAL:
        found = {name for name in EXPORT if name not in SKIPPED} | {"vanilla Americas"}
    else:
        found = set(EXPORT)
        if settings.continents.america and settings.new_world.keep_geography:
            found.add("vanilla Americas")
    if install:
        found.add("install")
    return frozenset(found)


def phase_of(stage: str, kind: Kind) -> str | None:
    """The phase ``stage`` is listed under; None for an unlisted one. A world of several
    continents chooses its area while it generates them and joins them into one map after."""
    if stage == "select canvas" and kind is Kind.COMPOSED:
        return "land"
    for name, info in PHASES.items():
        if stage in info.stages:
            return name
    return None


def members(phase: str, kind: Kind) -> tuple[str, ...]:
    """The stages of ``phase`` for a world of ``kind``, in the order they begin."""
    found = tuple(name for name in PHASES[phase].stages if phase_of(name, kind) == phase)
    if phase == "land" and kind is Kind.COMPOSED:
        return (*found, "select canvas")
    return found


@dataclass(frozen=True, slots=True)
class Row:
    """A phase as the window lists it.

    ``state`` is ``waiting`` (nothing of it has begun), ``running`` (one of its stages runs),
    ``partial`` (some are done and the next waits for another phase) or ``done``. ``steps`` are
    the stages that run now (the geography's parts and an optional wait included); ``done`` and
    ``total`` count the stages this world runs in it.
    """

    phase: str
    state: str
    steps: tuple[str, ...]
    done: int
    total: int


def rows(
    settings: Settings,
    *,
    install: bool,
    running: Collection[str],
    finished: Collection[str],
) -> list[Row]:
    """The phases of the world of ``settings`` with their state, in order; a phase none of whose
    stages the world runs is left out."""
    kind = kind_of(settings)
    wanted = expected(settings, install=install)
    found: list[Row] = []
    for phase in PHASES:
        stages = members(phase, kind)
        counted = [name for name in stages if name in wanted]
        if not counted:
            continue
        steps = tuple(name for name in stages if name in running)
        if any(name in GEOGRAPHY_PARTS for name in steps):
            # The part says more than the whole that the phase already names.
            steps = tuple(name for name in steps if name != "generate world")
        done = sum(1 for name in counted if name in finished)
        if done == len(counted) and not steps:
            state = "done"
        elif steps:
            state = "running"
        elif done:
            state = "partial"
        else:
            state = "waiting"
        found.append(Row(phase, state, steps, done, len(counted)))
    return found
