# Generation performance plan

**Status:** Implementation in progress, 2026-11-17. The owner requires substantially faster generation with
unchanged algorithm logic and quality, including rewriting hot paths in Rust where useful.
The first native kernels and exact calibration cache are implemented; the time targets remain open.
It follows [ADR 0005](adr/0005-native-core.md), [ADR 0006](adr/0006-machine-resources.md)
and the existing [verification rules](testing.md).

## Contract and targets

The same epoch, resolved settings, seed/rolls and installed inputs must produce the same
world bytes. Keep both cell-sizing passes, every growth/shore-feedback/relaxation round,
the rivers-first dependencies, climate votes and smoothing, relief detail, resolution,
location counts, validators and complete export. Preserve tie breaking, integer rounding,
RNG stream identities and draw order. Reducing any of these is outside this task.

The engineering targets on the machine that produced the reported run are:

* **At most 180 seconds** for a complete new world with an empty application cache.
* **At most 120 seconds** for a different new seed with only reusable installed-input
  calibration cached. The land and societies of that seed must actually be generated.
* No regression in peak memory or desktop responsiveness under comparable resource limits;
  retain the current supported memory floor. Cancellation must still be noticed within
  roughly one to two seconds during long kernels.

These are acceptance targets, not measured forecasts. The first detailed profile must assess
their feasibility and allocate the critical-path budget. A faster reroll of already cached
land does not satisfy either target. If the targets remain unmet, report the measured gap
and continue on the largest remaining costs; do not relax the equality contract.

## What is measured already

[V-EXEC] At source revision `8c9988e9c954a1b3e43b3c10bfaa7a3b3026cfeb`, the owner's
small-continents world `3xtvum6wfb`, seed `1145823653204280659`, epoch 64, installed build
26377361, completed generation and installation in **432.4 seconds**. The application used
a 31-thread budget and four overlapping stage slots. This is an observed application run,
not a controlled benchmark: cache hits, per-function CPU costs and peak memory were not
recorded. The log and the last matching application timing sample give:

| Stage | Measured seconds | Meaning |
|---|---:|---|
| Load map + select canvas | 27.5 | Sequential preparation |
| Generate world | 190.2 | Includes vanilla size calibration and geography |
| Land character | 37.2 | Biomes and wasteland planning, before coast construction |
| Biomes and rivers | 32.2 | Later export stage; not interchangeable with domain planning |
| Water textures | 61.3 | Overlaps other stages |
| Terrain decals | 75.4 | Overlaps the society/script branch |
| Natives | 36.9 | Includes historical final-start construction |
| Atlas | 20.5 | Follows natives |
| Vegetation instances | 20.4 | Follows terrain and water textures |
| Write files + install | 7.4 | Final sequential work |

Do not add these numbers: several stages overlap. Even making the whole 190.2-second
geography stage instantaneous would leave about **242 seconds** in this observed schedule.
Optimizing only the continents cannot meet the targets.

[V-EXEC] A separate diagnostic run with four threads and `cProfile`, reading the same installed
build, measured `_vanilla_sizes` at 21.6 seconds (23.9 including `load_map`). It identified
ground readings, block/cell statistics and roughness as sizeable costs. This is a profiled
isolated run, not an additive breakdown of the 432.4-second application run or an unprofiled
performance result.

The observed run's settings, world record, input manifest, output manifest and log were
snapshotted locally in `local_data/performance-20261117/`. Its 884 non-`.metadata` mod files
have the aggregate digest `da85e5c9b36734a15c8bc618085a1e6d58f112b4d237a41520931d74693241de`,
matching the world record. Game-derived evidence stays local.

## Implementation sequence

The order below is provisional after measurement: promote a later kernel when the profile
shows that it saves more end-to-end time. Commit each verified, coherent phase separately.

### 1. Establish a reproducible profile and preserve the oracle

Extend the opt-in diagnostics around `timing.py` and `parallel.py`, without changing world
files or normal generation work. Record start/end spans, call counts, dimensions, cache hits,
effective threads, CPU time, waiting and process peak memory. Distinguish inclusive and
exclusive spans and compute the actual critical path from timestamps and dependencies.
Profile worker threads and native kernels too: a main-thread profile can otherwise report
only time waiting on `Future.result()` and hide the work.

Split `generate world` into measurements for `_vanilla_sizes`, land/coast construction,
relief, drainage/basin shaping, climate, river rasterization, ground field, both spacing grids,
each seed scatter, every growth/correction round, merging and border wobble. Split land
character, water textures, terrain, natives/history and atlas similarly. Count full-raster
reads, temporary allocations and copies at Python/Rust boundaries in the hot paths.

Use the preserved world as an initial output oracle. Capture full-size intermediate inputs
for isolated kernel replay locally; use synthetic small fixtures in committed tests.
Record a controlled pre-change run before modifying the generator. Baseline the normal
application/service path as well as the CLI so bridge/UI overhead is visible. Include the
complete write, verification and installation path using an isolated temporary profile;
never benchmark by replacing the owner's existing world or changing their playset.

**Deliverable:** a ranked table of exclusive costs, memory/copy costs, critical-path effects
and candidate changes. Detailed profiling selects work; unprofiled wall-clock runs measure
its speed. Do not launch a large benchmark matrix while still choosing an implementation.

### 2. Remove computations whose results are discarded or repeated

There is already a concrete candidate in `eu5_biomes.py`: `coastal_offsets()` calls
`cell_readings()` and discards its first result. Producing that result calls `block_features`
and `_location_sums` over the raster. Separate the requested readings so the coast correction
computes its centres, ground votes, coastal flags and contacts without constructing unused
block-feature means. Keep the full readings for callers that use them.

Audit `newworld._river_cells`, `watersheds.river_cells`, `_land_character`, `_generated`
and `_biome_model` for repeated statistics. Reuse a result only while all its inputs are
identical. A grown label raster changes between correction rounds; its cell areas, contacts,
centres and votes must be recomputed. Likewise a moved island, modified height or changed
land/wasteland mask invalidates the corresponding measurements.

Share immutable preparation within a run where the data is actually identical. Do not assume
the size calibration's original vanilla map and the export's relocated map/`ShiftedStore`
have the same statistics. Measure their reusable subset explicitly.

**Acceptance:** identical intermediate arrays and full output; report eliminated passes,
allocation reduction and unprofiled end-to-end time. This phase also improves an empty-cache
run and does not depend on persistent caching.

### 3. Move the hot cell-construction loops to Rust

Use `native/` and the existing PyO3 extension. Preserve the current implementation as the
oracle in `tests/reference/` before replacing each kernel. Candidates, ranked by phase 1:

| Current code | Native implementation work | Exact behavior to preserve |
|---|---|---|
| `synth.grow_weighted`, `grow_regions`, `_claim` | Owned label/frontier buffers, reusable scratch space, bounded batches of rounds | Round eligibility, actual neighbour priority in the code, frontier ordering and competing claims |
| `watersheds._seed_candidates`, `_throw_seeds` | Candidate buffers and bucket lookup without Python objects | Hashes, lexicographic candidate order, distance test and seed numbering; greedy acceptance stays sequential |
| `watersheds.grade_spacing`, `_graded_grid` | Reuse relaxation buffers and fuse pointwise work within an iteration | Same convergence, land barriers, diagonal cost, binary-search choices, clamps and rounding |
| `_centre_pixels`, `_grown_areas`, `_shore_cells` and contact/statistics scans | Fused per-cell reductions; nearest-centre search without sorting every pixel where an exact reduction suffices | Empty-cell handling and the first raster pixel on equal distances |

Keep the number and meaning of all passes. A single native call can retain buffers across
rounds, but must expose bounded checkpoints for cancellation and release the GIL while
computing. Do not hold giant borrowed mutable NumPy arrays unsafely across callbacks.
Do not parallelize conflict resolution by racing writers. Parallel work must either be
independent or merge in the reference order.

### 4. Fuse the measured raster and classification hot paths

Reduce memory traffic as well as Python overhead. Likely candidates in `relief.py`,
`basins.py`, `eu5_biomes.py` and `watersheds.py` are:

* `_location_sums`, cell means/centres/ground scores, roughness and coastal contacts: accumulate
  integer statistics directly from bounded strips instead of materializing pixel-sized index,
  weight and gathered-feature arrays for each statistic.
* Relief arithmetic, `strip_bend`/`cell_roughness`, and basin spreading: use native strip kernels
  with the existing halo and the same sequence of rounding and updates. Fusing must not move
  an integer division across an addition or change a directional relaxation's update order.
* Classification: the exact k-d tree in `native/src/knn.rs` already exists. First measure tree
  rebuilding, standardization, queries and vote accumulation separately; reuse immutable
  trained structures or batch identical queries if those costs matter. Preserve each caller's
  existing tie behavior, including older NumPy-partition paths. Do not substitute approximate
  neighbours or globally switch all epochs to a different tie convention.

Only use narrower integers where proven ranges include all supported maps and settings.
Preserve signed floor division, overflow semantics and exact reductions; no floating-point
parallel reassociation. Verify halos on seams, strip ends, lakes and polar bands.

### 5. Cache immutable inputs and schedule work under one resource budget

Once input dependencies are explicit, keep exact reusable size/ground calibration and other
profitable installed-input tables, first within a process and then in a bounded local disk
cache. The key must include content fingerprints of every input read, directory inventories
where relevant, code/schema identity, applicable epoch/settings and any map transformations.
Steam build alone or modification times are insufficient. Persist validated data, not Python
pickle objects; write atomically, bound storage and preserve explicit corruption errors.
Prove cached and recomputed results equal and test invalidation after changed input contents.

This cache accelerates a **new seed**, not just rerolls. Measure its construction, load,
verification and disk costs. Improve first-run computation too; caching cannot replace the
180-second empty-cache target.

Review the real task graph in `eu5_nw_export.py` with `eta.DEPENDENCIES`. Start work earlier
only when its exact inputs are ready. The relocated-map reads currently depend on generated
island placement; keep that dependency. Preserve relief → drainage/rivers → cells and
wastelands → ports/straits. Update the ETA graph if the scheduling graph changes.

Coordinate Python stage/strip pools with rayon so nested work respects the total CPU and
memory budget. Benchmark thread counts and strip sizes; do not assume more threads are
faster. Reuse scratch buffers, avoid large boundary copies, and end buffer lifetimes as soon
as possible. Retain bounded memory on smaller machines.

### 6. Optimize the remaining export critical path

Reprofile after each substantial gain. The observed 75.4-second terrain branch and the
serial society → atlas → texts → scripts branch both matter; accelerating one can expose
the other as the new critical path. Water textures also compete for memory bandwidth.

`terrain` already has native height/slot/noise/packing kernels. Measure Python orchestration,
repeated mask/height construction, stamp work, compression, temporary copying and kernel
memory traffic before proposing another rewrite. For `eu5_water.py`, profile background
calibration, shelf synthesis and colour/foam rendering; port hot strips while preserving the
same textures and encoding. Inspect society/history and atlas CPU work separately from
waiting and serialization; port their measured loops without changing historical rounds,
decisions, stories or atlas contents. Keep every validator and write the complete world.

If boundary traffic and repeated setup still dominate, move a connected group of hot stages
behind one Rust-owned context. A larger Rust rewrite is acceptable, but its boundary is chosen
from the remaining profile and each migrated stage still compares against the existing
generator. Avoid a second, divergent generation model.

### 7. Verify the complete candidate and make progress reporting truthful

For every kernel, compare random, adversarial and boundary inputs to the reference: ties,
negative/sentinel values, non-contiguous arrays, isolated components, extreme spacing,
empty cases and integer limits. Test cancellation and error propagation. For threaded or
strip kernels, compare one and several threads, tiny and ordinary strips, and memory limits.

The full-world matrix includes the reported world, the current reference, all procedural
presets, a drawn land with marked relief/lakes, a seam-crossing world and a polar/density
extreme. Select a small fixed set that covers these cases, rather than a large seed sweep.
Compare the file set and every non-`.metadata` mod-file hash through `record.output_entries`
and `manifest_digest`. Compare deterministic atlas/preview data as well. Explicitly account
for timestamps, timings and build provenance outside world content; do not invent broad
exclusions for content that differs. Preserve the current and frozen older goldens unchanged.
An output difference is a regression to fix, not a new epoch or a reason to regenerate goldens.

Measure the principal case unprofiled at least three times before and after, sequentially
with matched settings, resource limits and background load. Report median and range, not
only the fastest run. Keep empty-application-cache and reusable-input-cache/new-seed cases
separate. Use fresh isolated data directories; do not clear the owner's caches or the OS page
cache. For a warm-input run, prime only the static input cache and ensure that the benchmark
seed has no cached geography; repeat the same benchmark seed across implementations.
Record the uncontrolled filesystem-cache limitation. Other matrix cases need a
timed parity run; repeat only noisy or problematic ones. Verify the supported native and
Windows packaged execution paths and resource behavior under the existing workflow.

Run `uv sync --locked --group dev && make check`, the relevant installed-game reference and
older-epoch checks, and desktop checks if its code changes. With equal world bytes, reuse
the existing installed candidate. Build/self-test and install the completed generator hub
with the authorized updater; record that installation in `experiments/INSTALLED.md`. Do not
launch EU5 or request an owner game sitting to establish an offline performance improvement.

Separately expose the existing relief/land-cell substage activity in both windows and
recalibrate progress weights and ETA from the new measurements. New visible strings, if
needed, must follow the localization workflow. Progress reporting is useful, but contributes
zero to the measured speedup and cannot satisfy the performance targets.

## Completion evidence

[V-EXEC 2026-11-17] The first implementation adds optional `RNW_TRACE=/path/trace.jsonl`
spans (including strip workers, nested wall/thread-CPU time and process peak memory),
ports frontier growth, spacing relaxation, greedy seed acceptance, small-cell merging,
centre selection, label/block statistics, bend and water colour work to Rust, removes
the coast correction's discarded block means, and caches the original map's size model.
The cache verifies content hashes and directory inventories and replays its dependencies
into the world's input record. Both windows now show the existing geography substages.

Three fresh-library baseline service runs, including verification, writing and installation
into isolated profiles, took **342.2, 332.8 and 335.4 seconds** (median 335.4; peak RSS
8.82–9.55 GiB). All reproduce the reported world's 884 files and digest above. The first
post-change diagnostic export also reproduces all 884 files and the same input digest;
it took **299.9 seconds**, peak 9.34 GiB. It overlapped development checks and is **not**
the final matched performance comparison. Its water stage took 8.8 seconds and geography
105.9 seconds. The 180/120-second targets are **not yet met**. Continue from the remaining
profile rather than treating this first gain as completion. The locked full checks pass
(3,393 Python tests, 22 optional skips; 31 Rust tests). Local raw evidence stays under
`local_data/performance-20261117/`.

[V-EXEC 2026-11-17] The next implementation also fuses land-height blurs, block relief,
mountain blending and material stamping; removes whole-raster component sorting and unused
roughness readings; batches exact geographic remaps; and reuses history queries only within
their immutable state snapshot. Terrain bands omit columns outside their active core, retain
all original halos, and evaluate land noise only where its value is consumed. The ground survey
computes the odd height samples directly instead of discarding three quarters of them. The
written decals still use the complete height field. Shifted island layers prepare their source
coordinates once, and inline vegetation numbers and localization hashes use exact native
conversions. Original implementations and adversarial equality cases remain in the tests.

An intermediate fresh-library export with eight threads took **262.5 seconds**, peak
**7.84 GiB**, reproducing the same 884 files and input digest. Its geography stage took 90.0 s,
including relief 19.8 s and land cells 40.5 s; the later terrain branch took 84.1 s (decals 53.5 s,
vegetation 28.4 s). Several of these spans overlap or wait for dependencies: they are not
additive exclusive CPU costs. This is a diagnostic comparison with a different thread limit,
not the final matched benchmark. The latest kernels still need a clean complete-world time
comparison and the installed-game current/frozen-epoch checks. Full locked checks pass after
this phase (3,450 Python tests, 22 optional skips; 31 Rust tests). No goldens have changed.

The latest complete candidate export took **301.4 s**, peak **8.55 GiB**, at eight threads,
again reproducing every output and input hash. Its terrain branch was 78.2 s, including
22.8 s for vegetation, but geography was 107.6 s and canvas selection 13.7 s. The difference
from the preceding 262.5-second diagnostic is unresolved host/run variability; do not select
the fastest observation as the after result. A matched repeated comparison remains required.
The additional mid-kernel cancellation test raises from the second native growth checkpoint
and preserves the caller's seed raster.

The bar also credits completed relief/sea-cell/land-cell subpasses against their parent's
weight, without counting them twice or inventing progress while a pass is running. This is
separate from generation speed. The **180/120-second targets remain open**.

The final result must include a before/after table of complete-world time, critical-path
stage time, peak memory, cache mode and output digest; the unchanged golden/reference
results; the coherent implementation commits and the installed hub self-test result.
Update this document with the measured results rather than duplicating the narrative across
the roadmap, ledger and experiment notes. Planning alone requires document/link checks,
not a generator rebuild, new reference world or hub installation.
