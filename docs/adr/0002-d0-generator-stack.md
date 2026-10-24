# ADR 0002: D0 generator stack and ID-preserving first exporter

**Status:** Accepted 2026-10-14 for the D0 candidate. Revisit after experiments 002–005 or a measured performance problem.

## Context

The [implementation contract](https://github.com/Sir-Starch/eu5-random-new-world/blob/ea518eed2fa36d8659a467d42d3e4643a76051c2/docs/implementation-contract.md) asks for a seeded, deterministic geography change exported as an isolated `rnw_exp_*` mod for EU5 1.4.1, with offline proof and no game launch. The location raster has 134,217,728 pixels [V-LOCAL C03]. Map override behavior, new IDs and visual terrain requirements are unknown [UNKNOWN C13, C25].

## Decision

- **Language and arrays.** Python 3.12 with NumPy for raster work and Pillow only for decoding PNGs. A full export takes about 10 s and stays in memory comfortably on the research machine [V-EXEC C28]. A Rust core is not needed yet.
- **Determinism.** RNG v1 is SplitMix64 with SHA-256-derived named streams and counter-based lattice hashing [SOURCE/V-EXEC C33]. Noise, thresholds and settings are integers (fractions in permille), so no float formatting or platform math enters the output. Output changes require a new version; since [ADR 0003](0003-versioning.md) this is the one product version.
- **PNG writing.** Our own encoder uses the Up filter for every row. `stored` mode is fully specified and used for synthetic golden tests. EU5 outputs use zlib level 6; their bytes are reproducible for one zlib build, so manifests also record encoding-independent pixel digests and the zlib version. Colour, gamma and palette chunks are copied verbatim from the source PNG.
- **Model and exporter split.** `model`, `synth`, `coast`, `topology` and `validate` know nothing about EU5. `eu5_map` reads game files; `eu5_export` writes the package. The model supports new cells (T3); the first EU5 exporter preserves IDs (T2) and only moves land–sea pixels while keeping every cell contact.
- **Minimal override set.** The candidate emits `locations.png` and `rivers.png` only, because IDs, colours and class lists do not change and the river layer carries a water mask [V-EXEC C24]. Visual terrain is not edited because the American relief source is unknown [C25].
- **Type checking.** `basedpyright` stays in `all` mode. NumPy-heavy modules disable only `reportAny`, because NumPy stubs type array comparisons, shapes and `tolist()` as `Any`.

## Consequences

Contact preservation keeps ports, adjacencies and the cell graph valid, but it cannot create islands or straits [INFERRED C32]. A richer New World needs the T3 path after experiment 005. If the engine requires visual terrain or `nodes.dat` changes, the exporter gains new writers; the model and validators stay. Windows byte identity of the synthetic golden outputs is designed in but not yet observed, because CI has not run [C31].
