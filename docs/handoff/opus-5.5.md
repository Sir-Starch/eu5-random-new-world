# Opus 5.5 architecture handoff

## Current state and evidence

EU5 Steam app 3450310 on `1.4-open-beta`, build 25905365, ran as version 1.4.1 under Proton on Linux (Wayland) [V-LOCAL C01; V-GAME C02]. The installed map has a 16384×8192 RGB location raster; a named color map; a continent → subcontinent → region → area → province → location hierarchy; sea/lake declarations, rivers, ports and adjacency data; and several terrain layers/caches [V-LOCAL C03–C08]. The corrected `rnw inspect` counted 28,573 location keys including 6,174 American keys and 28,582 named colors: every hierarchy key covered, nine extra declarations [V-EXEC C05]. The American hierarchy itself contains sea, lake, impassable and non-ownable keys, so it is not a simple land mask [V-EXEC C19]. A broad lexical scan found 104 categories of candidate American-key occurrences, but its 106,418 summed hits include false positives and are not a dependency graph [V-EXEC C10]. Start setup spans locations, pops, countries, markets, roads and more [V-LOCAL C09]. A ten-file map-contract fingerprint is available in gitignored `local_data/map-contract.json`; its aggregate digest is recorded in C20 [V-EXEC].

Experiment 001's metadata-only mod was recognized by the game and `1.4.*` matched 1.4.1 [V-GAME C11]. Its full “no new errors” rung is **INCONCLUSIVE** because baseline/current log capture stages differ. The isolated temporary profile stopped at an unresponsive Select Language screen; the game/input helper were closed and the owner requested no more game launches this session [V-GAME C12]. Its settings lacked `Game.first_time_playing`, unlike the normal profile; this could explain the screen appearing, but the ignored input remains unexplained [V-LOCAL/INFERRED C22]. Experiments 002–006 are **NOT-RUN**. No tier T0–T5 geography or start-state behavior is established in-game [UNKNOWN C13]. An offline D0 geography candidate now exists (see below). See [experiment records](../../experiments/) and [feasibility](../feasibility.md).

## What remains unknown

Highest risks, in order: mod content override precedence; minimum mandatory map files; map cache/`nodes.dat` regeneration; land/sea class changes and pathfinding; moved boundaries with existing IDs; new IDs and setup; exact script reference graph and failure modes; Old World preservation; patch compatibility; distribution rights for modified vanilla rasters [UNKNOWN C13; INFERRED C15,C18]. The 1.3.11 [community engine atlas](https://github.com/mattebin/eu5-engine-atlas) is only a lead for `script_docs` and must be revalidated on 1.4.1 [SOURCE C17].

## Open architecture decisions and required evidence

| Decision | Options | Evidence required |
|---|---|---|
| Geography tier | T3 free topology; T2 ID-preserving redraw; T1.5 cell reclassification | Experiments 003–006 with visible map and movement; use T3 if new IDs work, T2 if only reshaping works, T1.5 if only class changes work |
| Representation | Raster-first; polygon/graph-first; hybrid | Exact loader requirements; D0 raster-first export takes about 10 s on 134M pixels [V-EXEC C28] |
| Exporter | Full mod package; template patcher; curated worlds | Content override test, setup dependency graph, local-generation rights strategy |
| Implementation core | Python arrays; Rust; hybrid | Python + NumPy chosen for D0 ([ADR 0002](../adr/0002-d0-generator-stack.md)); revisit on a measured bottleneck or Windows identity failure |
| Political generation | Static setup; in-game script postload; hybrid | Experiment 002, then scripted hook and playability proof |

Do **not** claim a minimum engine file set, infer that new IDs work, commit a vanilla-derived raster, or reduce the product to owner shuffling before these gates. The conditional architectural direction is an external deterministic generator emitting a complete per-build mod; T2 is a first implementation slice and fallback if T3 fails [INFERRED C14]. [ADR 0001](../adr/0001-python-research-tooling.md) commits only the research tooling stack. [REA](https://github.com/morluto/rea) was evaluated as an optional native-analysis tool; `objdump` is available, but no full decompiler provider is installed and REA has not been run [SOURCE/V-LOCAL C21].

## First assignment: delivered offline, 2026-10-14

The D0 slice of the [implementation contract](../implementation-contract.md) is implemented and **NOT GAME VALIDATED** ([ADR 0002](../adr/0002-d0-generator-stack.md), C23–C33):

- `rnw synth` generates seeded synthetic worlds with new cells, hierarchy and colours (presets `continents`, `archipelago`) and byte-identical bundles with golden digests [V-EXEC C31].
- `rnw generate` stages `generated/rnw_exp_d0_coast_s42` from the fingerprinted 1.4.1 install. It moves 16,205 land–sea pixels between existing American IDs in window x 3700–4700, y 1700–2700, overriding only `locations.png` and `rivers.png`. All contacts, frozen pixels, outside-window bytes and Old World pixel counts are unchanged after re-decoding; a repeat run is byte-identical [V-EXEC C28–C30].
- Discoveries: the nine extra colours are zero-pixel declarations (C23); `rivers.png` holds a water mask (C24); `heightmap.png` does not cover the Americas, so the drawn terrain will not match the moved coast (C25); locator rows are flipped (C26).

## Next work, in order

**Owner requirement 2026-10-19:** terrain must be generated by a deliberate relief/climate/biome model with coherent regions and smooth transitions; this is mandatory phase V1 ([terrain-biomes](../terrain-biomes.md)). **V1a is implemented** (C48–C53): calibrated climate model for templates, vanilla slot rules for materials, continuous relief, regenerated vegetation instances, organic location borders. Next: owner review in game, then rivers (V1b).

**In-game update 2026-10-14:** experiment 004 is PARTIAL — the mod's `locations.png` reshapes location outlines in game, drawn terrain does not change (C34–C36). Priority 0 below is now the visual terrain layer.

0. **Visual coastline:** extend the exporter to write the affected height decals (C36) consistently with the moved pixels. First test which source the engine reads: a mod copy of one decal's PNG versus regenerated `.info`/`.bin` (LZAV; pin and review any LZAV implementation before use, or test `lzav=no`). Also check `terrain_cache/checksum.json` invalidation and material masks.

1. **When the owner authorizes game time:** fix the isolated-profile first-run input issue (C22), then run experiments 002 → 003 → 004 with a complete same-build baseline. For 004 install exactly the D0 candidate per its [record](../../experiments/004-boundary/README.md). Expect a drawn-terrain mismatch; the question is whether borders, selection and movement follow the moved pixels.
2. **Offline, now:** extend the exporter toward T3 behind a flag: new keys/colours in `named_locations`, `definitions.txt` and `default.map` for a small generated island using the existing model. Keep it out of default output until experiment 005 is authorized.
3. **Offline, now:** investigate the American visual terrain source (decal tiles, `terrain_cache/checksum.json`) read-only, to decide whether a later exporter can align the drawn coast.
4. Push only with the owner's approval, then confirm Windows CI matches the synthetic golden digests (C31).

Do **not** claim a minimum engine file set, infer that new IDs work, commit a vanilla-derived raster, or reduce the product to owner shuffling. Sonnet's bounded work can continue alongside ([backlog](sonnet-5.5-backlog.md)).
