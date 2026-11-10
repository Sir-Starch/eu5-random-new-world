"""The algorithm epoch: which releases make the same world from the same code (ADR 0010, G).

A world code names the release that made it, but most releases change the window, the packaging
or the text and nothing a world is made of. The epoch says what matters: **two frozen releases
of the same epoch make byte-identical mods from the same settings, seed and game files**, apart from
mod's ``.metadata`` (its title, version and picture), which is presentation and is written anew.

``ALGORITHM_SINCE`` lists the first release of every epoch. A release before the first entry is
epoch 0: made before epochs were recorded, so nothing is promised about it. The rule for whoever
changes the generator:

* A change that alters any file of a world's mod other than ``.metadata`` (the land, the peoples,
  the texts, the cover's shaders, a preset's values, the order of a random stream) is a new epoch:
  append an entry for the cycle's target release, or refresh its existing pending epoch
  reference, in the same change. Never change a frozen release's entry.
* The epochs from ``OLDEST_SELECTABLE`` to the current one stay reachable through the experimental
  features (ADR 0013). A new epoch therefore keeps the behaviour it replaces behind a named switch
  below (``settings.algorithm >= SWITCH``), unless the difference is too costly to keep, and then
  raises ``OLDEST_SELECTABLE`` past the epoch it drops. The epoch it follows needs its frozen
  reference world (``tests/golden_world_epoch<N>.json``), and a test checks that it exists.
* A change that alters none (the window, the packaging, a picture, the metadata, speed that
  proves equal bytes) is not.
* Ordinary commits keep the cycle's target version (ADR 0003). Output changes within a cycle
  may refine one pending epoch and its reference before its tag is frozen. Frozen epochs and
  goldens never change. Reproduction promises apply to frozen releases; development builds
  additionally need their exact source commit and inputs.

CI cannot make the game's files, so it cannot see a change of the real export; it does pin the
presets (``tests/test_epoch.py``) and the synthetic world's bytes, and a player or a developer with
the game checks the reference world (``tests/golden_world.json``) with ``rnw verify-world``.
"""

from __future__ import annotations

import re
from typing import Final

from rnw import __version__

Release = tuple[int, int, int]

# The first release of each epoch, in order; epoch numbers are 1, 2, 3, ... with no gaps.
ALGORITHM_SINCE: Final[tuple[Release, ...]] = (
    (0, 9, 20),
    (0, 9, 26),
    (0, 9, 27),
    (0, 9, 28),
    (0, 9, 29),
    (0, 9, 30),
    (0, 9, 31),
    (0, 9, 32),
    (0, 9, 33),
    (0, 10, 0),
    (0, 10, 1),
    (0, 10, 2),
    (0, 10, 3),
    (0, 10, 4),
    (0, 10, 5),
    (0, 10, 6),
    (0, 10, 7),
    (0, 10, 8),
    (0, 10, 9),
    (0, 10, 10),
    (0, 10, 11),
    (0, 10, 12),
    (0, 10, 13),
    (0, 10, 14),
    (0, 11, 1),
    (0, 11, 2),
    (0, 11, 3),
    (0, 11, 4),
    (0, 11, 5),
    (0, 12, 0),
    (0, 12, 1),
    (0, 12, 2),
    (0, 12, 3),
    (0, 12, 4),
    (0, 12, 5),
    (0, 12, 6),
    (0, 12, 7),
    (0, 12, 8),
    (0, 12, 9),
    (0, 13, 1),
    (0, 13, 2),
    (0, 13, 5),
    (0, 13, 6),
    (0, 13, 7),
    (0, 13, 8),
    (0, 13, 9),
    (0, 13, 10),
    (0, 13, 11),
    (0, 13, 12),
    (0, 13, 13),
    (0, 13, 14),
    (0, 13, 15),
    (0, 13, 16),
    (0, 13, 17),
    (0, 13, 18),
    (0, 13, 19),
    (0, 13, 20),
    (0, 13, 21),
    (0, 13, 22),
    (1, 1, 0),  # Resources, geography, populations and identity-aware state cores.
    (1, 2, 0),  # Causal prehistory, final start, closed-basin water and the Omerika world type.
    (1, 2, 1),  # Market centres only where the calibrated settlement plan puts them.
    (1, 2, 2),  # Subcontinents cut at the waist, with whole islands; smooth drawn coasts.
)


# The oldest epoch the experimental features can still make a world by (ADR 0013). Every epoch
# from here to the current one stays reachable: a change that opens a new epoch keeps the
# previous behaviour behind the switch below, and its frozen reference world proves the old
# path still makes the same bytes. Raising this number drops epochs for good; lowering it needs
# the old behaviour of every epoch in between.
OLDEST_SELECTABLE: Final[int] = 61

# The epoch that began each behaviour a world can still be made without. A generator stage asks
# ``settings.algorithm >= SWITCH`` and keeps the older path in its own words. Append only, and
# never above ``CURRENT``; a switch at or below ``OLDEST_SELECTABLE`` is dead code (a test says so).
NO_EXCHANGE_MARKETS: Final[int] = 62  # 1.2.1: an exchange partner is no market centre of its own.
SUBCONTINENT_WAISTS: Final[int] = 63  # 1.2.2: subcontinents are cut at the land's waist.
SMOOTH_DRAWN_COASTS: Final[int] = 63  # 1.2.2: a small drawing is stretched by a spline, not blocks.
SWITCHES: Final[dict[str, int]] = {
    "NO_EXCHANGE_MARKETS": NO_EXCHANGE_MARKETS,
    "SUBCONTINENT_WAISTS": SUBCONTINENT_WAISTS,
    "SMOOTH_DRAWN_COASTS": SMOOTH_DRAWN_COASTS,
}


class ReleaseError(ValueError):
    """Text that is not a release version (``major.minor.patch``)."""


class EpochError(ValueError):
    """An epoch this generator cannot make a world by."""


def parse(version: str) -> Release:
    """The numbers of a ``major.minor.patch`` release version."""
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if match is None:
        message = f"{version!r} is not a release version (major.minor.patch)"
        raise ReleaseError(message)
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def epoch_of(release: str) -> int:
    """The epoch of the world a release makes: 0 before the first epoch."""
    numbers = parse(release)
    return sum(1 for first in ALGORITHM_SINCE if first <= numbers)


CURRENT: Final[int] = epoch_of(__version__)


def first_release(number: int) -> str:
    """The first release of epoch ``number``, as the text of a version (``1.2.1``)."""
    if not 1 <= number <= len(ALGORITHM_SINCE):
        message = f"There is no epoch {number}; they run from 1 to {len(ALGORITHM_SINCE)}"
        raise EpochError(message)
    return ".".join(str(part) for part in ALGORITHM_SINCE[number - 1])


def selectable() -> tuple[int, ...]:
    """The epochs the experimental features can make a world by, oldest first."""
    return tuple(range(OLDEST_SELECTABLE, CURRENT + 1))


def available(*, experimental: bool) -> tuple[int, ...]:
    """The epochs this generator makes a world by now: the current one, and with the
    experimental features every selectable one."""
    return selectable() if experimental else (CURRENT,)


def require_selectable(number: int) -> int:
    """``number`` if a world can be made by it, else ``EpochError`` in words."""
    if number not in selectable():
        first, last = OLDEST_SELECTABLE, CURRENT
        message = f"Epoch {number} cannot be chosen; this generator makes epochs {first} to {last}"
        raise EpochError(message)
    return number


def stamp_of(number: int) -> str:
    """The release a world code of epoch ``number`` is stamped with: the running release for the
    current epoch, the epoch's first release for an older one, whose generator makes the same
    world (a code names the release that made it)."""
    return __version__ if require_selectable(number) == CURRENT else first_release(number)
