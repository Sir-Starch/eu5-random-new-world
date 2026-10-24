"""Synthetic localization files: replace names without redefining keys or touching other text."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.eu5_localization import LocalizationError, map_name_files

if TYPE_CHECKING:
    from pathlib import Path


def _source(root: Path, stem: str, data: bytes, language: str = "english") -> str:
    relative = f"main_menu/localization/{language}/{stem}_l_{language}.yml"
    path = root / "game" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(data)
    return relative


@pytest.mark.parametrize("language", ["english", "turkish"])
@pytest.mark.parametrize("bom", [b"", b"\xef\xbb\xbf"])
def test_map_names_replace_only_requested_values_and_preserve_installed_bytes(
    tmp_path: Path, language: str, bom: bytes
) -> None:
    area = (
        f'l_{language}:\r\n old_world:0 "Unchanged" # keep\r\n new_world:1 "Before" # also keep\r\n'
    ).encode()
    region = (f'l_{language}:\n north: "Before north"\n south: "Before south"\n').encode()
    a = _source(tmp_path, "area", bom + area, language)
    r = _source(tmp_path, "region_names", bom + region, language)
    _ = _source(
        tmp_path,
        "location_names/location_names",
        f'l_{language}:\n sea: "Sea"\n'.encode(),
        language,
    )
    files = map_name_files(tmp_path, language, {"new_world": 'A "Bay"', "south": "New south"})
    assert files == {
        a: bom + area.replace(b'"Before"', b'"A \\"Bay\\""'),
        r: bom + region.replace(b'"Before south"', b'"New south"'),
    }
    assert (tmp_path / "game" / a).read_bytes() == bom + area
    assert (tmp_path / "game" / r).read_bytes() == bom + region


def test_absent_or_duplicate_names_stop_generation(tmp_path: Path) -> None:
    _ = _source(tmp_path, "area", b'l_english:\n a: "A"\n')
    _ = _source(tmp_path, "region_names", b'l_english:\n r: "R"\n')
    _ = _source(tmp_path, "location_names/location_names", b'l_english:\n sea: "Sea"\n')
    with pytest.raises(LocalizationError, match="Missing map-name keys in english: lost"):
        _ = map_name_files(tmp_path, "english", {"lost": "New"})
    _ = _source(tmp_path, "region_names", b'l_english:\n a: "Duplicate"\n')
    with pytest.raises(LocalizationError, match="Duplicate map-name key a in english"):
        _ = map_name_files(tmp_path, "english", {"a": "New"})


def test_no_name_changes_need_no_localization_files(tmp_path: Path) -> None:
    assert map_name_files(tmp_path, "english", {}) == {}
