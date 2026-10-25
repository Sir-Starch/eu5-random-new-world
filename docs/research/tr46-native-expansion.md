# TR46 native expansion: rules, ownership and successors

**2026-10-25; TR46-05, with evidence relevant to TR46-L07.** Retrospective
read-only investigation of the original **0.12.3 / epoch 33** observer campaign,
EU5 **1.4.4 executable, Steam 26142040, on 1.4.3 data 26105915**. No balance
change, new world or game launch. Claims C325–C328; [experiment 059](../../experiments/059-native-expansion/README.md).

## Result and disposition

- [V-LOCAL / V-EXEC C325–C327] The absence of ordinary native colonization is
  consistent with the **vanilla default AI rule**, actually saved in TR46:
  `western_colonisation_only`. Its allowed capital continent is `europe`.
  It is not evidence that RNW forgot to give natives colonization technology.
- [V-EXEC C327] Large generated countries **did expand**. The two empires grow
  **53 → 98 → 121** and **86 → 119 → 142** owned locations. Tagomogre grows
  **7 → 69 → 149**, becoming `LIA`. Expansion of these states redistributes
  existing state territory; it does not fill the initially unowned New World.
- [V-EXEC C327] Results differ by society. All three sea-league members have
  no owned land by 1497; two of four fractured-realm members also lose all
  land. A country object left in a save is not proof it is still a living
  state, and its cached population is not used as a survival measure.
- [UNKNOWN C328] No vanilla control campaign establishes a normal growth
  rate, the reason for the league's defeat, or why no frontier action was
  active at either checkpoint. These are retained questions, not grounds for
  an AI bonus or an automatic change of the player's rule.

TR46-05 therefore does **not** establish a universal native-expansion defect.
The charter observation has an identified vanilla explanation; conquest and
consolidation are observed; frontier behaviour and society resilience remain
explicitly unproven. Keep these separate in future work.

## 1. Evidence and binding checks

[V-EXEC C326] The two frozen saves from [053](../../experiments/053-tr46-observer/README.md)
were read without modifying them. Both ZIP CRC checks pass and their SHA-256
hashes still match the original evidence manifest:

| Checkpoint | Filename suffix | Save SHA-256 |
|---|---|---|
| 1497.4.1 | `_19.eu5` | `4ec33534d8063a0efce3e0875ffa48ae0ed417a5dfe9924cfe7379eeada2aa00` |
| 1590.11.11 | `.eu5` | `b74a181c54881143eec729487263eed7647e6cc6f279b3a4b511d3987f3656de` |

The `_19` copy is **not** a 1337 baseline. The baseline is the frozen world's
written 1337 country setup and diplomacy. For archetype identification, the
0.12.4 coast reconstruction's country setup, diplomacy, native definitions and
map definitions are byte-identical to those frozen originals. Its report can
therefore identify the original groups; the later 0.12.8 LSI3 start cannot
substitute for this baseline.

[V-EXEC C326] A private reader consumes all **68,108,132 / 75,749,957 tokens**
of the two gamestates, with balanced containers and no unrecognized token.
It uses each save's own string lookup, not an external downloaded token map.
The map's **30,565** definition keys match the location-ID domain exactly;
the established one-based ordering is independently checked against **201
retained original state objects' start capitals** and **all 738 initially
native-owned locations' 1337 ownership records**. Every current country's
`owned_locations` list agrees exactly with a second count from location
`owner` fields: **2,653 / 2,619 country objects**, zero mismatches.
See interoperability [R-005](interoperability.md#r-005--read-only-tr46-save-state-analysis).

[V-EXEC C326–C327] Save handles are matched exactly, including their generation
bits; slot reuse is not identity. Of the 659 original objects, 658 retain their
original handle at both checkpoints. `QDL` is the explicit exception: original
handle **1538** changes identity in a civil war and is recorded dead in 1428;
the creation/name timeline binds the successor **150997337** back to `QDL`.
It owns **24 / 21** locations. Counting only low-numbered handles would omit
it. WBU's original handle **1546** persists through the formation of LIA;
its separate 1497 civil-war object **218106318** is excluded from the original
country's 69 locations. Do not merge every object sharing `original_tag`.

[V-EXEC C326] Ownership histories are **not an exhaustive current-owner
snapshot**: **172 / 102** location histories end at an owner different from the
current owner. The earlier checkpoint includes **23** such native locations,
held by the separate WBU civil-war object. The final checkpoint has none among
the traced native handles. Snapshot counts below use current ownership and
cross-check the country lists; no lifetime peak or exact acquisition cause is
inferred from incomplete history alone.

## 2. Vanilla mechanisms and generated eligibility

[V-EXEC C325] A fresh read-only count of the installed 1337 setup finds **223
American landed countries, 321 pop countries and 493 owned locations out of
4,434 passable American land locations**. TR46 starts with **202 / 457 / 738
out of 6,656**, respectively. Both start with about **11.1%** of passable
locations owned by states. Large unowned space is therefore present in the
vanilla start too. These are location counts, not equal-area/population measures
or a vanilla control campaign; no normal rate of later consolidation follows.

[V-LOCAL C325] These are installed-file contracts for this build, not results
of an unmodified vanilla campaign:

| Mechanism | Vanilla conditions relevant here | TR46 consequence |
|---|---|---|
| AI colonial charters | `main_menu/common/game_rules/00_game_rules.txt`: default `western_colonisation_only`; `loading_screen/common/defines/00_defines.txt`: allowed capital continent `europe`, with further exclusions | Both saves explicitly carry this rule. Capitals of all saved objects with an original generated tag remain in `america`; ordinary native AI charters are excluded by the rule |
| Colonization technology | `in_game/common/advances/0_age_of_traditions.txt`: `colonies` grants `can_colonize`, requires `mapmaking`, which requires `written_alphabet` | All nine extraordinary member countries have these advances researched at both late checkpoints; this does not establish their exact research dates |
| AI affordability | Installed defines: tax-base threshold **100**, minimum total population **5**, with named eager-colonizer exceptions; evaluations every six months | Removing the geographic rule would not promise every country colonies. Historical affordability was not reconstructed |
| Frontier settlement | `3_cabinet_actions_unlocks.txt`: `settle_the_frontier_advance` requires `city_building_advance`, a location/army country and an original capital in the specified geographic set; colonial nations excluded | **89 of 202** starting states meet the geographic part, **113** do not. This is a partial eligibility test, not a guarantee of target, research, staffing or AI selection |
| Frontier action itself | `cabinet_actions/settle_the_frontier.txt`: bordering candidate province, source province population above **1**, eligible loyal adult courtier; ten-year action with migration and completion/abort events | It has a distinct script path. It must not be measured solely by `COLONISATION: ... starts colonising` log rows |
| Pop countries | Frontier action/advance require a location/army country with land | All **457** starting pop countries remain `type = pop` with zero owned locations at both checkpoints. This says nothing about their migration or pop membership growth |
| Conquest and subjects | `ai_scripted_expansion_target/attack_neighbors.txt` evaluates neighbouring countries, subject to personality and time since war; other engine constraints still apply | Native declarations and territorial/subject changes are observed; declaration count alone is not a border measure |

[V-LOCAL C325] The frontier geographic set includes South America, Central
Africa, the named African/North American regions, `shiewhibak_area`, Oceania
and two explicit vanilla tags. Both TR46 empires and every league member start
outside that geographic set. All four fractured-realm members start within it
and have the frontier advance researched in both saves. No North-American
empire is assumed eligible merely because it is large or technologically strong.
The precise reach of the general AI colonization rule into frontier selection
is **[UNKNOWN]**; the cabinet script alone does not settle the hardcoded planner.

[V-EXEC C327] Active charters: **10 / 16** globally, **zero** belonging to the
original natives or descendants traced through explicit country-creation links
(**751 / 760** handles). There are **zero active frontier cabinet actions
anywhere** at both checkpoints, not merely among generated societies. Recorded
ownership histories contain no native acquisition outside initially native
state-owned land. Current native holdings also contain none. These observations
support persistent unowned space, but the incomplete histories do not prove
there was never a failed, aborted or temporary attempt.

## 3. Every extraordinary society actually present

[V-EXEC C327] Columns are **1337.4.1 / 1497.4.1 / 1590.11.11**. Land means
locations owned directly, excluding subjects, occupation/control, pop-country
membership and other civil-war objects. Subjects are direct saved dependency
relations, not a count of allies or recursive subject territory.

| Society | Original tag and name | Owned locations | Direct subjects |
|---|---|---|---|
| Great empire | OAQ — Chaurumrac | **53 / 98 / 121** | 3 / 1 / 0 |
| Great empire | MKD — Tecamachixtlan | **86 / 119 / 142** | 3 / 5 / 2 |
| Fractured realm | FQR — Guaru | 8 / 0 / 0 | 0 / 0 / 0 |
| Fractured realm | QBQ — Sabal | 8 / 37 / 7 | 0 / 1 / 1 |
| Fractured realm | WBU — Tagomogre; final tag LIA | **7 / 69 / 149** | 0 / 3 / 2 |
| Fractured realm | SBS — Atikaapirare | 7 / 0 / 0 | 0 / 0 / 0 |
| Sea league | VDE — Xalacōpan | 4 / 0 / 0 | 0 / 0 / 0 |
| Sea league | MIN — Colican | 1 / 0 / 0 | 0 / 0 / 0 |
| Sea league | GVQ — Azcapolco | 1 / 0 / 0 | 0 / 0 / 0 |

[V-EXEC C327] No highland confederation or sacred centre was instantiated in
this world. The report's **12 / 3 candidate options** are not actual societies
and must not be counted as defeated or inactive groups. There are two empires
and two non-empire archetype groups, containing seven countries.

[V-EXEC C327] The final OAQ keeps all 53 original locations and acquires 68
from other starting native states. MKD loses one original location and gains
57 others, giving net +56. WBU keeps its original seven and acquires 142 others.
Thus even these simple before/after counts hide internal losses and transfers;
“no colonization” and “no expansion” are different statements.

## 4. Ordinary natives and consolidation

[V-EXEC C327] The same frozen cohort is followed at both checkpoints, with
the explicit QDL successor binding above. New independent civil-war/released
countries are not silently added to it.

| Cohort | Starting countries | Directly owned land, 1337 / 1497 / 1590 | Countries with land, 1497 / 1590 | Direct subjects, 1337 / 1497 / 1590 |
|---|---:|---|---|---|
| Ordinary landed states | 193 | 563 / 387 / 314 | 50 / 36 | 15 / 3 / 2 |
| Great empires | 2 | 139 / 217 / 263 | 2 / 2 | 6 / 6 / 2 |
| Fractured-realm members | 4 | 30 / 106 / 156 | 2 / 2 | 0 / 4 / 3 |
| Sea-league members | 3 | 6 / 0 / 0 | 0 / 0 | 0 / 0 / 0 |
| All original landed states | 202 | **738 / 710 / 733** | **54 / 40** | **21 / 13 / 7** |
| Pop countries | 457 | 0 / 0 / 0 | 0 / 0 | 0 / 0 / 0 |

[V-EXEC C327] Against their own 1337 size, ordinary states at 1497 have
**32 growing / 14 unchanged / 147 smaller**; at 1590, **23 / 10 / 160**.
Across all 202 states the corresponding counts are **36 / 14 / 152** and
**26 / 10 / 166**. This is substantial consolidation into fewer countries,
not a frozen diplomatic map. The near-constant aggregate area is compatible
with the owner's visual impression that native settlement hardly spreads into
the large unowned spaces. It does not measure a vanilla-normal rate.

## 5. What remains actionable

1. [V-LOCAL / V-EXEC C325–C328] **Keep the vanilla colonization rule.** Changing
   it to `all_countries_colonize` would be an explicit balance/game-rule choice,
   not a repair demonstrated by this campaign. The vanilla option already
   exists; this phase adds neither an override nor a native-only bypass.
2. [UNKNOWN C328] **Frontier uptake:** identify the engine's rule/AI selection
   boundary and compare eligible target/staffing conditions before proposing a
   generator change. Both checkpoints show global non-use, so a generated-
   native-specific explanation is unproven. No long campaign or new owner
   sitting is requested.
3. [V-EXEC / UNKNOWN C327–C328] **League resilience / L07:** GVQ is conclusively
   a league member with two initial alliances. The ring construction's former
   assertion that two alliances cannot strain capacity is false as a guarantee:
   vanilla `alliance_upkeep_cost` depends on economic-base ratio, opinion,
   partner power status and bloc saturation, not a fixed slot count. The log's
   **0.9164 excess at DIP 0 / DIP 28 needed** is a conditional setup warning;
   actual starting ruler capacity, league defeat cause and a safe calibration
   remain unproven. Vanilla DWS warns too. Correct the explanatory comment,
   retain the warning as a separate initial-diplomacy issue, and do not add
   capacity bonuses or delete alliances on this evidence alone.
4. [UNKNOWN C328] **L04 AI command errors** remain unattributed. Their existence
   cannot override the saved evidence of conquest, nor establish why a
   particular society lost. Expedition and other independent log issues retain
   their own rows in the [problem register](tr46-observer-audit.md).
   [061's follow-up](tr46-ai-diagnostics.md), C333–C336, documents the inherited
   capital-distance division and identifies the three building clamps as Old
   World cases. Command actors/actions and division operands remain unknown;
   no new native AI or balance change is justified.

## 6. Verification and local reproduction record

[V-EXEC C326–C328] Private reader, baseline, snapshot extraction, validation and
all **659 country rows** stay under ignored `local_data/tr46-expansion/`:
`reader.py`, `baseline.py`, `extract.py`, `details.py`, `summarize.py`,
`validate_saves.py`, `finalize.py`, `native-country-table.csv`,
`final-report.json`, `save-validation.json` and `research-manifest.json`.
The manifest hashes the research inputs/results/helpers. Frozen source-save
hashes are checked against the original 053 manifest. ZIP/token/container,
capital/start-history and independent current-ownership checks pass as above.
Private synthetic checks also cover anonymous containers, string-reference
widths, complete handles, fixed-point values and rejection of unknown,
out-of-range, truncated or unbalanced input.
No generic save API, writer, save repair, decrypted asset or game binary is
shipped. Raw saves, strings, scripts, handles and dumps remain local.

[V-EXEC C328] `uv sync --locked --group dev && make check` passes on the current
source: **1,969 Python tests, 14 skips, 23 Rust tests**, formatting/lint/types
clean. The separate Workshop-text changes in `90f531e` had landed before this
check; earlier 058's 18 failures are a historical result, not this check's
status. This phase changes documentation and an unsupported source-comment
claim only: generator **0.12.8 / epoch 38**, world output and installed files
remain unchanged. No installation, launch, playset/save/settings modification,
process control, push or publication.
