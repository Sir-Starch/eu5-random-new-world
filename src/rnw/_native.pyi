# Typing of the Rust extension module (native/, ADR 0005).

from numpy import bool_, int32, int64
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
