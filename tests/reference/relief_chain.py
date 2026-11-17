"""Original NumPy chain arithmetic; noise generation stays in the caller."""

# pyright: reportAny=false
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from rnw.fields import PERMILLE, box_blur, smoothstep
from rnw.noise import NOISE_SCALE
from rnw.relief import AXIS_WANDER, SLOPE_BLUR, SLOPE_FADE, SLOPE_FLOOR, SLOPE_REACH

if TYPE_CHECKING:
    from numpy.typing import NDArray


def chain(
    axis: NDArray[np.int64],
    wander: NDArray[np.int64],
    width: NDArray[np.int64],
    core: int,
    flank: int,
) -> NDArray[np.int64]:
    reach = SLOPE_REACH
    padded = np.pad(axis, reach, mode="edge")
    dx = (
        (padded[reach:-reach, 2 * reach :] - padded[reach:-reach, : -2 * reach]) * 16 // (2 * reach)
    )
    dy = (
        (padded[2 * reach :, reach:-reach] - padded[: -2 * reach, reach:-reach]) * 16 // (2 * reach)
    )
    del padded
    slope = box_blur(np.sqrt(dx * dx + dy * dy).astype(np.int64), SLOPE_BLUR)
    del dx, dy
    distance = np.abs(axis + wander // AXIS_WANDER) * 256 // np.maximum(slope, SLOPE_FLOOR)
    decisive = smoothstep(slope, *SLOPE_FADE)
    del axis, wander, slope
    scale = PERMILLE + width * PERMILLE // (2 * NOISE_SCALE)
    del width
    inner = np.clip(
        PERMILLE - distance * PERMILLE // np.maximum(core * 16 * scale // PERMILLE, 1), 0, PERMILLE
    )
    outer = np.clip(
        PERMILLE - distance * PERMILLE // np.maximum(flank * 16 * scale // PERMILLE, 1), 0, PERMILLE
    )
    envelope = (
        smoothstep(outer, 0, PERMILLE) * 450 + smoothstep(inner, 0, PERMILLE) * 550
    ) // PERMILLE
    return envelope * decisive // PERMILLE
