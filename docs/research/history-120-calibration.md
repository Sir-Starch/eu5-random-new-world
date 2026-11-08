# History calibration for 1.2.0

2026-11-05, RNW **1.2.0 development / pending epoch 61**, EU5 **1.4.7 / Steam
build 26377361**. This is H7 evidence for the [accepted plan](../history-plan.md),
not a release or engine-acceptance claim. Corrected held-out timing, native and
sweep artifacts, reference reproduction, S9, cancellation, cross-platform native
parity and local package audits are complete. Held-out acceptance is **not met**:
S4 sweep correlation, S5 landmass dominance and S7 great-trajectory realization
fail their frozen thresholds. The calibration report retains the evidence and
limits. No parameters were fitted to held-out outcomes; no profile install, hub
update or owner game sitting was performed.

**Current R6 status, 2026-11-07:** the renewed freeze has now completed its held-out
run once. Q1 and Q9 fail; the other twelve checks pass. No parameters or thresholds
were changed after the run. See the final section for the complete result.

**Superseded as a gate (2026-11-05).** The independent
[audit](../history-plan.md#21-independent-audit-and-redesign-2026-11-05) measured
the 1337 maps of these same saved starts. It found that S1–S7 could pass on a
uniform small-state map that had lost 1.1.0's large-scale structure (findings
A1–A10). The S4 sweep's two-level Spearman criterion cannot reach 0.9 for a
perfect untied response (ceiling 0.873). The numbers below remain valid evidence
for their source and scope. The current gates are the plan's rewritten
[§18](../history-plan.md#18-acceptance-criteria).
R1–R5 are implemented ([history core](../history-core.md#audit-redesign-r1r5-2026-11-05)).
They have been checked on one development world only, with no seed-set results.
Calibration, the held-out run and delivery follow the
[R6 runbook](../history-core.md#r6-runbook), and their results belong in a new section of
this report.

## Method and scope

The [H0 matrix](history-contracts.md#seed-matrix-and-baseline) supplies six presets
and seeds 3/42/77/1000. Native starts use actual physical inputs captured from the
normal generator after its physical-world checks, not the fixed-geography
bootstrap reruns of H0. All 24 cases run Calm 200, Varied 500 and Turbulent 800.
The baseline native constructor is the exact source at tag `v1.1.0`
(`b9d2b81040b1bdf5cf5924c95eec9e99d76d16d4`, annotated tag object
`cb1e3d777e0829d98ba929b4e1db88bbf247a87c`). Its countries/vassals on the
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

## Equal-output performance follow-up

The first three quiet complete published pairs on the C486 source add
**17.29%, 17.49% and 17.14%** (continents seeds 3/42/77). They remain recorded in
`timed-published/`; a fourth current export completes before the queue is stopped.
This preliminary sample motivates further equal-output work, without claiming a
completed S8 failure or changing the chosen historical parameters.

A profile of the real continents/3 history and its independent replay attributes
**12.54 of 47.26 profiled seconds** to round-context construction, including 6.58 s
in contact calculations; rebuilding sparse indices accounts for another 3.54 s.
Round indices now reuse only the immutable physical graph and capacities, with
fresh ownership, cohorts and population caches for every snapshot. Mutual contact
minima update both directions together. Enumeration avoids already impossible
migrations and defence proposals before constructing them; full eligibility still
checks every retained action. No simulation round, validator or cause is removed.

Independent original indices, contact calculations and unpruned society choices
check the optimized path across eight synthetic histories and five turbulence
values. On actual continents/3 Varied, Wall/3 Calm and supercontinent/77 Turbulent,
**all 25 final-plan fields** equal their frozen C486 plans, including every event,
round, cohort, cause and projection; all measured counters and digests agree.
Locked full checks pass: **2,769 Python tests**, 17 optional skips, strict
types/format/lint and **23 Rust core tests**. These native-stage checks are not
full-world S8 timings. Private evidence:
`rounds-before-profile.txt` and `sparse-cache-final/equality.json`.

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

The initial reference generation ran alongside calibration with a different
worker count from H0; its elapsed time and peak are not paired S8/S9 evidence.
A subsequent quiet sequential reference pair on the **C486 source** uses fresh processes, identical
worker/memory settings and separate initially empty land caches, with the OS cache
left untouched. Both run the normal native producer, all writers and output
checks. Evidence is serialized only after generation time and peak are recorded.
The exact 1.1.0 source takes **225.312 s**, versus **241.996 s** for the frozen
history source: **+7.40%**. Peak memory increases by **19.00 MiB**, meeting S9 on
that revision; the optimized source still needs its final paired reference.
This single pair does not establish S8's seed-set distribution. The current output
equals the pending golden; the original source on the newer 1.4.7 scripts writes
868 files with digest `428d5282…2f26b5`, distinct from its immutable 1.4.6 golden.
That patch-dependent difference does not replace or amend the published golden.
Private evidence: `timed-reference/comparison.json` and both source manifests.

## Full normal S8 timings and boundary-only coast correction

[V-EXEC, 2026-11-04] The quiet complete published matrix ran all 24 worlds through
full generation, all normal producers and writers, and output checks with 31
workers and a 16 GiB budget. The original 1.1.0 baseline completed 23 cases;
`islands/1000` retained its known hierarchy-capacity failure and was compared to
the explicitly labelled matched-static sensitivity. The original-cohort median
added time is **13.27%** and inclusive linear p95 is **16.60%**. Including the
sensitivity, the median is **13.14%** and p95 **16.57%**. Both cohorts pass S8's
15% median and 25% p95 limits. The OS cache was left untouched; every run used a
fresh process and separate initially empty land cache. Full rows and digests are
in `local_data/history-120/h7/timed-published-final/summary.json`.

The first 20 held-out pairs also completed on the C487 source. The `eu5_newworld`
source change described below returns exactly the former coast mapping for every
successful C487 world: those runs passed the old explicit nonempty-coast guard,
so every retained regional coast remains nonempty. The published S8 outputs are
likewise unchanged by this correction. Corrected-source reference and held-out
results are recorded in the final section; they do not replace the published
seed-set S8 distribution.

[V-EXEC, 2026-11-04] Held-out `wall/1001` exposed a construction error in both the
pinned 1.1.0 baseline and the current generator: all four generated coastal sea
zones for `mesoamerica_region` touched the Old World boundary, leaving no
independent American coast. The generator failed explicitly before history
projection. The correction omits only regions with no nonboundary coastal zones
from regional-sea assignment; those boundary cells remain in the protected ocean
hierarchy. It adds no strait, inland mouth, or post-generation repair. The full
current `wall/1001` export then passes normal output checks for **870 files**,
SHA-256 `57851ca328cec5ba8fd8a97a2056be76f488aaf8c325e406279934a5cd3a596b`.
With fresh caches, matched-static takes **203.295 s** and current history takes
**215.841 s** (**+6.17%**), a labelled sensitivity because the original baseline
cannot construct this case. Focused hierarchy regressions pass; locked full
checks pass with **2,788 Python tests**, 17 optional skips, strict types/format/
lint and 23 Rust tests. Private evidence is in
`local_data/history-120/h7/timed-heldout/wall-1001-*/`.

The held-out source was frozen before the first held-out run, then the actual
failure required this narrow construction correction. The history policy and
thresholds were not tuned. Twenty prior successful timings are reused only where
the C488 coast filter is an identity; Wall/1001 uses the labelled matched-static
sensitivity and Wall/1002–1004 were measured on C488. All 24 rows are retained in
`timed-heldout-c488/summary.json`.

[V-EXEC] Locked full checks pass: **2,761 Python tests**, 17 optional skips,
strict types/format/lint and **23 Rust core tests**. Desktop checks/build pass
with no Svelte warnings, **15 interface tests** and **5 Rust shell tests**.

## Final held-out acceptance and local delivery

[V-EXEC, 2026-11-05; source commit `eb053fd`] The corrected held-out full-normal
timing cohort passes S8. Across 23 pairs with a successful original 1.1.0
baseline, added time has a **13.05% median** and **15.57% p95**. Including the
explicit Wall/1001 matched-static sensitivity, these are **12.75%** and **15.53%**.
The first 20 successful C487 measurements are reused only where C488's boundary
coast filter is proven to be an identity; four later cases were measured with
C488. These timings are regression evidence, not a fresh independent 24-pair
rerun.

On the corrected C488 reference pair, the original full producer and writers
take **202.547 s**, and history takes **229.793 s** (**+13.45%**). Peak memory
increases by **2,608 KiB = 2.547 MiB**, below S9's 256 MiB ceiling. The current
normal output passes all checks for 872 nonmetadata files and exactly matches
the pending epoch-61 golden, SHA-256
`435074c7582a41ea94e4872637db3deaeb0082a1b60c6bee659659d6668577fb`. The pinned
1.1.0 source on current EU5 1.4.7 inputs writes 868 files; its patch-dependent
digest is not substituted for the immutable epoch-60 golden. The standalone
reference reproduction and three-world layers check also pass on C488.

The C488 all-world native matrix completes for the corrected physical inputs;
the C488 sweep matrix contains 96 metric rows over 32 controls. Artifact
verification passes every native output. S1–S4 size, S6, S7 zero-seed and S11
pass. Three frozen acceptance checks fail:

- **S4 sweep:** Spearman midrank correlation across the eight raw state-size
  endpoints is **0.8889**, below **0.9**.
- **S5:** `small_continents/1002` reaches **51.90% at Calm** and **60.76% at
  Varied** for its largest polity with subjects on a qualifying landmass; the
  limit is 50% at both levels. Turbulent is reported separately and has no
  threshold.
- **S7:** Varied realizes **2 of 13** seeded great-empire trajectories (**15.38%**),
  below the required 30%. The two realized cases are
  `small_continents/1003` and `supercontinent/1001`.

The held-out acceptance record therefore has `all_pass: false`. S8 passes both
seed sets; the reference wrapper is **505,104 bytes**, the largest sweep wrapper
is **568,069 bytes**, and all are within S11. Real-export cancellation is
observed in **0.207 s**, with no completed output or spool left. A Windows
portable Python run under Wine and Linux runs (1 thread/hash seed 1 and 31
threads/hash seed 927) produce the same canonical full-plan SHA-256
`c10cc61de7e208e14e34bdc4bed77031077a5922d3374b3ad083bb8be02c2cf0`, exactly
53,948,865 canonical bytes, and history digest
`130c11aeabc5486860174fb5b587b0b1a1b2b0e2936333607afdbd72aa2e775f`.

The Linux standalone and packaged Windows hub pass their offscreen self-tests;
the latter and cross-platform native run were exercised under Wine. Local Linux,
Windows and Workshop/Proton archives pass the packaging allowlist audit and
SHA256SUMS verification. Their hashes are recorded in the ignored local
`dist/history-120-c488-{native,windows}/` folders. Nothing was published,
installed to a game profile, or enabled in a playset; EU5 was not launched.
Because the held-out thresholds fail, H7 candidate installation, hub replacement
and the owner sitting remain pending an explicit next calibration/acceptance
decision. The held-out results remain validation evidence and must not be used
to tune the current policy.

## Single-seed end-to-end stage profile (2026-11-06)

[V-EXEC] A normal `rnw world` run of Continents seed `319218363` (code
`RNW1-040G0-00000-9GDRN-V0410-002P3-ZZG`) completed in **258.8 s** (4:18.8),
with a process peak of **8.5 GiB**. It ran 1.2.0 development / pending epoch 61
against EU5 1.4.7 / build 26377361, with the default 31 threads and four
overlapping stage workers. Its dedicated land cache started empty; the OS file
cache was warm from an earlier interrupted run. The export completed its normal
output checks and wrote a compact world file; it was not installed or loaded in
EU5. This is a diagnostic single seed, not a paired S8 measurement or a new
acceptance result. Raw timings and output are in the ignored
`local_data/perf-20261106-continents-retry/` folder.

| Stage | Elapsed |
|---|---:|
| `load map` | 2.3 s |
| `select canvas` | 11.8 s |
| `generate world` | 54.7 s |
| ↳ `land cells` (overlapping substage) | 18.9 s |
| ↳ `sea cells` (overlapping substage) | 15.5 s |
| ↳ `relief` (overlapping substage) | 18.2 s |
| `vanilla reads` | 1.5 s |
| `vanilla geometry` | 1.9 s |
| `vanilla localization keys` | 11.4 s |
| `vanilla climate` | 16.6 s |
| `vanilla material levels` | 12.3 s |
| `vanilla natives` | 7.3 s |
| `settle coasts` | 13.9 s |
| `water shapes` | 5.8 s |
| `biomes and rivers` | 22.5 s |
| `identities` | 28.4 s |
| `world checks` | 30.3 s |
| `water textures` | 28.7 s |
| `slot tables` | 0.1 s |
| `location rasters` | 1.3 s |
| `png encoding` | 3.5 s |
| `terrain decals` | 111.2 s |
| `vegetation instances` | 14.0 s |
| `terrain` (aggregate of its work below) | 126.6 s |
| `natives` | 30.5 s |
| `atlas` | 1.9 s |
| `texts` | 13.4 s |
| `stories` | 4.9 s |
| `spline network` | 10.9 s |
| `script remap` | 5.4 s |
| `selection cover` | 0.8 s |
| `write files` and final persistence | ~9 s residual; not separately timed |

Durations overlap: the rows must not be added, and the `terrain` aggregate
includes its decal and vegetation work. `write files` currently reports progress
but does not use the timing helper. [INFERRED] The ~9 s residual is the total
service time after the last timed stage and also includes final world-file and
library persistence. The longest compute block is `terrain decals` (111.2 s);
the next largest is `generate world` (54.7 s). The latter is on the serial prefix
before downstream stages start, while terrain overlaps the native/text/script
branch. In this run terrain finished about 21 s after the selection-cover branch;
that is the initial end-to-end saving available from terrain-only work before
another branch becomes critical. Within `generate world`, the land/sea/relief
subtimers start 26 s after the parent and finish about 10 s before it, so a
follow-up profile should split the unlabelled preparation and finalization there.
The offsets also leave about 23 s after `script remap` ends and before
`selection cover` starts; instrument the intervening content, treaty and
localization checks before attributing that time to the 5.4 s remapper.

### Follow-up: the waits removed (2026-11-07)

[V-EXEC] The reference world of `tests/golden_world.json` (pending epoch 61, EU5 1.4.7 /
26377361, 31 threads, no land cache) took 295.3 s at `c229899` and 231.3 s at `d3d1b98`, with the
same output digest (`e1e4699e`, 884 files) and an 8.5 GiB peak (C505). Most of the difference was
waiting, not computing: alone on the captured inputs, `terrain_outputs` took 27–32 s, against
134.6 s for `terrain decals` in the export. A stage that makes many small native or NumPy calls
waits for the interpreter after each one while the main thread runs Python (natives, texts,
checks). With two threads spinning in pure Python beside it, the same terrain did not finish
within 600 s before the native layer reader and stamps; with one such thread it took 165 s
after them (42 s with a 0.5 ms switch interval). In the export a 0.5–1 ms switch interval sped
the terrain branch up but slowed `natives` and gained nothing overall, so the interval stays at
its default. Timings below are the final run's unless stated.

| Stage | Before | After |
|---|---:|---:|
| `select canvas` (kept per map input once selected) | 15.5 s | 12.4 s; 0.02 s kept |
| `generate world` | 59.3 s | 39.0 s; 32.9 s from a sketch |
| `terrain decals` | 134.6 s | 81.2 s, finishing before the main thread |
| `vegetation instances` | 17.0 s (after the main thread's work) | 25.1 s, beside the main thread |
| `stories` | 5.6 s | 0.8 s |
| Six sketches (`rnw.app.candidates`) | 205 s of land stages in the owner's 2026-11-01 log | 35.9 s; 21.5 s for five with the canvas kept |

The main thread is now the critical path: `natives` (about 48 s, of which the causal replay of
`validate_history` is 17 s), `texts` (19 s), the spline network (11 s) and the content checks
after the remap, with terrain finishing about 13 s before it. The history engine was left as
it is during the R6 freeze. Raw timings are in the ignored `local_data/perf-20261107/` folder.

### Follow-up: the history engine (2026-11-07)

[V-EXEC] The owner lifted the R6 freeze for this work (2026-11-07). At `823b662` one history start
(`build_history_start` on the captured input of continents/3, Varied, alone) takes about 22 s
instead of 36 s, and the whole result is the same (C506). A fifth of the old time went to
Python's automatic garbage collections, which walked millions of live history records again and
again and found nothing to free; the collector now pauses for a history start and for each export
and collects once at the end (a whole export leaves about 36 MiB of cycles, chiefly parsed
scripts). The rest is less work in each of the 60 rounds, which the causal replay repeats:
one search gives all of a realm's burden distances instead of one per place, a round's event
tables extend the previous round's, unchanged settlements and the geography's totals are not
checked again, draws share their hashed prefix, and choices that eligibility refuses for every
member (migrations between hostile societies) are not enumerated.

| Measure (31 threads) | Before | After |
|---|---:|---:|
| One start, continents/3 Varied, alone | 35.7 s | about 22 s |
| `simulate` + causal replay, same input, collector off for both | 22.6 s | 16.9 s |
| 22 captured starts (six presets × three levels, four sweeps), 11 at a time | 789.6 s | 479.6 s |
| R6 development matrix, 192 starts | 8.2 min (about 12 workers) | 4.2 min (31 workers, the machine's default) |
| `natives` in the reference export | 48.5 s | 27.9–29.4 s |
| `texts` in the reference export | 19.0 s | 12.7–13.3 s |
| Reference export, no land cache | 221–231 s | 200–211 s |

Equality: the 22 starts are equal field by field (`FinalStartPlan` and the R6 observation);
`R6_OUT=dev-c506` reproduces all 192 observations of `dev-d31` exactly; the reference world keeps
digest `e1e4699e` (884 files) with the default threads and with `RNW_THREADS=1 RNW_MEMORY=1500`.
In the export the terrain branch (92–103 s from 99 s) and the main thread (natives, texts, the
spline network and the remap, done by about 176 s) now end within a quarter of a minute of each
other, so a further gain needs both. With 31 starts on 16 cores a start takes a median 36.8 s,
so the matrix is near what the machine allows.

[V-EXEC] The development inputs predate the region layout W8 (`74b936b`, after the e60b77e
freeze). A capture of continents/3 at `823b662` puts 7,686 of its 8,773 cells in another region
and 8,090 in another area than the capture the calibration used, and its Varied start differs in
21 of the 25 numeric measures of the observation (republics 13 → 41, conflicts 647 → 703, one
seeded great empire → none). The development checks therefore describe the pre-W8 layout; the
held-out captures of runbook step 3 would have the new one.

## Development checks on the W8 layout (2026-11-07)

[V-EXEC] Step 1 was rerun on the current W8 physical inputs with the frozen history source at
`823b662` (`source_sha256` `b62231a9…a5a464`). The local harness routed inputs and baselines only
through `local_data/history-120/r6/w8/` when `R6_INPUTS` was set, so older H7 captures and
baselines could not shadow them. The 48 captures cover six presets × seeds 3/42/77/1000–1004;
each is physical-only, with at most four captures in flight. Successful captures retained only
`native-inputs.pkl` and `capture.json`; temporary land caches and generated data were removed.
The pinned 1.1.0 native producer supplied 48 world baselines and 24 baselines for the low/high
control sweeps (the default and turbulence rows use their world baseline). Every baseline points
to `baseline-source/src/rnw`. Two spot checks confirmed changed region assignments with unchanged
cell counts: continents/3, 7,686 of 8,773; archipelago/42, 4,431 of 7,447.

All 192 starts and sweeps completed `ok`; every output's source hash matches the freeze. No knobs
or acceptance thresholds changed. All fourteen checks were evaluated on the full matrix:

| Check | Gate | `dev-d31` | W8 | Result on W8 |
|---|---|---|---|---|
| Q1 | Patchwork, rivals and paramount ≥10%; fractured ≥3%; any class ≤50% | 41.2 / 40.9 / 11.6 / 4.1% | 40.2 / 43.8 / 12.1 / 2.4% | Fail: fractured share |
| Q2 | Median ≥3 region classes | 3.0 (48 worlds) | 3.0 (46 eligible worlds) | Pass |
| Q3 | Turmoil ratio ≥1.5; rising in ≥75%; class directions; continuity ≥0.40 | 2.193; 97.9%; 0.865 | 2.218; 100%; 0.859 | Pass |
| Q4 | Prudent realized ≥70%; overreach ended ≥50%; each group ≥50% | 74.2% (132/178); 56.4% (114/202); groups 80 / 80 / 66.7% | 61.0% (100/164); 62.9% (139/221); groups 93.8 / 90.9 / 100% | Fail: prudent realization |
| Q5 | All 16 control sweeps monotone, with high > low | No failures | `turbulence/continents-3`: 0.109 → 0.195 → 0.191 | Fail |
| Q6 | Great-empire ratio 0.5–1.5; ≥3 high-sweep worlds | 0.791; 31 realized; 4 worlds | 0.791; 30 realized; 4 worlds | Pass |
| Q7 | Varied ratio 0.75–1.25; Calm/Turbulent 0.60–1.40 | 1.000 / 1.000 / 0.667 | 1.000 / 1.000 / 0.667 | Pass |
| Q8 | Continent share ≤50%; landmass share ≤85%; no >20% dominated | No failures | No failures | Pass |
| Q9 | Subjects median 8–40; ≥90% scaled | 33.5; 99.4% | 33.0; 99.3% | Pass |
| Q10 | Alliance median 4–30 | 12 | 11 | Pass |
| Q11 | Republic median ≤25%; IQR ≥5 points; types; assortativity ≥0.20 | 13.5%; 8.8 points; yes; 0.254 | 15.8%; 11.1 points; yes; 0.240 | Pass |
| Q12 | Largest family ≤35%; routine ≤20%; distinct ≥3; short ≥10%; length ≤8 | 25.8%; 18.2%; 3; 23.6%; 8 | 25.7%; 18.2%; 3; 23.2%; 8 | Pass |
| Q13 | Visible median ≥50% | 91.0% | 90.9% | Pass |
| S11 | Archive ≤8 MiB | 584,589 bytes | 584,739 bytes | Pass |

Thus 11 of 14 pass; Q1, Q4 and Q5 fail. The earlier narrow margins remain visible: long-chronicle
families are still exactly three, and the unchanged Turbulent Q7 ratio of 0.667 is 0.067 above its
floor. Paramount share is now 12.1%, 2.1 points above its gate (11.6% before); fractured share
falls from 4.1% to 2.4%, 0.6 points below its gate.

Q4 on the two recognition scales, over the 48 Varied starts with the 9/9 great-empire aims added
to both rates, is:

| Scale | Regional power | Paramount | Combined |
|---|---:|---:|---:|
| R6 recognition | 71/112 = 63.4% | 12/29 = 41.4% | 92/150 = 61.3% |
| Q1 regional-share rule | 57/112 = 50.9% | 5/29 = 17.2% | 71/150 = 47.3% |

The corresponding `dev-d31` combined rates were 123/168 = 73.2% and 92/168 = 54.8%. The Q4
acceptance row above also includes the high `empire_permille` sweeps, so its denominator differs
from the 48-world Q4-scale diagnostic.
The combined figures above correct the first report, which inadvertently added five great-empire
aims from the high sweeps to this world-only diagnostic; the acceptance result was unaffected.

Ranked by median absolute delta across the 18 preset × level groups, the largest shifts were in
archive bytes, assortativity, ownership locations, conflicts and ownership events. Each group
median pairs the eight seeds; the level columns give signed medians across the six preset groups,
followed by the largest absolute group median. Assortativity is in thousandths.

| Measure | Calm Δ | Varied Δ | Turbulent Δ | Largest group median Δ |
|---|---:|---:|---:|---|
| Archive bytes | +214 | +806 | −1,413 | Supercontinent / Turbulent −5,455 |
| Assortativity (‰) | +18 | −3 | +8 | Small continents / Turbulent +129 |
| Ownership locations | +2 | +14 | +37 | Supercontinent / Varied +95.5 |
| Conflicts | +15 | +9 | +22 | Archipelago / Turbulent +100 |
| Ownership events | +9 | −3 | +9 | Islands / Turbulent +42 |

The capture phase took 2,107.6 s (35 min 8 s); the 72 baselines took 19.8 s; the 192-row matrix
took about 3 min on its automatically sized 31-worker pool. EU5 was not launched, and held-out
seeds 1005–1008 were not captured or run. Since three checks fail, stop before runbook step 3;
plan D28 leaves the next decision to the owner.

### W8 fixes and renewed development calibration (2026-11-07)

[V-EXEC] After C507 the owner authorized fixing the failures and reopened development. The
48 W8 inputs and their pinned 1.1.0 baselines were reused; no world was excluded, no held-out
input was captured or run, and `history_acceptance`'s thresholds and classifier precedence
were unchanged. The final source SHA-256 is `3a125fed…3d048d2`; the complete development run is
the ignored `local_data/history-120/r6/dev-w8-verified/` (192 rows, all `ok`, matching source
hashes). It reproduces every observation of the successful `dev-w8-final/` run after removal
of an unused helper. The measured wall time was 286.7 s, with other verification running.

The fixes address construction and causality, plus one measurement defect:

- Coordination and contest effort now use burden relative to administrative capacity.
  Previously a realm using a quarter of its enlarged capacity could already hit the absolute
  coordination penalty floor. The ordinary capacity of 1,000 retains its prior calculation.
- An expansion aim prefers the largest eligible gain against the same opponent, including a
  neighbour that crosses its domain boundary. A paramount keeps its preference for leaving a
  defeated neighbour standing. Regional centres need reachable room for their recognition
  share and scale; paramounts also need room against inaccessible founding rivals.
- Actual overload adds secession propensity, as D24 requires, rather than only enabling it.
- Direct resubmission after independence needs fear from a new defeat. The preceding trial
  contained 107 resubmissions without a new defeat; a current third-party threat remains valid.
- Fractured-region measurement follows the explicit source realms of successive secessions.
  Those actors stay parentless for aim inheritance. On the same saved starts this correction
  moves five patchwork regions to fractured (9 → 14 of 331), with no change to their histories,
  the rival/paramount/great classes, the 30% lineage rule or classifier precedence.

The gain-only trial raised prudent realization from 61.0% to 64.0%; room and overload reached
65.6%; relative coordination reached 75.9%. `LORD_POWER` is calibrated from 3 to 4: the subjects
median fell from 42.5 to 40.5 before the resubmission fix brought it to 39.5. Two trials were
rejected: `ESCALATION=1600` left two turbulence-sweep failures, so it stays 1200;
`UNREST_SLOPE=450` left 8 fractured regions, 43.5 subjects and one sweep failure, so it stays
350. `PRUDENT`, recognition shares, the other knobs and all acceptance thresholds stay as before.

All fourteen final checks pass (gates are in the preceding table and plan §18):

| Check | Final value |
|---|---|
| Q1 | Patchwork 35.95%, rivals 42.90%, paramount 13.29%, fractured 4.23%, great realm 3.63% |
| Q2 | Median 3 classes, 46 eligible worlds |
| Q3 | Recent-turmoil ratio 2.103; rising in 97.9%; class directions hold; continuity 85.31% |
| Q4 | Prudent 121/162 = 74.69%; overreach ended 177/223 = 79.37%; groups 93.75 / 90.91 / 100% |
| Q5 | All 16 control sweeps monotone |
| Q6 | Great-realm ratio 0.866; 31 realized; four high-sweep worlds |
| Q7 | Ordinary-size ratios 1.000 / 1.000 / 0.667 |
| Q8 | No domination failures |
| Q9 | Subjects median 39.5; 99.57% scaled |
| Q10 | Alliance median 11 |
| Q11 | Republic median 15.01%; IQR 9.88 points; types hold; assortativity 0.255 |
| Q12 | Largest family 25.52%; routine 18.32%; distinct 3; short 25.03%; length ≤8 |
| Q13 | Visible median 90.80% |
| S11 | Largest archive 574,884 bytes |

The turbulence sweep's recent-turmoil shares at Calm / Varied / Turbulent are 0.120 / 0.240 /
0.258 (continents/3), 0.109 / 0.141 / 0.242 (continents/42), 0.046 / 0.164 / 0.218
(archipelago/3), and 0.126 / 0.184 / 0.188 (archipelago/42). Thin margins remain: subjects 39.5
against 40, long-chronicle families exactly three, and Turbulent Q7 0.667 against 0.60.

Q4 at both scales on these 48 Varied starts (the same 9/9 great-empire aims enter both combined
rates; high sweeps are included only in the acceptance row above):

| Scale | Regional power | Paramount | Combined |
|---|---:|---:|---:|
| R6 recognition | 81/111 = 73.0% | 21/29 = 72.4% | 111/149 = 74.5% |
| Q1 regional-share rule | 68/111 = 61.3% | 12/29 = 41.4% | 89/149 = 59.7% |

Locked dependency sync and `make check` passed: format, lint, strict types, 3,035 Python tests
(17 optional skips) and 29 Rust tests. The synthetic divided-valley golden is now `1908cd27`:
comparison with `823b662` finds identical facts and events apart from two contest effort
commitments, 614 → 610, from the relative-load correction. The first full installed-game
reference export took 238.4 s and passed all normal writers and output checks, producing
`3a0eff79d1d23a819d9c8915960879a5502139130218c8cb1017475e4752afdb` (884 files) on the unchanged
game fingerprint. The pending epoch-61 golden is updated; the frozen epoch-60 and epoch-59
references are unchanged.
An independent installed-game reference test reproduced that digest and passed its additional
map/content assertions (`1 passed`, 220.2 s); EU5 itself was not launched.

The source is committed and frozen at `ea4b676` (`3a125fed…3d048d2`). The old freeze is preserved
as `local_data/history-120/r6/heldout-freeze-823b662.json`; the active record pins the W8 inputs,
final acceptance artifact, source, knobs, thresholds and reference. Step 3 was not started.
No hub replacement or game-profile installation belongs to this development calibration.

### R6 held-out run (2026-11-07)

[V-EXEC] Steps 3–4 of the [R6 runbook](../history-core.md#r6-runbook) completed against
the active freeze: source commit `ea4b676`, source SHA-256
`3a125fed6fcd31569973f9fb03abd9e7c40aed2f18dcf3c65367218cb3d048d2`, algorithm epoch 61,
EU5 1.4.7 / build 26377361. The source hash matched before and after the run. Step 3 captured
the six presets at seeds 1005–1008 (24 physical inputs) and generated 24 ordinary plus 24
non-default sweep baselines using the saved v1.1.0 source. Step 4 completed all 120 rows:
72 worlds and 48 control sweeps. All outputs record the frozen source hash. The Varied starts
were saved for the D30 Q4 diagnostic. No EU5 session was launched.

The frozen evaluator reports **12 of 14 checks passing**. Q1 fails only on fractured regions;
Q9 fails only on the median subject count. All other statistical checks and S11 pass:

| Check | Held-out result |
|---|---|
| Q1 | **Fail:** patchwork 26.16%, rival powers 48.84%, paramount 22.09%, fractured 1.74% (minimum 3%); largest class 48.84% |
| Q2 | Median 3 classes across 24 worlds |
| Q3 | Turbulent/Calm turmoil 2.387; rises in 100% of worlds; class directions hold; continuity 85.94% |
| Q4 | Prudent recognition 77.59%; overreach ended 74.19%; league 90.9%, confederation 100%, sacred centre 60% |
| Q5 | All 16 control sweeps monotone |
| Q6 | Great-realm ratio 0.659; 12 realized; four high-sweep worlds |
| Q7 | Ordinary-size ratios 1.000 / 1.000 / 0.667 at Calm / Varied / Turbulent |
| Q8 | No landmass-dominance failures |
| Q9 | **Fail:** median 42 subject pairs (maximum 40); 99.51% scaled |
| Q10 | Median 9.5 alliances |
| Q11 | Republic median 18.60%; IQR 14.90 points; government types hold; assortativity 0.2075 |
| Q12 | Largest family 25.29%; routine 17.98%; 3 distinct families; 24.02% short chronicles |
| Q13 | Median 91.47% of landed countries visible |
| S11 | Largest archive 554,854 bytes |

Q4 at both recognition scales on the 24 Varied worlds is:

| Scale | Regional power | Paramount | Combined |
|---|---:|---:|---:|
| R6 recognition (D30 gate) | 63/79 = 79.7% | 14/22 = 63.6% | 81/105 = 77.1% |
| Q1 regional-share rule | 53/79 = 67.1% | 13/22 = 59.1% | 70/105 = 66.7% |

The four prudent great-empire aims are included in both combined rates (4/4 realized).
The Q1-scale row is diagnostic under D30; Q4 passes on the frozen R6 recognition rule.
The local evidence is in the ignored `local_data/history-120/r6/captures/`, `baselines/`,
`sweep-baselines/` and `heldout/` directories, including `heldout/acceptance.json` and
`heldout/q4-scales.txt`. Because Q1 and Q9 fail, the runbook stops before step 5; no tuning,
new freeze or repeated held-out run was made. Plan D28 requires a further decision before R6
continues.

### D32 round: development findings on 72 worlds (2026-11-07)

[V-EXEC] After the owner's D32 decision (seeds 1005–1008 join development), the 72 worlds
at frozen source `ea4b676` give, at Varied: fractured regions 17/503 = 3.4%, median
subject pairs 41, prudent recognition 192/254 = 75.6% (`it72-base`). No held-out input
of 1009–1012 was captured. Thresholds and classifier are unchanged.

- **Fractured is a leftover class.** The fractured rule (living successors of one recorded realm
  hold at least 30% of the region) is true for 47 of 172 held-out and 80 of 331 W8 development
  regions, but great realm, paramount, league and rival powers are tested first. Ordering
  fractured above rivals would give 17.5% fractured, 30.8% rival powers, 16.3% paramount and
  32.6% patchwork on the 72 worlds; above paramount, 23.3% / 30.8% / 10.5% / 32.6%.
  Knobs move the share only within sampling noise (2.8–4.0% across `UNREST_SLOPE` 280–450,
  `PRUDENT` 40%, `LORD_LOCATIONS` 3–4). A held-out set has about 170 regions: a true share of
  4% falls under 3% with probability 0.31, 5% with 0.14 and 6% with 0.05.
- **Subjects.** Net 41 pairs per world are 53 submissions and 12 independences (the 72 starts
  hold 3,828 and 846 accepted events); the median subject has one location. Lord capacity
  (`CLIENT_CAPACITY_MULTIPLIER` 3 or 2) and `LEAVE_POWER` 3 barely move the median (40.5 / 39.0 /
  40.5). `LORD_LOCATIONS` 4 gives 35.5 and `ORDINARY_LORD_POWER` 6 gives 32.0 with Q4, Q7 and
  the other checks intact.
- **Coupling with Q5.** The full 72-world matrix with `ORDINARY_LORD_POWER` 6
  (`dev72-ord6`, 216 starts and 96 sweep rows) passes 13 of 14: Q5 fails on the
  continents/3 turbulence sweep, 0.120 → 0.253 → 0.221. At the committed value 4 all eight
  turbulence pairs are monotone, but archipelago/42 steps 0.184 → 0.188. Lord-margin values
  5 and 6, `LORD_LOCATIONS` 3–4 and `ESCALATION` 1600–2000 each leave one or two
  non-monotone pairs, always Varied above Turbulent: Turbulent recent turmoil sits at
  0.19–0.28 whatever the rule. The change is not committed.

Evidence is in the ignored `local_data/history-120/r6/dev72/` (inputs), `it72-*`, `dev72-ord6/`
and `turb-*` folders.

### D33: classifier order, turbulence control and lord margin (2026-11-07)

[V-EXEC] Decision [D33](../history-plan.md#213-decisions), made by the agent under the owner's
delegation before any capture of seeds 1009–1012. Source: the working tree that the D33 commit
records, source SHA-256 `b0ff59fd…6959e`, EU5 1.4.7 / 26377361. Three changes: fractured is tested
before rival powers; Q5's turbulence order is read pooled over the seed set (each sweep pair must
still be higher at high than at low); `ORDINARY_LORD_POWER` 6 with `UNREST_SLOPE` 450.

*Why Q5 changed.* On the 72 worlds with `ORDINARY_LORD_POWER` 6, recent turmoil pools to 0.103 /
0.173 / 0.230 at Calm / Varied / Turbulent. The per-world Turbulent − Varied step averages +0.055
with a standard deviation of 0.045 (7 of 72 worlds negative), so a test of four single pairs, each
non-decreasing, passes with probability near 0.6 for any rule. The event counts show why a
mechanism cannot widen the step cheaply: from Varied to Turbulent, conflicts triple, but most are
failed attacks (continents/3 at margin 6 and slope 350: 333 → 602 accepted conquests in the whole record, 306 → 1,384
failed; recent secessions 66 → 125), and the share of land last taken by turmoil moves 0.25 →
0.22–0.26. Changed land is bounded by capacity and rebound by breakaway. The pooled order has a
standard error near 0.01 on 24 worlds.

*Lord margin and unrest.* Single-knob trials on the 72 Varied starts (median subjects /
authority assortativity, Q11 floor 0.2): base 41 / 0.251; `LORD_LOCATIONS` 4 35.5 / 0.2625;
`ORDINARY_LORD_POWER` 6 32.0 / 0.2375; with `UNREST_SLOPE` 280 31.5 / 0.2375; with 450 35.0 /
0.2765. The lord margin cost 0.014 of Q11's margin (on the 24 failed held-out worlds it gave
0.1965), against the D32 rule that no other check loses margin. A steeper unrest slope more than
returned it. Drawing 400 held-out-like sets (four of the twelve development seeds per preset,
24 worlds each, the 96 sweep rows fixed) and applying every check: margin 6 alone failed some
check in 7.2% of draws (Q11 6.8%, Q4 0.5%); margin 6 with slope 450 in 2.8% (Q9 1.5%, Q11 1.0%,
Q8 0.3%). The draws overlap in the same 72 worlds, so the figures compare candidates and do not
predict the held-out probability.

The full matrix of the committed source (`dev72-d33f/`, 216 starts and 96 sweep rows; equal to
the same values set through `R6_KNOBS`, `dev72-d33-u450/`) passes all fourteen checks:

| Check | Development value (72 worlds) |
|---|---|
| Q1 | Patchwork 34.8%, rival powers 27.0%, paramount 18.3%, fractured 17.7%, great realm 2.2% |
| Q2 | Median 4 classes (70 worlds with at least four regions) |
| Q3 | Turbulent/Calm turmoil 2.235; rises in 100% of worlds; fractured + patchwork 36.6% → 65.4%; paramount 25.8% → 12.5%; continuity 81.7% |
| Q4 | Prudent recognition 78.4%; overreach ended 77.5%; league 88.9%, confederation 92.9%, sacred centre 71.4% |
| Q5 | Pooled recent turmoil 0.109 / 0.186 / 0.243; every pair of all four controls higher at high than at low |
| Q6 | Great-realm ratio 0.769; 42 realized; eight high-sweep worlds |
| Q7 | Ordinary-size ratios 1.000 / 1.000 / 0.667 at Calm / Varied / Turbulent |
| Q8 | No landmass-dominance failures |
| Q9 | Median 35 subject pairs; 99.6% scaled (development target ≤ 35 met; gate 40) |
| Q10 | Median 10 alliances |
| Q11 | Republic median 15.9%; IQR 10.8 points; assortativity 0.2765 |
| Q12 | Largest family 25.2%; routine 18.1%; 3 distinct families; 25.4% short chronicles |
| Q13 | Median 91.2% of landed countries visible |
| S11 | Largest archive 577,419 bytes |

The earlier W8 trial that rejected `UNREST_SLOPE` 450 (above) ran at lord margin 4, under the
per-pair Q5 and the old classifier. The thinnest margins now are Q9 (35 against 40), Q7 at
Turbulent (0.667 against 0.6, a median of ratios of whole-location sizes), and Q4's prudent
recognition (78.4% against 70%). Fractured at 17.7% (target 4%) no longer depends on a leftover
count. The development evidence is in the ignored `local_data/history-120/r6/dev72-d33f/`,
`dev72-d33-u450/` and `it72-*`.

### D33 held-out run (2026-11-07)

[V-EXEC] Steps 2–4 of the [R6 runbook](../history-core.md#r6-runbook) on the new freeze: commit
`1f6bc79`, source SHA-256 `b0ff59fdd48acbc34170120af64b7731d45ee4490cd70f3c296008018fb6959e`,
algorithm epoch 61, EU5 1.4.7 / build 26377361 (installed build checked). The freeze record was
written before any capture; the record of `ea4b676` is kept as `heldout-freeze-ea4b676.json`.
Step 3 captured the six presets at seeds 1009–1012 (24 physical inputs, 0 failures) and produced
24 ordinary plus 24 sweep baselines from the saved v1.1.0 source. Step 4 completed all 120 rows
(72 worlds, 48 sweeps) from the frozen source, once; outputs are in `heldout-d33/`, the C509 run
stays in `heldout/`. No EU5 session was launched. No knob, threshold or code changed after the run.

The frozen evaluator reports **11 of 14 checks passing**. The two checks of C509, Q1 and Q9, now
pass. Q4, Q5 and Q7 fail:

| Check | Held-out result |
|---|---|
| Q1 | Pass: patchwork 30.72%, rival powers 27.71%, paramount 17.47%, fractured 19.28%, great realm 4.82% (166 regions) |
| Q2 | Pass: median 4 classes (23 worlds) |
| Q3 | Pass: Turbulent/Calm turmoil 2.297; rises in 100% of worlds; class directions hold; continuity 82.4% |
| Q4 | **Fail:** prudent recognition 77.42% and overreach ended 63.72% pass; sea league 5/6, sacred centre 1/1, **highland confederation 0/1** (gate: each seeded kind ≥ 50%) |
| Q5 | **Fail:** `state_locations`/archipelago-1009 ordinary median 2.5 (setting 2) → 2 (setting 3) → 8 (setting 10). Turbulence passes: pooled recent turmoil 0.101 / 0.165 / 0.232 |
| Q6 | Pass: great-realm ratio 0.962; 31 realized; four high-sweep worlds |
| Q7 | **Fail:** ordinary-size ratios 1.000 / 0.667 / 0.667 at Calm / Varied / Turbulent (Varied gate 0.75–1.25) |
| Q8 | Pass |
| Q9 | Pass: median 37.5 subject pairs (gate 40); 99.49% scaled |
| Q10 | Pass: median 10.5 alliances |
| Q11 | Pass: republic median 12.2%; IQR 8.15 points; assortativity 0.2285 |
| Q12 | Pass: largest family 24.63%; routine 17.4%; 3 distinct families; 22.13% short chronicles |
| Q13 | Pass: median 92.0% of landed countries visible |
| S11 | Pass: largest archive 634,889 bytes |

Q4 at both recognition scales on the 24 Varied worlds (`q4-scales.txt`, D30): R6 recognition
61/81 = 75.3% combined; Q1 regional-share scale 53/81 = 65.4%.

*Read of the three failures (diagnosis only; nothing was rerun on these seeds).*

- **Q4 rests on one aim.** Only one highland confederation was seeded in the 24 Varied worlds (the
  72 development worlds seed 14, 13 realized, 0.19 a world; P(at most 1 of 24) ≈ 5%) and it was not
  realized. The gate is a rate over a count of one.
- **Q5 compares adjacent settings of a quantized statistic.** A world's ordinary median is 2, 2.5
  or 3, and the low and default settings are 2 and 3. The development matrix shows the same
  ties (archipelago/42: 2.0, 2.0; continents/1005: 3.0, 3.0; continents/1006: 2, 2); one pair fell the other way here. It is
  the same kind of flaw as the turbulence step that D33 pooled, in a control D33 did not examine.
- **Q7 sits on a cliff at Varied, and D33 moved it closer.** The ratio per world is 1.0 where the
  ordinary median is 3 and 0.667 where it is 2 (the 1.1.0 baseline is 3 in 22 of 24 worlds), so the
  median over worlds flips when more than half the worlds fall to 2. Share of development
  worlds at 2 with `UNREST_SLOPE` 350 / margin 4 (`it72-base`): 25%; margin 6 alone: 15%; margin 6
  with `UNREST_SLOPE` 450 (the D33 choice): 33%. Held-out: 15 of 24 (62.5%; archipelago, islands,
  supercontinent and wall 3 of 4 each). D33's candidate comparison counted Q7 as passing in all
  400 draws and so did not weigh that this knob roughly doubled the share near the cliff; the
  margin-6-alone candidate had traded it for Q11 margin (6.8% draw failures).

Held-out seeds 1009–1012 are used; they cannot serve as held-out again. Per runbook step 4 the run
stops here and plan D28 requires a further decision before R6 continues; steps 5–8 (S8–S10,
reference reproduction, packages, the owner's sitting, W2, W6, W7) are not started. The
evidence is in the ignored `local_data/history-120/r6/heldout-d33/` (observations, saved Varied
starts, `acceptance.json`, `q4-scales.txt`), `captures/`, `baselines/` and `sweep-baselines/`.

### D34: checks inform, they do not gate (2026-11-07)

[V-EXEC] After C512 the owner ruled that the statistical checks are diagnostics, not release holds
([plan D34](../history-plan.md#213-decisions)). One change followed: `UNREST_SLOPE` 450 → 350, because
450 doubled the share of worlds whose ordinary median is two locations rather than the slider's three
(33% against 15% on the 72 development worlds; 15 of 24 on held-out). The full development matrix on the
resulting source (`dev72-d34/`, `ORDINARY_LORD_POWER` 6, slope 350, D33 classifier and Q5) reports all
fourteen checks passing with the same values as `dev72-d33/`: fractured 18.5%, rival powers 28.0%,
paramount 17.1%, patchwork 33.8%; pooled recent turmoil 0.103 / 0.173 / 0.230; median subject pairs 32;
assortativity 0.2375. No held-out set was run on this source. On the C512 held-out set every sweep
pair of every slider was higher at high than at low, and the four region classes held 17–31%.

**Delivery measurements on this source (2026-11-08).** The source is commit `94bf99b` (`src/rnw`
SHA-256 `1324b77c…c6a57d7a`), EU5 build `26377361`; `make check` and `make desktop` pass on it.
- [V-EXEC] **S8.** Twenty-four fresh sequential pairs (six presets × seeds 1009–1012, order
  counterbalanced, 16 workers, 16384 MiB, `nice 19`, separate empty land caches) of the 1.1.0
  source against this one, full normal generation: added time **median −17.3%, p95 −14.7%, max
  −14.5%** (the new source is faster; no pair is slower). Every 1.1.0 baseline constructed, so the
  explicit-sensitivity cohort equals the original one. The reference pair is 239.25 s → 198.42 s
  (−17.1%). The speed-up comes from the 2026-11-07 waits and history-engine work, not from less
  output: every stage through `write files` ran. Driver: `r6/timed_d34.py`, results in `r6/timed-d34/`.
- [V-EXEC] **S9.** Reference peak 9.70 → 9.33 GiB: **−362 MiB** (limit +256 MiB, reference workload
  only). The 24 seed-set pairs are not the S9 workload and are noisy in peak: median −86 MiB, range
  −644 to +1173 MiB on a peak near 9 GiB, with four pairs above +590 MiB (small_continents 1009 and
  1012, islands 1011, wall 1010). The peak of a 16-thread run depends on when stages overlap, so
  these differences are reported, not read as a regression or as a pass.
- [V-EXEC] **S10.** The normal exporter cancelled 50 ms into the reference's real history
  simulation exits in **1.78 s, 1.69 s, 1.75 s** (three runs, `h7/cancel_export.py`), no complete output
  or spool left. This meets the 2 s limit but is much closer to it than the 0.207 s measured on the
  C486 source; cancellation latency on a slower machine is the thinnest resource margin now.
  The cause is not investigated.
- [V-EXEC] **S11.** Largest history in `atlas.json` over the 216 development worlds of
  `dev72-d34`: **570,564 bytes** (limit 8 MiB).
- [V-EXEC] The installed-game reference export reproduces the pending epoch-61 golden:
  884 files, SHA-256 `79dbf588…21240` (`RNW_REPRODUCE=1`, 3 min 53 s).

## R6 development calibration of the audited redesign (2026-11-05)

[V-EXEC, 2026-11-05] This is step 1 of the [R6 runbook](../history-core.md#r6-runbook)
on the **development** set only: six presets × seeds 3/42/77/1000–1004 at Calm,
Varied and Turbulent (144 native starts), plus the 48 control sweeps
(continents/archipelago × seeds 3/42). No held-out world (1005–1008) was captured or
run. EU5 was not launched. The harness is the ignored `local_data/history-120/r6/`
(`matrix.py`, `evaluate.py`; `iterate.py` runs the Varied starts alone in about two
minutes for single-knob experiments). The acceptance thresholds in
`history_acceptance` were not touched.

**Defects found while calibrating.** Four were mechanisms, not knobs:

1. **Groups never realized (0 of 22 seeded).** League partners merged by union and so
   ended the league; confederation pacts needed a feared third party that tribes never
   had; recognition recomputed the 1037 eligibility predicates on the 1337 snapshot, so
   any change to a seeded member (or a sacred host's rank) unrecognized it. Now partners
   of one seeded league cannot unite, confederates also bargain on mutual trust after an
   exchange (plan D23's "common defence still needs recorded pressure" is revised), the
   partners of a group rank their pacts and exchanges first, and recognition reads the
   living descendants of the seeded members (largest pact network of at least three that
   holds the anchor; leagues need council authority and an exchange network).
2. **Relaxed recognition exposed an export failure.** A recognized confederate without
   farmland made `state_economy` refuse a landed country ("lacks farming support",
   islands/1000 at Calm and Turbulent). The old agrarian and density prerequisites are
   restored for confederates, so the failure cannot recur.
3. **Rival aims destroyed each other.** In 15 of 23 lost regional anchors the winner was
   the other aim of the same region, and half of an aim holder's contests were wasted
   because its pressure on a tribe took the round's single contest slot. Aim holders now
   contest states before pressing tribes, and rivals that both hold an aim keep the
   ordinary strength margin instead of parity.
4. **Lowering the capacity threshold let a great realm take 88.6% of a small landmass**
   (Q8, small_continents/1002 at Calm). Great-realm inclinations are 850/850 again,
   which keeps their former capacity.

**Adjustments.** Each was measured on the Varied starts first (48 worlds, about 230
prudent aims; a single run moves the prudent-aim rate by about ±3 points, so no change
of less than that was kept on one run alone).

| Knob | Before | After | Reason and evidence |
|---|---|---|---|
| `CAPACITY_THRESHOLD` | 1200 | 1100 | Prudent holders sat at about 0.7 capacity; paramount class 8.7 → 11–15% |
| `UNREST_SLOPE` | 600 | 350 | Conquer-and-secede churn left 172 secessions per world and 74% of subjects were one-location states; median ordinary state 2 → 3, subjects 53 → 39 |
| `REGIONAL_SHARE`, `LEAD_HALVES` | 150‰, 5 | 80‰, 4 | Recognition of a regional power: 8% of the region and twice its median state; prudent regional aims 41 → 65% together with the rival rule |
| `PARAMOUNT_SHARE` | 400‰ | 300‰ | Aim recognition only; many holders reached 33–41% at twice the next bloc. The Q1 classifier stays at 40% |
| `PRUDENT` | 80/60/40% | 80/45/30% | More overreaching aims leave more realm-and-breakaway lineages (fractured 1.4 → 3.8% on that run) |
| `DOMINANT_TRADITION` | 3 | 8 | Assortativity follows the founding tradition: 0.15 → 0.25 (a ×10 run gave 0.29) |
| `OPPORTUNITY` (new) | 3 halves for all | 5 / 3 / 2 | Strength an ordinary society needs without a grievance, at Calm / Varied / Turbulent |
| `ESCALATION` (new) | 0 | 1200 | Contest propensity beyond Varied; with the line above the turbulence sweep rises 500 → 800 in all four pairs |
| `ORDINARY_LORD_POWER` (new) | 3 | 4 | Lords without an aim need 4× the subject's strength; aim holders keep 3×. Subjects 39 → 33.5 without shrinking paramount blocs |
| `ROUTINE_FILL` (new) | 8 | 3 | A routine chronicle entry only fills a life with fewer than three significant ones; routine share 20.3 → 18.2% |
| great-realm inclination | 900/900 | 850/850 | Defect 4 above |

**Result on the development set** (144 starts, 48 sweeps; all fourteen checks pass):

| Check | Value (threshold) |
|---|---|
| Q1 class shares | patchwork 41.2%, rival powers 40.9%, paramount 11.6% (≥10), fractured 4.1% (≥3), great realm 2.3%; largest ≤ 50 |
| Q2 / Q3 | median 3 classes per world; recent-turmoil ratio Turbulent/Calm 2.19 (≥1.5), rising in 97.9% of worlds, continuity 87% |
| Q4 | prudent aims realized 74.2% of 178 (≥70); overreaching aims ended 56.4% of 202 (≥50); league 80%, confederation 80%, sacred centre 67% |
| Q5 / Q6 | all sixteen sweep rows monotone; great realms 0.79× 1.1.0's median, four of four high sweeps realize one |
| Q7 / Q8 | ordinary-size ratio 1.00 / 1.00 / 0.67 at Calm / Varied / Turbulent; no dominated continent or landmass |
| Q9 / Q10 | 33.5 subject pairs (8–40), 99.4% scaled; 12 alliances (4–30) |
| Q11 | republics 13.5%, interquartile spread 8.8 points, assortativity 0.254 (≥0.20) |
| Q12 / Q13 / S11 | largest family 25.8%, routine 18.2%, 3 distinct families in long chronicles, 23.6% short; 91% of countries visible; largest wrapper 580,654 bytes |

**Measurement caveat: Q4 depends on the recognition shares (checked 2026-11-05).**
The 48 Varied starts were rerun on the committed code and are bit-identical to the
matrix above. For each prudent regional-power and paramount aim, recognition by the
D24 rule used here was compared with Q1's own scale (a regional power holds at least
15% of its region; a paramount at least 40% and twice the next bloc):

| Prudent aims (48 Varied starts) | Recognized (R6 shares) | At Q1's scale |
|---|---|---|
| Regional power | 102 of 133 (77%) | 74 of 133 (56%) |
| Paramount | 11 of 25 (44%) | 8 of 25 (32%) |
| Both | 113 of 158 (72%) | 82 of 158 (52%) |

With the great-empire aims (10 of 10) the Q4 rate is 123 of 168 (73%) here, and
would be 92 of 168 (55%) at Q1's scale. Q4's pass therefore rests on the lowered
recognition shares (8% and twice the median state; 30%), which D24 explains but
which is a weaker picture than Q1's: a regional power of 7 locations in a region of 80
is twice an ordinary state, not yet a rival power. The map itself is measured by
Q1, whose classifier did not change. How seeding shapes it, from the same starts:

| Region seeded with | patchwork | rival powers | paramount |
|---|---:|---:|---:|
| nothing (patchwork) | 55% | 32% | 5% |
| regional powers | 22% | 62% | 10% |
| a paramount | 35% | 30% | 33% |

A seeded setting moves its region toward its picture, a paramount weakly. Before
the held-out run the owner kept Q4 on the recognized rate (plan D30, 2026-11-06);
the held-out report gives the Q1-scale rate beside it.

**Recheck after D31 (2026-11-06).** [V-EXEC] Historical opinions now take vanilla
analogues (plan D31); a different opinion set changes which events the chronicles keep.
The whole development matrix was rerun (`R6_OUT=dev-d31`): all fourteen checks pass,
Q1–Q13 with the same values, S11 584,589 bytes (was 580,654).

**Limits.** Several margins are thin: the prudent rate (±3 points of noise on this
set, more on 24 held-out worlds), `distinct` families (exactly 3), the Turbulent size
ratio (a median of two against three), and the paramount and fractured shares. The
turbulence sweep is a noisy single world per row; a lumpy union or separation of a
single realm (up to 46 locations) can reverse one row. Aim recognition is now looser
than the Q1 classifier on purpose (see the caveat above for its size). S8–S10, the reference's timing, the held-out freeze
and run are not done. The reference export for the changed code passes every writer
and output check: SHA-256 `40596d56ad63929bb14830a99d2d19a19c9edd9f14007a7e1d4003ebff6127d9`,
872 files. The development outputs are calibration evidence; they are not acceptance.
