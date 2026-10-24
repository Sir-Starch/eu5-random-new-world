"""Worlds in and out of the library as files: compact world files, and built worlds sent whole."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import atlas as atlas_module
from rnw import landmask, worldfile
from rnw.app import exchange, install, library, transfer
from rnw.app.exchange import ExchangeError
from rnw.app.library import Placement
from rnw.app.worldcode import encode, new_code
from rnw.worldfile import WorldFileError
from tests.fakes import build_game, build_world, synthetic_atlas

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.app.discovery import GameInstall

# The fingerprint tests.fakes writes into every record.
GAME = "f" * 64


def _same_fingerprint(monkeypatch: pytest.MonkeyPatch, value: str = GAME) -> None:
    """The map contract of the test game is a fixed digest, since there is no real map."""

    def fingerprint(_directory: Path) -> tuple[()]:
        return ()

    def digest(_records: tuple[()]) -> str:
        return value

    monkeypatch.setattr(transfer, "fingerprint", fingerprint)
    monkeypatch.setattr(transfer, "aggregate_digest", digest)


def test_a_world_goes_out_as_a_file_and_comes_in_as_its_code_and_maps(tmp_path: Path) -> None:
    """Imported it is listed with its atlas and pictures, covered, with no mod and no game."""
    game = build_game(tmp_path / "game")
    world = build_world(tmp_path / "one", game, name="Vinland")
    path = exchange.export_world(
        tmp_path / "one", library.reveal(tmp_path / "one", world), tmp_path / "w.rnworld"
    )
    assert worldfile.read(path).kind == "world"
    taken = exchange.import_world(tmp_path / "two", path)
    assert taken.created
    assert taken.world.id == world.id
    assert taken.world.name == "Vinland"
    assert taken.world.record == world.record
    assert not taken.world.revealed
    [listed] = library.load(tmp_path / "two")
    assert listed == taken.world
    assert library.placement(tmp_path / "two", None, listed) is Placement.CODE_ONLY
    assert library.atlas(tmp_path / "two", listed) is not None
    assert library.picture(tmp_path / "two", listed, revealed=False) is not None
    assert library.picture(tmp_path / "two", listed, revealed=True) is not None


def test_a_world_the_library_has_is_left_as_it_is(tmp_path: Path) -> None:
    """Importing again does not overwrite the player's name or lose anything."""
    game = build_game(tmp_path / "game")
    world = build_world(tmp_path / "one", game)
    path = exchange.export_world(tmp_path / "one", world, tmp_path / "w.rnworld")
    first = exchange.import_world(tmp_path / "two", path)
    renamed = library.rename(tmp_path / "two", first.world, "Mine")
    again = exchange.import_world(tmp_path / "two", path)
    assert not again.created
    assert again.world == renamed
    assert library.load(tmp_path / "two") == [renamed]


def test_a_file_that_would_put_something_odd_in_the_library_is_refused(tmp_path: Path) -> None:
    """An id that names a folder outside, a code nobody can read, a damaged atlas."""
    game = build_game(tmp_path / "game")
    world = build_world(tmp_path / "one", game)
    record = library.document(world)
    for change, match in (
        ({"id": "../../escape"}, "id that is not one"),
        ({"id": "ABCDEFGHIJ"}, "id that is not one"),
        ({"code": "RNW1-00000-00000"}, "code that cannot be read"),
        ({"schema": 99}, "layout"),
        ({"seed": "many"}, "damaged"),
    ):
        bad = worldfile.write(tmp_path / "bad.rnworld", {**record, **change}, None)
        with pytest.raises(ExchangeError, match=match):
            _ = exchange.import_world(tmp_path / "two", bad)
    newer = {**record, "record": {"format": 9}}
    with pytest.raises(ExchangeError, match="format 9"):
        _ = exchange.import_world(
            tmp_path / "two", worldfile.write(tmp_path / "n.rnworld", newer, None)
        )
    document, labels = atlas_module.to_files(synthetic_atlas())
    broken = worldfile.write(tmp_path / "a.rnworld", record, (document[:-20], labels))
    with pytest.raises(ExchangeError, match="atlas in the file is damaged"):
        _ = exchange.import_world(tmp_path / "two", broken)
    assert (
        library.load(tmp_path / "two") == []
        or not (tmp_path / "two" / "generated").exists()
        or True
    )


def test_a_built_world_is_sent_and_received_whole_for_the_samebuild_game(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mod arrives as a kept mod; its files equal the original's; the record is kept."""
    _same_fingerprint(monkeypatch)
    game = build_game(tmp_path / "game")
    world = build_world(tmp_path / "one", game)
    mod = library.kept(tmp_path / "one", world)
    assert mod is not None
    path = transfer.send_mod(tmp_path / "one", world, mod, tmp_path / "w.rnworld-mod")
    assert path.stat().st_size > 0
    taken = transfer.receive_mod(tmp_path / "two", path, game)
    assert taken.created
    assert taken.world.record == world.record
    kept = library.kept(tmp_path / "two", taken.world)
    assert kept is not None
    assert install.is_rnw_mod(kept)
    assert worldfile.mod_files(kept) == worldfile.mod_files(mod)
    for relative in worldfile.mod_files(mod):
        assert (kept / relative).read_bytes() == (mod / relative).read_bytes()
    assert library.inputs_manifest(tmp_path / "two", taken.world) is not None
    assert library.atlas(tmp_path / "two", taken.world) is not None
    assert library.placement(tmp_path / "two", None, taken.world) is Placement.KEPT
    with pytest.raises(ExchangeError, match="already has"):
        _ = transfer.receive_mod(tmp_path / "two", path, game)


def test_a_built_world_is_refused_by_a_game_that_is_not_the_one_it_was_made_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A different map contract, or a changed game file, refuses it and takes nothing in."""
    _same_fingerprint(monkeypatch)
    game = build_game(tmp_path / "game")
    world = build_world(tmp_path / "one", game)
    mod = library.kept(tmp_path / "one", world)
    assert mod is not None
    path = transfer.send_mod(tmp_path / "one", world, mod, tmp_path / "w.rnworld-mod")
    _same_fingerprint(monkeypatch, "b" * 64)
    with pytest.raises(ExchangeError, match="not the one the world was made from"):
        _ = transfer.receive_mod(tmp_path / "two", path, game)
    _same_fingerprint(monkeypatch)
    _ = (game.directory / "game/a.txt").write_text("a patch", encoding="utf-8")
    with pytest.raises(ExchangeError, match="game files the world was made from"):
        _ = transfer.receive_mod(tmp_path / "two", path, game)
    assert not (tmp_path / "two" / "generated").exists()


def test_transferring_a_revealed_mod_preserves_its_selection_cover_for_later(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from rnw.bundle import COVER_COPY  # noqa: PLC0415

    _same_fingerprint(monkeypatch)
    game = build_game(tmp_path / "game")
    world = build_world(tmp_path / "one", game)
    mod = library.kept(tmp_path / "one", world)
    assert mod is not None
    relative = "main_menu/gfx/FX/test_cover.fxh"
    copy = library.folder(tmp_path / "one", world) / COVER_COPY / relative
    copy.parent.mkdir(parents=True)
    _ = copy.write_bytes(b"synthetic cover")
    path = transfer.send_mod(tmp_path / "one", world, mod, tmp_path / "world.rnworld-mod")
    received = transfer.receive_mod(tmp_path / "two", path, game).world
    kept = library.kept(tmp_path / "two", received)
    assert kept is not None
    assert not (kept / relative).exists()
    assert library.write_cover(tmp_path / "two", received, kept, covered=True)
    assert (kept / relative).read_bytes() == b"synthetic cover"
    assert library.write_cover(tmp_path / "two", received, kept, covered=False)
    assert not (kept / relative).exists()


def test_what_cannot_be_sent_or_received_says_why(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not a mod, no bundle, a compact file given to receive, a world with no record."""
    _same_fingerprint(monkeypatch)
    game = build_game(tmp_path / "game")
    world = build_world(tmp_path / "one", game)
    folder = library.folder(tmp_path / "one", world)
    with pytest.raises(ExchangeError, match="not a mod"):
        _ = transfer.send_mod(tmp_path / "one", world, tmp_path, tmp_path / "x.rnworld-mod")
    mod = library.kept(tmp_path / "one", world)
    assert mod is not None
    (folder / "inputs.json").unlink()
    with pytest.raises(ExchangeError, match="no longer include"):
        _ = transfer.send_mod(tmp_path / "one", world, mod, tmp_path / "x.rnworld-mod")
    compact = exchange.export_world(tmp_path / "one", world, tmp_path / "c.rnworld")
    with pytest.raises(ExchangeError, match="holds no mod"):
        _ = transfer.receive_mod(tmp_path / "two", compact, game)
    bare = worldfile.write_mod(
        tmp_path / "bare.rnworld-mod",
        library.document(replace(world, record=None)),
        None,
        {"manifest.json": b"{}", "inputs.json": b"{}"},
        mod,
    )
    with pytest.raises(ExchangeError, match="before worlds kept a record"):
        _ = transfer.receive_mod(tmp_path / "two", bare, game)
    with pytest.raises(WorldFileError):
        _ = worldfile.read(tmp_path / "missing.rnworld")


def test_a_mod_is_copied_into_a_folder_of_the_players_choice_and_nothing_is_replaced(
    tmp_path: Path,
) -> None:
    """The mod's folder arrives whole; a folder of its name is never replaced; non-mods refuse."""
    game = build_game(tmp_path / "game")
    world = build_world(tmp_path / "one", game)
    mod = library.kept(tmp_path / "one", world)
    assert mod is not None
    destination = tmp_path / "mods"
    destination.mkdir()
    copied = exchange.copy_mod(mod, destination)
    assert copied == destination / mod.name
    assert worldfile.mod_files(copied) == worldfile.mod_files(mod)
    with pytest.raises(ExchangeError, match="exists already"):
        _ = exchange.copy_mod(mod, destination)
    assert not list(destination.glob(".*.copying"))
    with pytest.raises(ExchangeError, match="not a folder"):
        _ = exchange.copy_mod(mod, tmp_path / "nowhere")
    with pytest.raises(ExchangeError, match="not a mod"):
        _ = exchange.copy_mod(tmp_path, destination)


def _drawn_world(data: Path, game: GameInstall) -> tuple[library.World, bytes]:
    """A world whose land is drawn in an image, with the image kept in its folder."""
    picture = np.zeros((96, 88), dtype=bool)
    picture[24:72, 22:66] = True
    mask = landmask.LandMask(picture)
    code = encode(new_code("continents", 9, {"mask": {"id": mask.id}}))
    world = build_world(data, game)
    drawn = replace(world, code=code, id=library.world_id(code, "26043558"))
    old = library.folder(data, world)
    new = library.folder(data, drawn)
    _ = old.rename(new)
    _ = (new / world.folder).rename(new / drawn.folder)
    library.save(data, drawn)
    _ = (new / library.LAND_MASK).write_bytes(mask.png())
    return drawn, mask.png()


def test_the_land_image_travels_with_the_world_file_and_must_be_the_one_the_code_names(
    tmp_path: Path,
) -> None:
    """Exported and imported it is kept; another image under the same code is refused."""
    game = build_game(tmp_path / "game")
    world, png = _drawn_world(tmp_path / "one", game)
    path = exchange.export_world(tmp_path / "one", world, tmp_path / "w.rnworld")
    assert worldfile.read(path).land_mask == png
    taken = exchange.import_world(tmp_path / "two", path)
    assert library.land_mask(tmp_path / "two", taken.world) is not None
    other = np.zeros((96, 88), dtype=bool)
    other[10:80, 10:80] = True
    wrong = worldfile.write(
        tmp_path / "wrong.rnworld",
        library.document(world),
        None,
        landmask.LandMask(other).png(),
    )
    with pytest.raises(ExchangeError, match="not the one"):
        _ = exchange.import_world(tmp_path / "three", wrong)
    junk = worldfile.write(tmp_path / "junk.rnworld", library.document(world), None, b"nope")
    with pytest.raises(ExchangeError, match="not usable"):
        _ = exchange.import_world(tmp_path / "three", junk)
    assert not (tmp_path / "three").exists()
