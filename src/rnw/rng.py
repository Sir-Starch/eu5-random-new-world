"""Versioned, explicitly specified integer pseudo-random numbers.

RNG v1 is SplitMix64 (Steele, Lea and Flood, 2014) with the constants below. Named
streams are derived from the user seed with SHA-256, so adding a stream never shifts
another stream. Lattice hashing is counter-based, therefore independent of iteration
order. No global, hash-seeded or platform-dependent state is used.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Final

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

RNG_VERSION: Final[str] = "splitmix64-v1"
SEED_LIMIT: Final[int] = 1 << 64
MASK64: Final[int] = SEED_LIMIT - 1
GAMMA: Final[int] = 0x9E37_79B9_7F4A_7C15
MUL1: Final[int] = 0xBF58_476D_1CE4_E5B9
MUL2: Final[int] = 0x94D0_49BB_1331_11EB
X_MUL: Final[int] = 0xD6E8_FEB8_6659_FD93
Y_MUL: Final[int] = 0xA076_1D64_78BD_642F


class SeedRangeError(ValueError):
    """A seed is outside the unsigned 64-bit range."""

    def __init__(self, seed: int) -> None:
        super().__init__(f"Seed must be in [0, 2**64): {seed}")


def check_seed(seed: int) -> int:
    """Return a valid unsigned 64-bit seed or raise."""
    if not 0 <= seed < SEED_LIMIT:
        raise SeedRangeError(seed)
    return seed


def mix64(value: int) -> int:
    """Apply the SplitMix64 output function to one 64-bit value."""
    z = value & MASK64
    z = ((z ^ (z >> 30)) * MUL1) & MASK64
    z = ((z ^ (z >> 27)) * MUL2) & MASK64
    return z ^ (z >> 31)


def derive_seed(seed: int, *labels: str) -> int:
    """Derive an independent 64-bit stream key from a seed and a label path."""
    payload = "\x1f".join((RNG_VERSION, str(check_seed(seed)), *labels)).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "little")


class SplitMix64:
    """Sequential SplitMix64 generator with unbiased bounded draws."""

    __slots__: tuple[str, ...] = ("_state",)

    def __init__(self, seed: int) -> None:
        self._state: int = check_seed(seed)

    def next_u64(self) -> int:
        """Advance once and return a 64-bit unsigned value."""
        self._state = (self._state + GAMMA) & MASK64
        return mix64(self._state)

    def below(self, bound: int) -> int:
        """Return a uniform integer in [0, bound) by rejection sampling."""
        if bound <= 0:
            message = "bound must be positive"
            raise ValueError(message)
        limit = SEED_LIMIT - SEED_LIMIT % bound
        while True:
            value = self.next_u64()
            if value < limit:
                return value % bound


def hash_grid(key: int, xs: NDArray[np.int64], ys: NDArray[np.int64]) -> NDArray[np.uint64]:
    """Hash broadcast integer lattice coordinates to 64-bit values.

    Equivalent to ``mix64(key ^ (x * X_MUL) ^ (y * Y_MUL) + GAMMA)`` modulo 2**64 for
    each coordinate pair; unsigned NumPy arithmetic wraps by definition.
    """
    with np.errstate(over="ignore"):
        z = (
            np.uint64(key & MASK64)
            ^ (xs.astype(np.uint64) * np.uint64(X_MUL))
            ^ (ys.astype(np.uint64) * np.uint64(Y_MUL))
        )
        z = z + np.uint64(GAMMA)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(MUL1)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(MUL2)
        return z ^ (z >> np.uint64(31))


def hash_point(key: int, x: int, y: int) -> int:
    """Pure-Python reference for one ``hash_grid`` value."""
    return mix64(((key ^ ((x * X_MUL) & MASK64) ^ ((y * Y_MUL) & MASK64)) + GAMMA) & MASK64)
