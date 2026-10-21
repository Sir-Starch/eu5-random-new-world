"""The spool keeps finished files on disk and installs them with their manifest records."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.artifacts import OutputPathError, Spool, check_new_output, spool_path
from rnw.eu5_export import MOD_NAME

if TYPE_CHECKING:
    from pathlib import Path


def test_files_are_written_hashed_and_installed(tmp_path: Path) -> None:
    """Bytes and arrays go to disk at once; install moves them and returns sorted records."""
    root = tmp_path / ".spool"
    stage = tmp_path / "stage"
    stage.mkdir()
    with Spool(root) as spool:
        spool["b/two.bin"] = b"two"
        spool["a.txt"] = b"one"
        array = np.arange(6, dtype="<f4").reshape(2, 3)
        spool["c.bin"] = array
        assert len(spool) == 3
        assert sorted(spool) == ["a.txt", "b/two.bin", "c.bin"]
        assert spool["a.txt"] == b"one"
        records = spool.install(stage, "mod")
        assert not spool
        assert (root / "a.txt").exists() is False
    assert [record["path"] for record in records] == ["mod/a.txt", "mod/b/two.bin", "mod/c.bin"]
    assert records[0] == {
        "path": "mod/a.txt",
        "size": 3,
        "sha256": hashlib.sha256(b"one").hexdigest(),
    }
    assert records[2]["size"] == array.nbytes
    assert records[2]["sha256"] == hashlib.sha256(array.tobytes()).hexdigest()
    assert (stage / "mod/c.bin").read_bytes() == array.tobytes()
    assert not root.exists()


def test_leaving_the_spool_removes_what_was_not_installed(tmp_path: Path) -> None:
    """A failed export leaves no spool directory behind, and a leftover one is refused."""
    root = tmp_path / ".spool"

    def fail() -> None:
        with Spool(root) as spool:
            spool["x"] = b"data"
            message = "boom"
            raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="boom"):
        fail()
    assert not root.exists()
    root.mkdir()
    with pytest.raises(OutputPathError, match="leftover spool"), Spool(root):
        pass
    with pytest.raises(KeyError):
        _ = Spool(tmp_path / ".other")["missing"]


def test_a_leftover_spool_blocks_a_new_export_until_it_is_replaced(tmp_path: Path) -> None:
    """The output check refuses to start beside scratch a killed run left behind, and
    ``replace`` clears it."""
    generated = tmp_path / "generated"
    output = generated / "rnw_exp_new_world"
    spool_path(output).mkdir(parents=True)
    _ = (spool_path(output) / "half.bin").write_bytes(b"x")
    with pytest.raises(OutputPathError, match=r"leftover staging.*--replace clears it"):
        check_new_output(output, MOD_NAME)
    check_new_output(output, MOD_NAME, replace=True)
    assert not spool_path(output).exists()
