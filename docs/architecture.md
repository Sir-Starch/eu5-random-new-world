# Current architecture

RNW 1.0.0 is an external Python/Rust generator with a desktop application: a Tauri window (Svelte/TypeScript and a Rust shell) and the classic Qt window as its fallback.
It reads the player's EU5 installation and emits one self-contained local world
mod. The Old World is preserved. Free-topology New World generation, native
societies and campaign content are implemented; the early T0–T5 research matrix
is [historical](archive/feasibility-1.4.1.md), not the current capability verdict.
Owner acceptance and released packages are recorded in C437–C439, C441.

## Pipeline and boundaries

```text
settings + seed/rolls + installed game inputs
  → physical geography and connected location hierarchy
  → resources, ordinary societies and 1037–1337 causal history
  → final start plan and campaign content
  → validators and EU5 serializers
  → local world mod + reproducibility record + atlas/library metadata
  → optional verified installation into the user's profile
```

The public hub contains the generator only. Its permanent ID is
`sirstarch.randomnewworld`; the maintained local folder is `rnw_exp_hub`.
The player enables one generated `rnw_exp_world_*` mod. Gameplay never depends
on keeping the hub enabled. The generator does not modify the game installation.
[ADR 0009](adr/0009-hub-mod-with-generator.md) defines delivery;
[ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md) defines layers,
world files and reproducibility.

The application/library/viewer are independent of the game adapters. Viewing a
compact world file does not need EU5. Generating a built world does: map inputs,
calibration, scripts, localization and optional covers are read locally. Derived
worlds are not shipped in the repository, GitHub release or Workshop hub.

## Module map

Paths below are relative to `src/rnw/` unless stated otherwise.

| Responsibility | Modules |
|---|---|
| Installation inspection and compatibility | `geography.py`, `contract.py`, `inputs.py`, `eu5_map.py`; fingerprint and record the installed inputs |
| Settings, deterministic streams and abstract topology | `settings.py`, `rng.py`, `noise.py`, `model.py`, `topology.py`, `synth.py`, `coast.py`, `validate.py` |
| Generated New World and fields | `newworld.py`, `islands.py`, `wall.py`, `fields.py`, `relief.py`, `climate.py`, `rivers.py`, `lakes.py`, `gulfs.py`, `isthmuses.py`, `hierarchy.py`; `landcache.py` keeps made land in the data folder (finished continents for rerolls, the land of sketched continents for the world made from one, the map's canvas), keyed by every input and the generator's own code, and bounded |
| Terrain serialization | `eu5_biomes.py`, `eu5_slots.py`, `eu5_terrain.py`, `eu5_mountains.py`, `eu5_objects.py`, `eu5_water.py`; `terrain_tiles.py`, `lzav.py`, `dds.py`, `png.py` |
| Seas, routes and currents | `ports.py`, `seas.py`, `seanames.py`, `lanes.py`, `sea_corridors.py`, `sea_policy.py`, `straits.py`, `crossings.py`, `currents.py`; `eu5_oceans.py`, `eu5_seas.py` |
| Native societies and start state | `societies.py`, `eu5_natives.py` (construction/writers), `eu5_start.py` (`FinalStartPlan`, countries and typed pop cohorts shared by writers, verifiers, AI, content and atlas), `eu5_ai.py`, `eu5_development.py`, `eu5_technology.py`, `eu5_empires.py`, `archetypes.py`, `eu5_archetypes.py` |
| History and societies (H2–H4, normal generation) | `history_model.py`, `history_checks.py`, `history_context.py`, `history_actions.py`, `history_societies.py`, `history_trajectories.py`, `history_engine.py`; `eu5_history_build.py` bridges physical bootstrap (`history_routes.py`, `eu5_history.py`), population (`history_population.py`) and final projection (`eu5_history_plan.py`, `eu5_history_values.py`, `history_diplomacy.py`, `history_plan_checks.py`); `history_text.py`, `eu5_history_text.py`, `history_output_checks.py` supply localized artifacts and parsed checks; [contracts and evidence](history-core.md) |
| Roads and spline network | `splnet.py`, `eu5_splines.py` |
| Vanilla content inventory and disposition | `content_inventory.py`, `content_decisions.py`, `content_check.py`, `content_report.py`, `eu5_content.py`, `eu5_places.py`; `eu5_reveal.py` (the optional start-of-game reveal of the New World, written from the written `definitions.txt`) |
| Stories, formations and colonial names | `history_content.py` (historical final-state eligibility), `content.py`, `storymodel.py`, `stories.py`, `stories_n4.py`, `stories_colonial.py`, `formations.py`, `colonial_names.py`, `eu5_story.py`, `eu5_formation.py` |
| Language discovery, translated text and names | `languages.py`, `translations.py`, `game_texts.py`, `wording.py`, `translit.py`, `names.py`, `loc_keys.py`; catalogues in `locale/<language>/<domain>.toml` |
| Export orchestration and script remapping | `eu5_nw_export.py`, `eu5_canvas.py`, `eu5_pacific.py`, `eu5_islands.py`, `eu5_newworld.py`, `eu5_rewrite.py`, `eu5_remap.py`, `eu5_events.py`, `pdx.py`, `artifacts.py` |
| Discovery, world library and recovery | `app/discovery.py`, `app/paths.py`, `app/library.py`, `app/recovery.py`, `app/worldcode.py`, `app/preferences.py` |
| Generation and installation service | `app/service.py`, `app/controls.py`, `app/install.py`, `progress.py`, `app/session.py`, `app/playset.py`; session and playset inspection is read-only |
| Atlas, previews and world naming | `history_archive.py`, `history_archive_checks.py`, `history_presenter.py` (bounded portable history and shared reading); `pictures.py`, `tagfont.py`, `worldname.py`, `atlas.py`; the viewer reads library data, not map-generation inputs |
| UI and text | `gui/controller.py`, `gui/window.py`, `gui/maps.py`, `gui/text.py`, `messages.py`, `app/gamenames.py`; `gui/start.py` chooses the window; the Tauri window is `gui/bridge.py` + `gui/view.py` (JSON-lines protocol and state) and repository `desktop/` (Svelte interface, Rust shell); the classic window is `gui/classic.py` + `gui/window.py`, drawing the maps through `gui/mapstyle.py` with the look both windows read from `gui/lenses.json` |
| Version and reproducibility | `epoch.py`, `record.py`, `inputs.py`; product version comes from `pyproject.toml` |
| CLI | `cli.py`; run `uv run rnw --help` for current commands |
| Native kernels and bounded resources | repository `native/`, `parallel.py`, `artifacts.Spool`; equality references in `tests/reference/` |
| Packaging | repository `packaging/hub.py`, `release.py`, `update_local_hub.py`, `allowlist.py`, `notices.py`; CI in `.github/workflows/` |

The original `eu5_export.py` and D0 commands remain diagnostic/synthetic tooling.
They do not define the capabilities or output set of `eu5_nw_export.py`.

## Invariants when changing code

- Construct valid output; reject broken topology, unresolved references and
  unknown required content dispositions. Do not repair it with a hidden fallback.
- Preserve Old World data and continuous identities across world wrap. Keep the
  accepted data-only visual extension and independent river watersheds.
- Large-map algorithms use strips/bands or bounded native kernels; verify equal
  output against references. Thread count must not change the world.
- Keep game inputs, abstract world data and public distributable assets separate.
- Check output goldens and the reference world when generated bytes change.
  [ADR 0003](adr/0003-versioning.md) governs the release target and pending epoch.
- A version keeps its world's land, so it is made only when this generator's algorithm
  epoch is the one that made the world. `Controller.version_problem` asks the world's
  record (the epoch that made its files; the release stamped in a code is only what the
  code was copied from) and falls back on the stamp when there is no record;
  `worldcode.require_same_land` asks a bare code, as `rnw reroll` has only that. Both
  windows and the command show the same message instead of writing land from the running
  algorithm. `worldcode.rolled` does not ask: its callers do.
- Library data is shared by application copies using the same data directory.
  An existing local library in a Workshop install is expected; it is not bundled
  world content. Installed-world recovery may adopt existing local RNW mods.

The Tauri window ([ADR 0011](adr/0011-tauri-window.md)) is the UI: it drives the same
`Controller` through `rnw.gui.bridge`. The classic Qt window opens when chosen or when
the Tauri window cannot open (no WebView2 in a Proton prefix, no WebKitGTK).
The controller's work thread is a daemon, so the bridge's loop is the generator's life:
a failure of polling or of drawing the state is recorded (`Controller.record_fault`) and
retried, never allowed to end the process; every `Task` that can be shown for a world has
a `task.<name>` text (tests guard both).
The original architecture alternatives are preserved in
[the archive](archive/architecture-options.md).
