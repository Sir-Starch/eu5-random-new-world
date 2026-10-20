# ADR 0005: A Rust core for the hot kernels, Python for everything else

**Status:** Accepted 2026-10-20 (owner direction to return to performance and Rust; roadmap R10).

## Context

A full export takes about 12 minutes on one core [V-EXEC C92, C96 builds]. The player waits for it in the application ([ADR 0004](0004-generator-application.md)); EU4's random New World took seconds. [ADR 0002](0002-d0-generator-stack.md) chose NumPy while an export took about 10 s and said to revisit after a measured performance problem. The profile (C92) found that five kernels take about 70% of the time: the pure-Python LZAV decoder (203 s, 1.4 billion single-byte appends), value noise (191 s), step and Euclidean distance fields (123 s), upsampling (28 s) and instance sampling (70 s). All of them are integer arithmetic on rasters, which is what Rust does well and what must stay bit-identical.

## Options

1. **Keep Python, cache and parallelise.** Caching decoded vanilla decals per game build and running the ten decals in processes would cut a repeat build, not the first one, and process pools cost memory (each decal holds tens of megabytes).
2. **Rewrite the generator in Rust.** Fastest result, but a second implementation of 13,000 lines of reviewed logic without a reference, and every change of generator behaviour would need both.
3. **Hybrid: Rust kernels behind the Python generator.** The generator, validators, game readers and tests stay in Python; the measured hot kernels move to a Rust extension module with integer-exact results.

## Decision

Option 3.

- **Layout.** A Cargo crate `native/` builds the extension module `rnw._native` with PyO3 (stable ABI, one wheel per platform) and rayon for data parallelism; maturin is the build backend, so `uv sync` compiles it. Dependencies are pinned by `Cargo.lock` and limited to `pyo3`, `numpy` and `rayon` (MIT/Apache-2.0/BSD-2 licences, checked in [legal](../legal.md)). Release profile, no unsafe outside what PyO3 requires.
- **One implementation at run time.** Each Rust kernel replaces its Python function; the module keeps the function name and signature so callers do not change. A missing native module is an import error, never a silent fallback.
- **The old code becomes the oracle.** The NumPy or pure-Python implementations move to `tests/reference/` and stay as the specification: tests compare Rust and reference on random and edge-case inputs, including negative coordinates (floor division) and the limits of every integer type.
- **Determinism contract.** Integer arithmetic only. Floor division is `div_euclid` with a positive divisor, overflow that NumPy would wrap is wrapped explicitly, and the only floating point operation is the correctly rounded square root of an exact integer that [ADR 0002](0002-d0-generator-stack.md) already allows. Results do not depend on the number of threads: tasks write disjoint output and no reduction combines floats.
- **Acceptance of a kernel.** Equality with the reference on the tests; the golden digests unchanged; and a full export whose `manifest.json` file hashes equal those of the Python build of the same version and seed (reference: 0.9.13, continents seed 319218363, 733 files). The product version does not change when only speed does.
- **Order of work.** By share of the profile: LZAV decode, value noise, distance fields, upsampling and block sums, instance sampling and canvas selection; then caching of what is read from vanilla once per game build, then whatever the next profile still shows. Each step is measured without a profiler and recorded in the claims ledger.

## Consequences

Building the project needs a Rust toolchain (rustup, stable); the application's own build ships the wheel so a player installs nothing. CI gains `cargo fmt`, `cargo clippy` and `cargo test` on Linux and Windows. Kernel changes must be made twice (Rust and reference) and prove equal, which is the price of the speed. If a kernel stops being hot it can go back to NumPy by deleting the Rust function and keeping the reference.
