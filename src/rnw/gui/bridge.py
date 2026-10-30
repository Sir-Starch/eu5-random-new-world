"""The generator behind the Tauri window: the controller, spoken to as JSON lines (ADR 0011).

``python -m rnw.gui.bridge`` reads requests from standard input, one JSON object a line:
``{"id": 7, "method": "set_seed", "params": {"value": "42"}}``, and answers on standard output
with ``{"id": 7, "result": ...}`` or ``{"id": 7, "error": "..."}``. Whenever the controller
changes, it also sends ``{"event": "state", "data": ...}`` (``rnw.gui.view.state``), at most a few
times a second and only when something the window draws is different. Everything that is not the
protocol (a library's print, a native kernel's message) goes to standard error, so it cannot break
a line the window reads.

The window asks; the bridge does what the Qt window's buttons did, by calling the same controller
methods, and returns the problem the controller reports (in the window's language) or None. All
calls run on one thread, as the Qt window's did; the controller's own thread does the long work.
Closing standard input cancels running work, waits for it and ends the process.

``--self-test`` answers ``hello`` for a temporary library, checks the native kernels and the world
codes, and exits with 0: the packaging jobs run it on the built folder.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO, TYPE_CHECKING, Final, cast

from rnw import __version__, _native
from rnw.app import logs, paths, random_types
from rnw.app.worldcode import decode, encode, new_code
from rnw.gui import text as window
from rnw.gui import view
from rnw.gui.controller import NEW, Controller, Phase, Task

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rnw.app.library import World

# The window redraws from a state at most this often; progress comes in smaller steps.
STATE_INTERVAL: Final[float] = 0.12
# A running generation's countdown is sent this often even when nothing else changed.
TICK: Final[float] = 1.0
# As the Qt window: notice worlds added by another copy of the generator, while idle.
POLL: Final[float] = 2.0
CLOSE_WAIT: Final[float] = 15.0
SELF_TEST: Final[str] = "--self-test"
DESCRIPTION: Final[str] = "The generator behind the Tauri window, spoken to as JSON lines."
PNG_URL: Final[str] = "data:image/png;base64,"
PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
NOT_PNG: Final[str] = "The picture is not a PNG data URL"

Params = dict[str, object]


class BridgeError(ValueError):
    """A request the bridge cannot carry out: an unknown method or a missing parameter."""


def _str(params: Params, name: str) -> str:
    value = params.get(name)
    if not isinstance(value, str):
        message = f"Parameter {name!r} must be text"
        raise BridgeError(message)
    return value


def _int(params: Params, name: str) -> int:
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        message = f"Parameter {name!r} must be a whole number"
        raise BridgeError(message)
    return value


def _float(params: Params, name: str) -> float:
    value = params.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        message = f"Parameter {name!r} must be a number"
        raise BridgeError(message)
    return float(value)


def _bool(params: Params, name: str) -> bool:
    value = params.get(name)
    if not isinstance(value, bool):
        message = f"Parameter {name!r} must be true or false"
        raise BridgeError(message)
    return value


def _ids(params: Params, name: str) -> tuple[str, ...]:
    value = params.get(name)
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in cast("list[object]", value)
    ):
        message = f"Parameter {name!r} must be a list of text"
        raise BridgeError(message)
    return tuple(cast("list[str]", value))


class Bridge:
    """The controller's actions by name, and the state the window draws."""

    def __init__(self, controller: Controller) -> None:
        self.controller: Controller = controller
        self.choices: view.Choices = view.Choices()
        self.dirty: threading.Event = threading.Event()
        self.dirty.set()
        controller.subscribe(self.dirty.set)
        c = controller
        self.methods: dict[str, Callable[[Params], object]] = {
            "hello": self.hello,
            "state": lambda _p: self.state(),
            "discover": lambda _p: c.discover(),
            # the new world
            "set_choice": self.set_choice,
            "set_seed": lambda p: c.set_seed(_str(p, "value")),
            "randomize": lambda _p: c.randomize(),
            "use_code": lambda p: c.use_code(_str(p, "value")),
            "set_value": self.set_value,
            "set_position": self.set_position,
            "reset_value": lambda p: c.reset_value(_str(p, "key")),
            "reset_values": lambda _p: c.reset_values(),
            "set_quick": lambda p: c.set_quick(_str(p, "name"), _str(p, "level")),
            "set_install": self.set_install,
            "set_destination": self.set_destination,
            "set_show_new_world": lambda p: c.set_show_new_world(_bool(p, "value")),
            "choose_land_image": lambda p: c.choose_land_image(Path(_str(p, "path"))),
            "clear_land_image": lambda _p: c.clear_land_image(),
            "save_land_template": lambda p: c.save_land_template(Path(_str(p, "path"))),
            "sketch_candidates": lambda _p: c.sketch_candidates(),
            "candidate_pictures": self.candidate_pictures,
            "choose_candidate": lambda p: c.choose_candidate(_int(p, "index")),
            "enqueue": lambda _p: c.enqueue(),
            "clear_queue": lambda _p: c.clear_queue(),
            "start_queue": lambda _p: c.start_queue(),
            "start": self.start,
            "retry_new_seed": lambda _p: c.retry_new_seed(),
            "cancel": lambda _p: c.cancel(),
            # the library
            "select": self.select,
            "refresh": lambda _p: c.refresh_library(),
            "import_file": lambda p: c.import_file(Path(_str(p, "path"))),
            "remove_entries": lambda p: c.remove_entries(_ids(p, "ids")),
            "delete_entries": lambda p: c.delete_entries(_ids(p, "ids")),
            "thumbnail": self.thumbnail,
            # the selected world
            "rename": self.rename,
            "annotate": self.annotate,
            "set_visibility": self.set_visibility,
            "reveal": self.reveal,
            "add": lambda _p: c.add_selected(),
            "check": lambda _p: c.check_selected(),
            "reroll": lambda p: c.reroll_selected(_str(p, "part"), keep_both=_bool(p, "keep_both")),
            "undo": lambda _p: c.undo_selected(),
            "like": self.like,
            "edit": lambda _p: c.edit_selected(),
            "export_file": self.export_file,
            "send_built": self.send_built,
            "copy_mod": self.copy_mod,
            "save_png": self.save_png,
            "save_preview": self.save_preview,
            "picture": self.picture,
            "folder": self.folder,
            "atlas": self.atlas,
            "compare_list": lambda _p: view.compare_list(c),
            # settings
            "choose_game": lambda p: c.choose_game(Path(_str(p, "path"))),
            "choose_profile": lambda p: c.choose_profile(Path(_str(p, "path"))),
            "pick_game": self.pick_game,
            "pick_profile": self.pick_profile,
            "set_language": self.set_language,
            "save_diagnostics": lambda p: c.save_diagnostics(Path(_str(p, "path"))),
            "diagnostics_name": self.diagnostics_name,
        }

    # -- what the window draws -----------------------------------------------------------------

    def hello(self, _params: Params) -> dict[str, object]:
        """The window's strings and choices, and the state to draw first."""
        return {"static": view.static(self.controller), "state": self.state()}

    def state(self) -> dict[str, object]:
        """What the window draws now."""
        return view.state(self.controller, self.choices)

    # -- the new world -------------------------------------------------------------------------

    def set_choice(self, params: Params) -> None:
        choice = _str(params, "choice")
        if choice == (self.controller.mode or self.controller.preset):
            return
        if choice in random_types.MODES:
            self.controller.set_mode(choice)
        else:
            self.controller.set_preset(choice)

    def set_value(self, params: Params) -> None:
        """A value typed in the window's unit."""
        from rnw.app import controls  # noqa: PLC0415 - one import for two methods

        key = _str(params, "key")
        control = controls.BY_KEY.get(key)
        if control is None:
            message = f"Unknown setting {key!r}"
            raise BridgeError(message)
        self.controller.set_value(key, control.stored(_float(params, "value")))

    def set_position(self, params: Params) -> None:
        """A slider's position, of ``controls.STEPS``."""
        from rnw.app import controls  # noqa: PLC0415 - one import for two methods

        key = _str(params, "key")
        control = controls.BY_KEY.get(key)
        if control is None:
            message = f"Unknown setting {key!r}"
            raise BridgeError(message)
        self.controller.set_value(key, control.value_at(_int(params, "position")))

    def set_install(self, params: Params) -> None:
        self.controller.install = _bool(params, "value")
        self.dirty.set()

    def set_destination(self, params: Params) -> None:
        """Where a new world goes: the library, a copy of its mod in a folder, or a world file
        alone; a path is the folder or the file, given when the player has chosen it."""
        kind = _str(params, "kind")
        if kind not in view.DESTINATIONS:
            message = f"Unknown destination {kind!r}"
            raise BridgeError(message)
        c = self.controller
        path = params.get("path")
        if kind != self.choices.destination:
            c.output_folder, c.world_file = None, None
            if kind != "library":
                c.install = False
        self.choices.destination = kind
        if isinstance(path, str) and path:
            if kind == "mod":
                c.output_folder = Path(path)
            elif kind == "world":
                c.world_file = Path(path)
        self.dirty.set()

    def candidate_pictures(self, _params: Params) -> list[str]:
        return [view.array_picture(found.picture) for found in self.controller.candidates]

    def start(self, _params: Params) -> str | None:
        c = self.controller
        problem = c.problem()
        unchosen = c.output_folder is None and c.world_file is None
        if problem is None and self.choices.destination != "library" and unchosen:
            problem = window.text("destination_missing")
        return problem or c.start()

    # -- the library ---------------------------------------------------------------------------

    def select(self, params: Params) -> None:
        self.controller.select(view.selection_of(self.controller, _str(params, "id")))

    def thumbnail(self, params: Params) -> str:
        return view.picture(
            view.library_picture(self.controller, _str(params, "id")), view.THUMBNAIL
        )

    # -- the selected world --------------------------------------------------------------------

    def _world(self, params: Params) -> World:
        key = _str(params, "id")
        world = next((item for item in self.controller.worlds if item.id == key), None)
        if world is None:
            message = f"No world {key!r} in the library"
            raise BridgeError(message)
        return world

    def _tell(self, world: World, message: str | None) -> str | None:
        """Keep what an action on a world came to, for its page, and return it."""
        if message:
            self.choices.told[world.id] = message
        else:
            _ = self.choices.told.pop(world.id, None)
        self.dirty.set()
        return message

    def rename(self, params: Params) -> str | None:
        world = self._world(params)
        return self._tell(world, self.controller.rename(world, _str(params, "name")))

    def annotate(self, params: Params) -> str:
        world = self._world(params)
        self.controller.annotate(
            world,
            _str(params, "notes"),
            _str(params, "user_tag"),
            starred=_bool(params, "starred"),
        )
        return window.text("notes_saved")

    def set_visibility(self, params: Params) -> str | None:
        world = self._world(params)
        problem = self.controller.set_world_visibility(world, show=_bool(params, "value"))
        return self._tell(world, problem or window.text("visibility_updated"))

    def reveal(self, params: Params) -> None:
        self.controller.reveal_world(self._world(params))

    def like(self, params: Params) -> None:
        self.controller.like(self._world(params))

    def export_file(self, params: Params) -> str:
        world, path = self._world(params), _str(params, "path")
        problem = self.controller.export_file(world, Path(path))
        return problem or window.text("file_saved", path=path)

    def send_built(self, params: Params) -> str | None:
        return self.controller.send_built(self._world(params), Path(_str(params, "path")))

    def copy_mod(self, params: Params) -> str | None:
        return self.controller.copy_mod_to(self._world(params), Path(_str(params, "path")))

    def save_png(self, params: Params) -> str:
        """Write a picture the window drew (a map as it is shown) from its PNG data URL."""
        path, data = _str(params, "path"), _str(params, "data")
        try:
            raw = base64.b64decode(data.removeprefix(PNG_URL), validate=True)
        except binascii.Error as error:
            raise BridgeError(NOT_PNG) from error
        if not data.startswith(PNG_URL) or not raw.startswith(PNG_SIGNATURE):
            raise BridgeError(NOT_PNG)
        try:
            _ = Path(path).write_bytes(raw)
        except OSError as error:
            return window.explain(error)
        return window.text("picture_saved", path=path)

    def save_preview(self, params: Params) -> str:
        world, path = self._world(params), _str(params, "path")
        problem = self.controller.save_preview(world, Path(path))
        return problem or window.text("picture_saved", path=path)

    def picture(self, params: Params) -> str:
        """The world's overview picture, covered unless it may be shown, full size."""
        return view.picture(self.controller.picture(self._world(params)))

    def folder(self, params: Params) -> str:
        key = _str(params, "id")
        stray = self.controller.selected_stray()
        if stray is not None and key == self.controller.selection:
            return str(stray)
        return str(view.world_folder(self.controller, self._world(params)))

    def atlas(self, params: Params) -> dict[str, object] | None:
        return view.atlas_bundle(self.controller, self._world(params))

    # -- settings ------------------------------------------------------------------------------

    def pick_game(self, params: Params) -> None:
        c, index = self.controller, _int(params, "index")
        if 0 <= index < len(c.games):
            c.game = c.games[index]
            self.dirty.set()

    def pick_profile(self, params: Params) -> None:
        c, index = self.controller, _int(params, "index")
        if 0 <= index < len(c.profiles):
            c.profile = c.profiles[index]
            c.refresh_library()

    def set_language(self, params: Params) -> dict[str, object]:
        """Remember the window's language (empty: the game's) and speak it at once."""
        self.controller.set_language(_str(params, "language"))
        window.set_language(self.controller.window_language())
        return self.hello(params)

    def diagnostics_name(self, _params: Params) -> str:
        from rnw.app import diagnostics  # noqa: PLC0415 - only for this

        stamp = time.strftime("%Y%m%d-%H%M")
        return diagnostics.default_name(stamp)

    # -- one request ---------------------------------------------------------------------------

    def call(self, method: str, params: Params) -> object:
        """Carry out ``method``; raises ``BridgeError`` for one that does not exist."""
        handler = self.methods.get(method)
        if handler is None:
            message = f"Unknown method {method!r}"
            raise BridgeError(message)
        return handler(params)


def _answer(bridge: Bridge, line: str) -> dict[str, object] | None:
    """The reply to one line of input; None for a blank line."""
    if not line.strip():
        return None
    try:
        request = cast("dict[str, object]", json.loads(line))
    except ValueError:
        return {"id": None, "error": "The request is not JSON"}
    number = request.get("id")
    method = request.get("method")
    params: object = request.get("params") or {}
    if not isinstance(method, str) or not isinstance(params, dict):
        return {"id": number, "error": "A request needs a method and an object of parameters"}
    try:
        result = bridge.call(method, cast("Params", params))
    except BridgeError as error:
        return {"id": number, "error": str(error)}
    except Exception as error:  # noqa: BLE001 - the window shows it; the log keeps the traceback
        logs.get().exception("request %s failed", method)
        return {"id": number, "error": window.explain(error)}
    return {"id": number, "result": result}


class _Pace:
    """When the loop last sent a state, ticked a countdown and looked at the library."""

    def __init__(self) -> None:
        self.state: str = ""
        self.sent: float = 0.0
        self.tick: float = 0.0
        self.poll: float = time.monotonic()

    def keep_up(self, bridge: Bridge, send: Callable[[dict[str, object]], None]) -> None:
        """Tick a running generation's countdown, poll an idle library, send a changed state."""
        controller = bridge.controller
        now = time.monotonic()
        live = controller.phase is Phase.RUNNING and controller.task is Task.GENERATE
        if live and now - self.tick >= TICK:
            self.tick = now
            bridge.dirty.set()
        if not controller.busy and now - self.poll >= POLL:
            self.poll = now
            controller.poll_library()
        if bridge.dirty.is_set() and now - self.sent >= STATE_INTERVAL:
            bridge.dirty.clear()
            self.sent = now
            data = bridge.state()
            encoded = json.dumps(data, ensure_ascii=False, sort_keys=True)
            if encoded != self.state:
                self.state = encoded
                send({"event": "state", "data": data})


def serve(bridge: Bridge, incoming: IO[str], outgoing: IO[str]) -> None:
    """Answer requests from ``incoming`` until it closes, sending states as the controller
    changes; then cancel running work and wait for it."""
    lines: queue.Queue[str | None] = queue.Queue()

    def read() -> None:
        for line in incoming:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=read, name="bridge-input", daemon=True).start()

    def send(message: dict[str, object]) -> None:
        _ = outgoing.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
        outgoing.flush()

    pace = _Pace()
    while True:
        try:
            line = lines.get(timeout=STATE_INTERVAL / 2)
        except queue.Empty:
            line = ""
        if line is None:
            break
        if line:
            reply = _answer(bridge, line)
            if reply is not None:
                send(reply)
        pace.keep_up(bridge, send)
    bridge.controller.cancel()
    bridge.controller.wait(CLOSE_WAIT)


def self_test() -> int:
    """Check the parts a broken package would miss; returns the exit code."""
    with TemporaryDirectory(prefix="rnw-self-test-") as temporary:
        try:
            controller = Controller(data=Path(temporary))
            bridge = Bridge(controller)
            hello = cast("dict[str, dict[str, object]]", bridge.call("hello", {}))
            if hello["static"]["version"] != __version__ or "new" not in hello["state"]:
                return 1
            code = new_code("continents", 42)
            if decode(encode(code)) != code:
                return 1
            if _native.configure_threads(1) < 1:
                return 1
        finally:
            logs.stop()  # Windows cannot remove the folder while the log is open.
    print(f"{window.TITLE} {__version__}: bridge, native kernels and world codes work")
    return 0


def _protocol_stream() -> IO[str]:
    """Standard output for the protocol alone: everything else printed goes to standard error."""
    _ = sys.stdout.flush()
    duplicate = os.dup(1)
    _ = os.dup2(2, 1)
    sys.stdout = sys.stderr
    return os.fdopen(duplicate, "w", encoding="utf-8", newline="\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Serve the window on standard input and output."""
    parser = argparse.ArgumentParser(prog="rnw-bridge", description=DESCRIPTION)
    _ = parser.add_argument("--data", type=Path, help="the generator's data folder")
    _ = parser.add_argument(SELF_TEST, action="store_true", help="check the package and exit")
    options = parser.parse_args(argv)
    if bool(cast("object", options.self_test)):
        return self_test()
    outgoing = _protocol_stream()
    incoming = open(sys.stdin.fileno(), encoding="utf-8", closefd=False)  # noqa: SIM115 - standard input
    data = cast("Path | None", options.data)
    controller = Controller(data=data, program_folder=paths.program_directory())
    window.set_language(controller.window_language())
    bridge = Bridge(controller)
    controller.discover()
    if controller.selection != NEW and controller.selected_world() is None:
        controller.select(NEW)
    try:
        serve(bridge, incoming, outgoing)
    finally:
        logs.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
