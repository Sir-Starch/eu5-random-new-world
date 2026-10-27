"""The hub builder's decisions, on synthetic folders (the build itself needs MinGW and uv)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import hub
import pytest

from rnw.app import install

if TYPE_CHECKING:
    from pathlib import Path


def test_qt_keeps_what_the_window_imports_and_nothing_else() -> None:
    """Core, Gui, Widgets, their bindings, the runtime and two platform plugins stay."""
    kept = (
        "__init__.py",
        "Qt6Core.dll",
        "Qt6Widgets.dll",
        "QtGui.pyd",
        "msvcp140_1.dll",
        "vcruntime140.dll",
        "support/signature/loader.py",
        "plugins/platforms/qwindows.dll",
        "plugins/platforms/qoffscreen.dll",
        "plugins/styles/qmodernwindowsstyle.dll",
    )
    dropped = (
        "Qt6Quick.dll",
        "Qt6Network.dll",
        "opengl32sw.dll",
        "designer.exe",
        "QtCore.pyi",
        "plugins/platforms/qdirect2d.dll",
        "plugins/imageformats/qjpeg.dll",
        "qml/QtQuick/Controls/impl.dll",
        "translations/qtbase_de.qm",
    )
    assert all(hub.keeps_qt(name) for name in kept)
    assert not any(hub.keeps_qt(name) for name in dropped)


def test_pruning_removes_the_rest_and_refuses_a_qt_without_the_window(tmp_path: Path) -> None:
    """Unwanted files and emptied folders go; a missing needed library is an error."""
    folder = tmp_path / "site" / "PySide6"
    needed = [name for name in hub.QT_KEPT if "*" not in name]
    for name in [*needed, "Qt6Quick.dll", "qml/QtQuick/a.dll", "msvcp140.dll"]:
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_bytes(b"x" * 10)
    removed = hub.prune_qt(tmp_path / "site")
    assert removed == 20
    assert not (folder / "qml").exists()
    assert (folder / "msvcp140.dll").is_file()
    (folder / "Qt6Widgets.dll").unlink()
    with pytest.raises(hub.BuildError, match="Qt6Widgets"):
        _ = hub.prune_qt(tmp_path / "site")


def test_versions_become_four_resource_numbers() -> None:
    """MAJOR.MINOR.PATCH gets a zero; anything else stops the build."""
    assert hub.version_fields("0.9.13") == (0, 9, 13, 0)
    for bad in ("0.9", "1.0.0-rc1", "1.0.0.1", "a.b.c"):
        with pytest.raises(hub.BuildError):
            _ = hub.version_fields(bad)


def test_the_hub_is_a_test_mod_the_installer_may_replace(tmp_path: Path) -> None:
    """Its metadata is UTF-8 with BOM, its id an rnw_exp_* name the installer accepts."""
    text = hub.metadata("0.9.13").decode("utf-8-sig")
    payload = cast("dict[str, object]", json.loads(text))
    assert (payload["id"], payload["version"]) == (hub.MOD_ID, "0.9.13")
    assert payload["name"] == "Random New World Generator"
    assert "test" not in cast("str", payload["name"]).lower()
    assert "not game validated" not in cast("str", payload["name"]).lower()
    assert "test" not in cast("str", payload["short_description"]).lower()
    assert "not game validated" not in cast("str", payload["short_description"]).lower()
    mod = tmp_path / hub.MOD_ID
    (mod / ".metadata").mkdir(parents=True)
    _ = (mod / ".metadata" / "metadata.json").write_bytes(hub.metadata("0.9.13"))
    assert install.is_rnw_mod(mod)


def test_python_imports_only_from_the_site_folder() -> None:
    """The ._pth names the standard library, the interpreter folder and ../site."""
    assert hub.PATH_LINES == ("python312.zip", ".", "../site", "import site")


def test_the_hub_holds_exactly_three_programs(tmp_path: Path) -> None:
    """Entry-point scripts are removed; any other program is an error."""
    for name in [*hub.PROGRAMS, "generator/site/bin/f2py", "generator/site/Scripts/x.exe"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_bytes(b"MZ")
    with pytest.raises(hub.BuildError, match="Programs"):
        hub.check_programs(tmp_path)
    hub.remove_scripts(tmp_path / "generator" / "site")
    hub.check_programs(tmp_path)
    _ = (tmp_path / "generator" / "run.bat").write_text("@echo off\n", encoding="utf-8")
    with pytest.raises(hub.BuildError, match=r"run\.bat"):
        hub.check_programs(tmp_path)
