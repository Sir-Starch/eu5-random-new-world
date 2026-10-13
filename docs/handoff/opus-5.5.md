# Opus 5.5 architecture handoff

## Current state and evidence

EU5 Steam app 3450310 on `1.4-open-beta`, build 25905365, ran as version 1.4.1 under Proton on Linux (Wayland) [V-LOCAL C01; V-GAME C02]. The installed map has a 16384×8192 RGB location raster; a named color map; a continent → subcontinent → region → area → province → location hierarchy; sea/lake declarations, rivers, ports and adjacency data; and several terrain layers/caches [V-LOCAL C03–C08]. `rnw inspect` counted 28,573 location keys including 6,174 American keys [V-EXEC C05]. A broad lexical scan found 104 categories of candidate American-key occurrences, but its 106,418 summed hits include false positives and are not a dependency graph [V-EXEC C10]. Start setup spans locations, pops, countries, markets, roads and more [V-LOCAL C09].

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

Do **not** lock a production map representation, claim a minimum file set, infer that new IDs work, commit a vanilla-derived raster, or reduce the product to owner shuffling before these gates. The conditional architectural direction is an external deterministic generator emitting a complete per-build mod; T2 is the runner-up if T3 fails [INFERRED C14]. [ADR 0001](../adr/0001-python-research-tooling.md) commits only the research tooling stack.

## First assignment for Opus

Design a small, versioned **experiment 002–005 decision protocol** that specifies an isolated-profile launch remedy, exact mod override files for one visible start-state edit, a same-build complete baseline, then minimal attribute/class/boundary/new-ID probes. Define pass/fail observations for rendering, selection and land/naval pathfinding and an Old World invariant set. Do not schedule a game launch until the owner separately decides to resume testing. Deliver an ADR only after evidence from those probes; feed bounded work to Sonnet from the [backlog](sonnet-5.5-backlog.md).
