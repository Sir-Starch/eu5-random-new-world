"""End-to-end candidate export against a synthetic EU5-shaped installation."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest
from PIL import Image
from typer.testing import CliRunner

from rnw.cli import app
from rnw.eu5_export import STATUS, UnsupportedBuildError, export_candidate
from rnw.eu5_map import LOCATIONS, RIVERS, load_map, read_class_lists
from rnw.model import CellClass
from tests.fixtures_eu5 import FRAME, RIVER_INDEX, fixture_settings, make_install

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.model import World


@pytest.fixture(name="install")
def fixture_install(tmp_path: Path) -> tuple[Path, World, str]:
    """A synthetic installation and its map-contract digest."""
    game = tmp_path / "game_install"
    world, digest = make_install(game)
    return game, world, digest


def _pixels(path: Path) -> NDArray[np.uint8]:
    with Image.open(path) as image:
        return np.asarray(image).copy()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _export(game: Path, output: Path, digest: str, seed: int = 3) -> dict[str, object]:
    return export_candidate(
        game, output, seed=seed, settings=fixture_settings(), accept_build=digest
    )


def test_adapter_reads_classes_points_and_unused_colours(install: tuple[Path, World, str]) -> None:
    """Class lists, locators and the unused colour declaration are read as observed."""
    game, world, _ = install
    game_map = load_map(game)
    assert game_map.keys[-1] == "unused_extra"
    assert len(game_map.keys) == len(world.cells) + 1
    assert np.array_equal(game_map.labels, world.labels)
    seas = read_class_lists(game / "game/in_game/map_data/default.map")["sea_zones"]
    assert len(seas) == int(np.count_nonzero(world.class_table(CellClass.SEA)))
    city = [point for point in game_map.points if point.source.endswith("locators_city.txt")]
    assert city
    assert all(world.cells[int(world.labels[p.y, p.x])].key == p.key for p in city)


def test_export_moves_coast_and_preserves_everything_else(
    install: tuple[Path, World, str], tmp_path: Path
) -> None:
    """The staged mod changes only American coast pixels inside the window."""
    game, world, digest = install
    output = tmp_path / "generated/rnw_exp_test"
    report = _export(game, output, digest)
    assert report["status"] == STATUS
    changes = cast("dict[str, int]", report["changes"])
    assert changes["to_land_px"] > 0
    assert changes["to_sea_px"] > 0
    mod = output / "rnw_exp_test"
    metadata = json.loads((mod / ".metadata/metadata.json").read_text(encoding="utf-8-sig"))
    assert metadata["id"] == "rnw_exp_test"
    assert STATUS in (output / "report.md").read_text(encoding="utf-8")
    before = _pixels(game / LOCATIONS)
    after = _pixels(mod / "in_game/map_data/locations.png")
    changed = np.any(before != after, axis=2)
    assert int(np.count_nonzero(changed)) == changes["changed_px"]
    old_world = np.array([cell.protected for cell in world.cells])[world.labels]
    assert not np.any(changed & old_world)
    assert not np.any(changed[:FRAME])
    assert not np.any(changed[:, :FRAME])
    rivers_before = _pixels(game / RIVERS)
    rivers_after = _pixels(mod / "in_game/map_data/rivers.png")
    assert np.array_equal(rivers_before != rivers_after, changed)
    assert int(np.count_nonzero(rivers_after == RIVER_INDEX)) == int(
        np.count_nonzero(rivers_before == RIVER_INDEX)
    )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    outputs = {record["path"]: record for record in manifest["files"]}
    record = outputs["rnw_exp_test/in_game/map_data/locations.png"]
    assert record["input_sha256"] == _digest(game / LOCATIONS)
    assert record["sha256"] == _digest(mod / "in_game/map_data/locations.png")


def test_same_inputs_repeat_bytes_and_other_seed_differs(
    install: tuple[Path, World, str], tmp_path: Path
) -> None:
    """Identical seed/settings/build give identical rasters; another seed does not."""
    game, _, digest = install
    first = tmp_path / "generated/rnw_exp_a"
    second = tmp_path / "generated/rnw_exp_b"
    third = tmp_path / "generated/rnw_exp_c"
    _ = _export(game, first, digest)
    _ = _export(game, second, digest)
    _ = _export(game, third, digest, seed=4)
    for relative in ("in_game/map_data/locations.png", "in_game/map_data/rivers.png"):
        assert _digest(first / "rnw_exp_a" / relative) == _digest(second / "rnw_exp_b" / relative)
        assert _digest(first / "rnw_exp_a" / relative) != _digest(third / "rnw_exp_c" / relative)


def test_unknown_build_is_refused_without_explicit_selection(
    install: tuple[Path, World, str], tmp_path: Path
) -> None:
    """A fingerprint that is not the tested 1.4.1 build needs --accept-build."""
    game, _, _ = install
    output = tmp_path / "generated/rnw_exp_refused"
    with pytest.raises(UnsupportedBuildError):
        _ = export_candidate(game, output, seed=1, settings=fixture_settings())
    with pytest.raises(UnsupportedBuildError):
        _ = export_candidate(
            game, output, seed=1, settings=fixture_settings(), accept_build="0" * 64
        )
    assert not output.exists()


def test_cli_refuses_unsafe_outputs(install: tuple[Path, World, str], tmp_path: Path) -> None:
    """Overwrites, non-generated parents, bad names and game-directory outputs fail."""
    game, _, digest = install
    runner = CliRunner()

    def run(output: Path) -> int:
        arguments = ["generate", "--game-dir", str(game), "--seed", "3", "--output", str(output)]
        settings = tmp_path / "fixture-settings.json"
        _ = settings.write_text(json.dumps(fixture_settings().to_json_data()), encoding="utf-8")
        result = runner.invoke(
            app, [*arguments, "--settings", str(settings), "--accept-build", digest]
        )
        return result.exit_code

    assert run(tmp_path / "generated/rnw_exp_cli") == 0
    assert run(tmp_path / "generated/rnw_exp_cli") == 2
    assert run(tmp_path / "elsewhere/rnw_exp_cli") == 2
    assert run(tmp_path / "generated/not_a_mod") == 2
    assert run(game / "generated/rnw_exp_inside") == 2
    assert not (game / "generated").exists()
