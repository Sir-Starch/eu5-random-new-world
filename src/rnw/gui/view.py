"""The controller's state as plain data, for a window drawn in a web view (ADR 0011).

The Tauri window knows nothing of Python: the bridge (``rnw.gui.bridge``) sends it what is here
as JSON. ``static`` is what does not change while the generator runs (the window's strings in its
language, the controls and their ranges, the world types, the layers); ``state`` is everything the
window draws now, the texts it shows already in its language; ``atlas_bundle`` is a world's atlas
as the map viewer paints it, with every layer's colours, legend and borders; ``picture`` is a
preview as a PNG data URL. Nothing here imports Qt, and nothing changes the controller.
"""

# NumPy stubs type array arithmetic and indexing as Any.
# pyright: reportAny=false

from __future__ import annotations

import base64
import io
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

import numpy as np
from PIL import Image

from rnw import __version__, parallel, worldname
from rnw import atlas as atlas_module
from rnw.app import controls, quick, random_types
from rnw.app.library import Placement
from rnw.gui import mapstyle
from rnw.gui.controller import NEW, STRAY, Controller, Phase, Task
from rnw.gui.text import GROUPING, LANGUAGE_NAMES, TITLE, grouped, language, table, text
from rnw.layers import PARTS
from rnw.png import COLOR_RGB, encode_png
from rnw.settings import WORLD_TYPES

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.app.library import World
    from rnw.atlas import Atlas

GIB: Final[float] = float(1 << 30)
THUMBNAIL: Final[tuple[int, int]] = (320, 160)
DESTINATIONS: Final[tuple[str, ...]] = ("library", "mod", "world")
# The tasks a world's own page reports, rather than the new-world page.
WORLD_TASKS: Final[frozenset[Task]] = frozenset(
    {Task.ADD, Task.REMOVE, Task.DELETE, Task.CHECK, Task.REROLL, Task.SEND, Task.COPY, Task.UNDO}
)
GENERATING: Final[frozenset[Task]] = frozenset({Task.GENERATE, Task.QUEUE, Task.CANDIDATES})


@dataclass(slots=True)
class Choices:
    """What the window chose that the controller does not keep: where a new world goes."""

    destination: str = "library"
    # World id -> the result of its last action, said under its page until another is shown.
    told: dict[str, str] = field(default_factory=dict)


def static(controller: Controller) -> dict[str, object]:
    """What the window needs once: its strings, the choices it offers and their ranges."""
    preset = controller.preset
    return {
        "title": TITLE,
        "version": __version__,
        "language": language(),
        "languages": [{"key": key, "name": name} for key, name in LANGUAGE_NAMES.items()],
        "grouping": GROUPING.get(language(), ","),
        "strings": table(),
        "choices": list(random_types.CHOICES),
        "modes": list(random_types.MODES),
        "world_types": list(WORLD_TYPES),
        "groups": list(controls.GROUPS),
        "controls": [
            {
                "key": control.key,
                "group": control.group,
                "low": control.shown(control.low),
                "high": control.shown(control.high),
                "decimals": control.decimals,
                "unit": text(f"unit.{control.unit}").strip(),
                "steps": controls.STEPS,
                "logarithmic": control.logarithmic,
                "advanced": control in controls.ADVANCED,
                "toggle": control.low == 0 and control.high == 1,
                "default": control.shown(control.default(preset)),
            }
            for control in controls.CONTROLS
        ],
        "quick": [
            {"name": item.name, "levels": [level.name for level in item.levels]}
            for item in quick.QUICK
        ],
        "budget": controls.LOCATION_BUDGET,
        "layers": list(atlas_module.LAYERS),
        "ramps": sorted(atlas_module.RAMPS),
        "bordered": sorted(atlas_module.BORDERED),
        "parts": list(PARTS),
        "destinations": list(DESTINATIONS),
        "name_limit": worldname.MAX_NAME,
    }


def state(controller: Controller, choices: Choices) -> dict[str, object]:
    """Everything the window draws now."""
    c = controller
    generating = c.task in GENERATING
    return {
        "phase": c.phase.value,
        "task": c.task.value if c.task else None,
        "target": c.task_target,
        "busy": c.busy,
        "runs": c.runs,
        "fraction": c.fraction,
        "generating": generating and c.phase is not Phase.IDLE,
        "running": c.running_text(),
        "stages": [{"label": label, "state": mark} for label, mark in c.stage_rows()],
        "eta": c.estimated_remaining(),
        "status": _status(c),
        "message": c.message,
        "result": (
            {"world": c.result.world.id, "seconds": round(c.result.seconds)}
            if c.result is not None
            else None
        ),
        "game": _game(c),
        "games": [str(game.directory) for game in c.games],
        "profiles": [str(profile.directory) for profile in c.profiles],
        "preferences": {
            "show_new_world": c.preferences.show_new_world,
            "language": c.preferences.language,
            "window": c.preferences.window,
        },
        "resources": _resources(),
        "selection": c.selection,
        "library": _library(c),
        "batch": _batch(c),
        "new": _new(c, choices),
        "world": _world(c, choices),
        "stray": _stray(c),
        "candidates": [
            {"seed": str(found.seed), "land": found.land_permille / 10} for found in c.candidates
        ]
        if c.task is Task.CANDIDATES and c.phase is Phase.FINISHED
        else [],
    }


def _status(c: Controller) -> str:
    match c.phase:
        case Phase.IDLE:
            return text("idle")
        case Phase.RUNNING:
            return text("running", stages=c.running_text() or "…")
        case Phase.CANCELLING:
            return text("cancelling")
        case Phase.FINISHED:
            seconds = round(c.result.seconds) if c.result else 0
            return text("finished", seconds=seconds)
        case Phase.FAILED:
            return text("failed", message=c.message, report_hint=text("report_hint"))
        case Phase.CANCELLED:
            return text("cancelled")


def _game(c: Controller) -> dict[str, object]:
    game, profile = c.game, c.profile
    return {
        "found": game is not None,
        "directory": str(game.directory) if game else "",
        "build": game.build_id if game else "",
        "status": text("game_status", build=game.build_id or "?") if game else TITLE,
        "profile": str(profile.directory) if profile else "",
        "problem": text("game_missing")
        if game is None
        else text("profile_missing")
        if profile is None
        else "",
    }


def _resources() -> str:
    free = parallel.available_memory()
    threads = parallel.thread_count()
    return (
        text("resources_unknown", threads=threads)
        if free is None
        else text("resources", threads=threads, free=f"{free / GIB:.1f}")
    )


def picture_key(path: Path | None) -> str:
    """A key that changes when the picture does, so the window fetches it again."""
    if path is None:
        return ""
    try:
        status = path.stat()
    except OSError:
        return ""
    return f"{path.name}:{status.st_mtime_ns}:{status.st_size}"


def _library(c: Controller) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for world, depth in c.listed():
        placement = c.placement(world)
        entries.append(
            {
                "kind": "world",
                "id": world.id,
                "title": c.name(world),
                "preset": world.preset,
                "type": text(f"type.{world.preset}"),
                "created": world.created,
                "placement": placement.value,
                "place": text(f"list.{placement.value}"),
                "part": text(f"part.{world.part}") if world.part else "",
                "depth": depth,
                "starred": world.starred,
                "tag": world.user_tag,
                "shown": c.shown(world),
                "picture": picture_key(c.picture(world)),
            }
        )
    entries.extend(
        {
            "kind": "stray",
            "id": f"{STRAY}{stray.name}",
            "title": text("stray_name"),
            "folder": stray.name,
            "placement": Placement.IN_GAME.value,
        }
        for stray in c.strays
    )
    return entries


def _batch(c: Controller) -> str:
    """What became of the last removal or deletion of several entries."""
    if c.task not in {Task.REMOVE, Task.DELETE}:
        return ""
    if c.busy:
        return text(f"task.{c.task.value}") if c.task else ""
    if c.phase is Phase.FAILED:
        return text("task_failed", message=c.message, report_hint=text("report_hint"))
    if c.phase is Phase.FINISHED:
        return text("batch_removed" if c.task is Task.REMOVE else "batch_deleted")
    if c.phase is Phase.CANCELLED:
        return text("batch_cancelled")
    return ""


def _new(c: Controller, choices: Choices) -> dict[str, object]:
    busy = c.busy
    values: dict[str, object] = {}
    for control in controls.CONTROLS:
        if control.group == "wall" and c.preset != "wall":
            continue
        value = c.value(control.key)
        default = control.default(c.preset)
        values[control.key] = {
            "shown": control.shown(value),
            "position": control.position(value),
            "default": control.shown(default),
            "default_position": control.position(default),
            "changed": control.key in c.changes,
        }
    try:
        estimate: int | None = c.estimated_locations()
    except ValueError:
        estimate = None
    problem = c.problem()
    target = c.output_folder or c.world_file
    if choices.destination != "library" and target is None and problem is None:
        problem = text("destination_missing")
    hint = (
        "generation_install"
        if c.install and choices.destination == "library"
        else "generation_copy"
        if c.output_folder is not None
        else "generation_file"
        if c.world_file is not None
        else "generation_keep"
    )
    drawn = c.land_mask
    return {
        "choice": c.mode or c.preset,
        "preset": c.preset,
        "mode": c.mode,
        "seed": str(c.seed),
        "code": c.code,
        "notice": c.notice,
        "values": values,
        "quick": {item.name: c.quick_level(item.name) for item in quick.QUICK},
        "changed": len(c.changes),
        "estimate": estimate,
        "estimate_text": text("estimate", count=grouped(estimate)) if estimate is not None else "",
        "over_budget": estimate is not None and estimate > controls.LOCATION_BUDGET,
        "problem": problem,
        "hint": text(hint),
        "install": c.install,
        "destination": choices.destination,
        "target": str(target) if target is not None else "",
        "land_mask": format(drawn.id, "x") if drawn is not None else "",
        "land_mask_text": text("land_image_chosen", id=format(drawn.id, "x")) if drawn else "",
        "candidates_enabled": not busy
        and c.game is not None
        and not c.world_code().settings().mask.id,
        "template_enabled": not busy and c.game is not None,
        "queue": [
            {"seed": str(job.code.seed), "type": text(f"type.{job.code.preset}")} for job in c.queue
        ],
        "queue_done": c.queue_done,
        "retry": c.phase is Phase.FAILED and c.task is Task.GENERATE,
        "retry_enabled": c.problem() is None,
    }


def _world(c: Controller, choices: Choices) -> dict[str, object] | None:
    world = c.selected_world()
    if world is None:
        return None
    placement = c.placement(world)
    changed = c.changed_count(world)
    note = c.build_note(world)
    found = c.atlas(world)
    parent = c.parent_of(world)
    mod = c.profile.directory / "mod" / world.folder if c.profile is not None else None
    mine = c.task_target == world.id and c.task in WORLD_TASKS
    return {
        "id": world.id,
        "name": c.name(world),
        "default_name": worldname.display_name(world.preset, worldname.tag_of(world.id)),
        "tag": worldname.tag_of(world.id),
        "code": world.code,
        "preset": world.preset,
        "type": text(f"type.{world.preset}"),
        "seed": str(world.seed),
        "custom": text("custom_some", count=changed) if changed else text("custom_none"),
        "created": world.created,
        "build": world.game_build or "?",
        "generator": world.generator,
        "reproduce": c.reproduction(world),
        "place": text("place.in_game", path=mod)
        if placement is Placement.IN_GAME
        else text("place.kept")
        if placement is Placement.KEPT
        else text("place.code_only", seconds=round(world.seconds or 120)),
        "placement": placement.value,
        "shown": c.shown(world),
        "revealed": c.revealed(world),
        "atlas": found is not None,
        "summary": c.summary(world),
        "totals": atlas_module.totals(found) if found is not None and c.revealed(world) else None,
        "notes": world.notes,
        "user_tag": world.user_tag,
        "starred": world.starred,
        "part": text(f"part.{world.part}") if world.part else "",
        "note": note,
        "advice": c.next_step(world) if placement is Placement.IN_GAME else "",
        "parent": parent.id if parent is not None else "",
        "parent_name": c.name(parent) if parent is not None else "",
        "picture": picture_key(c.picture(world)),
        "add_problem": c.world_problem(),
        "remove_problem": c.removal_problem(),
        "can_change": not c.busy and c.game is not None,
        "task": _world_task(c) if mine else None,
        "told": choices.told.get(world.id, ""),
        "compare": len(c.maps_to_compare()) >= 2,  # noqa: PLR2004 - two worlds are compared
    }


def _world_task(c: Controller) -> dict[str, object]:
    if c.busy:
        label = text(f"task.{c.task.value}") if c.task else ""
        return {
            "running": True,
            "line": f"{label} {c.running_text()}".strip(),
            "bar": c.task in {Task.ADD, Task.CHECK, Task.REROLL},
            "fraction": c.fraction,
        }
    failed = c.phase is Phase.FAILED
    return {
        "running": False,
        "line": text("task_failed", message=c.message, report_hint=text("report_hint"))
        if failed
        else "",
        "bar": False,
        "fraction": c.fraction,
        "failed": failed,
    }


def _stray(c: Controller) -> dict[str, object] | None:
    stray = c.selected_stray()
    if stray is None:
        return None
    return {
        "folder": stray.name,
        "path": str(stray),
        "about": text("stray_about", folder=stray.name),
        "remove_problem": c.removal_problem(),
    }


# -- pictures ------------------------------------------------------------------------------------


def data_url(png: bytes) -> str:
    """A PNG as a ``data:`` URL the web view shows without reading a file."""
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def picture(path: Path | None, size: tuple[int, int] | None = None) -> str:
    """A preview as a data URL, shrunk to fit ``size``; '' when there is none."""
    if path is None:
        return ""
    try:
        if size is None:
            return data_url(path.read_bytes())
        with Image.open(path) as image:
            image.thumbnail(size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            image.convert("RGB").save(buffer, format="PNG", optimize=False)
    except OSError:
        return ""
    return data_url(buffer.getvalue())


def array_picture(pixels: NDArray[np.uint8]) -> str:
    """An RGB array as a PNG data URL."""
    return data_url(
        encode_png(np.ascontiguousarray(pixels), color_type=COLOR_RGB, compression="zlib")
    )


# -- the atlas -----------------------------------------------------------------------------------


def _b64(array: NDArray[np.generic]) -> str:
    return base64.b64encode(np.ascontiguousarray(array).tobytes()).decode("ascii")


def runs(labels: NDArray[np.int32]) -> NDArray[np.uint32]:
    """The box's labels row by row as (label, length) pairs: a few hundred kilobytes instead of
    the megabytes of the raster, which the viewer unrolls in a moment."""
    flat = labels.reshape(-1).astype(np.int64)
    if flat.size == 0:
        return np.zeros(0, dtype=np.uint32)
    starts = np.concatenate(([0], np.flatnonzero(np.diff(flat)) + 1))
    lengths = np.diff(np.concatenate((starts, [flat.size])))
    return np.stack([flat[starts], lengths], axis=1).reshape(-1).astype("<u4")


def _hex(colour: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*colour)


def words_for(controller: Controller, found: Atlas) -> atlas_module.Words:
    """The window's words for an atlas: legend words, the game's names of the identifiers
    (regions too), names of the world in the window's language; as the classic window's."""
    return controller.words(found)


def atlas_bundle(controller: Controller, world: World) -> dict[str, object] | None:
    """A revealed world's atlas as the map viewer paints and asks it; None when it has none or
    its New World is covered."""
    found = controller.atlas(world)
    if found is None or not controller.revealed(world):
        return None
    started = time.perf_counter()
    words = words_for(controller, found)
    height, width = found.size

    def name(value: object) -> str:
        return mapstyle.written(value, words)

    layers: dict[str, object] = {}
    for layer in atlas_module.LAYERS:
        lens = atlas_module.lens(found, layer, words)
        layers[layer] = {
            "colours": _b64(lens.colours),
            "classes": _b64(lens.classes.astype("<i4")),
            "values": _b64(lens.values.astype("<i4")),
            "legend": [[label, _hex(colour), count] for label, colour, count in lens.legend],
            "ramp": [_hex(colour) for colour in lens.ramp],
        }
    names = [name(value) for value in found.names]
    bundle: dict[str, object] = {
        "id": world.id,
        "name": controller.name(world),
        "size": [height, width],
        "scale": found.scale,
        "cells": found.cells,
        "labels": _b64(runs(found.labels)),
        "kinds": list(atlas_module.KINDS),
        "keys": list(found.keys),
        "names": names,
        "kind": found.kinds.tolist(),
        "area": [name(value) for value in found.areas],
        "region": [name(value) for value in found.regions],
        "owner": found.owner.tolist(),
        "culture": found.culture.tolist(),
        "religion": found.religion.tolist(),
        "material": found.material.tolist(),
        "climate": found.climate.tolist(),
        "vegetation": found.vegetation.tolist(),
        "topography": found.topography.tolist(),
        "settlement": found.settlement.tolist(),
        "population": found.population.tolist(),
        "complexity": found.complexity.tolist(),
        "centre": found.centre.reshape(-1).tolist(),
        "vocabulary": {
            key: [words.key(word) for word in values] for key, values in found.vocabulary.items()
        },
        "precious": sorted(atlas_module.PRECIOUS),
        "raw": {key: list(values) for key, values in found.vocabulary.items()},
        "countries": [
            {
                "tag": country.tag,
                "name": words.name(country.name) if country.name else country.tag,
                "kind": country.kind,
                "color": _hex(country.color),
                "capital": country.capital,
                "culture": country.culture,
                "religion": country.religion,
                "locations": country.locations,
            }
            for country in found.countries
        ],
        "totals": atlas_module.totals(found),
        "layers": layers,
    }
    bundle["seconds"] = round(time.perf_counter() - started, 3)
    return bundle


def compare_list(controller: Controller) -> list[dict[str, str]]:
    """The worlds whose maps may be compared: revealed, with an atlas."""
    return [
        {"id": world.id, "name": controller.name(world)}
        for world, _found in controller.maps_to_compare()
    ]


def world_folder(controller: Controller, world: World) -> Path:
    """Where the world's mod is: in the game, or beside the generator."""
    if controller.placement(world) is Placement.IN_GAME and controller.profile is not None:
        return controller.profile.directory / "mod" / world.folder
    return controller.data / "generated" / world.folder


def selection_of(controller: Controller, key: str) -> str:
    """``key`` when it names the new-world page, a world or a stray; else the new-world page."""
    if key == NEW or any(world.id == key for world in controller.worlds):
        return key
    if key.startswith(STRAY) and any(f"{STRAY}{s.name}" == key for s in controller.strays):
        return key
    return NEW


def library_picture(controller: Controller, world_id: str) -> Path | None:
    """The preview the library shows for a world, covered unless it may be shown."""
    world = next((item for item in controller.worlds if item.id == world_id), None)
    return controller.picture(world) if world is not None else None
