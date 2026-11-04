"""Subset one face of an installed font to a page's characters, as WOFF2 (website/sitegen.py).

fontTools ships no type information, so this module is checked in pyright's basic mode; it only
moves values between fontTools calls and returns plain strings.
"""

# pyright: basic

from __future__ import annotations

from typing import TYPE_CHECKING

from fontTools import subset as ft_subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

if TYPE_CHECKING:
    from pathlib import Path

FEATURES = ("kern", "liga", "calt", "ccmp", "locl", "mark", "mkmk", "palt", "vert")


def subset_font(
    source: Path, index: int, weight: int | None, chars: str, target: Path
) -> dict[str, str]:
    """Write the subset to ``target``; return the source's version and copyright notice."""
    # The source's own timestamp, so the same text gives the same bytes.
    font = TTFont(source, fontNumber=index, lazy=False, recalcTimestamp=False)
    if weight is not None:
        font = instancer.instantiateVariableFont(font, {"wght": weight})
    options = ft_subset.Options(
        flavor="woff2",
        name_IDs=["*"],  # keep the copyright and licence records (SIL OFL 1.1)
        notdef_outline=True,
        hinting=False,
        desubroutinize=True,
        layout_features=list(FEATURES),
    )
    subsetter = ft_subset.Subsetter(options)
    subsetter.populate(text=chars)
    subsetter.subset(font)
    font.flavor = "woff2"
    target.parent.mkdir(parents=True, exist_ok=True)
    font.save(target)
    names = font["name"]
    return {"version": str(names.getDebugName(5)), "copyright": str(names.getDebugName(0))}
