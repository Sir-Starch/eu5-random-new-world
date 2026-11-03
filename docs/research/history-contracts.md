# History implementation contracts (H0)

[V-LOCAL, 2026-11-03] Read-only survey of EU5 **1.4.6 / Steam build 26300913**;
implementation starts at `4686f4c8347c102b855c863e2775b044c3f032eb`.
This is the inventory and baseline for the accepted [1.2.0 plan](../history-plan.md),
not evidence of engine loading or of a completed history simulation. No game was
launched. Raw measurements and collection scripts stay in ignored
`local_data/history-120/`.

## Layers and sliders

The [control contracts](../history-plan.md#5-layers-and-controls) are the H0
contract: physical geography and identity zones stay fixed; the organized-land
envelope stays fixed; histories read the peoples seed and never the resource roll.
The calibrated population, peasant share, complexity and farming eligibility remain
inputs. Ordinary size is a statistical calibration target, not a post-simulation
territory repair. Extraordinary chance seeds trajectories; turbulence changes
action propensities within viability constraints.

One existing distinction needs preserving explicitly in H1: `Societies.population`
is the calibrated budget, but the exporter adds 50 milli-pops for each unused
donor culture/religion through `diaspora`. The written population therefore exceeds
that budget by the diaspora total. H1 preserves both quantities and their bytes.
H2/H3 must establish the conserved cohort budget **after** this identity-completeness
step; movement must not recreate those cohorts or change their identities. This
does not authorize a population-generation change in H1.

## Installed societal-value inventory

Ranges are explicit values in the government blocks of the 17 templates actually
used by vanilla American countries. They are not the engine's global [-100, 100]
range. The survey follows `american_includes` / `slider_targets` rather than
inferring an unobserved range from a default or from a donor culture.

| Axis | American minimum…maximum | Age gate | History disposition |
|---|---:|---|---|
| `centralization_vs_decentralization` | 60…100 | none | Project within range |
| `traditionalist_vs_innovative` | -90…-70 | none | Project within range |
| `spiritualist_vs_humanist` | -90…-60 | none | Project within range |
| `aristocracy_vs_plutocracy` | -90…-60 | none | Available contract; no extra history dimension |
| `serfdom_vs_free_subjects` | -75…100 | none | Available contract; no extra history dimension |
| `mercantilism_vs_free_trade` | -50…50 | Reformation | Do not project |
| `belligerent_vs_conciliatory` | 30…100 | none | Project within range |
| `quality_vs_quantity` | -75…10 | none | Project within range |
| `offensive_vs_defensive` | -50…50 | none | Project within range |
| `land_vs_naval` | -90…60 | none | Project within range |
| `capital_economy_vs_traditional_economy` | 90…100 | none | Available contract; no extra history dimension |
| `individualism_vs_communalism` | 50…86 | none | Available contract; no extra history dimension |
| `outward_vs_inward` | -40…60 | Discovery | Do not project |
| `sinicized_vs_unsinicized` | no observed value | none | Do not project |
| `absolutism_vs_liberalism` | no observed value | Absolutism | Do not project |
| `mysticism_vs_jurisprudence` | no observed value | none | Internal/summary only |
| `latinization_vs_hellenization` | no observed value | none | Do not project |

In particular, religious authority may project through spiritualist positions,
government and holy sites; it cannot write a mysticism position on these inputs.
This applies the plan's existing projection rule, without changing D9. H4 must
read and validate these contracts from the player's installation at generation
time; this table is evidence for the target build, not hardcoded calibration.

## Text interfaces

Paths below are relative to installed `game/`. Counts and fingerprints agree with
the accepted plan's [survey](../history-plan.md#2-evidence-base).

| Interface | Contract and precedent | SHA-256 prefix |
|---|---|---|
| Start opinions | `main_menu/setup/1337/18_opinions.txt`: `opinion` with directed `first`, `second`, `type`; pair-specific friendship and ordinary event biases both used | `ffa73fdde1ece3c4` |
| Bias definitions | `in_game/common/biases/07_opinion_from_start_up.txt`: named key with `value`, optionally `min`/`max` or duration; `03_opinion_from_events.txt`: `value` and `yearly_decay` | `4f64ec810f2ba6ad` / `70f691c6483d30e5` |
| Decision | `in_game/common/decisions/navarre_decisions.txt`: named key, `decision_category`, `potential`, `allow`, `ai_will_do` block and named `option` with `effect`; ordinary decision files also use `trigger_event_non_silently` | `4785377b1953f5bb` |
| Chronicle event | Existing RNW `storymodel` / `eu5_story`: namespace, `type = country_event`, title/description localization keys, named option; `in_game/events/thalassocracy_events.txt` supplies conditional `desc` → `first_valid` → `triggered_desc` with `trigger` and `desc` | `fe540c90d0368906` (conditional description) |
| Protection | `main_menu/setup/1337/12_diplomacy.txt`: `diplomacy_manager` → `scripted_oneway` with `first`, `second`, `type = guarantee`; five uncommented precedents | `5b817a56fe72093b` |

**Our History implementation detail:** use `ai_will_do = { value = 0 }`, following
the installed block syntax, rather than a scalar `ai_will_do = 0`. Its voluntary
option triggers the visible event through `trigger_event_non_silently`, as in
`in_game/common/decisions/flavor_decisions_tun.txt` (SHA-256 prefix
`2d3ad9ab302cf954`). No game-start hook, cost, copied flavour text or new asset
is needed. Select the country's key with `first_valid` / `triggered_desc`, using
the living generated tag in its trigger; a static description cannot select it.

These observations establish syntax precedents, not acceptance of newly defined
biases, decisions or guarantees between generated tags. H7 and F1–F3 retain their
decided scope. [Interoperability R-007](interoperability.md#r-007--historical-opinions-decisions-and-protection-h0)
records the intended new text interfaces.

## Seed matrix and baseline

The published matrix is the Cartesian product of six presets (`continents`,
`supercontinent`, `small_continents`, `archipelago`, `islands`, `wall`) and seeds
**3, 42, 77, 1000**. The held-out matrix uses the same presets and seeds
**1001, 1002, 1003, 1004**; do not use it to tune propensities. Each full-world run
uses its preset's resolved settings and ordinary roll derivation. Sweep presets
are `continents` and `archipelago`, seeds 3 and 42: vary one control at a time,
state share 30/600‰, mean state size 2/10, population 250/3000‰, extraordinary
chance 0/1000‰; other controls stay at the preset values. Pair all comparisons
with the same settings and inputs in the pinned baseline implementation.

[V-EXEC, 2026-11-03] Initial **bootstrap-only** baseline: 24 serial society runs,
four peoples seeds above on each of six cached, game-derived land graphs from
the issue #8 measurement. The land seeds are 1000, 42, 42, 42, 7, 9 in the table's
order. These are fixed-geography reruns, **not** the 24 full-world acceptance runs.
The society and settings source is byte-equal to tag `v1.1.0`
(`cb1e3d777e0829d98ba929b4e1db88bbf247a87c`). The cached inputs include the
installed 338-milli / 122‰ agrarian floor, coast membership and preset native
settings (extraordinary chance 250‰). No held-out seed was run.

Medians across the four peoples seeds; state counts exclude great empires, while
state locations include them. Timings cover `generate_societies` only.

| Preset | Land locations | Ordinary states | Ordinary median size | Tribes | State locations | Seconds |
|---|---:|---:|---:|---:|---:|---:|
| Continents | 6,458 | 196 | 3 | 491 | 721 | 1.834 |
| Supercontinent | 6,686 | 209.5 | 3 | 517 | 744 | 2.071 |
| Small continents | 6,288 | 195 | 3 | 467.5 | 692.5 | 1.800 |
| Archipelago | 4,585 | 147.5 | 2 | 356.5 | 496 | 1.202 |
| Islands | 4,325 | 143 | 3 | 367 | 475 | 1.570 |
| The Wall | 4,582 | 150 | 3 | 348.5 | 493.5 | 1.014 |

Every run's counts, conserved bootstrap total and elapsed time are in local
`baseline.json`; this scoped baseline does not establish H7's S1–S11. H1 records full-world
timings, peak memory and output equality with its reference export.
H7 needs paired full exports on the same machine and cache conditions for S8/S9;
a bootstrap timing cannot be substituted for end-to-end generation time.


## H1 reference workload

[V-EXEC, 2026-11-03] The final-source export uses the unchanged code and settings
from `tests/golden_world.json`, the installed build above and the existing local
land cache. Its 868 nonmetadata file hashes reproduce the frozen epoch-60
reference exactly; the shared game-contract fingerprint is
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.

The reference has 5,903 land locations, 335 states holding 1,239 locations,
387 tribes holding 2,024, four great empires of 94/53/47/59 locations and 35 vassals.
Elapsed time is 193.404 s; native start construction 3.284 s;
atlas construction 0.335 s; process peak resident memory
8.981 GiB. Raw stage timings and metrics are in local
`reference.json`, output and all verifiers in
`generated/rnw_exp_history_h1_final/report.json`. These measurements describe
one cached reference export, not an S8/S9 paired performance result or the
older 5,098-location local world measured when the plan was written.
