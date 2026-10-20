# Typing of the Rust extension module (native/, ADR 0005).

from numpy import bool_, float32, int32, int64, uint8, uint32
from numpy.typing import NDArray

class LzavError(ValueError): ...

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
def distance_from(sources: NDArray[bool_], limit: int, octagonal: bool) -> NDArray[int32]: ...
def euclidean_distance(sources: NDArray[bool_], limit: int) -> NDArray[int64]: ...
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
