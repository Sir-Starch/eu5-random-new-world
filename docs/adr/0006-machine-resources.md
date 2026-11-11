# ADR 0006: The export reads the machine and bounds its memory

**Status:** Accepted 2026-10-21 (owner direction: the generator must not cause problems for any player, its kernels must adapt to the machine, and its memory must suit EU5's requirements rather than a calculator's).

## Context

EU5 asks for 16 GB of RAM at the minimum (Intel Core i7-8700K or Ryzen 5 3600, six cores) and recommends 32 GB (i7-14700K or Ryzen 7 7800X3D) [SOURCE: Steam store page of EU5, read 2026-10-21]. The player runs the generator before the game, on a machine that also holds a desktop, a browser and often the launcher. The first Rust export ([ADR 0005](0005-native-core.md), C101) peaked at 21.8 GB of resident memory with eight decal threads, because every decal window, water texture and sampling pass held whole-map eight-byte arrays, and the output files waited in memory until the bundle was written. On a 16 GB machine that is swapping, a stalled desktop or a killed process, and it would have been the application's first impression.

## Decision

1. **Target.** The continents preset (canvas 8192 x 10030 pixels, 733 files) peaks at 7.8 GiB of resident memory at the default thread count on a 32-thread machine (94 s), at 7.5 GiB with six threads, the minimum-spec CPU (96 s), and at 6.9 and 6.8 GiB with three threads and one, where the stages run one after the other and the thinnest bands (137 s and 192 s) (C102, C103); the process keeps about 3.3 GiB of rasters and tables and adds the transient set of the stage it is in. A machine with 16 GB runs it; a machine with 32 GB only runs it faster.
2. **Bounded working sets, identical output.** Every stage that was a whole-map array pass is a sequence of independent pieces whose size is a parameter and never changes a byte of the result:
   - decals are rebuilt in **bands** of location rows, each computed in a window that reaches `BAND_HALO` rows past it (the coast cap of the distance fields plus the interpolation and blur margins), so no row depends on where its neighbours begin;
   - water textures, vegetation sampling, relief, river valleys, climate grids, world statistics and the coast model run in **strips** with the halo of their own neighbourhood (zero for pointwise stages);
   - sums are exact integers in float64 added strip by strip, and thresholds are found by counting instead of partitioning a copy;
   - large output files (decal layers, vegetation instances) go to a **spool** directory beside the output as they are made and are moved into the bundle when it is written;
   - vanilla decal layers (30 ms each to decode) are read when needed and not kept; narrow types (`uint8`, `uint16`, `int32`) replace `int64` wherever the range is known, and 32-bit component numbers replace 64-bit ones.
3. **The allocator.** glibc gives every thread an arena that keeps what is freed in it; limiting it to two arenas (`mallopt`, set when the pool is sized) took the default peak from 8.4 to 6.9 GiB with the same output and speed. Other platforms need nothing.
4. **The machine is read at every run** (`rnw.parallel`): the threads the process may use (its affinity and a container's CPU quota; one thread stays free from four threads up so the desktop does not stall), the memory that is free now (`MemAvailable`, the container's cgroup headroom, or the Windows `GlobalMemoryStatusEx` figure), and a budget of 60% of it for bands and workers. The native thread pool is sized once from the same figures. `RNW_THREADS` and `RNW_MEMORY` (MiB) override them for benchmarks and tests. Where the system will not say how much memory is free, a conservative 4 GiB is assumed for sizing.
5. **Preflight.** The export first requires 8 GiB of free memory (7.5 GiB until 1.2.0, 9 GiB in 1.2.0 and 1.2.1; see the amendments below) and otherwise stops, before any work, saying how much it needs and how much is free; `--ignore-memory` starts anyway. Nothing falls back silently.
6. **Stages overlap when the machine allows.** The export is a graph of stages that start when their inputs exist (`parallel.Stages`); with four or more threads and 10 GiB free up to four run at once, otherwise they run one after the other in submission order, which is the old sequence. A stage may wait only for stages submitted before it, so waiting cannot deadlock. Overlap saves 30 s (C103): everything that reads only the vanilla game (reads, geometry, localization keys, the vanilla climate, the decals' material levels, the vanilla natives) runs beside the generation of the world, and the identities, the checks, the water textures and the biome model run beside each other after it. It costs about 1 GiB of peak.
7. **Proof.** Each banded or stripped function has a test that equals its whole-raster specification (kept in `tests/reference/`) for band heights from one row to the whole raster and for one thread and several, and a test that fails if the halo is smaller than the distance reach. A full export under `RNW_MEMORY=2500 RNW_THREADS=2`, `RNW_THREADS=6` and `RNW_MEMORY=3000 RNW_THREADS=3`, and with one thread, produces the same 733 file hashes as the default run, and those as the Python build of 0.9.13.

## Consequences

Memory and speed trade through two numbers the machine sets, so a slower, smaller machine gets the same world. The halo of a band is an engineering constant that must grow with the distance reach it covers: `BAND_HALO` is derived from `CAP_REACH`, and the test of the halo guards it. A new whole-map pass is a regression of this decision: it must be a strip, band or kernel with the same equality test.

The original peak-memory measurements above are Linux results. The later Windows
smoke (C428) and passing Linux/Windows CI (C439) establish their own scope, not a
cross-platform peak-memory comparison. Measure the affected workload when tuning
resource use; do not treat the absence of every platform measurement as a release hold.

## Amendment, 2026-11-09: the memory floor of 1.2.0

The 1.2.0 generator peaks higher than the 0.9.13 export this ADR measured (the cause was not isolated: the generator gained many stages since), so the figures of decisions 1 and 5 no longer hold. [V-EXEC: `main` at 65f8195 (1.2.0 and the Unreleased notes), continents preset, seed 42, installed EU5 1.4.7, Linux, 32 threads, peak resident memory of the process from `ru_maxrss` and a `/proc` sampler]

| Run | Peak | Time |
|---|---|---|
| default threads, plenty of memory | 9.81 GiB | 253 s |
| `RNW_THREADS=6` (the minimum-spec CPU) | 9.32 GiB | 253 s |
| `RNW_THREADS=6 RNW_MEMORY=8704` (8.5 GiB free) | 8.14 GiB | 370 s |
| `RNW_THREADS=1 RNW_MEMORY=1500` (the floor) | 8.08 GiB | 579 s |
| Omerika, `RNW_THREADS=6 RNW_MEMORY=9216` | 7.55 GiB | 293 s |

The floor is 8.1 GiB, 1.3 GiB above the 6.8 GiB of 0.9.13, and the old 7.5 GiB preflight lay below it: a machine with 8 GiB free was let through to a run that needed 8.1. The floor plus the 0.7 GiB margin decision 5 kept (6.8 to 7.5) is 8.8 GiB, rounded up to **9 GiB**: `EXPORT_MEMORY` is 9 GiB, and the player-facing text says "about 9 GB of free RAM". With more memory free the stages overlap and the peak rises to 9.3-9.8 GiB, which is why 16 GB machines are still told to close EU5 first. The adaptive sizing of decision 4 holds: with 8.5 GiB free and six threads the process stayed at 8.1 GiB. Nothing about the output changed. The measurement is of the continents preset and of Omerika; the export on the vanilla Americas (*Keep the real Americas*) reads the same limit and generates no land. The earlier figures above stay as the record of 0.9.13.

## Amendment, 2026-11-11: the floor isolated and lowered to 6.8 GiB

The amendment above left the rise of the floor "not isolated". Measured with a stage-by-stage `/proc` sampler, glibc's `mallinfo2` and a count of what the export function still holds when its last stage starts, three causes account for it. [V-EXEC: `main` at 465b1d6 before and ce013b9 after, continents seed 319218363 (C504) and seed 42, installed EU5 1.4.7, Linux, 32 threads]

1. **The check of the written map.** The last stage, "write files", decodes the `locations.png` it has just written and ran it through `pack_rgb`, whole-map `int64` temporaries of 1 GiB each (the canvas is 16384 x 8192), and then diffed it against the vanilla picture in a third whole-map pass. On the full canvas `labels_from_rgb` cost +2.06 GiB at once and +0.75 GiB in 256-row strips, with the same result; in the export, with the arenas trimmed first, the stage rose by 3.6 GiB. This was the 8.1 GiB floor, and `load_map` (2.5 GiB for a 0.4 GiB picture) used the same function. `labels_from_rgb` and a new `differing_pixels` now work in strips and `pack_rgb` packs into `int32`.
2. **Freed memory that glibc kept.** The stages' bands and strips lie below glibc's mmap threshold; freed, they stay in an arena. At the start of "write files" the live data was 3.8 GiB of a resident 6.2 GiB, 1.9 GiB of it free but held (`mallinfo2`: 0.22 in use, 1.90 held); `malloc_trim(0)` returned exactly that. A stage that ends now calls it (`parallel.release_free_memory`).
3. **References to dead arrays.** The settled coast, the carved relief and the vanilla climate (0.3, 0.3 and 0.4 GiB) stayed referenced until the export function returned; they are dropped when the stages end.

The map files are not the cause: file-backed memory is 0.06 GiB of the peak.

A world of seed 319218363 made before and after has the same 894 files byte for byte, at default threads and at `RNW_THREADS=3 RNW_MEMORY=1500` (the two `world.json` differ only in `created` and `seconds`).

| Run (seed 319218363) | before | after | time |
|---|---|---|---|
| default threads | 9.08 GiB | 8.94 GiB | 208 s, 203 s |
| `RNW_THREADS=3 RNW_MEMORY=1500` (the floor) | 8.17 GiB | 6.65 GiB | 341 s, 339 s |

| Run (seed 42, after) | Peak | Time |
|---|---|---|
| `RNW_THREADS=6 RNW_MEMORY=7680` (7.5 GiB free) | 7.16 GiB | 270 s |
| `RNW_THREADS=1 RNW_MEMORY=1500` (the floor) | 6.81 GiB | 357 s |

The floor is 6.8 GiB. Decision 5's margin of 0.7 GiB gives 7.5 GiB, rounded up to **8 GiB**: `EXPORT_MEMORY` is 8 GiB and the player-facing text says "about 8 GB of free RAM". The adaptive sizing of decision 4 holds: with 7.5 GiB free and six threads the process stayed at 7.2 GiB. The default peak fell little (9.1 to 8.9 GiB): the humps of overlapped stages remain, and the highest is now in the terrain stages (a resident 6.9 GiB before them, +2 GiB while they build), so a machine that overlaps stages (10 GiB free, `OVERLAP_MEMORY`) still holds under its free memory. What the export keeps at the end of its stages is still large (the old and the new label raster 0.5 GiB each, the coast 0.6 GiB, the location picture 0.4 GiB); lowering the floor further means releasing those earlier. Not measured again: Omerika, six threads with plenty of memory, and the Windows build.
