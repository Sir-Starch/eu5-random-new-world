"""The Tauri window's bridge: the controller spoken to as JSON lines, and the state it sends."""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from rnw import atlas
from rnw.app import library, preferences, service
from rnw.app.discovery import Environment, GameInstall, Profile
from rnw.app.worldcode import decode
from rnw.gui import text, view
from rnw.gui.bridge import Bridge, BridgeError, serve
from rnw.gui.controller import NEW, Controller, Phase
from rnw.png import COLOR_RGB, encode_png
from rnw.settings import RESOURCE_FIELDS
from tests.fakes import synthetic_atlas

if TYPE_CHECKING:
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
