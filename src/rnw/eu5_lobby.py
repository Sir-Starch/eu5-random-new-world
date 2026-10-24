"""Cover the generated New World while a country is chosen (NOT GAME VALIDATED).

A new game opens on the country-selection screen. There the engine draws no terra incognita (TI)
at all, and its TI visibility texture reads every location as unknown; in a campaign the TI
overlay, a mesh above the map, covers the locations the player's country does not know
[V-GAME C134, C135]. So the vanilla TI rule, *cover where nothing is known*, restricted to the
generated New World, covers it at selection and changes nothing in a campaign, where the overlay
draws over the same places. It has to be drawn by the layers the map draws at selection, in
files of the mod that replace the game's own, made from the installed game and never committed
(AGENTS.md); the owner chose the four layers seen there (C136):

* the terrain, in 3D and on the flat map, and the water take the colour of TI where the cover
  holds, after the game's ``terra_incognita.shader`` where nothing is known, with its drawings
  (dragons, compasses) read from the game's own texture through a sampler of the mod's
  (``DRAWINGS_SAMPLER``, an ``Index`` and the path in ``file``, as that shader declares it);
* borders and map names fade out there;
* the context menu of a country on the map leaves out *Select* for a country of the New World,
  which a scripted GUI of the mod recognises by its capital's continent;
* the lobby's country cards use a vertical list that excludes invisible children from layout.

The close-zoom failure of C150 adds detail, mesh and tree-shadow passes and lobby/marker GUI
guards (C151). Native map picking is not intercepted; the lobby guard hides a selected New
World country's information and disables its UI start controls. Runtime confirmation is open.

Where the cover lies is a grid of ``CELL``-pixel squares held in the include as a constant
array, a bit each, first row north: the generated locations and the game's ocean wastelands
(impassable sea zones) that border them, which a country in a game does not know either and
which, left open at selection, would outline the New World. The shader smooths the grid's
steps bilinearly. A file texture cannot carry it: the game declares a ``TextureSampler`` only
with a ``Ref`` (an engine slot) or an ``Index``, and drops one with a ``File`` alone, so the
shader that reads it does not compile and the game crashes when the map is first drawn
[V-GAME C137]. Nor may a shader name one engine slot twice: the shaders that already read
the province indirection or TI and got a second sampler for it were never compiled, and the
game crashed (C138). So the cover's code takes the samplers it reads as arguments, and a sampler
of the mod's (``OWN_SAMPLERS``) is added only to a shader without one for that slot, which the
export checks against the installed game's includes (``binding_problem``). World z grows
northwards while image rows run
southwards (C135). The generator's setting whether the New World is shown before it is played
decides whether a world's mod carries these files (``rnw.app.preferences``); the export also
keeps a copy beside the mod (``COVER_COPY``).
"""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw.eu5_lobby_gui import COUNTRY_SCOPE, GUI_FILES, new_world_country
from rnw.eu5_lobby_gui import scripted_gui_text as location_scripted_gui_text

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

    from numpy.typing import NDArray

CONTEXT_MENU: Final[str] = "game/in_game/gui/context_menu.gui"
GRAPHICS_DEFINES: Final[str] = "game/loading_screen/common/defines/graphic/00_graphics.txt"
SCRIPTED_GUI_FILE: Final[str] = "in_game/common/scripted_guis/rnw_new_world.txt"
COVER_INCLUDE: Final[str] = "rnw_new_world_cover.fxh"
VISIBILITY_INCLUDE: Final[str] = "rnw_new_world_visibility.fxh"
INDIRECTION_INCLUDE: Final[str] = "rnw_new_world_indirection.fxh"
# The drawings of terra incognita (dragons, compasses): a texture of the game's own, named by
# path and read through a sampler of the mod's with an ``Index``, as terra_incognita.shader does.
DRAWINGS_INCLUDE: Final[str] = "rnw_new_world_drawings.fxh"
DRAWINGS_SAMPLER: Final[str] = "RnwDrawings"
DRAWINGS_INDEX: Final[int] = 2
DRAWINGS_FILE: Final[str] = "gfx/map/flatmap/terra_incognita.dds"
TI_REF: Final[str] = "TerraIncognitaVisibilityTexture"
INDIRECTION_REF: Final[str] = "JominiProvinceColorIndirection"
# The mod's own sampler includes: the sampler each declares and the engine slot it reads.
OWN_SAMPLERS: Final[dict[str, tuple[str, str]]] = {
    VISIBILITY_INCLUDE: ("RnwVisibility", TI_REF),
    INDIRECTION_INCLUDE: ("RnwProvinceIndirection", INDIRECTION_REF),
}
# Where the game keeps the includes a shader names, relative to the installation.
INCLUDE_DIRS: Final[tuple[str, ...]] = (
    "game/main_menu/gfx/FX",
    "game/loading_screen/gfx/FX",
    "jomini/main_menu/gfx/FX",
    "jomini/loading_screen/gfx/FX",
    "clausewitz/main_menu/gfx/FX",
    "clausewitz/loading_screen/gfx/FX",
)
SHADER_DIR: Final[str] = "main_menu/gfx/FX"
# The folder of a world's bundle that keeps the cover's files while its mod is without them.
SCRIPTED_GUI: Final[str] = "rnw_new_world_country"
CONTINENT: Final[str] = "america"
# Map pixels per side of a cell of the cover's grid; a cell is covered from half its area.
CELL: Final[int] = 32
WORDS_PER_LINE: Final[int] = 4
# What terra_incognita.shader does to the flat map's land colour where nothing is known.
GREY: Final[tuple[float, float, float]] = (0.299, 0.587, 0.114)
GREY_SHARE: Final[float] = 0.5
UNKNOWN_BRIGHTNESS: Final[float] = 0.1
LAND_HSV: Final[re.Pattern[str]] = re.compile(
    r"(?m)^[ \t]*FLAT_MAP_COLOR_LAND_HSV\s*=\s*\{\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s*\}"
)
INCLUDES: Final[re.Pattern[str]] = re.compile(r"\AIncludes = \{\n(.*?)\n\}\n", re.DOTALL)
SAMPLER: Final[re.Pattern[str]] = re.compile(r"TextureSampler\s+(\w+)\s*\{(.*?)\}", re.DOTALL)
REF: Final[re.Pattern[str]] = re.compile(r"\bRef\s*=\s*(\w+)")
INDEX: Final[re.Pattern[str]] = re.compile(r"\bIndex\s*=\s*(\d+)")
INCLUDE_NAMES: Final[re.Pattern[str]] = re.compile(r"Includes\s*=\s*\{(.*?)\}", re.DOTALL)
SELECT: Final[str] = 'visible = "[And(IsLobbyOpen, IsCountryPlayable(Country.Self))]"'
NEW_WORLD_COUNTRY: Final[str] = new_world_country("Country")
NOTE: Final[str] = "// Random New World: the New World is covered where nothing is known (C136)."


@dataclass(frozen=True, slots=True)
class ShaderEdit:
    """A game shader the cover changes: includes added, lines replaced (each found once), and the
    samplers of the province indirection and of TI that its call of the cover passes.

    ``path`` is the override destination; ``source_path`` derives a private copy from a
    different installed file without overriding that shared original. ``drawings`` names the
    sampler of the terra incognita drawings that a call of ``RnwCovered`` passes, for the
    shaders that paint the colour of the cover (empty where the cover only clips or fades).
    """

    path: str
    includes: tuple[str, ...]
    indirection: str
    visibility: str
    edits: tuple[tuple[str, str], ...]
    source_path: str | None = None
    drawings: str = ""


def _lines(indent: int, *lines: str) -> str:
    return "".join("\t" * indent + line + "\n" for line in lines)


def _shader(
    path: str,
    includes: tuple[str, ...],
    samplers: tuple[str, ...],
    anchor: str,
    *lines: str,
    source_path: str | None = None,
) -> ShaderEdit:
    """One edit at ``anchor``: ``lines`` before it, ``{samplers}`` standing for the call's.

    ``samplers`` are the indirection's and TI's, and the drawings' for a shader that paints.
    """
    indent = len(anchor) - len(anchor.lstrip("\t"))
    arguments = ", ".join(samplers)
    body = _lines(indent, NOTE, *(line.format(samplers=arguments) for line in lines))
    indirection, visibility, *drawings = samplers
    return ShaderEdit(
        path,
        includes,
        indirection,
        visibility,
        ((anchor, body + anchor),),
        source_path,
        drawings[0] if drawings else "",
    )


def _tree_effect(name: str, vertex_shader: str, pixel_shader: str) -> str:
    return "\n".join(
        (
            f"Effect {name}",
            "{",
            f"\tVertexShader = {vertex_shader}",
            f"\tPixelShader = {pixel_shader}",
        )
    )


def _tree_lighting_call(function: str, *arguments: str) -> str:
    return f"float3 Color = {function}( {', '.join(arguments)} );"


TERRAIN_SAMPLERS: Final[tuple[str, str]] = ("ProvinceColorIndirectionTexture", "RnwVisibility")
# The shaders that paint the unknown colour read the drawings of terra incognita as well.
DRAWN_SAMPLERS: Final[tuple[str, str, str]] = (*TERRAIN_SAMPLERS, DRAWINGS_SAMPLER)
TREE_SHADOW_EFFECTS: Final[tuple[tuple[str, str, str], ...]] = (
    ("treeShadow", '"VertexPdxMeshStandardShadow"', '"PixelPdxMeshAlphaBlendShadow"'),
    ("tree_two_sidedShadow", '"VertexPdxMeshStandardShadow"', '"PixelPdxMeshAlphaBlendShadow"'),
    (
        "tree_alpha_to_coverageShadow",
        '"VertexPdxMeshStandardShadow"',
        '"PixelPdxMeshAlphaBlendShadow"',
    ),
    (
        "tree_alpha_to_coverage_two_sidedShadow",
        '"VertexPdxMeshStandardShadow"',
        '"PixelPdxMeshAlphaBlendShadow"',
    ),
    ("treeShadow_mapobject", "VS_mapobject_shadow", '"PS_jomini_mapobject_shadow_alphablend"'),
    (
        "tree_two_sidedShadow_mapobject",
        "VS_mapobject_shadow",
        '"PS_jomini_mapobject_shadow_alphablend"',
    ),
    (
        "tree_alpha_to_coverageShadow_mapobject",
        "VS_mapobject_shadow",
        '"PS_jomini_mapobject_shadow_alphablend"',
    ),
    (
        "tree_alpha_to_coverage_two_sidedShadow_mapobject",
        "VS_mapobject_shadow",
        '"PS_jomini_mapobject_shadow_alphablend"',
    ),
    ("billboard_testShadow", "VS_billboard_test_shadow", "PixelPdxMeshAlphaBlendShadow"),
    (
        "billboard_testShadow_mapobject",
        "VS_billboard_test_mapobject_shadow",
        "PS_jomini_mapobject_shadow_alphablend",
    ),
)
TREE_SHADOW_CODE: Final[str] = "\n".join(
    [
        "MainCode PS_RnwTreeShadow",
        "{",
        '\tInput = "VS_OUTPUT_PDXMESHSHADOWSTANDARD"',
        '\tOutput = "void"',
        "\tCode",
        "\t[[",
        "\t\tPDX_MAIN",
        "\t\t{",
        "\t\t\tfloat Alpha = PdxTex2D( PDXMESH_AlphaBlendShadowMap, Input.UV_InstanceIndex.xy ).a;",
        "\t\t#ifdef PDXMESH_USE_DITHERED_OPACITY",
        "\t\t\tfloat Opacity = PdxMeshGetOpacity( uint( Input.UV_InstanceIndex.z + 0.5 ) );",
        "\t\t\tPdxMeshApplyDitheredOpacity( Opacity, Input.Position.xy );",
        "\t\t#endif",
        "\t\t\tfloat4x4 WorldMatrix = PdxMeshGetWorldMatrix( {} );".format(
            "uint( Input.UV_InstanceIndex.z + 0.5 )"
        ),
        "\t\t\tfloat2 WorldSpacePosXZ = float2( WorldMatrix[0][3], WorldMatrix[2][3] );",
        "\t\t\tclip( 0.001f - RnwCover( {}, {}, {} ) );".format(
            "WorldSpacePosXZ", "ProvinceColorIndirectionTexture", "RnwVisibility"
        ),
        "\t\t\tclip( Alpha - 0.5f );",
        "\t\t}",
        "\t]]",
        "}",
        "MainCode PS_RnwTreeMapObjectShadow",
        "{",
        '\tInput = "VS_OUTPUT_MAPOBJECT_SHADOW"',
        '\tOutput = "void"',
        "\tCode",
        "\t[[",
        "\t\tPDX_MAIN",
        "\t\t{",
        "\t\t\tApplyDither( Input );",
        "\t\t\tfloat Alpha = PdxTex2D( PDXMESH_AlphaBlendShadowMap, Input.UV ).a;",
        "\t\t\tfloat4x4 WorldMatrix = UnpackAndGetMapObjectWorldMatrix( {} );".format(
            "Input.Index24_Packed1_Opacity6_Sign1"
        ),
        "\t\t\tfloat2 WorldSpacePosXZ = float2( WorldMatrix[0][3], WorldMatrix[2][3] );",
        "\t\t\tclip( 0.001f - RnwCover( {}, {}, {} ) );".format(
            "WorldSpacePosXZ", "ProvinceColorIndirectionTexture", "RnwVisibility"
        ),
        "\t\t\tclip( Alpha - 0.5f );",
        "\t\t}",
        "\t]]",
        "}",
    ]
)
SHADERS: Final[tuple[ShaderEdit, ...]] = (
    ShaderEdit(
        "game/main_menu/gfx/FX/pdxterrain2.shader",
        (VISIBILITY_INCLUDE, DRAWINGS_INCLUDE, COVER_INCLUDE),
        *TERRAIN_SAMPLERS,
        (
            (
                _lines(4, "return TerrainShader( Input );"),
                _lines(
                    4,
                    "PS_OUTPUT RnwOutput = TerrainShader( Input );",
                    NOTE,
                    "float2 RnwPosition = Input.WorldSpacePos.xz;",
                    "RnwOutput._Color.rgb = RnwCovered( RnwOutput._Color.rgb, RnwPosition,",
                    "\tProvinceColorIndirectionTexture, RnwVisibility, RnwDrawings );",
                    "return RnwOutput;",
                ),
            ),
            (
                _lines(4, "return FinalColor;"),
                _lines(
                    4,
                    NOTE,
                    "FinalColor.rgb = RnwCovered( FinalColor.rgb, Input.WorldSpacePos.xz,",
                    "\tProvinceColorIndirectionTexture, RnwVisibility, RnwDrawings );",
                    "return FinalColor;",
                ),
            ),
        ),
        drawings=DRAWINGS_SAMPLER,
    ),
    _shader(
        "game/main_menu/gfx/FX/pdxwater.shader",
        (VISIBILITY_INCLUDE, DRAWINGS_INCLUDE, COVER_INCLUDE),
        DRAWN_SAMPLERS,
        _lines(4, "return PS_Return( Water._Color, Material );"),
        "float2 RnwPosition = Input.WorldSpacePos.xz;",
        "Water._Color.rgb = RnwCovered( Water._Color.rgb, RnwPosition, {samplers} );",
    ),
    ShaderEdit(
        "game/main_menu/gfx/FX/pdxborder.shader",
        (COVER_INCLUDE,),
        "ProvinceColorIndirectionTexture",
        "VisibilityMap",
        (
            (
                _lines(4, "#ifndef IGNORE_TERRA_INCOGNITA"),
                _lines(4, "#ifndef IGNORE_TERRA_INCOGNITA")
                + _lines(
                    5,
                    NOTE,
                    "Diffuse.a *= 1.0f - RnwCover( Input.WorldSpacePos.xz,",
                    "\tProvinceColorIndirectionTexture, VisibilityMap );",
                ),
            ),
        ),
    ),
    _shader(
        "game/main_menu/gfx/FX/mapname.shader",
        (INDIRECTION_INCLUDE, VISIBILITY_INCLUDE, COVER_INCLUDE),
        ("RnwProvinceIndirection", "RnwVisibility"),
        _lines(3, "return MixedColor;"),
        "MixedColor.a *= 1.0f - RnwCover( Input.WorldSpacePos.xz, {samplers} );",
    ),
    ShaderEdit(
        "game/main_menu/gfx/FX/tree.shader",
        (VISIBILITY_INCLUDE, COVER_INCLUDE),
        "ProvinceColorIndirectionTexture",
        "RnwVisibility",
        (
            (
                "MainCode PS_leaf\n",
                TREE_SHADOW_CODE + "MainCode PS_leaf\n",
            ),
            (
                _lines(
                    4,
                    _tree_lighting_call(
                        "CalculateSunLighting", "MaterialProps", "LightingProps", "EnvironmentMap"
                    ),
                ),
                _lines(
                    4,
                    NOTE,
                    "clip( 0.001f - RnwCover( Input.WorldSpacePos.xz,",
                    "\tProvinceColorIndirectionTexture, RnwVisibility ) );",
                    _tree_lighting_call(
                        "CalculateSunLighting", "MaterialProps", "LightingProps", "EnvironmentMap"
                    ),
                ),
            ),
            (
                _lines(
                    4,
                    _tree_lighting_call(
                        "CalculateCustomLeafLighting",
                        "TranslucencyMask",
                        "MaterialProps",
                        "LightingProps",
                        "EnvironmentMap",
                        "ShadowTerm",
                        "SoftShadowTerm",
                    ),
                ),
                _lines(
                    4,
                    NOTE,
                    "clip( 0.001f - RnwCover( Input.WorldSpacePos.xz,",
                    "\tProvinceColorIndirectionTexture, RnwVisibility ) );",
                    _tree_lighting_call(
                        "CalculateCustomLeafLighting",
                        "TranslucencyMask",
                        "MaterialProps",
                        "LightingProps",
                        "EnvironmentMap",
                        "ShadowTerm",
                        "SoftShadowTerm",
                    ),
                ),
            ),
            *(
                (
                    _tree_effect(name, vertex_shader, old_pixel_shader),
                    _tree_effect(name, vertex_shader, "PS_RnwTreeShadow"),
                )
                for name, vertex_shader, old_pixel_shader in TREE_SHADOW_EFFECTS
                if "mapobject" not in name and "Shadow" in name
            ),
            *(
                (
                    _tree_effect(name, vertex_shader, old_pixel_shader),
                    _tree_effect(name, vertex_shader, "PS_RnwTreeMapObjectShadow"),
                )
                for name, vertex_shader, old_pixel_shader in TREE_SHADOW_EFFECTS
                if "mapobject" in name
            ),
        ),
    ),
    _shader(
        "game/main_menu/gfx/FX/river_surface.shader",
        (VISIBILITY_INCLUDE, COVER_INCLUDE),
        TERRAIN_SAMPLERS,
        _lines(4, "return PS_Return( FinalColor, Material );"),
        "FinalColor.a *= 1.0f - RnwCover( Input.WorldSpacePos.xz, {samplers} );",
    ),
    _shader(
        "game/main_menu/gfx/FX/river_bottom.shader",
        (VISIBILITY_INCLUDE, COVER_INCLUDE),
        TERRAIN_SAMPLERS,
        _lines(4, "return Out;"),
        "clip( 0.001f - RnwCover( Input.WorldSpacePos.xz, {samplers} ) );",
    ),
    _shader(
        "game/main_menu/gfx/FX/city_generated_geometry.shader",
        (VISIBILITY_INCLUDE, COVER_INCLUDE),
        TERRAIN_SAMPLERS,
        _lines(3, "return PS_Return( Color, Alpha * Opacity * FlatmapFade.y, MaterialProps );"),
        "Alpha *= 1.0f - RnwCover( WorldSpacePos.xz, {samplers} );",
    ),
    ShaderEdit(
        "game/main_menu/gfx/FX/pdxmesh.shader",
        (VISIBILITY_INCLUDE, COVER_INCLUDE),
        *TERRAIN_SAMPLERS,
        (
            (_lines(1, '"pdxmesh_base.fxh"'), _lines(1, '"rnw_map_mesh.fxh"')),
            (
                _lines(3, "return TerrainShader( InputTerrain, Input.Normal );"),
                _lines(
                    3,
                    NOTE,
                    "clip( 0.001f - RnwCover( Input.WorldSpacePos.xz,",
                    "\tProvinceColorIndirectionTexture, RnwVisibility ) );",
                    "return TerrainShader( InputTerrain, Input.Normal );",
                ),
            ),
        ),
    ),
    _shader(
        "game/main_menu/gfx/FX/rnw_map_mesh.fxh",
        ("jomini/jomini_province_overlays.fxh", VISIBILITY_INCLUDE, COVER_INCLUDE),
        ("ProvinceColorIndirectionTexture", "RnwVisibility"),
        _lines(4, "float Alpha = Diffuse.a;"),
        "clip( 0.001f - RnwCover( Input.WorldSpacePos.xz, {samplers} ) );",
        source_path="game/loading_screen/gfx/FX/pdxmesh_base.fxh",
    ),
    ShaderEdit(
        "game/main_menu/gfx/FX/pdxmesh_decal.shader",
        (VISIBILITY_INCLUDE, COVER_INCLUDE),
        "ProvinceColorIndirectionTexture",
        "RnwVisibility",
        (
            (
                _lines(4, "return float4( Color, Alpha );"),
                _lines(
                    4,
                    NOTE,
                    "Alpha *= 1.0f - RnwCover( Input.WorldSpacePos.xz,",
                    "\tProvinceColorIndirectionTexture, RnwVisibility );",
                    "return float4( Color, Alpha );",
                ),
            ),
            (
                _lines(4, "return float4( Color, Diffuse.a );"),
                _lines(
                    4,
                    NOTE,
                    "Diffuse.a *= 1.0f - RnwCover( Input.WorldSpacePos.xz,",
                    "\tProvinceColorIndirectionTexture, RnwVisibility );",
                    "return float4( Color, Diffuse.a );",
                ),
            ),
        ),
    ),
    _shader(
        "game/main_menu/gfx/FX/worldtext.shader",
        (INDIRECTION_INCLUDE, VISIBILITY_INCLUDE, COVER_INCLUDE),
        ("RnwProvinceIndirection", "RnwVisibility"),
        _lines(3, "return MixedColor;"),
        "MixedColor.a *= 1.0f - RnwCover( Input.WorldSpacePos.xz, {samplers} );",
    ),
)


def mod_path(relative: str) -> str:
    """Where a game file goes in the mod."""
    return relative.removeprefix("game/")


def cover_files() -> tuple[str, ...]:
    """The mod's files that cover the New World at country selection, relative to the mod."""
    return (
        f"{SHADER_DIR}/{COVER_INCLUDE}",
        f"{SHADER_DIR}/{DRAWINGS_INCLUDE}",
        *(f"{SHADER_DIR}/{name}" for name in OWN_SAMPLERS),
        *(mod_path(edit.path) for edit in SHADERS),
        mod_path(CONTEXT_MENU),
        *(mod_path(path) for path in GUI_FILES),
        SCRIPTED_GUI_FILE,
    )


def cover_grid(labels: NDArray[np.int32], covered: NDArray[np.bool_]) -> NDArray[np.bool_]:
    """The cells of ``CELL`` pixels that covered locations fill at least half of, north first.

    ``labels`` is the finished map's location raster, first row north; ``covered`` says for
    every label whether the cover takes it. The map is read in bands of ``CELL`` rows.
    """
    rows, columns = labels.shape
    if rows % CELL or columns % CELL:
        message = f"the map ({columns} x {rows}) is not a multiple of {CELL} pixels"
        raise ValueError(message)
    width = columns // CELL
    grid = np.zeros((rows // CELL, width), dtype=bool)
    for band in range(rows // CELL):
        inside = covered[labels[band * CELL : (band + 1) * CELL]]
        counts = inside.reshape(CELL, width, CELL).sum(axis=(0, 2))
        grid[band] = counts * 2 >= CELL * CELL
    return grid


def cover_words(grid: NDArray[np.bool_]) -> list[int]:
    """The grid as 32-bit words, row by row, the first cell in the lowest bit."""
    packed = np.packbits(np.ascontiguousarray(grid).ravel(), bitorder="little")
    return [int(word) for word in packed.view("<u4")]


def land_colour(defines: str) -> tuple[float, float, float] | None:
    """The flat map's land colour from the game's graphics defines, or None when not found once."""
    found = LAND_HSV.findall(defines)
    if len(found) != 1:
        return None
    hue, saturation, value = (float(part) for part in found[0])
    return colorsys.hsv_to_rgb(hue, saturation, value)


def unknown_colour(land: tuple[float, float, float]) -> tuple[float, float, float]:
    """Terra incognita's colour where nothing is known: the land colour half grey, at a tenth.

    ``terra_incognita.shader`` also darkens it where its drawings lie; the cover multiplies this
    colour by them (``RnwDrawn``), read from the game's texture through ``DRAWINGS_SAMPLER``.
    """
    grey = sum(part * weight for part, weight in zip(land, GREY, strict=True))
    red, green, blue = ((part + (grey - part) * GREY_SHARE) * UNKNOWN_BRIGHTNESS for part in land)
    return red, green, blue


def _words_text(words: list[int]) -> str:
    vectors = [
        "uint4( " + ", ".join(f"0x{word:08x}" for word in words[start : start + 4]) + " )"
        for start in range(0, len(words), 4)
    ]
    lines = [
        ", ".join(vectors[start : start + WORDS_PER_LINE])
        for start in range(0, len(vectors), WORDS_PER_LINE)
    ]
    return ",\n\t\t\t".join(lines)


def cover_include(
    shape: tuple[int, int], grid: NDArray[np.bool_], colour: tuple[float, float, float]
) -> str:
    """The include of the cover's code: how much of a point it takes and what it paints there.

    It declares no sampler: the shader passes the ones of the province indirection, of TI and,
    where the colour is painted, of the drawings of terra incognita.
    """
    rows, columns = shape
    grid_rows, grid_columns = grid.shape
    words = cover_words(grid)
    if len(words) % 4 or grid_rows * CELL != rows or grid_columns * CELL != columns:
        message = "the cover's grid does not tile the map in whole 128-bit vectors"
        raise ValueError(message)
    unknown = ", ".join(f"{part:.6f}f" for part in colour)
    return f"""# Random New World: the cover of the New World at country selection (C136-C138).
# Made by the generator for one world: the grid and the map's size are this world's. It declares
# no sampler; the shader passes those of the province indirection, of terra incognita and of its
# drawings.

PixelShader =
{{
	Code
	[[
		static const float2 RnwMapSize = float2( {columns}.0f, {rows}.0f );
		static const float RnwCell = {CELL}.0f;
		static const int2 RnwGrid = int2( {grid_columns}, {grid_rows} );
		// The flat map's land colour, half grey, at a tenth, as terra_incognita.shader paints
		// where nothing is known (without its drawings).
		static const float3 RnwUnknownColour = float3( {unknown} );
		// One bit per cell, row by row from the north, the first cell in the lowest bit.
		static const uint4 RnwCoverWords[{len(words) // 4}] = {{
			{_words_text(words)}
		}};

		float RnwCell01( int2 Cell )
		{{
			Cell.x = ( Cell.x % RnwGrid.x + RnwGrid.x ) % RnwGrid.x;
			Cell.y = clamp( Cell.y, 0, RnwGrid.y - 1 );
			uint Index = uint( Cell.y * RnwGrid.x + Cell.x );
			uint Word = RnwCoverWords[ Index >> 7 ][ ( Index >> 5 ) & 3 ];
			return float( ( Word >> ( Index & 31 ) ) & 1 );
		}}

		// The grid, bilinear between cell centres and sharpened, so its edge is smooth. The
		// world's z grows northwards, the grid's rows southwards. The map wraps in x but ends in
		// z: beyond its north and south edges lies the table of its frame, which the grid's first
		// and last rows (clamped for the interpolation) must not reach.
		float RnwMask( float2 WorldSpacePosXZ )
		{{
			[branch] if( WorldSpacePosXZ.y < 0.0f || WorldSpacePosXZ.y > RnwMapSize.y )
			{{
				return 0.0f;
			}}
			float2 Cell = float2( WorldSpacePosXZ.x, RnwMapSize.y - WorldSpacePosXZ.y );
			Cell = Cell / RnwCell - vec2( 0.5f );
			float2 Corner = floor( Cell );
			float2 Frac = Cell - Corner;
			int2 Base = int2( Corner );
			float North = lerp( RnwCell01( Base ), RnwCell01( Base + int2( 1, 0 ) ), Frac.x );
			int2 Below = Base + int2( 0, 1 );
			float South = lerp( RnwCell01( Below ), RnwCell01( Below + int2( 1, 0 ) ), Frac.x );
			return smoothstep( 0.35f, 0.65f, lerp( North, South, Frac.y ) );
		}}

		// 1 where no country knows the location, read as terra_incognita_visibility.fxh reads it.
		float RnwUnknownAt( float2 WorldSpacePosXZ, in PdxTextureSampler2D Indirection,
			in PdxTextureSampler2D Visibility )
		{{
			float2 Texel = clamp( WorldSpacePosXZ, vec2( 0.0f ), RnwMapSize - vec2( 1.0f ) );
			float2 ColorIndex = PdxTex2DLod0( Indirection, Texel / RnwMapSize ).rg;
			float Known = PdxTex2DLoad0( Visibility, int2( ColorIndex * 255.0f ) ).r;
			uint Data = uint( 255.0f * Known );
			return ( Data & 0x3 ) < 3 ? 1.0f : 0.0f;
		}}

		// Bilinear between neighbouring map pixels, as GetBilinear of the game.
		float RnwUnknown( float2 WorldSpacePosXZ, in PdxTextureSampler2D Indirection,
			in PdxTextureSampler2D Visibility )
		{{
			float2 East = WorldSpacePosXZ + float2( 1.0f, 0.0f );
			float2 North = WorldSpacePosXZ + float2( 0.0f, 1.0f );
			float2 NorthEast = WorldSpacePosXZ + float2( 1.0f, 1.0f );
			float C11 = RnwUnknownAt( WorldSpacePosXZ, Indirection, Visibility );
			float C21 = RnwUnknownAt( East, Indirection, Visibility );
			float C12 = RnwUnknownAt( North, Indirection, Visibility );
			float C22 = RnwUnknownAt( NorthEast, Indirection, Visibility );
			float2 Frac = frac( WorldSpacePosXZ );
			return lerp( lerp( C11, C21, Frac.x ), lerp( C12, C22, Frac.x ), Frac.y );
		}}

		// How much of the point the cover takes: inside the New World where nothing is known. At
		// country selection every location reads as unknown; in a game the TI overlay draws over
		// the same places.
		float RnwCover( float2 WorldSpacePosXZ, in PdxTextureSampler2D Indirection,
			in PdxTextureSampler2D Visibility )
		{{
			float Mask = RnwMask( WorldSpacePosXZ );
			[branch] if( Mask <= 0.0f )
			{{
				return 0.0f;
			}}
			return Mask * RnwUnknown( WorldSpacePosXZ, Indirection, Visibility );
		}}

		// What terra_incognita.shader multiplies its colour by where the drawings lie: the texture
		// covers the whole map, its top row north, the red channel darkens by up to three quarters
		// and the green by up to a half.
		float RnwDrawn( float2 WorldSpacePosXZ, in PdxTextureSampler2D Drawings )
		{{
			float2 UV = float2( WorldSpacePosXZ.x / RnwMapSize.x,
				1.0f - WorldSpacePosXZ.y / RnwMapSize.y );
			float2 Drawing = PdxTex2D( Drawings, UV ).rg;
			return ( 1.0f - 0.75f * Drawing.r ) * ( 1.0f - 0.5f * Drawing.g );
		}}

		float3 RnwCovered( float3 Color, float2 WorldSpacePosXZ, in PdxTextureSampler2D Indirection,
			in PdxTextureSampler2D Visibility, in PdxTextureSampler2D Drawings )
		{{
			float Drawn = RnwDrawn( WorldSpacePosXZ, Drawings );
			float Cover = RnwCover( WorldSpacePosXZ, Indirection, Visibility );
			return lerp( Color, RnwUnknownColour * Drawn, Cover );
		}}
	]]
}}
"""


def sampler_include(name: str) -> str:
    """One of the mod's sampler includes (``OWN_SAMPLERS``): a single point sampler of a slot."""
    sampler, ref = OWN_SAMPLERS[name]
    vertical = "Wrap" if ref == TI_REF else "Clamp"
    return f"""# Random New World: a sampler of the engine's {ref} for the cover (C138), for a
# shader that has none for that slot; a shader must not name one slot twice.

PixelShader =
{{
	TextureSampler {sampler}
	{{
		Ref = {ref}
		MagFilter = "Point"
		MinFilter = "Point"
		MipFilter = "Point"
		SampleModeU = "Wrap"
		SampleModeV = "{vertical}"
	}}
}}
"""


def drawings_include() -> str:
    """The include with the sampler of the drawings of terra incognita, a texture of the game.

    It is declared as ``terra_incognita.shader`` declares the same texture, with an ``Index`` and
    the path in ``file``, so the game binds it without the mod carrying a copy of it.
    """
    return f"""# Random New World: a sampler of the game's own drawings of terra incognita (dragons
# and compasses), as terra_incognita.shader declares them, for the cover. A shader must
# have no other sampler of this Index (C172).

PixelShader =
{{
	TextureSampler {DRAWINGS_SAMPLER}
	{{
		Index = {DRAWINGS_INDEX}
		MagFilter = "Linear"
		MinFilter = "Linear"
		MipFilter = "Linear"
		SampleModeU = "Wrap"
		SampleModeV = "Clamp"
		file = "{DRAWINGS_FILE}"
		srgb = no
	}}
}}
"""


def samplers_bound(include: str) -> bool:
    """Whether every sampler of an include names an engine slot, without which it is dropped."""
    return all(
        re.search(r"\b(Ref|Index)\s*=", body) is not None for _, body in SAMPLER.findall(include)
    )


def _declared(text: str, read: Callable[[str], str | None]) -> list[tuple[str, str]] | None:
    """Every ``(name, body)`` of a sampler a shader declares itself or through its includes.

    ``read`` gives the text of an include by its name, or None when there is none; a missing
    include gives None for the whole shader. Each include is read once, as the game does.
    """
    declared: list[tuple[str, str]] = []
    seen: set[str] = set()
    pending = [text]
    while pending:
        current = pending.pop()
        names = INCLUDE_NAMES.search(current)
        for name in re.findall(r'"([^"]+)"', names.group(1)) if names else []:
            if name in seen:
                continue
            seen.add(name)
            found = read(name)
            if found is None:
                return None
            pending.append(found)
        declared.extend(SAMPLER.findall(current))
    return declared


def shader_samplers(text: str, read: Callable[[str], str | None]) -> dict[str, str | None] | None:
    """Every sampler a shader declares itself or through its includes, with its slot (``Ref``)."""
    declared = _declared(text, read)
    if declared is None:
        return None
    samplers: dict[str, str | None] = {}
    for sampler, body in declared:
        ref = REF.search(body)
        samplers[sampler] = ref.group(1) if ref else None
    return samplers


def shader_indexes(text: str, read: Callable[[str], str | None]) -> dict[int, list[str]] | None:
    """The samplers of each ``Index`` a shader declares itself or through its includes."""
    declared = _declared(text, read)
    if declared is None:
        return None
    indexes: dict[int, list[str]] = {}
    for sampler, body in declared:
        index = INDEX.search(body)
        if index:
            indexes.setdefault(int(index.group(1)), []).append(sampler)
    return indexes


def binding_problem(
    edit: ShaderEdit,
    samplers: Mapping[str, str | None] | None,
    indexes: Mapping[int, Sequence[str]] | None = None,
) -> str | None:
    """Why the patched shader would not bind as the cover expects, or None when it would.

    The samplers its call passes must read the province indirection and TI, no engine slot
    may stand under two names (C138), and the sampler of the drawings must be the only one of
    its ``Index`` (``indexes``, from ``shader_indexes``; a slot named twice fails the same way).
    """
    if samplers is None or (edit.drawings and indexes is None):
        return "an include it names is missing"
    expected = {edit.indirection: INDIRECTION_REF, edit.visibility: TI_REF}
    wrong = [name for name, ref in expected.items() if samplers.get(name) != ref]
    if wrong:
        return f"no sampler {', '.join(wrong)} of the expected slot"
    names: dict[str, list[str]] = {}
    for sampler, ref in samplers.items():
        if ref is not None:
            names.setdefault(ref, []).append(sampler)
    twice = sorted(ref for ref, found in names.items() if len(found) > 1)
    if twice:
        return f"the slots {', '.join(twice)} are named twice"
    if (
        edit.drawings
        and indexes is not None
        and list(indexes.get(DRAWINGS_INDEX, ())) != [edit.drawings]
    ):
        shared = ", ".join(indexes.get(DRAWINGS_INDEX, ())) or "none"
        return f"the Index {DRAWINGS_INDEX} of the drawings is held by {shared}"
    return None


def cover_shader(edit: ShaderEdit, text: str) -> str | None:
    """The game shader with the cover, or None when it is not laid out as expected."""
    includes = INCLUDES.match(text)
    if includes is None or any(text.count(old) != 1 for old, _ in edit.edits):
        return None
    added = "".join(f'\n\t"{name}"' for name in edit.includes)
    patched = f"Includes = {{\n{includes.group(1)}{added}\n}}\n" + text[includes.end() :]
    for old, new in edit.edits:
        patched = patched.replace(old, new)
    return patched


def hide_select_entry(text: str) -> str | None:
    """The country context menu without *Select* for a country of the New World."""
    if text.count(SELECT) != 1:
        return None
    replacement = (
        'visible = "[And3(IsLobbyOpen, IsCountryPlayable(Country.Self), '
        f'Not({NEW_WORLD_COUNTRY}))]"'
    )
    return text.replace(SELECT, replacement)


def scripted_gui_text() -> str:
    """The scripted GUI that tells the context menu whether a country is of the New World.

    The lobby can ask with no country selected. A saved optional scope, rather than a typed
    country root, lets ``exists`` reject it without evaluating a country trigger on none.
    """
    return (
        "# Random New World: is the country's capital in the generated New World?\n"
        f"{SCRIPTED_GUI} = {{\n\tsaved_scopes = {{ {COUNTRY_SCOPE} }}\n\tis_shown = {{\n"
        f"\t\texists = scope:{COUNTRY_SCOPE}.capital\n"
        f"\t\tscope:{COUNTRY_SCOPE}.capital ?= {{\n"
        f"\t\t\tcontinent = continent:{CONTINENT}\n\t\t}}\n\t}}\n}}\n"
    ) + location_scripted_gui_text()
