"""The vegetation of a canvas is the same for any strip height."""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import eu5_objects
from rnw.eu5_objects import MAP_OBJECTS, PixelClasses, canvas_pixels, object_outputs
from rnw.fields import upsample

if TYPE_CHECKING:
    from collections.abc import Buffer, Callable
    from pathlib import Path

ROWS, COLUMNS = 90, 70


def _classes(seed: int) -> tuple[PixelClasses, np.ndarray]:
    generator = np.random.default_rng(seed)
    shape = (ROWS, COLUMNS)
    labels = (
        upsample(generator.integers(0, 6, (ROWS // 15 + 2, COLUMNS // 15 + 2)), 15, shape) % 6
    ).astype(np.int32)
    materials = generator.integers(0, 20, (ROWS * 2, COLUMNS * 2), dtype=np.uint8)
    canvas = np.zeros(shape, dtype=bool)
    canvas[10:70, 8:52] = True
    classes = PixelClasses(
        labels=labels,
        materials=materials,
        label_class=np.array([0, 1, 2, 0, 1, -1], dtype=np.int64),
        label_coarse=np.array([0, 0, 1, 0, 0, 1], dtype=np.int64),
        calibrate=np.array([True, True, True, False, False, False]),
    )
    return classes, canvas


def _fixed(value: int) -> Callable[..., int]:
    """A stand-in for ``band_rows`` that always answers ``value``."""

    def answer(*_arguments: object, **_options: object) -> int:
        return value

    return answer


def _instances(root: Path, seed: int) -> None:
    folder = root / MAP_OBJECTS
    folder.mkdir(parents=True)
    generator = np.random.default_rng(seed)
    for name in ("trees_generator_a.bin", "grass_generator_b.bin"):
        records = np.zeros((4000, 10), dtype=np.float32)
        records[:, 0] = generator.random(4000) * COLUMNS
        records[:, 2] = generator.random(4000) * ROWS
        records[:, 3:7] = generator.random((4000, 4))
        records[:, 7:] = 1
        _ = (folder / name).write_bytes(records.astype("<f4").tobytes())
    references = "".join(
        f'{label}={{ transform_bin_file="gfx/map/map_objects/{name}" }}\n'
        for label, name in (("a", "trees_generator_a.bin"), ("b", "grass_generator_b.bin"))
    )
    _ = (folder / "objects.txt").write_text(references, encoding="utf-8")


@pytest.mark.parametrize("seed", [1, 3])
def test_strips_of_any_height_give_the_same_instance_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, seed: int
) -> None:
    """Pixels, counts and sampled records do not depend on where the strips are cut."""
    classes, canvas = _classes(seed)
    _instances(tmp_path / "game", seed)
    results: list[tuple[dict[str, bytes], dict[str, object]]] = []
    for height in (1, 7, 33, 10_000):
        monkeypatch.setattr(eu5_objects, "band_rows", _fixed(min(height, ROWS)))
        sink: dict[str, Buffer] = {}
        stats = object_outputs(
            tmp_path / "game",
            classes=classes,
            canvas=canvas,
            class_count=3,
            coarse_count=2,
            seed=seed,
            sink=sink,
        )
        results.append(({path: bytes(memoryview(data)) for path, data in sink.items()}, stats))
    files, stats = results[0]
    assert len(files) == 2
    assert int(str(stats["instances_added"])) > 0
    assert all(result == results[0] for result in results)


def test_canvas_pixels_of_strips_join_into_those_of_the_canvas() -> None:
    """Rows keep their place in the whole raster, so strips concatenate to the whole."""
    classes, canvas = _classes(3)
    whole = canvas_pixels(classes, canvas)
    parts = [
        canvas_pixels(classes, canvas, first, last)
        for first, last in ((0, 25), (25, 26), (26, ROWS))
    ]
    for kind in range(4):
        assert np.array_equal(np.concatenate([part[kind] for part in parts]), whole[kind])
    assert whole[0].size > 1000
