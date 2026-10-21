"""Test configuration shared by every test module."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.pictures import TERRA_INCOGNITA
from rnw.png import COLOR_RGB, encode_png

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.app.service import Exporter
    from rnw.progress import Progress

# Qt windows are tested without a display (tests/test_window.py).
_ = os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _png(color: tuple[int, int, int]) -> bytes:
    image = np.zeros((32, 64, 3), dtype=np.uint8)
    image[:] = (25, 45, 90)
    image[:, :20] = color
    return encode_png(image, color_type=COLOR_RGB, compression="zlib")


@pytest.fixture
def fake_export() -> Exporter:
    """An export that writes a tiny world bundle (mod, pictures) and reports one stage."""

    def export(  # noqa: PLR0913 - the export's own signature
        game_dir: Path,
        output: Path,
        *,
        seed: int,
        settings: object,
        accept_build: str | None = None,
        settings_file: str | None = None,
        replace: bool = False,
        check_memory: bool = True,
        progress: Progress | None = None,
        world_code: str | None = None,
    ) -> dict[str, object]:
        del game_dir, settings, accept_build, settings_file, replace, check_memory, world_code
        if progress is not None:
            progress.begin("generate world")
            progress.finish("generate world")
        mod = output / output.name
        (mod / ".metadata").mkdir(parents=True, exist_ok=True)
        _ = (mod / ".metadata/metadata.json").write_text(
            f'{{"name": "Random New World: seed {seed}"}}', encoding="utf-8"
        )
        (mod / "in_game/map_data").mkdir(parents=True, exist_ok=True)
        _ = (output / "preview.png").write_bytes(_png((96, 160, 72)))
        _ = (output / "preview_hidden.png").write_bytes(_png(TERRA_INCOGNITA))
        return {"status": "NOT GAME VALIDATED"}

    return export
