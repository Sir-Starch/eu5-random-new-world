"""Making worlds for a player: each a mod of its own, recorded, added and removed again."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw import epoch, worldname
from rnw.app import install, library, service
from rnw.app.discovery import GameInstall, Profile
from rnw.app.library import Placement
from rnw.app.service import Request, generate
from rnw.app.worldcode import encode, new_code
from rnw.bundle import COVER_COPY
from rnw.eu5_lobby import SCRIPTED_GUI_FILE
from rnw.pictures import TERRA_INCOGNITA
from rnw.png import COLOR_RGB, encode_png
from rnw.progress import STAGES, Cancelled, Progress
from rnw.record import Verdict, manifest_digest
from tests.fakes import write_bundle_record

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.landmask import LandMask
    from rnw.worldname import Label


def _png(color: tuple[int, int, int]) -> bytes:
    image = np.zeros((32, 64, 3), dtype=np.uint8)
    image[:] = (25, 45, 90)
    image[:, :20] = color
    return encode_png(image, color_type=COLOR_RGB, compression="zlib")


class FakeExport:
    """Writes a tiny bundle like the export does and reports through ``progress``."""

    def __init__(
        self, *, fail: Exception | None = None, cancel: bool = False, drift_after: int | None = None
    ) -> None:
        self.fail: Exception | None = fail
        self.cancel: bool = cancel
        self.drift_after: int | None = drift_after
        self.calls: list[tuple[int, str | None]] = []
        self.labels: list[Label | None] = []
        self.masks: list[LandMask | None] = []

    def __call__(  # noqa: PLR0913
        self,
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
        del settings, settings_file, accept_build, replace, check_memory, cache_dir
        self.calls.append((seed, world_code))
        self.labels.append(world_label)
        self.masks.append(land_mask)
        if progress is not None and self.cancel:
            progress.cancel()
            progress.checkpoint()
        if self.fail is not None:
            raise self.fail
        mod = output / output.name
        (mod / ".metadata").mkdir(parents=True, exist_ok=True)
        _ = (mod / ".metadata/metadata.json").write_text('{"name": "World"}', encoding="utf-8")
        (mod / "in_game/map_data").mkdir(parents=True, exist_ok=True)
        drifting = self.drift_after is not None and len(self.calls) > self.drift_after
        _ = (mod / "seed.txt").write_text(str(seed) + ("!" if drifting else ""), encoding="utf-8")
        for root in (mod, output / COVER_COPY):
            (root / SCRIPTED_GUI_FILE).parent.mkdir(parents=True, exist_ok=True)
            _ = (root / SCRIPTED_GUI_FILE).write_text("cover", encoding="utf-8")
        _ = (output / "preview.png").write_bytes(_png((96, 160, 72)))
        _ = (output / "preview_hidden.png").write_bytes(_png(TERRA_INCOGNITA))
        record = write_bundle_record(
            output, game_dir, seed=seed, preset="continents", code=world_code
        )
        return {
            "status": "NOT GAME VALIDATED",
            "canvas": {},
            "generated": {},
            "invariants": {},
            **record,
        }


def _request(tmp_path: Path, *, seed: int = 4242, install: bool = True) -> Request:
    profile = tmp_path / "profile"
    profile.mkdir(exist_ok=True)
    return Request(
        game=GameInstall(tmp_path / "game", None, "26043558"),
        code=new_code("continents", seed),
        data=tmp_path / "data",
        profile=Profile(profile, "linux", has_mods=False),
        install=install,
    )


def test_a_world_file_only_needs_no_profile_and_keeps_no_built_mod(tmp_path: Path) -> None:
    from rnw import worldfile  # noqa: PLC0415

    output = tmp_path / "saved.rnworld"
    request = replace(_request(tmp_path, install=False), profile=None, world_file=output)
    result = generate(request, exporter=FakeExport())
    assert output.is_file()
    assert worldfile.read(output).kind == worldfile.KIND_WORLD
    assert result.installed is None
    assert library.kept(request.data, result.world) is None
    assert library.load(request.data)[0].id == result.world.id
    assert not (tmp_path / "profile/mod").exists()


def test_a_mod_can_go_directly_to_a_chosen_folder_without_a_profile(tmp_path: Path) -> None:
    destination = tmp_path / "my_mods"
    destination.mkdir()
    request = replace(_request(tmp_path, install=False), profile=None, output_folder=destination)
    result = generate(request, exporter=FakeExport())
    assert install.is_rnw_mod(destination / result.world.folder)
    assert not (tmp_path / "profile/mod").exists()


def test_personal_notes_survive_regeneration_of_the_same_world(tmp_path: Path) -> None:
    request = _request(tmp_path, install=False)
    first = generate(request, exporter=FakeExport()).world
    library.save(
        request.data, replace(first, notes="Keep this coast", user_tag="coop", starred=True)
    )
    second = generate(request, exporter=FakeExport()).world
    assert (second.notes, second.user_tag, second.starred) == ("Keep this coast", "coop", True)


def test_every_world_is_a_mod_of_its_own_and_is_moved_into_the_game(tmp_path: Path) -> None:
    """Two seeds make two mods side by side; the bundle keeps the pictures, not a second copy."""
    export = FakeExport()
    first = generate(_request(tmp_path, seed=1), Progress(), export)
    second = generate(_request(tmp_path, seed=2), Progress(), export)
    assert first.world.folder != second.world.folder
    assert export.calls == [(1, first.world.code), (2, second.world.code)]
    mods = tmp_path / "profile" / "mod"
    assert sorted(path.name for path in mods.iterdir()) == sorted(
        [first.world.folder, second.world.folder]
    )
    assert first.installed == mods / first.world.folder
    assert not (first.bundle / first.world.folder).exists()
    assert (first.bundle / library.PREVIEW_HIDDEN).is_file()
    worlds = library.load(tmp_path / "data")
    assert {world.id for world in worlds} == {first.world.id, second.world.id}
    assert library.placement(tmp_path / "data", tmp_path / "profile", first.world) is (
        Placement.IN_GAME
    )


def test_the_same_code_on_the_same_build_is_the_same_world(tmp_path: Path) -> None:
    """Generating a code again replaces its own mod and record, nothing else."""
    export = FakeExport()
    first = generate(_request(tmp_path, seed=5), Progress(), export)
    again = generate(_request(tmp_path, seed=5), Progress(), export)
    assert again.world.id == first.world.id
    assert len(library.load(tmp_path / "data")) == 1
    assert install.installed_mods(tmp_path / "profile") == [again.installed]


def test_a_world_made_without_adding_is_kept_and_added_later(tmp_path: Path) -> None:
    """Unticked 'add to the game' keeps the mod beside the generator until it is added."""
    request = _request(tmp_path, install=False)
    result = generate(request, Progress(), FakeExport())
    assert result.installed is None
    assert library.placement(request.data, tmp_path / "profile", result.world) is Placement.KEPT
    assert request.profile is not None
    added = service.add_to_game(
        result.world, game=request.game, data=request.data, profile=request.profile
    )
    assert added.installed == tmp_path / "profile" / "mod" / result.world.folder
    assert library.kept(request.data, result.world) is None


def test_removing_keeps_the_record_and_deleting_forgets_it(tmp_path: Path) -> None:
    """Out of the game, a world is code and pictures; deleted, it is gone everywhere."""
    request = _request(tmp_path)
    result = generate(request, Progress(), FakeExport())
    assert request.profile is not None
    service.remove_from_game(result.world.folder, request.profile)
    assert library.placement(request.data, tmp_path / "profile", result.world) is (
        Placement.CODE_ONLY
    )
    assert library.load(request.data) == [result.world]
    again = generate(_request(tmp_path), Progress(), FakeExport())
    service.delete(again.world, request.data, request.profile)
    assert library.load(request.data) == []
    assert install.installed_mods(tmp_path / "profile") == []


def test_a_missing_profile_is_refused_before_any_work(tmp_path: Path) -> None:
    """Asking to add a world without a profile fails at once and records nothing."""
    request = _request(tmp_path)
    request = Request(game=request.game, code=request.code, data=request.data, install=True)
    export = FakeExport()
    with pytest.raises(install.InstallError):
        _ = generate(request, Progress(), export)
    assert export.calls == []
    assert library.load(request.data) == []


def test_failures_and_cancels_record_nothing(tmp_path: Path) -> None:
    """An export error or a cancel is raised; no world is recorded and nothing is added."""
    request = _request(tmp_path)
    with pytest.raises(RuntimeError, match="boom"):
        _ = generate(request, Progress(), FakeExport(fail=RuntimeError("boom")))
    with pytest.raises(Cancelled):
        _ = generate(request, Progress(), FakeExport(cancel=True))
    assert library.load(request.data) == []
    assert install.installed_mods(tmp_path / "profile") == []


def test_the_mod_shows_the_new_world_only_when_asked(tmp_path: Path) -> None:
    """With the player's choice the mod gets the full picture and loses the selection cover."""
    request = _request(tmp_path)
    shown = Request(
        game=request.game,
        code=request.code,
        data=request.data,
        profile=request.profile,
        show_new_world=True,
    )
    result = generate(shown, Progress(), FakeExport())
    assert result.installed is not None
    assert (result.installed / library.THUMBNAIL).is_file()
    assert not (result.installed / SCRIPTED_GUI_FILE).exists()
    assert (library.folder(request.data, result.world) / COVER_COPY / SCRIPTED_GUI_FILE).is_file()
    assert encode(request.code) == result.world.code
    hidden = generate(_request(tmp_path, seed=7), Progress(), FakeExport())
    assert hidden.installed is not None
    assert (hidden.installed / SCRIPTED_GUI_FILE).is_file()
    assert result.world.show_new_world is True
    assert hidden.world.show_new_world is False


def test_adding_a_kept_world_applies_its_choice_without_exporting_again(tmp_path: Path) -> None:
    export = FakeExport()
    request = _request(tmp_path, install=False)
    result = generate(replace(request, show_new_world=True), Progress(), export)
    profile = Profile(tmp_path / "profile", "linux", has_mods=False)
    added = service.add_to_game(
        result.world,
        game=request.game,
        data=request.data,
        profile=profile,
        show_new_world=False,
        exporter=export,
    )

    assert len(export.calls) == 1
    assert added.world.show_new_world is False
    assert added.installed is not None
    assert (added.installed / SCRIPTED_GUI_FILE).is_file()


def test_install_waits_while_the_game_holds_a_mod_of_that_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refused moves are retried until the game lets go; the window shows the instruction."""
    monkeypatch.setattr(service, "WAIT_PAUSE", 0.0)
    real = install.put_in_place
    refusals = [2]

    def held(incoming: Path) -> Path:
        if refusals[0] > 0:
            refusals[0] -= 1
            message = "The game is using the world"
            raise install.WorldInUseError(message)
        return real(incoming)

    monkeypatch.setattr(install, "put_in_place", held)
    labels: list[str] = []
    result = generate(
        _request(tmp_path), Progress(lambda update: labels.append(update.label)), FakeExport()
    )
    assert result.installed == tmp_path / "profile" / "mod" / result.world.folder
    assert STAGES["waiting for the game"].label in labels


def test_a_cancel_while_waiting_keeps_the_world_beside_the_generator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancel stops the wait; the made world stays recorded and kept, ready to be added."""
    monkeypatch.setattr(service, "WAIT_PAUSE", 0.0)
    progress = Progress()

    def held(incoming: Path) -> Path:
        progress.cancel()
        message = f"The game is using {incoming.name}"
        raise install.WorldInUseError(message)

    monkeypatch.setattr(install, "put_in_place", held)
    with pytest.raises(Cancelled):
        _ = generate(_request(tmp_path), progress, FakeExport())
    [world] = library.load(tmp_path / "data")
    assert library.placement(tmp_path / "data", tmp_path / "profile", world) is Placement.KEPT


def test_without_a_progress_a_held_mod_is_an_error_at_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The command line has no Cancel button, so it does not wait; the world is kept."""

    def held(incoming: Path) -> Path:
        message = f"The game is using {incoming.name}"
        raise install.WorldInUseError(message)

    monkeypatch.setattr(install, "put_in_place", held)
    with pytest.raises(install.WorldInUseError):
        _ = generate(_request(tmp_path), None, FakeExport())
    [world] = library.load(tmp_path / "data")
    assert library.kept(tmp_path / "data", world) is not None


def test_the_export_is_given_the_title_and_the_tag_of_the_world(tmp_path: Path) -> None:
    """The title is ``RNW: <Type> <TAG>`` from the world's id; the player's name replaces it."""
    export = FakeExport()
    plain = generate(_request(tmp_path, seed=8), Progress(), export)
    [label] = export.labels
    assert label is not None
    assert label.tag == worldname.tag_of(plain.world.id)
    assert label.title == f"RNW: Continents {label.tag}"
    named = replace(_request(tmp_path, seed=9), name="  Vinland  ")
    result = generate(named, Progress(), export)
    assert export.labels[-1] is not None
    assert export.labels[-1].title == "RNW: Vinland"
    assert result.world.name == "Vinland"


def test_a_world_made_again_keeps_the_players_name_only_on_the_same_build(tmp_path: Path) -> None:
    """The same code on the same build is the same world and keeps its name; another build, none."""
    export = FakeExport()
    data = tmp_path / "data"
    profile = Profile(tmp_path / "profile", "linux", has_mods=False)
    made = generate(_request(tmp_path, seed=10), Progress(), export)
    named = library.rename(data, made.world, "Vinland")
    service.remove_from_game(named.folder, profile)
    game = GameInstall(tmp_path / "game", None, "26043558")
    again = service.add_to_game(named, game=game, data=data, profile=profile, exporter=export)
    assert again.world.id == named.id
    assert again.world.name == "Vinland"
    assert export.labels[-1] is not None
    assert export.labels[-1].title == "RNW: Vinland"
    service.remove_from_game(again.world.folder, profile)
    other = GameInstall(tmp_path / "game", None, "99999999")
    later = service.add_to_game(
        again.world, game=other, data=data, profile=profile, exporter=export
    )
    assert later.world.id != again.world.id
    assert later.world.name == ""
    assert export.labels[-1] is not None
    assert export.labels[-1].title == f"RNW: Continents {worldname.tag_of(later.world.id)}"


def _checked(tmp_path: Path, export: FakeExport) -> tuple[library.World, GameInstall]:
    """A world made by ``export`` and kept beside the generator, with a game of two files."""
    game_dir = tmp_path / "game"
    for relative in ("game/a.txt", "game/b.txt"):
        (game_dir / relative).parent.mkdir(parents=True, exist_ok=True)
        _ = (game_dir / relative).write_text(relative, encoding="utf-8")
    made = generate(_request(tmp_path, install=False), Progress(), export)
    return made.world, GameInstall(game_dir, None, "26043558")


def test_a_world_keeps_the_record_of_how_it_was_made(tmp_path: Path) -> None:
    """The record from the export is in the world's record file and comes back from the library."""
    export = FakeExport()
    world, _game = _checked(tmp_path, export)
    assert world.record is not None
    assert world.record.seed == 4242
    assert world.record.algorithm == epoch.CURRENT
    assert world.record.game.inputs_count == 2
    assert library.load(tmp_path / "data") == [world]
    assert library.inputs_manifest(tmp_path / "data", world) is not None
    outputs = library.exported_outputs(tmp_path / "data", world)
    assert outputs is not None
    assert manifest_digest(outputs) == world.record.output_sha256
    assert ".metadata/metadata.json" not in outputs


def test_a_world_that_is_made_again_the_same_checks_out_and_leaves_no_scratch(
    tmp_path: Path,
) -> None:
    """The rebuild equals the record: reproduced, and the scratch folder is gone."""
    export = FakeExport()
    world, game = _checked(tmp_path, export)
    found = service.check(
        world, game=game, data=tmp_path / "data", progress=Progress(), exporter=export
    )
    assert found.verdict is Verdict.IDENTICAL
    assert found.reproduced is True
    assert found.differing == []
    assert len(export.calls) == 2
    assert not list((tmp_path / "data" / "generated").glob("rnw_exp_check_*"))


def test_a_rebuild_that_differs_names_the_files(tmp_path: Path) -> None:
    """When the rebuild is not the same bytes, the files that differ are listed."""
    export = FakeExport(drift_after=1)
    world, game = _checked(tmp_path, export)
    found = service.check(world, game=game, data=tmp_path / "data", exporter=export)
    assert found.reproduced is False
    assert found.verdict is Verdict.OTHER_INPUTS
    assert found.differing == ["seed.txt"]


def test_changed_game_files_are_named_without_a_rebuild(tmp_path: Path) -> None:
    """A game file the world read, edited or gone, answers the check at once."""
    export = FakeExport()
    world, game = _checked(tmp_path, export)
    _ = (game.directory / "game/a.txt").write_text("a patch", encoding="utf-8")
    (game.directory / "game/b.txt").unlink()
    found = service.check(world, game=game, data=tmp_path / "data", exporter=export)
    assert found.verdict is Verdict.OTHER_INPUTS
    assert found.reproduced is None
    assert sorted(found.changed_inputs) == ["game/a.txt", "game/b.txt"]
    assert len(export.calls) == 1
    changed = service.inputs_changed(world, game=game, data=tmp_path / "data")
    assert changed is not None
    assert sorted(changed) == ["game/a.txt", "game/b.txt"]


def test_a_world_of_another_epoch_is_not_rebuilt_to_be_checked(tmp_path: Path) -> None:
    """This generator would make a different world; the verdict says so and nothing is made."""
    export = FakeExport()
    world, game = _checked(tmp_path, export)
    assert world.record is not None
    older = replace(world, record=replace(world.record, algorithm=epoch.CURRENT + 1))
    found = service.check(older, game=game, data=tmp_path / "data", exporter=export)
    assert found.verdict is Verdict.OTHER_ALGORITHM
    assert found.reproduced is None
    assert len(export.calls) == 1


def test_a_world_without_a_record_or_a_bundle_cannot_be_checked(tmp_path: Path) -> None:
    """Both are errors that say why, not a pass."""
    export = FakeExport()
    world, game = _checked(tmp_path, export)
    with pytest.raises(service.CheckError, match="no reproducibility record"):
        _ = service.check(replace(world, record=None), game=game, data=tmp_path / "data")
    (library.folder(tmp_path / "data", world) / "manifest.json").unlink()
    with pytest.raises(service.CheckError, match="no longer the ones"):
        _ = service.check(world, game=game, data=tmp_path / "data", exporter=export)


def test_a_world_stays_valid_for_another_build_when_the_files_it_read_did_not_change(
    tmp_path: Path,
) -> None:
    """After a patch that touched nothing the world read, its kept mod goes in as it is."""
    export = FakeExport()
    world, game = _checked(tmp_path, export)
    patched = GameInstall(game.directory, None, "99999999")
    data = tmp_path / "data"
    assert service.compatible(world, game=game, data=data) is True
    assert service.compatible(world, game=patched, data=data) is True
    profile = Profile(tmp_path / "profile", "linux", has_mods=False)
    added = service.add_to_game(world, game=patched, data=data, profile=profile, exporter=export)
    assert added.installed is not None
    assert len(export.calls) == 1
    assert added.world == world


def test_a_world_is_made_again_for_another_build_when_a_file_it_read_changed(
    tmp_path: Path,
) -> None:
    """A changed game file makes it a world of its own; no list of files means nothing is known."""
    export = FakeExport()
    world, game = _checked(tmp_path, export)
    patched = GameInstall(game.directory, None, "99999999")
    data = tmp_path / "data"
    _ = (game.directory / "game/a.txt").write_text("a patch", encoding="utf-8")
    assert service.compatible(world, game=patched, data=data) is False
    profile = Profile(tmp_path / "profile", "linux", has_mods=False)
    added = service.add_to_game(world, game=patched, data=data, profile=profile, exporter=export)
    assert len(export.calls) == 2
    assert added.world.id != world.id
    (library.folder(data, world) / library.INPUTS).unlink()
    assert service.compatible(world, game=patched, data=data) is None
    assert service.compatible(world, game=game, data=data) is True
