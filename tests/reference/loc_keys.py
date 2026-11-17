"""Original scalar localization hash, retained as the equality oracle."""

from typing import Final

MASK: Final[int] = 0xFFFFFFFF
C1: Final[int] = 0xCC9E2D51
C2: Final[int] = 0x1B873593


def _rotl(value: int, shift: int) -> int:
    return ((value << shift) | (value >> (32 - shift))) & MASK


def murmur3_32(data: bytes, seed: int = 0) -> int:
    """MurmurHash3 x86_32 of ``data``."""
    length = len(data)
    hashed = seed & MASK
    tail_start = length - length % 4
    for start in range(0, tail_start, 4):
        block = int.from_bytes(data[start : start + 4], "little")
        block = _rotl(block * C1 & MASK, 15) * C2 & MASK
        hashed = (_rotl(hashed ^ block, 13) * 5 + 0xE6546B64) & MASK
    tail = int.from_bytes(data[tail_start:], "little")
    if length % 4:
        hashed ^= _rotl(tail * C1 & MASK, 15) * C2 & MASK
    hashed ^= length
    hashed = (hashed ^ (hashed >> 16)) * 0x85EBCA6B & MASK
    hashed = (hashed ^ (hashed >> 13)) * 0xC2B2AE35 & MASK
    return hashed ^ (hashed >> 16)
