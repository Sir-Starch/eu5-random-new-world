"""The algorithm epoch: which releases make the same world from the same code (ADR 0010, G).

A world code names the release that made it, but most releases change the window, the packaging
or the text and nothing a world is made of. The epoch says what matters: **two releases of the
same epoch make byte-identical mods from the same settings, seed and game files**, apart from the
mod's ``.metadata`` (its title, version and picture), which is presentation and is written anew.

``ALGORITHM_SINCE`` lists the first release of every epoch. A release before the first entry is
epoch 0: made before epochs were recorded, so nothing is promised about it. The rule for whoever
changes the generator:

* A change that alters any file of a world's mod other than ``.metadata`` (the land, the peoples,
  the texts, the cover's shaders, a preset's values, the order of a random stream) is a new epoch:
  append an entry for the release that carries it, in the same change.
* A change that alters none (the window, the packaging, a picture, the metadata, speed that
  proves equal bytes) is not.
* The release version still moves for everything (ADR 0003). The epoch is what a reproducibility
  record (``rnw.record``) and a world code's promise are made of.

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
)


class ReleaseError(ValueError):
    """Text that is not a release version (``major.minor.patch``)."""


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
