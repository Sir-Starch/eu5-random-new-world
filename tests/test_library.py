"""The library of worlds: records, placements, strays, names, pictures and the cover."""

# NumPy stubs type array indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import json
from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np

from rnw import worldname
from rnw.app import library
from rnw.app.library import Placement, World
from rnw.app.worldcode import encode, new_code
from rnw.atlas import JSON_FILE as ATLAS_JSON
from rnw.atlas import LABELS_FILE as ATLAS_LABELS
from rnw.atlas import to_files as atlas_files
from rnw.bundle import COVER_COPY
from rnw.pictures import SIZE, TAG_COLOR, TERRA_INCOGNITA
from rnw.png import COLOR_RGB, encode_png
from rnw.pngread import read_rgb
from rnw.record import FORMAT, GameRecord, Manifest, Record
from rnw.settings import build_settings
from tests.fakes import synthetic_atlas

if TYPE_CHECKING:
    from pathlib import Path


def _world(seed: int, created: int = 100) -> World:
    code = f"RNW1-TEST-{seed}"
    return World(
        id=library.world_id(code, "26043558"),
        code=code,
        preset="continents",
        seed=seed,
        generator="0.9.14",
        game_build="26043558",
        created=created,
        seconds=90.0,
    )


def _coded(
    seed: int,
    *,
    created: int,
    rolls: dict[str, int] | None = None,
    parent: str = "",
    part: str = "",
) -> World:
    """A world whose code is a real one, so that its land can be read."""
    code = encode(new_code("continents", seed, {"rolls": rolls} if rolls else None))
    return World(
        id=library.world_id(code, "26043558"),
        code=code,
        preset="continents",
        seed=seed,
        generator="0.9.22",
        game_build="26043558",
        created=created,
        seconds=90.0,
        parent=parent,
        part=part,
    )


def _bundle(data: Path, world: World, *, kept: bool = True) -> Path:
    folder = library.folder(data, world)
    if kept:
        (folder / world.folder / ".metadata").mkdir(parents=True)
        _ = (folder / world.folder / ".metadata/metadata.json").write_text("{}", encoding="utf-8")
    folder.mkdir(parents=True, exist_ok=True)
    image = np.zeros((32, 64, 3), dtype=np.uint8)
    image[:, :20] = TERRA_INCOGNITA
    _ = (folder / library.PREVIEW_HIDDEN).write_bytes(
        encode_png(image, color_type=COLOR_RGB, compression="zlib")
    )
    image[:, :20] = (96, 160, 72)
    _ = (folder / library.PREVIEW).write_bytes(
        encode_png(image, color_type=COLOR_RGB, compression="zlib")
    )
    library.save(data, world)
    return folder


def test_records_load_newest_first_and_a_damaged_one_is_skipped(tmp_path: Path) -> None:
    """World ids come from code and build; records sort by time; a broken one is left out."""
    older, newer = _world(1, created=100), _world(2, created=200)
    _ = _bundle(tmp_path, older)
    _ = _bundle(tmp_path, newer)
    assert library.world_id("A", "1") != library.world_id("A", "2")
    assert len(older.id) == library.ID_LENGTH
    assert library.load(tmp_path) == [newer, older]
    _ = (library.folder(tmp_path, older) / library.RECORD).write_text("{", encoding="utf-8")
    assert library.load(tmp_path) == [newer]


def test_a_legacy_world_keeps_its_old_visibility_choice_during_migration(tmp_path: Path) -> None:
    world = _world(9)
    _ = _bundle(tmp_path, world)
    path = library.folder(tmp_path, world) / library.RECORD
    record = json.loads(path.read_text(encoding="utf-8"))
    record.pop("show_new_world")
    _ = path.write_text(json.dumps(record), encoding="utf-8")

    migrated = library.migrate_visibility(tmp_path, default=True)

    assert migrated == [replace(world, show_new_world=True)]
    assert library.load_one(library.folder(tmp_path, world)) == migrated[0]


def test_placement_names_and_forgetting(tmp_path: Path) -> None:
    """Kept beside the generator, in the game, or code only; a name is saved; forget removes."""
    world = _world(3)
    _ = _bundle(tmp_path / "data", world)
    profile = tmp_path / "profile"
    (profile / "mod").mkdir(parents=True)
    assert library.placement(tmp_path / "data", profile, world) is Placement.KEPT
    kept = library.kept(tmp_path / "data", world)
    assert kept is not None
    _ = kept.rename(profile / "mod" / world.folder)
    assert library.placement(tmp_path / "data", profile, world) is Placement.IN_GAME
    renamed = library.rename(tmp_path / "data", world, "  Vinland  ")
    assert library.load(tmp_path / "data") == [renamed]
    assert renamed.name == "Vinland"
    library.forget(tmp_path / "data", renamed)
    assert library.load(tmp_path / "data") == []


def test_worlds_in_the_game_without_a_record_are_strays(tmp_path: Path) -> None:
    """A world mod of the project the library does not know is listed; the hub is not."""
    profile = tmp_path / "profile"
    for name, world_like in (("rnw_exp_new_world", True), ("rnw_exp_hub", False)):
        mod = profile / "mod" / name
        (mod / ".metadata").mkdir(parents=True)
        _ = (mod / ".metadata/metadata.json").write_text("{}", encoding="utf-8")
        if world_like:
            (mod / library.MAP_MARKER).mkdir(parents=True)
    assert [path.name for path in library.strays(profile, [])] == ["rnw_exp_new_world"]
    assert library.strays(None, []) == []


def test_the_mod_list_picture_is_covered_unless_asked(tmp_path: Path) -> None:
    """The square is drawn from the covered or the full preview, around the covered columns."""
    world = _world(4)
    folder = _bundle(tmp_path, world)
    mod = folder / world.folder
    assert library.picture(tmp_path, world, revealed=False) == folder / library.PREVIEW_HIDDEN
    assert library.write_thumbnail(tmp_path, world, mod, revealed=False)
    covered = read_rgb(mod / library.THUMBNAIL)
    assert covered.shape == (SIZE, SIZE, 3)
    assert np.all(covered == TERRA_INCOGNITA, axis=2).any()
    assert np.all(covered == TAG_COLOR, axis=2).any()
    assert library.write_thumbnail(tmp_path, world, mod, revealed=True)
    shown = read_rgb(mod / library.THUMBNAIL)
    assert tuple(shown[SIZE // 2, SIZE // 2]) == (96, 160, 72)
    assert not np.all(shown == TAG_COLOR, axis=2).any()
    (folder / library.PREVIEW).unlink()
    assert not library.write_thumbnail(tmp_path, world, mod, revealed=True)


def test_the_selection_cover_is_taken_out_of_the_mod_and_put_back(tmp_path: Path) -> None:
    """Showing removes the cover's files and the folders they leave empty; hiding restores them."""
    world = _world(5)
    folder = _bundle(tmp_path, world)
    mod = folder / world.folder
    relative = "in_game/common/scripted_guis/rnw_new_world.txt"
    assert not library.write_cover(tmp_path, world, mod, covered=True)
    (folder / COVER_COPY / relative).parent.mkdir(parents=True)
    _ = (folder / COVER_COPY / relative).write_text("cover", encoding="utf-8")
    (mod / "in_game/common/scripted_guis").mkdir(parents=True)
    _ = (mod / "in_game/common/other.txt").write_text("kept", encoding="utf-8")
    assert library.write_cover(tmp_path, world, mod, covered=False)
    assert not (mod / "in_game/common/scripted_guis").exists()
    assert (mod / "in_game/common/other.txt").is_file()
    library.show(tmp_path, world, mod, shown=False)
    assert (mod / relative).read_text(encoding="utf-8") == "cover"
    assert np.all(read_rgb(mod / library.THUMBNAIL) == TAG_COLOR, axis=2).any()
    library.show(tmp_path, world, mod, shown=True)
    assert not (mod / relative).exists()
    assert tuple(read_rgb(mod / library.THUMBNAIL)[SIZE // 2, SIZE // 2]) == (96, 160, 72)


def test_a_rename_reaches_the_mods_metadata_and_keeps_the_rest(tmp_path: Path) -> None:
    """The title goes into the metadata's name, in the same layout, and nothing else changes."""
    world = _world(6)
    folder = _bundle(tmp_path, world)
    mod = folder / world.folder
    target = mod / ".metadata/metadata.json"
    _ = target.write_text('{"name": "old", "id": "x", "tags": ["Map"]}', encoding="utf-8-sig")
    named = library.rename(tmp_path, world, "  Vinland  ")
    assert library.retitle(named, mod)
    raw = target.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    document = json.loads(raw.decode("utf-8-sig"))
    assert document == {"name": "RNW: Vinland", "id": "x", "tags": ["Map"]}
    assert library.retitle(library.rename(tmp_path, named, ""), mod)
    title = json.loads(target.read_text(encoding="utf-8-sig"))["name"]
    assert title == f"RNW: Continents {worldname.tag_of(world.id)}"
    assert not list((mod / ".metadata").glob(".*.new"))


def test_a_mod_whose_metadata_cannot_be_written_reports_it(tmp_path: Path) -> None:
    """A missing or unreadable metadata file is False, not an exception, and leaves no scratch."""
    world = _world(7)
    folder = _bundle(tmp_path, world, kept=False)
    (folder / world.folder / ".metadata").mkdir(parents=True)
    assert not library.retitle(world, folder / world.folder)
    _ = (folder / world.folder / ".metadata/metadata.json").write_text("{", encoding="utf-8")
    assert not library.retitle(world, folder / world.folder)
    assert not list((folder / world.folder / ".metadata").glob(".*.new"))


def _record() -> Record:
    return Record(
        format=FORMAT,
        algorithm=1,
        release="0.9.22",
        code="RNW1-TEST",
        preset="continents",
        seed=3,
        settings=build_settings("continents").to_json_data(),
        game=GameRecord("EU5 test", "f" * 64, "1.4.*", "e" * 64, 3),
        output_sha256="d" * 64,
        output_count=2,
    )


def test_a_worlds_record_is_saved_with_it_and_old_or_damaged_records_still_load(
    tmp_path: Path,
) -> None:
    """The record comes back equal; a world without one, or with a damaged one, is listed; a
    record of a newer layout is not, as with a newer schema."""
    world = replace(_world(8), record=_record())
    _ = _bundle(tmp_path, world)
    assert library.load(tmp_path) == [world]
    path = library.folder(tmp_path, world) / library.RECORD
    document = json.loads(path.read_text(encoding="utf-8"))
    document.pop("record")
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    assert library.load(tmp_path) == [replace(world, record=None)]
    document["record"] = {"format": FORMAT, "algorithm": "one"}
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    assert library.load(tmp_path) == [replace(world, record=None)]
    document["record"] = {"format": FORMAT + 1}
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    assert library.load(tmp_path) == []


def test_the_bundles_inputs_and_outputs_are_read_back(tmp_path: Path) -> None:
    """The list of game files and the hashes of the mod's files come from the bundle."""
    world = _world(9)
    folder = _bundle(tmp_path, world, kept=False)
    assert library.inputs_manifest(tmp_path, world) is None
    assert library.exported_outputs(tmp_path, world) is None
    manifest = Manifest({"game/a.txt": "1"})
    _ = (folder / library.INPUTS).write_text(json.dumps(manifest.to_json()), encoding="utf-8")
    files = [
        {"path": f"{world.folder}/in_game/x.txt", "sha256": "5"},
        {"path": f"{world.folder}/.metadata/metadata.json", "sha256": "6"},
        {"path": "preview.png", "sha256": "7"},
    ]
    _ = (folder / library.MANIFEST).write_text(json.dumps({"files": files}), encoding="utf-8")
    assert library.inputs_manifest(tmp_path, world) == manifest
    assert library.exported_outputs(tmp_path, world) == {"in_game/x.txt": "5"}
    _ = (folder / library.INPUTS).write_text("{", encoding="utf-8")
    assert library.inputs_manifest(tmp_path, world) is None


def test_versions_of_one_continent_are_listed_together_with_the_first_made_first(
    tmp_path: Path,
) -> None:
    """Worlds that share a land stand together, indented; continents newest first."""
    del tmp_path
    first = _coded(1, created=100)
    other = _coded(2, created=200)
    version = _coded(1, created=300, rolls={"peoples": 1}, parent=first.id, part="peoples")
    later = _coded(1, created=400, rolls={"resources": 1}, parent=version.id, part="resources")
    assert library.land_of(first) == library.land_of(version) == library.land_of(later)
    assert library.land_of(first) != library.land_of(other)
    listed = library.grouped([other, first, version, later])
    assert [(world.id, depth) for world, depth in listed] == [
        (first.id, 0),
        (version.id, 1),
        (later.id, 1),
        (other.id, 0),
    ]
    broken = replace(other, id="zzzzzzzzzz", code="RNW1-BROKEN")
    assert library.land_of(broken) == "zzzzzzzzzz"


def test_a_version_remembers_what_it_is_a_version_of(tmp_path: Path) -> None:
    """The parent and the part are in the record and come back."""
    parent = _world(20)
    world = replace(_world(21), parent=parent.id, part="peoples")
    _ = _bundle(tmp_path, world)
    [loaded] = library.load(tmp_path)
    assert (loaded.parent, loaded.part) == (parent.id, "peoples")


def test_the_atlas_is_read_from_the_bundle_and_a_world_can_be_revealed(tmp_path: Path) -> None:
    """None without files or with damaged ones; the atlas once there; the choice is kept."""
    world = _world(30)
    folder = _bundle(tmp_path, world, kept=False)
    assert library.atlas(tmp_path, world) is None
    document, labels = atlas_files(synthetic_atlas())
    _ = (folder / ATLAS_JSON).write_bytes(document)
    _ = (folder / ATLAS_LABELS).write_bytes(labels)
    first = library.atlas(tmp_path, world)
    assert first is not None
    assert library.atlas(tmp_path, world) is first
    _ = (folder / ATLAS_LABELS).write_bytes(b"damaged")
    assert library.atlas(tmp_path, world) is None
    assert not world.revealed
    shown = library.reveal(tmp_path, world)
    assert shown.revealed
    assert [item.revealed for item in library.load(tmp_path)] == [True]
    assert not library.reveal(tmp_path, shown, revealed=False).revealed
