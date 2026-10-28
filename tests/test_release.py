from __future__ import annotations

import hashlib
import subprocess
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
        release.check_tag("v0.0.0")


@pytest.mark.parametrize("tag", ["v01.0.0", "v1.0.0-rc.1", "v1.0.0+sha", "main", "1.0.0"])
def test_release_tags_are_canonical_numeric_versions(tag: str) -> None:
    with pytest.raises(ValueError, match=r"must be vMAJOR\.MINOR\.PATCH"):
        release.check_tag(tag)


def test_source_gate_rejects_wrong_commit_and_dirty_candidates(tmp_path: Path) -> None:
    def git(*args: str) -> str:
        result = subprocess.run(  # noqa: S603 - synthetic local repository, fixed arguments
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],  # noqa: S607 - test environment provides git
            cwd=tmp_path,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    _ = git("init")
    source = tmp_path / "source.txt"
    _ = source.write_text("candidate", encoding="utf-8")
    _ = git("add", "source.txt")
    _ = git("-c", "commit.gpgsign=false", "commit", "-m", "Candidate")
    tag = f"v{__version__}"
    commit = git("rev-parse", "HEAD")
    release.check_source_ref(tag, tmp_path, candidate_commit=commit)
    with pytest.raises(ValueError, match="full lowercase Git SHA"):
        release.check_source_ref(tag, tmp_path, candidate_commit="main")
    with pytest.raises(ValueError, match="HEAD is not"):
        release.check_source_ref(tag, tmp_path, candidate_commit="0" * 40)
    _ = git("-c", "tag.gpgsign=false", "tag", tag)
    release.check_source_ref(tag, tmp_path)
    extra = tmp_path / "extra.txt"
    _ = extra.write_text("untracked", encoding="utf-8")
    with pytest.raises(ValueError, match="clean checkout"):
        release.check_source_ref(tag, tmp_path)
    extra.unlink()
    _ = source.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="clean checkout"):
        release.check_source_ref(tag, tmp_path)
    _ = git("add", "source.txt")
    with pytest.raises(ValueError, match="clean checkout"):
        release.check_source_ref(tag, tmp_path)
    _ = git("-c", "commit.gpgsign=false", "commit", "-m", "Another commit")
    with pytest.raises(ValueError, match="HEAD is not"):
        release.check_source_ref(tag, tmp_path)


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
