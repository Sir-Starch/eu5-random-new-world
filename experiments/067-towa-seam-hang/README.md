# Towa's immediately reproducible seam hang

## Question and evidence boundary

[V-GAME owner C366] The owner independently reproduced a hang immediately
after raising troops for **Towa**, whose territory occupies both sides of the
raster seam. This sharply narrows the recurring EVXP hang investigated in
[066](../066-1341-hang/README.md). Whether it happened while paused or after
unpausing is not yet confirmed by the owner. No new agent launch occurred.

[V-LOCAL / V-EXEC C366] Preserved 28 logs from the owner's 05:58 session,
playset information and console records in ignored
`local_data/towa-seam-20261026/`. The pause log switches off at **05:59:48**;
the final positive-position assertion has that timestamp. This is temporal
agreement, not a recovered task or a proven causal assertion. Read-only host
checks subsequently find no EU5 process to inspect.

The executable remains the pinned 1.4.4 Steam build **26142040**, SHA-256
`725a4c6ca50c0ef738f5ef0c00660637365ad01eebd462b39d61eac202714009`,
on the previously fingerprinted 1.4.3 map data. The installed world remains
**EVXP 0.13.2 / epoch 41**. Research does not alter the generator's 0.13.4
version, epoch or reference world.

## What the offline comparison establishes

[V-LOCAL / V-EXEC C367] Installed English localization identifies Towa as
**KVF**. Its start state owns 71 locations in 20 provinces; several provinces
themselves cross the raster seam. The old hot-task location pair from C365
belongs to two different provinces and is not Towa's initial pair, so splitting
only seam-spanning administrative provinces is not an established remedy.

[V-EXEC C367] The history separates two changes:

- `dbdb857`, **0.12.2 / epoch 32**, introduced continuous mainland wrap,
  seam land contacts and canonical-coordinate wrapped spline paths.
- `dc24d5d`, **0.12.6 / epoch 36**, extended primary terrain sources to remove
  the visual crack. Experiment 056's output comparison found terrain2 changes,
  with geography, countries and road paths preserved.

[INFERRED / UNKNOWN C367] The owner's temporal correlation is a useful lead.
Neither comparison isolates the visual-terrain change as the hang's cause;
the earlier unobserved engine behavior at land wrap remains relevant too.
Rolling back the visual fix is not a verified repair.

[V-LOCAL / V-EXEC C368] Both the installed world and vanilla retain
`wrap_x = yes`. The installed vanilla spline survey contains no road with a
raw step above 1,000 pixels or opposite-seam endpoints. The generator's
synthetic spline tests establish short cylindrical steps and correct anchors,
not how this engine consumes a wrapped land strip. No authoritative vanilla
encoding example was found. The scripted-adjacency parser recognizes `sea`
and `canal`; it does not establish an ordinary-land override.

[V-LOCAL / V-EXEC C368] Bounded inspection of the recovered path functions
shows that `Units.PathRefiner.EnablePathTightening` gates a later smoothing
stage, after the earlier search in the captured hot task. Disabling it is
therefore not justified as a way to bypass that search. The positive-position
assertion also occurs in the path-point append routine, but its logged
occurrence alone does not identify the malformed point or freeze trigger.

[UNKNOWN C368] The original unit route and the operation producing C365's
half-map intermediate coordinate are still missing. A spline jump, a
province crossing the seam and the assertion are not independently sufficient
to prove the root cause. No path rewrite, engine switch or candidate is
presented as a verified fix.

## Bounded capture prepared for the missing input

[V-EXEC C369] Private helpers verify the executable hash and 671,666 PE
function records before attachment. Offline replay against the existing
1346 stack agrees with all **17** previously recovered frame returns and
recovers the unit-state pointer. Compilation and prepare-only validation pass;
the new heap capture has not yet been exercised in a running game.

The proposed capture records general registers, selected hot-thread stacks,
XMM registers, the recovered unit record, its caller's route arrays and
bounded candidate arrays. The
array headers are explicitly untyped research leads, not a shipped decoder.
The debugger has a 20-second timeout; cleanup restores the prior execution
state and checks that no debugger or group stop remains. Its private memory
copies have per-thread limits. It neither starts EU5 nor writes game memory,
save files or mod data. See [interoperability R-006](../../docs/research/interoperability.md).

One immediate owner reproduction, leaving the hung process open, was requested
because the terminated process's omitted heap buffers cannot be recovered
from its logs or saved stack. No date waiting or campaign is requested.
This capture is pending; no successful live result or fix is claimed.

[V-EXEC C369] Locked dependency synchronization and the complete project check
pass: **1,999 Python tests, 14 skips, 23 Rust tests**, formatting, lint and
types. Documentation diff checks pass. These checks do not establish a runtime
hang remedy or exercise the pending heap capture.

## Installation and removal

No candidate, test mod, package or profile change. Nothing to remove.
