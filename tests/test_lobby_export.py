from pathlib import Path

import pytest

from rnw import eu5_nw_export
from rnw.eu5_lobby import INDIRECTION_REF, TI_REF, ShaderEdit


def test_binding_audit_reads_overridden_includes_before_installed_ones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = "game/main_menu/gfx/FX/mesh.shader"
    shared = "game/loading_screen/gfx/FX/shared.fxh"
    native = tmp_path / shared
    native.parent.mkdir(parents=True)
    _ = native.write_text("Code = vanilla\n", encoding="utf-8")
    edit = ShaderEdit(path, (), "Indirection", "Visibility", ())
    monkeypatch.setattr(eu5_nw_export, "SHADERS", (edit,))
    shaders = {
        path: "\n".join(
            (
                'Includes = {\n "shared.fxh"\n}',
                f"TextureSampler Indirection {{ Ref = {INDIRECTION_REF} }}",
                f"TextureSampler Visibility {{ Ref = {TI_REF} }}",
            )
        ),
        shared: f"TextureSampler Duplicate {{ Ref = {INDIRECTION_REF} }}\n",
    }

    problems = eu5_nw_export.binding_problems(tmp_path, shaders, {})

    assert len(problems) == 1
    assert INDIRECTION_REF in problems[0]
    assert "named twice" in problems[0]
