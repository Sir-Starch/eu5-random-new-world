"""Localization keys whose hashes cannot collide.

EU5 identifies localization keys by their 32-bit MurmurHash3 (x86, seed 0) and logs a
collision when two keys share a hash [V-EXEC C89]. With about 315,000 vanilla keys and
11,000 generated ones a build expects about one collision by chance, so generated keys
are handed out by a ``KeySpace`` that knows every hash already taken.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rnw import _native

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


def murmur3_32(data: bytes, seed: int = 0) -> int:
    """MurmurHash3 x86_32 of ``data``."""
    return _native.murmur3(data, seed & 0xFFFFFFFF)


def key_hash(key: str) -> int:
    """The engine's hash of a localization key."""
    return murmur3_32(key.encode("utf-8"))


def key_hashes(keys: Iterable[str]) -> set[int]:
    """Hashes of ``keys``."""
    return set(_native.key_hashes(list(keys)))


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

    def holds(self, keys: Sequence[str]) -> bool:
        """Whether the hashes of all of ``keys`` are already taken (reserved static keys)."""
        return all(key_hash(key) in self._hashes for key in keys)

    def group(self, prefix: str, suffixes: Sequence[str]) -> str:
        """The next ``prefix`` + number whose keys with every one of ``suffixes`` are all free,
        claimed together: a formable's key and its description, a mission and its tasks."""
        serial = self._serials.get(prefix, 0)
        while True:
            serial += 1
            base = f"{prefix}{serial}"
            if self.claim(tuple(base + suffix for suffix in suffixes)):
                self._serials[prefix] = serial
                return base

    def next(self, prefix: str, width: int) -> str:
        """The next serial key ``prefix`` + zero-padded number whose hash is free."""
        serial = self._serials.get(prefix, 0)
        while True:
            serial += 1
            key = f"{prefix}{serial:0{width}d}"
            if self.claim((key,)):
                self._serials[prefix] = serial
                return key
