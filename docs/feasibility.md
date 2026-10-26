# Feasibility and ambition ladder

> [!NOTE]
> **Historical record** of the research stage (EU5 1.4.1, October 2026), kept for its evidence. Since then T2 and T3 have been observed in game (C34, C45). Current status: [roadmap](roadmap.md) and [changelog](../CHANGELOG.md).

Current verdict for EU5 **1.4.1 open beta, Steam build 25905365**: the highest tier established in-game is **none of T0–T5**. Only metadata discovery passed a limited startup check [V-GAME, C11]. T1.5–T3 remain plausible research targets because relevant static data exists [V-LOCAL, C03–C09], but no geography override or playability has been observed [UNKNOWN, C13]. This is a confidence limit, not a finding that genuine RNW is impossible. On 2026-10-14 an offline T2 candidate (moved land–sea pixels between existing IDs) was generated and validated outside the game; it does not change any tier classification until tested in game [V-EXEC C28; UNKNOWN C13]. **Update:** in game, a mod-provided `locations.png` reshaped existing location outlines, including land–sea boundaries [V-GAME C34]. That is the first observed T2 behavior; drawn terrain, movement and save behavior are not yet established, so T2 is not yet playable-verified.

Capability terms: **Verified possible** means observed in game for 1.4.1; **Strongly supported** means multiple local interfaces exist but a game test is missing; **Plausible but unverified** means an experiment is needed; **Technically difficult** means numerous coupled assets/contracts must be solved; **Blocked via supported interfaces** requires evidence of an actual engine restriction, which we do not have.

| Tier | Candidate files and derived data | Breakage / test needed | Current classification, effort and risk |
|---|---|---|---|
| T0 political and demographic reroll on fixed geometry | `main_menu/setup/1337/{06_pops,10_countries,21_locations,...}.txt`, cultures/religions | Prove override semantics and visible changed start state; audit events and markets | Plausible but unverified [V-LOCAL C09; UNKNOWN C13]; medium effort, high integration risk |
| T1 regenerate attributes and hierarchy | T0 plus `location_templates.txt`, `definitions.txt`, localization | Test changed climate/topography/resource and regrouping; preserve references or rewrite them | Plausible but unverified [V-LOCAL C04,C08]; high effort/risk |
| T1.5 convert existing cells between land/sea/lake/wasteland | T1 plus `default.map`, sea/lake lists, location raster, heightmap, rivers, port/adjacency data and terrain layers as required | Determine whether existing IDs can switch class, visual layers/caches rebuild, naval and land pathfinding update | Technically difficult [V-LOCAL C03,C06–C08; UNKNOWN C13]; high effort, very high risk |
| T2 ID-preserving reshape | T1.5 plus pixel recoloring, key/color map consistency, centers/ports and derived nodes | Observe moved boundary and pathfinding; constrain Old World pixels; determine cache invalidation | Technically difficult [V-LOCAL C03–C07; UNKNOWN C13]; very high effort/risk |
| T3 free topology in bounded New World | T2 plus genuinely new keys/colors, hierarchy, setup and possibly new sea zones | Prove new IDs load; generate all dependencies; test exploration, colonization, movement and Old World regression | Plausible but unverified as an interface, technically difficult as a product [V-LOCAL C03–C10; UNKNOWN C13]; extreme effort/risk |
| T4 whole world | T3 at global scale | No simplification evident; out of product scope | Technically difficult [INFERRED C03–C10]; extreme effort/risk |
| T5 runtime geography generation | Would require a documented or discovered engine API for raster/topology mutation | No such 1.4.1 API established; investigate `script_docs` only as a versioned lead | Plausible but unverified, low confidence [UNKNOWN C13; SOURCE C17]; extreme risk |

The **minimal mandatory map override set is unknown**. `default.map` names several files, but it does not tell us which ones the mod loader accepts or which cached results the engine rebuilds. Listing a full file set as “mandatory” now would confuse observed files with tested loading behavior.

## Capability matrix for product controls

| Control / feature | Current route | Status |
|---|---|---|
| Seed, reproducibility, presets and reroll | External generator with versioned RNG and deterministic export | Strongly supported as our own tooling [INFERRED C14], engine compatibility pending |
| Culture, religion, owners, populations and economics | Static setup generation | Plausible but unverified [V-LOCAL C09] |
| Terrain, climate, vegetation, resources and names | Template/hierarchy/export edits | Plausible but unverified [V-LOCAL C04,C08] |
| Landmass size, archipelagos, coastlines and new seas | T1.5/T2 or T3 raster and topology output | Technically difficult [V-LOCAL C03,C06–C07; UNKNOWN C13] |
| New location count and free topology | T3 | Plausible but unverified [UNKNOWN C13] |
| Rare civilizations, intensity and historical/fantasy toggle | External start-state design after T0/T3 contracts | Plausible but unverified [V-LOCAL C09] |
| Preview | Our own raster/model viewer | Strongly supported as standalone tooling [INFERRED C03,C14], no engine claim |
| Runtime in-game generation | T5 | Plausible but unverified with weak evidence [UNKNOWN C13] |
| Multiplayer, ironman, achievements | Generated-mod compatibility tests | Unknown [UNKNOWN C13] |

## Ranked blockers and alternatives

1. **Override contract and startup gate:** No 1.4.1 content override has been observed. Exact risk: a well-formed generated raster may never mount or may be superseded by vanilla. Next experiment: one visible T0 setup edit in a fresh isolated profile; then one small map edit. Alternative: stop at static pre-generated mod packs only if their load path is proven. [UNKNOWN C13]
2. **Map consistency and derived data:** Raster, hierarchy, classifications, ports, adjacency, river and terrain data may disagree or require opaque `nodes.dat`/cache rebuilding. Exact failure modes remain unknown. Next experiments: attribute change, pixel boundary move, movement/naval test. Alternative: T1 or T2 preserving IDs if T3 fails. [V-LOCAL C03–C08; INFERRED]
3. **New IDs and whole-world coupling:** At least 6,174 American location keys and broad references in setup, localization, gfx and scripts create a large rewrite surface. A lexical scan is not a dependency graph. Next: syntax-aware coupling graph, deliberate new-ID experiment and a few-location playable island. Alternative: ID-preserving T2, then T1.5 if coastlines can be changed. [V-EXEC C05,C10; UNKNOWN C13]
4. **User experience and patch churn:** The isolated profile's Select Language screen was unresponsive; beta updates can change contracts. Next: solve validation access only with owner-approved game time, retain build fingerprints and patch regression. No further game launches in this session. [V-GAME C12; INFERRED C18]
5. **Distribution rights:** A full modified vanilla map may be a derivative asset. Generate locally from a lawful user installation until rights are clarified; distribute original generator code and original assets only. [SOURCE C15; INFERRED]

**Recommended conditional approach:** external deterministic generator emitting a complete EU5 mod from the player's installed version; validate all cross-references and raster/graph invariants before installation. **Runner-up:** T2 ID-preserving reshape with generated visual layers, if new IDs fail but boundary changes load. Neither approach is yet verified. Do not silently redefine the target as T0 ownership randomization.

## Later observed constraint: mainland wrap, 2026-10-26

The original engine-only interpretation below is superseded by the 0.13.5
identity-construction correction at the end of this section.

[V-GAME owner / V-LOCAL / V-EXEC C370–C372] On EU5 1.4.4 executable 26142040,
EVXP's immediately reproducible Towa troop-raising hang exposes an engine
horizontal midpoint calculation using the map's height. A bounded route
capture and independent arithmetic reproduce five erroneous points exactly.
Offline cylindrical adjacency and a visually continuous seam therefore do
not establish stable unit movement across a wrapped mainland.

[UNKNOWN C373] A safe data-only remedy preserving that mainland is unresolved;
neither a corrected-engine runtime comparison nor a clean-vanilla crossing
test was performed. No binary patch or replacement geography is part of this
diagnosis. See [067](../experiments/067-towa-seam-hang/README.md).

**Correction following vanilla comparison (0.13.5, C374–C378).** The preceding
trace was not sufficient to conclude that mainland wrap needs an engine repair.
[V-GAME owner / V-LOCAL / V-EXEC] Vanilla uses continuous location identities
across the raster edge; RNW's forced split introduced a different, defective
adjacency structure. Version 0.13.5 removes that split at construction time.
The corrected owner-world's physical-class raster and retained Old World land
are exact, with continuous IDs and correctly placed anchors; a separate candidate
is prepared. [UNKNOWN] Runtime movement and hang resolution still require game
observation, distinct from the verified data correction. See
[068](../experiments/068-continuous-location-identities/README.md).
