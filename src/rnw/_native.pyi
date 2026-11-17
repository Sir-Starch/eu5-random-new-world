# Typing of the Rust extension module (native/, ADR 0005).

from collections.abc import Callable

from numpy import bool_, float32, int8, int32, int64, uint8, uint16, uint32, uint64
from numpy.typing import NDArray

class LzavError(ValueError): ...
class TerrainRangeError(ValueError): ...

class RidgeAccumulator:
    def __init__(self, height: int, width: int, scale: int, gain: int) -> None: ...
    def add(self, noise: NDArray[int64], share: int) -> None: ...
    def finish(self, shares: int) -> NDArray[int64]: ...

def relief_chain(
    axis: NDArray[int64],
    wander: NDArray[int64],
    width: NDArray[int64],
    params: tuple[int, int, int, int, int, int, int, int, int],
) -> NDArray[int64]: ...
def parse_instances(text: str) -> NDArray[float32]: ...
def murmur3(data: bytes, seed: int) -> int: ...
def key_hashes(keys: list[str]) -> list[int]: ...
def lzav_decode(data: bytes, size: int) -> bytes: ...
def value_window(
    key: int, x0: int, y0: int, width: int, height: int, period: int
) -> NDArray[int64]: ...
def fractal_window(
    key: int,
    x0: int,
    y0: int,
    width: int,
    height: int,
    period: int,
    octaves: int,
    persistence_permille: int,
) -> NDArray[int64]: ...
def value_noise_at(
    key: int, xs: NDArray[int64], ys: NDArray[int64], period: int
) -> NDArray[int64]: ...
def fractal_at(
    key: int,
    xs: NDArray[int64],
    ys: NDArray[int64],
    period: int,
    octaves: int,
    persistence_permille: int,
) -> NDArray[int64]: ...
def distance_from(
    sources: NDArray[bool_], limit: int, octagonal: bool, wrap_x: bool = False
) -> NDArray[int32]: ...
def euclidean_distance(sources: NDArray[bool_], limit: int) -> NDArray[int64]: ...
def sea_voronoi(mask: NDArray[bool_], seeds: NDArray[int32]) -> NDArray[int32]: ...
def nearest_rows(train: NDArray[int64], query: NDArray[int64], k: int) -> NDArray[int64]: ...
def nearest_label(
    labels: NDArray[int32], sources: NDArray[bool_], limit: int
) -> NDArray[int32]: ...
def upsample(coarse: NDArray[int64], step: int, height: int, width: int) -> NDArray[int64]: ...
def block_mean(values: NDArray[int64], step: int) -> NDArray[int64]: ...
def box_blur(values: NDArray[int64], radius: int) -> NDArray[int64]: ...
def canvas_pixels(
    labels: NDArray[int32],
    materials: NDArray[uint8],
    canvas: NDArray[bool_],
    fine_classes: NDArray[int64],
    coarse_classes: NDArray[int64],
) -> tuple[NDArray[uint32], NDArray[uint32], NDArray[uint32], NDArray[uint32]]: ...
def canvas_counts(
    labels: NDArray[int32],
    materials: NDArray[uint8],
    canvas: NDArray[bool_],
    fine_classes: NDArray[int64],
    coarse_classes: NDArray[int64],
    use_fine: NDArray[bool_],
    coarse_keys: int,
) -> tuple[NDArray[int64], NDArray[int64]]: ...
def pixel_counts(
    labels: NDArray[int32],
    materials: NDArray[uint8],
    table: NDArray[int64],
    mask: NDArray[bool_],
    keys: int,
) -> NDArray[int64]: ...
def sample_instances(
    rows: NDArray[uint32],
    columns: NDArray[uint32],
    fine_keys: NDArray[uint32],
    coarse_keys: NDArray[uint32],
    use_fine: NDArray[bool_],
    fine: NDArray[int64],
    coarse: NDArray[int64],
    donors: NDArray[float32],
    key: int,
    map_rows: int,
) -> NDArray[float32]: ...
def adjacency_pairs(labels: NDArray[int32], wrap_x: bool, diagonal: bool) -> NDArray[int64]: ...
def adjacency_lengths(labels: NDArray[int32]) -> tuple[NDArray[int64], NDArray[int64]]: ...
def cell_sums(labels: NDArray[int32], elevation: NDArray[int32], count: int) -> NDArray[int64]: ...
def sample_instance_sets(
    rows: NDArray[uint32],
    columns: NDArray[uint32],
    fine_keys: NDArray[uint32],
    coarse_keys: NDArray[uint32],
    use_fine: NDArray[bool_],
    fines: list[NDArray[int64]],
    coarses: list[NDArray[int64]],
    donors: list[NDArray[float32]],
    keys: list[int],
    map_rows: int,
) -> list[NDArray[float32]]: ...
def label_components(labels: NDArray[int32], wrap_x: bool) -> NDArray[int32]: ...
def drainage(
    land: NDArray[bool_], height: NDArray[int64], rain: NDArray[int64], key: int
) -> tuple[NDArray[int64], NDArray[int64]]: ...
def interior_points(
    labels: NDArray[int32], land: NDArray[bool_], interior_limit: int, shore_limit: int
) -> NDArray[int64]: ...
def synthesize_slots(
    labels: NDArray[int32],
    land: NDArray[bool_],
    rivers: NDArray[bool_],
    tables: list[NDArray[int64]],
    water: NDArray[bool_],
    keys: list[int],
    periods: list[int],
    quantiles: list[NDArray[int64]],
    x0: int,
    y0: int,
    remap: NDArray[int64],
    core: tuple[int, int, int, int],
) -> NDArray[uint8]: ...
def lzav_encode(raw: bytes) -> bytes: ...
def configure_threads(threads: int) -> int: ...
def pack_layer(image: NDArray[uint16], sample_bytes: int) -> tuple[list[int], bytes]: ...
def mountain_stamp(
    sources: NDArray[uint16],
    materials: NDArray[uint8],
    placements: NDArray[int64],
    bounds: NDArray[int64],
    rotations: list[tuple[int, int]],
    origin: tuple[int, int],
    shape: tuple[int, int],
    unit: int,
    no_material: int,
) -> tuple[NDArray[int64], NDArray[uint8]]: ...
def read_level0(
    data: bytes, spans: list[tuple[int, int]], shape: tuple[int, int], sample_bytes: int
) -> NDArray[uint16] | NDArray[uint8]: ...
def decal_heights(
    codes: NDArray[int8],
    vanilla_water: NDArray[bool_],
    relief: NDArray[int64],
    keys: tuple[int, int],
    origin: tuple[int, int],
    table: list[tuple[int, int]],
    profile_end: int,
    params: dict[str, int],
    core: tuple[int, int, int, int],
    sampled: bool = False,
) -> tuple[NDArray[bool_], NDArray[bool_], NDArray[int64]]: ...
def grow_labels(
    mask: NDArray[bool_],
    seeds: NDArray[int32],
    speed: NDArray[int64] | None,
    checkpoint: Callable[[], None],
) -> NDArray[int32]: ...
def grade_spacing(
    spacing: NDArray[int64],
    land: NDArray[bool_],
    step: int,
    checkpoint: Callable[[], None],
) -> NDArray[int64]: ...
def throw_seeds(
    xs: NDArray[int64],
    ys: NDArray[int64],
    radius: NDArray[int64],
    smallest: int,
    widest: int,
    columns: int,
    gap: int,
    checkpoint: Callable[[], None],
) -> NDArray[int64]: ...
def label_moments(
    labels: NDArray[int32],
    values: NDArray[int64] | None,
    count: int,
    first: int,
) -> NDArray[int64]: ...
def location_sums(
    labels: NDArray[int32],
    table: NDArray[int64],
    count: int,
    step: int,
    block_columns: int,
    first: int,
) -> tuple[NDArray[int64], NDArray[int64]]: ...
def centre_pixels(labels: NDArray[int32], flat: NDArray[int64]) -> NDArray[int64]: ...
def merge_small(labels: NDArray[int32], minimum: int) -> NDArray[int32]: ...
def water_open_cells(
    image: NDArray[uint8],
    distance: NDArray[uint8],
    reach: int,
    first: int,
    last: int,
) -> NDArray[int64]: ...
def water_profile_sums(
    image: NDArray[uint8],
    distance: NDArray[uint8],
    grid: NDArray[int64],
    reach: int,
    first: int,
    last: int,
) -> NDArray[int64]: ...
def water_render(
    image: NDArray[uint8],
    old: NDArray[uint8],
    new: NDArray[uint8],
    touched: NDArray[bool_],
    table: NDArray[int64],
    grid: NDArray[int64],
    first: int,
    last: int,
    reach: int,
    key: int,
) -> NDArray[uint8]: ...
def strip_bend(
    land: NDArray[bool_],
    values: NDArray[int64],
    start: int,
    stop: int,
    rows: int,
    step: int,
) -> NDArray[int64]: ...
def land_blur(land: NDArray[bool_], values: NDArray[int64], radius: int) -> NDArray[int64]: ...
def block_relief(
    land: NDArray[bool_],
    values: NDArray[int64],
    bend: NDArray[int64] | None,
    blocks: int,
    step: int,
    first: int,
) -> NDArray[int64]: ...
def block_labels(land: NDArray[bool_], step: int) -> tuple[NDArray[int32], NDArray[int64]]: ...
def renumber(labels: NDArray[int32]) -> NDArray[int32]: ...
def format_instances(values: NDArray[float32]) -> str: ...
def coastal_pixels(
    labels: NDArray[int32],
    land: NDArray[bool_],
    sea: NDArray[bool_],
) -> NDArray[int64]: ...
def blend_mountains(
    heights: NDArray[int64],
    inside: NDArray[bool_],
    detail: NDArray[int64],
    laid: NDArray[uint8],
    reach: NDArray[int32],
    limits: tuple[int, int, int],
    no_material: int,
) -> tuple[NDArray[int64], NDArray[uint8]]: ...
def stamp_slots(
    slots: NDArray[uint8],
    stamped: NDArray[uint8],
    labels: NDArray[int32],
    materials: NDArray[int64],
    remap: NDArray[int64],
) -> NDArray[uint8]: ...
def first_pixels32(labels: NDArray[int32]) -> NDArray[int64]: ...
def first_pixels64(labels: NDArray[int64]) -> NDArray[int64]: ...
def first_pixels_u64(labels: NDArray[uint64]) -> NDArray[int64]: ...
