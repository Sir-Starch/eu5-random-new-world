from __future__ import annotations

import shutil
from importlib.metadata import distribution
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).resolve().parent.parent
RUNTIME: Final[tuple[str, ...]] = (
    "numpy",
    "pillow",
    "typer",
    "pyside6-essentials",
    "shiboken6",
    "rich",
    "markdown-it-py",
    "mdurl",
    "pygments",
    "shellingham",
    "annotated-doc",
)


def write_notices(folder: Path) -> None:
    target = folder / "licenses"
    target.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for name in RUNTIME:
        package = distribution(name)
        sources = package.metadata.get_all("Project-URL", [])
        lines.append(f"{name} {package.version}\n" + "\n".join(sources) + "\n")
        for entry in package.files or ():
            if any(word in entry.name.lower() for word in ("license", "copying", "notice")):
                source = Path(str(package.locate_file(entry)))
                if source.is_file():
                    destination = target / name / entry
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    _ = shutil.copyfile(source, destination)
    _ = (target / "packages.txt").write_text("\n".join(lines), encoding="utf-8")
    for source in (ROOT / "LICENSE", ROOT / "packaging/THIRD_PARTY_NOTICES.md"):
        _ = shutil.copyfile(source, folder / source.name)
