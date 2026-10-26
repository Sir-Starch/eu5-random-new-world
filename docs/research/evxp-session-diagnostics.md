# EVXP fixed — current-session diagnostic audit

2026-10-26; claims C381–C386. EU5 **1.4.4**, Steam **26142040**,
executable SHA-256 **725a4c6c…14009**. Active world **EVXP fixed 0.13.5 /
epoch 42**, `rnw_exp_evxp_identities`.

**Correction follow-up, 0.13.6 / epoch 43 (C390–C392):** the
[campaign mod fixes](../../experiments/069-campaign-mod-fixes/README.md)
correct G01's treaty representation/encoding/localization, G02's boundary river
drawing, G03's duplicate retained-ocean VFX records and G04's incompatible initial
guild levels. These are verified offline, not a replay of this campaign. The
two locator rectangle warnings, five minority-culture initialization warnings
and other unresolved attributions below are not claimed fixed.

## Scope and attribution

[V-LOCAL / V-EXEC C381] The owner left EU5 running. A host process listing
binds PID 4018904 (`MainThread`) to the Proton EU5 executable. Preserve the
28 available log files with original hashes in ignored
`local_data/pestilence-20261026/`; the first captured current-session error
interval is **16:57:15–18:07:33 CET**. A separate continuation snapshot through
19:01:35 CET is analyzed below. These are fixed audit cutoffs, not the game's
end time. Both current error files in the first snapshot end with complete records.
`error.1.log` belongs to this launch, whereas `error.2.log` through
`error.5.log` predate it. The event CSV is from 23 October and supplies no
current event trace.

At the first cutoff there are **5,149 timestamped error-log records**, **50
engine origins** and **427 exact message variants**. Continuation lines belong
to their preceding record. Mirrors in `debug.log`, `game.log`, `gui.log` and `ecs.log` are not
added again. An origin or a repeated warning is not a distinct defect.

The process first loaded **22F4** data, switched to **EVXP fixed** at 16:57:38,
and built the campaign afterwards. Keep the two map-loading batches separate.
The active playset contains EVXP fixed alone. VFS diagnostics also mount other
local RNW worlds and eight Workshop resources while inspecting/loading data;
those mounts do **not** establish that every resource was active in simulation.
They prevent treating this as a clean-vanilla control. Preserve the distinction
between an installed source reference, the effective VFS source and runtime
causation. No game, save, profile, playset or installed mod is edited.

## Consequential findings

### G01 — Generated treaty scripts: confirmed loader defects

[V-LOCAL / V-EXEC C382] Six reader errors explicitly name
`common/scripted_triggers/rnw_treaty_longitudes.txt:4`: three during each
world's database validation. The installed generated predicate compares the
two custom longitude values inside a hidden trigger. The engine rejects that
file; the exact grammar correction and the resulting treaty behavior remain
[UNKNOWN]. Passing our structural parser and arithmetic tests in experiment
062 did not prove engine acceptance. Treat the longitude adaptation as
**not runtime validated**, with a high-priority generator correction required.

Eight encoding notices name the three generated treaty files; all actually
lack the requested UTF-8 BOM. The loader says it will try to read them anyway,
so the BOM warning alone does not establish the trigger parser's cause.
Fifty-six localization notices cover **28** generated geography-bit identifiers
in two loads. These are separate output-completeness issues. Two other reader
errors report malformed key references with an **empty source filename**;
they cannot be assigned to this script merely because the engine origin matches.

### G02 — River export remains incompatible in the current world

[V-LOCAL / V-EXEC C382] Initial 22F4 loading logs ten river diagnostics,
including four failed components and **5,140** unprocessed pixel entries.
The later EVXP load independently logs **sixteen** diagnostics: six processing
failures totaling **2,875** unprocessed pixel entries, three malformed-tributary
clusters, six source/tributary conflicts and one ambiguous continuation at
`rnw_loc_01100`. Coordinates concentrate at or near raster columns 0/16383.
These are recorded loader failures, not harmless rendering notices. The
reported pixel total is not a count of unique rivers or lost population.

Experiment 055's one-start-per-planar-component checks did not establish the
engine's complete tributary/mesh contract. This session supplies the previously
missing negative runtime evidence for these different worlds. Investigate the
written boundary channel markers and junctions in the initial serializer,
preserving continuous physical geography. No specific engine defect, campaign
hang, terrain cause or repair is inferred from this log alone.

### G03 — Generated map locators

[V-LOCAL / V-EXEC C382] Six bounds warnings concern **two** EVXP locations:
`rnw_loc_00821` and `rnw_loc_00873`, each for city, combat and unit-stack
locators. Written anchors are respectively (16372.5, 6960.5) and
(16378.5, 6887.5); the engine reports approximately map-width separation and
zero maximum distance. This is a seam/bounding-box investigation lead, not
proof that the anchor is outside its coloured identity or that troops hang.
C377's own-identity pixel check addresses a different invariant.

One incomplete VFX-category warning and two city/VFX override-change notices
remain separate. The latter are instructions emitted by the game, not an
authorization to run locator regeneration or edit the profile. Correct the
initial generated representation where necessary; do not silence these checks.

### G04 — Starting development and setup

[V-LOCAL / V-EXEC C382] At 16:58:16, Rapampa (`rnw_loc_03856`, TTU's
starting capital) has a **level-2 granary against a runtime maximum of 1**.
Generated setup assigns `andes_town`; installed vanilla's template contains
a level-2 granary. The building cap uses `guild_max_level`, including development
and population. RNW gives the location development 8 and chooses cultural
rank templates without checking their buildings against generated capacity.
This is an incompatible template/generated-state combination, not evidence
that the generator directly writes a duplicate granary. It needs initial
setup validation/construction, preserving the vanilla building rule.

Five retained cultures have no starting pops: `chiapanec_culture`,
`toltec_culture`, `itza_culture`, `huastec_culture`, `sacha_p_qulla_culture`.
After replacement of the Americas, absence of pops is not by itself a broken
reference or a playable fault; audit retained content dependencies before
removing a culture merely to clear a warning.

Three additional game-log setup notices concern DWS and generated QJH/GVK.
They exceed diplomatic capacity by 0.6478 / 0.9961 / 1.90563 under the logger's
**hypothetical DIP-0 ruler** (required DIP 10 / 34 / 94). This is a generated
alliance-budget design risk for QJH/GVK, not an observation of their actual
ruler's capacity or a reason to grant arbitrary bonuses (compare C328).

### G05 — Expedition lifecycle

[V-LOCAL / V-EXEC C383] All **141** exhausted-route errors name
`mining_survey_expedition`, across **59 owner tags / 60 numerical destinations**.
A one-based installed-definition binding, cross-checked against the explicit
Quillaqta ID/name diagnostic, places **97** in Europe, **32** in Asia,
**7** in Africa and **5** in the generated Americas. The five American rows
name FAT, YBM, TCJ twice and ABA18. Do not carry C329's all-Old-World finding
from the different TR46 campaign into this one.

The current world overrides neither the mining type nor its events. C330's
installed-source no-travel/capital-arrival lifecycle edge remains a concrete
lead. It does not reconstruct each of these launches. **31** non-stalled
resume errors omit expedition type, owner, caller and location; they cannot
all be assigned to mining. No western-voyage pathfinding, Pacific exhaustion,
port assertion or expansion division-by-zero record occurs in this snapshot.
Their absence here does not prove those older issues fixed in every case.

### G06 — Country-name formatting

[V-LOCAL / INFERRED C383] There are **680** malformed acronym-tag warnings
and **340** country-name lookup failures between 17:47:15 and 17:47:30.
They start with the game-log civil war of the **Wattasid rebels in Morocco**
(`game.log:11476`), with the same escaped dynasty-tooltip/name pattern studied
in C347. That prior investigation attributes acronym formation to the engine;
this session independently corroborates the episode and symptom, without a
new debugger inspection. It is not a generated colonial-name failure.
Another **20** lowercase-`l` formatting warnings share the presentation family
but lack enough context to assign every one to that acronym path.

### G07 — Installed beta/DLC data and validation notices

[V-LOCAL / INFERRED / UNKNOWN C383] The session reports unavailable
`d009_across_the_pillars` descriptor/content, twelve invalid setup checks,
six skipped Iberian religious orders and twelve unavailable achievements.
There are **194** unresolved database-link records covering **27** identifiers,
**38** unknown-effect records at nineteen sites, **22** effect-postvalidation
failures, four achievement-trigger failures and **48** missing-tooltip notices
for three strings. Missing `golden_century`, `battle_for_the_strait`, related
Iberian laws/bureaucracies/succession definitions and effects form an obvious
installed-content consistency cluster. It can disable those mechanics; it is
not merely cosmetic and is not evidence of failed Great Pestilence scripts.

The named references exist in installed game sources. Some files are inherited
verbatim; RNW also rewrites whole Castilian/Portuguese/on-action/treaty-effect
files, preserving the diagnosed source references. Their presence in generated
copies alone does not establish that RNW introduced them. Twenty-nine of the
35 referenced file paths resolve directly in `in_game/`; other installed
sources include main-menu achievements, textures and portrait templates.
A matching-build vanilla control is absent, and VFS mounting limits effective
source attribution. Do not globally stub missing mechanics in RNW.

Six missing Castilian beard-template records and two unavailable
`levy_sometent` unlocks belong to this installed-source cluster. Twenty
static-database-size notices concern optimization expectations, not measured
slowdowns. Forty-two never-set-variable/flag/target warnings, six set-but-unused
warnings, nine unused modifiers and **168 possible-match suggestions** are
static analysis/hygiene diagnostics; the suggestions are not new failures.
Some absent setters follow deliberately retired American content, and static
reachability does not establish a runtime failure of every listed object.

### G08 — UI, animation and missing assets

[V-LOCAL / INFERRED C383] Three missing situation icons produce twelve VFS
and twelve GUI-texture records during reloads. Three DLC thumbnail path reads
are rejected as illegal/insecure and each has an additional glow-loader record.
This supports missing pictures/path handling, not a disease-simulation defect.

**462** invalid subunit-text records are **154** repetitions each of type,
prefix and levy-structure text lookups. The actor is omitted; exact unit data
cause remains unknown. Five missing melee-spark entities pair with five attack
state-machine failures: the corresponding animation effect fails, with no
recorded simulation/crash consequence. Danger and disease map-mode widgets
each reference an unavailable input action once. These are binding errors;
the log does not establish that the map mode itself cannot open.

The 66 additional ECS records are animation-global-variable deprecation
notices in sixteen installed animation files, separate from the mirrored spark
failures. None authorizes rewriting vanilla UI/animation files in this audit.

### G09 — Graphics and environment

[V-LOCAL C383] The two unknown-vendor notices concern enumerated **llvmpipe**,
whereas the selected Vulkan renderer is **NVIDIA GeForce RTX 4080 SUPER**.
They do not show software rendering. The graphics-context fallback version
1.0.0 occurs twice while the actual loaded game identifies as 1.4.4; these
are different fields. NVAPI driver checking was not performed, which is not a
failed driver-health test. No fatal exception, out-of-memory diagnostic or
assertion appears in the archived current error files.

### G10 — Runtime script failures and refused operations

[V-LOCAL / INFERRED / UNKNOWN C383] **2,117** `policy_vote` proposals are
rejected from the installed imperial-circles interaction; **440** western-schism
proposals are rejected from the installed religious effects (438 at line 354,
two at line 473). The files are not overridden by this world. This is the
largest error-log family and records real refused operations, but omits the
rejection reason and actors. Counts do not establish failed unique reforms,
a global HRE deadlock or RNW causation.

Ten wrong-type HRE authority changes (nine at line 774, one at 852) and nine
Majapahit list/order-value errors are separate inherited-source failures.
Their missing runtime scopes/operands prevent exact reconstruction. One
Hussite event attempts an HAB-to-HAB alliance; it cannot create that relation.
Twenty Reformation migrations have the same source and destination province;
those attempts cannot transfer population as intended. Two artist events cap
an out-of-range list index and continue with the documented clamp. One CB has
no required target character. Finally, 125 movement messages report no other
religion to switch to; no country/religion is identified. These sources are
not overridden, but indirect or mounted-resource interaction remains unknown.

### G11 — Mercenary creation in generated America

[V-LOCAL / UNKNOWN C383] At 17:59:56 the engine cannot select heavy infantry
in **Quillaqta**, ID **22920 / rnw_loc_03435**, then reports an empty mercenary
subunit array. These are **two stages of one attempted creation**, not two
independent incidents. It is a generated location, so it must not be dismissed
as an Old World-only warning. Actor, selected unit filters, current technology,
culture eligibility and initiating event are absent. The failed selection is
established; whether native military availability or an inherited caller is
wrong remains unresolved. No arbitrary unit/technology unlock follows.

## Exhaustive error-log origin accounting

[V-EXEC C381] Every captured error record is accounted for below. Times and
line numbers refer to the frozen originals, not to subsequently growing logs.

| Engine origin | Records | First evidence | Last evidence | Interpretation |
|---|---:|---|---|---|
| `gfx_caps.cpp:39` | 2 | `error.1.log:1` 16:57:15 | `error.1.log:2` 16:57:15 | G09: llvmpipe vendor discovery; NVIDIA is the selected renderer. |
| `virtualfilesystem.cpp:634` | 15 | `error.1.log:3` 16:57:19 | `error.1.log:408` 16:57:58 | G08: three situation icons and three DLC thumbnail paths unavailable. |
| `pdx_gui_texture.cpp:61` | 12 | `error.1.log:4` 16:57:19 | `error.1.log:409` 16:57:58 | G08: missing situation icons; paired texture diagnostics, not twelve distinct assets. |
| `lexer.cpp:513` | 8 | `error.1.log:9` 16:57:23 | `error.1.log:397` 16:57:58 | G01: generated treaty files lack UTF-8 BOM; loader explicitly attempts to continue. |
| `dnamodifier.cpp:342` | 6 | `error.1.log:11` 16:57:23 | `error.1.log:358` 16:57:45 | G07: three missing Castilian beard templates in installed portrait data. |
| `advance_definition.cpp:857` | 2 | `error.1.log:14` 16:57:24 | `error.1.log:359` 16:57:46 | G07: installed advance references unavailable levy_sometent. |
| `map.cpp:1256` | 4 | `error.1.log:16` 16:57:25 | `error.1.log:367` 16:57:47 | G02: ambiguous river continuation at the raster boundary; three initial-world, one EVXP records. |
| `map.cpp:1406` | 5 | `error.1.log:18` 16:57:25 | `error.1.log:368` 16:57:47 | G02: malformed tributary clusters; two initial-world, three EVXP records. |
| `map.cpp:1391` | 7 | `error.1.log:19` 16:57:25 | `error.1.log:370` 16:57:47 | G02: main-river sources encountered as tributaries; one initial-world, six EVXP records. |
| `map.cpp:1731` | 10 | `error.1.log:22` 16:57:25 | `error.1.log:376` 16:57:47 | G02: four initial-world and six EVXP river-processing failures. |
| `jomini_effect.cpp:557` | 38 | `error.1.log:26` 16:57:25 | `error.1.log:395` 16:57:49 | G07: three unavailable effect identifiers across nineteen source sites. |
| `pdx_gui_glow.cpp:322` | 3 | `error.1.log:46` 16:57:29 | `error.1.log:50` 16:57:29 | G08: three failed DLC thumbnail reads, paired with VFS records. |
| `game_dlc.cpp:443` | 2 | `error.1.log:51` 16:57:32 | `error.1.log:396` 16:57:58 | G07: d009 content has no matching DLC descriptor. |
| `pdx_persistent_reader.cpp:289` | 8 | `error.1.log:59` 16:57:32 | `error.1.log:440` 16:58:00 | G01: six treaty trigger errors; G07: two anonymous key-reference failures. |
| `jomini_trigger.cpp:275` | 4 | `error.1.log:65` 16:57:32 | `error.1.log:411` 16:57:58 | G07: two d009 achievement policy checks fail in both database loads. |
| `localization_util.cpp:103` | 56 | `error.1.log:67` 16:57:32 | `error.1.log:439` 16:57:58 | G01: 28 generated longitude-bit geography keys lack names; each reported twice. |
| `database_object_reflection.h:694` | 20 | `error.1.log:98` 16:57:34 | `error.1.log:452` 16:58:00 | G07: seven database-size mismatch variants; optimization diagnostics. |
| `persistence_tests.cpp:1068` | 48 | `error.1.log:108` 16:57:34 | `error.1.log:483` 16:58:00 | G07: three unavailable effect tooltip strings, not 48 unrelated missing texts. |
| `jomini_eventtarget.h:314` | 194 | `error.1.log:118` 16:57:34 | `error.1.log:573` 16:58:00 | G07: 27 unresolved identifiers at 89 sites; 194 records across loading/validation. |
| `jomini_effect.cpp:141` | 22 | `error.1.log:229` 16:57:34 | `error.1.log:584` 16:58:00 | G07: eleven failing modifier/tooltip effect validation sites, each repeated. |
| `jomini_effect.cpp:1165` | 42 | `error.1.log:240` 16:57:34 | `error.1.log:691` 16:58:00 | G07: 21 never-set flags/variables/targets; static validation, not proof each branch ran. |
| `jomini_effect.cpp:1207` | 168 | `error.1.log:241` 16:57:34 | `error.1.log:692` 16:58:00 | G07: possible-match suggestions attached to other warnings; not independent errors. |
| `jomini_effect.cpp:1160` | 6 | `error.1.log:280` 16:57:34 | `error.1.log:652` 16:58:00 | G07: three set-but-unused variable notices. |
| `game_object_locators.cpp:1272` | 6 | `error.1.log:693` 16:58:02 | `error.1.log:698` 16:58:02 | G03: city/combat/unit_stack bounds fail for two generated identities. |
| `game_object_locators.cpp:1158` | 1 | `error.1.log:699` 16:58:02 | `error.1.log:699` 16:58:02 | G03: incomplete VFX locator category. |
| `manual_locators_database.cpp:212` | 2 | `error.1.log:700` 16:58:02 | `error.1.log:701` 16:58:02 | G03: city/VFX override regeneration notices; do not execute the suggested mutation. |
| `dlc_setup_reader.h:18` | 12 | `error.1.log:702` 16:58:04 | `error.1.log:713` 16:58:04 | G07: twelve setup checks refer to unknown d009 DLC. |
| `static_modifier.cpp:537` | 9 | `error.1.log:714` 16:58:15 | `error.1.log:722` 16:58:15 | G07: nine unused modifiers; hygiene notices. |
| `religious_order_manager.cpp:157` | 6 | `error.1.log:723` 16:58:15 | `error.1.log:728` 16:58:15 | G07: six religious orders skipped for unknown d009 DLC. |
| `initialize_from_bookmark.cpp:1470` | 5 | `error.1.log:729` 16:58:16 | `error.1.log:733` 16:58:16 | G04: five retained cultures have no starting population. |
| `building_manager.cpp:136` | 1 | `error.1.log:734` 16:58:16 | `error.1.log:734` 16:58:16 | G04: Rapampa granary level 2 exceeds runtime cap 1. |
| `pdx_achievements_steam.cpp:298` | 12 | `error.1.log:735` 16:58:27 | `error.1.log:746` 16:58:27 | G07: twelve achievement identifiers unavailable. |
| `expedition_manager.cpp:675` | 141 | `error.1.log:747` 17:03:09 | `error.log:1115` 18:07:03 | G05: 141 mining surveys fail after exhausting waypoints; 59 tags / 60 destinations. |
| `jomini_custom_text.h:93` | 308 | `error.1.log:750` 17:04:44 | `error.log:728` 18:02:17 | G08: 154 missing subunit type texts plus 154 missing prefix texts. |
| `jomini_custom_text.h:108` | 154 | `error.1.log:752` 17:04:44 | `error.log:729` 18:02:17 | G08: 154 invalid levy-structure text objects; same presentation family. |
| `expedition_effects.cpp:352` | 31 | `error.1.log:766` 17:12:57 | `error.log:855` 18:03:32 | G05: 31 anonymous resume attempts on non-stalled expeditions. |
| `jomini_scriptlists.cpp:414` | 2 | `error.1.log:786` 17:16:40 | `error.1.log:1575` 17:41:18 | G10: two artist-event list-index caps; fallback explicitly logged. |
| `diplomacy.cpp:5979` | 1 | `error.1.log:794` 17:19:09 | `error.1.log:794` 17:19:09 | G10: one CB lacks its required target character; actor/caller omitted. |
| `common_effects.cpp:3246` | 2557 | `error.1.log:796` 17:19:52 | `error.log:1159` 18:07:17 | G10: 2,117 rejected policy_vote proposals and 440 western-schism proposals. |
| `jomini_scriptvalue.cpp:1965` | 19 | `error.1.log:1238` 17:20:44 | `error.log:1164` 18:07:23 | G10: ten HRE authority-value and nine Majapahit wrong-type evaluations. |
| `country_effects.cpp:4972` | 1 | `error.1.log:1239` 17:20:44 | `error.1.log:1239` 17:20:44 | G10: Hussite event tries to ally HAB to HAB. |
| `pdx_text_formatter.cpp:807` | 700 | `error.1.log:2041` 17:47:15 | `error.1.log:3112` 17:47:30 | G06: 680 malformed acronym tags plus twenty lowercase-l formatting warnings. |
| `countryname.cpp:1135` | 340 | `error.1.log:2043` 17:47:15 | `error.1.log:3113` 17:47:30 | G06: 340 unreadable country-name data calls during the Morocco rebel episode. |
| `pdx_gui_widget.cpp:3891` | 2 | `error.1.log:3741` 17:54:26 | `error.log:508` 18:00:49 | G08: danger/disease map-mode input actions absent; one each. |
| `particle_event.h:114` | 5 | `error.1.log:3825` 17:55:31 | `error.log:93` 17:56:26 | G08: five missing melee spark entities. |
| `state_event.h:391` | 5 | `error.1.log:3826` 17:55:31 | `error.log:94` 17:56:26 | G08: five corresponding attack-animation event failures. |
| `common_effects.cpp:2498` | 20 | `error.log:92` 17:56:26 | `error.log:1167` 18:07:24 | G10: twenty Reformation migrations target their own source province. |
| `common_effects.cpp:2698` | 1 | `error.log:398` 17:59:56 | `error.log:398` 17:59:56 | G11: no eligible heavy-infantry subunit at Quillaqta. |
| `common_effects.cpp:2758` | 1 | `error.log:399` 17:59:56 | `error.log:399` 17:59:56 | G11: the same mercenary creation has an empty subunit array. |
| `movement.cpp:156` | 125 | `error.log:849` 18:03:30 | `error.log:1177` 18:07:33 | G10: 125 movements have no alternative religion; actor/selection reason omitted. |

Total: **5,149**. Private `error-catalog.json` retains all 427 exact variants;
source excerpts and raw logs are not distributed.

## All AI-warning categories

[V-EXEC / UNKNOWN C381] The snapshot contains **52,615 timestamped headers**:
**52,317 complete execution warnings**, **297 complete posting warnings** and
**one incomplete final execution record**. That buffered tail lacks its command
and is not a 44th known command category. The **43 complete stage/command
categories** below sum to **52,614**. These records omit actor, target, reason
and successful-command denominator; they establish refusals, not a failure
rate, native-expansion defect or campaign-wide AI inactivity (C333).

| Stage | Command | Complete records |
|---|---|---:|
| execute | `set_cabinet_action` | 32483 |
| execute | `disband_subunit` | 5222 |
| execute | `build_road` | 3143 |
| execute | `diplomaticactioncommand` | 2712 |
| execute | `transfer_occupation` | 2014 |
| execute | `change_trade_capacity` | 1733 |
| execute | `toggle_can_attach_to` | 1375 |
| execute | `split_unit` | 772 |
| execute | `construct_building` | 691 |
| execute | `merge_army` | 594 |
| execute | `move_unit` | 327 |
| execute | `add_bureaucracy` | 302 |
| execute | `upgrade_rgo` | 251 |
| posting | `diplomaticactioncommand` | 180 |
| execute | `create_supply_depot` | 176 |
| execute | `detach_unit` | 137 |
| posting | `move_unit` | 107 |
| execute | `asssume_siege_control` | 61 |
| execute | `set_unit_activity` | 53 |
| execute | `use_unit_ability` | 46 |
| execute | `raise_all_levies` | 33 |
| execute | `hire_mercenary_from_leader` | 33 |
| execute | `production_methods` | 30 |
| execute | `perform_generic_action` | 22 |
| execute | `take_over_siege` | 21 |
| execute | `refill_garrison` | 15 |
| execute | `attach_unit` | 13 |
| execute | `embark_army` | 10 |
| posting | `destroy_building` | 10 |
| execute | `disband_unit` | 9 |
| execute | `construct_unit` | 8 |
| execute | `consolidate` | 6 |
| execute | `found_city` | 6 |
| execute | `invite_scholars` | 3 |
| execute | `military_objective_unassign_unit` | 3 |
| execute | `marry_noble_command` | 2 |
| execute | `vote_on_resolution` | 2 |
| execute | `decision_taken` | 2 |
| execute | `revoke_privilege` | 2 |
| execute | `balance_army` | 2 |
| execute | `perform_character_interaction_command` | 1 |
| execute | `upgrade_subunit` | 1 |
| execute | `propose_resolution` | 1 |

## Additional diagnostics outside the error files

[V-LOCAL / V-EXEC C381, C383] The complete origin inventory was reviewed,
including logs without error entries. The following adds context/families;
mirrors above are excluded. Normal wars, revolts, loading, saves, successful
allocations and zero-count repair summaries are not errors.

| Log / origin | Records | Meaning and limit |
|---|---:|---|
| debug / `pdx_paths.cpp:69` | 1 | Optional checksummed-path settings absent; no checksum validation is thereby established. |
| debug / `systemsettings.cpp:354` | 2 | Default settings filenames chosen. |
| debug / `gfx_vk_master_context.cpp:122` | 2 | Graphics-context version fallback; not actual game version. |
| debug / `pdx_localize.cpp:257` | 226 | 56 duplicate-localization variants during reloads; final winner/visual impact varies. |
| debug / `pdx_json_settings.cpp:450` | 7 | Three variants of absent settings fields. |
| debug / `pdx_json_settings.cpp:550` | 8 | Four variants of settings categories not written. |
| debug / `pdx_json_doc_serialize.cpp:100` | 28992 | 28 skipped-member variants, mostly color entries and metadata; verbosity is not evidence of corrupted saves. |
| debug / `pdxfilewatcher.cpp:197` | 1 | Unmounted skins path limits hot reload. |
| debug / `pdxfilewatcher_windows.cpp:333` | 2 | Missing/invalid tools_import path; editor import watcher. |
| debug / `defines.cpp:230` | 46 | 23 unavailable define/macro variants; installed config/executable consistency lead, no measured effect. |
| debug / `genedatabase.cpp:541` | 4 | Empty special gene categories during initialization; the message explicitly allows this initialization mode. |
| debug / `gfx_vk_swapchain.cpp:384` | 1 | Suboptimal swapchain result, no recorded fatal graphics failure. |
| debug / `icondatabase.h:273` | 34 | 15 default-icon lookup/fallback variants. |
| debug / `status_widget.cpp:192` | 4 | Account-status widget unavailable. |
| debug / `pdx_ecs_context.cpp:260` | 10 | Deleted/unregistered presentation-world reference during context changes; no exception recorded. |
| debug / `pdx_ecs_context.cpp:295`, `:320` | 1 + 1 | Repeated debug-world/spawn-getter setup; affects debug spawning context. |
| debug / `jomini_trigger.cpp:102` | 7920 | Triggers added after validation; no named caller, so do not assign them all to treaty scripts. |
| debug / `savegameinfo.cpp:402` | 52 | 26 text setup files read as text after a file-magic warning, twice. |
| debug / `audio2_wwise.cpp:811`, `audio_state.cpp:184` | 2 + 2 | Winter-level sound parameter absent; paired reports. |
| debug / `camera_state_ambience_node.cpp:47` | 1608 | 1607 complete MapHeight sound-limit notices plus one partial buffered tail. |
| debug / `rivers_ambience_node.cpp:20` | 1617 | River sound alias absent; independent of river raster loader failures. |
| game / `message_handler.cpp:381` | 10 | Five duplicate message-type declarations during reloads. |
| game / `advance_manager.cpp:168` | 6 | Missing age advance trees are created; initialization behavior, not six failed researches. |
| game / `initialize_from_bookmark.cpp:1396` | 3 | DIP-0 capacity estimates for DWS/QJH/GVK; see G04. |
| ecs / `state_machine_parse_helpers.h:389` | 66 | Animation variable placement deprecations; see G08. |
| graphics / `gfx_driver_check.cpp:114` | 1 | NVAPI check not performed; not a driver failure. |
| dedicated server | 2 warning lines within 15 records | Observer return is restricted by the active country-switch game rule; expected rule warning. |

`database_conflicts.log` and `warning.log` are empty. `multiplayer.log` contains
session lifecycle/network selection, not a new failure family. Performance
samples are telemetry, not an out-of-memory or memory-leak diagnosis. The
remaining system/setup/code-revision entries provide environment and successful
initialization context. The event CSV and older rotated logs are outside the
current-session count.

## Great Pestilence: original question

[V-LOCAL / INFERRED / UNKNOWN C384] `game.log:14020` records situation start
on **1 March 1540**, at wall-clock **18:03:28**. Métahi is the generated name
of `rnw_loc_02875`. Installed vanilla's situation GUI uses the original
outbreak's total deaths for its upper counter (`:72`), but asks for affected
locations **in Player.Self's country** (`:147`) and deaths **in Player.Self's
country** (`:236`) below. EVXP overrides none of that panel, disease definition,
situation or event file. The screenshot's observer banner plus these distinct
queries explains the two lower zeros; they are not a global affected-location
count. Observer-mode zero country statistics are expected from this context,
not proof of an epidemic that killed people in zero places.

No direct Great Pestilence/original-outbreak/these-counter error is present
in either current error file. The disease-map input binding failure predates
the situation and concerns a different interface action. The screenshot's
**29.648M** value, actual death arithmetic, origin state and eventual situation
completion are not independently reconstructed from logs. A no-error search
is not proof of complete disease correctness.

## Disposition and verification

Prioritize **G01 treaty acceptance**, **G02 river serialization**, **G03 locator
bounds**, and **G04 compatible starting buildings** as concrete RNW work;
retain **G11 mercenaries** and QJH/GVK capacity as scoped investigations.
Inherited-source lifecycle/data/UI failures remain explicit, with no blanket
vanilla/engine attribution and no requested new owner campaign.

This is a diagnostic phase: no generator output, game assets, binary reader,
process memory, product version, epoch, reference world or installation changes.
Counts are reconciled to every origin and complete AI category; frozen original
hashes are rechecked. Locked sync and full check pass: **2,005 Python tests,
14 skips, 23 Rust tests**, format/lint/types clean. Code tests cannot establish
engine acceptance of the already logged defects.

## Follow-up: campaign continued through 1682

[V-LOCAL / V-EXEC C385] A read-only snapshot of all 27 current `.log` files was
captured at **19:01:36 CET** under ignored
`local_data/pestilence-20261026/followup-1901/`; every file was stable during
its read and has a recorded SHA-256. PID 4018904 was still running at capture.
`error.1.log` is unchanged, and the first 1,177 parsed records of the new
`error.log` exactly match the first snapshot, so the **3,947** following records
are a clean delta from **18:07:35–19:01:28**. The current-launch total is now
**9,096 errors, 52 origins and 445 exact variants**. These remain log records,
not 9,096 independently established defects.

| New error records | Logged signature | Reading and limit |
|---:|---|---|
| 3,340 | `movement.cpp:156`: “No other religions to move away from a movement to” | Same family as the initial 125; the session total is 3,465. Actor and movement-selection context remain absent. |
| 351 | `jomini_custom_text.h:93/:108`: invalid `sub_unit` for `subunit_type_`, `subunit_prefix`, and `subunit_structure_army_levy` (117 each) | Repeated presentation/custom-text failures; caller and visible impact are not identified. |
| 90 | `expedition_manager.cpp:675`: route exhausted without adding a waypoint or ending the expedition | 89 mining surveys and one Pacific crossing; the engine logs that it fails these expeditions. Across the launch this is 230 mining surveys plus one Pacific crossing. |
| 72 | `common_effects.cpp:3246`: `propose_resolution 'policy_vote'` rejected at `imperial_circles.txt:375` | Repeats the earlier rejected-resolution family. |
| 55 | `common_effects.cpp:2498`: migration from and to the same province; 51 at `settle_the_frontier.txt:111`, four at `reformation.txt:871` | Immediate callers are identified, but no log gives the scopes or whether a generated location caused the equality. The installed frontier script checks that source and target exist, then passes them to `add_migration` without an explicit distinct-province guard. This is a concrete rejected no-op, with effective VFS attribution still bounded. |
| 24 | `expedition_effects.cpp:352`: `resume_expedition` called when the expedition is not stalled | Repeated invalid lifecycle calls; caller is not logged. |
| 5 + 1 | `common_effects.cpp:2698` cannot find heavy-infantry subunits at Kobda, Sadak, Ushkan, Manysai and Tumain; `:2758` reports an empty mercenary subunit array | Five failed creation attempts and one follow-on empty-array error; eligibility and callers remain unknown. |
| 4 | `pdx_ecs_entity_3d_utils.cpp:608`: failed to attach entity to `cargo_lctr` | Also appears four times in `ecs.log`; count mirrors are not added twice. Runtime impact is unknown. |
| 2 | `jomini_scriptlists.cpp:414`: list position capped at `artist_events.txt:2579` | Bounded list-index diagnostic. |
| 2 | `jomini_scriptvalue.cpp:1965`: `none/any` value at `events/hre.txt:1047` and `:852` | Two wrong-type script values; whether the guarded branches were reached is unknown. |
| 1 | `ai_tick_context.cpp:169`: building candidate truncation 56 with only two candidates for BRB | Engine clamps the candidate count; downstream choice is not recorded. |

The table totals all **3,947** new error-log records. Eighteen exact message
variants are new to this launch; the only new error origins are the candidate
truncation and cargo-locator attachment diagnostics. Four cargo-locator lines
are mirrored in ECS output. No direct Great Pestilence error appears.

`ai.log` now has **92,956 complete warnings** and one unfinished tail; the
previous partial final record was completed in the continuation. This snapshot
adds **40,341** complete AI warnings and five command/warning categories:
`assign_commander`, `cancel_construction`, `deposit_food`, `redeem_bonds`, and
“too many loans.” The largest new groups are invalid `set_cabinet_action`
(26,898), `change_trade_capacity` (3,040), `disband_subunit` (2,072),
`build_road` (1,559), and `diplomaticactioncommand` (1,376). They are rejected
AI commands or AI-context warnings, not proof that each command changed game
state. `debug.log` adds 5,239 timestamped entries, mostly the already known
missing river ambience alias (1,500) and `MapHeight` sound limit (1,493).
Four ECS attach failures mirror the error log; the additional dedicated-server
lines are speed and pause toggles.

### Great Pestilence after the continuation

[V-LOCAL / INFERRED / UNKNOWN C386] `game.log` reaches **1 January 1682** at
19:01:02. It records Great Pestilence starting on 1 March 1540, but no end entry
through the captured tail at 19:01:28. The same log does record other situation
starts and ends during this period. This is evidence of no logged Pestilence
completion, not a readout of its current UI state or disease counters.

The installed 1.4.4 `common/situations/great_pestilence.txt` has no calendar
timeout in its outcome. It requires all three region flags (Caribbean,
Mesoamerica and Andes), the disease to be inactive, and no more than 30 settled
American countries left without `had_great_pestilence`. The disease script can
also spread into new colonies while the situation is ongoing. Thus a long-lived
situation is compatible with the installed script if any outcome condition is
still unmet; the logs do not expose which one, and a save-state inspection would
be needed to say whether the situation remains active or identify an unmet
condition. No mod or engine defect is established by the missing end entry.

At 19:01:13, `debug.log` records the `disease_outbreak_manager` serialization
section as 10.81 MB (4.00 MB reserved, 3.55 ms). These are writer telemetry, not
death or affected-location counters. The screenshot's 29.648M value still is
not independently reconstructed. The two observer-mode country counters
remain consistent with the country-scoped vanilla UI queries described above.

## Colonial range and East Asian AI

[V-LOCAL / V-EXEC C387–C388] C387's earlier cutoff was 1 January 1727. A
captured continuation now reaches **1 January 1795** and contains **1,460**
colonization-start log records: **131** by Muscovy and **zero** by Ashikaga.
These are start events, not unique completed colonies. The captured
`error.log` and `ai.log` contain no lines with colonial, colonization,
charter, or range terms. The stable three-file snapshot and hashes are under
ignored `local_data/colonial-ai-20261026/followup-1795/`. These logs show no
Japanese start through that cutoff, but do not record failed target checks,
the selected game rules, or current country range values.

[V-LOCAL C388] The installed vanilla rules set both `ai_colonisation_rule` and
`ai_exploration_rule` to western-only by default. The colonization define allows
AI capitals on Europe to colonize under that rule; the exploration trigger
likewise requires Europe (or a European overlord for a subject), unless the
respective `all_countries_*` rule is selected. Ashikaga's Asian capital has no
exception. The vanilla setup also gives non-American-capital AI countries a
`-0.9` American exploration preference. Muscovy is eligible under the default
because its capital is European, and receives additional Siberia/Alaska
exploration preferences from vanilla country effects/events. The current logs
show its route advancing through Yakutia, Koryak and Itelmen locations.

[OWNER / INFERRED C388] The owner reports leaving the game rules at their
defaults. If so, the default western-only AI rules explain why AI-controlled
Japan does not explore and colonize America. The exact rule state is not
independently read from the campaign save; logs do not print it. Selecting
`all_countries_colonize` and `all_countries_explore` at setup would remove this
AI eligibility restriction in a future campaign. These rules do not set the
`Within Colonial Range` overlay and do not prevent a player-controlled Japan
from colonizing.

[V-LOCAL / V-EXEC C388] The range overlay is a separate calculation. Vanilla
starts with `naval_range = 1000` and `colonial_range = 1000` as distinct
modifiers; advances add colonial range. The active RNW world does not override
the game-rule file, colonization defines, exploration preferences or vanilla
static modifiers containing `colonial_range`; those relevant static-modifier
blocks match vanilla exactly. The mod carries a modified copy of
`exploration_triggers.txt` to add generated American sea areas to its discovery
check, but its `country_can_start_exploration_trigger` block matches vanilla
exactly. Its `_hardcoded.txt` retains the vanilla calls that initialize area
preferences. The mod does replace map geography and port positions.

For one generated Alaska-region target, `rnw_loc_00677`, its map port is
(2683, 7083). In the active map's 16384-pixel-wide wrapped coordinate grid,
the northern Japanese-region port Shumushu (14804, 6337) is about **4,328**
straight-line map units away; the far-eastern Siberian port Nuvuqaq (16328,
7431) is about **2,761**. This makes that target about 1.57 times farther from
the Japanese-side candidate than the Siberian-side candidate. These are
coordinate comparisons, **not** asserted engine colonial-distance values;
ownership of those two source ports at the relevant date is not established by
the logs. The difference is nevertheless consistent with Muscovy gaining
nearer source ports as it colonizes Siberia while Japan remains farther away.

[INFERRED / UNKNOWN C388] The observed asymmetry is consistent with vanilla
AI rules and preferences plus the active world's geography; no logged script
or range error, nor active-mod range override, points to a mod logic defect.
The default rules explain AI Japan's lack of colonization, while port geography
and possibly different advance-derived colonial-range totals explain the
overlay. The screenshot has no hovered target or numeric range. Since the
engine's exact distance calculation and current country values are not exposed
in these logs/scripts, the exact yellow/gray cutoff remains unverified. A
count of reachable sea zones or naval range alone does not establish colonial
range.

## Final follow-up: campaign reached 1 January 1849

[OWNER / V-LOCAL / V-EXEC / INFERRED / UNKNOWN C389] A stable, read-only
snapshot of the 28 log files was captured after the owner saved and closed the
campaign, under ignored `local_data/campaign-1849-20261026/logs/`; raw logs are
not committed. `game.log` records `NEW YEAR: 1849` at 20:25:50 and continues
through 20:29:29. It does not record a 1850 rollover, so the evidence proves
entry into 1849, not completion of the entire calendar year. At 20:29:23–29,
`debug.log` records the persistent writer serializing game managers, including
the situation and disease managers, then `Savegame time 5.878` and
`Quit: Quit from inside game`, followed by `Game->MainMenu`. This is consistent
with the owner's save and an orderly exit; the save file itself was not read
or independently validated.

The three current-launch error rotations contain **21,820 timestamped
records**, **53 source-line origins** and **464 exact message variants**;
**12,724** records were added after the 19:01:35 checkpoint. These are repeated
log records, not that many independent defects. The largest new families are
6,934 unknown lowercase-`l` text-format tags, 2,922 list-position caps, 1,655
rejected `policy_vote` proposals and 1,011 invalid `sub_unit` display-text
lookups. Other repeated failures include 78 expeditions explicitly failed
after exhausting their routes, 67 same-province migration attempts, 27
`resume_expedition` calls on expeditions that were not stalled and 15 cargo
locator attachment failures; smaller families are seven wrong-type script
values, five truncated building-candidate lists and one rejected invalid
`calligrapher` artist. These indicate broken or rejected individual actions
and text lookups, but they did not prevent the campaign from progressing to
1849. No direct Great Pestilence, colonial-range or colonization error appears
in the current error logs. The AI log has 181,546 `[AI Warning]` records and
no line containing `colon` or `range`. No explicit fatal, crash, assertion,
out-of-memory or segmentation-fault marker appears in the current error logs.

[V-LOCAL / INFERRED C389] Most of the newly frequent list caps cite vanilla
script sites. Although the world mod carries a copy of
`common/scripted_effects/situation_effects.txt`, its edits are confined to
Tordesillas handling; the three capped-list sites around lines 1004, 1043 and
1082 are unchanged. Other repeated source files for list caps, policy votes,
same-province migration and invalid artist creation are not overridden by the
world mod. This weighs against attributing those repeated errors to EVXP.
The text-format and sub-unit messages have no logged callsite, so their exact
origin and visible impact remain unknown.

[V-LOCAL / INFERRED / UNKNOWN C389] The log still records Great Pestilence
starting on 1 March 1540 and records no end by the 1849 tail. No related error
is present. Vanilla has no time limit for its outcome: regional infection,
disease exhaustion and the remaining uninfected American-country threshold
must all be met. A 309-year span with no end entry is therefore compatible
with unmet outcome conditions; the logs do not say which condition remained
false, or prove the final UI state. The observer-panel zeroes remain
country-scoped values, not a global count of zero affected locations.

[V-LOCAL / INFERRED / UNKNOWN C389] The final `game.log` contains **1,875
colonization-start records**, including **144** attributed to Muscovy and
**none** attributed to Ashikaga. None of the checked Japanese, Korean or
Chinese polity labels appears as a colonizer. These are starts, not completed
colonies, and country renames/control cannot be reconstructed from these
records alone. This extends the pattern seen through 1795 and remains
consistent with the default western-only AI colonization/exploration rules
reported by the owner; it does not measure Japan's live range overlay or prove
the saved rule state. `event_log.csv` is stale from 23 October and was not used
to infer the campaign's final state.

The frozen manifest records the snapshot hashes. No save, settings, playset,
installed mod, game process or game installation was changed, and EU5 was not
launched for this follow-up.
