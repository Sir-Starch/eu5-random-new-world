"""The societies-only export on the vanilla Americas (ADR 0012, phase V2).

A world that keeps the geography generates no land. The cells are the installed game's own locations
(``rnw.vanilla_world``), and what is generated is what stands on them: the peoples, their states,
cultures and religions, the 1037-1337 history, the start's development, the AI, the stories and the
formations, by the same stages as every world. Vanilla's own American setup is removed and
replaced, and the scripts that name a removed country are remapped or retired as in every world.

The mod holds no physical file: no ``locations.png``, ``rivers.png``, terrain, vegetation, water,
``definitions.txt``, ``default.map``, templates, ports, adjacencies or locators. Places keep the
game's names, so the generator's place names are replaced by references to the game's own texts.
"""

# NumPy stubs type array comparisons, shapes and tolist() as Any.
# pyright: reportAny=false, reportPrivateUsage=false
# ruff: noqa: SLF001

from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING, Final

import numpy as np

from rnw import (
    __version__,
    eu5_history_text,
    inputs,
    landcache,
    text_references,
    wording,
    worldname,
)
from rnw import eu5_nw_export as nw
from rnw.app.gamenames import game_names
from rnw.app.worldcode import WorldCodeError, decode
from rnw.artifacts import check_new_output, staged, write_bytes
from rnw.atlas import JSON_FILE as ATLAS_JSON
from rnw.atlas import LABELS_FILE as ATLAS_LABELS
from rnw.atlas import to_files as atlas_files
from rnw.content_check import check_decisions, check_outcomes
from rnw.eu5_ai import PERSONALITIES
from rnw.eu5_ai import assignments as ai_assignments
from rnw.eu5_ai import lines as ai_personality_lines
from rnw.eu5_archetypes import alliance_lines, confederation_lines, rival_lines
from rnw.eu5_atlas import build_atlas
from rnw.eu5_biomes import template_attributes
from rnw.eu5_canvas import NEW_WORLD, Canvas
from rnw.eu5_content import TENOCHTITLAN, ContentError, carry_out, cohort_places
from rnw.eu5_development import (
    Development,
    DevelopmentCalibration,
    build_development,
    building_lines,
    development_lines,
    development_rules,
    river_sizes,
    shelter,
)
from rnw.eu5_empires import opinion_lines, road_lines
from rnw.eu5_export import MOD_NAME, STATUS, resolve_build
from rnw.eu5_history_build import build_history_start
from rnw.eu5_islands import moved_pixels_of
from rnw.eu5_map import DEFINITIONS, PORTS, load_map
from rnw.eu5_natives import (
    DEFINITION_FILE,
    city_lines,
    country_definitions,
    country_names,
    country_records,
    holy_site_outputs,
    market_lines,
    pop_lines,
    vanilla_natives,
    vassal_lines,
)
from rnw.eu5_newworld import vanilla_geometry
from rnw.eu5_remap import GeographicRemap, remap_scripts
from rnw.eu5_rewrite import drop_block_entries, prune_setup
from rnw.eu5_seas import read_ports
from rnw.eu5_terrain import ShiftedStore
from rnw.eu5_towns import plan_towns
from rnw.export_stages import SKIPPED
from rnw.game_texts import localize, untranslated
from rnw.geography import read_locations
from rnw.history_output_checks import verify_diplomacy
from rnw.history_output_checks import verify_text as verify_history_text
from rnw.languages import official_languages
from rnw.layers import PEOPLES, layer_seed
from rnw.loc_keys import KeySpace, key_hashes
from rnw.model import CellClass
from rnw.parallel import collector_paused, configure, require_memory
from rnw.pdx import parse
from rnw.pictures import center_column, tagged, thumbnail
from rnw.progress import active, checkpoint, run_stage, running, skip_stages
from rnw.settings import canonical_json, run_spec, spec_digest
from rnw.vanilla_world import VanillaWorld, build

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

    from rnw.eu5_map import Eu5Map
    from rnw.eu5_newworld import Plan
    from rnw.eu5_start import FinalStartPlan
    from rnw.geography import Location
    from rnw.progress import Progress
    from rnw.settings import Settings
    from rnw.worldname import Label

TIER: Final[str] = "Native societies on the vanilla Americas, no generated geography"


def export_vanilla_world(  # noqa: PLR0913 - the CLI contract names each input.
    game_dir: Path,
    output: Path,
    *,
    seed: int,
    settings: Settings,
    accept_build: str | None = None,
    settings_file: str | None = None,
    replace: bool = False,
    check_memory: bool = True,
    progress: Progress | None = None,
    world_code: str | None = None,
    world_label: Label | None = None,
    cache_dir: Path | None = None,
) -> dict[str, object]:
    """Generate, validate and stage one societies-only mod bundle; return its report."""
    check_new_output(output, MOD_NAME, game_dir, replace=replace)
    if check_memory:
        require_memory(nw.EXPORT_MEMORY, "The export on the vanilla Americas")
    with active(progress), collector_paused(), inputs.recording(game_dir) as recorder:
        return _export(
            recorder,
            game_dir,
            output,
            seed=seed,
            settings=settings,
            accept_build=accept_build,
            settings_file=settings_file,
            world_code=world_code,
            world_label=world_label,
            cache_dir=cache_dir,
        )


def _american_keys(hierarchy: dict[str, Location]) -> tuple[set[str], set[str]]:
    """What a world replaces in the setup (every American location and province, as the footprint of
    the game's content is read) and the keys whose development entries it drops (those and the
    areas and regions, as ``vanilla_new_world_keys`` finds them)."""
    americas = [location for location in hierarchy.values() if location.continent == NEW_WORLD]
    gone = {name for location in americas for name in (location.key, location.province)}
    dropped = gone | {name for location in americas for name in (location.area, location.region)}
    return gone, dropped


def _named_keys(vanilla: VanillaWorld) -> set[str]:
    """The places, areas and regions that a world's texts name."""
    wanted: set[str] = set()
    for cell in vanilla.plan.cells:
        if cell.kind in {CellClass.LAND, CellClass.WASTELAND}:
            wanted.update((cell.key, cell.area, cell.region))
    return wanted


def _reference_names(vanilla: VanillaWorld, texts: set[str]) -> dict[str, wording.Name]:
    """The game's own names of the places, areas and regions, as references to its texts."""
    return {key: wording.reference(key) for key in sorted(_named_keys(vanilla) & texts)}


def _word_names(game_dir: Path, vanilla: VanillaWorld) -> dict[str, wording.Name]:
    """The same names as plain English words, for the formations that are named after a place."""
    found = game_names(game_dir, "english", frozenset(_named_keys(vanilla)))
    return dict(sorted(found.items()))


def _docks(game_dir: Path, vanilla: VanillaWorld, height: int) -> dict[int, tuple[int, int]]:
    """The dock of each land cell that the game gives a port: (row, column) on the map."""
    ports = read_ports(nw._read(game_dir, PORTS))
    positions: dict[int, tuple[int, int]] = {}
    for index, cell in enumerate(vanilla.plan.cells):
        port = ports.get(cell.key)
        if port is not None and cell.kind is CellClass.LAND:
            positions[index] = (height - 1 - round(float(port.y)), round(float(port.x)))
    return positions


def _plan_development(  # noqa: PLR0913 - development reads the calibration, map, world and docks.
    calibration: DevelopmentCalibration,
    *,
    game_map: Eu5Map,
    vanilla: VanillaWorld,
    natives: FinalStartPlan,
    docks: dict[int, tuple[int, int]],
    rivers: NDArray[np.uint8],
) -> Development:
    """The start's development on the game's own coasts and rivers."""
    wet = {CellClass.SEA, CellClass.LAKE}
    table = np.array([kind in wet for kind in game_map.classes], dtype=bool)
    cells = sorted(docks)
    scores = shelter(
        table[game_map.labels], np.array([docks[cell] for cell in cells], dtype=np.int64)
    )
    sizes = river_sizes(
        vanilla.world.labels,
        rivers,
        len(vanilla.world.classes) + 1,
        sizes=nw.RIVER_SIZES,
    )
    plan = vanilla.plan
    cell_fields = [
        (
            cell.key,
            vanilla.biomes.vegetation[i],
            vanilla.biomes.climate[i],
            vanilla.biomes.topography[i],
            int(sizes[i]),
        )
        for i, cell in enumerate(plan.cells)
        if cell.kind is CellClass.LAND
    ]
    return build_development(
        calibration=calibration,
        natives=natives,
        cells=cell_fields,
        scores={
            plan.cells[cell].key: score for cell, score in zip(cells, scores.tolist(), strict=True)
        },
    )


def _society_texts(  # noqa: PLR0913 - every rewritten society file needs the shared plan.
    game_dir: Path,
    *,
    vanilla: VanillaWorld,
    natives: FinalStartPlan,
    development: Development,
    loc_keys: KeySpace,
    gone: set[str],
    american: set[str],
) -> tuple[dict[str, bytes], dict[str, object]]:
    """The setup, definitions, history and localization of the start, and their statistics."""
    plan = vanilla.plan
    world = vanilla.world
    outputs: dict[str, bytes] = {}
    history_text = (
        eu5_history_text.build(natives, loc_keys, tuple(cell.key for cell in plan.cells))
        if natives.history is not None
        else None
    )
    if history_text is not None:
        verify_history_text(natives, history_text)
        outputs.update(history_text.files)
    written_pops = pop_lines(natives.pops)
    holders = [
        cell.key for cell in plan.cells if cell.kind in {CellClass.LAND, CellClass.WASTELAND}
    ]
    setup = prune_setup(
        dict(nw._setup_texts(game_dir)), gone, {k: written_pops.get(k, []) for k in holders}
    )
    towns = plan_towns(game_dir, natives.ranks, development.initial, natives.population)
    ai_decisions = nw._ai_assignment_records(game_dir, natives, world, plan)
    ai_records = ai_assignments(ai_decisions)
    additions: dict[str, tuple[str, ...]] = {
        nw.COUNTRIES_FILE: (country_records(natives.countries),),
        PERSONALITIES: (ai_personality_lines(ai_records),),
        nw.BUILDINGS_FILE: (
            city_lines(towns.ranks),
            building_lines(development.villages),
        ),
        "03_markets.txt": (market_lines(natives.markets),),
        "09_roads.txt": (road_lines(natives.roads),),
        "12_diplomacy.txt": (
            vassal_lines(natives.vassals) + eu5_history_text.guarantee_lines(natives.protections),
            alliance_lines(natives.alliances),
        ),
        "15_international_organizations.txt": (
            confederation_lines(natives.confederation_date, natives.confederations),
        ),
        nw.DEVELOPMENT_FILE: (development_lines(development.terms),),
        "18_opinions.txt": (opinion_lines(natives.opinions),),
        "20_rivals.txt": (rival_lines(natives.rivals),),
    }
    for name, original_text in setup.texts.items():
        relative = f"{nw.SETUP_DIR}/{name}"
        setup_text = original_text
        if name == nw.DEVELOPMENT_FILE:
            setup_text = drop_block_entries(setup_text, ("development",), american)
        setup_text = nw._insert_setup_additions(name, setup_text, additions, ai_records)
        if name == "12_diplomacy.txt" and natives.history is not None:
            verify_diplomacy(
                natives, setup_text, nw._read(game_dir, relative), gone | setup.removed_ids
            )
        if setup_text != nw._read(game_dir, relative):
            outputs[nw._mod_path(relative)] = nw._encode(game_dir, relative, setup_text)
    outputs.update(nw.country_definition_outputs(game_dir, setup.removed_ids))
    outputs.update(towns.files())
    outputs[DEFINITION_FILE] = country_definitions(natives.countries)
    languages = official_languages(game_dir)
    extra = {
        **country_names(natives.countries),
        **(history_text.texts if history_text is not None else {}),
    }
    for language in languages:
        outputs[f"main_menu/localization/{language}/rnw_new_world_l_{language}.yml"] = nw._yaml(
            language, localize(extra, language)
        )
    stats: dict[str, object] = {
        "starting_towns": {
            "adjusted_locations": towns.adjusted_locations,
            "derived_templates": len(towns.definitions),
        },
        "setup_records_deleted": {k: v for k, v in setup.deleted.items() if v},
        "setup_identifiers_removed": len(setup.removed_ids),
        "ai_personalities": dict(sorted(Counter(profile for _, profile in ai_records).items())),
        "languages": list(languages),
        "untranslated_languages": untranslated(languages),
    }
    return outputs, stats


def _export(  # noqa: PLR0913, PLR0915 - one pass over every stage of the export.
    recorder: inputs.InputRecorder,
    game_dir: Path,
    output: Path,
    *,
    seed: int,
    settings: Settings,
    accept_build: str | None,
    settings_file: str | None,
    world_code: str | None,
    world_label: Label | None,
    cache_dir: Path | None,
) -> dict[str, object]:
    _ = configure()
    skip_stages(*SKIPPED)
    digest, build_label, accepted = resolve_build(game_dir, accept_build)
    spec = run_spec(seed, settings)
    peoples_seed = layer_seed(seed, PEOPLES, settings.rolls.peoples)
    origin = ""
    try:
        origin = decode(world_code or "").origin
    except WorldCodeError:
        origin = ""
    named = world_label or worldname.label(
        settings.preset,
        worldname.fallback_tag(world_code or spec_digest(spec)),
        settings=settings,
        origin=origin,
    )

    def load() -> tuple[Eu5Map, dict[str, Location]]:
        loaded = load_map(game_dir)
        return loaded, {
            location.key: location for location in read_locations(game_dir / DEFINITIONS)
        }

    game_map, hierarchy = run_stage("load map", load)
    canvas = run_stage(
        "select canvas",
        lambda: landcache.get_canvas(
            cache_dir, game_map, settings.new_world.ocean_band_px, expanded=False
        ),
    )
    attributes = template_attributes(nw._read(game_dir, nw.TEMPLATES))
    height, width = (int(size) for size in game_map.labels.shape)
    store = ShiftedStore(game_dir, (height, width), moved_pixels_of(canvas))
    heights = store.world_heights()
    vanilla = run_stage(
        "vanilla Americas", lambda: build(game_map, hierarchy, attributes, canvas, height=heights)
    )
    plan = vanilla.plan
    del store
    calibration = nw.calibrate_development(game_dir, game_map, hierarchy)
    geometry = vanilla_geometry(game_map, canvas, hierarchy)
    calibrated = run_stage(
        "vanilla natives",
        lambda: vanilla_natives(game_dir, game_map, geometry, attributes, hierarchy),
    )
    texts_known = nw.vanilla_localization_keys(game_dir)
    loc_keys = KeySpace(key_hashes(texts_known) | nw.static_hashes())
    natives = run_stage(
        "natives",
        lambda: build_history_start(
            world=vanilla.world,
            plan=plan,
            biomes=vanilla.biomes,
            river_pixels=vanilla.river_pixels,
            vanilla=calibrated,
            settings=settings.natives,
            seed=peoples_seed,
            loc_keys=loc_keys,
        ),
    )
    # Places keep the game's names: every name the generator drew is the game's own text.
    natives = replace(natives, names=_reference_names(vanilla, texts_known))
    checkpoint()
    crop_rivers = np.where(canvas.mask, _crop(canvas, game_map.rivers), 255).astype(np.uint8)
    development = _plan_development(
        calibration,
        game_map=game_map,
        vanilla=vanilla,
        natives=natives,
        docks=_docks(game_dir, vanilla, height),
        rivers=crop_rivers,
    )
    atlas_json, atlas_png = run_stage(
        "atlas",
        lambda: atlas_files(
            build_atlas(
                world=vanilla.world,
                plan=plan,
                biomes=vanilla.biomes,
                natives=natives,
                mask=canvas.mask,
                development=development.initial,
            )
        ),
    )
    gone, american = _american_keys(hierarchy)
    texts, text_stats = run_stage(
        "texts",
        lambda: _society_texts(
            game_dir,
            vanilla=vanilla,
            natives=natives,
            development=development,
            loc_keys=loc_keys,
            gone=gone,
            american=american,
        ),
    )
    # A formation is named after a place by its word, which a reference to a text is not.
    spoken = replace(natives, names=_word_names(game_dir, vanilla))
    written = run_stage(
        "stories",
        lambda: nw._story_outputs(
            game_dir,
            plan=plan,
            world=vanilla.world,
            natives=spoken,
            river_pixels=vanilla.river_pixels,
            topography=vanilla.biomes.topography,
            vanilla=calibrated,
            loc_keys=loc_keys,
            seed=peoples_seed,
        ),
    )
    texts.update(written.files)
    text_stats["stories"] = written.stats
    checkpoint()
    vanilla_hashes = key_hashes(texts_known)
    definitions = (game_dir / DEFINITIONS).read_bytes()
    if settings.new_world.reveal_at_start:
        shown = {**texts, nw._mod_path(DEFINITIONS): definitions}
        text_stats.update(nw._add_reveal(shown, enabled=True))
        texts.update({k: v for k, v in shown.items() if k != nw._mod_path(DEFINITIONS)})
    text_checks: dict[str, object] = {}
    text_checks.update(nw._verify_natives(natives, plan))
    text_checks.update(nw.verify_technology(texts, natives, calibrated))
    text_checks.update(
        _verify_development(texts, plan, natives, development, calibration, american)
    )
    removed_tags = nw._defined_tags(game_dir, {}) - nw._defined_tags(game_dir, texts)
    originals = {
        name: nw._read(game_dir, f"{nw.SETUP_DIR}/{name}")
        for name in ("09_roads.txt", "18_opinions.txt")
    }
    text_checks.update(
        nw.verify_empires(
            texts, natives, plan, vanilla.world, calibrated, originals, american | removed_tags
        )
    )
    text_checks.update(
        nw.verify_archetypes(
            texts,
            natives,
            plan,
            calibrated,
            {name: nw._read(game_dir, f"{nw.SETUP_DIR}/{name}") for name in nw.ARCHETYPE_FILES},
            american | removed_tags,
        )
    )
    # No vanilla location is replaced, so no script's place is bound to another and nothing the
    # map holds (monuments, illustrations, dynamic objects) is dropped: the remap of the scripts is
    # empty. The seat of the game's start and the holy sites that follow the peoples stand for
    # themselves (``rnw.eu5_content``, ``holy_site_outputs``).
    nowhere = GeographicRemap({}, {}, {})
    seat = GeographicRemap({TENOCHTITLAN: TENOCHTITLAN}, {}, {})
    sites = GeographicRemap({key: key for key in natives.holy_sites}, {}, {})
    rewrite = run_stage("script remap", lambda: remap_scripts(game_dir, nowhere, removed_tags))
    try:
        checked = check_decisions(
            game_dir,
            events=[event for found in rewrite.retired.values() for event in found],
            modifiers=list(rewrite.modifiers),
            removed_tags=removed_tags,
        )
    except ValueError as error:
        raise nw.NewWorldExportError(str(error)) from error
    text_checks.update(checked.stats())
    scripts = rewrite.outputs
    scripts.update(holy_site_outputs(game_dir, sites, natives.holy_sites))
    unchanged = [
        path
        for path, data in scripts.items()
        if (game_dir / "game" / path).is_file() and (game_dir / "game" / path).read_bytes() == data
    ]
    for path in unchanged:
        del scripts[path]
    try:
        text_stats["content"] = carry_out(
            game_dir,
            scripts,
            checked,
            cohort_places(natives.pops),
            hierarchy,
            seat,
            sea_areas=sorted(
                {
                    cell.area
                    for cell in plan.cells
                    if cell.kind is CellClass.SEA and cell.continent == NEW_WORLD
                }
            ),
        )
        text_stats["script_outcomes"] = check_outcomes(
            game_dir, scripts, checked, _present_keys(hierarchy)
        )
    except (ValueError, ContentError) as error:
        raise nw.NewWorldExportError(str(error)) from error
    texts.update(scripts)
    checkpoint()
    text_checks.update(nw.verify_country_tags(game_dir, texts))
    text_checks.update(nw.verify_localization(texts, vanilla_hashes, game_dir=game_dir))
    try:
        text_checks.update(text_references.verify(texts, vanilla_hashes))
    except text_references.TextReferenceError as error:
        raise nw.NewWorldExportError(str(error)) from error
    text_stats["scripts_remapped"] = rewrite.remapped
    text_stats["illustrations_dropped"] = rewrite.illustrations
    text_stats["monuments_dropped"] = rewrite.monuments
    text_stats["events_retired"] = {path: len(ids) for path, ids in rewrite.retired.items()}
    text_stats["event_modifiers_retired"] = list(rewrite.modifiers)
    # The pictures draw the game's few non-ownable locations (lakes of the Arctic) as wasteland.
    drawn = replace(
        vanilla.world,
        classes=tuple(
            CellClass.WASTELAND if kind is CellClass.NON_OWNABLE else kind
            for kind in vanilla.world.classes
        ),
    )
    revealed, hidden = nw._previews(game_map, canvas, drawn, canvas.mask)
    name = output.name
    with running("write files"), staged(output) as stage:
        files: list[dict[str, object]] = [
            write_bytes(stage, f"{name}/{relative}", data)
            for relative, data in sorted(texts.items())
        ]
        files.append(
            write_bytes(
                stage, f"{name}/.metadata/metadata.json", _metadata(name, named.title, world_code)
            )
        )
        files.append(
            write_bytes(
                stage,
                f"{name}/.metadata/thumbnail.png",
                nw._preview(tagged(thumbnail(hidden, center_column(hidden)), named.tag)),
            )
        )
        preview_record = write_bytes(stage, "preview.png", nw._preview(revealed))
        hidden_record = write_bytes(stage, "preview_hidden.png", nw._preview(hidden))
        settings_record = write_bytes(
            stage, "settings.json", canonical_json(spec["settings"]).encode()
        )
        atlas_records = [
            write_bytes(stage, ATLAS_JSON, atlas_json),
            write_bytes(stage, ATLAS_LABELS, atlas_png),
        ]
        record, inputs_record = nw._reproducibility(
            stage,
            recorder,
            game_dir,
            files,
            mod=name,
            seed=seed,
            settings=settings,
            spec=spec,
            game=(digest, build_label),
            world_code=world_code,
        )
        kinds = [cell.kind for cell in plan.cells]
        report: dict[str, object] = {
            "schema": 1,
            "status": STATUS,
            "tier": TIER,
            "mod": name,
            "title": named.title,
            "land_mask": None,
            "spec": spec,
            "spec_sha256": spec_digest(spec),
            "record": record.to_json(),
            "settings_source": settings_file or f"preset {settings.preset}",
            "build": {"fingerprint_sha256": digest, "label": build_label, "explicit": accepted},
            "canvas": {
                "pixels": int(np.count_nonzero(canvas.mask)),
                "removed_vanilla_locations": 0,
                "changed_pixels_on_disk": 0,
            },
            "generated": {
                "locations": sum(kind is CellClass.LAND for kind in kinds),
                "wastelands": sum(kind is CellClass.WASTELAND for kind in kinds),
                "sea_zones": sum(kind is CellClass.SEA for kind in kinds),
                "lakes": sum(kind is CellClass.LAKE for kind in kinds),
                "geography": "the installed game's own",
            },
            "invariants": {**text_checks},
            "text_stats": text_stats,
            "natives": natives.stats,
            "technology": natives.technology,
            "extraordinary": natives.extraordinary,
            "archetypes": natives.archetypes,
            "development": development.stats,
            "files": [
                *files,
                preview_record,
                hidden_record,
                settings_record,
                inputs_record,
                *atlas_records,
            ],
            "inputs": [
                {"path": record.path, "size": record.size, "sha256": record.sha256}
                for record in game_map.inputs
            ],
            "untested_engine_behaviors": list(nw.UNTESTED),
        }
        manifest = {
            key: report[key]
            for key in ("schema", "status", "spec_sha256", "record", "build", "inputs", "files")
        }
        _ = write_bytes(stage, "manifest.json", canonical_json(manifest).encode())
        _ = write_bytes(stage, "report.json", canonical_json(report).encode())
    return report


def _present_keys(hierarchy: dict[str, Location]) -> dict[str, frozenset[str]]:
    """The map keys of each kind that the installed game defines."""
    return {
        "location": frozenset(location.key for location in hierarchy.values()),
        "province": frozenset(location.province for location in hierarchy.values()),
        "area": frozenset(location.area for location in hierarchy.values()),
        "region": frozenset(location.region for location in hierarchy.values()),
        "subcontinent": frozenset(location.subcontinent for location in hierarchy.values()),
    }


def _verify_development(  # noqa: PLR0913, PLR0917 - every development record is checked.
    texts: dict[str, bytes],
    plan: Plan,
    natives: FinalStartPlan,
    development: Development,
    calibration: DevelopmentCalibration,
    american: set[str],
) -> dict[str, object]:
    """No positional development of the Americas is left but the plan's; villages are as planned."""
    rules_text = texts[nw._mod_path(f"{nw.SETUP_DIR}/{nw.DEVELOPMENT_FILE}")].decode("utf-8-sig")
    block = parse(rules_text).block("development")
    if block is None:
        message = "No development block in the output"
        raise nw.NewWorldExportError(message)
    ours = {cell.key for cell in plan.cells}
    kept = sorted(
        entry.key for entry in block.entries if entry.key in american and entry.key not in ours
    )
    if kept:
        message = f"Development entry {kept[0]} of the vanilla Americas was kept"
        raise nw.NewWorldExportError(message)
    old = {key: value for key, value in calibration.rules.items() if key not in american}
    if {k: v for k, v in development_rules(rules_text).items() if k not in ours} != old:
        message = "Development rules outside the Americas differ from vanilla"
        raise nw.NewWorldExportError(message)
    found = nw._verify_terms(block, plan, development, calibration)
    manager = parse(
        texts[nw._mod_path(f"{nw.SETUP_DIR}/{nw.BUILDINGS_FILE}")].decode("utf-8-sig")
    ).block("building_manager")
    villages = nw._verify_villages(manager, natives, development)
    return {"development_entries": len(found), "market_villages": len(villages)}


def _metadata(name: str, title: str, world_code: str | None) -> bytes:
    """The mod's metadata: native societies on the original map, and how to make them again."""
    code = f" World code: {world_code}." if world_code else ""
    payload: dict[str, object] = {
        "name": title,
        "id": name,
        "version": __version__,
        "supported_game_version": nw.SUPPORTED_GAME,
        "short_description": (
            "Generated native societies on the original Americas, made with Random New World "
            f"Generator.{code} Play this on its own; get the generator on Steam Workshop to "
            "create your own worlds."
        ),
        "tags": ["Map"],
        "picture": "thumbnail.png",
        "relationships": [],
        "game_custom_data": {},
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8-sig")


def _crop(canvas: Canvas, raster: NDArray[np.uint8]) -> NDArray[np.uint8]:
    return np.roll(raster, canvas.roll, axis=1)[:, canvas.col0 : canvas.col0 + canvas.mask.shape[1]]
