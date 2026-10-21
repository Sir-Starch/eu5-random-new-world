"""The window's controller: choices, validation and the generation lifecycle, no display."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from rnw.app import discovery, history
from rnw.app.discovery import Environment, GameInstall
from rnw.app.service import Request, Result
from rnw.app.worldcode import WorldCode, encode, new_code
from rnw.gui.controller import SEED_MAX, Controller, Generator, Phase

if TYPE_CHECKING:
    from pathlib import Path

    from rnw.progress import Progress


def _game(root: Path) -> GameInstall:
    (root / "game" / "in_game" / "map_data").mkdir(parents=True, exist_ok=True)
    return GameInstall(root, None, "26043558")


def _result(request: Request) -> Result:
    return Result(encode(request.code), request.data, None, 1.5, {"status": "x"})


def _instant(request: Request, progress: Progress | None = None) -> Result:
    del progress
    return _result(request)


def _controller(tmp_path: Path, generator: Generator) -> Controller:
    environment = Environment(system="linux", home=tmp_path / "home", variables={})
    controller = Controller(data=tmp_path / "data", environment=environment, generator=generator)
    controller.game = _game(tmp_path / "game")
    controller.install = False
    return controller


def test_choices_are_validated_and_remembered(tmp_path: Path) -> None:
    """Seeds, codes, presets, game and profile folders are checked; bad input changes nothing."""
    controller = _controller(tmp_path, _instant)
    changes: list[int] = []
    controller.subscribe(lambda: changes.append(1))
    assert controller.set_seed("12345") is None
    assert controller.seed == 12345
    assert controller.set_seed("-1") is not None
    assert controller.set_seed("x") is not None
    assert controller.set_seed(str(SEED_MAX + 1)) is not None
    assert controller.seed == 12345
    controller.set_preset("archipelago")
    controller.set_preset("flat")
    assert controller.preset == "archipelago"
    pasted = encode(new_code("continents", 777))
    assert controller.set_seed(f" {pasted.lower()} ") is None
    assert (controller.preset, controller.seed) == ("continents", 777)
    assert controller.use_code("RNW1-00000") is not None
    other = encode(WorldCode("continents", 5, "0.1.0"))
    assert controller.use_code(other) is None
    assert "0.1.0" in controller.notice
    controller.randomize()
    assert controller.notice == ""
    assert controller.code.startswith("RNW1-")
    assert controller.choose_game(tmp_path / "nowhere") is not None
    assert controller.choose_profile(tmp_path / "nowhere") is not None
    folder = tmp_path / "profile"
    folder.mkdir()
    assert controller.choose_profile(folder) is None
    assert controller.profile is not None
    assert controller.profile.directory == folder
    assert changes


def test_a_generation_reports_progress_and_finishes(tmp_path: Path) -> None:
    """The thread runs the generator, the state follows its stages, and the end is announced."""
    seen: list[tuple[Phase, float, tuple[str, ...]]] = []

    def generator(request: Request, progress: Progress | None = None) -> Result:
        assert progress is not None
        progress.begin("generate world")
        progress.begin("relief")
        progress.finish("relief")
        progress.finish("generate world")
        return _result(request)

    controller = _controller(tmp_path, generator)
    controller.subscribe(
        lambda: seen.append((controller.phase, controller.fraction, controller.running))
    )
    assert controller.problem() is None
    assert controller.start() is None
    controller.wait(10)
    assert controller.phase is Phase.FINISHED
    assert controller.fraction == 1.0
    assert controller.result is not None
    assert any(
        running == ("Raising mountains and valleys", "Generating continents, seas and relief")
        or "Generating continents, seas and relief" in running
        for _, _, running in seen
    )
    rows = dict(controller.stage_rows())
    assert rows["Generating continents, seas and relief"] == "done"
    assert rows["Writing the mod"] == "waiting"
    assert "Raising mountains and valleys" not in rows


def test_cancel_stops_the_generation_and_says_so(tmp_path: Path) -> None:
    """Cancel switches to 'cancelling' at once and to 'cancelled' when the thread has stopped."""
    started = threading.Event()

    def generator(request: Request, progress: Progress | None = None) -> Result:
        del request
        assert progress is not None
        started.set()
        while True:
            progress.checkpoint()
            _ = threading.Event().wait(0.005)

    controller = _controller(tmp_path, generator)
    assert controller.start() is None
    assert started.wait(10)
    assert controller.problem() is not None
    controller.cancel()
    assert controller.phase in {Phase.CANCELLING, Phase.CANCELLED}
    controller.wait(10)
    assert controller.phase is Phase.CANCELLED
    assert controller.running == ()
    assert controller.problem() is None


def test_a_failure_is_explained_and_logged(tmp_path: Path) -> None:
    """The error text reaches the window and the traceback goes to a file in the data folder."""

    def generator(request: Request, progress: Progress | None = None) -> Result:
        del request, progress
        message = "the disk is full"
        raise OSError(message)

    controller = _controller(tmp_path, generator)
    assert controller.start() is None
    controller.wait(10)
    assert controller.phase is Phase.FAILED
    assert controller.message == "the disk is full"
    log = (tmp_path / "data" / "last-error.log").read_text(encoding="utf-8")
    assert "OSError: the disk is full" in log


def test_generate_needs_a_game_and_a_profile_to_install_into(tmp_path: Path) -> None:
    """The reasons Generate cannot start are the player's to fix and are worded for them."""
    controller = _controller(tmp_path, _instant)
    controller.game = None
    assert controller.problem() == "Choose the game folder first."
    assert controller.start() == "Choose the game folder first."
    controller.game = _game(tmp_path / "game")
    controller.install = True
    controller.profile = None
    assert controller.problem() is not None
    assert "profile" in (controller.problem() or "")
    controller.install = False
    assert controller.problem() is None


def test_discover_takes_the_first_game_and_profile(tmp_path: Path) -> None:
    """With nothing installed discovery leaves the choices empty instead of failing."""
    controller = _controller(tmp_path, _instant)
    controller.discover()
    assert controller.games == []
    assert controller.game is None
    assert controller.profile is None
    assert discovery.is_game(tmp_path / "game")
    assert history.load(tmp_path / "data") == []
    assert controller.history() == []
