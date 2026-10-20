"""Localization keys whose hashes cannot collide.

EU5 identifies localization keys by their 32-bit MurmurHash3 (x86, seed 0) and logs a
collision when two keys share a hash [V-EXEC C89]. With about 315,000 vanilla keys and
11,000 generated ones a build expects about one collision by chance, so generated keys
are handed out by a ``KeySpace`` that knows every hash already taken.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

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


def key_hash(key: str) -> int:
    """The engine's hash of a localization key."""
    return murmur3_32(key.encode("utf-8"))


def key_hashes(keys: Iterable[str]) -> set[int]:
    """Hashes of ``keys``."""
    return {key_hash(key) for key in keys}


class KeySpace:
    """Hashes taken by localization keys; claims new keys only while their hashes are free."""

    def __init__(self, taken: set[int]) -> None:
        self._hashes: set[int] = set(taken)
        self._serials: dict[str, int] = {}

    def claim(self, keys: Sequence[str]) -> bool:
        """Take all of ``keys`` together, or none if any hash is taken or repeats."""
        values = [key_hash(key) for key in keys]
        if len(set(values)) != len(values) or any(value in self._hashes for value in values):
            return False
        self._hashes.update(values)
        return True

    def next(self, prefix: str, width: int) -> str:
        """The next serial key ``prefix`` + zero-padded number whose hash is free."""
        serial = self._serials.get(prefix, 0)
        while True:
            serial += 1
            key = f"{prefix}{serial:0{width}d}"
            if self.claim((key,)):
                self._serials[prefix] = serial
                return key
