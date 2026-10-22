from __future__ import annotations

import hashlib
import zipfile
from typing import TYPE_CHECKING

import pytest
import release

from rnw import __version__

if TYPE_CHECKING:
    from pathlib import Path


def test_release_tag_must_match_the_product_version() -> None:
    release.check_tag(f"v{__version__}")
    with pytest.raises(ValueError, match="does not match"):
        release.check_tag("v1.0.0")


def test_release_archives_cannot_carry_derived_game_data(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("source/src/rnw/worldfile.py", "our code")
        handle.writestr("source/local_data/game/main_menu/gfx/FX/copied.fxh", "game data")
    with pytest.raises(ValueError, match="files of the game"):
        release.check_archive(archive)


def test_checksum_file_covers_each_artifact(tmp_path: Path) -> None:
    _ = (tmp_path / "linux.tar.gz").write_bytes(b"linux")
    _ = (tmp_path / "windows.zip").write_bytes(b"windows")
    path = release.checksums(tmp_path)
    expected = hashlib.sha256(b"linux").hexdigest()
    assert f"{expected}  linux.tar.gz" in path.read_text(encoding="ascii")
    assert len(path.read_text(encoding="ascii").splitlines()) == 2
