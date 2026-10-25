# TR46 — Long observer campaign: open problems and log audit

2026-10-25. Retrospective [experiment 053](../../experiments/053-tr46-observer/README.md).
Generator **0.12.3**, epoch **33**, EU5 **1.4.4**, Steam build **26142040**.
Evidence: C298–C303 in the [claims ledger](claims-ledger.md).

**Scope:** record the owner's seven observations and every diagnostic family in
the available session logs. No fix, regeneration, installation or game launch.
Every item below is **OPEN**. A recorded symptom is not an established cause.
This is the starting list for subsequent work; the owner need not retell it.

**Follow-up:** [054](../../experiments/054-tr46-coast-footprint/README.md) records
the vanilla/treaty findings and the 0.12.4 correction of the removed coast's
offshore visual footprint (TR46-07). Written-file and preservation checks pass;
the rendered result remains unobserved. TR46-06a and L01 remain separate open
boundary problems. The observations below retain their original 0.12.3 scope.

## 1. Session and preserved evidence

[V-LOCAL C298] The enabled playset and the session's mounted mod identify
**RNW: Continents TR46**, folder `rnw_exp_world_tr46hr3fkn`, metadata version
0.12.3, world code:

```text
RNW1-040XN-DR20S-1RQ4T-Z0060-602JM-HB0
```

[V-EXEC C298] The code decodes to preset `continents`, seed
`15760067646932620127`, generator 0.12.3 and no setting overrides.

[V-LOCAL C298] Steam's current manifest says build 26142040; `continue_game.json`
says 1.4.4. `code_revisions.log` records executable hash `ef497c42f07`, timestamp
2026-10-22 14:01:29 +0000. The previously established 1.4.3-data / 1.4.4-executable
boundary is C198; this audit does not claim compatibility with another patch.

[V-GAME logs C298] Session clocks run **04:03:47–07:01:39**. Campaign starts at
1337.4.1 (`performance_degradation.log`); `game.log` records 253 new years,
1338–1590. The last performance rows record **1590.11.11**. Country control is
cleared at 04:13:33–04:13:38 (`multiplayer.log`); the owner's report identifies
the subsequent run as observer mode. It is therefore not described as an
observer game from the very first startup frame. The final save/disconnect is
at 06:57:58, followed by a normal `SplashScreen->Empty` transition at 07:01:39.
There is one nonfatal assertion, recorded separately in L02. The prior crash
folder `Europa Universalis V20261025_025342` predates this run and is not evidence
that TR46 crashed. Times here are the clocks written in the logs; the archive
manifest also retains UTC filesystem times.

[V-EXEC C298] Evidence is under ignored **`local_data/tr46-observer-20261025/`**:

| Local evidence | Contents and limits |
|---|---|
| `evidence-manifest.json` | Original source paths, sizes, SHA-256 and available UTC modification times for 37 initially copied files; 129,669,006 bytes |
| `profile/logs/` | Every available log, including rotated errors; `error.log` has 2,368 physical lines and 2,366 timestamped records, one with two continuation lines |
| `profile/playsets.json`, `profile/continue_game.json` | Read-only snapshots; no playset or save setting changed |
| `profile/save games/` | Untouched copies of the latest `autosave_36c88242-8980-410a-9d50-5582e2dcc0ed.eu5` and oldest retained member of that campaign, suffix `_19.eu5`; not decoded into campaign state |
| `screenshots/` | All three owner attachments, original filenames and SHA-256 |
| `world-file-inventory.json` | Hashes and sizes of all 807 installed world files; 732 selected files copied to `world/` (235,520,278 bytes), including scripts, map PNGs, localization and metadata; large binary terrain assets are inventoried, not duplicated |
| `appmanifest_3450310.acf` | Steam installation snapshot, local only |
| `error-catalog.json` | Every timestamped error record, grouped by origin, with original line and clock |
| `debug.log.origins.json`, `game.log.origins.json` | Complete origin/message counts and first/last occurrences for those logs |
| `ai-command-counts.json`, `native-activity.json` | Recountable command totals and name-matched colonial/war activity, with source lines |

[V-LOCAL C298] **`event_log.csv` is stale:** its filesystem time is
2026-10-23 15:12:29 UTC. It is preserved but excluded from all TR46 event claims.
`error.1.log` begins at 03:53:58 and `error.2.log` at 03:23:50; rotated logs are
context, not additional errors counted against this run. Nine logs are empty:
`game_tests`, `memory`, `game_ai`, `custom_automated_stats`, `message`, `warning`,
`hardware_checker`, `database_conflicts`, `pdxsdk`. Empty files do not prove the
absence of gameplay defects. All raw game material stays outside Git.

## 2. The owner's seven problems

[V-GAME owner C299] These are observations from TR46 on 1.4.4 / generator 0.12.3.
Only item 7 has the attached screenshots. The proposed causes and vanilla
comparisons are [UNKNOWN], unless another evidence label is given explicitly.

| ID | Owner's point | Open problem |
|---|---|---|
| TR46-01 | 1 | Impassable land remains split into many small locations |
| TR46-02 | 2 | Impassable relief, especially mountains, is flat and discontinuous |
| TR46-03 | 3 | Too many distinct, adjacent named oceans / sea zones |
| TR46-04 | 4 | Implausible sea connections force long detours between nearby lands |
| TR46-05 | 5 | Extraordinary societies and large native states appear to expand very little |
| TR46-06a | 6, visual | Terrain/texture crack persists at the horizontal map boundary |
| TR46-06b | 6, gameplay/design | Wrapped “Alaska” counts as east in the Spain/Britain colonial division; vanilla comparison and wrap policy are unresolved |
| TR46-07 | 7 | Remnants of removed vanilla “Alaska” remain near Chukotka |

### TR46-01 — Merge compatible connected impassable land

**Observed:** impassable land is divided into dozens of small locations instead
of large coherent units like the owner's Siberian reference. The owner recalls
the earlier analogous ocean fragmentation problem.

**Unresolved:** exact vanilla partitioning rules; whether each connected
compatible impassable patch should be one location; which generated boundaries
are necessary for terrain classes, hierarchy or retained Old World contacts.
“All impassable land must become one global location” is not the requirement.

**Work entry points:** `newworld.py`, `hierarchy.py`, `eu5_nw_export.py`, the
written `default.map`, location raster and hierarchy. Compare vanilla Siberian
units before changing the topology. Count connected components and their
location counts on the archived TR46 raster; preserve protected contacts.

**Closure evidence:** a documented vanilla-based grouping rule, synthetic and
TR46 component checks, and a generated map whose compatible connected
impassable regions are coherent units. Terrain appearance is a separate test.

### TR46-02 — Impassable mountain relief

**Observed:** Old World mountain ranges look high and continuous; TR46's
impassable mountains look low, flat and isolated, with spot-like peaks.

**Hypothesis, not conclusion:** fragmentation in TR46-01 might affect the
appearance. Do not close this issue merely by merging location colours.
Classification as mountains and rendered physical height are separate facts.

**Work entry points:** `relief.py`, `fields.py`, `eu5_biomes.py`, `eu5_slots.py`,
`eu5_terrain.py`, `terrain_tiles.py`; written height/material/decal data. Compare
height range, ridge continuity and terrain-detail scale with analogous vanilla
mountains at the same camera scale. No new mountain screenshot was supplied.

**Closure evidence:** a numerical and visual reference comparison explaining
the physical discrepancy, with continuous, visibly substantial generated
ranges. Keep this open independently of TR46-01 and the seam defect.

### TR46-03 — Adjacent oceans and sea identities

**Observed:** a chain of **five or more neighbouring “oceans”**, each with a
different name and its own sea zone, where geography suggests seas or a single
ocean. This is both an identity/naming complaint and a partitioning complaint.

**Unresolved:** exact offending TR46 zone keys were not named in the report;
the screenshots of item 7 do not identify this chain. Reconstruct it from the
archived raster, names and hierarchy rather than inventing an example. The
earlier connected-ocean-name work in experiment 049 is not proof this is solved.

**Work entry points:** `seas.py`, `seanames.py`, `lanes.py`, `hierarchy.py`,
`eu5_seas.py`. Distinguish a physical basin, a named sea, a sea-zone location,
and closed `ocean_wasteland`. Connected water alone does not prove it needs
one navigable location or one name across the whole world.

**Closure evidence:** explicit vanilla-based identity and classification rules;
an audit of neighbouring TR46 water identities; sensible regional names and
partitions without artificial strings of unrelated “oceans”.

### TR46-04 — Local maritime routes and detours

**Observed:** two visually neighbouring landmasses often have no direct sea
connection; travel requires going around two or three of TR46-03's “oceans”.

**Unresolved:** deliberate closed deep water versus a missing lane, coastal
contact, port, adjacency or crossing. A globally connected lane graph does not
prove reasonable local travel. This complaint is about ships; army straits are
a related but separate interface.

**Work entry points:** `lanes.py`, `ports.py`, `straits.py`, `currents.py`,
`eu5_seas.py`, written `ports.csv` and `adjacencies.csv`. Reconstruct nearby
coast pairs and compare navigable shortest paths with geographic distance.
L02 and L03 below supply concrete additional engine diagnostics; neither proves
the cause of every reported detour.

**Closure evidence:** documented local routing criteria; TR46 near-neighbour
route cases with bounded detours, valid ports and retained Old World contacts;
separate results for ship lanes and army crossings.

### TR46-05 — Expansion of extraordinary societies and native states

**Observed:** extraordinary societies, including large New World countries,
appear to expand little during this long run. The owner explicitly asks whether
vanilla natives colonize and whether this is a generation problem.

[V-EXEC C301] Matching the **659 starting generated country tags and their
English names** against this run's `game.log` finds **210 colonization-start
records**, with **zero exact matches to those starting country names**. There
are **139 war declarations involving a matched name**, of which **137 have a
matched native attacker**. Examples: Siriça attacks Jabo Verde (`game.log:3618`),
Diripetio attacks Ixcatengo (`3619`). Tachila appears as attacker 16 times.
Thus native war activity exists; declarations do not establish territorial gain.

**Limits:** name matching can miss renamed/formable or successor countries;
colonization starts are not completed colonies; neither measure gives borders,
growth rate, eligibility or AI intent. No vanilla control campaign was run.
No claim that extraordinary societies specifically are expanding is established
by the aggregate. The binary saves were preserved, not decoded. Their `_19`
copy is a late campaign checkpoint, not an assumed 1337 baseline.

**Work entry points:** `societies.py`, `archetypes.py`, `eu5_natives.py`,
`eu5_archetypes.py`, `eu5_empires.py`, `eu5_technology.py`, `eu5_development.py`;
vanilla colonization eligibility, government/reforms, advances, AI expansion
targets and budgets. Use the written 1337 setup as the starting baseline and
the preserved saves where existing read-only tooling permits. Separate
conquest, annexation, tribal settlement and colonization. Inspect L04 and L07
without assuming they explain all stagnation.

**Closure evidence:** a vanilla comparison of native expansion mechanisms;
tag-based start/end land and subject counts for ordinary natives, great empires
and each extraordinary archetype; an explanation of whether the observed low
growth is expected or a generation defect. No new long campaign is requested.

### TR46-06a — Persistent physical seam

**Observed:** the texture/terrain crack remains at the horizontal wrap.
TR46 uses 0.12.3, so the offline periodic-placement candidate of experiment 052
does **not** establish that the visible seam is fixed. Its source-interface tests
remain valid within their stated scope; engine appearance is still a failure
reported by the owner. This report supplies no new seam screenshot.

**Work entry points:** the first/last columns of height, normals, materials,
water, terrain placement/cache and their admitted engine geometry. Reuse the
exact TR46 code; do not conflate smooth source rasters with seamless rendering.
L01's seam-adjacent river failures are another boundary defect, not proof of the
visual crack's cause.

**Closure evidence:** an explanation and verified visible result at both edges
and relevant zooms. If choosing the no-wrap alternative in 06b, record that as
an explicit design decision and prove it avoids the observed boundary problem;
do not claim the original renderer path was repaired.

### TR46-06b — “Alaska”, colonial east/west and the wrap decision

**Observed:** during a colonial division between **Spain (west)** and
**Britain (east)**, the generated “Alaska” at the **right edge of the raster**
was counted for Britain's east. “Alaska” here describes the owner's geographic
comparison, not a confirmed country, area or location key.

**Unresolved questions to answer together:**

1. Does vanilla Alaska actually cross the raster boundary, and which land,
   island, sea and hierarchy records occur on the right edge?
2. How does vanilla's colonial division classify that territory: coordinate,
   meridian, region/area membership, scripted lists or another mechanism?
3. Does generated reassignment of the retained American hierarchy keys change
   the intended treaty side independently of longitude?
4. Should generated continents cross this boundary at all? Compare preserving
   cylindrical geography with an explicit prohibition on crossing land. The
   owner is open to dropping land wrap if that better matches vanilla; the
   main currently reported objection is the visible crack.

**Work entry points:** vanilla map and American hierarchy; installed Tordesillas
situation/events/triggers, `eu5_content.py`, `eu5_remap.py`, `hierarchy.py`,
`newworld.py`, `landmask.py`. L05 is a separate confirmed treaty-text error;
its existence does not prove wrong geographic allocation.

**Closure evidence:** a recorded vanilla comparison and reasoned wrap-policy
decision, followed by treaty-side tests on the resulting geography. No policy
has been changed or accepted in this documentation phase.

### TR46-07 — Removed-Alaska remnants near Chukotka

**Observed and pictured:** near Chukotka, the sea retains shapes resembling
removed vanilla Alaska. The wide view shows pale shelf/underwater silhouettes;
the close views show stepped, angular, partly exposed-looking edges and a
sunken outline beneath the water. These are not evidence of generated mountain
quality, ocean routing or the dateline crack.

| Owner attachment | What to inspect locally |
|---|---|
| `Screenshot_20261025_040702.jpg` | Wide Chukotka context and offshore outline; separates preserved Old World land from the remnant |
| `Screenshot_20261025_040728.jpg` | Close view of the large angular underwater patch, light border and repeated straight/stepped edges |
| `Screenshot_20261025_040746.jpg` | Another close view showing the extent and shape of the remnant and the same edge defect |

**Hypothesis, not established cause:** the replacement canvas or a visual layer
may leave original Alaska terrain, shelf, materials, water/bathymetry or
placements behind. “The location raster is water” alone cannot settle this.
Audit all contributing layers and the exact protection-mask boundary, while
preserving Chukotka and the other Old World geography.

**Work entry points:** `landmask.py`, `eu5_nw_export.py`, `eu5_terrain.py`,
`terrain_tiles.py`, `eu5_water.py`, `seas.py`; installed vanilla versus archived
TR46 assets near the former-Alaska/Chukotka boundary.

**Closure evidence:** identify the responsible retained layer(s), show that
replacement water has no orphan original land/shelf silhouette, and verify
protected Old World pixels and geography remain intact. This issue is separate
from 06a even if the investigation later finds a common cause.

## 3. Additional problems found in the logs

[V-GAME logs C300/C302] Counts below refer to **one current-session source**;
the same errors mirrored in `debug.log`, `game.log`, `gui.log` or `ecs.log` are
not counted as extra incidents. [UNKNOWN] Attribution to RNW versus vanilla,
DLC availability or other mounted resources remains open where stated.

### TR46-L01 — Five rivers fail to load near the wrap

`error.log:53–57`, 04:04:18, `map.cpp:1731`: no river source; **698 unprocessed
pixels** total. Coordinates are preserved exactly in the local raw log:

| Bottom-left origin | Top-left origin | Unprocessed pixels |
|---|---|---:|
| (16343, 5469) | (16343, 2723) | 107 |
| (6, 5525) | (6, 2667) | 502 |
| (16383, 5609) | (16383, 2583) | 65 |
| (0, 5622) | (0, 2570) | 16 |
| (16383, 5631) | (16383, 2561) | 8 |

[INFERRED: these x coordinates are at/near both ends of the 16,384-wide map]
This is a concrete wrap-adjacent river-loading defect. Compare the written
`rivers.png` and the engine's source/continuity contract; do not infer that a
cylindrically connected raster is accepted as a single wrapped river. Closure:
valid sources and zero corresponding loader failures in the resulting candidate.

### TR46-L02 — Port/water assertion during play

`error.log:1574`, `debug.log:48300`, **06:32:02**: assertion
`pNewLocation->HasPort() || pNewLocation->GetTemplate().IsWater()` fails once.
The run continues. The log gives no affected country, unit, location, stack
trace or action. The invariant concerns a destination being water or having a
port; the exact subsystem and cause are [UNKNOWN]. Investigate with TR46-04;
do not equate one assertion with every bad route. Closure requires identifying
the failing case and validating the corresponding written port/adjacency data.

### TR46-L03 — Expedition routing and lifecycle failures

`error.log:1419–1420`, **06:12:25**; `1434–1435`, **06:17:45**;
`1553–1554`, **06:30:52**: three consecutive-waypoint pathfinding failures and
three discarded `western_ocean_voyage_expedition` waypoints: location ID
**21039** once, **21247** twice. Runtime ID-to-key mapping and route owners are
not established here. These supply concrete cases for TR46-04.

Other expedition diagnostics: **178** mining surveys fail after exhausting
waypoints without ending; **38** resumes target a non-stalled expedition;
**38** starts use a leader that fails requirements; **4** starts use a type
that cannot start. The survey records include many countries and do not by
themselves prove generated-ocean routing caused the failures. Closure separates
the sea-path defects from vanilla/script lifecycle failures and records attribution.

### TR46-L04 — AI command rejection and expansion calculation

`ai.log` contains **57,352** warning records: **57,156** invalid-command execution
warnings and **196** invalid-command posting warnings. Largest execution
categories: `set_cabinet_action` **35,724**, `disband_subunit` **5,898**,
`build_road` **3,170**, `change_trade_capacity` **2,396**,
`diplomaticactioncommand` **2,324**, `transfer_occupation` **2,096**.
All 42 execution/posting categories are in the companion catalog.

`error.log:381,533–534`: **3** division-by-zero errors at
`common/ai_scripted_expansion_target/attack_neighbors.txt:40`, clocks 04:20:24,
05:02:25, 05:02:28. Three building-candidate truncations also clamp for NAV,
ABA43, IFA (`1622`, `1623`, `2015`). There is no actor context on the division
errors and most AI warnings; none can yet be assigned to extraordinary natives.
Closure: establish origin and affected actors before connecting these to TR46-05.

### TR46-L05 — Tordesillas option text has a broken scope

`error.log:1730–1733`, **06:37:42**, mirrored at `debug.log:48917–48920`:
four diagnostics resolve to **one localization failure** for
`treaty_of_tordesillas.5.c`, referencing `overlord.GetNameWithNoTooltip`.
The `overlord` data type/promotion cannot be resolved. Investigate the installed
event option, scope and effective localization. This confirms broken text,
not which side owns the Alaska-like territory. Closure tests text and 06b's
geographic allocation separately.

### TR46-L06 — Corrupted country-name formatting

`error.log:1210–1269`, **05:56:43–05:56:44**: **40** unknown formatting tags
and **20** country-name text-data failures. The string contains control bytes;
retain it in the local raw log, not as a rendered country name in documentation.
Affected tag and name producer are [UNKNOWN]; generated names, a formable,
a colony, vanilla content and other resources need attribution. Closure:
identify the tag/name source and validate its effective name/localization path.

### TR46-L07 — A generated country exceeds the start relation budget

`game.log:3571`, **04:04:48**: **GVQ / Azcapolco** starts **0.9164** over
diplomatic capacity under the engine's worst-case DIP-0 ruler check; the
warning threshold is 0.5 and it reports DIP 28 needed to fall within the limit.
[V-LOCAL] GVQ is present in TR46's generated `rnw_natives.txt` and written
1337 country setup; it is not established here as an extraordinary archetype.
Vanilla DWS / Dawasir also warns at `3570` (0.64781, DIP 10).
This is a conditional setup warning, not proof of actual ruler capacity or
stagnation. Closure: audit generated alliances/subjects/relations and budgets,
then explain or correct the generated excess by construction.

### TR46-L08 — Incomplete map locators

`error.log:327–329`, **04:04:33**: incomplete `vfx` locator, plus two notices
that `city` and `vfx` locator transforms changed. Earlier occurrences of this
family are documented in C97; that history is not proof the current file is
correct. Inspect written versus inherited locator coverage; no automatic engine
locator-generation command was executed. Closure identifies the actual omission
and distinguishes stale overrides from required generated locators.

### TR46-L09 — Startup data/DLC/script inconsistencies

The current run records a missing descriptor for **`d009_across_the_pillars`**,
**12** invalid-DLC setup entries, **6** skipped religious orders, **12** invalid
achievements, **97** unresolved database-link records (**27 distinct target
identifiers**), **38** unknown-effect records, **11** effect and **2** trigger
postvalidation failures. Targets include `golden_century`,
`battle_for_the_strait`, Iberian laws/reforms/bureaucracies and the two
`gold_fleet_*_expedition` definitions. There are **24** missing effect-tooltip
records, **17** never-set flag warnings, **3** unused-variable warnings,
**76** possible-match suggestions, **9** unused-modifier notices and **10**
database-size notices. One persistent-reader error spans three physical lines
without naming its source file (`error.log:86–88`).

[INFERRED: several matching messages already occur before TR46's 04:04:17
mount and concern the unavailable d009 data] Some are likely installation/DLC
background. Others are in files RNW overrides, so startup presence alone does
not clear those overrides. There is no clean same-build vanilla control log in
this audit. Closure: compare effective files and ownership of each diagnostic;
do not suppress them or classify all as harmless vanilla noise. The full origin
catalog prevents low-frequency failures being lost behind the larger totals.

### TR46-L10 — Other runtime script failures

Record for attribution and later triage:

- **589** religious-movement records with no alternative religion, from 06:27:09;
- **306** rejected resolution proposals (305 `policy_vote`, one other case);
- **6** same-province migrations from `events/situations/reformation.txt:871`;
- **6** weather-system starts without enough path;
- **4** list-index caps (one kritarchy, three artist events);
- **2** HRE script values of wrong type;
- **2** loops aborted at 1,000 iterations (`flavor_gra.txt:1450`, `flavor_son.txt:318`);
- one missing CB target character, one AI event with no good option
  (`flavor_vol.1102`), one invalid-country event trigger (`flavor_vij.1203`);
- one null civil-war enemy and one invalid `TakeBackFromCivilWar` call.

Locations, clocks and counts are in the companion catalog. Attribution and
gameplay impact remain [UNKNOWN]. Closure records which are RNW-caused and
which belong to the installed game/content, with a reason rather than a blanket
waiver. None is evidence by itself for flat mountains or fragmented oceans.

### TR46-L11 — Presentation, UI and audio diagnostics

`error.log`: **717** invalid `sub_unit` text-object records (239 each for type,
prefix and levy structure), **15** VFS texture failures, **9** GUI texture
failures, **6** DLC thumbnail load failures, **6** missing portrait-template
records, **5** missing `waves_vfx` entities, **5** boat `foam_stop` state errors,
**7** `cargo_lctr` attachment failures, **3** missing map-mode input-action
records and **2** location-window layout failures. Counts for the same texture
or effect at different logging layers describe diagnostics, not distinct assets.

Additional `debug.log` families: **226** duplicate localization-key notices,
**34** default-icon fallback notices, **52** setup-file “magix” text-default
warnings, **5,689** missing `MapHeight` sound-parameter-limit notices,
**5,747** absent `river_node` sound-alias notices, **2** Wwise and **2** audio-state
records for `masDataWinterLevel`. Audio notices are not evidence that river
geometry failed; use L01 for that. These diagnostics have no established
connection to the three Chukotka pictures. Closure attributes effective assets
and records reproducible player impact before proposing generator work.

`ecs.log` additionally records **66** deprecation notices for global animation
variables that should reside in the shared state-machine directory. The other
ECS errors mirror the boat/cargo errors already counted above.

### TR46-L12 — Session environment and evidence-quality warnings

The launcher scans a missing **`rnw_exp_physical_seam`** folder (five records);
this is not the active TR46 world. Two software-GPU vendor notices coexist with
the system log identifying the RTX 4080 SUPER; they do not establish software
rendering of the campaign. The debug log has **46** missing-define-macro
notices, **2** invalid `tools_import` path notices, a missing checksummed-paths
file, a filewatcher mount warning and two graphics-context version-parse
fallbacks. `multiplayer.log` has **20** invalid
`set_preferred_mapmode` commands, each followed by command data, before observer
control was cleared. This does not mean the run was multiplayer.

[V-LOCAL C303] Although the active playset lists only TR46, the VFS log also
records mounts for Workshop IDs **3599543453, 3601047146, 3602694948, 3605677866,
3610757528, 3629368670, 3721193233, 3817487775**. A mount is not proof of a
gameplay conflict or an enabled entry in the saved playset. Preserve this as a
confounder when assigning errors; do not silently call this a clean vanilla/RNW
comparison. No Workshop files, account features or playset entries were changed.

The dedicated-server log's checksum-only playset warning and warning about
returning from observer mode are recorded context, not newly discovered defects.
The graphics log says the NVAPI driver check was not performed; setup/system
logs otherwise supply startup and hardware context, without an additional
map-specific failure family.

[V-LOCAL C303] `performance_degradation.log` records memory rising from about
9,524 MB at the initial campaign row to about 22,001 MB at 1590.2.27; the later
menu rows retain date 1590.11.11. These samples do not establish a leak or a
generator-specific performance regression, and the owner reported neither.
Normal zero-count repair summaries and generated advance-tree notices are
recorded as context, not invented corruption failures.

## 4. Work order and closure discipline

This is a future triage order, **not authorization to implement in this audit**:

1. **Boundary and replacement integrity:** TR46-07, 06a/06b and L01 together;
   establish vanilla Alaska/treaty behaviour and choose wrap policy explicitly.
2. **Maritime geography:** TR46-03/04 with L02/L03; separate basin identity,
   naming, navigable partitioning, local routes and port validity.
3. **Impassable land:** TR46-01/02; grouping and physical relief need separate
   acceptance evidence even if implemented in one phase.
4. **Society growth:** TR46-05 with L04/L07; use start setup, existing saves and
   vanilla eligibility before proposing balance changes.
5. **Content and diagnostic attribution:** L05/L06/L08–L12; prioritize broken
   player text and invalid generated setup over confirmed background notices.

For each stable ID, record cause, affected files, vanilla evidence, chosen
change (if any), offline checks and remaining engine uncertainty. Do not close
an owner observation because existing unit tests pass. No new manual sitting,
long campaign, probe/companion mod or request for more screenshots is due from
this audit. Use the preserved evidence first; if a later change truly needs
engine observation, batch it under the project's normal testing policy.

For complete diagnostic coverage and precise source locations, use the
[log catalog](tr46-log-catalog.md). For the history of the previously attempted
boundary fixes, use [051](../../experiments/051-wrap-continuity/README.md) and
[052](../../experiments/052-physical-seam-and-coasts/README.md).
