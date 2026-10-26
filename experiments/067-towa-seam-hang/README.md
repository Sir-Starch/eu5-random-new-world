# Towa's immediately reproducible seam hang

## Question and evidence boundary

[V-GAME owner C366] The owner independently reproduced a hang immediately
after raising troops for **Towa**, whose territory occupies both sides of the
raster seam. This sharply narrows the recurring EVXP hang investigated in
[066](../066-1341-hang/README.md). The owner subsequently confirmed that the
freeze begins **after unpausing**, and agreed to one immediate repeat (C370).
No new agent launch occurred.

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
At this preparation stage capture was pending. The completed capture and its
findings follow below; preparation alone did not establish a remedy.

[V-EXEC C369] Locked dependency synchronization and the complete project check
pass: **1,999 Python tests, 14 skips, 23 Rust tests**, formatting, lint and
types. Documentation diff checks pass. These checks do not establish a runtime
hang remedy or exercise the pending heap capture.

## Owner repetition and completed capture

[V-GAME owner / V-LOCAL / V-EXEC C370] On the owner's **"ready"** message,
captured PID **3893335** at **14:41:38 +01:00**, without starting the game.
The pinned executable hash passed. The process has **95 threads**; hot
`Task_BN 10` is in **70793b0**, called by **707b6e0**, the same refinement
family as 066. Preserved the caller's **144 path points**, matching location
and flag arrays, the unit record and small candidate arrays. A separate
snapshot preserves **27 logs** from the 14:39 session. The final positive
position assertion is at **14:41:16**. The debugger detached and cleanup
verified **R (running), TracerPid 0**; this is not a recovery of the hung game.

[V-EXEC C370] A later attempt to collect the adjacency objects found no EU5
process and did not attach. The agent did not terminate or launch the game.
The main route capture is already preserved; the added adjacency-object
collector therefore remains untested. No new owner sitting is required for
the conclusion below. Private files have a hash manifest.

## Identified horizontal-wrap arithmetic defect

[V-LOCAL / V-EXEC C371] The captured path-manager fields are **width 16,384**
at offset **+0x08**, **height 8,192** at **+0x0c**, horizontal wrap enabled and
vertical wrap disabled. The executable's subdivision branch at RVA
**707f3b3** loads **+0x0c** when choosing the horizontal periodic displacement.
The same branch's later horizontal normalization at **707f437** loads **+0x08**.
The factor loaded for division is independently checked as **0.5**. This
mixes the vertical period into horizontal midpoint construction.

[V-EXEC C371] Replaying those float32 operations on the captured anchor and
adjacency control point produces midpoint **(12253.25, 6115.75)**. Using the
horizontal period instead produces **(16349.25, 6115.75)**, close to the seam.
The wrong first midpoint and **four subsequent bisections** all match points
in the live route **bit for bit**, including the current refinement endpoint.
Synthetic positive-coordinate examples in both crossing directions reproduce
the same error, while an ordinary noncrossing example agrees. Negative input
alone is therefore not necessary for this dimensional mistake.

[V-LOCAL / V-EXEC C372] The unit's stored location route starts in
**rnw_loc_01306**, then visits **rnw_loc_01329**, **rnw_loc_05117**,
**rnw_loc_01342** and **rnw_loc_01383**. The middle pair crosses the seam;
written anchors are on their respective sides. A bounded raster-crop read
confirms that the two identities already lie on separate planar sides, so
an additional location split is not the missing feature. The runtime path
has a negative boundary control point and then progressively visits
unrelated Old World IDs as its intermediate coordinates move across the map.
This is not the installed short wrapped spline's point list. Its canonical
points are all nonnegative; the recovered land-unit branch appends adjacency
control points directly. Rewriting that spline is not an established remedy.

[INFERRED from C370–C372] The generated mainland's seam crossing exposes an
engine-side horizontal midpoint defect, which sends the graphical route
refiner into unrelated parts of the map. This accounts concretely for the
captured Towa task. It establishes more than a merely stale framebuffer or
a coincidence with taking a screenshot. Neither a formal infinite loop nor
the exact operation of the first 1341 episode is proven. A clean-vanilla
crossing experiment and a corrected-engine runtime comparison were not run.

## Repair boundary

[V-EXEC / UNKNOWN C373] The offending instructions belong to the installed
game executable, not generated terrain or spline files. C367 separates the
terrain-crack fix from the earlier introduction of mainland wrap; no evidence
isolates that visual fix as causal. No verified data-only remedy preserving
the requested continuous mainland is available yet. No engine switch is
claimed to repair the arithmetic. The correct-period replay is diagnostic
evidence, not a tested binary patch or a playable fix.

No executable, memory, installed world or save is patched. No channel,
impassable seam, scripted replacement crossing, removed route or disabled
unit rendering is shipped. Product version **0.13.4 / epoch 41** and golden
world remain unchanged. The owner was informed that the immediate cause is
identified but a safe mod-level repair is not ready.

[V-EXEC C373] Post-capture locked sync/full check again passes **1,999 Python
tests, 14 skips and 23 Rust tests**, with formatting, lint, types and diff
checks clean. The private arithmetic replay passes independently. These
checks verify the recorded diagnosis and unchanged generator, not a game fix.

## Installation and removal

**Subsequent correction:** [068](../068-continuous-location-identities/README.md)
compares the working vanilla representation and finds the generator's forced
seam split. The claim that already-split cells excluded a generator-level
repair was incorrect: vanilla continues the same identity across the cut.
The midpoint trace remains evidence of the observed failure branch, not proof
that valid wrapped geography requires an engine patch. Version 0.13.5 fixes
identity construction and installs a separate candidate; post-fix runtime
acceptance remains unobserved.

No candidate, package or profile change occurred in 067. The subsequent
candidate installation and removal belong to 068.
