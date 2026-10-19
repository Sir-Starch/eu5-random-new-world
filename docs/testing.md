# Validation protocol

This document describes offline checks and future in-game tests. No more EU5 launches will be performed in the current research session at the owner's request. The existing first-run Select Language issue is recorded in [experiment 001](../experiments/001-metadata/README.md).

## Current runnable checks

`uv sync --locked --group dev && make check` runs format, lint, static typing and synthetic unit tests [V-EXEC]. `EU5_GAME_DIR=/path/to/Europa\ Universalis\ V uv run pytest -q tests/test_local_install.py` enables a local-only parse check; it skips when the variable is absent and is excluded from CI by default [V-EXEC]. `uv run rnw inspect "$EU5_GAME_DIR"` and `uv run rnw coupling "$EU5_GAME_DIR" local_data/coupling.json` produce counts and a gitignored broad coupling inventory, not proof of in-game behavior [V-EXEC C05,C10]. `uv run rnw fingerprint "$EU5_GAME_DIR" local_data/map-contract.json` produces only stable file digests and sizes, so later beta builds can be compared before generating output [V-EXEC C20].

The D0 suite adds generator and exporter checks [V-EXEC C28–C31]:

- `tests/test_rng_noise.py`: SplitMix64 reference vectors, stream independence, NumPy/Python hash equality, noise window consistency.
- `tests/test_synth.py`: every seed/preset passes all validators; same seed is identical; presets differ measurably; seed-1 bundles match committed golden digests (the cross-platform gate once CI runs on Windows).
- `tests/test_validate.py`: negative fixtures for orphan sea, duplicate/reserved colour, duplicate/invalid key, broken parent, changed protected pixel, vanished or split cells, undeclared labels, frozen-pixel change, ineligible change and new contacts.
- `tests/test_coast.py`: topology preserved, displacement bounded by pass count, field sign controls direction, size floor/cap.
- `tests/test_eu5_export.py`: a synthetic EU5-shaped installation (`tests/fixtures_eu5.py`, no game data) exercises the adapter, the full export, repeatability, the fingerprint refusal and unsafe output paths.
- `tests/test_local_install.py` (local only): raster colours, unused declarations, river water mask and locator rows on the real installation (C23–C26).

`uv run rnw generate --game-dir "$EU5_GAME_DIR" --seed N --preset continents --output generated/rnw_exp_NAME` re-decodes the written PNGs and compares them with the installation before it finishes; its `report.json` lists every invariant. Not yet covered: port/dock placement quality beyond freezing, river path continuity beyond freezing, start-state references (no setup is rewritten) and anything in game. Synthetic fixtures belong in Git; game-derived rasters and logs do not.

## Determinism and completeness gate

For the same seed, settings schema, generator version and target game build, compare hashes of every emitted file on Linux and Windows; require byte identity [INFERRED]. Fix ordering, RNG algorithm/version, line endings, BOM handling, numerical rules, image encoding/compression and archive metadata. Change the schema or generator version intentionally when output changes. Test that all generated IDs resolve and every Old World reference remains valid. Linux status: the synthetic golden digests pass and a repeated EU5 export was byte-identical [V-EXEC C28,C31]. Windows byte identity of the synthetic outputs is a pending CI result; EU5 PNG bytes depend on the zlib build, so cross-platform comparison of EU5 outputs uses the recorded pixel digests.

## In-game test protocol when the owner next authorizes it

1. Record exact app build/branch and ensure the game is closed. Use an isolated `-userdir` profile; do not edit the normal playset or existing mods. Resolve the isolated profile's first-run input problem before attempting geography tests.
2. On that same build/profile, capture a complete vanilla baseline error/debug log and startup time, from process start to a stable main menu and, for gameplay tests, a loaded 1337 campaign. Do not compare incomplete logs.
3. Generate one `rnw_exp_*` mod into `generated/`, inspect its manifest and file hashes, then use `rnw install-mod` only into the isolated profile. Enable only that test mod in the isolated playset. Record the exact mod path in `experiments/INSTALLED.md`.
4. Start once per necessary experiment, capture complete logs, and run `uv run rnw logdiff baseline.log current.log`. Review all new messages manually; this text diff strips volatile timestamps but cannot determine error significance.
5. Capture game-window-only screenshots where relevant. For start-state changes verify owner/culture/pop in the 1337 view. For map edits verify visible boundary/class, selection, land and naval movement, exploration/colonization/conquest as appropriate, and save/reload. Measure startup time against the same-build baseline.
6. Mark `PASSED` only for the exact observed behavior, with version and evidence. A syntax check or version match alone cannot pass a geometry experiment. Record `FAILED`, `INCONCLUSIVE`, `PENDING-HUMAN-VALIDATION` or `NOT-RUN` honestly. Re-run critical tests after each beta patch [INFERRED C18].

`rnw prepare-mod generated/rnw_exp_001_metadata` and `rnw install-mod generated/rnw_exp_001_metadata USER_DIR` are the current metadata validation kit [V-EXEC]. They do **not** enable a launcher playset or run the game. A prepared, NOT GAME VALIDATED geography candidate exists locally for experiment 004 (`rnw generate`, C28); experiments 002–003 still come first. The temporary test folder can be removed as described in [INSTALLED](../experiments/INSTALLED.md).

`tests/test_terrain_model.py` covers the V1 models on synthetic data: exact bilinear upsampling, noise determinism, the Euclidean distance against brute force, label spreading, rain shadow, relief invariants, latitude anchors, k-nearest-neighbour votes and graph smoothing, coherence statistics, slot rules on a two-location island, slots limited to short biome material lists, biome rule resolution, level counting, instance sampling and inline instance rewriting [V-EXEC]. `tests/test_newworld.py` checks the seam strait and shore-aware city points on synthetic domains; `tests/test_rivers.py` checks drainage, the stream tree, the river raster rules, size classes and valley carving. With `EU5_GAME_DIR` set, `test_local_slot_rules_reproduce_vanilla_structure` rebuilds a vanilla decal crop from vanilla templates and requires at least 80% agreement on structural slot classes (85.6% measured, C51). Biome coherence, instance densities and biome material counts of a full build are in its `report.json` (`biomes.coherence`, `biomes.materials`, `terrain.objects`; C53, C57); `biomes.materials.default_biome_locations` must be 0.
