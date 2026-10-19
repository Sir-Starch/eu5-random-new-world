"""Seeded, pronounceable place names built from syllables (no real-world name lists)."""

from __future__ import annotations

import unicodedata
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


def name_key(name: str) -> str:
    """Comparison key of a name: accents dropped, case folded."""
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


MARKOV_ORDER: Final[int] = 3
MARKOV_TRIES: Final[int] = 40
NAME_LENGTH: Final[tuple[int, int]] = (4, 14)
START: Final[str] = "\x02"
END: Final[str] = "\x03"


class MarkovNames:
    """Names drawn from a character Markov chain over a corpus of place names.

    Contexts are the previous ``MARKOV_ORDER`` characters; counts are kept in insertion
    order of a sorted corpus, so draws depend only on the corpus and the seed. A name
    must be new (not in the corpus, the reserved set or earlier draws) and 4 to 14
    characters long; after ``MARKOV_TRIES`` misses the syllable generator answers.
    """

    __slots__: tuple[str, ...] = ("_fallback", "_next", "_rng", "_used")

    def __init__(
        self, corpus: list[str], seed: int, stream: str, used: set[str] | None = None
    ) -> None:
        self._rng: SplitMix64 = SplitMix64(derive_seed(seed, "names", "markov", stream))
        self._used: set[str] = used if used is not None else set()
        self._used.update(name_key(name) for name in corpus)
        self._next: dict[str, list[tuple[str, int]]] = {}
        counts: dict[str, dict[str, int]] = {}
        for name in sorted(set(corpus)):
            padded = START * MARKOV_ORDER + name + END
            for index in range(MARKOV_ORDER, len(padded)):
                context = padded[index - MARKOV_ORDER : index]
                options = counts.setdefault(context, {})
                options[padded[index]] = options.get(padded[index], 0) + 1
        for context, options in counts.items():
            self._next[context] = sorted(options.items())
        self._fallback: NameGenerator = NameGenerator(seed, f"markov_{stream}")

    def _draw(self) -> str:
        context = START * MARKOV_ORDER
        out: list[str] = []
        while len(out) <= NAME_LENGTH[1]:
            options = self._next.get(context)
            if not options:
                break
            total = sum(count for _, count in options)
            pick = self._rng.below(total)
            char = END
            for option, count in options:
                if pick < count:
                    char = option
                    break
                pick -= count
            if char == END:
                return "".join(out)
            out.append(char)
            context = context[1:] + char
        return ""

    def next(self) -> str:
        """Return a new name; shared ``used`` sets keep several generators distinct."""
        for _ in range(MARKOV_TRIES):
            word = self._draw().strip()
            low, high = NAME_LENGTH
            if low <= len(word) <= high and name_key(word) not in self._used:
                self._used.add(name_key(word))
                return word[0].upper() + word[1:]
        while True:
            word = self._fallback.next()
            if name_key(word) not in self._used:
                self._used.add(name_key(word))
                return word
