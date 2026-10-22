from __future__ import annotations

from rnw.eu5_lobby import COVER_INCLUDE, SHADERS, cover_shader


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
        "pdxmesh_base.fxh": ("float Alpha = Diffuse.a;",),
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
