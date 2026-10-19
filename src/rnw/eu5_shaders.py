"""Patch EU5 1.4.1 shaders read from the local installation (NOT GAME VALIDATED).

The terra incognita overlay samples visibility per location pixel with a one-pixel
bilinear blend (``GetBilinear`` in ``terra_incognita.shader``), so its edge repeats
the pixel steps of the location raster at close zoom; the multi-sample blur the
engine defines (``GetMultiSamples``) is not called [V-LOCAL C69]. The patch averages
twelve more samples within two pixels wherever the visibility changes nearby, and
keeps the single sample elsewhere.
"""

from __future__ import annotations

from typing import Final

TERRA_INCOGNITA: Final[str] = "game/main_menu/gfx/FX/terra_incognita.shader"
CALL: Final[str] = "float Visibility = GetBilinear(Input.WorldSpacePos.xz, Mode);"
INDENT: Final[str] = "\t\t\t\t\t"
CORNERS: Final[tuple[tuple[str, str], ...]] = (
    ("-2.0", "-2.0"), ("2.0", "-2.0"), ("-2.0", "2.0"), ("2.0", "2.0"),
)  # fmt: skip
# Two rings: radius 2 at 0, 60, ... 300 degrees and radius 1 at 30, 90, ... 330 degrees.
RING: Final[tuple[tuple[str, str], ...]] = (
    ("2.0", "0.0"), ("1.0", "1.732"), ("-1.0", "1.732"),
    ("-2.0", "0.0"), ("-1.0", "-1.732"), ("1.0", "-1.732"),
    ("0.866", "0.5"), ("0.0", "1.0"), ("-0.866", "0.5"),
    ("-0.866", "-0.5"), ("0.0", "-1.0"), ("0.866", "-0.5"),
)  # fmt: skip


def _sample(dx: str, dy: str) -> str:
    return f"GetBilinear( Input.WorldSpacePos.xz + float2( {dx}, {dy} ), RnwMode )"


def soft_visibility_code() -> str:
    """Replacement for the bilinear visibility line of ``PS_TerraIncognita``."""
    lines = [
        CALL,
        "// RNW: soften the one-pixel steps of location borders over about two pixels.",
        "float RnwMode = 0.0f;",
        "float RnwEdge = 0.0f;",
        *(f"RnwEdge += abs( {_sample(dx, dy)} - Visibility );" for dx, dy in CORNERS),
        "if( RnwEdge > 0.0f )",
        "{",
        "\tfloat RnwSum = Visibility;",
        *(f"\tRnwSum += {_sample(dx, dy)};" for dx, dy in RING),
        f"\tVisibility = RnwSum / {len(RING) + 1}.0f;",
        "}",
    ]
    return ("\n" + INDENT).join(lines)


def soften_terra_incognita(text: str) -> str | None:
    """Patched shader text, or None when the expected line is not there exactly once."""
    target = INDENT + CALL
    if text.count(target) != 1:
        return None
    return text.replace(target, INDENT + soft_visibility_code())
