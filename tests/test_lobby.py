"""The cover of the New World at country selection, on synthetic layouts (NOT GAME VALIDATED)."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import re
import shutil
import subprocess
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.eu5_lobby import (
    CELL,
    CONTEXT_MENU,
    COVER_INCLUDE,
    DRAWINGS_FILE,
    DRAWINGS_INCLUDE,
    DRAWINGS_INDEX,
    DRAWINGS_SAMPLER,
    INDIRECTION_INCLUDE,
    INDIRECTION_REF,
    OWN_SAMPLERS,
    SCRIPTED_GUI,
    SCRIPTED_GUI_FILE,
    SHADERS,
    TI_REF,
    VISIBILITY_INCLUDE,
    ShaderEdit,
    binding_problem,
    cover_files,
    cover_grid,
    cover_include,
    cover_shader,
    cover_words,
    drawings_include,
    hide_select_entry,
    land_colour,
    mod_path,
    sampler_include,
    samplers_bound,
    scripted_gui_text,
    shader_indexes,
    shader_samplers,
    unknown_colour,
)
from rnw.pdx import parse

if TYPE_CHECKING:
    from pathlib import Path

ROWS, COLUMNS = 4 * CELL, 32 * CELL  # 128 cells: one 128-bit vector


def test_the_grid_marks_cells_the_covered_locations_fill_at_least_half_of() -> None:
    """Whole and half cells are marked, smaller shares are not; the first row is the map's first."""
    labels = np.zeros((ROWS, COLUMNS), dtype=np.int32)  # label 0: open
    labels[CELL : 2 * CELL, : 2 * CELL] = 1  # covered: two whole cells of the second row
    labels[2 * CELL : 2 * CELL + CELL // 2, -CELL:] = 2  # covered: half of the east cell
    labels[3 * CELL : 3 * CELL + 4, :CELL] = 2  # covered: an eighth of a cell
    labels[:CELL, 5 * CELL : 6 * CELL] = 3  # open
    covered = np.array([False, True, True, False])
    grid = cover_grid(labels, covered)
    assert grid.shape == (ROWS // CELL, COLUMNS // CELL)
    assert grid[1, :2].all()
    assert grid[2, -1]
    assert not grid[3, 0]
    assert np.count_nonzero(grid) == 3


def test_the_grid_refuses_a_map_that_cells_do_not_tile() -> None:
    """A map size that is not a multiple of the cell is a defect, not a smaller grid."""
    labels = np.zeros((ROWS + 1, COLUMNS), dtype=np.int32)
    with pytest.raises(ValueError, match="multiple"):
        _ = cover_grid(labels, np.array([True]))


def test_the_words_hold_the_grid_row_by_row_from_the_lowest_bit() -> None:
    """The first cell is bit 0 of word 0, the 33rd bit 0 of word 1."""
    grid = np.zeros((4, 64), dtype=bool)
    grid[0, 0] = grid[0, 32] = grid[1, 0] = True
    words = cover_words(grid)
    assert words[:3] == [1, 1, 1]
    assert sum(words) == 3


def test_the_land_colour_comes_from_the_graphics_define_once() -> None:
    """HSV to RGB; a missing or doubled define gives nothing."""
    define = "\tFLAT_MAP_COLOR_LAND_HSV = { 0.0 1.0 0.5 }\t\t#Base color of land\n"
    assert land_colour(define) == (0.5, 0.0, 0.0)
    assert land_colour("FLAT_MAP_COLOR_WATER_BLUE_HSV = { 0.58 0.50 0.46 }") is None
    assert land_colour(define + define) is None


def test_the_unknown_colour_is_the_land_colour_half_grey_at_a_tenth() -> None:
    """Grey stays grey at a tenth; a pure red moves halfway to its grey."""
    assert unknown_colour((1.0, 1.0, 1.0)) == pytest.approx((0.1, 0.1, 0.1))
    red = unknown_colour((1.0, 0.0, 0.0))
    assert red == pytest.approx(((1.0 + 0.299) / 2 / 10, 0.299 / 2 / 10, 0.299 / 2 / 10))


def _shader(edit: ShaderEdit) -> str:
    """A shader with the include block first and every anchor of the edit once."""
    anchors = "".join(f"{old}\n}}\n" if old.startswith("Effect ") else old for old, _ in edit.edits)
    return f'Includes = {{\n\t"a.fxh"\n}}\n\nPixelShader =\n{{\n{anchors}}}\n'


@pytest.mark.parametrize("edit", SHADERS, ids=lambda edit: edit.path.rsplit("/", 1)[-1])
def test_each_shader_takes_its_includes_and_edits_and_is_refused_otherwise(
    edit: ShaderEdit,
) -> None:
    """The includes join the first block; every anchor is replaced; another layout is refused."""
    text = _shader(edit)
    patched = cover_shader(edit, text)
    assert patched is not None
    added = "".join(f'\t"{name}"\n' for name in edit.includes)
    assert patched.startswith(f'Includes = {{\n\t"a.fxh"\n{added}}}\n')
    assert edit.includes[-1] == COVER_INCLUDE
    replacements = [replacement for _, replacement in edit.edits]
    expected_notes = sum(replacement.count("Random New World") for replacement in replacements)
    arguments = ", ".join(filter(None, (edit.indirection, edit.visibility, edit.drawings)))
    expected_calls = sum(replacement.count(f"{arguments} )") for replacement in replacements)
    assert patched.count("Random New World") == expected_notes
    assert patched.count(f"{arguments} )") == expected_calls
    assert all(replacement.strip() in patched for replacement in replacements)
    assert patched.count("{") == patched.count("}")
    assert patched.count("(") == patched.count(")")
    first = edit.edits[0][0]
    assert cover_shader(edit, text.replace(first, "")) is None
    assert cover_shader(edit, text + first) is None
    assert cover_shader(edit, "\n" + text) is None


@pytest.mark.parametrize("edit", SHADERS, ids=lambda edit: edit.path.rsplit("/", 1)[-1])
def test_a_shader_adds_a_sampler_of_its_own_only_for_a_slot_it_lacks(edit: ShaderEdit) -> None:
    """Own samplers are the ones the call passes; the others the game's shader has (C138)."""
    own = {sampler: name for name, (sampler, _) in OWN_SAMPLERS.items()}
    for sampler in (edit.indirection, edit.visibility):
        assert (sampler in own) == (own.get(sampler) in edit.includes)
    # The drawings are always the mod's own, and only the shaders that paint read them.
    assert (DRAWINGS_INCLUDE in edit.includes) == bool(edit.drawings)
    assert edit.drawings in ("", DRAWINGS_SAMPLER)


def _reader(files: dict[str, str]):  # noqa: ANN202 - a test's small lookup
    return files.get


SAMPLE = 'TextureSampler {name}\n{{\n\tRef = {ref}\n\tMagFilter = "Point"\n}}\n'


def test_the_samplers_of_a_shader_are_found_through_its_includes_once_each() -> None:
    """Nested includes are followed once; a missing include gives nothing."""
    files = {
        "a.fxh": 'Includes = {\n\t"b.fxh"\n}\n' + SAMPLE.format(name="A", ref="SlotA"),
        "b.fxh": 'Includes = {\n\t"a.fxh"\n}\n' + SAMPLE.format(name="B", ref="SlotB"),
    }
    shader = 'Includes = {\n\t"a.fxh"\n\t"b.fxh"\n}\n' + SAMPLE.format(name="C", ref="SlotC")
    assert shader_samplers(shader, _reader(files)) == {"A": "SlotA", "B": "SlotB", "C": "SlotC"}
    assert shader_samplers('Includes = {\n\t"x.fxh"\n}\n', _reader(files)) is None


def test_a_slot_named_twice_or_a_missing_sampler_is_a_binding_problem() -> None:
    """As in 0.9.19: a second sampler of the province indirection is refused (C138)."""
    edit = SHADERS[0]
    fine = {edit.indirection: INDIRECTION_REF, edit.visibility: TI_REF, "Other": "Slot"}
    mine = {DRAWINGS_INDEX: [DRAWINGS_SAMPLER]}
    assert binding_problem(edit, fine, mine) is None
    assert binding_problem(edit, None, mine) is not None
    twice = binding_problem(edit, fine | {"RnwProvinceIndirection": INDIRECTION_REF}, mine)
    assert twice is not None
    assert INDIRECTION_REF in twice
    missing = binding_problem(edit, {edit.visibility: TI_REF}, mine)
    assert missing is not None
    assert edit.indirection in missing


def test_the_include_holds_the_grid_north_first_and_declares_no_sampler() -> None:
    """The map's size, the grid, the flip of z and the colour; the shader passes the samplers."""
    grid = np.zeros((ROWS // CELL, COLUMNS // CELL), dtype=bool)
    grid[0, 0] = True
    include = cover_include((ROWS, COLUMNS), grid, (0.1, 0.05, 0.025))
    assert f"float2( {COLUMNS}.0f, {ROWS}.0f )" in include
    assert f"int2( {COLUMNS // CELL}, {ROWS // CELL} )" in include
    assert f"static const uint4 RnwCoverWords[{grid.size // 128}]" in include
    assert "uint4( 0x00000001, 0x00000000, 0x00000000, 0x00000000 )" in include
    assert "RnwMapSize.y - WorldSpacePosXZ.y" in include
    # The grid's edge rows stop at the map's edge: the table of its frame is not the New World.
    assert "WorldSpacePosXZ.y < 0.0f || WorldSpacePosXZ.y > RnwMapSize.y" in include
    assert "float3( 0.100000f, 0.050000f, 0.025000f )" in include
    assert shader_samplers(include, _reader({})) == {}
    assert "Includes" not in include
    assert include.count("{") == include.count("}")
    assert include.count("[[") == include.count("]]") == 1
    with pytest.raises(ValueError, match="vectors"):
        _ = cover_include((ROWS, COLUMNS), grid[:, :-1], (0.0, 0.0, 0.0))


@pytest.mark.parametrize("name", list(OWN_SAMPLERS))
def test_an_own_sampler_include_declares_one_bound_sampler(name: str) -> None:
    """One sampler, of the slot it stands for, which the game declares."""
    text = sampler_include(name)
    sampler, ref = OWN_SAMPLERS[name]
    assert shader_samplers(text, _reader({})) == {sampler: ref}
    assert samplers_bound(text)
    assert "File" not in text
    assert {VISIBILITY_INCLUDE, INDIRECTION_INCLUDE} == set(OWN_SAMPLERS)


def test_the_drawings_take_an_index_that_no_other_sampler_of_the_shader_holds() -> None:
    """The drawings' sampler must be alone at its Index, or the shader is refused (C172)."""
    edit = SHADERS[0]
    fine = {edit.indirection: INDIRECTION_REF, edit.visibility: TI_REF}
    assert edit.drawings == DRAWINGS_SAMPLER
    assert binding_problem(edit, fine, {DRAWINGS_INDEX: [DRAWINGS_SAMPLER]}) is None
    held = binding_problem(edit, fine, {DRAWINGS_INDEX: [DRAWINGS_SAMPLER, "Other"]})
    assert held is not None
    assert "Other" in held
    assert binding_problem(edit, fine, {}) is not None
    assert binding_problem(edit, fine, None) is not None
    assert binding_problem(edit, fine, {DRAWINGS_INDEX + 1: ["Other"]}) is not None
    # A shader that only clips takes no drawings and is not asked for an Index.
    plain = next(shader for shader in SHADERS if not shader.drawings)
    assert (
        binding_problem(
            plain,
            {plain.indirection: INDIRECTION_REF, plain.visibility: TI_REF},
        )
        is None
    )


def test_the_indexes_of_a_shader_are_found_through_its_includes() -> None:
    """Each Index lists its samplers, a Ref-only sampler is left out, a missing include fails."""
    files = {
        "a.fxh": 'TextureSampler A\n{\n\tIndex = 2\n\tfile = "x.dds"\n}\n'
        + SAMPLE.format(name="R", ref="SlotR"),
    }
    shader = (
        'Includes = {\n\t"a.fxh"\n}\n'
        "TextureSampler B\n{\n\tIndex = 2\n}\nTextureSampler C\n{\n\tIndex = 5\n}\n"
    )
    found = shader_indexes(shader, _reader(files))
    assert found is not None
    assert {index: sorted(names) for index, names in found.items()} == {
        2: ["A", "B"],
        5: ["C"],
    }
    assert shader_indexes('Includes = {\n\t"x.fxh"\n}\n', _reader(files)) is None


def test_the_drawings_include_names_the_games_texture_with_an_index() -> None:
    """The sampler is bound by its Index and carries the path of the game's texture, no copy."""
    text = drawings_include()
    assert samplers_bound(text)
    assert shader_indexes(text, _reader({})) == {DRAWINGS_INDEX: [DRAWINGS_SAMPLER]}
    assert f'file = "{DRAWINGS_FILE}"' in text
    assert DRAWINGS_FILE.startswith("gfx/map/flatmap/")
    assert text.count("{") == text.count("}")
    assert "Ref" not in text


def test_a_sampler_with_only_a_file_is_not_bound() -> None:
    """The game drops a sampler that names neither a Ref nor an Index (C137)."""
    dropped = 'TextureSampler Mask\n{\n\tMagFilter = "Linear"\n\tFile = "gfx/a.dds"\n}\n'
    kept = 'TextureSampler Noise\n{\n\tRef = FlatMap3\n\tfile = "gfx/b.dds"\n}\n'
    assert not samplers_bound(dropped)
    assert samplers_bound(kept)
    assert not samplers_bound(kept + dropped)


def test_the_cover_files_are_the_mods_own_and_the_changed_game_files() -> None:
    """Paths relative to the mod, each once, with every changed shader and include."""
    files = cover_files()
    assert len(set(files)) == len(files)
    assert not any(path.startswith("game/") for path in files)
    assert {mod_path(edit.path) for edit in SHADERS} <= set(files)
    assert {mod_path(CONTEXT_MENU), SCRIPTED_GUI_FILE} <= set(files)
    for name in (COVER_INCLUDE, DRAWINGS_INCLUDE, *OWN_SAMPLERS):
        assert f"main_menu/gfx/FX/{name}" in files
    assert not any(path.endswith(".dds") for path in files)
    assert "in_game/gui/multiplayer_lobby.gui" in files
    assert "in_game/gui/map_markers.gui" in files


def test_the_context_menu_loses_select_for_a_country_of_the_new_world() -> None:
    """The one expected entry asks the mod's scripted GUI, which reads the capital's continent."""
    entry = 'visible = "[And(IsLobbyOpen, IsCountryPlayable(Country.Self))]"'
    patched = hide_select_entry(f"entry = {{\n\t{entry}\n}}\n")
    assert patched is not None
    assert entry not in patched
    assert "And3(IsLobbyOpen, IsCountryPlayable(Country.Self), Not(" in patched
    assert f"GetScriptedGui('{SCRIPTED_GUI}').IsShown(GuiScope.SetRoot(Country.MakeScope).End)" in (
        patched
    )
    assert "GetContinent" not in patched
    assert "GameRule" not in patched
    assert hide_select_entry("nothing here") is None
    assert hide_select_entry(entry + entry) is None
    assert CONTEXT_MENU.endswith("context_menu.gui")


def test_the_scripted_gui_reads_the_capitals_continent() -> None:
    """A country scope, shown when the capital is on the New World's continent; no game rule."""
    gui = parse(scripted_gui_text()).block(SCRIPTED_GUI)
    assert gui is not None
    scope = gui.first("scope")
    assert scope is not None
    assert scope.value == "country"
    assert gui.block("is_shown") is not None
    assert "capital.continent = continent:america" in scripted_gui_text()
    assert "has_game_rule" not in scripted_gui_text()


# Stand-ins for the game's sampler macros: a sampler is a texture read through one sampler state.
HARNESS_HEAD = """SamplerState RnwHarnessSampler : register(s0);
#define PdxTextureSampler2D Texture2D
#define PdxTex2D(samp, uv) (samp).Sample(RnwHarnessSampler, (uv))
#define PdxTex2DLod0(samp, uv) (samp).SampleLevel(RnwHarnessSampler, (uv), 0)
#define PdxTex2DLoad0(samp, uv) (samp).Load(int3((uv), 0))
float2 vec2(float v) { return float2(v, v); }
"""
HARNESS_MAIN = """
struct RnwHarnessInput { float4 Pos : SV_Position; float3 WorldSpacePos : TEXCOORD0; };
float4 main(RnwHarnessInput Input) : SV_Target
{
\tfloat2 Position = Input.WorldSpacePos.xz;
\tfloat3 Color = RnwCovered( float3( 1.0f, 1.0f, 1.0f ), Position, RnwProvinceIndirection,
\t\tRnwVisibility, RnwDrawings );
\treturn float4( Color, 1.0f - RnwCover( Position, RnwProvinceIndirection, RnwVisibility ) );
}
"""


def _harness(include: str) -> str:
    """The include's code with the mod's samplers declared, as the game declares bound ones."""
    samplers = [sampler for sampler, _ in OWN_SAMPLERS.values()] + [DRAWINGS_SAMPLER]
    declared = [
        f"Texture2D {sampler} : register(t{slot});" for slot, sampler in enumerate(samplers)
    ]
    code = re.search(r"\[\[(.*)\]\]", include, re.DOTALL)
    assert code is not None
    return "\n".join(declared) + "\n" + HARNESS_HEAD + code.group(1) + HARNESS_MAIN


def _compile(source: Path) -> subprocess.CompletedProcess[str]:
    command = ["glslangValidator", "-D", "-V", "-S", "frag", "-e", "main", str(source)]
    return subprocess.run(  # noqa: S603 - a local compiler on a file of the test's own
        command, capture_output=True, text=True, check=False, cwd=source.parent
    )


@pytest.mark.skipif(shutil.which("glslangValidator") is None, reason="no glslangValidator")
def test_the_include_compiles_as_hlsl_for_a_full_size_map(tmp_path: Path) -> None:
    """The include's code compiles to SPIR-V, the samplers passed in as the shaders pass them."""
    rows, columns = 8192, 16384
    grid = np.random.default_rng(3).random((rows // CELL, columns // CELL)) < 0.3
    include = cover_include((rows, columns), grid, unknown_colour((1.0, 0.59, 0.3)))
    source = tmp_path / "cover.hlsl"
    _ = source.write_text(_harness(include), encoding="utf-8")
    result = _compile(source)
    assert result.returncode == 0, result.stdout + result.stderr
    _ = source.write_text(_harness(include).replace("RnwVisibility )", "Missing )"), "utf-8")
    assert _compile(source).returncode != 0
