"""Seeded, pronounceable place names built from syllables (no real-world name lists)."""

from __future__ import annotations

from typing import Final

from rnw.rng import SplitMix64, derive_seed

ONSETS: Final[tuple[str, ...]] = (
    "", "", "b", "c", "ch", "d", "g", "h", "k", "l", "m", "n", "p", "q", "r", "s",
    "t", "tl", "ts", "v", "w", "x", "y", "z", "br", "kw", "tz", "hu",
)  # fmt: skip
VOWELS: Final[tuple[str, ...]] = (
    "a", "a", "e", "i", "o", "u", "ai", "au", "ia", "ua", "ei", "oa",
)  # fmt: skip
CODAS: Final[tuple[str, ...]] = ("", "", "", "", "n", "l", "r", "m", "s", "c", "t", "x", "k")
MIN_SYLLABLES: Final[int] = 2
SPREAD: Final[int] = 2


class NameGenerator:
    """Draws unique capitalised names from one named RNG stream."""

    __slots__: tuple[str, ...] = ("_rng", "_used")

    def __init__(self, seed: int, stream: str, reserved: frozenset[str] | None = None) -> None:
        self._rng: SplitMix64 = SplitMix64(derive_seed(seed, "names", stream))
        self._used: set[str] = {name.casefold() for name in reserved or ()}

    def _pick(self, options: tuple[str, ...]) -> str:
        return options[self._rng.below(len(options))]

    def next(self) -> str:
        """Return a new name not produced before by this generator."""
        while True:
            count = MIN_SYLLABLES + self._rng.below(SPREAD)
            word = "".join(
                self._pick(ONSETS) + self._pick(VOWELS) + self._pick(CODAS) for _ in range(count)
            )
            if len(word) >= 4 and word.casefold() not in self._used:  # noqa: PLR2004
                self._used.add(word.casefold())
                return word[0].upper() + word[1:]
