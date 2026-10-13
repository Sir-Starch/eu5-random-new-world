# Opus 5.5 architecture handoff

## Current state and evidence

EU5 Steam app 3450310 on `1.4-open-beta`, build 25905365, ran as version 1.4.1 under Proton on Linux (Wayland) [V-LOCAL C01; V-GAME C02]. The installed map has a 16384×8192 RGB location raster; a named color map; a continent → subcontinent → region → area → province → location hierarchy; sea/lake declarations, rivers, ports and adjacency data; and several terrain layers/caches [V-LOCAL C03–C08]. The corrected `rnw inspect` counted 28,573 location keys including 6,174 American keys and 28,582 named colors: every hierarchy key covered, nine extra declarations [V-EXEC C05]. The American hierarchy itself contains sea, lake, impassable and non-ownable keys, so it is not a simple land mask [V-EXEC C19]. A broad lexical scan found 104 categories of candidate American-key occurrences, but its 106,418 summed hits include false positives and are not a dependency graph [V-EXEC C10]. Start setup spans locations, pops, countries, markets, roads and more [V-LOCAL C09]. A ten-file map-contract fingerprint is available in gitignored `local_data/map-contract.json`; its aggregate digest is recorded in C20 [V-EXEC].

Experiment 001's metadata-only mod was recognized by the game and `1.4.*` matched 1.4.1 [V-GAME C11]. Its full “no new errors” rung is **INCONCLUSIVE** because baseline/current log capture stages differ. The isolated temporary profile stopped at an unresponsive Select Language screen; the game/input helper were closed and the owner requested no more game launches this session [V-GAME C12]. Experiments 002–006 are **NOT-RUN**. No tier T0–T5 geography or start-state behavior is established in-game [UNKNOWN C13]. See [experiment records](../../experiments/) and [feasibility](../feasibility.md).

## What remains unknown

Highest risks, in order: mod content override precedence; minimum mandatory map files; map cache/`nodes.dat` regeneration; land/sea class changes and pathfinding; moved boundaries with existing IDs; new IDs and setup; exact script reference graph and failure modes; Old World preservation; patch compatibility; distribution rights for modified vanilla rasters [UNKNOWN C13; INFERRED C15,C18]. The 1.3.11 [community engine atlas](https://github.com/mattebin/eu5-engine-atlas) is only a lead for `script_docs` and must be revalidated on 1.4.1 [SOURCE C17].

## Open architecture decisions and required evidence

| Decision | Options | Evidence required |
|---|---|---|
| Geography tier | T3 free topology; T2 ID-preserving redraw; T1.5 cell reclassification | Experiments 003–006 with visible map and movement; use T3 if new IDs work, T2 if only reshaping works, T1.5 if only class changes work |
| Representation | Raster-first; polygon/graph-first; hybrid | Exact loader requirements and benchmark on real 134M-pixel size, not intuition |
| Exporter | Full mod package; template patcher; curated worlds | Content override test, setup dependency graph, local-generation rights strategy |
| Implementation core | Python arrays; Rust; hybrid | First accepted raster prototype and measured time/memory, plus Windows/Linux byte identity |
| Political generation | Static setup; in-game script postload; hybrid | Experiment 002, then scripted hook and playability proof |

Do **not** claim a minimum engine file set, infer that new IDs work, commit a vanilla-derived raster, or reduce the product to owner shuffling before these gates. The conditional architectural direction is an external deterministic generator emitting a complete per-build mod; T2 is a first implementation slice and fallback if T3 fails [INFERRED C14]. [ADR 0001](../adr/0001-python-research-tooling.md) commits only the research tooling stack. [REA](https://github.com/morluto/rea) was evaluated as an optional native-analysis tool, but no provider is installed and it has not been run [SOURCE/V-LOCAL C21].

## First assignment for Opus

**Implement the first deterministic geography-generating mod candidate** in [the implementation contract](../implementation-contract.md). Deliver a seeded world model, meaningful generated coast/island variation on synthetic fixtures, an EU5 1.4.1 exporter that stages a new `rnw_exp_*` package from the user's local installation, and offline evidence that a bounded American land–sea boundary changed while protected Old World pixels and IDs did not. Include the exact command and hashes for reproduction. Mark the package **NOT GAME VALIDATED**; do not launch EU5 until the owner separately resumes testing. This is development of the mod itself, not a request to plan more research. Eventual engine validation follows experiments 002–004 in order, then T3 new-ID testing if T2 loads. Sonnet's remaining bounded tooling work can proceed alongside this [backlog](sonnet-5.5-backlog.md).
