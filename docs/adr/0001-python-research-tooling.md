# ADR 0001: Python for the research and validation kit

**Status:** Accepted 2026-10-13 for research tooling only. The production raster/geometry implementation remains undecided.

## Context

[V-LOCAL C03,C07] EU5 1.4.1 uses a 16384×8192 location raster (134,217,728 pixels), a 8192×4096 16-bit heightmap and several graph/script files. A production exporter needs deterministic byte output across Windows and Linux, robust Paradox-script parsing and efficient pixel/graph operations. The current task needs small, inspectable experiments before that exporter exists.

## Decision

Use Python 3.12+, `uv` lockfile, Typer CLI, Ruff, basedpyright and pytest for the **research kit** [V-EXEC]. Keep the code small: `geography.py` parses one known hierarchy, while `cli.py` inspects an installation, generates a metadata-only mod, installs it into a designated user directory and compares logs. No production world model or geometry abstraction is invented.

## Alternatives and consequences

| Option | Trade-off |
|---|---|
| Python now | Fast to review and test, good ecosystem for PNG/graph tooling; naive full-raster Python loops would be too slow [INFERRED from C03]. |
| Rust now | Explicit types and fast raster pipeline, but higher startup cost before override feasibility is known [INFERRED]. |
| Python orchestration plus Rust/native core later | Viable if benchmarks show a real bottleneck; complicates packaging, so defer [INFERRED]. |

Future generator work must specify a versioned RNG, ordered iteration, canonical encodings/line endings, stable compression and byte-for-byte cross-platform golden tests before claiming reproducibility [UNKNOWN]. Do not rely on Python hash iteration, random global state, or platform-dependent floating-point output. The current CLI has no seed or generator, so determinism is a future requirement rather than an achieved claim.
