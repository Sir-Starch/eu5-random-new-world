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
current is a **course**: a directed path of cells along which the arrows follow the path, that
continues a current of the game at one end or the other. Every other navigable deep cell stays
deep ocean without an arrow, as one of the game's 750 deep zones is [V-LOCAL 1.4.3]. The course
planner therefore:

* reads every lane cell's *evidence*: the zones of the game that touch it (they also *anchor* a
  course), and the lanes that ran over it before the canvas replaced the sea (they direct a
  course at half weight, never anchor one), each counted by how well it points along an edge to a
  neighbouring lane cell;
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
  neighbours whose arrows disagree, and whole pieces that no zone of the game anchors or that are
  too short to be a current rather than a stub (a short piece is kept only when it joins two
  currents of the game).

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
# Where no current of the game touches an edge, the direction of the nearest ones (a field
# interpolated between this many sources) breaks the tie, with a weight too small to change an
# orientation that a current of the game has an opinion on.
FIELD_SOURCES: Final[int] = 4
FIELD: Final[float] = 1e-4
# A cell with two or more edges whose water only enters or only leaves (a spring or a sink in the
# middle of a course) is cut out of it, at this cost in evidence. Reversing a stretch costs twice
# the evidence along it, and a current of the game touching a cell in the middle of a lane
# counts for both of its edges: a stretch that one or two currents of the game support is
# reversed to keep a course whole (the cells that the evidence opposes then drop out), a stretch
# that three or more support is a course of its own and the course is cut where they meet.
CUT: Final[float] = 5.0
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
    courses: Mapping[int, Vector] | None = None,
) -> Flow:
    """The courses on ``lanes``: the current of each lane cell that carries one.

    ``docks`` maps a generated sea cell to the currents of the game's zones that touch it: they
    anchor a course. ``courses`` maps a cell to the current of a lane that ran over it before
    the canvas replaced the sea: it only helps to direct a course that a dock anchors.
    """
    members = sorted(set(lanes))
    vectors = [vector for each in docks.values() for vector in each]
    vectors.extend((courses or {}).values())
    magnitudes = [math.hypot(*vector) for vector in vectors if any(vector)]
    if not members or not any(any(vector) for each in docks.values() for vector in each):
        return Flow({}, frozenset(members))
    strength = math.fsum(magnitudes) / len(magnitudes)
    plan = _Plan(world, docks, courses or {})
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
        courses: Mapping[int, Vector],
    ) -> None:
        self.centres: NDArray[np.int64] = world.centroids
        self.pairs: list[tuple[int, int]] = sorted(
            {(min(a, b), max(a, b)) for a, b in world.edges if a != b}
        )
        self.docks: dict[int, list[Vector]] = {
            cell: [vector for vector in vectors if any(vector)] for cell, vectors in docks.items()
        }
        self.courses: dict[int, Vector] = {
            cell: vector for cell, vector in courses.items() if any(vector)
        }
        # Every current of the game, touching or not, shapes the field that breaks ties.
        self.sources: dict[int, list[Vector]] = {}
        for cell, vectors in sorted(self.docks.items()):
            self.sources.setdefault(cell, []).extend(vectors)
        for cell, vector in sorted(self.courses.items()):
            self.sources.setdefault(cell, []).append(vector)
        self.members: list[int] = []
        self.field: dict[int, tuple[float, float]] = {}

    # -- geometry --------------------------------------------------------------------

    def _field(self) -> dict[int, tuple[float, float]]:
        """The direction of the nearest currents of the game at every cell that has none."""
        sources = sorted(self.sources)
        units: dict[int, tuple[float, float]] = {}
        for cell in sources:
            x = math.fsum(v[0] / math.hypot(*v) for v in self.sources[cell])
            y = math.fsum(v[1] / math.hypot(*v) for v in self.sources[cell])
            units[cell] = (x, y)
        return {cell: self._interpolate(cell, sources, units) for cell in self.members}

    def _interpolate(
        self, cell: int, sources: Sequence[int], units: Mapping[int, tuple[float, float]]
    ) -> tuple[float, float]:
        row, column = int(self.centres[cell][0]), int(self.centres[cell][1])
        nearest = sorted(
            (
                (int(self.centres[s][0]) - row) ** 2 + (int(self.centres[s][1]) - column) ** 2,
                s,
            )
            for s in sources
        )[:FIELD_SOURCES]
        total = x = y = 0.0
        for squared, source in nearest:
            weight = 1.0 / (squared + 1.0)
            total += weight
            x += weight * units[source][0]
            y += weight * units[source][1]
        return (x / total, y / total) if total else (0.0, 0.0)

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

        The currents that touch either cell count in full; the field of the nearest ones
        adds a very small tie-break.
        """
        direction = self.heading(first, second)
        norm = math.hypot(*direction)
        near = (
            self.field[first][0] + self.field[second][0],
            self.field[first][1] + self.field[second][1],
        )
        return (
            self.support(first, direction)
            + self.support(second, direction)
            + FIELD * _cosine(near, direction, norm)
        )

    # -- rounds ----------------------------------------------------------------------

    def settle(self, members: Sequence[int]) -> dict[int, tuple[float, float]]:
        """Prune until every remaining cell is on a clear course; return each one's heading."""
        alive = set(members)
        self.members = sorted(members)
        self.field = self._field()
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
        return found or self._branches(anchor) or self._stub(anchor, down)

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

    def _stub(self, support: Mapping[int, float], down: Mapping[int, int]) -> set[int]:
        """The whole tree, when it is a stub or follows no current of the game."""
        sources = [cell for cell in self.adjacency if not self.incoming[cell]]
        sinks = [cell for cell in self.adjacency if not self.outgoing[cell]]
        length = max(down[cell] for cell in sources)
        anchored = any(value >= ANCHOR for value in support.values())
        bridge = any(support[cell] >= ANCHOR for cell in sources) and any(
            support[cell] >= ANCHOR for cell in sinks
        )
        if (anchored and length >= MIN_COURSE) or (bridge and length >= BRIDGE):
            return set()
        return set(self.adjacency)


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
