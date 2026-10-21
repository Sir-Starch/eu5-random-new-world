"""Generating for a player: the flow, the history and the errors, with a stand-in export."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from rnw.app import history, install, service
from rnw.app.discovery import GameInstall, Profile
from rnw.app.service import Request, generate
from rnw.app.worldcode import encode, new_code
from rnw.progress import STAGES, Cancelled, Progress

if TYPE_CHECKING:
    from pathlib import Path


class FakeExport:
    """Writes a tiny bundle like the export does and reports through ``progress``."""

    def __init__(self, *, fail: Exception | None = None, cancel: bool = False) -> None:
        self.fail: Exception | None = fail
        self.cancel: bool = cancel
        self.calls: list[tuple[int, str | None, bool]] = []

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
    ) -> dict[str, object]:
        del game_dir, settings, settings_file
        self.calls.append((seed, accept_build, replace and check_memory))
        if progress is not None and self.cancel:
            progress.cancel()
            progress.checkpoint()
        if self.fail is not None:
            raise self.fail
        mod = output / "rnw_exp_new_world"
        (mod / ".metadata").mkdir(parents=True)
        _ = (mod / ".metadata/metadata.json").write_text("{}", encoding="utf-8")
        _ = (mod / "seed.txt").write_text(str(seed), encoding="utf-8")
        return {"status": "NOT GAME VALIDATED", "canvas": {}, "generated": {}, "invariants": {}}


def _request(tmp_path: Path, *, with_profile: bool = True, install: bool = True) -> Request:
    profile = tmp_path / "profile"
    profile.mkdir(exist_ok=True)
    return Request(
        game=GameInstall(tmp_path / "game", None, "26043558"),
        code=new_code("continents", 4242),
        data=tmp_path / "data",
        profile=Profile(profile, "linux", has_mods=False) if with_profile else None,
        install=install,
    )


def test_generate_installs_and_records(tmp_path: Path) -> None:
    """The bundle is made in the application's folder, installed into the profile, recorded."""
    request = _request(tmp_path)
    export = FakeExport()
    result = generate(request, Progress(), export)
    assert export.calls == [(4242, None, True)]
    installed = tmp_path / "profile" / "mod" / "rnw_exp_new_world"
    assert result.installed == installed
    assert (installed / "seed.txt").read_text(encoding="utf-8") == "4242"
    assert result.bundle == tmp_path / "data" / "generated" / "rnw_exp_new_world"
    assert result.code == encode(request.code)
    assert result.summary["status"] == "NOT GAME VALIDATED"
    entries = history.load(request.data)
    assert [(entry.outcome, entry.game_build) for entry in entries] == [("installed", "26043558")]
    assert entries[0].code == result.code


def test_generate_without_installing_keeps_the_profile_untouched(tmp_path: Path) -> None:
    """Install off: the profile gets nothing and the outcome is 'generated'."""
    request = _request(tmp_path, install=False)
    result = generate(request, None, FakeExport())
    assert result.installed is None
    assert not (tmp_path / "profile" / "mod").exists()
    assert history.load(request.data)[0].outcome == "generated"


def test_a_missing_profile_is_refused_before_any_work(tmp_path: Path) -> None:
    """Asking to install without a profile fails at once and is recorded as failed."""
    request = _request(tmp_path, with_profile=False)
    export = FakeExport()
    with pytest.raises(install.InstallError, match="no profile"):
        _ = generate(request, None, export)
    assert export.calls == []
    assert history.load(request.data)[0].outcome == "failed"


def test_failures_and_cancels_are_recorded_and_raised(tmp_path: Path) -> None:
    """An export error is raised after being written to the history; so is a cancel."""
    request = _request(tmp_path)
    with pytest.raises(ValueError, match="boom"):
        _ = generate(request, None, FakeExport(fail=ValueError("boom")))
    failed = history.load(request.data)[0]
    assert failed.outcome == "failed"
    assert "ValueError: boom" in failed.note
    with pytest.raises(Cancelled):
        _ = generate(request, Progress(), FakeExport(cancel=True))
    assert [entry.outcome for entry in history.load(request.data)] == ["cancelled", "failed"]
    assert not (tmp_path / "profile" / "mod").exists()


def test_install_waits_while_the_game_holds_the_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refused moves are retried until the game lets go; the window shows the instruction."""
    monkeypatch.setattr(service, "WAIT_PAUSE", 0.0)
    real = install.put_in_place
    refusals = [2]

    def held(incoming: Path) -> Path:
        if refusals[0] > 0:
            refusals[0] -= 1
            message = "The game is using rnw_exp_new_world"
            raise install.WorldInUseError(message)
        return real(incoming)

    monkeypatch.setattr(install, "put_in_place", held)
    labels: list[str] = []
    result = generate(
        _request(tmp_path), Progress(lambda update: labels.append(update.label)), FakeExport()
    )
    assert result.installed == tmp_path / "profile" / "mod" / "rnw_exp_new_world"
    assert STAGES["waiting for the game"].label in labels
    assert [entry.outcome for entry in history.load(tmp_path / "data")] == ["installed"]


def test_a_cancel_while_waiting_leaves_the_installed_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancel stops the wait, removes the staged copy and is recorded; nothing is half done."""
    monkeypatch.setattr(service, "WAIT_PAUSE", 0.0)
    progress = Progress()

    def held(incoming: Path) -> Path:
        progress.cancel()
        message = f"The game is using {incoming.name}"
        raise install.WorldInUseError(message)

    monkeypatch.setattr(install, "put_in_place", held)
    with pytest.raises(Cancelled):
        _ = generate(_request(tmp_path), progress, FakeExport())
    assert not (tmp_path / "profile" / "mod" / install.WORK).exists()
    assert [entry.outcome for entry in history.load(tmp_path / "data")] == ["cancelled"]


def test_without_a_progress_a_held_world_is_an_error_at_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The command line has no Cancel button, so it does not wait."""

    def held(incoming: Path) -> Path:
        message = f"The game is using {incoming.name}"
        raise install.WorldInUseError(message)

    monkeypatch.setattr(install, "put_in_place", held)
    with pytest.raises(install.WorldInUseError):
        _ = generate(_request(tmp_path), None, FakeExport())
    assert not (tmp_path / "profile" / "mod" / install.WORK).exists()
