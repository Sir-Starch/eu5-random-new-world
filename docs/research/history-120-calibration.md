# History calibration for 1.2.0

2026-11-04, RNW **1.2.0 development / pending epoch 61**, EU5 **1.4.7 / Steam
build 26377361**. This is H7 evidence for the [accepted plan](../history-plan.md),
not a release or engine-acceptance claim. Held-out seeds remain untouched at this
checkpoint. Full normal paired performance, held-out validation and delivery are
still required.

## Method and scope

The [H0 matrix](history-contracts.md#seed-matrix-and-baseline) supplies six presets
and seeds 3/42/77/1000. Native starts use actual physical inputs captured from the
normal generator after its physical-world checks, not the fixed-geography
bootstrap reruns of H0. All 24 cases run Calm 200, Varied 500 and Turbulent 800.
The baseline native constructor is the exact source at tag `v1.1.0`
(`cb1e3d777e0829d98ba929b4e1db88bbf247a87c`). Its countries/vassals on the
continents/3 capture equal that version's complete normal export, and the full
captured physical inputs agree across epochs on that case.

The [islands/1000 construction correction](n5-region-keys.md#child-capacity-construction-correction-2026-11-04)
is necessary before that case reaches natives. Its baseline native comparison
uses the corrected physical input. The original 1.1.0 hierarchy constructor
rejects the same input; a native-only row cannot supply a nonexistent complete
1.1.0 export time. The timed phase must retain that original failure and distinguish
any comparison using the common corrected construction.

Counters follow [the predeclared definitions](../history-core.md#h7-measurement-foundation).
S4 reports the median paired ratio over the seed set, as §7 makes calibration
statistical over seed sets; individual deviations are retained below. S5 instead
checks every qualifying physical landmass. S4's sweep correlation uses Spearman
midranks on all eight raw low/high endpoints (one world median per preset/seed),
without first collapsing endpoints to two slider averages.

The 32 one-control sweep cases use continents/archipelago, seeds 3/42, and the
prescribed low/high state share, state size, population and extraordinary chance.
Each also runs all three turbulence choices. Thus **168 real native starts** pass
full causal replay and final-plan validation. All 168 additionally pass portable
compression/decoding, causal/lifetime/ownership validation against the atlas links,
parsed country/government/technology/rank/discovery and directed-diplomacy checks,
exact written-population cohort round trips, historical scripts and all eleven
languages, and actual story/formable writers with explained political bindings.
These affected-writer checks do not regenerate terrain or claim complete-world
performance. A complete normal reference export is recorded separately below.

## Chosen policy

The bootstrap size factor remains **b = 1**. Each society draws action-family
admission independently of the number of available neighbours. It then chooses
one eligible alternative per admitted family and ranks at most three proposals.
Early family filtering equals filtering the complete eligible candidate set;
candidate iteration order changes no result.

The base propensity is 180‰ for ordinary families, 50 + turbulence/2 for conflict
and pressure, and turbulence³/1,000² for separation, followed by the existing
independent society-orientation adjustments. This prevents a dense contact graph
from filling all three slots with repeated exchanges or movements. Separation
still needs a real eligible union and viable connected successors.

A great-empire ambition chooses the eligible hearth centre with the greatest
existing model strength, with a stable anchor tie-break. Its centralization and
integration inclination are at least 900, alongside ruler/offensive orientation.
It grants no land, population, technology, rank, client or guaranteed outcome.
Recognition still requires twelve actual owned locations, sufficient authority,
manageable burden and the seeded polity or its recorded successor.

A prospective client realm consumes administrative capacity at every ancestor
ruler: total client population may not exceed the ruler's own population ×
centralization × integration × 4 / 1,000². The incoming lord's clients count too.
Only one admission can commit an administrative line in a round. Refusals cite
the earlier commitment; capacity decisions include the supporting realm's causal
facts. Existing treaties are not silently removed or ownership repaired afterwards.
This has no world-share quota. It replaces an observed unlimited-client effect:
three Wall cases reached 53–59% of a qualifying landmass before this constraint.

## Published results

[V-EXEC] All **24 × 3** starts and **32 × 3** sweeps complete. Medians unless
marked as maxima; the one-to-one baseline comparisons retain every world.

| Measure | Calm 200 | Varied 500 | Turbulent 800 |
|---|---:|---:|---:|
| Conflicts per 100 bootstrap states | 63.744 | 122.348 | 172.985 |
| Ownership events per 100 bootstrap states | 29.974 | 41.640 | 47.874 |
| Separations per 100 bootstrap states | 0 | 1.315 | 1.791 |
| Landed-polity continuity | 100% | 100% | 100% |
| Countries with a projected historical relation | 94.48% | 93.90% | 93.26% |
| Ordinary state size / paired baseline | 1.00 | 1.00 | 1.00 |
| Largest qualifying polity + clients, maximum | 37.42% | 42.58% | 38.40% |
| Effective government/position combinations | 163 | 157.5 | 153 |
| Great ambitions realized / seeded | 5/12 | 7/12 | 7/12 |
| History wrapper, maximum bytes | 512,929 | 515,439 | 515,454 |

The baseline median government/position count is 3. Chronicle medians are at
least three and their maximum is eight. The Varied great-empire rate is **58.3%**.
No extraordinary trajectory is seeded at chance zero in any sweep. State-size
sweep rank correlation is **0.95618** (required ≥ 0.9); the largest sweep history
wrapper is **560,999 bytes**.

S4's paired-ratio outliers remain visible: Calm/Varied range from 0.667 to 1.50;
Turbulent ranges from 1.00 to 1.50. Wall/3 has ordinary median 3 against the
baseline's 2 at all three levels. Islands/42 at Calm and islands/3 at Varied have
median 2 against 3. These are reported deviations, not seed-specific adjustments
or omitted worlds. The median paired ratio is 1.00 at each level.

The Varied distributions below retain their full range; quartiles use inclusive
linear interpolation over all 24 world observations.

| Measure | Minimum | Q1 | Median | Q3 | Maximum |
|---|---:|---:|---:|---:|---:|
| Conflicts / 100 bootstrap states | 76.970 | 112.354 | 122.348 | 130.492 | 232.692 |
| Ownership events / 100 bootstrap states | 31.847 | 37.166 | 41.640 | 43.806 | 56.087 |
| Separations / 100 bootstrap states | 0 | 0.604 | 1.315 | 2.395 | 4.459 |
| Continuity | 97.18% | 99.37% | 100% | 100% | 100% |
| Projected historical relations | 91.06% | 92.82% | 93.90% | 95.06% | 98.54% |
| Ordinary state median | 2 | 3 | 3 | 3 | 3 |
| Government/position combinations | 112 | 135 | 157.5 | 180.5 | 192 |

Private raw data and scripts are under `local_data/history-120/h7/`: `family-v3/`,
`sweeps-v3/`, `artifact-checks-published.json` and `artifact-checks-sweeps.json`.
Earlier rejected trials retain their original outcomes and scopes.

## Reference, portability and cancellation

[V-EXEC] The **normal producer**, without a cached native stage, and all normal
writers/output checks pass for **872 nonmetadata files**, SHA-256
`435074c7582a41ea94e4872637db3deaeb0082a1b60c6bee659659d6668577fb`.
The pending epoch-61 golden records this result; frozen epoch 60 remains intact.
The reference history wrapper is **505,104 bytes**, below 2 MiB. The real compact
world file is 971,935 bytes; its 1,065 actors and 30,055 portable events survive
actual import and receipt recovery in a private profile, covered in both cases.
No real profile or EU5 session is used for that check.

Cancellation 50 ms into the reference's actual history simulation exits the
complete normal exporter, including sibling stages and spool cleanup, in
**0.207 s after the request**. No completed output or spool remains. Separate
native-entry, simulation, digest and archive measurements also remain below two
seconds. This establishes S10 on those observed paths, not an engine observation.

The reference generation ran alongside calibration with a different worker count
from H0; its elapsed time and peak are not a paired S8/S9 result. Independent
normal reproduction, controlled full-generation comparisons, held-out acceptance,
package self-tests, installation and the one owner sitting remain open.

[V-EXEC] Locked full checks pass: **2,761 Python tests**, 17 optional skips,
strict types/format/lint and **23 Rust core tests**. Desktop checks/build pass
with no Svelte warnings, **15 interface tests** and **5 Rust shell tests**.
