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
    15: {
        "continents": "fed30cb71160d6a2e080f2d73ec85b73c3f4951b78063bd0d78aa2572062772d",
        "archipelago": "d1ecc970727aa1c6dc6ce621d16e4e2026bc0e4fc1a0c75b14119cc7b2f495e1",
    },
    16: {
        "continents": "dc9945d7ab316d7d5ba13b99e534045049b48ab52daf62763448957c844f7ef3",
        "archipelago": "0a4f19ca0ebd0ec4677b5c35bc984b4dea2618fb1c11536cba7dd3220ed82ca3",
    },
    17: {
        "continents": "d0a6bf8839851fbcbce8a697416829be68135b35f0d9c02d306384f5e2a9bb6a",
        "archipelago": "b03be093110306dcfe07949787cd395dcbbfef14d461748b98d691f53ac0d606",
    },
    18: {
        "continents": "dfbf9607eea9825e952b4f3810d2fb213e53e0dfe14307355e7a197a9f39e965",
        "archipelago": "57a95cb47e3b3eda7d629a50ed788ae491abdb0a777eb9269ab4aff618da2959",
    },
    19: {
        "continents": "20141aa1545daa95ffed44ad9eb9ba37cb483460d816861290440798a2721122",
        "archipelago": "d8ceda319ac4d2a96d4ce2881f1c3d588cd6995af46ff4105b0b6f96f6ae3406",
    },
    20: {
        "continents": "fc82f4b3878862a58eca87095d959495ca47d8fddec2fbdd92c2cd1c884e984d",
        "archipelago": "207062eee5f96d6b5795b94dd6cb554d01706277a0cff7694b45caadae0618bd",
    },
    21: {
        "continents": "42365e53abb06a80e0cc5b26f75e5575c4ee11c8e8f496b9b96a2395ded93fcc",
        "archipelago": "07f4124c815649921a15c96e54d01440b121a9a556edc60697672e93274e50aa",
    },
    22: {
        "continents": "446d0babe8d79945c76ce239ed34296bcff242e9b78d608c58654e120a56bcee",
        "archipelago": "ba31cf3e4f07d9dae00087016c5ee0158e6fcc97770b360964e23112bd46b94e",
    },
    23: {
        "continents": "adcff1088d9de2fce801b3693f7f554758eab5bb634eef583e091d837bd018f2",
        "archipelago": "eb9d45de361de76805cad8697b0bf57804e8b5039f8dd8c1063a73bd0a551ed4",
    },
    24: {
        "continents": "9d9bfcf311f3c473b3833785bb5a99b48f8be6ba3b03d37e6b0d63bb59ae40f7",
        "archipelago": "1df6b59029f83442b10de619415b9fe539b30b5160b124b4d2e173a71b3befdc",
    },
    25: {
        "continents": "c2d22b395ed8c296597e6b928ee646439dad16ab37d30af7418be8130ec78c53",
        "archipelago": "78a3da0f37f414c7563d71382e762aecd5b7723b8c3e7434e8292c4c5f63b11d",
    },
    26: {
        "continents": "5f86d760c2cbac611f078963bcf37be7513722feb1b0356cdd94ce4b9eca5e66",
        "archipelago": "1209bf34bf90a3e2bd84390549ea0025e9ee39c23c0a2a564b2af171cf798496",
    },
    27: {
        "continents": "d150b74c3b852e753f3f8cd7d3507b7cb8b9c5ec3d831052fa12ab2b51f0aafe",
        "archipelago": "78e708ee643ff55e781f1e9c7e3108ef6b3e12b1d4422de0be7bdeceb8445801",
    },
    28: {
        "continents": "182c3a41cacdad746d401db18a3589bc8f8f3c39d74857be846b76522f23a87a",
        "archipelago": "3128d381a806cf0a63bf17d97a87cd3364a47e95d603cf858ceb32f0edc89e57",
    },
    29: {
        "continents": "82fa6f3dbf6b9aa89e7ce6b254438af1f7b728aecb26e8d42fcb27f7389a1e4a",
        "archipelago": "3e32abc9af265f36ea9ed7ceb4e91f64fd458d51b260a5edf00682018252df34",
    },
    30: {
        "continents": "7154b44cdfada5a0ea94f0f6aeb4d2c2e932b2bc6dfdcbf8afbce9228365f410",
        "archipelago": "5f9567f10ba01ca7cd8fc3c56c1ca8b9f2eb6559a6bebc0f4f9dcfb9ffe14cec",
    },
    31: {
        "continents": "9c8d17d84e5b1ea564edb023a5fb30b85a5df6c691e252173a0c7da28bfd3887",
        "archipelago": "5e0dcf56b542586e213114cb45d6a944e99ed9b2e57eeefd8d4638ac5b51d1e6",
    },
    32: {
        "continents": "7a5511ccbb1fdaf0ba0452cb251ae81c403b7418d8b3d7786e5c4ab74e44727b",
        "archipelago": "1921d728b66e70424d44dc774e61708a7bcaf9a79f6232c6fc0ef20b7f6cc011",
    },
    33: {
        "continents": "473d6c593a4470627e4e36738588e65451536fb78604cf7e3ba1fbf8a5230189",
        "archipelago": "759398aaa5e9df6cb4ce2205ba086de2a0e124dfb264334f631aabbd611600bc",
    },
    34: {
        "continents": "f3fe8a6d3cb0db0892588b98ec2924b5e9d11a88bb7edf79e646c98caa98e139",
        "archipelago": "57fa35ca374dbd648bed28821ba7f873da3269bb637376bd4a94d0a970d29d4c",
    },
    35: {
        "continents": "dae5cd2efd23a64e4c39f1730bbacfa61e6b095859ce1dbba9b0ab317e54ef18",
        "archipelago": "a0acb6a042bc7f8bfe9fc90151288ced9022f944b0b5ef43d7539b545cb76c3c",
    },
    36: {
        "continents": "d3e537c4e39ec82bcd1e950835218b48fedfa8593c66964be508ecc509ef26f5",
        "archipelago": "87ce847fea5150e19d2b3bbb3b1ee1f47a4d30a1f78fc27e7c46d5524df5c362",
    },
    37: {
        "continents": "02105da224e39870ff73b42676ab4512e6490c91d1be400e5a30e6babb0e06c3",
        "archipelago": "48d2e14db3446f54d46ad21d0239d9dcc28e94dd6e6e146849d07615e14af365",
    },
    38: {
        "continents": "c04cad8a136566285b2bdb1c81ea600f83b7fdd2f58c8ae2992b1a633d01423c",
        "archipelago": "a7304cb062c03c014fb4115e4df226d936cc0ec8f61f988f6b114130019c5b5d",
    },
    39: {
        "continents": "e0a7439c658f386869deefc777a84da2cf8002b36ce50eb17d611582cad69c0f",
        "archipelago": "20db7031796ffff191a1b8083194696d8ff353fce8ef3f2a708b0c0f79a4a13b",
    },
    40: {
        "continents": "f07897ef0eec174ca2e01d31e41abb7e0e7f0053460275a2bda12d42790d6c31",
        "archipelago": "ddab74d9a7132dab9a7b1fc39860514d0e2a497d2243ef4e28be1365e9cbe5d5",
    },
    41: {
        "continents": "414a8e40d9c1561ce2d995a838a575b9f8abff75076d06dcc2dc856de2948e63",
        "archipelago": "5a2a7874ab015cd705de5b58ada4ab69114b7715071b3950533b1c0102f94f64",
    },
    42: {
        "continents": "676b8ec51c43041f2a3a97b5f1eda7ee15b50e2e9b0057ca8de4b22ab5904758",
        "archipelago": "b5488938b6b5ac786d9ad7c9d9f48c553bff9db703a0df47bfa76980a4adc0ec",
    },
    43: {
        "continents": "af6fb40ecc6ca05d0dccb3bbbb3d42ea21cd20a45b14298ff0e76edf539b6b70",
        "archipelago": "2e1ca4b869fec2fb78db620f8fb2f97b6dcdd815e86d11bb0fa0b17fae20f6d4",
    },
    44: {
        "continents": "26935f0de512e3863121675286a8835ce8a365644204f13af9782a6c009837bd",
        "archipelago": "b030158b8ced4733ed87ac4e723617b50b98f3280cae9e117855d3e5176547d8",
    },
    45: {
        "continents": "55a2801f09a04848b0469b46e75529a3c5825398e436f33fdce0d111463f0137",
        "archipelago": "5f189e0851a54ac50474239aa5becf7a27095a89f548c1d8a421425a14fad4a6",
    },
    46: {
        "continents": "cd96e5baf9376be37d8c15b32e3c56b32946e2b7cb1e1d4e72f638492f067ffd",
        "archipelago": "03db7442d4694a5648b05f16db3c0e648fa92b69791451c5082b766b0b93bf21",
    },
    47: {
        "continents": "d81e5d173b8b11a5bf4b744df07a4f9661ce614f80a54f4095249b1a1c6595f2",
        "archipelago": "03fc3e9ab4cb8b2261efc25609fd1ba98befbd75d8b4e85c60b6b393b44edb04",
    },
    48: {
        "continents": "3472cf78d39de8c54df75c616d4ea50594b2d211167693d9881090c1c5e11d67",
        "archipelago": "ffb0286e78cd6b71f87a7c97b797479cf3c02915200bcee5ff1f0009caa176f0",
    },
    49: {
        "continents": "9fc0fc76c4b23cd3c2b03dcf4b8a88a6e0e05f3312b088d5a353519c93ad0f62",
        "archipelago": "1e1d98d2c15dfe3574003917ec50642d766d2938f360948b042d82105455c236",
    },
    50: {
        "continents": "8bef410e5f6decd3aebc3681dde7d829f7146dfb71616b763afb04ef0adefa4a",
        "archipelago": "243e71057203fd29ba478f097a7dba15e619e25f83436fa37a5df46844a27cb7",
    },
    51: {
        "continents": "3c4d86632e7f23c579befd8736d7ce7ad154960b714de10468bf3a0247185f38",
        "archipelago": "b1e5991748c545114154ed65b8a84a5eb4718d2a55a699a81d173e3b613986c5",
    },
    52: {
        "continents": "4d9cffdfba94f1c79ed6290354a9997b5a9394df251d6459410c2fed6ef653d9",
        "archipelago": "d4fdf4f7864d95be543b5f95c79f11bb151395a96394c12995980226b523b03d",
    },
    53: {
        "continents": "a9804ad66d56aaeb8a4df00e4cee6fb8134c07bace733bc345e112ddce3d50b6",
        "archipelago": "51dbc2a74764038bb01af3145ffa2590d380f28ed45fea5dce340c5893006343",
    },
    54: {
        "continents": "2356245e2e5f688f98a4cee5464b2ce3b15abdf9709d7fe8aa302de500c6202b",
        "archipelago": "ce8babf55765a85429bb3f321b53cffc87a1d88367b23b1f876235ecb40f4b68",
    },
    55: {
        "continents": "fa90b22fbebb1a5d3bf7b141955b6399e2f6dccf2c3ecedade11c9125e515a10",
        "archipelago": "f14e67cb0d2f14c67b7c96ccf8da6a5df1c0fc013d5626c3cafffe0b81c1a946",
    },
    56: {
        "continents": "3dc8ff499ef1b3a850cda235d349e10888d3bebfbf90e721d3fb15a74e43d6c3",
        "archipelago": "e5463e6997d7e7c462461d0d6ada06558e0fb2658553179f294663bb31251b39",
    },
    57: {
        "continents": "06963f8f8194db314b052f05d2afb02224e1ce720e284c9214f431d512b22aeb",
        "archipelago": "566678eee355622c5a5ce3819807acbd23516b9fe451bbaa291d20a43d641a79",
    },
    58: {
        "continents": "3823ddf4455d4367fa1afbe4df103c32dcdc6461ad1b921f10599ca0277cab70",
        "archipelago": "d6bbfc6c36847c8cbec36756e211aa868d2dd0fff4298f0afc46829cb8498c93",
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
