"""Read an image file of our own making (a world's picture), with no game in the picture.

The viewer reads the pictures a world's export wrote beside it; this is the reader for them. The
game's own rasters are read by ``rnw.eu5_map``, which refuses an unexpected mode or size as a
contract break; a picture of ours is simply decoded to RGB.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np
from PIL import Image

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

MAX_PIXELS: Final[int] = 64_000_000


def read_rgb(path: Path) -> NDArray[np.uint8]:
    """The picture at ``path`` as height x width x 3 pixels; raises ``ValueError`` when it is too
    large, ``OSError`` when it cannot be read."""
    with Image.open(path) as image:
        if image.width * image.height > MAX_PIXELS:
            message = f"{path.name} is larger than a picture of a world may be"
            raise ValueError(message)
        return np.array(image.convert("RGB"), dtype=np.uint8)
