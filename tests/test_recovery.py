"""Installed worlds are recognized without changing mods, playsets or existing records."""

from __future__ import annotations

import json
import shutil
from dataclasses import replace
from typing import TYPE_CHECKING, cast

import pytest

from rnw import __version__, atlas
from rnw.app import library, recovery, service
from rnw.app.discovery import GameInstall, Profile
from rnw.app.worldcode import encode, new_code
from rnw.gui.controller import Controller
from tests.fakes import synthetic_atlas
from tests.test_service import FakeExport

if TYPE_CHECKING:
    from pathlib import Path


def _mod(profile: Path, name: str = "rnw_exp_manual", *, code: str | None = None) -> Path:
    mod = profile / "mod" / name
    (mod / ".metadata").mkdir(parents=True)
    (mod / "in_game/map_data").mkdir(parents=True)
    _ = (mod / "in_game/map_data/test.txt").write_text("generated water", encoding="utf-8")
    code = code if code is not None else encode(new_code("continents", 42))
    _ = (mod / ".metadata/metadata.json").write_text(
        json.dumps(
            {
                "name": "RNW: Vinland",
                "version": __version__,
                "short_description": f"World code {code}.",
            }
        ),
        encoding="utf-8-sig",
    )
    return mod


def test_metadata_code_is_adopted_in_place_without_guessing_a_build(tmp_path: Path) -> None:
    profile, data = tmp_path / "profile", tmp_path / "data"
    mod = _mod(profile)
    original = (mod / ".metadata/metadata.json").read_bytes()
    _ = (profile / "playsets.json").write_text("leave this alone", encoding="utf-8")
    world = recovery.adopt(data, profile)[0]
    assert world.name == "Vinland"
    assert world.seed == 42
    assert world.record is None
    assert world.game_build == ""
    assert world.folder == mod.name
    assert library.folder(data, world).name != mod.name
    assert library.placement(data, profile, world) is library.Placement.IN_GAME
    assert (mod / ".metadata/metadata.json").read_bytes() == original
    assert (profile / "playsets.json").read_text() == "leave this alone"
    assert library.load(data) == [world]
    assert not library.strays(profile, library.load(data))
    assert recovery.adopt(data, profile) == []
    service.delete(world, data, Profile(profile, "chosen", has_mods=True))
    assert not mod.exists()
    assert library.load(data) == []


@pytest.mark.parametrize("code", ["unreadable", "RNW1-BAD-CHECKSUM"])
def test_a_mod_without_a_valid_code_stays_visible_as_unregistered(
    tmp_path: Path, code: str
) -> None:
    profile = tmp_path / "profile"
    mod = _mod(profile, code=code)
    assert recovery.adopt(tmp_path / "data", profile) == []
    assert library.strays(profile, []) == [mod]


def test_a_generated_mod_restores_atlas_record_and_previews_after_library_loss(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    data = tmp_path / "data"
    request = service.Request(
        game=GameInstall(tmp_path / "game", None, "26043558"),
        code=new_code("continents", 42),
        data=data,
        profile=Profile(profile, "chosen", has_mods=False),
        install=True,
        show_new_world=True,
    )
    made = service.generate(request, exporter=FakeExport())
    assert made.installed is not None
    assert made.world.record is not None
    world = replace(
        made.world,
        notes="PRIVATE NOTE",
        user_tag="PRIVATE TAG",
        starred=True,
        record=replace(made.world.record, release=made.world.generator),
    )
    bundle = library.folder(data, world)
    document, labels = atlas.to_files(synthetic_atlas())
    _ = (bundle / atlas.JSON_FILE).write_bytes(document)
    _ = (bundle / atlas.LABELS_FILE).write_bytes(labels)
    recovery.write(data, world, made.installed)
    receipt = cast(
        "dict[str, object]",
        json.loads((made.installed / recovery.RECEIPT / library.RECORD).read_text()),
    )
    assert receipt["notes"] == receipt["user_tag"] == ""
    assert not receipt["starred"]
    assert (made.installed / recovery.RECEIPT / library.RECORD).is_file()
    shutil.rmtree(bundle)
    restored = recovery.adopt(data, profile)[0]
    assert restored.code == world.code
    assert restored.game_build == world.game_build
    assert restored.record == world.record
    assert library.atlas(data, restored) is not None
    assert library.picture(data, restored, revealed=True) is not None
    assert (library.folder(data, restored) / library.INPUTS).is_file()
    assert library.placement(data, profile, restored) is library.Placement.IN_GAME


def test_existing_library_records_are_never_overwritten(tmp_path: Path) -> None:
    data, profile = tmp_path / "data", tmp_path / "profile"
    mod = _mod(profile)
    first = recovery.adopt(data, profile)[0]
    changed = replace(first, notes="my campaign", name="My name")
    library.save(data, changed)
    before = (library.folder(data, first) / library.RECORD).read_bytes()
    assert recovery.adopt(data, profile) == []
    assert (library.folder(data, first) / library.RECORD).read_bytes() == before
    assert mod.exists()


def test_metadata_first_copy_is_upgraded_only_when_valid_assets_arrive(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    source_data, data = tmp_path / "source", tmp_path / "recovered"
    made = service.generate(
        service.Request(
            game=GameInstall(tmp_path / "game", None, "26043558"),
            code=new_code("continents", 42),
            data=source_data,
            profile=Profile(profile, "chosen", has_mods=False),
        ),
        exporter=FakeExport(),
    )
    assert made.installed is not None
    assert made.world.record is not None
    original = replace(made.world, record=replace(made.world.record, release=made.world.generator))
    recovery.write(source_data, original, made.installed)
    receipt = made.installed / recovery.RECEIPT
    pending = receipt.rename(tmp_path / "arriving-later")
    _ = (made.installed / ".metadata/metadata.json").write_text(
        json.dumps(
            {
                "name": "RNW: Vinland",
                "version": __version__,
                "short_description": f"World code {original.code}.",
            }
        ),
        encoding="utf-8",
    )
    [partial] = recovery.adopt(data, profile)
    assert partial.record is None
    partial = replace(partial, name="My campaign", notes="keep this", starred=True)
    library.save(data, partial)
    before = (library.folder(data, partial) / library.RECORD).read_bytes()
    _ = pending.rename(receipt)
    listing = receipt / library.INPUTS
    valid_inputs = listing.read_bytes()
    _ = listing.write_text('{"format": 1, "files": {"changed": "wrong"}}', encoding="utf-8")
    signature = recovery.signature(data, profile)
    assert recovery.adopt(data, profile) == []
    assert (library.folder(data, partial) / library.RECORD).read_bytes() == before
    _ = listing.write_bytes(valid_inputs)
    assert recovery.signature(data, profile) != signature
    [upgraded] = recovery.adopt(data, profile)
    assert upgraded.id == partial.id
    assert upgraded.record == original.record
    assert upgraded.game_build == original.game_build
    assert upgraded.name == "My campaign"
    assert upgraded.notes == "keep this"
    assert upgraded.starred
    assert library.atlas(data, upgraded) is not None
    assert recovery.adopt(data, profile) == []


def test_bad_receipts_and_symlinks_cannot_write_partial_library_records(tmp_path: Path) -> None:
    profile, data = tmp_path / "profile", tmp_path / "data"
    mod = _mod(profile)
    receipt = mod / recovery.RECEIPT
    receipt.mkdir()
    _ = (receipt / library.RECORD).write_text("[]", encoding="utf-8")
    assert recovery.adopt(data, profile) == []
    assert library.load(data) == []
    (receipt / library.RECORD).unlink()
    try:
        (receipt / library.RECORD).symlink_to(mod / ".metadata/metadata.json")
    except OSError:
        pytest.skip("Symbolic links are unavailable")
    assert recovery.adopt(data, profile) == []
    assert library.load(data) == []


def test_open_controller_detects_new_mods_and_external_library_records(tmp_path: Path) -> None:
    data, profile = tmp_path / "data", tmp_path / "profile"
    controller = Controller(data=data)
    controller.profile = Profile(profile, "chosen", has_mods=True)
    controller.refresh_library()
    changes: list[bool] = []
    controller.subscribe(lambda: changes.append(True))
    controller.poll_library()
    assert changes == []
    mod = _mod(profile)
    controller.poll_library()
    assert len(controller.worlds) == 1
    assert not controller.strays
    world = controller.worlds[0]
    assert controller.removable_entries((world.id,)) == (mod.name,)
    assert len(changes) == 1
    controller.poll_library()
    assert len(changes) == 1
    library.save(data, replace(world, name="Changed outside"))
    controller.poll_library()
    assert controller.worlds[0].name == "Changed outside"


def test_an_installed_alias_cannot_escape_the_mod_directory(tmp_path: Path) -> None:
    mod = _mod(tmp_path / "profile")
    world = recovery.adopt(tmp_path / "data", tmp_path / "profile")[0]
    row = library.document(world)
    row["mod_folder"] = "rnw_exp_../../elsewhere"
    with pytest.raises(ValueError, match="simple RNW"):
        _ = library.world_of(row)
    assert mod.is_dir()


def test_same_export_folder_in_another_profile_cannot_bind_or_delete_a_different_world(
    tmp_path: Path,
) -> None:
    data, first, second = tmp_path / "data", tmp_path / "first", tmp_path / "second"
    first_mod = _mod(first)
    [one] = recovery.adopt(data, first)
    second_mod = _mod(second, code=encode(new_code("continents", 99)))
    assert library.placement(data, second, one) is library.Placement.CODE_ONLY
    [two] = recovery.adopt(data, second)
    assert two.seed == 99
    assert one.id != two.id
    assert library.installed(first, one) == first_mod
    assert library.installed(first, two) is None
    assert library.installed(second, two) == second_mod
    service.delete(one, data, Profile(second, "chosen", has_mods=True))
    assert second_mod.exists()
    assert first_mod.exists()
