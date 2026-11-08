"""One cancellable atlas worker; the protocol thread keeps accepting input and sending states."""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rnw.app import library, logs
from rnw.gui import view
from rnw.gui.text import explain, language

if TYPE_CHECKING:
    from rnw.app.library import World
    from rnw.gui.controller import Controller


class SupersededError(Exception):
    """The viewer no longer needs this map."""


@dataclass
class Request:
    number: object
    request_key: str
    world: World
    key: tuple[object, ...]
    cancelled: threading.Event = field(default_factory=threading.Event)

    def checkpoint(self) -> None:
        if self.cancelled.is_set():
            raise SupersededError


class AtlasRequests:
    """Bound work to one thread and retain prepared bundles for the last four file revisions.

    Only this worker builds bundles. Only the serving thread submits/cancels requests and
    drains replies. Cancellation also settles the RPC immediately, including a queued request.
    """

    def __init__(self, controller: Controller) -> None:
        self.controller: Controller = controller
        self.pending: dict[str, Request] = {}
        self.work: queue.Queue[Request | None] = queue.Queue()
        self.replies: queue.Queue[tuple[Request, dict[str, object] | None]] = queue.Queue()
        self.cache: dict[tuple[object, ...], dict[str, object]] = {}
        self.thread: threading.Thread = threading.Thread(
            target=self._run, name="atlas-loading", daemon=True
        )
        self.thread.start()

    def key(self, world: World) -> tuple[object, ...]:
        c = self.controller
        return (
            library.atlas_stamp(c.data, world),
            world.id,
            world.name,
            c.revealed(world),
            language(),
            c.game,
        )

    def submit(self, number: object, request_key: str, world: World) -> None:
        self.cancel(request_key)
        request = Request(number, request_key, world, self.key(world))
        self.pending[request_key] = request
        self.work.put(request)

    def cancel(self, request_key: str) -> None:
        request = self.pending.pop(request_key, None)
        if request is not None:
            request.cancelled.set()
            self.replies.put((request, None))

    def drain(self) -> list[dict[str, object]]:
        replies: list[dict[str, object]] = []
        while True:
            try:
                request, reply = self.replies.get_nowait()
            except queue.Empty:
                return replies
            if reply is None:
                replies.append({"id": request.number, "result": None})
            elif (
                not request.cancelled.is_set() and self.pending.get(request.request_key) is request
            ):
                del self.pending[request.request_key]
                world = next((w for w in self.controller.worlds if w.id == request.world.id), None)
                if world is None or self.key(world) != request.key:
                    reply = {"id": request.number, "result": None}
                replies.append(reply)

    def close(self) -> None:
        for request_key in list(self.pending):
            self.cancel(request_key)
        self.work.put(None)

    def _run(self) -> None:
        while (request := self.work.get()) is not None:
            if request.cancelled.is_set():
                continue
            try:
                request.checkpoint()
                bundle = self.cache.pop(request.key, None)
                if bundle is None:
                    bundle = view.atlas_bundle(self.controller, request.world, request.checkpoint)
                request.checkpoint()
                if self.key(request.world) != request.key:
                    bundle = None
                if bundle is not None:
                    self.cache[request.key] = bundle
                    while len(self.cache) > library.ATLAS_CACHE:
                        del self.cache[next(iter(self.cache))]
                reply: dict[str, object] = {"id": request.number, "result": bundle}
            except SupersededError:
                continue
            except Exception as error:  # noqa: BLE001 - report it, keep serving and allow retry
                logs.get().exception("atlas request failed")
                reply = {"id": request.number, "error": explain(error)}
            # Cancellation and completion are serialized by drain on the protocol thread.
            self.replies.put((request, reply))
