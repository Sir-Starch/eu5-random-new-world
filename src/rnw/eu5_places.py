"""Exceptional resource places: the rare rich seams and fishing grounds of the generated land.

Vanilla gives five locations of the Americas a historical bonus, by name (the richest silver
mountain, two lesser silver districts, the mercury mine, the great fishery), and a world that
replaces the continent loses them (G5 of the content plan). They are replaced by places the
generated land and its resources hold: a seam of silver in mountains, a mercury lode, a fishery on
a coast. A place has a modifier of the mod's own, with the same size of bonus the vanilla one has
(read from the installation at generation time, never copied into the project) and its own name
and text; a location template names it with ``modifier = ``.

The places belong to the resources part of the world (``rnw.layers``): they are drawn from the
resources seed over the materials, the relief and the coast, so rerolling the peoples leaves them
where they are and rerolling the resources moves them without touching a country. A world whose
materials hold no suitable cell has no such place, and says so.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rnw.pdx import Block, parse
from rnw.rng import derive_seed, hash_point

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

BASE_VALUES: Final[str] = (
    "game/main_menu/common/static_modifiers/location_historical_base_values.txt"
)
OUTPUT: Final[str] = "main_menu/common/static_modifiers/rnw_exceptional_places.txt"
NAME_KEY: Final[str] = "STATIC_MODIFIER_NAME_"
DESCRIPTION_KEY: Final[str] = "STATIC_MODIFIER_DESC_"


@dataclass(frozen=True, slots=True)
class Spec:
    """One kind of exceptional place: what it copies, where it may stand, how it reads."""

    modifier: str
    base: str
    material: str
    topographies: tuple[str, ...]
    coastal: bool
    name: str
    description: str


SPECS: Final[tuple[Spec, ...]] = (
    Spec(
        "rnw_great_silver_lode",
        "potosi_base",
        "silver",
        ("mountains",),
        coastal=False,
        name="Great Silver Lode",
        description="A mountain of silver richer than any other mine of the known world.",
    ),
    Spec(
        "rnw_rich_silver_vein",
        "zacatecas_base",
        "silver",
        ("hills", "mountains"),
        coastal=False,
        name="Rich Silver Vein",
        description="A silver vein that outdoes every other mine of the region.",
    ),
    Spec(
        "rnw_silver_seam",
        "guanajuato_base",
        "silver",
        ("mountains", "hills", "plateau"),
        coastal=False,
        name="Silver Seam",
        description="A seam of silver richer than the mines around it.",
    ),
    Spec(
        "rnw_mercury_lode",
        "huancavelica_base",
        "mercury",
        ("mountains", "hills"),
        coastal=False,
        name="Mercury Lode",
        description="A mine of cinnabar, prized for its quicksilver far beyond its region.",
    ),
    Spec(
        "rnw_rich_fishery",
        "newfoundland_fishing_grounds_base",
        "fish",
        (),
        coastal=True,
        name="Rich Fishing Grounds",
        description="Waters so full of fish that they feed the coasts around them.",
    ),
)


class PlacesError(ValueError):
    """An installation whose historical base values are not what the places copy."""


@dataclass(frozen=True, slots=True)
class Cells:
    """What the choice reads about each generated cell, by index."""

    land: Sequence[bool]
    material: Sequence[str]
    topography: Sequence[str]
    coastal: Sequence[bool]


def choose(cells: Cells, seed: int, specs: Sequence[Spec] = SPECS) -> dict[int, Spec]:
    """The cell of each kind of place, by index; a kind with no suitable cell is left out.

    A kind takes the first of its preferred topographies that has a candidate (any, if it has
    none), then the candidate whose hash under the kind's own stream is lowest, so adding a
    kind never moves another and no cell holds two.
    """
    taken: dict[int, Spec] = {}
    for spec in specs:
        stream = derive_seed(seed, "exceptional_place", spec.modifier)
        candidates = [
            index
            for index in range(len(cells.land))
            if cells.land[index]
            and cells.material[index] == spec.material
            and (cells.coastal[index] or not spec.coastal)
            and index not in taken
        ]
        for wanted in spec.topographies:
            tier = [index for index in candidates if cells.topography[index] == wanted]
            if tier:
                candidates = tier
                break
        if candidates:
            best = min(candidates, key=lambda index: (hash_point(stream, index, 0), index))
            taken[best] = spec
    return taken


def payloads(game_dir: Path, specs: Sequence[Spec] = SPECS) -> dict[str, str]:
    """The effect lines of each vanilla historical base value the places copy."""
    text = (game_dir / BASE_VALUES).read_text(encoding="utf-8-sig")
    entries = {
        entry.key: entry.value
        for entry in parse(text).entries
        if entry.key is not None and isinstance(entry.value, Block)
    }
    found: dict[str, str] = {}
    for spec in specs:
        block = entries.get(spec.base)
        if block is None:
            message = f"The historical base value {spec.base} is gone from the installation"
            raise PlacesError(message)
        lines = [
            "\t" + text[entry.start : entry.end].strip()
            for entry in block.entries
            if entry.key not in {"game_data", None}
        ]
        if not lines:
            message = f"{spec.base} no longer has an effect to copy"
            raise PlacesError(message)
        found[spec.modifier] = "\n".join(lines)
    return found


def modifiers_file(used: Sequence[Spec], effects: Mapping[str, str]) -> bytes:
    """The mod's static modifiers for the kinds that were placed."""
    blocks = [
        "\n".join(
            [
                f"{spec.modifier} = {{",
                "\tgame_data = {",
                "\t\tcategory = location",
                "\t}",
                effects[spec.modifier],
                "}",
                "",
            ]
        )
        for spec in used
    ]
    return "\n".join(blocks).encode("utf-8-sig")


def texts(used: Sequence[Spec]) -> dict[str, str]:
    """The localization of the kinds that were placed (English, until L1 translates it)."""
    found: dict[str, str] = {}
    for spec in used:
        found[f"{NAME_KEY}{spec.modifier}"] = spec.name
        found[f"{DESCRIPTION_KEY}{spec.modifier}"] = spec.description
    return found
