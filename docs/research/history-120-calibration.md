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
