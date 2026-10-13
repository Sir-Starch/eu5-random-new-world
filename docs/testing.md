# Validation protocol

This document describes future tests. No more EU5 launches will be performed in the current research session at the owner's request. The existing first-run Select Language issue is recorded in [experiment 001](../experiments/001-metadata/README.md).

## Current runnable checks

`uv sync --locked --group dev && make check` runs format, lint, static typing and synthetic unit tests [V-EXEC]. `EU5_GAME_DIR=/path/to/Europa\ Universalis\ V uv run pytest -q tests/test_local_install.py` enables a local-only parse check; it skips when the variable is absent and is excluded from CI by default [V-EXEC]. `uv run rnw inspect "$EU5_GAME_DIR"` and `uv run rnw coupling "$EU5_GAME_DIR" local_data/coupling.json` produce counts and a gitignored broad coupling inventory, not proof of in-game behavior [V-EXEC C05,C10].

The present parser validates duplicate location keys and parsed named colors, but it is not a complete geography validator. Future tests must cover each key/color mapping, one parent per level, no overlapping pixel colors, raster dimensions, sea/land classification, adjacency symmetry, graph reachability, port/coast consistency, river paths, Old World pixel/hash invariants and valid start-state references [INFERRED C03–C10]. Synthetic fixtures belong in Git; game-derived rasters and logs do not.

## Determinism and completeness gate

For the same seed, settings schema, generator version and target game build, compare hashes of every emitted file on Linux and Windows; require byte identity [INFERRED]. Fix ordering, RNG algorithm/version, line endings, BOM handling, numerical rules, image encoding/compression and archive metadata. Change the schema or generator version intentionally when output changes. Test that all generated IDs resolve and every Old World reference remains valid. These are future gates, not current achievements [UNKNOWN].

## In-game test protocol when the owner next authorizes it

1. Record exact app build/branch and ensure the game is closed. Use an isolated `-userdir` profile; do not edit the normal playset or existing mods. Resolve the isolated profile's first-run input problem before attempting geography tests.
2. On that same build/profile, capture a complete vanilla baseline error/debug log and startup time, from process start to a stable main menu and, for gameplay tests, a loaded 1337 campaign. Do not compare incomplete logs.
3. Generate one `rnw_exp_*` mod into `generated/`, inspect its manifest and file hashes, then use `rnw install-mod` only into the isolated profile. Enable only that test mod in the isolated playset. Record the exact mod path in `experiments/INSTALLED.md`.
4. Start once per necessary experiment, capture complete logs, and run `uv run rnw logdiff baseline.log current.log`. Review all new messages manually; this text diff strips volatile timestamps but cannot determine error significance.
5. Capture game-window-only screenshots where relevant. For start-state changes verify owner/culture/pop in the 1337 view. For map edits verify visible boundary/class, selection, land and naval movement, exploration/colonization/conquest as appropriate, and save/reload. Measure startup time against the same-build baseline.
6. Mark `PASSED` only for the exact observed behavior, with version and evidence. A syntax check or version match alone cannot pass a geometry experiment. Record `FAILED`, `INCONCLUSIVE`, `PENDING-HUMAN-VALIDATION` or `NOT-RUN` honestly. Re-run critical tests after each beta patch [INFERRED C18].

`rnw prepare-mod generated/rnw_exp_001_metadata` and `rnw install-mod generated/rnw_exp_001_metadata USER_DIR` are the current metadata validation kit [V-EXEC]. They do **not** enable a launcher playset or run the game. There is no prepared geography mod yet; experiments 002–006 specify how to build one after the preceding gate. The temporary test folder can be removed as described in [INSTALLED](../experiments/INSTALLED.md).
