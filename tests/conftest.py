"""Test configuration shared by every test module."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.bundle import COVER_COPY
from rnw.eu5_lobby import SCRIPTED_GUI_FILE
from rnw.pictures import TERRA_INCOGNITA
from rnw.png import COLOR_RGB, encode_png
from tests.fakes import write_bundle_record

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.app.service import Exporter
    from rnw.landmask import LandMask
    from rnw.progress import Progress
    from rnw.worldname import Label

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
        world_label: Label | None = None,
        land_mask: LandMask | None = None,
        cache_dir: Path | None = None,
    ) -> dict[str, object]:
        del settings, accept_build, settings_file, replace, check_memory, land_mask, cache_dir
        title = world_label.title if world_label is not None else f"seed {seed}"
        if progress is not None:
            progress.begin("generate world")
            progress.finish("generate world")
        mod = output / output.name
        (mod / ".metadata").mkdir(parents=True, exist_ok=True)
        _ = (mod / ".metadata/metadata.json").write_text(f'{{"name": "{title}"}}', encoding="utf-8")
        (mod / "in_game/map_data").mkdir(parents=True, exist_ok=True)
        for root in (mod, output / COVER_COPY):
            (root / SCRIPTED_GUI_FILE).parent.mkdir(parents=True, exist_ok=True)
            _ = (root / SCRIPTED_GUI_FILE).write_text("cover", encoding="utf-8")
        _ = (output / "preview.png").write_bytes(_png((96, 160, 72)))
        _ = (output / "preview_hidden.png").write_bytes(_png(TERRA_INCOGNITA))
        record = write_bundle_record(
            output, game_dir, seed=seed, preset="continents", code=world_code
        )
        return {"status": "NOT GAME VALIDATED", **record}

    return export
