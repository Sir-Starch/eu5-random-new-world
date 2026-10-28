# Dynamic content catalogue

What RNW adds to a campaign: **8 story families (32 visible events and 72 choices),
6 families of formable countries, colonial naming traditions and 5 kinds of
exceptional resource places**. This catalogue describes implemented content, with
spoilers. The [complete reference](content-reference.md) lists every event title,
choice, effect, delay, AI weight, modifier and identifier. [V-EXEC C409]

All of this belongs to the generated world's mod. The hub carries the generator;
it adds no campaign content. Names, participants and territories depend on the
world, so there is no universal list of named RNW countries. A family may be absent
when a world has no suitable opportunity. [V-EXEC C193, C218, C409]

These are descriptions of what the generator writes. Offline checks and observed
gameplay are different evidence: the river pilot and formation hooks were seen in
part in EU5 1.4.4, while not every story path or natural start has been observed.
See [known limitations](known-limitations.md), [N3 experiment](../experiments/035-new-world-content-n3/README.md)
and [N4 experiment](../experiments/039-new-world-content-n4/README.md) for the
boundaries. [V-GAME C199–C211; UNKNOWN C214, C217, C220]

## Contents

- [When stories start](#when-stories-start)
- [Stories and their choices](#stories-and-their-choices)
- [Formable countries](#formable-countries)
- [Colonial names](#colonial-names)
- [Exceptional places and starting societies](#exceptional-places-and-starting-societies)
- [Vanilla content](#vanilla-content)
- [Inspecting one particular world](#inspecting-one-particular-world)
- [Maintaining this catalogue](#maintaining-this-catalogue)

## When stories start

The first six families are assigned to suitable countries and places during
generation. A country receives at most two of these opportunities, with at most
one per family. A place claimed as a story centre is not reused as another claimed
centre; capitals can also serve as unclaimed anchors. The cap is a cap on assigned
opportunities, not a guarantee that both will happen. [V-EXEC C409]

Each opportunity has its own 45-year dynamic historical event window. Its initial
start year is drawn from **1340–1397**, with **2–5% monthly chance**; a conflicting
start year for the same country is moved forward. This separates the windows'
start years, rather than guaranteeing that two stories cannot fire in one year.
The country must still own the centre when the start event fires; the road story
also requires both endpoints. The exact window, country and location are in that
world's hidden start event. [V-EXEC C409]

**Contact** and **Colony** instead find participants during play through the yearly
country pulse. Contact has a **4% yearly start chance** and **60-year cooldown**;
Colony has **6%** and **40 years**. Their conditions below must be met. These are
scripted start chances, not measured campaign frequencies. [V-EXEC C218, C409]

Each chain has four visible events: one opening offers three branches, each of
which leads to its own follow-up with two endings. You normally see two events,
not all four. Follow-ups arrive after a branch-specific delay of **24–84 months**.
Each visible event checks ownership of the centre again, and some require a
separate partner owner or ownership of the second location. Interrupted chains
have a hidden state cleanup scheduled **15 years** after starting. This clears
story variables; timed modifiers retain their own durations. [V-EXEC C409]

Gold rewards and costs use the game's scaled gold effect; a scale of `-3` is not
three gold. Paid choices are available only with **more than 100 gold**. Stability,
legitimacy and prestige likewise use vanilla symbolic scales. Modifier payloads
are copied from the installed game's sources at generation time, under RNW's own
names and texts; exact numerical bonuses therefore belong to that world's files
and in-game tooltips. [V-EXEC C193, C409]

## Stories and their choices

Every family below links to its full event and outcome tables. Conditions in the
first six rows select starting opportunities; they do not continuously assign
new ones after conquests. [V-EXEC C409]

| Story | Who can receive it | Opening choices and consequences |
|---|---|---|
| [River centre](content-reference.md#river_centre) — **The River Turns** | A state-owned centre on a river; at most 4 per world | Pay for embankments, then fund granaries or take the surplus; collect tolls and later face a flood, paying to clear it or accepting damage; entrust the banks to guilds, then confirm their charter or reclaim revenues at a political cost. |
| [Sacred centre](content-reference.md#sacred_centre) — **Pilgrims at the Gate** | A holy place whose owner shares its local religion; at most 4 | Endow the shrine, then build a great temple or recover income; tax offerings, then return part or face the priests; seat the high priest among the estates, then welcome or restrict the priesthood. The priesthood branch unlocks an estate privilege. |
| [Harvest and food supply](content-reference.md#harvest) — **A Thin Harvest** | A centre on hills, mountains or plateau, or among the most populous tenth of state-owned places; at most 3 | The opening reduces the centre's province food by the vanilla `-0.2` effect. Buy grain and later charter merchants or fund public granaries; ration village stores, then compensate the villages or refuse; clear new fields, then grant them to families or sell them. |
| [Route and market](content-reference.md#route_market) — **A Road Between Two Cities** | Two centres held by one state, joined by a route of 2–8 location steps over its own land; at most 3 | Fund a road, then maintain it or collect tolls; let merchants build it, then cap or defend their tolls; agree on village market days, then charter fairs or leave them local. Both endpoints must remain yours. |
| [Great alliance](content-reference.md#great_alliance) — **Envoys From the Next Valley** | Bordering states sharing a religion or the main culture of their capitals, neither the other's subject; at most 3 | Meet as equals, then deepen ties or keep the council limited; demand deference, then withdraw with gifts or stand firm; refuse, then reopen talks or maintain the refusal. Effects change opinions and timed country modifiers; the text about treaties does not itself create an alliance or marriage. |
| [Empire and periphery](content-reference.md#empire_periphery) — **The Far Provinces** | A state with subjects, paired with its most distant subject capital; at most 2 | Send governors, then rotate or retain them; grant a local charter, then extend or revoke the precedent; settle heartland families, then include old families or favour settlers. These choices apply modifiers and political effects; they do not move populations or directly annex subjects. |
| [Contact across the ocean](content-reference.md#contact) — **Strangers on the Shore** | During play: capital in America, native American culture, at least one port, a known country with an Old World capital, and not a colonial-nation subject | Welcome envoys and later grant a trading house or restrict inland trade; allow one port, then keep or ease restrictions; raise coastal levies, then demobilize or keep the watch. Port restrictions and trading houses are modifiers, not changes to port count or actual access rights. This is an encounter story, not a unique first-discovery detector. |
| [Colony becomes a country](content-reference.md#colony) — **A Colonial Assembly** | During play: a `colonial_nation` subject with its capital in America | Petition for council seats, then buy or reject them; assert a local identity, then favour colonial or old-country law; demand self-government, then prepare militia or negotiate autonomy. These are opinion, legitimacy, stability and modifier effects: the story does not automatically start a war, grant independence, change culture or form a federation. |

The sacred story's **Great Temple** is a location modifier, not a new buildable
temple. **High Priesthood of the Shrine** is an available clergy privilege,
not an automatic grant: the branch opens its availability. Ending the story
normally retains that unlock; the restrictive ending removes it. The full
[sacred reference](content-reference.md#sacred_centre) identifies the source
payloads and every duration. [V-EXEC C409]

## Formable countries

These are generated political goals with names based on their seat, their own
tags, colours and arms. They are offered through EU5's normal formable-country
mechanism. The six families are listed below; they are not six fixed historical
countries. [V-EXEC C212, C218, C409]

| Family | Territory chosen during generation | Ownership required | Level / rank | Founding modifier |
|---|---|---|---|---|
| **River-basin union** | 12–30 connected river locations; at least 3 centres and 2 states with capitals inside; up to 2 unions | 60% | 3 / Kingdom | **Markets of One River**, 10 years |
| **Highland confederation** | 10–24 connected hill, mountain or plateau locations; at least 34% mountains/plateau, 3 centres and 2 states with capitals inside; up to 2 | 60% | 2 / Duchy | **Compact of the Valleys**, 20 years |
| **Maritime league** | 8–18 coastal locations; connections may cross between ports sharing a sea zone; at least 3 centres and 2 states with capitals inside; up to 2 | 60%, plus **at least 3 ports** | 2 / Duchy | **Charter of the League**, 20 years |
| **Cultural commonwealth** | 12–30 connected locations of one culture group, using each location's main culture; at least 3 centres and 2 states with capitals inside; up to 2 | 50% | 3 / Kingdom | **One People**, 20 years |
| **Regional realm** | 24–48 connected locations, without a river/coast/culture restriction; at least 4 centres and 3 states with capitals inside; up to 1 | 50% | 4 / Empire | **Administration of the Realm**, 15 years |
| **Postcolonial federation** | 20–40 connected coastal locations, including sea-zone links; no minimum starting states or centres; up to 2 | 35% | 3 / Kingdom | **A Nation Founded**, 10 years |

For the first five families, eligibility is assigned to **up to 8 starting tags**
whose capitals are inside the target, ranked by their holdings there. Conquering
the territory as an unrelated tag does not add that tag to the authored list.
The cultural commonwealth chooses the narrowest available vanilla culture group
with enough main-culture locations; a scattered minority does not establish a
territory. The first five families start growing their territory from a qualifying
centre; the federation can start from any qualifying coastal location.
[V-EXEC C409]

The federation uses a runtime cultural condition instead of starting tags:
`culture ?= { is_culture_native_american = no }`. Its name describes its intended
role, but the authored condition does **not** require previous colonial status,
independence or completion of the Colony story. Every family writes
`capital_required = yes`, the target locations, the ownership fraction and
`rule = plausible`; the game also applies its own formation rules. The founding
effect raises country rank only if it is below the family's rank. Territory size
and starting-state counts above are generation rules, not additional conquests
the player must perform. [V-EXEC C409]

“Centre” usually means a city/town or a place at or above the 75th population
percentile among state-owned places. The highland and maritime families use the
50th percentile to allow opportunities in less urban terrain. Targets of the
same family do not overlap; different families can overlap. Families need not
reach their maximum counts. See the [reference](content-reference.md#formable-countries)
for keys and founding-modifier sources. [V-EXEC C409]

## Colonial names

RNW writes one naming entry per generated land region and tradition:
**Spanish, Portuguese, English, French and Dutch**. The first four test the
overlord's cultural language; Dutch tests an accepted or primary culture in the
Netherlandish group. The colony's capital must be in the corresponding region.
The name combines the tradition's word for “new” with that region's generated
name, localized for the game's languages. There is no fixed New Spain or New York
slot on random land. [V-EXEC C218, C409]

These are scripted naming rules, not additional starting countries or formables.
Applying a scripted name to a country created by a console effect was not
established in the earlier sitting; the written entries alone do not prove that
every way of creating a colonial country uses them. [V-GAME C207, C210; UNKNOWN C220]

## Exceptional places and starting societies

The resource layer can place a **Great Silver Lode**, **Rich Silver Vein**,
**Silver Seam**, **Mercury Lode** and **Rich Fishing Grounds**. Each type appears
at most once, only on the matching resource, with no two sharing a location.
Relief is an ordered preference, not an absolute mountain requirement; the
fishery requires a coast. A world without suitable candidates omits that type.
These are starting location modifiers, not event chains or decisions. Their
locations follow the resources seed, so rerolling peoples does not move them.
[V-EXEC C409; sources in the [reference](content-reference.md#exceptional-places)]

Starting **great empires, sea leagues, highland confederations, fractured realms
and sacred centres** are described in [Native societies](natives.md#more-varied-societies-r7d-societies)
and [Technology and empires](r7-technology-and-empires.md). They are starting
political arrangements, distinct from the similarly named formable and story
families. Their presence does not itself promise a story or a formation goal;
content eligibility is evaluated separately. [V-EXEC C251–C253, C409]

## Vanilla content

Generic vanilla systems remain the source of colonization, diseases, Columbian
exchange, colonial revolution, religion, government and technology. RNW retires
or closes historical American chains whose actors no longer exist, reuses
suitable payloads in its original stories and can rebind selected historical
formables to their actual culture. This catalogue counts RNW's original
families, not every retained or remapped vanilla event. The authoritative
object-by-object policy and implementation status are in the
[content plan](content-plan.md#one-decision-for-every-vanilla-consumer),
[decision table](../src/rnw/content_decisions.py) and
[audit](research/n0-n4-audit.md). [V-EXEC C222–C223, C409]

## Inspecting one particular world

The catalogue describes families. To find a particular world's actual countries,
targets and starts, use its own generated files. **These files reveal hidden
geography and future opportunities.** Paths below are relative to the world mod
except for the export report. [V-EXEC C409]

| What to find | Where |
|---|---|
| Names, tags, family, target size and eligible tags of the generated formables | Export bundle `report.json` → `text_stats.stories.formations` |
| Family counts, missing-family reasons, pulse families and opportunity-to-start-event mapping | Export bundle `report.json` → `text_stats.stories`: `opportunities`, `absences`, `pulses`, `starts` |
| A start's country, centre, optional partner, year window and monthly chance | `in_game/events/rnw_story.txt`; start IDs are assigned per world, so do not assume `rnw_story.1001` always means the same family |
| Actual target locations, potential and extra formation conditions | `in_game/common/formable_countries/rnw_formations.txt` |
| Visible story events, hidden cleanup and pulse starts | `in_game/events/rnw_river.txt`, `rnw_sacred.txt`, `rnw_harvest.txt`, `rnw_route.txt`, `rnw_alliance.txt`, `rnw_empire.txt`, `rnw_contact.txt`, `rnw_colony.txt`; bearer-bound families without opportunities are omitted |
| Numeric story/founding bonuses and clergy privilege | `main_menu/common/static_modifiers/rnw_story_modifiers.txt`; `in_game/common/estate_privileges/rnw_story.txt` when present |
| Colonial naming rules | `in_game/common/scripted_country_names/rnw_colonial_names.txt` |
| Numeric exceptional-resource bonuses | `main_menu/common/static_modifiers/rnw_exceptional_places.txt` |
| Translated event texts and formed-country names | `main_menu/localization/<language>/rnw_story_l_<language>.yml` |

The export report belongs to the generation bundle and need not be copied into
the installed mod. The installed scripts above remain the record of what that
world carries. Updating the generator does not change an existing world's
campaign scripts. [V-EXEC C409]

## Maintaining this catalogue

The readable explanations here are maintained alongside the content definitions.
The complete reference is generated directly from `STORIES`, formation `SPECS`
and `RULES`, and exceptional-place `SPECS`, using only original project content
and vanilla source identifiers. No game installation is needed. [V-EXEC C409]

```sh
uv run python docs/build_content_reference.py
uv run python docs/build_content_reference.py --check
```

`tests/test_content_catalog.py` checks that the committed reference matches the
definitions; adding an unsupported effect also fails until it has a readable
explanation. When changing eligibility, timing or exporter paths, update this
catalogue too. See the [content plan](content-plan.md) for design history and the
[claims ledger](research/claims-ledger.md) for evidence; neither replaces the
current player catalogue.
