"""The algorithm epoch: its table is well formed, releases map to it, and presets stay pinned."""

from __future__ import annotations

import hashlib

import pytest

from rnw import __version__, epoch
from rnw.settings import PRESETS, canonical_json

# The digest of every preset's resolved settings, by epoch. A preset's value is part of the
# algorithm (a short code resolves to it): changing one without a new epoch would make an old
# code another world. A new epoch adds a line; a line of a released epoch never changes.
PRESET_DIGESTS = {
    1: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    2: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    3: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    4: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    5: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    6: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    7: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    8: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    9: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    10: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    11: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    12: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    13: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    14: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    15: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    16: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    17: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    18: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    19: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    20: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    21: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    22: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    23: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    24: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    25: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    26: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    27: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    28: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    29: "26cc8c9a08f5bca3f32ccae294cc43176ae55ba96cbe49e9b7b7c7f000173974",
    30: "71b4a1a32c222cad6f4bd0bfa499361f8d2bbe89e4bda4e6661499fcc7985a1a",
    31: "71b4a1a32c222cad6f4bd0bfa499361f8d2bbe89e4bda4e6661499fcc7985a1a",
    32: "71b4a1a32c222cad6f4bd0bfa499361f8d2bbe89e4bda4e6661499fcc7985a1a",
    33: "71b4a1a32c222cad6f4bd0bfa499361f8d2bbe89e4bda4e6661499fcc7985a1a",
    34: "71b4a1a32c222cad6f4bd0bfa499361f8d2bbe89e4bda4e6661499fcc7985a1a",
}


def _preset_digest() -> str:
    document = {name: settings.to_json_data() for name, settings in sorted(PRESETS.items())}
    return hashlib.sha256(canonical_json(document).encode("ascii")).hexdigest()


def test_the_table_is_increasing_and_the_running_release_has_an_epoch() -> None:
    """Epochs are 1, 2, 3 in order of release; the release being run is at or after the first."""
    assert list(epoch.ALGORITHM_SINCE) == sorted(set(epoch.ALGORITHM_SINCE))
    assert epoch.epoch_of(__version__) == epoch.CURRENT
    assert epoch.CURRENT >= 1


def test_a_release_belongs_to_the_epoch_that_began_at_or_before_it() -> None:
    """The release that begins an epoch is in it; the one before is in the epoch before."""
    first = epoch.ALGORITHM_SINCE[0]
    assert epoch.epoch_of(".".join(str(part) for part in first)) == 1
    assert epoch.epoch_of(f"{first[0]}.{first[1]}.{first[2] - 1}") == 0
    assert epoch.epoch_of("0.1.0") == 0
    assert epoch.epoch_of("99.0.0") == len(epoch.ALGORITHM_SINCE)


def test_a_version_that_is_not_a_release_is_refused() -> None:
    """Only ``major.minor.patch`` parses."""
    for bad in ("1.2", "1.2.3.4", "v1.2.3", "1.2.x", ""):
        with pytest.raises(epoch.ReleaseError):
            _ = epoch.parse(bad)


def test_the_presets_of_the_running_epoch_are_pinned() -> None:
    """Retuning a preset needs a new epoch (``rnw.epoch``) and a new line here."""
    assert _preset_digest() == PRESET_DIGESTS[epoch.CURRENT]
