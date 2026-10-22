"""What needs the game and what does not, enforced (ADR 0010, H).

The viewer of a world (its record, atlas, world files, library, maps) must work where EU5 is not
installed, and must never be a way for a game file to travel. So the modules that make it never
import, even through other modules, the ones that read the game; and no public release holds a
file of the game.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import cast

import allowlist
import pytest

ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "src"
# The modules of the viewer: what opens a world, its maps and its files without the game.
VIEWER = (
    "rnw.atlas",
    "rnw.worldfile",
    "rnw.record",
    "rnw.epoch",
    "rnw.layers",
    "rnw.worldname",
    "rnw.tagfont",
    "rnw.pictures",
    "rnw.png",
    "rnw.pngread",
    "rnw.settings",
    "rnw.bundle",
    "rnw.app.worldcode",
    "rnw.app.library",
    "rnw.app.exchange",
    "rnw.app.paths",
    "rnw.app.preferences",
    "rnw.app.logs",
    "rnw.app.diagnostics",
    "rnw.app.install",
    "rnw.app.session",
    "rnw.gui.maps",
    "rnw.gui.preview",
    "rnw.gui.text",
)
# What reads the game: the export's readers, the map contract, the inputs, and what uses them.
GAME_SIDE_PREFIXES = ("rnw.eu5_",)
GAME_SIDE = frozenset(
    {
        "rnw.contract",
        "rnw.geography",
        "rnw.inputs",
        "rnw.app.service",
        "rnw.app.transfer",
        "rnw.cli",
        "rnw.gui.controller",
        "rnw.gui.window",
    }
)


def _module_file(name: str) -> Path | None:
    path = SOURCE.joinpath(*name.split("."))
    if path.with_suffix(".py").is_file():
        return path.with_suffix(".py")
    if (path / "__init__.py").is_file():
        return path / "__init__.py"
    return None


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _runtime_imports(path: Path) -> set[str]:
    """The project modules a file imports when it runs (not under ``if TYPE_CHECKING``)."""
    found: set[str] = set()

    def walk(nodes: list[ast.stmt]) -> None:
        for node in nodes:
            if isinstance(node, ast.If) and _is_type_checking(node.test):
                walk(node.orelse)
                continue
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names if alias.name.startswith("rnw"))
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("rnw"):
                found.add(node.module)
                found.update(
                    f"{node.module}.{alias.name}"
                    for alias in node.names
                    if _module_file(f"{node.module}.{alias.name}") is not None
                )
            for field in ("body", "orelse", "finalbody", "handlers"):
                children = cast_list(getattr(node, field, None))
                walk(children)

    walk(ast.parse(path.read_text(encoding="utf-8")).body)
    return found


def cast_list(value: object) -> list[ast.stmt]:
    """The statements in a field of a node, or none."""
    if not isinstance(value, list):
        return []
    items: list[ast.stmt] = []
    for item in cast("list[object]", value):
        if isinstance(item, ast.stmt):
            items.append(item)
        elif isinstance(item, ast.ExceptHandler):
            items.extend(item.body)
    return items


def _reach(start: str) -> dict[str, str]:
    """Every project module ``start`` imports, through any depth, with who imported it first."""
    seen: dict[str, str] = {start: ""}
    queue = [start]
    while queue:
        current = queue.pop()
        file = _module_file(current)
        if file is None:
            continue
        for name in sorted(_runtime_imports(file)):
            if name not in seen:
                seen[name] = current
                queue.append(name)
    return seen


def _is_game_side(name: str) -> bool:
    return name in GAME_SIDE or name.startswith(GAME_SIDE_PREFIXES)


@pytest.mark.parametrize("module", VIEWER)
def test_a_viewer_module_never_reaches_the_code_that_reads_the_game(module: str) -> None:
    """No chain of imports leads from the viewer to a reader of the game."""
    assert _module_file(module) is not None, f"{module} is not a module of the project"
    reached = _reach(module)
    bad = sorted(name for name in reached if _is_game_side(name))
    assert not bad, f"{module} reaches {bad[0]} through {reached[bad[0]]}"


def test_the_check_would_notice_a_chain_to_the_game() -> None:
    """The control: the application layer does reach the game's readers, and the test sees it."""
    reached = _reach("rnw.app.service")
    assert any(name.startswith("rnw.eu5_") for name in reached)
    assert _is_game_side("rnw.eu5_map")
    assert not _is_game_side("rnw.atlas")


def test_the_viewer_set_has_no_stray_names() -> None:
    """Every module named exists, so a rename cannot silently shrink the check."""
    assert all(_module_file(name) is not None for name in VIEWER)
    assert len(set(VIEWER)) == len(VIEWER)


def test_no_tracked_file_is_a_file_of_the_game() -> None:
    """The repository holds no game folder, shader or raster of the game's kind."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],  # noqa: S607
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git is not available")
    problems = allowlist.problems(listed, ignore=allowlist.REPOSITORY_NOTES)
    assert not problems, problems[:5]


def test_the_allowlist_refuses_what_looks_like_the_game(tmp_path: Path) -> None:
    """Game folders, shaders, rasters and generated worlds in a release are named."""
    for relative in (
        "generator/site/rnw/__init__.pyc",
        "generator/python/python.exe",
        "LICENSE",
        "game/main_menu/gfx/FX/pdxterrain2.shader",
        "app/jomini/x.txt",
        "app/rnw_new_world_cover.fxh",
        "app/terrain.dds",
        "generated/rnw_exp_world_x/world.json",
        "local_data/baseline/error.log",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_bytes(b"x")
    found = allowlist.problems_in_folder(tmp_path)
    flagged = {item.split(":")[0] for item in found}
    assert flagged == {
        "game/main_menu/gfx/FX/pdxterrain2.shader",
        "app/jomini/x.txt",
        "app/rnw_new_world_cover.fxh",
        "app/terrain.dds",
        "generated/rnw_exp_world_x/world.json",
        "local_data/baseline/error.log",
    }
    assert allowlist.problems(["README.md", "src/rnw/atlas.py", "docs/adr/0010.md"]) == []


def test_a_wheel_may_have_any_folder_but_not_a_shader(tmp_path: Path) -> None:
    """Vendored libraries are held to the kind-of-file rule only."""
    for relative in (
        "generator/site/somelib/game/engine.py",
        "generator/site/somelib/generated/x.py",
        "generator/site/somelib/shaders/bad.shader",
        "generator/python/python.exe",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_bytes(b"x")
    found = allowlist.problems_in_folder(tmp_path)
    assert [item.split(":")[0] for item in found] == ["generator/site/somelib/shaders/bad.shader"]


def test_the_hub_build_runs_the_check(tmp_path: Path) -> None:
    """The hub's own decision refuses a folder with a game file in it."""
    import hub  # noqa: PLC0415 - the packaging script, imported by path

    clean = tmp_path / "clean"
    (clean / "generator").mkdir(parents=True)
    _ = (clean / "LICENSE").write_text("x", encoding="utf-8")
    hub.check_no_game_files(clean)
    dirty = tmp_path / "dirty"
    (dirty / "in_game").mkdir(parents=True)
    _ = (dirty / "in_game" / "locations.png").write_bytes(b"x")
    with pytest.raises(hub.BuildError, match="looks like a file of the game"):
        hub.check_no_game_files(dirty)
