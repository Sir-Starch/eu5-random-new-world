"""Roads for a generated world: contacts, road paths and the mod's spline network."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import numpy as np
import pytest

from rnw import eu5_splines
from rnw.eu5_splines import (
    SPACING,
    build_splines,
    land_contacts,
    road_path,
    spline_problems,
)
from rnw.splnet import (
    NewStrip,
    SplineError,
    SplineNetwork,
    parse,
    polyline,
    rebuild,
    serialize,
    strip_id,
)

EMPTY = SplineNetwork(
    anchors=np.zeros(0, dtype=np.int64),
    anchor_xy=np.zeros((0, 2), dtype=np.float32),
    point_xy=np.zeros((0, 2), dtype=np.float32),
    segments=(),
    strips={},
)
LABELS = np.array(
    [
        [5, 0, 0, 1, 1, 2, 5],
        [5, 0, 0, 1, 1, 2, 5],
        [5, 3, 3, 3, 4, 4, 5],
        [5, 3, 3, 3, 4, 4, 5],
    ],
    dtype=np.int32,
)
LAND = np.array([True, True, True, True, True, False])
GENERATED = np.array([False, True, False, False, True, False])


def _brute_force(
    labels: np.ndarray, land: np.ndarray, generated: np.ndarray
) -> set[tuple[int, int]]:
    found: set[tuple[int, int]] = set()
    rows, columns = labels.shape
    for r in range(rows):
        for c in range(columns):
            for dr, dc in ((0, 1), (1, 0)):
                if r + dr < rows and c + dc < columns:
                    a, b = int(labels[r, c]), int(labels[r + dr, c + dc])
                    if a != b and land[a] and land[b] and (generated[a] or generated[b]):
                        found.add((min(a, b), max(a, b)))
    return found


def test_contacts_are_land_pairs_with_a_generated_location() -> None:
    """Only land contacts with a generated location count; the points lie on the border."""
    found = land_contacts(LABELS, LAND, GENERATED)
    assert set(found) == _brute_force(LABELS, LAND, GENERATED)
    assert set(found) == {(0, 1), (1, 2), (1, 3), (1, 4), (2, 4), (3, 4)}
    x, y = found[(0, 1)]  # the border of columns 2 and 3 on the two top rows
    assert x == 3.0
    assert y in {3.5, 2.5}
    assert found[(1, 3)] == (3.5, 2.0)
    assert (0, 3) not in found  # two old locations
    assert not any(5 in pair for pair in found)  # label 5 is no land


def test_contacts_do_not_depend_on_the_band_that_is_scanned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same contacts and points come out of any band height."""
    whole = land_contacts(LABELS, LAND, GENERATED)
    for band in (1, 2, 3):
        monkeypatch.setattr(eu5_splines, "BAND", band)
        assert land_contacts(LABELS, LAND, GENERATED) == whole


def test_contacts_include_the_other_edge_of_the_map() -> None:
    """Generated land on the two map edges shares a normal land contact at x=0."""
    wrapped = np.array([[1, 0, 0, 2]], dtype=np.int32)
    found = land_contacts(wrapped, np.array([True, True, True]), np.array([False, True, False]))
    assert found[(1, 2)] == (0.0, 0.5)


def test_a_road_across_the_map_wrap_uses_the_short_path() -> None:
    """A road between the edges is short on the cylinder and keeps its actual anchors."""
    start, border, end = (990.5, 20.5), (0.0, 25.0), (12.5, 30.5)
    path = road_path(start, border, end, map_width=1000)
    assert path[0].tolist() == list(start)
    assert path[-1].tolist() == list(end)
    assert len(path) < 20
    dx = (np.diff(path[:, 0]) + 500) % 1000 - 500
    assert float(np.hypot(dx, np.diff(path[:, 1])).max()) <= SPACING + 0.5
    assert np.all((path[:, 0] < 30) | (path[:, 0] > 970))


def test_wrapped_road_survives_serialization_and_rejects_a_planar_detour() -> None:
    """Read-back validation measures short steps across the cylinder, including the wrap."""
    anchors = {"west": (990.5, 20.5), "east": (12.5, 30.5)}
    contacts = {("west", "east"): (0.0, 25.0)}
    vanilla = serialize(EMPTY)
    data, stats = build_splines(
        vanilla,
        vanilla_keys=[],
        mod_keys=list(anchors),
        contacts=contacts,
        anchors=anchors,
        map_width=1000,
    )
    assert stats["wrapped_strips_added"] == 1

    def check(payload: bytes) -> list[str]:
        return spline_problems(
            payload,
            vanilla,
            vanilla_keys=[],
            mod_keys=list(anchors),
            contacts=list(contacts),
            roads=list(contacts),
            map_width=1000,
        )

    assert check(data) == []
    network = parse(data)
    network.point_xy[:, 0] = 500
    assert any("discontinuous step" in problem for problem in check(serialize(network)))


def test_a_road_runs_from_anchor_to_anchor_through_the_border_point() -> None:
    """The ends are exactly the anchors, the middle the border point, points a few pixels apart."""
    start, border, end = (10.5, 10.5), (40.5, 20.5), (70.5, 10.5)
    path = road_path(start, border, end)
    assert path.dtype == np.float32
    assert path[0].tolist() == list(start)
    assert path[-1].tolist() == list(end)
    middle = path[len(path) // 2]
    assert abs(float(middle[0]) - border[0]) < 0.5
    assert abs(float(middle[1]) - border[1]) < 0.5
    steps = np.hypot(*np.diff(path, axis=0).T)
    assert float(steps.max()) <= SPACING + 0.5
    assert np.array_equal(path, road_path(start, border, end))
    straight = road_path((0.5, 0.5), (5.5, 0.5), (10.5, 0.5))
    assert np.allclose(straight[:, 1], 0.5)


def _vanilla() -> tuple[bytes, list[str]]:
    keys = ["a", "b", "c", "d"]
    places = {1: (10.5, 10.5), 2: (30.5, 10.5), 3: (30.5, 30.5), 4: (50.5, 30.5)}

    def road(low: int, high: int, inner: tuple[float, float]) -> NewStrip:
        return NewStrip(low, high, np.array([places[low], inner, places[high]], dtype=np.float32))

    roads = [road(1, 2, (20.0, 12.0)), road(2, 3, (31.0, 20.0)), road(3, 4, (40.0, 31.0))]
    return serialize(rebuild(EMPTY, {}, places, roads)), keys


MOD_KEYS = ["a", "g1", "c", "d", "g2"]  # b is gone, g1 is new at 2, c and d move up, g2 is new at 5
CONTACTS = {("a", "g1"): (20.5, 10.5), ("c", "g1"): (21.5, 20.5), ("c", "g2"): (35.5, 31.5)}
ANCHORS = {"g1": (20.5, 18.5), "g2": (40.5, 36.5)}


def _build() -> tuple[bytes, bytes, dict[str, object]]:
    vanilla, keys = _vanilla()
    data, stats = build_splines(
        vanilla, vanilla_keys=keys, mod_keys=MOD_KEYS, contacts=CONTACTS, anchors=ANCHORS
    )
    return data, vanilla, stats


def test_the_mods_network_keeps_old_strips_drops_lost_ones_and_roads_every_contact() -> None:
    """Locations that are gone take their strips along; every contact of a new one gets a strip."""
    data, vanilla, stats = _build()
    network = parse(data)
    assert network.anchors.tolist() == [1, 2, 3, 4, 5]
    assert sorted(network.strips) == sorted(
        [strip_id(1, 2), strip_id(2, 3), strip_id(3, 5), strip_id(3, 4)]
    )
    assert stats["strips_added"] == 3
    assert stats["anchors_added"] == 2
    assert (
        polyline(network, strip_id(3, 4)).tolist()
        == polyline(parse(vanilla), strip_id(3, 4)).tolist()
    )
    assert polyline(network, strip_id(1, 2))[0].tolist() == [10.5, 10.5]
    assert polyline(network, strip_id(1, 2))[-1].tolist() == list(ANCHORS["g1"])
    assert data == _build()[0]


def _problems(data: bytes, vanilla: bytes, roads: list[tuple[str, str]]) -> list[str]:
    keys = ["a", "b", "c", "d"]
    return spline_problems(
        data,
        vanilla,
        vanilla_keys=keys,
        mod_keys=MOD_KEYS,
        contacts=list(CONTACTS),
        roads=roads,
    )


def test_the_check_accepts_the_built_network_and_names_what_is_missing() -> None:
    """A good file has no problems; a missing contact, road or vanilla strip is named."""
    data, vanilla, _ = _build()
    assert _problems(data, vanilla, [("c", "d"), ("a", "g1")]) == []
    assert _problems(data, vanilla, [("g1", "g2")]) == ["The road g1 = g2 has no strip"]
    network = parse(data)
    without = rebuild(network, {i: i for i in range(1, 6)} | {}, {}, [])
    assert without.strips == network.strips
    fewer = rebuild(network, {1: 1, 2: 2, 3: 3, 5: 5}, {}, [])  # location 4 (d) loses its strips
    problems = _problems(serialize(fewer), vanilla, [])
    assert any("vanilla strips" in problem for problem in problems)
    extra = rebuild(
        network,
        {i: i for i in range(1, 6)},
        {},
        [NewStrip(1, 5, np.array([(10.5, 10.5), (40.5, 36.5)], dtype=np.float32))],
    )
    assert any("neither" in problem for problem in _problems(serialize(extra), vanilla, []))
    assert _problems(b"not a network", vanilla, []) != []


def test_a_contact_without_an_anchor_or_in_no_location_stops_the_build() -> None:
    """A generated location needs a position for its anchor; every key must be a location."""
    vanilla, keys = _vanilla()
    with pytest.raises(SplineError, match="no anchor"):
        _ = build_splines(
            vanilla,
            vanilla_keys=keys,
            mod_keys=MOD_KEYS,
            contacts=CONTACTS,
            anchors={"g1": ANCHORS["g1"]},
        )
    with pytest.raises(SplineError, match="no location"):
        _ = build_splines(
            vanilla,
            vanilla_keys=keys,
            mod_keys=MOD_KEYS,
            contacts={("a", "nowhere"): (1.0, 1.0)},
            anchors=ANCHORS,
        )
