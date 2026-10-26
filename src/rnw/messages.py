"""Messages the player reads when something cannot be done, in English and by key.

An error that the generator's window shows is raised with ``say(key, **values)``: a message that
prints as English, as the command line and the log show it, and keeps its key and values so that
the window can write it in its own language (``rnw.gui.text.explain``; the ``window`` catalogs
hold ``error.<key>``). Technical details that only a bug report needs stay English.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, override

MESSAGES: Final[dict[str, str]] = {
    # world codes
    "code.prefix": "A world code starts with {prefix}.",
    "code.short": "The world code is too short.",
    "code.typo": "The world code has a typing mistake: its check does not match.",
    "code.format": "This world code comes from a newer or different generator.",
    "code.damaged": "The changed settings in the world code are damaged.",
    "code.extra": "The world code has data left over at its end.",
    "code.characters": "The world code holds characters that cannot be part of one.",
    # where a world goes
    "destination.one": "Choose one destination for the world.",
    "destination.outside": "The destination must be outside the game's folder.",
    "destination.folder": "Choose an existing folder for the mod.",
    "destination.exists": "{file} already exists. Choose another name for the world file.",
    "destination.profile": "There is no profile to add the world to. Choose one, or do not add it.",
    "land_image.gone": (
        "This world's land is drawn on a picture the library no longer has. Open the world's "
        "file again, or choose the picture, to make the world."
    ),
    "check.no_record": (
        "This world has no reproducibility record, so its original output cannot be checked."
    ),
    "check.bundle": "The world's files in the library are no longer the ones it was made from.",
    # the game and the profile
    "install.in_use": (
        "The game is using {mod}. Untick it in the game's playset and apply the playset, or close "
        "the game."
    ),
    "pictures.missing": (
        "The pictures of {folder} are missing, so its picture in the game cannot change."
    ),
    "cover.missing": "The saved country-selection cover of {folder} is missing.",
    "picture.unwritten": "The picture of {folder} could not be written.",
    # moving worlds between machines
    "transfer.bundle": (
        "The world's files in the library no longer include {name}, so it cannot be moved."
    ),
    "transfer.no_mod": "This file holds no mod. Open it as a world file.",
    "transfer.no_record": (
        "This world has no reproducibility record, so its game files cannot be verified."
    ),
    "transfer.have": "The library already has this world. Delete it first to take this copy.",
    "transfer.foreign": "The mod in the file was not made by this generator.",
    "transfer.other_game": (
        "This game is not the one the world was made from: the files of its map differ. Make the "
        "world again here from its code."
    ),
    "transfer.no_listing": (
        "The file lists no game files, so this game cannot be checked against it."
    ),
    "transfer.changed": (
        "{count} game files the world was made from are not as they were, for example {names}. "
        "Make the world again here from its code."
    ),
    # a drawn land
    "mask.unreadable": "The picture cannot be read ({error}).",
    "mask.size": (
        "The picture is {width} × {height}. It must be at least {side} pixels each way and at "
        "most {millions} million pixels in all."
    ),
    "mask.share": (
        "The picture is {share} % land; a world needs between {low} % and {high} %. White is land, "
        "black is sea."
    ),
    "mask.file": "{name} cannot be read ({error}).",
    "mask.aspect": (
        "The picture is {given} times as wide as it is high; the New World's area is {wanted}. "
        "Draw it in that proportion, for example {width} × {height} pixels."
    ),
    # continent sketches
    "candidates.count": "Choose between 1 and {count} sketches.",
    "candidates.drawn": "Sketches need generated land. Go back to generated land first.",
}


@dataclass(frozen=True, slots=True)
class Said:
    """A message by its key and values; ``str`` of it is the English."""

    key: str
    values: dict[str, object]

    @override
    def __str__(self) -> str:
        return MESSAGES[self.key].format(**self.values)


def say(key: str, **values: object) -> Said:
    """The message ``key`` with ``values`` filled in."""
    return Said(key, values)
