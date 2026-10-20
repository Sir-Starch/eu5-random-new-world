"""Seeded synthetic geography: valid, repeatable and seed/preset sensitive."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest
from typer.testing import CliRunner

from rnw.artifacts import write_synthetic_bundle
from rnw.cli import app
from rnw.settings import build_settings, run_spec
from rnw.synth import generate_world, synthetic_base
from rnw.validate import topology_metrics, validate_world

if TYPE_CHECKING:
    from pathlib import Path

ISLAND_PX = 400
GOLDEN_MANIFESTS = {
    "continents": "b120547c923544fc0a665722999f6ae318ff4dfb4630a8e765446b3816906efa",
    "archipelago": "8a5a99f247287d28e6bd1d683adb87659a859beacb8050640afa64827d8d1a81",
}


@pytest.mark.parametrize("preset", ["continents", "archipelago"])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_generated_worlds_pass_every_invariant(preset: str, seed: int) -> None:
    """Every generated world keeps the protected base and is fully valid."""
    settings = build_settings(preset)
    world = generate_world(seed, settings)
    validate_world(world, base=synthetic_base(settings.synthetic))


def test_same_seed_is_identical_and_other_seed_differs() -> None:
    """Geometry is a pure function of seed and settings."""
    settings = build_settings("continents")
    first = generate_world(4, settings)
    assert np.array_equal(first.labels, generate_world(4, settings).labels)
    assert first.cells == generate_world(4, settings).cells
    other = generate_world(5, settings)
    assert not np.array_equal(first.labels, other.labels)
    assert topology_metrics(first, ISLAND_PX) != topology_metrics(other, ISLAND_PX)


def test_presets_yield_measurably_different_coasts() -> None:
    """Archipelagos have more landmasses and a longer coast per land pixel."""
    for seed in range(1, 5):
        continents = topology_metrics(generate_world(seed, build_settings("continents")), ISLAND_PX)
        islands = topology_metrics(generate_world(seed, build_settings("archipelago")), ISLAND_PX)
        assert islands["landmasses"] >= 3 * continents["landmasses"]
        assert (
            islands["coast_edges"] * continents["land_px"]
            > 2 * continents["coast_edges"] * islands["land_px"]
        )


def _bundle_digest(output: Path, preset: str) -> str:
    settings = build_settings(preset)
    world = generate_world(1, settings)
    manifest = write_synthetic_bundle(
        world, run_spec(1, settings), topology_metrics(world, ISLAND_PX), output
    )
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


@pytest.mark.parametrize("preset", ["continents", "archipelago"])
def test_bundle_bytes_match_cross_platform_golden(tmp_path: Path, preset: str) -> None:
    """All bundle files are byte-identical across runs and match the committed golden.

    CI runs this on Linux and Windows; a mismatch means output changed and needs a new
    generator version, or the platform produced different bytes.
    """
    first = _bundle_digest(tmp_path / "generated/rnw_synth_a", preset)
    assert first == _bundle_digest(tmp_path / "generated/rnw_synth_b", preset)
    assert first == GOLDEN_MANIFESTS[preset]


def test_cli_synth_writes_bundle_and_refuses_overwrite(tmp_path: Path) -> None:
    """The synth command writes a new generated/rnw_synth_* folder exactly once."""
    output = tmp_path / "generated/rnw_synth_cli"
    arguments = ["synth", "--seed", "3", "--preset", "archipelago", "--output", str(output)]
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == 0, result.output
    manifest = cast("dict[str, object]", json.loads((output / "manifest.json").read_text()))
    assert manifest["kind"] == "synthetic-world"
    assert (output / "locations.png").is_file()
    again = CliRunner().invoke(app, arguments)
    assert again.exit_code == 2
    assert "Refusing to overwrite" in again.output


def test_cli_synth_requires_generated_parent(tmp_path: Path) -> None:
    """Outputs outside a generated/ directory are refused."""
    output = tmp_path / "rnw_synth_elsewhere"
    result = CliRunner().invoke(app, ["synth", "--seed", "1", "--output", str(output)])
    assert result.exit_code == 2
    assert not output.exists()
