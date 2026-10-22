# 025: EU5 1.4.3 patch regression

Date: 2026-10-22. **OFFLINE PASS; NOT GAME VALIDATED.** No EU5 launch, installation,
playset change or change to an existing world. The owner approved the full generation.

## Installed build and input changes

[V-LOCAL C148] Steam app 3450310 is installed on `1.4-open-beta`, build **26105915**,
updated at 16:24:02 CEST. The manifest has `StateFlags=4` and equal installed/target build
ids. The owner identifies this patch as 1.4.3; no running-version observation is claimed.

[V-EXEC C148] Compared with the 1.4.2 map contract, only `location_templates.txt` changed
(3,754,030 to 3,754,033 bytes). The aggregate SHA-256 is
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
The other nine files, including the location raster and hierarchy, are byte-identical.
The new fingerprint was absent from the generator's known builds before this check.

[V-EXEC C148] Comparison with C144's recorded inputs (13,870 files and 3,750 directories)
finds **977 changed files**, seven changed directory listings and one missing directory
(`game/in_game/setup/religious_orders/`); no recorded input file is missing.
Of the changed files, **16** are overridden by the previous reference mod: location templates,
the context menu, two 1337 setup files, achievements, three static-modifier files, four DHE
event files, the hardcoded on-actions, the western-ocean expedition, situation effects and
the Treaty of Tordesillas situation. [INFERRED] Keeping that old mod enabled can undo those
patch changes; regenerate worlds against 1.4.3.

## Full export

[V-EXEC C149] Generator **0.9.25** makes reference code
`RNW1-0426C-SYW6B-MW73Y-C004H-0037F-87G` through the real application CLI in **92.4 s**:

```sh
uv run rnw world RNW1-0426C-SYW6B-MW73Y-C004H-0037F-87G \
  --game-dir '<steam-library>/steamapps/common/Europa Universalis V' \
  --data-dir local_data/patch-1.4.3/application
```

The retained bundle is
`local_data/patch-1.4.3/application/generated/rnw_exp_world_yx2z7qw242/`.
`installed` and `copied_to` are null; no normal-profile removal applies. The bundle is
ignored local game-derived data. Its exact folder can be removed later when no longer needed.

The export passes every invariant: pixels outside the canvas identical, zero lost Old World
contacts, zero split generated cells, zero unreachable generated sea zones and zero land
cells without port access. It makes 451 native countries. Its record lists **13,873 input
files**, **3,750 directory listings** and **739 non-metadata mod files** with digest
`533979a9b7bc00dddd431423dd587845036bb8b7bbf30a4a9cc98676bd96dc38`.
Rehashing every output file from disk matches both the manifest and aggregate digest.

Compared with C144's 1.4.2 world, 15 non-metadata mod files change; none are added or removed.
No raster or terrain file changes. All changed files are
among the overridden patch inputs above; `flavor_CHK.txt`'s patch difference does not survive
the exporter rewrite. A patch input change can change output without changing the algorithm.
Epoch **1** therefore remains: the only generator change registers the build; release metadata
moves to 0.9.25. `tests/golden_world.json` now records the current build's reference; C144
retains the 1.4.2 reference digest.

## Validation boundary

[V-EXEC] All **eight** installation tests pass with `RNW_REPRODUCE=1` in **113.27 s**:
an independent full export matches the new reference digest. Reproduce with:

```sh
RNW_REPRODUCE=1 \
EU5_GAME_DIR='<steam-library>/steamapps/common/Europa Universalis V' \
  uv run pytest -q tests/test_local_install.py
```

Formatting, lint, strict types, 811 Python tests (8 optional skips) and 23 Rust tests pass
through `uv sync --locked --group dev --offline && make check`. The type checker
cannot inspect Python inside the agent sandbox; the same check succeeds outside it, with
no source/configuration workaround.

[UNKNOWN] Loading, shader compilation, country selection, game start and playability on
1.4.3 require an owner-authorized game test. This offline pass establishes none of them.
