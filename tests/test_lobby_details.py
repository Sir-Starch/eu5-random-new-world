from __future__ import annotations

from rnw.eu5_lobby import COVER_INCLUDE, SHADERS, cover_files, cover_shader


def test_cover_does_not_override_the_base_used_by_loading_art_and_portrait_scenes() -> None:
    files = cover_files()
    assert "loading_screen/gfx/FX/pdxmesh_base.fxh" not in files, (
        "shared scene shaders still receive the map-only RnwVisibility reference"
    )
    assert "main_menu/gfx/FX/rnw_map_mesh.fxh" in files


def test_only_the_map_mesh_shader_uses_the_private_covered_base() -> None:
    edit = next(edit for edit in SHADERS if edit.path.endswith("/pdxmesh.shader"))
    source = 'Includes = {\n\t"pdxmesh_base.fxh"\n}\n'
    source += "\t\t\treturn TerrainShader( InputTerrain, Input.Normal );\n"
    patched = cover_shader(edit, source)
    assert patched is not None
    assert '"pdxmesh_base.fxh"' not in patched
    assert '"rnw_map_mesh.fxh"' in patched
    assert '"rnw_new_world_visibility.fxh"' in patched.split("}\n", 1)[0]
    private = next(edit for edit in SHADERS if edit.path.endswith("/rnw_map_mesh.fxh"))
    assert private.source_path == "game/loading_screen/gfx/FX/pdxmesh_base.fxh"
    assert all(
        not edit.path.endswith(
            (
                "/pdxmesh_without_terrain.shader",
                "/pdxmesh_pulse_uv.shader",
                "/pdxmesh_rotate_uv.shader",
                "/pdxmesh_emissive.shader",
            )
        )
        for edit in SHADERS
    )


def test_close_zoom_shader_families_clip_the_unknown_new_world() -> None:
    required = {
        "tree.shader": (
            "CalculateSunLighting( MaterialProps, LightingProps, EnvironmentMap );",
            "float3 Color = CalculateCustomLeafLighting(",
        ),
        "river_surface.shader": ("return PS_Return( FinalColor, Material );",),
        "river_bottom.shader": ("return Out;",),
        "city_generated_geometry.shader": (
            "return PS_Return( Color, Alpha * Opacity * FlatmapFade.y, MaterialProps );",
        ),
        "pdxmesh.shader": ("return TerrainShader( InputTerrain, Input.Normal );",),
        "rnw_map_mesh.fxh": ("float Alpha = Diffuse.a;",),
        "pdxmesh_decal.shader": (
            "return float4( Color, Alpha );",
            "return float4( Color, Diffuse.a );",
        ),
        "worldtext.shader": ("return MixedColor;",),
    }
    edits = {edit.path.rsplit("/", 1)[-1]: edit for edit in SHADERS}

    for filename, functions in required.items():
        assert filename in edits, f"close-zoom shader {filename} still draws through the cover"
        edit = edits[filename]
        assert COVER_INCLUDE in edit.includes
        patched = cover_shader(
            edit,
            'Includes = {\n\t"base.fxh"\n}\n\n' + "".join(anchor for anchor, _ in edit.edits),
        )
        assert patched is not None
        anchors = "".join(anchor for anchor, _ in edit.edits)
        for anchor in functions:
            assert anchor in anchors, f"{filename} no longer pins the {anchor} rendering point"
        assert "RnwCover(" in "".join(replacement for _, replacement in edit.edits), (
            f"{filename} does not clip detail fragments where the New World is unknown"
        )


def test_tree_shadow_effects_use_world_matrix_cover_checks() -> None:
    edit = next(edit for edit in SHADERS if edit.path.endswith("/tree.shader"))
    patches = "\n".join(replacement for _, replacement in edit.edits)
    assert patches.count("PixelShader = PS_RnwTreeShadow") == 5
    assert patches.count("PixelShader = PS_RnwTreeMapObjectShadow") == 5
    assert "PdxMeshGetWorldMatrix( uint( Input.UV_InstanceIndex.z + 0.5 ) )" in patches
    assert "UnpackAndGetMapObjectWorldMatrix( Input.Index24_Packed1_Opacity6_Sign1 )" in patches
    assert patches.count("clip( 0.001f - RnwCover(") == 4
    assert "clip( Alpha - 0.5f );" in patches
