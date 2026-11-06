# New World content

N0–N5 are implemented and included in the accepted 1.0.0 product (C437).
The exporter adapts content that refers to the Americas to generated geography
and societies. It also supplies original stories, formations and colonial names.
The [catalogue](content-catalog.md) describes player content; the generated
[reference](content-reference.md) lists definitions in detail.

## One decision for every vanilla consumer

`content_inventory.py` inventories references to replaced American keys/tags.
`content_decisions.py` decides each object: keep, rebind, neutralize or replace.
`content_check.py` stops export on an undecided required consumer;
`content_report.py` provides the report. The table stores identifiers and decisions,
not redistributed vanilla scripts. `eu5_content.py`, `eu5_remap.py` and related
writers apply them locally from the installed game.

The 1.4.5 / Across the Pillars audit found 655 consumers, including 19 newly
requiring decisions; 0.13.22/epoch 59 supplies them (C426–C427). New patches need
an updated inventory rather than a blanket assumption that all new objects work.
The [compatibility audit](research/compatibility-1-4-5.md) holds exact dispositions
and limits of runtime observations.

## Generated stories and formations (N2–N4)

`content.py` plans content eligibility for each world's states; `storymodel.py`
defines scripts, graphs and pulse checks. `stories.py`, `stories_n4.py` and
`stories_colonial.py` hold the story families. `formations.py` and
`colonial_names.py` define formables and names. `eu5_story.py`, `eu5_formation.py`
and `eu5_places.py` write their game records.

For 1.2.0, phases N6–N9 of the [history plan](history-plan.md#22-goals-and-consequences-in-play-2026-11-06)
rework the formable goals and add political inheritance, AI goals and events driven
by the recorded past (D29).

Keep vanilla mechanisms where they express the feature. All scripts and hooks
belong to the generated world, never an enabled companion/probe mod. Conditions
and outcomes must resolve against the actual generated geography and societies;
validate references, localization and graph consistency at construction.

## Geography keys chosen for content (N5)

Generated regions and land areas reuse the needed vanilla identities within their
original hierarchy. Subcontinents are north-to-south bands. A region key goes to the
part that lies where the key lies in its vanilla subcontinent, and physical similarity
chooses among comparable places. An area key goes to the physically closest part, and
place breaks ties. The [N5 audit](research/n5-region-keys.md) records the
matching policy and all positional consumers. `hierarchy.py` and the New World
exporter construct and verify the hierarchy. Preserve the Old World and treat
content meaning as part of generation, not a repair layer over already-written output.

## History continuity (H6, 1.2.0 development)

Existing families now consume the historical final start. `history_content.py`
selects location-based countries, including landed highland confederates, and
supplies surviving cooperation, rivalries, directed dependencies and verified
physical contacts. Pop-type tribes remain ineligible bearers because their setup
has no location ownership/capital. Retired bootstrap actors never become live tags.
No new family or quota is introduced; a missing opportunity retains its reason.

| Family | Reviewed binding |
|---|---|
| River centre | Current owner, population/settlement centre and actual river |
| Sacred centre | Current holder and its faith at the actual sacred place |
| Harvest | Current populated centre and its high ground/population threshold |
| Route market | Two centres connected through the current bearer's own land |
| Great alliance | Shared border and faith/culture, actual surviving cooperative bargain or positive memory, no current rivalry or direct subject relationship |
| Empire periphery | Current overlord/subject pair; farthest capital over actual physical contacts, including verified maritime passages |
| River union | Current river geography, centres and multiple landed bearers |
| Highland confederation | Current connected highland territory, relief share and landed bearers |
| Maritime league | Current coastal territory and actual shared sea zones |
| Cultural union | Current inhabitants' culture-group membership and landed bearers |
| Regional realm | Current region, centres and multiple landed bearers |
| Postcolonial federation | Existing colonial-shore geography; the later colonial story/pulse remains unchanged |

Geographical territory rules and per-country story limits remain. Maritime travel
for a distant subject does not create an edge in a river basin or land formation.
Council and periphery opportunities retain their exact backward causes in the
report's `historical_bindings`. The council's opening no longer invents generations
of complaints or shared enemies. Its revised English and all ten translations
retain the existing runtime country/place scopes. The periphery event gate now
requires the current owner to remain a subject of the bearer; its scheduled cleanup
still runs after a broken binding. Other existing ownership guards remain.

[V-LOCAL, EU5 1.4.7 / 26377361, 2026-11-04] Landed confederates use
`own_control_core` and an explicit capital, with no `type = pop`; the installed
tribal government has country court and estate settings. The `is_subject_of = root` gate has
installed event precedents (for example `flavor_BOS.txt`). This is source/serializer
evidence, not a new claim of observed campaign outcomes.

[V-EXEC] Full checks pass: 2,723 Python tests, 17 optional skips, strict types/lint,
23 Rust tests; 15 read-only installed checks pass with two optional skips. New cases
cover cooperative/hostile eligibility, causal bindings, historical maritime travel,
landed confederates, dead/missing actors, stale dependencies and the parsed runtime
subject gate/cleanup. All eleven language catalogues and the generated content
reference pass. On the independently simulated real H4 reference plan, the actual
story writers produce all twelve existing families, 28 files and five explained
council/periphery bindings, with no missing cause or absence. Full writers/output
checks then pass for 872 nonmetadata world files, digest
`4fed89a3b0edca6e8974b539670826bbc45c831a1d453fadc4db4c2436f5b9f5`,
using that compact native plan only after exact relevant-input comparison. This
refreshes the pending epoch-61 reference; the frozen epoch-60 reference is unchanged.
The reused native stage is not an uncached end-to-end timing or reproduction test.
H7 retains final calibration, normal reproduction, package/candidate delivery and
the bounded owner-only engine observations. Local evidence is under
`local_data/history-120/h6-*`; no partial candidate or hub was installed.

## Changes and verification

A new story, family or compatible option normally belongs in MINOR; compatible
corrections belong in PATCH. Use the release-level rules of
[ADR 0003](adr/0003-versioning.md), affected goldens and a pending world epoch
when nonmetadata world files change. Translate affected player text into the
official languages and update catalogue/reference output where definitions change.

Synthetic content tests and read-only installed-game checks establish written
syntax, dispositions, references and deterministic output. Owner sessions and logs
establish their own observed engine behavior. Historical per-family unknowns are
research scope, not a demand to rerun every story before each change; use the
[current verification workflow](testing.md).

The [original implementation plan](archive/content-implementation-plan-0.x.md)
preserves the gap analysis, stage breakdown, hook experiments and final-audit
checklists. Its per-commit versioning and pending 0.x acceptance instructions are
superseded by the current release policy and owner acceptance.
