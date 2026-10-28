# EU5 1.4.5 and Across the Pillars

Audit date: 2026-10-28. Target: the public Steam build **26211608**.
This audit reads installed files and the owner's existing session; no agent
launches or controls EU5. Raw sources, logs and derived worlds remain ignored
under `local_data/compat-145/`.

## Installed build and owner's session — C425

[V-LOCAL] Steam's manifest identifies build 26211608 on the `public` branch,
updated at 19:35:18 CET on 28 October. All ten map-contract files hash exactly
as on 1.4.3/1.4.4: aggregate
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
The wider inputs are different: 922 previously recorded files changed, all
localization files; the release also adds D009 gameplay scripts that the old
worlds could not override. An unchanged map fingerprint establishes the map
interface, not complete script or DLC compatibility.

[V-GAME owner/logs] The session explicitly identifies **1.4.5**, first loading
Restored visual wrap / RNW 0.13.20 at 19:46:53, then Complete sacred-centre
governments / 0.13.21 at 19:47:35. `game.log` records new years 1338–1342 and
`debug.log` records normal exit at 19:51:25. This is a short startup/campaign
observation, not another long-campaign validation. The current `error.log`
contains 91 timestamped records and two continuation lines. Earlier rotations
are excluded; `event_log.csv` is still dated 23 October and cannot establish
events fired in this session.

[V-GAME owner/logs] Eight D009 expedition definitions fail their initial waypoint
lookup on each of the two loads: Cibola, City of Caesars, El Dorado, Fountain of
Youth, Norumbega, Quivira, Saguenay and Sierra de la Plata. The missing keys are
`culiacan`, `la_plata_river_mouth`, `cumana`, `havana_bay`, `massachusetts_bay`,
`florida_keys`, `mouth_of_saint_lawrence` and `salta`; the last expedition has
two missing entries. These are an RNW compatibility fault: the old world removed
the keys before the new DLC scripts existed. Metadata matching `1.4.*` did not
validate those definitions.

[V-GAME owner/logs / UNKNOWN attribution] The session also records thumbnail/VFS,
network/marketing, graphics-vendor, database-size, unused-variable, locator and
vanilla GUI warnings, plus a self-relation failure in the Old World's SWB.
These are not all established RNW regressions or established harmless messages.
The previous sacred-centre missing-law/parliament diagnostics do not appear in
this session; later succession behavior is unobserved. Existing world-wrap
diagnostics remain governed by the [separate dossier](map-wrap-dossier.md).

## Official notes and DLC disposition — C426

[SOURCE, accessed 2026-10-28] The official [1.4 release announcement](https://store.steampowered.com/news/app/3450310/view/716794361145196901)
describes expeditions with both fixed and dynamic routes, colonial-charter
improvements, daily pacing, and the other free-update systems. The official
[DLC announcement](https://steamcommunity.com/app/3450310/announcements/?l=english)
lists the Golden Century's colonial interactions and unique expeditions.
[Tinto Talks 127](https://steamcommunity.com/app/3450310/announcements/?l=english)
specifically describes eight legendary-city searches and two treasure fleets.
These announcements distinguish paid content from the free update, but do not
specify every script operand. The launch announcement points to the forum for
its full list; a direct forum fetch returned a client challenge. No separate
complete 1.4.4→1.4.5 changelog was established from that page. Installed-file
comparison and executable-version logs therefore determine the local delta.

[V-LOCAL / INFERRED disposition] Inspection covers the base game and all installed
DLC script roots, including D009's direct map references and its dynamic colonial
consumers. The content inventory finds **655** consumers, **19 newly undecided**;
none of the old decisions is stale. Every retired-country event/modifier count,
official language and existing map/lobby interface check retains its previous
contract. Adaptation is required, but only part of the DLC depends on vanilla
American identities:

| Content | Installed dependency | Disposition |
|---|---|---|
| Eight legendary searches | Initial fixed waypoints, discovered sea areas, later targets and retry waypoints | Keep the legends; remap every geographic operand through the existing shared bindings. These are searches for mythical places, not a requirement to recreate the corresponding historical country. |
| Two treasure fleets | Fixed ocean waypoints, remapped Cuba geography, American region keys and Pacific coastal provinces; actual ports/resources chosen dynamically | Keep; remap the fixed references and retain dynamic ownership, port and resource filters. Preserved region keys refer to the generated hierarchy. |
| Seven referenced expedition events | Guide origins, reward locations, continued/retry destinations | Keep; use the same bindings as their expeditions. No retired native tag is required. Vanilla narrative and historical notes remain vanilla. |
| `is_on_pacific_coast_americas` | Eleven American coastal province keys | Keep; the province remap points them at generated sea provinces. This retains the vanilla positional coast classification, not a newly simulated Atlantic/Pacific basin system. |
| `d009_sephardi_diaspora.8` | Literal Brazilian-refugees/New-Amsterdam incident, 1654–1660 | Neutralize its trigger consistently with other literal American historical incidents; retain the event definition and the rest of the Sephardi chain. |
| Golden Century dominance, flashpoints, native integration and tribute actions | Current winner, subjects, charters, owners and location properties | Keep vanilla scripts; no retired American state or location is required. |
| Council of the Indies, viceroy bureaucracy, Patronato Real and Encomienda Visitation | Current colonial subjects, policy/reform/religion and Old World actor | Keep vanilla scripts; no adaptation of generated natives or map identities is needed. |
| Iberian Union, Strait contest, Maghrebi content and cosmetics | Preserved Old World countries/places or nongeographic assets | Keep vanilla content. |

[INFERRED] Dynamic selectors remain meaningful on generated geography. That is an
inspection finding, not proof that an expedition or Golden Century campaign has
completed successfully in the engine. DLC ownership gates must survive every
rewritten file; installing RNW does not grant the DLC.

## Implementation and verification — C427

RNW **0.13.22 / epoch 59** explicitly decides all 19 consumers: 18 kept and one
historical incident neutralized. The existing geographic writer carries their
bindings; no new game-file format, shader/GUI workaround, runtime repair, or
new DLC dependency is introduced. An unknown future consumer still fails the
export. Worlds generated before this release are preserved and do not acquire
new DLC overrides automatically.

The synthetic regression exercises a complete DLC route, its arrival callback,
guide birthplace, reward and return waypoint at the mounted mod paths. It also
checks province/location name collisions and retains the DLC gate and Old World
return port.

[V-EXEC] The complete reference export has **867** canonical nonmetadata files,
SHA-256 `23c0437734288ffa913061f627838855c97962185fe939da18b313ccb1bd9c85`.
An independent complete export reproduces it with no changed inputs or differing
files. All **851** canonical files of 0.13.21 match exactly; the sole additions
are **16 D009 text files**. Geography, populations, countries, governments, water,
terrain, localization overrides and the selection cover retain their bytes.

[V-EXEC] Independent written-file inspection resolves all **nine** initial
waypoint entries and **111** scoped geographic references in the added files.
The initial ports retain port access, water targets remain water, all ten
adapted expedition definitions retain their `has_dlc` gate, and the diaspora
event has its closed trigger. The export's existing checks find no lost Old
World contacts, unreachable generated sea zones, land cells without port access,
missing definitions, undecided consumers or dangling geographic references.
The final inventory has **655** consumers: keep 408, neutralize 87, rebind 7,
replace 153; no missing or stale decision or carrier.

[V-EXEC] Locked environment sync and `make check` pass: **2,133 Python tests**,
14 optional skips, **23 Rust tests**, clean formatting/lint/types. The read-only
installed-game suite passes **12**, with the two opt-in long checks skipped;
the independent reference reproduction above runs separately. The CLI help check
also succeeds. The installed Windows and native Linux generators produce the
same complete 655-consumer inventory and synthetic expedition rewrite digests.
These results do not establish runtime completion of DLC content.

[V-EXEC] Installed **RNW: EU5 1.4.5 + DLC** as the separate
`mod/rnw_exp_world_jzrscmin4p`: **878 files hash-verified**, complete recovery
metadata, and complete native/Windows library entries. Updated the generator-only
hub to 0.13.22 with source, package, installed-copy and isolated Windows generator
self-test verification; its former 0.13.21 copy is backed up. The installation
hash-preserves all **5,124 files of six existing worlds**, all **3,274** files of
the updated hub and **nine** profile-root files. Exact delivery and removal are
in [INSTALLED](../../experiments/INSTALLED.md). No game installation, existing world,
save, setting or playset was changed; no EU5 process was launched or controlled.

[UNKNOWN] The engine has not run this new candidate. Syntax, geographic bindings,
deterministic output and packaged-generator operation are verified separately
from completing the adapted expeditions, treasure fleets or Golden Century
interactions. These remain part of the eventual combined release acceptance;
no extra game sitting is requested by this audit.
