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

from rnw import epoch
from rnw.artifacts import write_synthetic_bundle
from rnw.cli import app
from rnw.settings import build_settings, run_spec
from rnw.synth import generate_world, synthetic_base
from rnw.validate import topology_metrics, validate_world

if TYPE_CHECKING:
    from pathlib import Path

ISLAND_PX = 400
# By algorithm epoch (``rnw.epoch``): the bytes of a released epoch never change, and a change of
# the synthetic bundle needs a new epoch and a new entry.
GOLDEN_MANIFESTS = {
    1: {
        "continents": "d015dd203991263dd05b338814277a64d50020f0b5c32b3fe035a312c8ca2c91",
        "archipelago": "37e42f8a44c0ca0c856300c9daffd16152674ba7bf55ed781ada821ebfa02a27",
    },
    2: {
        "continents": "f5357e34eb47ffdd9d8bfa11ef46e69c45ca9f187bfc872948dc809f23104e39",
        "archipelago": "504ad143aa184a3aef7798c9d230d7cde3f57dbfa0d6a36c52d2828771a305b0",
    },
    3: {
        "continents": "6a4e8fbcda026667913cfa03e318a990dd7fdb6c60ae0a64c568a1e7a7357283",
        "archipelago": "c04865e0e3144479fb54a0d3fe5c2eec15755acb8c119608ae0c9bd0b1c34cdf",
    },
    4: {
        "continents": "a0bdd570e3013d0042bc21fbe0be24f08c4a6ebd8fac25bd50ff8f488e7b2410",
        "archipelago": "4ac0ffeb4644378f50c8f2880c43bc4f06387019dfc574e811a4198dc17f00e9",
    },
    5: {
        "continents": "949108bb22e87d278e79716235529ff4392d2bcbb74e7005ef7c53ae16bdee92",
        "archipelago": "8e5ddad11f7e43a6fbf514ca19dcceb6307412d6fee1be56d4df48890c82baf7",
    },
    6: {
        "continents": "8bc06a7bde1ed7889952874c484361f0869746a74659a9c0e2d665256e38c3e8",
        "archipelago": "cd9240618e6cbb378c3434a5b57f44de80ff41388cfc00e41497c247bdfd8983",
    },
    7: {
        "continents": "b0f3b4d2e67fc5c65bf02912ddc155c60eb636e61db96f62bd20f056cd9dc172",
        "archipelago": "4309586b5010a6ed9e6ea803b41b4887302ea5060f50bc14e45325c237c84538",
    },
    8: {
        "continents": "c3f807b86ea93409b933e53d8b5bd9b9a104f7c534df0e467e36b032583e2c0b",
        "archipelago": "a0b4d0a27ba8ab8a85ca3a15759ebf8d074ccb589dee5495ca3b9bc6e9bc190e",
    },
    9: {
        "continents": "34630424f9b536e7facac9194818ac92a49fbb0443f4d25d9f82d169fd8e35b6",
        "archipelago": "fcaee00b81a987b7ce30822146bb986cd285d2dbd97d6c93b4510d7b0e12c4df",
    },
    10: {
        "continents": "08c50d72faea290eb4e031d0376403734ba4daa80febc40f21af47e5f47aea4d",
        "archipelago": "1254f145aee8f8c0806b14866fb24a580a34f0caa883dc4b5cefa5292be87d56",
    },
    11: {
        "continents": "2696fced19b72af91366d7d1fa72b6cadeba7e8a01464aa34e27c13e3a086879",
        "archipelago": "fc934fd49fb8e62ef653003e206b9a886f31bbc1a7841de24f7cfc1b0e9f70ce",
    },
    12: {
        "continents": "bd7c767c23cd2007c1be565bc113e2906a6790590a92056e58df5c8d5c58a8b3",
        "archipelago": "b2d6e33cf771658978257f554f5cc5254c62bd50cb5e00d39d59ed80355a4f7e",
    },
    13: {
        "continents": "128d54e1909507206b0405de29004c73558b0d997aa1f2c0381126805cb3ee1b",
        "archipelago": "277f980584d2d9f45a419f00efa5b96aafdf8e5b5df821012eda7158fa4768ce",
    },
    14: {
        "continents": "a427a86e0c0586382d240ff9bf4cbabed0ff562823bc021fcd753273e62eb5ea",
        "archipelago": "c1eb94be7aeb0d0656c9e55963bea77dba829330b73682b7a5af9d5cc3a69a33",
    },
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
    assert first == GOLDEN_MANIFESTS[epoch.CURRENT][preset]


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
