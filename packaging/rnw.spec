# PyInstaller spec of the application (a Python file; run through packaging/build.py).
# ruff: noqa
# pyright: basic
import sys
from pathlib import Path

root = Path(SPECPATH).resolve().parent.parent  # build/pyinstaller -> project
sys.path.insert(0, str(root / "packaging"))
import layout  # noqa: E402

analysis = Analysis(
    [str(root / "packaging" / "entry.py")],
    pathex=[str(root / "src")],
    # The translation catalogs are data files of the package (rnw.translations).
    datas=[(str(root / "src" / "rnw" / "locale"), "rnw/locale")],
    excludes=list(layout.EXCLUDED_MODULES),
)
analysis.binaries = [item for item in analysis.binaries if layout.wanted(item[0])]
analysis.datas = [item for item in analysis.datas if layout.wanted(item[0])]
archive = PYZ(analysis.pure)
program = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=layout.NAME,
    console=False,
)
COLLECT(program, analysis.binaries, analysis.datas, name=layout.NAME)
