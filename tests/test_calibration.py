"""Static calibration is content-validated and never loses a world's input provenance."""

from __future__ import annotations

import os
from dataclasses import replace
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw import calibration, inputs
from rnw.landcache import CacheError
from tests.fakes import SIZES

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.eu5_biomes import SizeModel
    from rnw.eu5_map import Eu5Map


def test_calibration_hit_invalidation_and_replayed_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game, cache = tmp_path / "game", tmp_path / "cache"
    game.mkdir()
    dependency = game / "heights"
    _ = dependency.write_text("1")
    inventory = game / "sources"
    inventory.mkdir()
    monkeypatch.setattr(calibration, "code_identity", lambda: "original-code")
    original = cast(
        "Eu5Map", cast("object", SimpleNamespace(inputs=(), labels=np.zeros((2, 3), np.int32)))
    )
    calls: list[int] = []

    def make() -> SizeModel:
        calls.append(1)
        value = int(dependency.read_text()) + len(list(inventory.iterdir()))
        return replace(SIZES, features=SIZES.features + value)

    def read() -> tuple[SizeModel, list[str]]:
        with inputs.recording(game) as recorder:
            model = calibration.get_sizes(cache, game, original, make)
            manifest = recorder.manifest(game, workers=1)
        assert set(manifest.directories) == {"sources"}
        return model, sorted(manifest.files)

    first, files = read()
    second, cached_files = read()
    assert files == cached_files == ["heights"]
    assert len(calls) == 1
    assert first.digest() == second.digest()
    timestamp = dependency.stat().st_mtime_ns
    _ = dependency.write_text("2")
    os.utime(dependency, ns=(timestamp, timestamp))
    changed, _ = read()
    assert len(calls) == 2
    assert first.digest() != changed.digest()
    _ = (inventory / "new_source").write_text("new")
    listed, _ = read()
    assert len(calls) == 3
    assert listed.digest() != changed.digest()
    monkeypatch.setattr(calibration, "code_identity", lambda: "changed-code")
    _ = read()
    assert len(calls) == 4
    assert len(list((cache / "calibration").glob("*.npz"))) == 2


def test_corrupt_calibration_fails_explicitly(tmp_path: Path) -> None:
    original = cast(
        "Eu5Map", cast("object", SimpleNamespace(inputs=(), labels=np.zeros((2, 3), np.int32)))
    )
    _ = calibration.get_sizes(tmp_path, tmp_path, original, lambda: SIZES)
    target = next((tmp_path / "calibration").glob("*.npz"))
    _ = target.write_bytes(b"broken archive")
    with pytest.raises(CacheError, match="Cannot read size calibration"):
        _ = calibration.get_sizes(tmp_path, tmp_path, original, lambda: SIZES)
