"""Localization key hashes, the key space, and the tag and localization export checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.eu5_nw_export import (
    NewWorldExportError,
    country_definition_outputs,
    vanilla_localization_keys,
    verify_country_tags,
    verify_localization,
)
from rnw.loc_keys import KeySpace, key_hash, key_hashes, murmur3_32

if TYPE_CHECKING:
    from pathlib import Path

# Published MurmurHash3 x86_32 test vectors.
VECTORS = (
    (b"", 0, 0),
    (b"", 1, 0x514E28B7),
    (b"", 0xFFFFFFFF, 0x81F16F39),
    (b"\xff\xff\xff\xff", 0, 0x76293B50),
    (b"!Ce\x87", 0, 0xF55B516B),
    (b"abc", 0, 0xB3DD93FA),
    (b"aaaa", 0x9747B28C, 0x5A97808A),
    (b"Hello, world!", 0x9747B28C, 0x24884CBA),
    (b"The quick brown fox jumps over the lazy dog", 0x9747B28C, 0x2FA826CD),
)


@pytest.mark.parametrize(("data", "seed", "expected"), VECTORS)
def test_murmur3_matches_reference_vectors(data: bytes, seed: int, expected: int) -> None:
    """The hash is MurmurHash3 x86_32."""
    assert murmur3_32(data, seed) == expected


def test_key_hash_reproduces_the_logged_collision() -> None:
    """The two keys the engine logged as a collision share this hash (C89)."""
    assert key_hash("flavor_brapru.1301.entry") == key_hash("rnw_loc_05454") == 1813186726


def test_key_space_skips_taken_serials() -> None:
    """A serial whose hash is taken is skipped; later serials continue from it."""
    keys = KeySpace(key_hashes(["flavor_brapru.1301.entry"]))
    assert keys.next("rnw_loc_", 5) == "rnw_loc_00001"
    for _ in range(5452):
        _ = keys.next("rnw_loc_", 5)
    assert keys.next("rnw_loc_", 5) == "rnw_loc_05455"
    assert keys.next("rnw_prov_", 5) == "rnw_prov_00001"


def test_key_space_claims_all_or_nothing() -> None:
    """A group is refused if one key is taken or two of its keys share a hash."""
    keys = KeySpace(key_hashes(["TAKEN"]))
    assert not keys.claim(("FREE", "TAKEN"))
    assert keys.claim(("FREE", "FREE_ADJ"))
    assert not keys.claim(("FREE",))
    assert not keys.claim(("flavor_brapru.1301.entry", "rnw_loc_05454"))


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


SETUP = "game/main_menu/setup/1337/10_countries.txt"
VANILLA_SETUP = """countries = {
	countries = {
		ZNI = { capital = halona }
		TEY = { capital = teypana }
		FRA = { capital = paris }
	}
}
"""
GENERATED_SETUP = """countries = {
	countries = {
		TEY = { capital = teypana }
		FRA = { capital = paris }
		RNA = { capital = rnw_loc_00001 }
	}
}
"""


def _install(root: Path) -> None:
    _write(root, "game/in_game/setup/countries/_default.txt", "DUMMY = { color = red }\n")
    _write(
        root,
        "game/in_game/setup/countries/america.txt",
        "# Zuni\nZNI = {\n\tcolor = map_zuni\n}\n\nTEY = { color = map_teypana }\n",
    )
    _write(root, "game/in_game/setup/countries/europe.txt", "FRA = { color = blue }\n")
    _write(root, SETUP, VANILLA_SETUP)


def test_definitions_of_removed_tags_go_with_their_setup(tmp_path: Path) -> None:
    """Removed tags leave their definition file; the rest of the file stays byte for byte."""
    _install(tmp_path)
    outputs = country_definition_outputs(tmp_path, {"ZNI", "halona", "FRA_missing"})
    assert list(outputs) == ["in_game/setup/countries/america.txt"]
    assert outputs["in_game/setup/countries/america.txt"].decode() == (
        "# Zuni\n\nTEY = { color = map_teypana }\n"
    )


def test_country_tags_must_agree_with_setup_as_in_vanilla(tmp_path: Path) -> None:
    """A definition left without its setup entry, or a setup entry without one, fails."""
    _install(tmp_path)
    natives = "in_game/setup/countries/rnw_natives.txt"
    outputs = {
        "main_menu/setup/1337/10_countries.txt": GENERATED_SETUP.encode(),
        natives: b"RNA = { }\n",
    }
    with pytest.raises(NewWorldExportError, match="2 defined without a setup entry"):
        _ = verify_country_tags(tmp_path, outputs)
    outputs.update(country_definition_outputs(tmp_path, {"ZNI"}))
    checks = verify_country_tags(tmp_path, outputs)
    assert checks == {"country_tags_defined": 4, "country_tags_without_setup": ["DUMMY"]}
    del outputs[natives]
    with pytest.raises(NewWorldExportError, match="1 set up without a definition"):
        _ = verify_country_tags(tmp_path, outputs)


def test_vanilla_localization_keys_cover_every_language_root(tmp_path: Path) -> None:
    """Keys come from every localization folder of the installation, with or without versions."""
    _write(
        tmp_path, "game/main_menu/localization/english/a_l_english.yml", 'l_english:\n a:0 "A"\n'
    )
    _write(tmp_path, "game/dlc/d1/main_menu/localization/german/b.yml", 'l_german:\n b: "B"\n')
    _write(tmp_path, "jomini/localization/c.yml", 'l_english:\n # note\n c.d:1 "C"\n')
    _write(tmp_path, "game/in_game/common/not_localization.yml", 'x:\n e: "E"\n')
    assert vanilla_localization_keys(tmp_path) == {"a", "b", "c.d"}


def test_generated_localization_must_not_collide() -> None:
    """A generated key sharing a hash with vanilla or with another generated key fails."""
    vanilla = key_hashes(["flavor_brapru.1301.entry"])
    names = "main_menu/localization/english/rnw_new_world_l_english.yml"
    replace = "main_menu/localization/english/replace/rnw_new_world_replace_l_english.yml"
    clean = {names: b'l_english:\n rnw_loc_00001: "A"\n', replace: b'l_english:\n TAKEN: "B"\n'}
    assert verify_localization(clean, vanilla) == {"localization_keys": 1}
    clashing = {names: b'l_english:\n rnw_loc_05454: "A"\n'}
    with pytest.raises(NewWorldExportError, match="1 generated localization keys collide"):
        _ = verify_localization(clashing, vanilla)
