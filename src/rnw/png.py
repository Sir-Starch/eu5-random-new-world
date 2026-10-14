"""A small deterministic PNG writer and chunk reader.

Rows use filter type 2 (Up). ``stored`` compression emits uncompressed deflate blocks,
so its bytes are fully specified by this module on every platform. ``zlib`` uses the
runtime zlib at a fixed level; its bytes are reproducible for the same zlib build, while
the decoded pixels are always identical. Callers record which mode they used.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import struct
import zlib
from typing import TYPE_CHECKING, Final, Literal

import numpy as np

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
STORED_BLOCK: Final[int] = 65_535
IDAT_SIZE: Final[int] = 1 << 20
ZLIB_LEVEL: Final[int] = 6
FILTER_UP: Final[int] = 2
COLOR_GRAY: Final[int] = 0
COLOR_RGB: Final[int] = 2
COLOR_PALETTE: Final[int] = 3
PRESERVED_CHUNKS: Final[frozenset[bytes]] = frozenset(
    {b"cHRM", b"gAMA", b"sRGB", b"pHYs", b"PLTE", b"tRNS"}
)
Compression = Literal["stored", "zlib"]


class PngFormatError(ValueError):
    """Input bytes are not a PNG this module can read."""


def _chunk(kind: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(kind + data) & 0xFFFF_FFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def _stored_deflate(raw: bytes) -> bytes:
    """Wrap bytes in a zlib stream of uncompressed deflate blocks."""
    parts = [b"\x78\x01"]
    blocks = range(0, max(len(raw), 1), STORED_BLOCK)
    for start in blocks:
        block = raw[start : start + STORED_BLOCK]
        final = 1 if start + STORED_BLOCK >= len(raw) else 0
        size = len(block)
        parts.append(struct.pack("<BHH", final, size, size ^ 0xFFFF) + block)
    parts.append(struct.pack(">I", zlib.adler32(raw) & 0xFFFF_FFFF))
    return b"".join(parts)


def _filtered_rows(rows: NDArray[np.uint8]) -> bytes:
    filtered = np.empty((rows.shape[0], rows.shape[1] + 1), dtype=np.uint8)
    filtered[:, 0] = FILTER_UP
    filtered[0, 1:] = rows[0]
    _ = np.subtract(rows[1:], rows[:-1], out=filtered[1:, 1:])
    return filtered.tobytes()


def encode_png(
    pixels: NDArray[np.uint8],
    *,
    color_type: int,
    compression: Compression,
    extra_chunks: tuple[tuple[bytes, bytes], ...] = (),
) -> bytes:
    """Encode 8-bit gray/palette ``(h, w)`` or RGB ``(h, w, 3)`` pixels.

    ``extra_chunks`` are written verbatim before IDAT in the given order, for example a
    palette or colour-space chunk copied from the source image.
    """
    if pixels.dtype != np.uint8:
        message = "PNG pixels must be uint8"
        raise PngFormatError(message)
    channels = 3 if color_type == COLOR_RGB else 1
    expected_ndim = 3 if channels == 3 else 2  # noqa: PLR2004 - RGB has three channels.
    if pixels.ndim != expected_ndim or (channels == 3 and pixels.shape[2] != 3):  # noqa: PLR2004
        message = "Pixel array shape does not match the PNG colour type"
        raise PngFormatError(message)
    height, width = int(pixels.shape[0]), int(pixels.shape[1])
    if height == 0 or width == 0:
        message = "PNG dimensions must be positive"
        raise PngFormatError(message)
    raw = _filtered_rows(np.ascontiguousarray(pixels).reshape(height, width * channels))
    payload = _stored_deflate(raw) if compression == "stored" else zlib.compress(raw, ZLIB_LEVEL)
    header = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    parts = [SIGNATURE, _chunk(b"IHDR", header)]
    parts.extend(_chunk(kind, data) for kind, data in extra_chunks)
    parts.extend(
        _chunk(b"IDAT", payload[start : start + IDAT_SIZE])
        for start in range(0, len(payload), IDAT_SIZE)
    )
    parts.append(_chunk(b"IEND", b""))
    return b"".join(parts)


def read_chunks(path: Path) -> tuple[tuple[bytes, bytes], ...]:
    """Return the colour/palette/density chunks that precede IDAT, in file order."""
    found: list[tuple[bytes, bytes]] = []
    with path.open("rb") as stream:
        if stream.read(len(SIGNATURE)) != SIGNATURE:
            message = f"Not a PNG file: {path.name}"
            raise PngFormatError(message)
        while header := stream.read(8):
            length, kind = struct.unpack(">I4s", header)
            if kind == b"IDAT":
                break
            data = stream.read(length)
            _ = stream.read(4)
            if kind in PRESERVED_CHUNKS:
                found.append((kind, data))
    return tuple(found)
