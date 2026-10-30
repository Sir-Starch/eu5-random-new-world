"""Versioned generator settings, presets and canonical JSON.

Every value is an integer (fractions are permille), so canonical JSON and generated
geometry contain no platform-dependent floating-point text. Changing output for the
same seed and settings requires a new product version (ADR 0003).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields, replace
from typing import TYPE_CHECKING, Final, cast

from rnw.epoch import CURRENT as ALGORITHM
from rnw.rng import RNG_VERSION, check_seed

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA_VERSION: Final[int] = 1
GENERATOR: Final[str] = "rnw-geo"
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
    # Gold, silver, gems and pearls against their vanilla frequency (1000: as in vanilla).
    precious_permille: int = 1000
    # 1: a fixed ocean sector; 0: the original distance band around vanilla America.
    expand_oceans: int = 1


@dataclass(frozen=True, slots=True)
class NativeSettings:
    """Controls for native societies of the New World (location counts are means)."""

    population_permille: int
    hearths_per_10k: int
    hearth_reach_steps: int
    state_share_permille: int
    state_locations: int
    culture_locations: int
    religion_locations: int
    tribe_locations: int
    organized_permille: int
    # Share of the state land given to lone states away from the hearths' clusters.
    state_spread_permille: int = 0
    # Chance, per hearth, that a great empire rises around it (EU4's fantasy native empires):
    # one state of many times the usual size with an advanced government. The same chance, per
    # hearth's domain, raises a sea league, a highland confederation, a fractured realm or a
    # sacred centre (R7d). 0: none of them.
    empire_permille: int = 0


@dataclass(frozen=True, slots=True)
class ResourceSettings:
    """Relative ordinary New World RGO weights, in permille of vanilla frequencies."""

    alum: int = 1000
    amber: int = 1000
    beeswax: int = 1000
    chili: int = 1000
    clay: int = 1000
    coal: int = 1000
    cocoa: int = 1000
    copper: int = 1000
    cotton: int = 1000
    dyes: int = 1000
    fiber_crops: int = 1000
    fish: int = 1000
    fruit: int = 1000
    fur: int = 1000
    incense: int = 1000
    iron: int = 1000
    ivory: int = 1000
    lead: int = 1000
    legumes: int = 1000
    livestock: int = 1000
    lumber: int = 1000
    maize: int = 1000
    marble: int = 1000
    medicaments: int = 1000
    mercury: int = 1000
    potato: int = 1000
    salt: int = 1000
    saltpeter: int = 1000
    sand: int = 1000
    stone: int = 1000
    tin: int = 1000
    tobacco: int = 1000
    wild_game: int = 1000
    wool: int = 1000


RESOURCES: Final[ResourceSettings] = ResourceSettings()
RESOURCE_FIELDS: Final[tuple[str, ...]] = tuple(item.name for item in fields(RESOURCES))


@dataclass(frozen=True, slots=True)
class RollSettings:
    """Rerolls of a part of a world on the same seed (``rnw.layers``): 0 is the seed's own."""

    resources: int = 0
    peoples: int = 0


ROLLS: Final[RollSettings] = RollSettings()


@dataclass(frozen=True, slots=True)
class MaskSettings:
    """The land drawn in an image instead of by the generator (``rnw.landmask``): the id of the
    image, 48 bits of the hash of what it draws, or 0 for land the generator makes itself. The
    image is not in the settings, only its id; the world's folder and a world file carry it."""

    id: int = 0


MASK: Final[MaskSettings] = MaskSettings()
NATIVES: Final[NativeSettings] = NativeSettings(
    population_permille=1000,
    hearths_per_10k=6,
    hearth_reach_steps=16,
    state_share_permille=110,
    state_locations=3,
    culture_locations=10,
    religion_locations=80,
    tribe_locations=6,
    organized_permille=450,
    # Vanilla 1337 America: 15 % of its states lie in small groups apart from the two great
    # centres (C117).
    state_spread_permille=150,
    # "Seldom" of the four levels the window offers (0, 250, 500, 800), as EU4's default of
    # its fantasy setting.
    empire_permille=250,
)


@dataclass(frozen=True, slots=True)
class Settings:
    """A complete settings document."""

    preset: str
    synthetic: SyntheticSettings
    geography: GeographySettings
    coast: CoastSettings
    new_world: NewWorldSettings
    natives: NativeSettings = NATIVES
    rolls: RollSettings = ROLLS
    mask: MaskSettings = MASK
    resources: ResourceSettings = RESOURCES

    def to_json_data(self) -> dict[str, object]:
        """Return the schema-tagged document; no rolls are written while all are 0, so that the
        document, and every digest of it, is what it was before rolls existed."""
        data = cast("dict[str, object]", asdict(self))
        coast = cast("dict[str, object]", data["coast"])
        coast["window"] = list(self.coast.window)
        if self.rolls == ROLLS:
            del data["rolls"]
        if self.mask == MASK:
            del data["mask"]
        if self.resources == RESOURCES:
            del data["resources"]
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
    "expand_oceans": (0, 1),
    "population_permille": (0, 5000),
    "hearths_per_10k": (0, 100),
    "hearth_reach_steps": (1, 100),
    "state_share_permille": (1, 1000),
    "state_locations": (1, 100),
    "culture_locations": (1, 1000),
    "religion_locations": (1, 10_000),
    "tribe_locations": (1, 100),
    "organized_permille": (0, 1000),
    "precious_permille": (0, 5000),
    "state_spread_permille": (0, 1000),
    "empire_permille": (0, 1000),
    "resources": (0, 65_535),
    "peoples": (0, 65_535),
    "id": (0, (1 << 48) - 1),
    **dict.fromkeys(RESOURCE_FIELDS, (0, 5000)),
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
            location_px=53,
            sea_zone_px=120,
            min_cell_px=300,
            min_sea_cell_px=2000,
            wasteland_permille=90,
            province_size=6,
            ocean_band_px=1600,
        ),
        natives=NATIVES,
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
        natives=replace(NATIVES, hearths_per_10k=8, religion_locations=60),
    ),
}
# More kinds of New World from the same model: its scale (``feature_px``), land share and
# smallest island decide whether the land joins into one mass or falls apart. Measured on
# seeds 42, 7 and 1000 (share of the land in masses of at least 3 %): continents 84-92 %
# in one mass with its isthmuses, like the Americas; supercontinent about 95 %; small
# continents three or four masses (48/35/12, 49/24/18, 44/22/17); archipelago five to eleven
# islands, the largest 21-42 %; islands six to twelve, the largest 13-25 % (C116).
PRESETS["supercontinent"] = replace(
    PRESETS["continents"],
    preset="supercontinent",
    new_world=replace(
        PRESETS["continents"].new_world,
        land_permille=540,
        feature_px=3600,
        persistence_permille=470,
        min_island_px=6000,
        # More land, so larger locations keep the map under the engine's location cap.
        location_px=61,
    ),
)
PRESETS["small_continents"] = replace(
    PRESETS["continents"],
    preset="small_continents",
    new_world=replace(
        PRESETS["continents"].new_world,
        land_permille=300,
        location_px=47,
        feature_px=1000,
        min_island_px=1200,
    ),
)
PRESETS["archipelago"] = replace(
    PRESETS["archipelago"],
    new_world=replace(PRESETS["archipelago"].new_world, land_permille=200, feature_px=420),
)
PRESETS["islands"] = replace(
    PRESETS["archipelago"],
    preset="islands",
    new_world=replace(
        PRESETS["archipelago"].new_world,
        land_permille=180,
        feature_px=300,
        octaves=6,
        persistence_permille=600,
        min_island_px=120,
    ),
    natives=replace(NATIVES, hearths_per_10k=10, religion_locations=50),
)
# English names, for a mod's metadata and the window's default text.
TITLES: Final[dict[str, str]] = {
    "supercontinent": "Supercontinent",
    "continents": "Continents",
    "small_continents": "Small continents",
    "archipelago": "Archipelago",
    "islands": "Scattered islands",
}
# The order in which the generator's window offers them.
WORLD_TYPES: Final[tuple[str, ...]] = (
    "supercontinent",
    "continents",
    "small_continents",
    "archipelago",
    "islands",
)


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


def _merge[
    T: (
        SyntheticSettings,
        GeographySettings,
        CoastSettings,
        NewWorldSettings,
        NativeSettings,
        RollSettings,
        MaskSettings,
        ResourceSettings,
    )
](base: T, section: str, override: object) -> T:
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
    unknown = sorted(
        set(data)
        - {"synthetic", "geography", "coast", "new_world", "natives", "rolls", "mask", "resources"}
    )
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
        natives=_merge(base.natives, "natives", data.get("natives", {})),
        rolls=_merge(base.rolls, "rolls", data.get("rolls", {})),
        mask=_merge(base.mask, "mask", data.get("mask", {})),
        resources=_merge(base.resources, "resources", data.get("resources", {})),
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
    """Everything that determines generated output apart from game input files.

    The algorithm epoch (``rnw.epoch``), not the release, so that a release that changes nothing a
    world is made of leaves the specification, and every digest of it, as it was."""
    return {
        "generator": GENERATOR,
        "algorithm": ALGORITHM,
        "rng": RNG_VERSION,
        "seed": check_seed(seed),
        "settings": settings.to_json_data(),
    }


def spec_digest(spec: dict[str, object]) -> str:
    """SHA-256 of a run specification's canonical JSON."""
    return hashlib.sha256(canonical_json(spec).encode("ascii")).hexdigest()
