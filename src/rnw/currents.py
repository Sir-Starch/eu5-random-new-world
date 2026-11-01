"""Ocean currents of the generated deep water: clear directed courses, or none.

Game-independent. Every deep-ocean zone of the game's own map holds a current, ``movement_assistance
= { east north }``, a vector of about 92 units that the Sea Currents map mode draws as an arrow
and ships feel as a speed bonus or a headwind: 749 of the 750 deep-ocean zones of 1.4.3 have one,
no other sea zone has [V-LOCAL 1.4.3, C234]. The vectors follow the real gyres: the north
equatorial currents run west at about 90, the equatorial counter-currents east, the Gulf Stream
east-north-east (the second number grows northwards) [V-LOCAL, C236]. The generated New World
replaces a great part of the Atlantic and the Pacific, so the generated deep water must continue
the game's currents where they meet it.

The lane planner (``rnw.lanes``) decides which deep water is *navigable*; that is a question of
routes. Whether a navigable deep cell carries a *current* is a different one, answered here. A
current is a **course**: a directed path of cells along which the arrows follow the path. Every
other navigable deep cell stays deep ocean without an arrow, as one of the game's 750 deep zones
is [V-LOCAL 1.4.3]. Two kinds of course exist. A *continuation* is a piece of lane that a zone of
the game touches along its direction: it carries that current into the generated water. A
*crossing* is a piece that no zone touches (the long straight lanes through the generated
oceans): it carries the direction of the game's gyres there, where they are clear. The planner:

* reads every lane cell's *evidence*: the zones of the game that touch it (they also *anchor* a
  continuation), and the lanes that ran over it before the canvas replaced the sea (half weight),
  each counted by how well it points along an edge to a neighbouring lane cell; and the *field of
  gyres*: near a source the interpolation of the nearest ones, fading with distance into the
  zonal current of the game at the cell's latitude (westward in the trades, eastward in the
  westerlies), with a small vote on each edge;
* cuts the lane cells into a minimum spanning tree per connected piece (a band two cells wide
  becomes one chain with short twigs) and orients each tree so that the flow agrees with the
  evidence as well as any orientation can, with the structural rule that water that enters a cell
  also leaves it: no interior cell is a spring or a sink, so two currents are never driven
  head-on into one cell. A stretch that only one or two zones of the game support is reversed to
  keep a course whole; a better supported one is a course of its own and the cell where two such
  courses meet is cut out;
* gives each cell the direction of its path (the heading from two cells upstream to two cells
  downstream), never the interpolation of far away sources, so an arrow cannot point sideways
  across its own lane;
* drops what is not clear: cells that the zones touching them oppose, short side branches,
  neighbours whose arrows disagree, continuations that no zone anchors or that are too short, and
  crossings where the gyres are unsure, point across the lane, or run in a short stretch (a short
  continuation is kept only when it joins two currents of the game).

The strength is the mean of the game's currents it continues. Integer geometry and IEEE
arithmetic are used in a fixed order; ties go to the lower cell.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, final

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping, Sequence

    import numpy as np
    from numpy.typing import NDArray

    from rnw.newworld import NewWorld

# A current: hundredths of the game's unit, east then north.
Vector = tuple[int, int]
HUNDREDTHS: Final[int] = 100
# A directed path shorter than this many cells is a stub, not a current, unless it joins two
# currents of the game (an anchored source and an anchored sink).
MIN_COURSE: Final[int] = 6
# A side branch shorter than this many cells is dropped unless a current of the game flows along it.
MIN_BRANCH: Final[int] = 5
# A piece that joins two currents of the game (a source and a sink that the game's currents
# follow) is a bridge whatever its length, from this many cells.
BRIDGE: Final[int] = 2
# The weight of the current of a lane that ran over a cell before the canvas replaced the sea,
# against the full weight of a zone of the game that touches it.
COURSE_WEIGHT: Final[float] = 0.5
# A cell is anchored when the game's zones touching it point this well along its own direction
# (the sum of the cosines).
ANCHOR: Final[float] = 0.5
# Evidence against the direction of a cell (the sum of the cosines of the currents of the game
# that touch it) that makes the cell too contradictory to carry it: its arrow would point
# against a current beside it.
OPPOSED: Final[float] = -0.5
# The direction of a cell is the heading across this many cells upstream and downstream.
WINDOW: Final[int] = 2
# Two neighbouring cells whose arrows point at each other this well (cosine) collide head-on.
HEAD_ON: Final[float] = 0.3
# Neighbouring arrows more than this far apart (cosine; 120 degrees) are not one course: the cell
# that disagrees with most of its neighbours gives way.
TURN: Final[float] = -0.5
# The gyres of the game give open water its direction: the zones touching the lanes and the
# lanes that ran over the canvas before it replaced the sea (from this share of a cell, in
# permille) are interpolated between the nearest FIELD_SOURCES of them, by inverse square of
# the distance in typical cells, and fade out over FIELD_REACH typical cells from the nearest.
EVIDENCE_PERMILLE: Final[int] = 500
FIELD_PERMILLE: Final[int] = 250
FIELD_SOURCES: Final[int] = 4
FIELD_REACH: Final[float] = 12.0
# Far from every source the field is the zonal current of the game at the cell's latitude: the
# sources within a Gaussian of this many typical cells of its row, which is how the game's own
# currents run (westward in the trades, eastward in the westerlies).
ZONAL_SIGMA: Final[float] = 4.0
ZONAL_REACH: Final[float] = 3.0
# At least this much weight of sources must lie near the row for the zonal current to exist.
ZONAL_MASS: Final[float] = 2.0
# The field votes on an edge with this weight, against a full contact's 1: it directs open water
# but never outweighs two contacts of the game, and it is too weak to cut a course on its own.
FIELD_WEIGHT: Final[float] = 0.05
# A course that no zone of the game touches (a crossing of open water) is a current only where the
# field is sure of itself and agrees with it: each stretch of it between junctions needs a mean
# field length of at least FIELD_CONFIDENCE and a mean cosine of at least FIELD_COHERENCE between
# the field and the stretch (within about 75 degrees of the flow), and the course at least MIN_OPEN
# cells: a straight crossing of open water is shorter than a current that continues one.
# A run of a stretch is straight while its heading stays within about 60 degrees of its first.
BEND: Final[float] = 0.5
FIELD_CONFIDENCE: Final[float] = 0.3
FIELD_COHERENCE: Final[float] = 0.25
MIN_OPEN: Final[int] = 4
# A cell with two or more edges whose water only enters or only leaves (a spring or a sink in the
# middle of a course) is cut out of it, at this cost in evidence. Reversing a stretch costs twice
# the evidence along it, and a current of the game touching a cell in the middle of a lane
# counts for both of its edges: a stretch that one current in the middle (loss about 4.4) or two at
# an end supports is reversed to keep a course whole (the cells that the evidence opposes then drop
# out), a stretch that three at an end (about 6.2) or more support is a course of its own and the
# course is cut where they meet.
CUT: Final[float] = 5.3
# A last, smaller bias: with no opinion at all the flow runs from the side with more evidence.
TIE: Final[float] = 1e-7
MIN_NORM: Final[float] = 1e-9


class CurrentError(ValueError):
    """The planned currents are not clear courses."""


@dataclass(frozen=True, slots=True)
class Flow:
    """The currents of the lane cells that carry one, and the lane cells that do not.

    ``dropped`` cells stay navigable deep water; they have no arrow because no clear course
    runs through them.
    """

    flows: dict[int, Vector]
    dropped: frozenset[int]


def flow(
    world: NewWorld,
    lanes: Iterable[int],
    docks: Mapping[int, Sequence[Vector]],
    courses: Mapping[int, tuple[Vector, int]] | None = None,
) -> Flow:
    """The courses on ``lanes``: the current of each lane cell that carries one.

    ``docks`` maps a generated sea cell to the currents of the game's zones that touch it: they
    anchor a course. ``courses`` maps a cell to the current of the lanes that ran over it before
    the canvas replaced the sea, with the share of the cell (permille) they covered: they direct
    courses and, with the docks, give open water the direction of the game's gyres.
    """
    members = sorted(set(lanes))
    over = courses or {}
    vectors = [vector for each in docks.values() for vector in each]
    vectors.extend(vector for vector, permille in over.values() if permille >= EVIDENCE_PERMILLE)
    magnitudes = [math.hypot(*vector) for vector in vectors if any(vector)]
    if not members or not magnitudes:
        return Flow({}, frozenset(members))
    strength = math.fsum(magnitudes) / len(magnitudes)
    plan = _Plan(world, docks, over)
    kept = plan.settle(members)
    return Flow(
        {cell: _scaled(heading, strength) for cell, heading in sorted(kept.items())},
        frozenset(members) - frozenset(kept),
    )


def check_courses(world: NewWorld, flows: Mapping[int, Vector]) -> None:
    """Raise ``CurrentError`` when two neighbouring currents are driven head-on into one another.

    Read from the finished vectors alone, as the game would draw them: a cell's arrow pointing at
    a neighbour whose arrow points back at it.
    """
    for first, second in sorted({(min(a, b), max(a, b)) for a, b in world.edges}):
        if first not in flows or second not in flows:
            continue
        row = int(world.centroids[second][0]) - int(world.centroids[first][0])
        column = int(world.centroids[second][1]) - int(world.centroids[first][1])
        toward = (float(column), float(-row))
        norm = math.hypot(*toward)
        if (
            _cosine(flows[first], toward, norm) > HEAD_ON
            and _cosine(flows[second], (-toward[0], -toward[1]), norm) > HEAD_ON
        ):
            message = f"The currents of sea cells {first} and {second} flow head-on"
            raise CurrentError(message)


def _scaled(heading: tuple[float, float], strength: float) -> Vector:
    """The direction of ``heading`` at the game's strength, in hundredths."""
    norm = math.hypot(*heading)
    if norm < MIN_NORM:
        message = "A current has no direction"
        raise CurrentError(message)
    factor = strength / norm
    return round(heading[0] * factor), round(heading[1] * factor)


@final
class _Plan:
    """The geometry and evidence of one world's lane cells, and the rounds that settle them."""

    def __init__(
        self,
        world: NewWorld,
        docks: Mapping[int, Sequence[Vector]],
        courses: Mapping[int, tuple[Vector, int]],
    ) -> None:
        self.centres: NDArray[np.int64] = world.centroids
        self.pairs: list[tuple[int, int]] = sorted(
            {(min(a, b), max(a, b)) for a, b in world.edges if a != b}
        )
        self.pixels: NDArray[np.int64] = world.pixels
        self.docks: dict[int, list[Vector]] = {
            cell: [vector for vector in vectors if any(vector)] for cell, vectors in docks.items()
        }
        # The old lanes that covered most of a cell direct its course.
        self.courses: dict[int, Vector] = {
            cell: vector
            for cell, (vector, permille) in courses.items()
            if any(vector) and permille >= EVIDENCE_PERMILLE
        }
        # Docks and every old lane that covered a fair share of a cell shape the field of gyres.
        self.sources: dict[int, tuple[float, float, float]] = {}
        for cell, vectors in sorted(self.docks.items()):
            units = [
                (x / math.hypot(x, y), y / math.hypot(x, y)) for x, y in vectors if any((x, y))
            ]
            if units:
                self.sources[cell] = (
                    math.fsum(u[0] for u in units) / len(units),
                    math.fsum(u[1] for u in units) / len(units),
                    1.0,
                )
        for cell, (vector, permille) in sorted(courses.items()):
            if cell not in self.sources and any(vector) and permille >= FIELD_PERMILLE:
                norm = math.hypot(*vector)
                self.sources[cell] = (vector[0] / norm, vector[1] / norm, permille / 1000)
        self.members: list[int] = []
        self.docked: set[int] = set()
        self.field: dict[int, tuple[float, float]] = {}

    # -- geometry --------------------------------------------------------------------

    def _field(self) -> dict[int, tuple[float, float]]:
        """The direction of the game's gyres at every lane cell, as a vector of length <= 1.

        Near a source of the game it is the interpolation of the nearest ones; the length is how
        much they agree. It fades out with the distance to the nearest into the zonal current of
        the game at the cell's latitude, which is what open water far from any source follows.
        """
        areas = sorted(int(self.pixels[cell]) for cell in self.members)
        scale = math.sqrt(areas[len(areas) // 2]) if areas else 1.0
        sources = sorted(self.sources)
        field: dict[int, tuple[float, float]] = {}
        for cell in self.members:
            row, column = int(self.centres[cell][0]), int(self.centres[cell][1])
            nearest = sorted(
                (
                    ((int(self.centres[s][0]) - row) ** 2 + (int(self.centres[s][1]) - column) ** 2)
                    / (scale * scale),
                    s,
                )
                for s in sources
            )[:FIELD_SOURCES]
            local = (0.0, 0.0)
            reach = 0.0
            if nearest:
                total = x = y = 0.0
                for distance, source in nearest:
                    ux, uy, weight = self.sources[source]
                    share = weight / (distance + 1.0)
                    total += share
                    x += share * ux
                    y += share * uy
                reach = max(0.0, 1.0 - math.sqrt(nearest[0][0]) / FIELD_REACH)
                local = (x / total, y / total)
            zonal = self._zonal(row, scale, sources)
            field[cell] = (
                reach * local[0] + (1.0 - reach) * zonal[0],
                reach * local[1] + (1.0 - reach) * zonal[1],
            )
        return field

    def _zonal(self, row: int, scale: float, sources: Sequence[int]) -> tuple[float, float]:
        """The mean direction of the sources near this row (a Gaussian of ``ZONAL_SIGMA``)."""
        total = x = y = 0.0
        for source in sources:
            offset = (int(self.centres[source][0]) - row) / (scale * ZONAL_SIGMA)
            if abs(offset) > ZONAL_REACH:
                continue
            ux, uy, weight = self.sources[source]
            share = weight * math.exp(-offset * offset / 2)
            total += share
            x += share * ux
            y += share * uy
        return (x / total, y / total) if total > ZONAL_MASS else (0.0, 0.0)

    def _touches(self, cell: int, piece: Mapping[int, Sequence[int]]) -> bool:
        """Whether a zone of the game at ``cell`` points along (either way) a lane of the piece."""
        for other in piece[cell]:
            direction = self.heading(cell, other)
            if abs(self.support(cell, direction, anchors_only=True)) >= ANCHOR:
                return True
        return False

    def field_support(self, cell: int, direction: tuple[float, float]) -> float:
        """The cosine between the gyres' direction at ``cell`` and ``direction``, scaled by
        how sure the field is there."""
        norm = math.hypot(*direction)
        x, y = self.field[cell]
        return 0.0 if norm < MIN_NORM else (x * direction[0] + y * direction[1]) / norm

    def heading(self, first: int, second: int) -> tuple[float, float]:
        """East and north from the centre of ``first`` to that of ``second``."""
        row = int(self.centres[second][0]) - int(self.centres[first][0])
        column = int(self.centres[second][1]) - int(self.centres[first][1])
        return float(column), float(-row)

    def support(
        self, cell: int, direction: tuple[float, float], *, anchors_only: bool = False
    ) -> float:
        """The sum of the cosines between the game's currents at ``cell`` and ``direction``.

        The zones of the game that touch the cell count in full; a lane that ran over it before
        the canvas replaced the sea counts for ``COURSE_WEIGHT`` and never anchors a course.
        """
        norm = math.hypot(*direction)
        if norm < MIN_NORM:
            return 0.0
        total = 0.0
        for x, y in self.docks.get(cell, ()):
            total += (x * direction[0] + y * direction[1]) / (math.hypot(x, y) * norm)
        if not anchors_only and cell in self.courses:
            x, y = self.courses[cell]
            total += (
                COURSE_WEIGHT * (x * direction[0] + y * direction[1]) / (math.hypot(x, y) * norm)
            )
        return total

    def evidence(self, first: int, second: int) -> float:
        """How well the game's currents point from ``first`` to ``second``.

        The zones that touch either cell count in full, the old lanes that covered them at half,
        and the field of gyres (the nearest of both kinds) adds a small vote for open water.
        """
        direction = self.heading(first, second)
        return (
            self.support(first, direction)
            + self.support(second, direction)
            + FIELD_WEIGHT
            * (self.field_support(first, direction) + self.field_support(second, direction))
            / 2
        )

    # -- rounds ----------------------------------------------------------------------

    def settle(self, members: Sequence[int]) -> dict[int, tuple[float, float]]:
        """Prune until every remaining cell is on a clear course; return each one's heading."""
        alive = set(members)
        self.members = sorted(members)
        self.field = self._field()
        # A piece of lane that a zone of the game touches along a lane (not across it) is a
        # continuation of that current; one that none touches is a crossing of open water.
        # Pruning never joins pieces.
        self.docked = set()
        for piece in self._trees(alive):
            if any(self._touches(cell, piece) for cell in piece):
                self.docked.update(piece)
        # Every round that does not end the planning removes a cell, so there are at most as many.
        for _ in range(len(members) + 1):
            doomed: set[int] = set()
            headings: dict[int, tuple[float, float]] = {}
            for tree in self._trees(alive):
                directed = _orient(tree, self)
                found = directed.headings(self)
                headings.update(found)
                doomed |= directed.doomed(self, found)
            if not doomed:
                doomed = self._head_on(alive, headings)
            if not doomed:
                return headings
            alive -= doomed
        message = "The currents do not settle into clear courses"
        raise CurrentError(message)

    def _trees(self, alive: Collection[int]) -> list[dict[int, list[int]]]:
        """A minimum spanning tree of each connected piece of ``alive`` (adjacency lists)."""
        parents = {cell: cell for cell in alive}

        def root(cell: int) -> int:
            while parents[cell] != cell:
                parents[cell] = parents[parents[cell]]
                cell = parents[cell]
            return cell

        edges: list[tuple[int, int, int]] = []
        for first, second in self.pairs:
            if first in parents and second in parents:
                dr = int(self.centres[second][0]) - int(self.centres[first][0])
                dc = int(self.centres[second][1]) - int(self.centres[first][1])
                edges.append((dr * dr + dc * dc, first, second))
        tree: dict[int, list[int]] = {cell: [] for cell in sorted(alive)}
        for _, first, second in sorted(edges):
            a, b = root(first), root(second)
            if a != b:
                parents[max(a, b)] = min(a, b)
                tree[first].append(second)
                tree[second].append(first)
        seen: set[int] = set()
        pieces: list[dict[int, list[int]]] = []
        for start in sorted(tree):
            if start in seen:
                continue
            seen.add(start)
            piece, stack = {start: sorted(tree[start])}, [start]
            while stack:
                for other in tree[stack.pop()]:
                    if other not in seen:
                        seen.add(other)
                        piece[other] = sorted(tree[other])
                        stack.append(other)
            pieces.append(piece)
        return pieces

    def _head_on(
        self, alive: Collection[int], headings: Mapping[int, tuple[float, float]]
    ) -> set[int]:
        """Cells to drop so that neighbouring arrows agree: none head-on, none far apart.

        The spanning trees direct their own edges consistently; two arms of one piece that meet
        without a tree edge between them, or the several arms that meet in a wide cluster of cells,
        can still be driven together or pulled apart. Of each such pair the cell that disagrees
        with more of its neighbours gives way, then the one the game's currents support less,
        then the higher cell number.
        """
        pairs: list[tuple[int, int]] = []
        count: Counter[int] = Counter()
        for first, second in self.pairs:
            if first not in alive or second not in alive:
                continue
            toward = self.heading(first, second)
            norm = math.hypot(*toward)
            head_on = (
                _cosine(headings[first], toward, norm) > HEAD_ON
                and _cosine(headings[second], (-toward[0], -toward[1]), norm) > HEAD_ON
            )
            apart = _cosine(headings[first], headings[second], math.hypot(*headings[second])) < TURN
            if head_on or apart:
                pairs.append((first, second))
                count[first] += 1
                count[second] += 1
        found: set[int] = set()
        for first, second in pairs:
            if first in found or second in found:
                continue
            found.add(
                min(
                    (first, second),
                    key=lambda cell: (-count[cell], self.support(cell, headings[cell]), -cell),
                )
            )
        return found


def _cosine(heading: Sequence[float], other: tuple[float, float], norm: float) -> float:
    length = math.hypot(*heading) * norm
    return 0.0 if length < MIN_NORM else (heading[0] * other[0] + heading[1] * other[1]) / length


@dataclass(slots=True)
class _Tree:
    """One spanning tree with every edge directed."""

    adjacency: dict[int, list[int]]
    outgoing: dict[int, list[int]]
    incoming: dict[int, list[int]]
    cuts: frozenset[int]

    def _reach(self) -> tuple[dict[int, int], dict[int, int]]:
        """The cells on the longest directed path starting at, and ending at, each cell."""
        waiting = {cell: len(self.incoming[cell]) for cell in self.adjacency}
        order = sorted(cell for cell, count in waiting.items() if count == 0)
        for cell in order:
            for other in self.outgoing[cell]:
                waiting[other] -= 1
                if waiting[other] == 0:
                    order.append(other)
        down: dict[int, int] = {}
        for cell in reversed(order):
            down[cell] = 1 + max((down[other] for other in self.outgoing[cell]), default=0)
        up: dict[int, int] = {}
        for cell in order:
            up[cell] = 1 + max((up[other] for other in self.incoming[cell]), default=0)
        return down, up

    def _window(
        self, cell: int, down: Mapping[int, int], up: Mapping[int, int]
    ) -> tuple[list[int], list[int]]:
        """The cells within ``WINDOW`` steps downstream and upstream, along the longer course."""
        found: list[list[int]] = []
        for links, reach in ((self.outgoing, down), (self.incoming, up)):
            path: list[int] = []
            at = cell
            for _ in range(WINDOW):
                options = links[at]
                if not options:
                    break
                at = max(options, key=lambda other: (reach[other], -other))
                path.append(at)
            found.append(path)
        return found[0], found[1]

    def headings(self, plan: _Plan) -> dict[int, tuple[float, float]]:
        """The direction of every cell: along its course, from upstream to downstream."""
        down, up = self._reach()
        result: dict[int, tuple[float, float]] = {}
        for cell in sorted(self.adjacency):
            after, before = self._window(cell, down, up)
            result[cell] = plan.heading(
                before[-1] if before else cell, after[-1] if after else cell
            )
        return result

    def doomed(self, plan: _Plan, headings: Mapping[int, tuple[float, float]]) -> set[int]:
        """The cells on no clear course: a spring or sink, opposed, a short branch, or a stub."""
        if self.cuts:
            return set(self.cuts)
        down, _ = self._reach()
        support = {cell: plan.support(cell, headings[cell]) for cell in self.adjacency}
        anchor = {
            cell: plan.support(cell, headings[cell], anchors_only=True) for cell in self.adjacency
        }
        found = {cell for cell in sorted(self.adjacency) if support[cell] < OPPOSED}
        return found or self._branches(anchor) or self._stub(plan, headings, anchor, down)

    def _branches(self, support: Mapping[int, float]) -> set[int]:
        """Short side branches (from a junction to a free end) that no game current anchors."""
        found: set[int] = set()
        for leaf in sorted(self.adjacency):
            if len(self.adjacency[leaf]) != 1:
                continue
            chain = [leaf]
            while True:
                (step,) = (o for o in self.adjacency[chain[-1]] if o not in chain[-2:])
                if len(self.adjacency[step]) != 2:  # noqa: PLR2004 - a junction or another end.
                    break
                chain.append(step)
            if (
                len(self.adjacency[step]) >= 3  # noqa: PLR2004 - a junction.
                and len(chain) < MIN_BRANCH
                and support[leaf] < ANCHOR
            ):
                found.update(chain)
        return found

    def _stub(
        self,
        plan: _Plan,
        headings: Mapping[int, tuple[float, float]],
        anchor: Mapping[int, float],
        down: Mapping[int, int],
    ) -> set[int]:
        """The whole tree, when it is a stub or follows neither a current nor the gyres of the game.

        A tree that a zone of the game touches along its direction is a course from ``MIN_COURSE``
        cells, or a bridge between two such zones from ``BRIDGE``. A tree that none touches (a
        crossing of open water) is a course from ``MIN_OPEN`` cells where the field of gyres
        agrees with each stretch of it: the mean field cosine of the stretch's cells is at least
        ``FIELD_COHERENCE``; a stretch that does not agree is dropped.
        """
        sources = [cell for cell in self.adjacency if not self.incoming[cell]]
        sinks = [cell for cell in self.adjacency if not self.outgoing[cell]]
        length = max(down[cell] for cell in sources)
        anchored = any(value >= ANCHOR for value in anchor.values())
        bridge = any(anchor[cell] >= ANCHOR for cell in sources) and any(
            anchor[cell] >= ANCHOR for cell in sinks
        )
        if any(cell in plan.docked for cell in self.adjacency):
            if (anchored and length >= MIN_COURSE) or (bridge and length >= BRIDGE):
                return set()
            return set(self.adjacency)
        # No zone of the game touches this piece of lane: open water. Each stretch between junctions
        # keeps only the cells where the gyres of the game agree with its direction.
        disagree: set[int] = set()
        for chain in self._chains():
            for run in self._runs(chain, headings):
                surety = math.fsum(math.hypot(*plan.field[cell]) for cell in run)
                agreement = math.fsum(plan.field_support(cell, headings[cell]) for cell in run)
                if (
                    len(run) < MIN_OPEN
                    or surety < FIELD_CONFIDENCE * len(run)
                    or agreement < FIELD_COHERENCE * surety
                ):
                    disagree.update(run)
        if disagree:
            return disagree
        return set() if length >= MIN_OPEN else set(self.adjacency)

    def _runs(
        self, chain: Sequence[int], headings: Mapping[int, tuple[float, float]]
    ) -> list[list[int]]:
        """A stretch cut into straight runs: a run ends where its heading has turned ``BEND``."""
        members = set(chain)
        start = next(
            (cell for cell in sorted(chain) if not (set(self.incoming[cell]) & members)), min(chain)
        )
        ordered = [start]
        while True:
            options = [other for other in self.outgoing[ordered[-1]] if other in members]
            if not options:
                break
            ordered.append(min(options))
        runs: list[list[int]] = [[ordered[0]]]
        for cell in ordered[1:]:
            first = headings[runs[-1][0]]
            if _cosine(headings[cell], first, math.hypot(*first)) < BEND:
                runs.append([])
            runs[-1].append(cell)
        return runs

    def _chains(self) -> list[list[int]]:
        """The stretches of the tree between its junctions and free ends (junctions excluded)."""
        plain = {cell for cell, links in self.adjacency.items() if len(links) <= 2}  # noqa: PLR2004
        seen: set[int] = set()
        found: list[list[int]] = []
        for start in sorted(plain):
            if start in seen:
                continue
            seen.add(start)
            chain, stack = [start], [start]
            while stack:
                for other in self.adjacency[stack.pop()]:
                    if other in plain and other not in seen:
                        seen.add(other)
                        chain.append(other)
                        stack.append(other)
            found.append(sorted(chain))
        return found


def _orient(tree: dict[int, list[int]], plan: _Plan) -> _Tree:
    """Direct every edge of ``tree`` to agree with the evidence, with water that enters leaving.

    Exact dynamic programming on the tree rooted at its lowest free end. A cell with two or more
    edges has one entering and one leaving; a cell that does not (a spring or a sink in the middle
    of a course) is cut out, which costs ``CUT``, unless reversing the cheapest edge costs less. The
    evidence only expresses a preference; the best total wins, and when the evidence has no
    opinion the flow follows the field of the nearest currents.
    """
    cells = sorted(tree)
    leaves = [cell for cell in cells if len(tree[cell]) == 1]
    root = leaves[0] if leaves else cells[0]
    parent: dict[int, int] = {root: -1}
    order = [root]
    for cell in order:
        for other in tree[cell]:
            if other not in parent:
                parent[other] = cell
                order.append(other)
    children = {cell: [o for o in tree[cell] if parent[o] == cell] for cell in cells}
    gain = {cell: plan.evidence(parent[cell], cell) for cell in order[1:]}
    mass = dict.fromkeys(cells, 0.0)
    for cell in reversed(order[1:]):
        mass[parent[cell]] += mass[cell] + abs(gain[cell])
    # For each non-root cell, the edge from its parent directed down (parent to cell) or up has
    # this gain, including the tie-break towards the lighter side.
    lean = {
        cell: TIE if mass[root] - mass[cell] - abs(gain[cell]) >= mass[cell] else -TIE
        for cell in order[1:]
    }
    value = {cell: (gain[cell] + lean[cell], -gain[cell] - lean[cell]) for cell in order[1:]}
    best: dict[int, list[float]] = {}
    choice: dict[tuple[int, int], tuple[dict[int, int], bool]] = {}
    for cell in reversed(order):
        kids = children[cell]
        # A child's edge directed down leaves this cell (0); directed up it enters it (1).
        totals = {u: (value[u][0] + best[u][0], value[u][1] + best[u][1]) for u in kids}
        scores: list[float] = []
        for parent_way in (0, 1) if cell != root else (None,):
            picked = {u: (0 if totals[u][0] >= totals[u][1] else 1) for u in kids}
            score = sum(totals[u][picked[u]] for u in kids)
            entering = sum(1 for u in kids if picked[u] == 1) + (parent_way == 0)
            leaving = sum(1 for u in kids if picked[u] == 0) + (parent_way == 1)
            cut = False
            if len(tree[cell]) >= 2 and not (entering and leaving):  # noqa: PLR2004
                need = 1 if not entering else 0
                flippable = [u for u in kids if picked[u] != need]
                cheapest = min(flippable, key=lambda u: (abs(totals[u][0] - totals[u][1]), u))
                loss = abs(totals[cheapest][0] - totals[cheapest][1])
                if loss <= CUT:
                    picked[cheapest] = need
                    score -= loss
                else:
                    cut = True
                    score -= CUT
            choice[cell, 0 if parent_way is None else parent_way] = (picked, cut)
            scores.append(score)
        best[cell] = scores
    way: dict[int, int] = {}
    cuts: set[int] = set()
    for cell in order:
        picked, cut = choice[cell, way.get(cell, 0)]
        if cut:
            cuts.add(cell)
        way.update(picked)
    outgoing: dict[int, list[int]] = {cell: [] for cell in cells}
    incoming: dict[int, list[int]] = {cell: [] for cell in cells}
    for cell in order[1:]:
        source, target = (parent[cell], cell) if way[cell] == 0 else (cell, parent[cell])
        outgoing[source].append(target)
        incoming[target].append(source)
    return _Tree(tree, outgoing, incoming, frozenset(cuts))
