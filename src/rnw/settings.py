"""Versioned generator settings, presets and canonical JSON.

Every value is an integer (fractions are permille), so canonical JSON and generated
geometry contain no platform-dependent floating-point text. Changing output for the
same seed and settings requires a new ``GENERATOR_VERSION``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields, replace
from typing import TYPE_CHECKING, Final, cast

from rnw.rng import RNG_VERSION, check_seed

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA_VERSION: Final[int] = 1
GENERATOR: Final[str] = "rnw-geo"
GENERATOR_VERSION: Final[str] = "0.5.0"
WINDOW_SIZE: Final[int] = 4


class SettingsError(ValueError):
    """Settings are unknown, mistyped or out of range."""


@dataclass(frozen=True, slots=True)
class SyntheticSettings:
    """Canvas of the committed synthetic fixture world."""

    width: int = 384
    height: int = 192
    old_world_columns: int = 96


@dataclass(frozen=True, slots=True)
class GeographySettings:
    """Shape controls for generating new land, sea and cells (T3-capable model)."""

    land_permille: int
    feature_px: int
    octaves: int
    persistence_permille: int
    coast_margin_px: int
    min_island_px: int
    min_lake_px: int
    location_px: int
    sea_zone_px: int
    min_cell_px: int
    group_size: int


@dataclass(frozen=True, slots=True)
class CoastSettings:
    """Controls for moving land-sea pixel boundaries between existing IDs (T2)."""

    window: tuple[int, int, int, int]
    feature_px: int
    octaves: int
    persistence_permille: int
    passes: int
    threshold_base_permille: int
    threshold_step_permille: int
    min_keep_permille: int
    max_growth_permille: int
    locator_radius_px: int
    river_radius_px: int
    border_px: int


@dataclass(frozen=True, slots=True)
class NewWorldSettings:
    """Controls for replacing the whole New World with generated cells (T3)."""

    land_permille: int
    feature_px: int
    octaves: int
    persistence_permille: int
    coast_margin_px: int
    min_island_px: int
    min_lake_px: int
    max_lake_px: int
    location_px: int
    sea_zone_px: int
    min_cell_px: int
    min_sea_cell_px: int
    wasteland_permille: int
    province_size: int
    ocean_band_px: int


@dataclass(frozen=True, slots=True)
class Settings:
    """A complete settings document."""

    preset: str
    synthetic: SyntheticSettings
    geography: GeographySettings
    coast: CoastSettings
    new_world: NewWorldSettings

    def to_json_data(self) -> dict[str, object]:
        """Return the schema-tagged document."""
        data = cast("dict[str, object]", asdict(self))
        coast = cast("dict[str, object]", data["coast"])
        coast["window"] = list(self.coast.window)
        return {"schema": SCHEMA_VERSION, **data}


EU5_WINDOW: Final[tuple[int, int, int, int]] = (3700, 1700, 4700, 2700)
RANGES: Final[dict[str, tuple[int, int]]] = {
    "width": (64, 4096),
    "height": (32, 4096),
    "old_world_columns": (16, 2048),
    "land_permille": (50, 800),
    "feature_px": (4, 4096),
    "octaves": (1, 8),
    "persistence_permille": (100, 900),
    "coast_margin_px": (2, 256),
    "min_island_px": (1, 100_000),
    "min_lake_px": (1, 100_000),
    "location_px": (3, 512),
    "sea_zone_px": (4, 2048),
    "min_cell_px": (1, 10_000),
    "group_size": (1, 64),
    "passes": (0, 64),
    "threshold_base_permille": (0, 1000),
    "threshold_step_permille": (0, 1000),
    "min_keep_permille": (100, 1000),
    "max_growth_permille": (1000, 10_000),
    "locator_radius_px": (0, 64),
    "river_radius_px": (0, 64),
    "border_px": (1, 64),
    "window": (0, 1 << 20),
    "min_sea_cell_px": (1, 100_000),
    "max_lake_px": (1, 1_000_000),
    "wasteland_permille": (0, 500),
    "province_size": (1, 32),
    "ocean_band_px": (0, 8192),
}
PRESETS: Final[dict[str, Settings]] = {
    "continents": Settings(
        preset="continents",
        synthetic=SyntheticSettings(),
        geography=GeographySettings(
            land_permille=420,
            feature_px=96,
            octaves=4,
            persistence_permille=450,
            coast_margin_px=6,
            min_island_px=24,
            min_lake_px=10,
            location_px=10,
            sea_zone_px=32,
            min_cell_px=6,
            group_size=4,
        ),
        coast=CoastSettings(
            window=EU5_WINDOW,
            feature_px=64,
            octaves=3,
            persistence_permille=450,
            passes=10,
            threshold_base_permille=40,
            threshold_step_permille=30,
            min_keep_permille=600,
            max_growth_permille=1600,
            locator_radius_px=3,
            river_radius_px=2,
            border_px=2,
        ),
        new_world=NewWorldSettings(
            land_permille=400,
            feature_px=1600,
            octaves=7,
            persistence_permille=520,
            coast_margin_px=48,
            min_island_px=600,
            min_lake_px=80,
            max_lake_px=4000,
            location_px=46,
            sea_zone_px=120,
            min_cell_px=300,
            min_sea_cell_px=2000,
            wasteland_permille=90,
            province_size=6,
            ocean_band_px=1600,
        ),
    ),
    "archipelago": Settings(
        preset="archipelago",
        synthetic=SyntheticSettings(),
        geography=GeographySettings(
            land_permille=260,
            feature_px=28,
            octaves=4,
            persistence_permille=600,
            coast_margin_px=6,
            min_island_px=6,
            min_lake_px=10,
            location_px=9,
            sea_zone_px=28,
            min_cell_px=4,
            group_size=4,
        ),
        coast=CoastSettings(
            window=EU5_WINDOW,
            feature_px=20,
            octaves=3,
            persistence_permille=650,
            passes=14,
            threshold_base_permille=30,
            threshold_step_permille=22,
            min_keep_permille=500,
            max_growth_permille=2000,
            locator_radius_px=3,
            river_radius_px=2,
            border_px=2,
        ),
        new_world=NewWorldSettings(
            land_permille=300,
            feature_px=520,
            octaves=7,
            persistence_permille=580,
            coast_margin_px=48,
            min_island_px=250,
            min_lake_px=80,
            max_lake_px=4000,
            location_px=46,
            sea_zone_px=120,
            min_cell_px=300,
            min_sea_cell_px=2000,
            wasteland_permille=90,
            province_size=6,
            ocean_band_px=1600,
        ),
    ),
}


def _checked_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        message = f"Setting {name} must be an integer"
        raise SettingsError(message)
    low, high = RANGES[name]
    if not low <= value <= high:
        message = f"Setting {name} must be in [{low}, {high}]: {value}"
        raise SettingsError(message)
    return value


def _checked_window(value: object) -> tuple[int, int, int, int]:
    if not isinstance(value, list | tuple):
        message = "Setting window must be a list of four integers"
        raise SettingsError(message)
    items = [_checked_int("window", item) for item in cast("list[object]", value)]
    if len(items) != WINDOW_SIZE or items[0] >= items[2] or items[1] >= items[3]:
        message = "Setting window must be [x0, y0, x1, y1] with x0 < x1 and y0 < y1"
        raise SettingsError(message)
    return (items[0], items[1], items[2], items[3])


def _merge[T: (SyntheticSettings, GeographySettings, CoastSettings, NewWorldSettings)](
    base: T, section: str, override: object
) -> T:
    if not isinstance(override, dict):
        message = f"Settings section {section} must be an object"
        raise SettingsError(message)
    values = cast("dict[str, object]", override)
    known = {item.name for item in fields(base)}
    unknown = sorted(set(values) - known)
    if unknown:
        message = f"Unknown {section} settings: {', '.join(unknown)}"
        raise SettingsError(message)
    changes: dict[str, object] = {
        name: _checked_window(value) if name == "window" else _checked_int(name, value)
        for name, value in sorted(values.items())
    }
    return replace(base, **changes)


def build_settings(preset: str, overrides: dict[str, object] | None = None) -> Settings:
    """Apply a JSON-like override object to a named preset and validate it."""
    data = dict(overrides or {})
    schema = data.pop("schema", SCHEMA_VERSION)
    if schema != SCHEMA_VERSION:
        message = f"Unsupported settings schema: {schema}"
        raise SettingsError(message)
    name = data.pop("preset", preset)
    if not isinstance(name, str) or name not in PRESETS:
        message = f"Unknown preset: {name}; choose one of {', '.join(sorted(PRESETS))}"
        raise SettingsError(message)
    base = PRESETS[name]
    unknown = sorted(set(data) - {"synthetic", "geography", "coast", "new_world"})
    if unknown:
        message = f"Unknown settings sections: {', '.join(unknown)}"
        raise SettingsError(message)
    synthetic = _merge(base.synthetic, "synthetic", data.get("synthetic", {}))
    if synthetic.old_world_columns * 2 > synthetic.width:
        message = "Setting old_world_columns must leave at least half of the canvas"
        raise SettingsError(message)
    return Settings(
        preset=name,
        synthetic=synthetic,
        geography=_merge(base.geography, "geography", data.get("geography", {})),
        coast=_merge(base.coast, "coast", data.get("coast", {})),
        new_world=_merge(base.new_world, "new_world", data.get("new_world", {})),
    )


def load_settings(preset: str, path: Path | None) -> Settings:
    """Load an optional UTF-8 JSON override file on top of a preset."""
    if path is None:
        return build_settings(preset)
    loaded = cast("object", json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(loaded, dict):
        message = "Settings file must contain a JSON object"
        raise SettingsError(message)
    return build_settings(preset, cast("dict[str, object]", loaded))


def canonical_json(data: object) -> str:
    """Serialize with sorted keys, compact separators, ASCII and a final LF."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def run_spec(seed: int, settings: Settings) -> dict[str, object]:
    """Everything that determines generated output apart from game input files."""
    return {
        "generator": GENERATOR,
        "generator_version": GENERATOR_VERSION,
        "rng": RNG_VERSION,
        "seed": check_seed(seed),
        "settings": settings.to_json_data(),
    }


def spec_digest(spec: dict[str, object]) -> str:
    """SHA-256 of a run specification's canonical JSON."""
    return hashlib.sha256(canonical_json(spec).encode("ascii")).hexdigest()
