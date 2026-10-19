"""Shader patches on synthetic shader text."""

from __future__ import annotations

from rnw.eu5_shaders import CALL, INDENT, soften_terra_incognita


def test_terra_incognita_patch_replaces_the_single_call() -> None:
    """The bilinear line gains a guarded multi-sample blend; unknown layouts are skipped."""
    text = f"\t\t\t\t#else\n{INDENT}{CALL}\n\t\t\t\t#endif\n"
    patched = soften_terra_incognita(text)
    assert patched is not None
    assert patched.count(CALL) == 1
    assert patched.count("GetBilinear(") == 1 + 4 + 12
    assert "Visibility = RnwSum / 13.0f;" in patched
    assert patched.count("{") == patched.count("}")
    assert patched.count("(") == patched.count(")")
    assert soften_terra_incognita(text + text) is None
    assert soften_terra_incognita("float Visibility = 1.0;\n") is None
