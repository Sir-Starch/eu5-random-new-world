"""Relief, climate, biome, material-slot and vegetation-instance models (synthetic data)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from rnw.climate import RainSettings, rainfall
from rnw.eu5_biomes import (
    biome_of,
    biome_rules,
    knn_scores,
    label_statistics,
    latitude_tenths,
    material_counts,
    smooth_scores,
    template_attributes,
)
from rnw.eu5_objects import budget_scale, rewrite_inline, sample_instances
from rnw.eu5_slots import (
    COAST_TRANSITION,
    NO_MATERIAL,
    VARIATION,
    VEGETATION_BORDER,
    SlotTables,
    level_counts,
    slot_remap,
    synthesize,
)
from rnw.fields import block_mean, smoothstep, upsample, warped_noise
from rnw.relief import COAST_HEIGHT, generate_relief
from rnw.topology import euclidean_distance, nearest_label

if TYPE_CHECKING:
    from pathlib import Path

RAIN = RainSettings(decay_px=200, recharge_px=10, lift_units=40000, blur_px=1, relief_blur_px=1)


def test_upsample_reproduces_linear_fields_and_block_mean_averages() -> None:
    """Bilinear interpolation is exact on a linear ramp; block means average blocks."""
    coarse = np.arange(5, dtype=np.int64)[np.newaxis, :].repeat(3, axis=0) * 8
    fine = upsample(coarse, 4, (8, 16))
    assert fine[0].tolist() == [2 * x for x in range(16)]
    assert block_mean(np.arange(16, dtype=np.int64).reshape(4, 4), 2).tolist() == [
        [2, 4],
        [10, 12],
    ]
    assert smoothstep(np.array([-5, 0, 50, 100, 200]), 0, 100).tolist() == [0, 0, 500, 1000, 1000]


def test_warped_noise_is_deterministic_and_bounded() -> None:
    """Equal keys give equal fields; values stay inside the noise range."""
    first = warped_noise(7, (40, 60), step=4, period=32, octaves=3, warp_px=12)
    second = warped_noise(7, (40, 60), step=4, period=32, octaves=3, warp_px=12)
    assert first.shape == (40, 60)
    assert np.array_equal(first, second)
    assert int(np.abs(first).max()) <= 1 << 15
    assert not np.array_equal(first, warped_noise(8, (40, 60), step=4, period=32, octaves=3,
                                                  warp_px=12))  # fmt: skip


def test_euclidean_distance_matches_brute_force() -> None:
    """The separable transform equals the exact distance to the nearest source."""
    rng = np.random.default_rng(3)
    sources = rng.random((23, 31)) < 0.05
    sources[0, 0] = True
    got = euclidean_distance(sources, 40)
    points = np.argwhere(sources)
    rows, columns = np.indices(sources.shape)
    best = np.full(sources.shape, 1 << 40, dtype=np.int64)
    for row, column in points.tolist():
        best = np.minimum(best, (rows - row) ** 2 + (columns - column) ** 2)
    exact = np.sqrt(best.astype(np.float64))
    assert np.array_equal(got, np.floor(exact * 8).astype(np.int64))


def test_nearest_label_spreads_lowest_neighbour_first() -> None:
    """Labels spread step by step; ties go to the lower-index neighbour."""
    labels = np.array([[1, -1, 2]], dtype=np.int32)
    out = nearest_label(labels, labels >= 0, 2)
    assert out.tolist() == [[1, 1, 2]]
    far = nearest_label(
        np.array([[5, -1, -1, -1]], dtype=np.int32), np.array([[1, 0, 0, 0]]) > 0, 2
    )
    assert far.tolist() == [[5, 5, 5, -1]]


def test_rainfall_has_a_rain_shadow_behind_a_range() -> None:
    """Westerly air rains out on the windward slope; the lee is drier than the coast."""
    sea = np.zeros((4, 60), dtype=bool)
    sea[:, :10] = True
    height = np.full((4, 60), 6000, dtype=np.int64)
    height[:, 25:30] = np.arange(5)[np.newaxis, :] * 4000 + 8000
    westerly = np.full(4, 450, dtype=np.int64)
    rain = rainfall(sea, height, westerly, RAIN)
    assert rain[1, 27] > rain[1, 12]
    assert rain[1, 40] < rain[1, 12]
    assert rain[1, 5] == 0


def test_relief_is_deterministic_and_starts_at_the_coast() -> None:
    """Relief is zero on water, at least the coast height on land and seed-stable."""
    land = np.zeros((96, 128), dtype=bool)
    land[16:80, 20:110] = True
    first = generate_relief(land, seed=5)
    assert np.array_equal(first, generate_relief(land, seed=5))
    assert np.all(first[~land] == 0)
    assert int(first[land].min()) >= COAST_HEIGHT
    assert int(first[48, 64]) > int(first[17, 64])


def test_latitude_follows_anchors_and_is_symmetric() -> None:
    """The equator row is 0 degrees; rows mirror around it."""
    rows = np.array([4839, 4839 - 1689, 4839 + 1689, 4839 - 3029])
    assert latitude_tenths(rows).tolist() == [0, 300, 300, 515]


def test_knn_votes_rank_weighted_and_smoothing_spreads_majority() -> None:
    """Nearer rows weigh more; graph smoothing pulls an outlier to its neighbours."""
    train = np.array([[0], [1], [10], [11], [12]], dtype=np.int64)
    classes = np.array([0, 0, 1, 1, 1], dtype=np.int64)
    scores = knn_scores(train, classes, np.array([[0], [11]], dtype=np.int64), 2)
    assert np.argmax(scores, axis=1).tolist() == [0, 1]
    chain = np.array([[10, 0], [0, 10], [10, 0], [10, 0]], dtype=np.int64)
    edges = np.array([[0, 1], [1, 2], [2, 3]], dtype=np.int64)
    smoothed = smooth_scores(chain, edges, 2)
    assert np.argmax(smoothed, axis=1).tolist() == [0, 0, 0, 0]


def test_label_statistics_measure_regions() -> None:
    """Same-label edges and connected regions are counted on the graph."""
    edges = np.array([[0, 1], [1, 2], [2, 3]], dtype=np.int64)
    stats = label_statistics(["a", "a", "b", "a"], edges)
    assert stats["regions"] == 3
    assert stats["same_label_edges_permille"] == 333
    assert stats["singleton_regions_permille"] == 666


def test_template_attributes_read_one_line_templates() -> None:
    """Climate, vegetation, topography and raw material are read per key."""
    text = (
        "a = { topography = hills vegetation = forest climate = oceanic raw_material = fish }\n"
        "b = { topography = ocean climate = arctic}\n"
    )
    attributes = template_attributes(text)
    assert attributes["a"]["vegetation"] == "forest"
    assert attributes["b"] == {"topography": "ocean", "climate": "arctic"}


def _island() -> tuple[np.ndarray, SlotTables]:
    labels = np.zeros((80, 80), dtype=np.int32)
    labels[10:70, 10:40] = 1
    labels[10:70, 40:70] = 2
    tables = SlotTables(
        water=np.array([True, False, False]),
        coast_slot=np.array([0, 1, 1], dtype=np.int64),
        topography=np.array([0, 1, 1], dtype=np.int64),
        vegetation=np.array([0, 1, 2], dtype=np.int64),
        climate=np.array([0, 1, 1], dtype=np.int64),
        level_one=np.array([0, 1000, 300], dtype=np.int64),
        level_two=np.array([0, 0, 500], dtype=np.int64),
        materials=np.array([16, 16, 16], dtype=np.int64),
    )
    return labels, tables


def test_slot_rules_mark_coast_borders_and_variations() -> None:
    """Shores get coast slots, a vegetation change gets a band, interiors vary."""
    labels, tables = _island()
    land = labels > 0
    rivers = np.zeros(labels.shape, dtype=bool)
    slots = synthesize(labels, land, rivers, tables, seed=1, origin=(0, 0))
    assert np.array_equal(slots, synthesize(labels, land, rivers, tables, seed=1, origin=(0, 0)))
    assert slots[0, 0] == NO_MATERIAL
    assert slots[40, 10] == 1
    assert slots[40, 13] in {COAST_TRANSITION, 1}
    assert slots[40, 40] == VEGETATION_BORDER
    left = slots[25:55, 22:34]
    assert set(np.unique(left).tolist()) <= {VARIATION, VARIATION + 3}
    right = slots[25:55, 48:60]
    levels = {(slot - VARIATION) % 3 for slot in np.unique(right).tolist() if slot >= VARIATION}
    assert levels == {0, 1, 2}


def test_short_material_lists_get_only_listed_slots() -> None:
    """A biome with 13 materials keeps its slots; missing variations reuse family one."""
    remap = slot_remap()
    assert remap[13].tolist() == [*range(13), 10, 11, 12]
    assert remap[12].tolist()[10:] == [10, 11, 11, 10, 11, 11]
    assert remap[1].tolist() == [0] * 16
    assert remap[16].tolist() == list(range(16))
    labels, tables = _island()
    short = replace(tables, materials=np.array([16, 16, 13], dtype=np.int64))
    land = labels > 0
    rivers = np.zeros(labels.shape, dtype=bool)
    full = synthesize(labels, land, rivers, tables, seed=1, origin=(0, 0))
    slots = synthesize(labels, land, rivers, short, seed=1, origin=(0, 0))
    right = labels == 2
    assert int(slots[right].max()) <= 12
    assert np.array_equal(slots[~right], full[~right])
    assert np.any(full[right] >= 13)


BIOMES_TEXT = """# comment = { biome = no }
000 = { biome = default_biome }
001 = {
 climate = arid climate = hot_semi_arid # both
 vegetation = desert biome = dry
}
002 = { climate = arid vegetation = desert topography = hills biome = dry_hills }
"""
MATERIALS_TEXT = """materials = { { name = "x" diffuse = "a.dds" }
{ name = dry materials = {
 a # coast
 b c } }
{ name = dry_hills materials = { a } } }
"""


def test_biome_rules_pick_the_most_specific_match() -> None:
    """Rules with more named attributes win; unlisted values fall back to the default."""
    rules = biome_rules(BIOMES_TEXT)
    assert [rule.biome for rule in rules] == ["default_biome", "dry", "dry_hills"]
    assert biome_of(rules, "hot_semi_arid", "desert", "hills") == "dry"
    assert biome_of(rules, "arid", "desert", "hills") == "dry_hills"
    assert biome_of(rules, "arctic", "forest", "flatland") == "default_biome"
    assert material_counts(MATERIALS_TEXT) == {"dry": 3, "dry_hills": 1}


def test_level_counts_skip_borders() -> None:
    """Only pixels far from every location border are counted."""
    labels = np.zeros((20, 20), dtype=np.int32)
    labels[:, 10:] = 1
    materials = np.full((40, 40), VARIATION + 1, dtype=np.int64)
    counts = level_counts(materials, labels, np.array([0, 1], dtype=np.int64), 2)
    assert counts[:, 1].sum() > 0
    assert counts[:, 0].sum() == 0
    interior = (40 - 2 * 6) * ((20 - 6) - 6)
    assert counts.sum() == interior * 2


def test_instance_sampling_matches_density() -> None:
    """Expected instance count equals the fixed-point density; donors supply transforms."""
    rows, columns = np.nonzero(np.ones((100, 100), dtype=bool))
    density = np.full(rows.size, 1 << 22, dtype=np.int64)  # a quarter per pixel
    source = np.array([[0, 0, 0, 0, 0.5, 0, 0.866, 0.8, 0.8, 0.8]], dtype=np.float32)
    out = sample_instances(rows, columns, density=density, source=source, rows=50, key=9)
    assert abs(out.shape[0] - 2500) < 200
    assert np.all(out[:, 4] == np.float32(0.5))
    assert np.all((out[:, 0] >= 0) & (out[:, 0] < 50))
    assert np.all((out[:, 2] > 0) & (out[:, 2] <= 50))


def test_inline_instances_are_rewritten_in_place(tmp_path: Path) -> None:
    """Counts and transform blocks change only for the named object."""
    path = tmp_path / "objects.txt"
    first = 'object={\n\tname="a"\n\tcount=1\n\ttransform="1.000000 0.000000 2.000000'
    second = 'object={\n\tname="b"\n\tcount=1\n\ttransform="3 0 4 0 0 0 1 1 1 1\n"}\n'
    _ = path.write_text(
        f'{first} 0 0 0 1 1 1 1\n"}}\n{second}',
        encoding="utf-8",
    )
    values = np.array([[5, 0, 6, 0, 0, 0, 1, 1, 1, 1], [7, 0, 8, 0, 0, 0, 1, 1, 1, 1]], np.float32)
    text = rewrite_inline(path, {"a": values}).decode("utf-8")
    assert "count=2" in text
    assert "5.000000 0.000000 6.000000" in text
    assert 'transform="3 0 4 0 0 0 1 1 1 1\n"}' in text


def test_density_scale_keeps_new_instances_within_the_budget() -> None:
    """Expected instances are the pixel counts times the key densities; the scale is at most 1."""
    one = 1 << 24
    fine = np.array([2 * one, 0], dtype=np.int64)  # two instances per pixel
    coarse = np.array([0, one], dtype=np.int64)  # one instance per pixel
    tables = [(fine, coarse)]
    fine_pixels = np.array([100, 0], dtype=np.int64)
    coarse_pixels = np.array([0, 50], dtype=np.int64)  # 100 * 2 + 50 * 1 = 250 expected
    assert budget_scale(tables, fine_pixels, coarse_pixels, 500) == one
    assert budget_scale(tables, fine_pixels, coarse_pixels, 250) == one
    assert budget_scale(tables, fine_pixels, coarse_pixels, 125) == one // 2
    assert budget_scale(tables, fine_pixels, coarse_pixels, 0) == 0
    assert budget_scale([], fine_pixels, coarse_pixels, 10) == one
