"""Stage an ID-preserving EU5 1.4.1 coastline candidate (D0, NOT GAME VALIDATED).

Inside a bounded American window, land-sea pixel boundaries move between existing
location IDs. The mod overrides only ``locations.png`` and ``rivers.png`` (whose 254/255
background is a water/land mask [V-EXEC]); hierarchy, colours and class lists are not
rewritten. Every output is re-decoded from disk and compared with the installation.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false

from __future__ import annotations

import json
import re
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast, override

import numpy as np

from rnw import __version__
from rnw.artifacts import check_new_output, pixel_digest, staged, write_bytes
from rnw.coast import move_coast
from rnw.contract import aggregate_digest, fingerprint
from rnw.eu5_map import (
    LOCATIONS,
    RIVER_LAND,
    RIVER_WATER,
    RIVERS,
    Eu5Map,
    labels_from_rgb,
    load_map,
    open_png,
)
from rnw.model import CellClass
from rnw.noise import fractal_noise
from rnw.png import COLOR_PALETTE, COLOR_RGB, ZLIB_LEVEL, encode_png
from rnw.rng import derive_seed
from rnw.settings import canonical_json, run_spec, spec_digest
from rnw.topology import adjacency_pairs, unpack_pairs
from rnw.validate import check_boundary_move

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.coast import CoastResult
    from rnw.settings import Settings

STATUS: Final[str] = "NOT GAME VALIDATED"
AMERICA: Final[str] = "america"
MOD_NAME: Final[re.Pattern[str]] = re.compile(r"rnw_exp_[a-z0-9_]{1,48}")
KNOWN_BUILDS: Final[dict[str, str]] = {
    "07f8cd273bdde1711e222533b9640a51ff2747c08eead36331fc1281fa5bc055": (
        "EU5 1.4.1 open beta, Steam build 25905365"
    ),
}
MOD_LOCATIONS: Final[str] = "in_game/map_data/locations.png"
MOD_RIVERS: Final[str] = "in_game/map_data/rivers.png"
NEW_LAND: Final[tuple[int, int, int]] = (250, 200, 40)
NEW_SEA: Final[tuple[int, int, int]] = (220, 40, 40)
UNCHANGED_INPUTS: Final[tuple[str, ...]] = (
    "named_locations/00_default.txt (colours, including the nine unused declarations)",
    "definitions.txt (hierarchy)",
    "default.map (sea, lake, impassable and non-ownable lists)",
    "location_templates.txt and start setup",
    "ports.csv, adjacencies.csv and all locator files (coasts near them are frozen)",
    "nodes.dat (opaque, not regenerated)",
    "gfx/terrain2 heightmap, decal height tiles and terrain cache",
)
UNTESTED: Final[tuple[str, ...]] = (
    "Whether EU5 1.4.1 mounts these two files from a mod and lets them override vanilla.",
    "Whether borders, selection, province shapes and centres follow the moved pixels.",
    "Whether nodes.dat or other derived caches conflict with moved boundaries.",
    (
        "Rendered terrain: visual heightmap/decal tiles and water are unchanged, so the drawn "
        "coastline will not match the moved location boundary."
    ),
    "Land and naval movement, ports and docks, unit/combat locators near moved coasts.",
    "Startup error log, startup time, save/reload, checksum, multiplayer and ironman.",
)


class ExportError(ValueError):
    """The installation or settings cannot produce a valid candidate."""


@dataclass(frozen=True, slots=True)
class UnsupportedBuildError(ExportError):
    """The map-contract fingerprint is not a known, tested build."""

    digest: str

    @override
    def __str__(self) -> str:
        return (
            f"Unsupported map-contract fingerprint {self.digest}; "
            "pass --accept-build with this digest to select it explicitly"
        )


@dataclass(frozen=True, slots=True)
class Window:
    """Half-open pixel rectangle [x0, x1) x [y0, y1)."""

    x0: int
    y0: int
    x1: int
    y1: int

    def slices(self) -> tuple[slice, slice]:
        """Row and column slices."""
        return slice(self.y0, self.y1), slice(self.x0, self.x1)


@dataclass(frozen=True, slots=True, eq=False)
class Eligibility:
    """Per-label permissions and per-pixel locks for one window."""

    land_ok: NDArray[np.bool_]
    sea_ok: NDArray[np.bool_]
    enclosed: NDArray[np.bool_]
    anchors: tuple[int, ...]
    frozen: NDArray[np.bool_]
    points_in_window: int


def dilate(mask: NDArray[np.bool_], radius: int) -> NDArray[np.bool_]:
    """Square (Chebyshev) dilation by ``radius`` pixels."""
    out = mask.copy()
    for _ in range(radius):
        grown = out.copy()
        grown[1:] |= out[:-1]
        grown[:-1] |= out[1:]
        out = grown
    for _ in range(radius):
        grown = out.copy()
        grown[:, 1:] |= out[:, :-1]
        grown[:, :-1] |= out[:, 1:]
        out = grown
    return out


def resolve_build(game_dir: Path, accept_build: str | None) -> tuple[str, str, bool]:
    """Return (digest, label, explicitly accepted) or refuse an unknown build."""
    digest = aggregate_digest(fingerprint(game_dir))
    if digest in KNOWN_BUILDS:
        return digest, KNOWN_BUILDS[digest], False
    if accept_build == digest:
        return digest, "Unknown build selected explicitly by the user", True
    raise UnsupportedBuildError(digest)


def check_window(game_map: Eu5Map, window: Window) -> None:
    """Keep the window inside the raster and away from the horizontal wrap seam."""
    height, width = game_map.labels.shape
    if not (0 < window.x0 < window.x1 < width and 0 <= window.y0 < window.y1 <= height):
        message = f"Window {window} must lie inside the {width}x{height} map off the wrap seam"
        raise ExportError(message)


def eligibility(game_map: Eu5Map, window: Window, settings: Settings) -> Eligibility:
    """Decide which American cells may change and which pixels are locked."""
    count = len(game_map.keys)
    crop = game_map.labels[window.slices()]
    totals = np.bincount(game_map.labels.ravel(), minlength=count)
    inner = np.bincount(crop[1:-1, 1:-1].ravel(), minlength=count)
    enclosed = (inner == totals) & (totals > 0)
    america = np.array([name == AMERICA for name in game_map.continents], dtype=bool)
    kinds = game_map.classes
    land = np.array([kind is CellClass.LAND for kind in kinds], dtype=bool)
    sea = np.array([kind is CellClass.SEA for kind in kinds], dtype=bool)
    water = sea | np.array([kind is CellClass.LAKE for kind in kinds], dtype=bool)
    anchors: set[int] = set()
    for first, second in unpack_pairs(adjacency_pairs(crop, diagonal=True)):
        for own, other in ((first, second), (second, first)):
            if sea[own] and america[own] and not america[other]:
                anchors.add(own)
    anchor_mask = np.zeros(count, dtype=bool)
    anchor_mask[list(anchors)] = True
    base = enclosed & america & ~game_map.ambiguous
    rivers = game_map.rivers[window.slices()]
    coast = settings.coast
    is_river = (rivers != RIVER_WATER) & (rivers != RIVER_LAND)
    expected = np.where(water[crop], RIVER_WATER, RIVER_LAND)
    frozen = dilate(is_river, coast.river_radius_px) | (rivers != expected)
    points = np.zeros(crop.shape, dtype=bool)
    inside = 0
    for point in game_map.points:
        if window.x0 <= point.x < window.x1 and window.y0 <= point.y < window.y1:
            points[point.y - window.y0, point.x - window.x0] = True
            inside += 1
    frozen |= dilate(points, coast.locator_radius_px)
    return Eligibility(
        land_ok=base & land,
        sea_ok=base & sea & ~anchor_mask,
        enclosed=enclosed,
        anchors=tuple(sorted(anchors)),
        frozen=frozen,
        points_in_window=inside,
    )


def _coast_edges(labels: NDArray[np.int32], water: NDArray[np.bool_]) -> int:
    wet = water[labels]
    return int(np.count_nonzero(wet[:, 1:] != wet[:, :-1])) + int(
        np.count_nonzero(wet[1:] != wet[:-1])
    )


def _check_points(game_map: Eu5Map, window: Window, after: NDArray[np.int32]) -> None:
    for point in game_map.points:
        if window.x0 <= point.x < window.x1 and window.y0 <= point.y < window.y1:
            row, column = point.y - window.y0, point.x - window.x0
            if after[row, column] != game_map.labels[point.y, point.x]:
                message = f"Map point moved to another cell: {point.source} {point.key}"
                raise ExportError(message)


def _preview(game_map: Eu5Map, result: CoastResult, frozen: NDArray[np.bool_]) -> NDArray[np.uint8]:
    palette = np.array(
        [
            (32, 64, 150)
            if kind is CellClass.SEA
            else (90, 150, 220)
            if kind is CellClass.LAKE
            else (96, 160, 72)
            if kind is CellClass.LAND
            else (128, 128, 128)
            for kind in game_map.classes
        ],
        dtype=np.uint8,
    )
    image = palette[result.labels]
    image[frozen] //= 2
    image[result.to_land] = NEW_LAND
    image[result.to_sea] = NEW_SEA
    return image


def _metadata(name: str, seed: int, preset: str) -> bytes:
    payload: dict[str, object] = {
        "name": f"RNW D0 coast {preset} seed {seed} ({STATUS})",
        "id": name,
        "version": __version__,
        "supported_game_version": "1.4.*",
        "short_description": f"Generated New World coastline candidate; local only; {STATUS}",
        "tags": ["Map"],
        "relationships": [],
        "game_custom_data": {},
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8-sig")


def _verify_written(
    game_dir: Path,
    mod_dir: Path,
    game_map: Eu5Map,
    window: Window,
    after: NDArray[np.int32],
) -> dict[str, object]:
    """Decode the written files and compare them with fresh decodes of the inputs."""
    height, width = game_map.labels.shape
    vanilla_rgb = open_png(game_dir / LOCATIONS, "RGB")
    written_rgb = open_png(mod_dir / MOD_LOCATIONS, "RGB", (width, height))
    differs = np.any(written_rgb != vanilla_rgb, axis=2)
    del vanilla_rgb
    outside = differs.copy()
    outside[window.slices()] = False
    if np.any(outside):
        message = "Written locations.png differs outside the window"
        raise ExportError(message)
    written_labels = labels_from_rgb(written_rgb, game_map.colors)
    if not np.array_equal(written_labels[window.slices()], after):
        message = "Written locations.png does not decode to the validated labels"
        raise ExportError(message)
    count = len(game_map.keys)
    before_counts = np.bincount(game_map.labels.ravel(), minlength=count)
    after_counts = np.bincount(written_labels.ravel(), minlength=count)
    del written_labels
    old_world = np.array([name != AMERICA for name in game_map.continents], dtype=bool)
    if not np.array_equal(before_counts[old_world], after_counts[old_world]):
        message = "A non-American cell changed its pixel count"
        raise ExportError(message)
    vanilla_rivers = open_png(game_dir / RIVERS, "P")
    written_rivers = open_png(mod_dir / MOD_RIVERS, "P", (width, height))
    river_changes = written_rivers != vanilla_rivers
    if np.any(river_changes & ~differs):
        message = "rivers.png changed where locations.png did not"
        raise ExportError(message)
    return {
        "outside_window_identical": True,
        "written_raster_matches_validated_labels": True,
        "non_american_cells": int(np.count_nonzero(old_world)),
        "non_american_pixel_counts_identical": True,
        "changed_location_px_on_disk": int(np.count_nonzero(differs)),
        "changed_river_px_on_disk": int(np.count_nonzero(river_changes)),
        "rivers_changed_only_with_locations": True,
    }


def export_candidate(  # noqa: PLR0913 - the CLI contract names each input explicitly.
    game_dir: Path,
    output: Path,
    *,
    seed: int,
    settings: Settings,
    accept_build: str | None = None,
    settings_file: str | None = None,
    replace: bool = False,
) -> dict[str, object]:
    """Generate, validate and stage one candidate bundle; return its report."""
    check_new_output(output, MOD_NAME, game_dir, replace=replace)
    digest, build_label, accepted = resolve_build(game_dir, accept_build)
    spec = run_spec(seed, settings)
    game_map = load_map(game_dir)
    window = Window(*settings.coast.window)
    check_window(game_map, window)
    rules = eligibility(game_map, window, settings)
    before = game_map.labels[window.slices()].copy()
    coast = settings.coast
    field = fractal_noise(
        derive_seed(seed, "eu5_coast"),
        window.x0,
        window.y0,
        window.x1 - window.x0,
        window.y1 - window.y0,
        period=coast.feature_px,
        octaves=coast.octaves,
        persistence_permille=coast.persistence_permille,
    )
    result = move_coast(
        before,
        land_ok=rules.land_ok,
        sea_ok=rules.sea_ok,
        frozen=rules.frozen,
        field=field,
        settings=coast,
    )
    checks = check_boundary_move(
        before,
        result.labels,
        keys=game_map.keys,
        editable=rules.land_ok | rules.sea_ok,
        enclosed=rules.enclosed,
        frozen=rules.frozen,
    )
    if not (np.any(result.to_land) and np.any(result.to_sea)):
        message = "No land-sea boundary moved in both directions; adjust window or settings"
        raise ExportError(message)
    _check_points(game_map, window, result.labels)
    water = np.array([kind in {CellClass.SEA, CellClass.LAKE} for kind in game_map.classes])
    rows, columns = window.slices()
    colors = game_map.colors[result.labels]
    game_map.rgb[rows, columns] = np.stack(
        [(colors >> 16) & 0xFF, (colors >> 8) & 0xFF, colors & 0xFF], axis=-1
    ).astype(np.uint8)
    river_window = game_map.rivers[rows, columns]
    river_window[result.to_land] = RIVER_LAND
    river_window[result.to_sea] = RIVER_WATER
    name = output.name
    compression = f"zlib level {ZLIB_LEVEL}, Up filter, zlib {zlib.ZLIB_RUNTIME_VERSION}"
    inputs = {record.path: record for record in game_map.inputs}
    with staged(output) as stage:
        files: list[dict[str, object]] = []
        for relative, source, pixels, mode, color_type, chunks in (
            (MOD_LOCATIONS, LOCATIONS, game_map.rgb, "RGB", COLOR_RGB, game_map.locations_chunks),
            (MOD_RIVERS, RIVERS, game_map.rivers, "P", COLOR_PALETTE, game_map.rivers_chunks),
        ):
            data = encode_png(
                pixels, color_type=color_type, compression="zlib", extra_chunks=chunks
            )
            record = write_bytes(stage, f"{name}/{relative}", data)
            record |= {
                "derived_from": source,
                "input_sha256": inputs[source].sha256,
                "pixels_sha256": pixel_digest(pixels, mode),
                "encoding": compression,
            }
            files.append(record)
        metadata = _metadata(name, seed, settings.preset)
        files.append(write_bytes(stage, f"{name}/.metadata/metadata.json", metadata))
        verified = _verify_written(game_dir, stage / name, game_map, window, result.labels)
        preview = _preview(game_map, result, rules.frozen)
        preview_record = write_bytes(
            stage, "preview.png", encode_png(preview, color_type=COLOR_RGB, compression="zlib")
        )
        settings_json = canonical_json(spec["settings"]).encode()
        settings_record = write_bytes(stage, "settings.json", settings_json)
        report: dict[str, object] = {
            "schema": 1,
            "status": STATUS,
            "tier": "T2 candidate: land-sea boundary moved between existing location IDs",
            "mod": name,
            "spec": spec,
            "spec_sha256": spec_digest(spec),
            "settings_source": settings_file or f"preset {settings.preset}",
            "build": {"fingerprint_sha256": digest, "label": build_label, "explicit": accepted},
            "window": {"x0": window.x0, "y0": window.y0, "x1": window.x1, "y1": window.y1},
            "eligibility": {
                "enclosed_cells": int(np.count_nonzero(rules.enclosed)),
                "editable_land_cells": int(np.count_nonzero(rules.land_ok)),
                "editable_sea_cells": int(np.count_nonzero(rules.sea_ok)),
                "anchor_sea_cells": [game_map.keys[index] for index in rules.anchors],
                "frozen_px": int(np.count_nonzero(rules.frozen)),
                "map_points_in_window": rules.points_in_window,
            },
            "changes": {
                **checks,
                "to_land_px": int(np.count_nonzero(result.to_land)),
                "to_sea_px": int(np.count_nonzero(result.to_sea)),
                "moved_by_pass": list(result.moved_by_pass),
                "coast_edges_before": _coast_edges(before, water),
                "coast_edges_after": _coast_edges(result.labels, water),
            },
            "invariants": {
                "frozen_pixels_identical": True,
                "only_enclosed_american_land_and_sea_cells_changed": True,
                "no_cell_vanished_or_fragmented": True,
                "cell_contacts_identical_4_and_8_neighbour": True,
                "map_points_stay_in_their_cells": True,
                **verified,
            },
            "files": [*files, preview_record, settings_record],
            "inputs": [
                {"path": record.path, "size": record.size, "sha256": record.sha256}
                for record in game_map.inputs
            ],
            "not_changed": list(UNCHANGED_INPUTS),
            "untested_engine_behaviors": list(UNTESTED),
        }
        manifest = {
            "schema": 1,
            "status": STATUS,
            "spec_sha256": report["spec_sha256"],
            "build": report["build"],
            "inputs": report["inputs"],
            "files": report["files"],
        }
        _ = write_bytes(stage, "manifest.json", canonical_json(manifest).encode())
        _ = write_bytes(stage, "report.json", canonical_json(report).encode())
        _ = write_bytes(stage, "report.md", render_report(report, seed, build_label).encode())
    return report


def render_report(report: dict[str, object], seed: int, build_label: str) -> str:
    """Human-readable summary of a candidate report."""
    lines = [
        f"# {report['mod']} — {STATUS}",
        "",
        (
            f"{report['tier']}. Target: {build_label}, map-contract fingerprint "
            f"`{cast('dict[str, object]', report['build'])['fingerprint_sha256']}`."
        ),
        "This package was generated and validated offline only. It has not been loaded in EU5.",
        "",
        "## Reproduce",
        "",
        "```sh",
        (
            f'uv run rnw generate --game-dir "$EU5_GAME_DIR" --seed {seed} '
            f"--settings generated/{report['mod']}/settings.json "
            "--output generated/rnw_exp_NEW_NAME"
        ),
        "```",
        "",
        (
            f"Run-spec SHA-256: `{report['spec_sha256']}` ({report['settings_source']}). "
            "The same seed, settings, generator version and build give identical pixels; "
            "PNG bytes are identical for the same zlib build."
        ),
        "",
        "## Changes and invariants",
        "",
        f"```json\n{json.dumps(report['changes'], indent=2, sort_keys=True)}\n```",
        "",
        f"```json\n{json.dumps(report['invariants'], indent=2, sort_keys=True)}\n```",
        "",
        "## Files",
        "",
        f"```json\n{json.dumps(report['files'], indent=2, sort_keys=True)}\n```",
        "",
        "## Not changed",
        "",
        *(f"- {item}" for item in UNCHANGED_INPUTS),
        "",
        "## Untested engine behaviour",
        "",
        *(f"- {item}" for item in UNTESTED),
        "",
    ]
    return "\n".join(lines)
