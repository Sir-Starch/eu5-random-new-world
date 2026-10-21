"""Making worlds for a player: each a mod of its own, recorded, added and removed again."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from rnw.app import install, library, service
from rnw.app.discovery import GameInstall, Profile
from rnw.app.library import Placement
from rnw.app.service import Request, generate
from rnw.app.worldcode import encode, new_code
from rnw.pictures import TERRA_INCOGNITA
from rnw.png import COLOR_RGB, encode_png
from rnw.progress import STAGES, Cancelled, Progress

if TYPE_CHECKING:
    from pathlib import Path


def _png(color: tuple[int, int, int]) -> bytes:
    image = np.zeros((32, 64, 3), dtype=np.uint8)
    image[:] = (25, 45, 90)
    image[:, :20] = color
    return encode_png(image, color_type=COLOR_RGB, compression="zlib")


class FakeExport:
    """Writes a tiny bundle like the export does and reports through ``progress``."""

    def __init__(self, *, fail: Exception | None = None, cancel: bool = False) -> None:
        self.fail: Exception | None = fail
        self.cancel: bool = cancel
        self.calls: list[tuple[int, str | None]] = []

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
    ) -> dict[str, object]:
        del game_dir, settings, settings_file, accept_build, replace, check_memory
        self.calls.append((seed, world_code))
        if progress is not None and self.cancel:
            progress.cancel()
            progress.checkpoint()
        if self.fail is not None:
            raise self.fail
        mod = output / output.name
        (mod / ".metadata").mkdir(parents=True, exist_ok=True)
        _ = (mod / ".metadata/metadata.json").write_text('{"name": "World"}', encoding="utf-8")
        (mod / "in_game/map_data").mkdir(parents=True, exist_ok=True)
        _ = (mod / "seed.txt").write_text(str(seed), encoding="utf-8")
        _ = (output / "preview.png").write_bytes(_png((96, 160, 72)))
        _ = (output / "preview_hidden.png").write_bytes(_png(TERRA_INCOGNITA))
        return {"status": "NOT GAME VALIDATED", "canvas": {}, "generated": {}, "invariants": {}}


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


def test_the_mod_list_picture_shows_the_new_world_only_when_asked(tmp_path: Path) -> None:
    """With the player's choice the mod gets the full picture; without it, the export's own."""
    request = _request(tmp_path)
    revealed = Request(
        game=request.game,
        code=request.code,
        data=request.data,
        profile=request.profile,
        reveal_thumbnail=True,
    )
    result = generate(revealed, Progress(), FakeExport())
    assert result.installed is not None
    assert (result.installed / library.THUMBNAIL).is_file()
    assert encode(request.code) == result.world.code


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
