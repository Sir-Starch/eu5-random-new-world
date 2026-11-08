"""The Tauri window's bridge: the controller spoken to as JSON lines, and the state it sends."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import base64
import io
import json
import queue
import re
import threading
import time
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, cast, final

import numpy as np
import pytest

from rnw import atlas
from rnw.app import library, preferences, service
from rnw.app.candidates import Candidate
from rnw.app.discovery import Environment, GameInstall, Profile
from rnw.app.worldcode import decode
from rnw.gui import text, view
from rnw.gui.atlas_loading import AtlasRequests
from rnw.gui.bridge import Bridge, BridgeError, serve
from rnw.gui.controller import NEW, Controller, Phase, Task
from rnw.png import COLOR_RGB, encode_png
from rnw.settings import RESOURCE_FIELDS
from tests.fakes import made_by_older_generator, synthetic_atlas

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import IO

    from rnw.app.library import World
    from rnw.app.service import Exporter
    from rnw.progress import Progress

DESKTOP = Path(__file__).resolve().parent.parent / "desktop" / "src"


def _bridge(tmp_path: Path, export: Exporter) -> Bridge:
    def generator(request: service.Request, progress: Progress | None = None) -> service.Result:
        return service.generate(request, progress, export)

    environment = Environment(system="linux", home=tmp_path / "home", variables={})
    controller = Controller(data=tmp_path / "data", environment=environment, generator=generator)
    (tmp_path / "game" / "game" / "in_game" / "map_data").mkdir(parents=True)
    controller.game = GameInstall(tmp_path / "game", None, "26043558")
    (tmp_path / "profile" / "mod").mkdir(parents=True)
    controller.profile = Profile(tmp_path / "profile", "linux", has_mods=True)
    return Bridge(controller)


def _made(bridge: Bridge, *, shown: bool = True) -> str:
    controller = bridge.controller
    controller.set_show_new_world(shown)
    controller.install = False
    assert bridge.call("set_seed", {"value": "42"}) is None
    assert bridge.call("start", {}) is None
    controller.wait(10)
    assert controller.phase is Phase.FINISHED, controller.message
    return controller.worlds[0].id


def test_hello_gives_the_strings_choices_and_a_state_that_is_json(
    tmp_path: Path, fake_export: Exporter
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    hello = cast("dict[str, dict[str, object]]", bridge.call("hello", {}))
    static, state = hello["static"], hello["state"]
    assert static["strings"] == text.sources()
    assert static["layers"] == list(atlas.LAYERS)
    assert static["budget"] == 31_200
    controls = cast("list[dict[str, object]]", static["controls"])
    mix = next(control for control in controls if control["key"] == "natives.peasant_peak_permille")
    assert mix["low"] == 30
    assert mix["high"] == 80
    assert mix["advanced"] is True
    assert state["selection"] == NEW
    new = cast("dict[str, object]", state["new"])
    assert new["choice"] == "continents"
    assert new["destination"] == "library"
    _ = json.dumps(hello)


def test_the_window_choice_is_kept_for_the_next_start(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Use the classic window: remembered in the preferences that rnw.gui.start reads."""
    bridge = _bridge(tmp_path, fake_export)
    _ = bridge.call("set_window", {"classic": True})
    assert preferences.load(bridge.controller.data).window == "classic"
    shown = cast("dict[str, object]", bridge.state()["preferences"])
    assert shown["window"] == "classic"
    _ = bridge.call("set_window", {"classic": False})
    assert preferences.load(bridge.controller.data).window == ""


def test_the_window_changes_the_new_world_as_the_qt_window_did(
    tmp_path: Path, fake_export: Exporter
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    controller = bridge.controller
    _ = bridge.call("set_choice", {"choice": "archipelago"})
    assert controller.preset == "archipelago"
    _ = bridge.call("set_value", {"key": "new_world.land_permille", "value": 25.0})
    assert controller.changes["new_world.land_permille"] == 250
    _ = bridge.call("set_position", {"key": "new_world.octaves", "position": 1000})
    assert controller.value("new_world.octaves") == 8
    assert bridge.call("set_seed", {"value": "not a seed"}) == text.text("bad_seed")
    _ = bridge.call("set_destination", {"kind": "world"})
    assert controller.install is False
    assert bridge.call("start", {}) == text.text("destination_missing")
    state = bridge.state()
    assert cast("dict[str, object]", state["new"])["problem"] == text.text("destination_missing")
    _ = bridge.call("set_destination", {"kind": "world", "path": str(tmp_path / "w.rnworld")})
    assert controller.world_file == tmp_path / "w.rnworld"
    _ = bridge.call("set_choice", {"choice": "chaos"})
    assert controller.mode == "chaos"
    seed, before = controller.seed, controller.code
    _ = bridge.call("randomize_settings", {})
    assert controller.seed == seed
    assert controller.code != before
    assert decode(controller.code).origin == "chaos"


def test_the_queue_is_kept_listed_and_managed_through_the_bridge(
    tmp_path: Path, fake_export: Exporter
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    controller = bridge.controller
    controller.install = False
    assert bridge.call("set_seed", {"value": "7"}) is None
    assert bridge.call("enqueue", {}) is None
    assert bridge.call("enqueue", {}) == text.text("queue_duplicate")
    assert bridge.call("set_seed", {"value": "8"}) is None
    assert bridge.call("enqueue", {}) is None
    new = cast("dict[str, object]", bridge.state()["new"])
    queue = cast("list[dict[str, object]]", new["queue"])
    assert [job["seed"] for job in queue] == ["7", "8"]
    assert not any(job["running"] for job in queue)
    assert new["preparable"] is True
    assert new["queue_problem"] is None
    _ = json.dumps(new)
    assert bridge.call("dequeue", {"code": queue[0]["code"]}) is None
    assert [job.code.seed for job in controller.queue] == [8]
    assert bridge.call("clear_queue", {}) is None
    assert controller.queue == []


def test_a_failed_queue_world_is_listed_with_its_error_and_the_next_one_is_made(
    tmp_path: Path, fake_export: Exporter
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    controller = bridge.controller
    controller.install = False
    original = controller.generator

    def generate(request: service.Request, progress: Progress | None = None) -> service.Result:
        if request.code.seed == 7:
            message = "the first world failed"
            raise OSError(message)
        return original(request, progress)

    controller.generator = generate
    for seed in ("7", "8"):
        assert bridge.call("set_seed", {"value": seed}) is None
        assert bridge.call("enqueue", {}) is None
    assert bridge.call("start_queue", {}) is None
    controller.wait(10)
    state = bridge.state()
    new = cast("dict[str, object]", state["new"])
    queue = cast("list[dict[str, object]]", new["queue"])
    assert [job["seed"] for job in queue] == ["7"]
    assert "the first world failed" in cast("str", queue[0]["error"])
    assert queue[0]["running"] is False
    assert new["queue_failed"] == 1
    # The run ended well: a world was made, and the status counts the one that stays queued.
    assert state["phase"] == "finished"
    assert "1 could not be made" in cast("str", state["status"])
    _ = json.dumps(state)
    assert bridge.call("dequeue", {"code": queue[0]["code"]}) is None
    new = cast("dict[str, object]", bridge.state()["new"])
    assert new["queue"] == []
    assert new["queue_failed"] == 0


def test_a_destination_that_was_not_chosen_stops_the_queue_as_it_stops_generate(
    tmp_path: Path, fake_export: Exporter
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    assert bridge.call("set_destination", {"kind": "mod"}) is None
    problem = text.text("destination_missing")
    assert bridge.call("enqueue", {}) == problem
    assert bridge.call("start", {}) == problem
    new = cast("dict[str, object]", bridge.state()["new"])
    assert new["queue_problem"] == problem
    assert bridge.controller.queue == []


def test_sketched_continents_stay_on_the_page_and_are_queued_one_by_one(
    tmp_path: Path, fake_export: Exporter
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    controller = bridge.controller
    controller.install = False
    picture = np.zeros((2, 2, 3), dtype=np.uint8)
    controller.candidates = [Candidate(seed, picture, 250) for seed in (5, 6)]
    controller.candidate_code = controller.world_code()
    controller.task, controller.phase = Task.CANDIDATES, Phase.FINISHED
    assert bridge.call("enqueue_candidate", {"index": 1}) is None
    sketches = cast("list[dict[str, object]]", bridge.state()["candidates"])
    assert [(item["seed"], item["queued"]) for item in sketches] == [("5", False), ("6", True)]
    assert bridge.call("enqueue_candidate", {"index": 1}) == text.text("queue_duplicate")
    # Another task after the sketching does not take the sketches away from the page.
    controller.task = Task.QUEUE
    assert len(cast("list[object]", bridge.state()["candidates"])) == 2


def test_the_tauri_bridge_sets_and_encodes_the_peasant_mix(
    tmp_path: Path, fake_export: Exporter
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    assert bridge.call("set_value", {"key": "natives.peasant_peak_permille", "value": 80.0}) is None
    assert bridge.controller.value("natives.peasant_peak_permille") == 800
    assert decode(bridge.controller.code).settings().natives.peasant_peak_permille == 800


def test_the_tauri_bridge_turns_the_reveal_on_and_it_is_not_an_advanced_control(
    tmp_path: Path, fake_export: Exporter
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    new = cast("dict[str, object]", bridge.state()["new"])
    values = cast("dict[str, dict[str, object]]", new["values"])
    assert values["new_world.reveal_at_start"]["shown"] == 0
    assert values["new_world.reveal_at_start"]["changed"] is False
    assert bridge.call("set_value", {"key": "new_world.reveal_at_start", "value": 1}) is None
    assert decode(bridge.controller.code).settings().new_world.reveal_at_start == 1
    new = cast("dict[str, object]", bridge.state()["new"])
    values = cast("dict[str, dict[str, object]]", new["values"])
    assert values["new_world.reveal_at_start"]["shown"] == 1
    assert values["new_world.reveal_at_start"]["changed"] is True
    rows = cast("list[dict[str, object]]", view.static(bridge.controller)["controls"])
    row = next(item for item in rows if item["key"] == "new_world.reveal_at_start")
    assert row["advanced"] is False


def test_a_made_world_is_listed_shown_and_answered_about(
    tmp_path: Path, fake_export: Exporter
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    world_id = _made(bridge)
    state = bridge.state()
    assert state["selection"] == world_id
    [entry] = cast("list[dict[str, object]]", state["library"])
    assert entry["id"] == world_id
    assert entry["placement"] == "kept"
    world = cast("dict[str, object]", state["world"])
    assert world["id"] == world_id
    assert world["revealed"] is True
    assert str(bridge.call("thumbnail", {"id": world_id})).startswith("data:image/png;base64,")
    assert bridge.call("rename", {"id": world_id, "name": "Vinland"}) is None
    assert bridge.controller.worlds[0].name == "Vinland"
    message = bridge.call(
        "annotate", {"id": world_id, "notes": "n", "user_tag": "t", "starred": True}
    )
    assert message == text.text("notes_saved")
    assert bridge.controller.worlds[0].starred


def test_the_viewer_is_told_why_a_world_of_another_epoch_has_no_versions(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """W3: the state carries the refusal, so the version buttons are off with its words, and the
    actions a call could still make refuse with the same words and change nothing."""
    bridge = _bridge(tmp_path, fake_export)
    world_id = _made(bridge)
    assert cast("dict[str, object]", bridge.state()["world"])["version_problem"] is None
    older = made_by_older_generator(bridge.controller.data, bridge.controller.worlds[0])
    bridge.controller.refresh_library()
    state = cast("dict[str, object]", bridge.state()["world"])
    problem = state["version_problem"]
    assert isinstance(problem, str)
    assert "1.1.0" in problem
    assert "would not be on the same land" in problem
    assert json.dumps(state)
    for part in ("peoples", "resources"):
        assert bridge.call("reroll", {"part": part, "keep_both": False}) == problem
    assert bridge.call("edit", {}) == problem
    assert bridge.controller.selection == older.id == world_id
    assert bridge.controller.worlds == [older]
    assert bridge.controller.phase is Phase.FINISHED


def test_the_atlas_reaches_the_viewer_whole(tmp_path: Path, fake_export: Exporter) -> None:
    """The runs unroll to the labels; each layer's colours and classes are the lens's."""
    bridge = _bridge(tmp_path, fake_export)
    world_id = _made(bridge)
    built = synthetic_atlas()
    document, labels = atlas.to_files(built)
    folder = library.folder(bridge.controller.data, bridge.controller.worlds[0])
    _ = (folder / atlas.JSON_FILE).write_bytes(document)
    _ = (folder / atlas.LABELS_FILE).write_bytes(labels)
    bundle = cast("dict[str, object]", bridge.call("atlas", {"id": world_id}))
    assert bundle["cells"] == built.cells
    runs = np.frombuffer(base64.b64decode(str(bundle["labels"])), dtype="<u4").reshape(-1, 2)
    unrolled = np.repeat(runs[:, 0].astype(np.int64), runs[:, 1].astype(np.int64))
    assert np.array_equal(unrolled.reshape(built.size), built.labels)
    layers = cast("dict[str, dict[str, object]]", bundle["layers"])
    assert set(layers) == set(atlas.LAYERS)
    for layer, sent in layers.items():
        lens = atlas.lens(built, layer, view.words_for(bridge.controller, built))
        colours = np.frombuffer(base64.b64decode(str(sent["colours"])), dtype=np.uint8)
        classes = np.frombuffer(base64.b64decode(str(sent["classes"])), dtype="<i4")
        assert np.array_equal(colours.reshape(-1, 3), lens.colours)
        assert np.array_equal(classes, lens.classes)
        assert len(cast("list[object]", sent["legend"])) == len(lens.legend)
    _ = json.dumps(bundle)


def test_the_window_saves_the_map_it_drew(tmp_path: Path, fake_export: Exporter) -> None:
    """A map picture is drawn by the window, as shown; the bridge only writes it, as a PNG."""
    bridge = _bridge(tmp_path, fake_export)
    drawn = encode_png(
        np.zeros((2, 3, 3), dtype=np.uint8), color_type=COLOR_RGB, compression="zlib"
    )
    output = tmp_path / "map.png"
    data = "data:image/png;base64," + base64.b64encode(drawn).decode("ascii")
    message = bridge.call("save_png", {"path": str(output), "data": data})
    assert message == text.text("picture_saved", path=str(output))
    assert output.read_bytes() == drawn
    for wrong in (
        "data:image/png;base64,bm90IGEgcGljdHVyZQ==",
        "data:text/plain;base64,AAAA",
        "%%%",
    ):
        with pytest.raises(BridgeError):
            _ = bridge.call("save_png", {"path": str(tmp_path / "no.png"), "data": wrong})
    assert not (tmp_path / "no.png").exists()


def test_a_covered_world_has_no_atlas_for_the_viewer(tmp_path: Path, fake_export: Exporter) -> None:
    bridge = _bridge(tmp_path, fake_export)
    world_id = _made(bridge, shown=False)
    built = synthetic_atlas()
    folder = library.folder(bridge.controller.data, bridge.controller.worlds[0])
    document, labels = atlas.to_files(built)
    _ = (folder / atlas.JSON_FILE).write_bytes(document)
    _ = (folder / atlas.LABELS_FILE).write_bytes(labels)
    assert bridge.call("atlas", {"id": world_id}) is None
    _ = bridge.call("reveal", {"id": world_id})
    assert bridge.call("atlas", {"id": world_id}) is not None


def test_the_protocol_answers_each_line_and_sends_states(
    tmp_path: Path, fake_export: Exporter
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    requests = "\n".join(
        [
            json.dumps({"id": 1, "method": "set_seed", "params": {"value": "7"}}),
            json.dumps({"id": 2, "method": "nonsense"}),
            "not json",
            json.dumps({"id": 3, "method": "set_value", "params": {"key": "x", "value": 1}}),
            "",
        ]
    )
    outgoing = io.StringIO()
    serve(bridge, io.StringIO(requests), outgoing)
    messages = [json.loads(line) for line in outgoing.getvalue().splitlines()]
    answers = {message.get("id"): message for message in messages if "event" not in message}
    assert answers[1] == {"id": 1, "result": None}
    assert "Unknown method" in answers[2]["error"]
    assert answers[None]["error"] == "The request is not JSON"
    assert "Unknown setting" in answers[3]["error"]
    states = [message["data"] for message in messages if message.get("event") == "state"]
    assert states
    assert states[-1]["new"]["seed"] == "7"


def test_every_string_the_tauri_window_asks_for_exists() -> None:
    """The window's text comes from the bridge; a key it names must be in the table."""
    keys: set[str] = set()
    for path in DESKTOP.rglob("*"):
        if path.suffix in {".svelte", ".ts"}:
            keys |= set(re.findall(r'\bt\(\s*"([a-z_.0-9]+)"', path.read_text(encoding="utf-8")))
    assert keys
    assert sorted(keys - text.sources().keys()) == []


def test_the_self_test_passes(capsys: pytest.CaptureFixture[str]) -> None:
    from rnw.gui.bridge import self_test  # noqa: PLC0415 - the entry point under test

    assert self_test() == 0
    assert "bridge, native kernels and world codes work" in capsys.readouterr().out


def test_resource_controls_reach_the_tauri_window_and_survive_its_actions(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """The Tauri bridge exposes every RGO, stores shown multiples, and resets them."""
    bridge = _bridge(tmp_path, fake_export)
    hello = cast("dict[str, dict[str, object]]", bridge.call("hello", {}))
    controls = cast("list[dict[str, object]]", hello["static"]["controls"])
    members = [row for row in controls if str(row["key"]).startswith("resources.")]
    assert {row["key"] for row in members} == {f"resources.{name}" for name in RESOURCE_FIELDS}
    assert all(row["group"] == "resources" and row["advanced"] for row in members)
    _ = bridge.call("set_value", {"key": "resources.maize", "value": 0.0})
    _ = bridge.call("set_value", {"key": "resources.iron", "value": 3.0})
    settings = decode(bridge.controller.code).settings()
    assert (settings.resources.maize, settings.resources.iron) == (0, 3000)
    _ = bridge.call("reset_value", {"key": "resources.maize"})
    assert bridge.controller.value("resources.maize") == 1000
    assert bridge.controller.value("resources.iron") == 3000


# -- W2: the version path through the bridge ---------------------------------------------------


def test_the_state_can_be_drawn_whatever_the_thread_does_to_the_selected_world(
    tmp_path: Path, fake_export: Exporter
) -> None:
    """Every kind of work, in every phase, on the selected world or the new-world page: a
    string missing for one task (``task.reroll`` was) is a ``KeyError`` that stops the bridge."""
    bridge = _bridge(tmp_path, fake_export)
    world = _made(bridge)
    controller = bridge.controller
    controller.select(world)
    failures: list[str] = []
    for task in Task:
        for phase in Phase:
            for target in (world, NEW):
                controller.task, controller.phase, controller.task_target = task, phase, target
                controller.message = "Technical detail"
                try:
                    _ = json.dumps(bridge.state())
                except Exception as error:  # noqa: BLE001 - every failure is listed together
                    failures.append(f"{task.value}/{phase.value}/{target}: {error!r}")
    assert failures == []


def test_every_kind_of_work_that_shows_a_line_for_a_world_has_its_words() -> None:
    """The line under a world names the work; the classic window shows the same words."""
    named = {task for task in Task if f"task.{task.value}" in text.sources()}
    shown_for_a_world = {
        Task.ADD,
        Task.REMOVE,
        Task.DELETE,
        Task.CHECK,
        Task.REROLL,
        Task.SEND,
        Task.COPY,
        Task.UNDO,
    }
    assert shown_for_a_world <= named


class _Lines:
    """Standard input as the bridge reads it: lines that arrive while it serves, then its end."""

    def __init__(self) -> None:
        self._lines: queue.Queue[str | None] = queue.Queue()

    def __iter__(self) -> Iterator[str]:
        return iter(self._lines.get, None)

    def send(self, method: str, **params: object) -> None:
        number = next(_NUMBERS)
        self._lines.put(json.dumps({"id": number, "method": method, "params": params}) + "\n")

    def close(self) -> None:
        self._lines.put(None)


_NUMBERS = iter(range(1, 10_000))


@final
class _Outgoing:
    """What the bridge writes; ``states`` are the states it sent, as the window would read them."""

    def __init__(self) -> None:
        self._text: list[str] = []
        self._guard = threading.Lock()

    def write(self, chunk: str, /) -> int:
        with self._guard:
            self._text.append(chunk)
        return len(chunk)

    def flush(self) -> None:
        pass

    def messages(self) -> list[dict[str, object]]:
        with self._guard:
            lines = "".join(self._text).splitlines()
        return [json.loads(line) for line in lines]

    def states(self) -> list[dict[str, object]]:
        with self._guard:
            lines = "".join(self._text).splitlines()
        messages = [json.loads(line) for line in lines]
        return [message["data"] for message in messages if message.get("event") == "state"]


def _until(condition: Callable[[], bool], what: str, seconds: float = 20.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition():
        assert time.monotonic() < deadline, f"timed out: {what}"
        time.sleep(0.02)


def _served(bridge: Bridge) -> tuple[_Lines, _Outgoing, threading.Thread, list[BaseException]]:
    lines, outgoing = _Lines(), _Outgoing()
    ended: list[BaseException] = []

    def run() -> None:
        try:
            serve(
                bridge,
                cast("IO[str]", cast("object", lines)),
                cast("IO[str]", cast("object", outgoing)),
            )
        except BaseException as error:  # noqa: BLE001 - what ended the bridge is the test's result
            ended.append(error)

    thread = threading.Thread(target=run, name="served-bridge", daemon=True)
    thread.start()
    return lines, outgoing, thread, ended


@pytest.mark.parametrize("keep_both", [False, True])
def test_a_version_is_made_while_the_bridge_goes_on_serving_and_sending_states(
    tmp_path: Path,
    fake_export: Exporter,
    keep_both: bool,  # noqa: FBT001 - the parameter
) -> None:
    """W2: *Create a version* stopped "the generator" because the state drawn while it ran
    raised, which ended the bridge's loop and with it the process."""
    release = threading.Event()
    working = threading.Event()

    def generator(request: service.Request, progress: Progress | None = None) -> service.Result:
        if request.part:
            working.set()
            assert release.wait(30)
        return service.generate(request, progress, fake_export)

    bridge = _bridge(tmp_path, fake_export)
    bridge.controller.generator = generator
    world = _made(bridge, shown=True)
    lines, outgoing, thread, ended = _served(bridge)
    lines.send("select", id=world)
    lines.send("reroll", part="peoples", keep_both=keep_both)
    _until(working.is_set, "the version started")

    def line_of_the_version() -> str:
        for state in outgoing.states():
            task = cast(
                "dict[str, object] | None", cast("dict[str, object]", state["world"])["task"]
            )
            if task is not None and task["running"]:
                return cast("str", task["line"])
        return ""

    _until(lambda: bool(line_of_the_version()), "a state that shows the version being made")
    assert text.text("task.reroll") in line_of_the_version()
    assert thread.is_alive()
    assert ended == []
    release.set()
    _until(lambda: bridge.controller.phase is Phase.FINISHED, "the version finished")
    _until(lambda: len(bridge.controller.worlds) == 2, "the version is in the library")
    lines.close()
    thread.join(30)
    assert not thread.is_alive()
    assert ended == []


def test_a_state_that_cannot_be_drawn_is_logged_and_the_next_one_is_sent(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure of the drawing must not end the process that is making a world: it goes to the
    log and to the last-error file for a report, and the bridge tries again."""
    bridge = _bridge(tmp_path, fake_export)
    real = view.state
    broken = {"calls": 0}

    def state(controller: Controller, choices: view.Choices) -> dict[str, object]:
        broken["calls"] += 1
        if broken["calls"] <= 3:
            message = "the state could not be drawn"
            raise KeyError(message)
        return real(controller, choices)

    monkeypatch.setattr(view, "state", state)
    lines, outgoing, thread, ended = _served(bridge)
    _until(lambda: bool(outgoing.states()), "a state after the failures")
    assert thread.is_alive()
    assert ended == []
    lines.close()
    thread.join(30)
    assert not thread.is_alive()
    log = (tmp_path / "data" / "generator.log").read_text(encoding="utf-8")
    assert "the state could not be drawn" in log
    assert "Traceback" in log
    assert log.count("the window's state could not be drawn") == 1, "one entry per distinct error"
    assert "the state could not be drawn" in (tmp_path / "data" / "last-error.log").read_text(
        encoding="utf-8"
    )


def test_state_and_comparison_listing_never_decode_library_atlases(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    _ = _made(bridge)
    original = bridge.controller.worlds[0]
    document, labels = atlas.to_files(synthetic_atlas())
    worlds = [replace(original, id=f"test{i:06d}") for i in range(6)]
    for world in worlds:
        folder = library.folder(bridge.controller.data, world)
        folder.mkdir(parents=True)
        _ = (folder / atlas.JSON_FILE).write_bytes(document)
        _ = (folder / atlas.LABELS_FILE).write_bytes(labels)
    bridge.controller.worlds = worlds

    def forbidden(*_args: object) -> None:
        pytest.fail("A state refresh must not load any atlas")

    monkeypatch.setattr(library, "atlas", forbidden)
    for world in worlds * 2:
        bridge.controller.select(world.id)
        state = cast("dict[str, object]", bridge.state()["world"])
        assert state["atlas"] is True
        assert state["compare"] is True
        assert state["atlas_revision"]
    assert len(view.compare_list(bridge.controller)) == len(worlds)


def test_switching_worlds_cancels_obsolete_atlases_while_the_bridge_keeps_serving(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A blocked map must not block selection, cancel, state ticks or the last chosen map."""
    bridge = _bridge(tmp_path, fake_export)
    _ = _made(bridge)
    original = bridge.controller.worlds[0]
    worlds = [replace(original, id=f"test{i:06d}") for i in range(3)]
    bridge.controller.worlds = worlds
    started, release = threading.Event(), threading.Event()
    loaded: list[str] = []

    def load(
        _controller: Controller, world: World, checkpoint: Callable[[], None]
    ) -> dict[str, object]:
        loaded.append(world.id)
        if world is worlds[0]:
            started.set()
            assert release.wait(5)
        checkpoint()
        return {"id": world.id}

    monkeypatch.setattr(view, "atlas_bundle", load)
    lines, outgoing, thread, ended = _served(bridge)
    try:
        lines.send("select", id=worlds[0].id)
        lines.send("atlas", id=worlds[0].id, request_key="main:first")
        assert started.wait(5)
        lines.send("cancel_atlas", request_key="main:first")
        lines.send("select", id=worlds[1].id)
        lines.send("atlas", id=worlds[1].id, request_key="main:middle")
        lines.send("cancel_atlas", request_key="main:middle")
        lines.send("select", id=worlds[2].id)
        lines.send("atlas", id=worlds[2].id, request_key="main:last")
        lines.send("set_seed", value="123")
        _until(
            lambda: any(s["selection"] == worlds[2].id for s in outgoing.states()),
            "selection delivered before the blocked atlas finishes",
            seconds=2,
        )
        assert bridge.controller.seed == 123
        release.set()
        _until(
            lambda: any(m.get("result") == {"id": worlds[2].id} for m in outgoing.messages()),
            "last map delivered",
        )
        assert loaded == [worlds[0].id, worlds[2].id]
        # The prepared bundle is reused on returning to the same map.
        lines.send("atlas", id=worlds[2].id, request_key="main:again")
        _until(
            lambda: sum(m.get("result") == {"id": worlds[2].id} for m in outgoing.messages()) == 2,
            "cached map delivered",
        )
        assert loaded == [worlds[0].id, worlds[2].id]
        ids = [m["id"] for m in outgoing.messages() if "id" in m]
        assert len(ids) == len(set(ids)), "Every cancelled/completed RPC has exactly one reply"
    finally:
        release.set()
        lines.close()
        thread.join(5)
    assert not thread.is_alive()
    assert not ended


def test_background_atlas_failure_can_retry_and_file_changes_expire_prepared_bundles(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    _ = _made(bridge)
    world = bridge.controller.worlds[0]
    calls = 0

    def load(
        _controller: Controller, _world: World, checkpoint: Callable[[], None]
    ) -> dict[str, object]:
        nonlocal calls
        calls += 1
        checkpoint()
        if calls == 1:
            message = "cannot read the atlas"
            raise OSError(message)
        return {"id": world.id}

    monkeypatch.setattr(view, "atlas_bundle", load)
    worker = AtlasRequests(bridge.controller)

    def ask(number: int) -> dict[str, object]:
        replies: list[dict[str, object]] = []
        worker.submit(number, "viewer", world)

        def delivered() -> bool:
            replies.extend(worker.drain())
            return bool(replies)

        _until(delivered, "atlas response")
        assert len(replies) == 1
        return replies[0]

    try:
        assert "error" in ask(1)
        assert ask(2)["result"] == {"id": world.id}
        assert ask(3)["result"] == {"id": world.id}
        assert calls == 2
        folder = library.folder(bridge.controller.data, world)
        document, labels = atlas.to_files(synthetic_atlas())
        _ = (folder / atlas.JSON_FILE).write_bytes(document)
        _ = (folder / atlas.LABELS_FILE).write_bytes(labels)
        assert ask(4)["result"] == {"id": world.id}
        assert calls == 3
        # A game change also changes the localized names even when world files stay the same.
        game = bridge.controller.game
        assert game is not None
        bridge.controller.game = replace(game, build_id="new-build")
        assert ask(5)["result"] == {"id": world.id}
        assert calls == 4
    finally:
        worker.close()
        worker.thread.join(5)
    assert not worker.thread.is_alive()


def test_a_game_change_during_preparation_does_not_poison_the_old_cache_key(
    tmp_path: Path, fake_export: Exporter, monkeypatch: pytest.MonkeyPatch
) -> None:
    bridge = _bridge(tmp_path, fake_export)
    _ = _made(bridge)
    c = bridge.controller
    world, game = c.worlds[0], c.game
    assert game is not None
    started, release = threading.Event(), threading.Event()
    calls = 0

    def load(
        controller: Controller, _world: World, checkpoint: Callable[[], None]
    ) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            started.set()
            assert release.wait(5)
        checkpoint()
        assert controller.game is not None
        return {"build": controller.game.build_id}

    monkeypatch.setattr(view, "atlas_bundle", load)
    worker = AtlasRequests(c)
    replies: list[dict[str, object]] = []

    def delivered() -> bool:
        replies.extend(worker.drain())
        return bool(replies)

    try:
        worker.submit(1, "viewer", world)
        assert started.wait(5)
        c.game = replace(game, build_id="other")
        release.set()
        _until(delivered, "obsolete response")
        assert replies.pop()["result"] is None
        # Revisiting the original game must prepare its own words, not the mixed old request.
        c.game = game
        worker.submit(2, "viewer", world)
        _until(delivered, "original game response")
        assert replies.pop()["result"] == {"build": game.build_id}
        assert calls == 2
    finally:
        release.set()
        worker.close()
        worker.thread.join(5)
