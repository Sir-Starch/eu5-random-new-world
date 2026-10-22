"""What the real export leaves beside a world, for tests that stand in for the export."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from rnw import epoch
from rnw.app import library
from rnw.app.discovery import GameInstall
from rnw.app.worldcode import encode, new_code
from rnw.atlas import JSON_FILE, LABELS_FILE
from rnw.atlas import to_files as atlas_files
from rnw.eu5_atlas import build_atlas
from rnw.eu5_biomes import CellBiomes
from rnw.eu5_natives import Country, NativeWorld
from rnw.eu5_newworld import Plan, PlannedCell
from rnw.inputs import hash_files
from rnw.model import CellClass
from rnw.newworld import NewWorld
from rnw.record import FORMAT, GameRecord, Record, manifest_digest, output_entries
from rnw.settings import build_settings

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.atlas import Atlas


def write_bundle_record(
    output: Path, game_dir: Path, *, seed: int, preset: str, code: str | None
) -> dict[str, object]:
    """Write ``manifest.json`` and ``inputs.json`` for the mod already in ``output`` and return
    what the export's report carries: its ``record`` and its ``files``.

    The files of the mod are hashed from disk; the inputs are the files under the game folder.
    """
    mod = output / output.name
    files = [
        {
            "path": f"{output.name}/{path.relative_to(mod).as_posix()}",
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(item for item in mod.rglob("*") if item.is_file())
    ]
    names = (
        sorted(
            path.relative_to(game_dir).as_posix() for path in game_dir.rglob("*") if path.is_file()
        )
        if game_dir.is_dir()
        else []
    )
    manifest = hash_files(game_dir, names, workers=1)
    entries = output_entries(files, output.name)
    record = Record(
        format=FORMAT,
        algorithm=epoch.CURRENT,
        release="0.0.0",
        code=code,
        preset=preset,
        seed=seed,
        settings=build_settings(preset).to_json_data(),
        game=GameRecord("EU5 test", "f" * 64, "1.4.*", manifest.digest, len(manifest.files)),
        output_sha256=manifest_digest(entries),
        output_count=len(entries),
    )
    document, labels = atlas_files(synthetic_atlas())
    _ = (output / JSON_FILE).write_bytes(document)
    _ = (output / LABELS_FILE).write_bytes(labels)
    _ = (output / "manifest.json").write_text(json.dumps({"files": files}), encoding="utf-8")
    _ = (output / "inputs.json").write_text(json.dumps(manifest.to_json()), encoding="utf-8")
    return {"record": record.to_json(), "files": files}


CLASSES = (
    CellClass.SEA,
    CellClass.LAND,
    CellClass.LAND,
    CellClass.WASTELAND,
    CellClass.LAKE,
    CellClass.SEA,
)


def _pop(culture: str, religion: str, size: str = "1.000") -> list[str]:
    head = "\tdefine_pop = {\ttype = peasants\t"
    return [f"{head}size = {size}\tculture = {culture}\treligion = {religion} }}"]


def synthetic_world() -> tuple[NewWorld, Plan, CellBiomes, NativeWorld, np.ndarray]:
    """Six cells in vertical stripes of a 24 x 72 crop; the far sea has no land near it."""
    labels = np.zeros((24, 72), dtype=np.int32)
    for cell in range(6):
        labels[:, cell * 12 : (cell + 1) * 12] = cell
    mask = np.ones((24, 72), dtype=bool)
    mask[:, 70:] = False
    world = NewWorld(
        labels=labels,
        classes=CLASSES,
        elevation=np.zeros((24, 72), dtype=np.int32),
        pixels=np.full(6, 288, dtype=np.int64),
        centroids=np.zeros((6, 2), dtype=np.int64),
        interior=np.zeros((6, 2), dtype=np.int64),
        mean_elevation=np.zeros(6, dtype=np.int64),
        spread=np.zeros(6, dtype=np.int64),
        edges=(),
    )
    cells = [
        PlannedCell(
            f"rnw_loc_{i}", f"Cell {i}", i, kind, f"p{i}", f"area{i}", "region", "sub", "con"
        )
        for i, kind in enumerate(CLASSES)
    ]
    plan = Plan(cells=cells)
    biomes = CellBiomes(
        climate=("", "tropical", "arctic", "", "", ""),
        vegetation=("", "jungle", "grasslands", "", "", ""),
        topography=("", "mountains", "flatland", "", "", ""),
        raw_material=("", "goods_gold", "maize", "", "", ""),
    )
    countries = (
        Country(
            tag="AAA",
            name="Aland",
            kind="state",
            members=("rnw_loc_1",),
            capital="rnw_loc_1",
            culture="a_culture",
            religion="a_faith",
            include="x",
            areas=(),
            color=(200, 30, 30),
            color2=(0, 0, 0),
        ),
    )
    natives = NativeWorld(
        pops={"rnw_loc_1": _pop("a_culture", "a_faith"), "rnw_loc_2": _pop("b_culture", "b_faith")},
        countries=countries,
        ranks={"rnw_loc_1": ("city", "")},
        markets=(),
        holy_sites={},
        names={"rnw_loc_1": "Alandia", "area1": "Great Area"},
        vassals=(),
        complexity={"rnw_loc_1": 900, "rnw_loc_2": 100},
        population={"rnw_loc_1": 5000, "rnw_loc_2": 700},
        stats={},
    )
    return world, plan, biomes, natives, mask


def synthetic_atlas(step: int = 1, margin: int = 10) -> Atlas:
    world, plan, biomes, natives, mask = synthetic_world()
    return build_atlas(
        world=world, plan=plan, biomes=biomes, natives=natives, mask=mask, step=step, margin=margin
    )


def build_game(root: Path) -> GameInstall:
    for relative in ("game/a.txt", "game/b.txt"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text(relative, encoding="utf-8")
    return GameInstall(root, None, "26043558")


def build_world(data: Path, game: GameInstall, *, name: str = "") -> library.World:
    """A world made the way the export leaves it: a kept mod, its bundle, record and atlas."""
    code = encode(new_code("continents", 5))
    identity = library.world_id(code, "26043558")
    world = library.World(
        id=identity,
        code=code,
        preset="continents",
        seed=5,
        generator="0.9.22",
        game_build="26043558",
        created=100,
        seconds=90.0,
        name=name,
    )
    folder = library.folder(data, world)
    mod = folder / world.folder
    for relative, content in (
        (".metadata/metadata.json", '{"name": "RNW: x"}'),
        ("in_game/map_data/x.txt", "x"),
    ):
        target = mod / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text(content, encoding="utf-8")
    report = write_bundle_record(folder, game.directory, seed=5, preset="continents", code=code)
    document, labels = atlas_files(synthetic_atlas())
    _ = (folder / JSON_FILE).write_bytes(document)
    _ = (folder / LABELS_FILE).write_bytes(labels)
    made = replace(world, record=Record.from_json(report["record"]))
    library.save(data, made)
    return made
