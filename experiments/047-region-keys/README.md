# 047 - Region and area keys chosen by physical content (N5)

2026-10-24, generator **0.11.4**, algorithm epoch **28**, EU5 1.4.4 executable (Steam build 26142040) on 1.4.3 data. **OFFLINE CHECKS; NOT GAME VALIDATED.** Claims C262-C265. No game launch or separate owner sitting is requested.

[V-EXEC] The generator gives each of the 14 American land region keys and 135 land area keys to one generated part by a global minimum of climate, relief, coast and relative-size differences. The profiles come from the installed templates and the generated land; regions remain in their subcontinent and areas in their original region. All child areas must fit, so the reference no longer loses `moqoit_area`. The world report records each profile, cost and positional comparison.

[V-EXEC] The reference, continents seed 210 with extraordinary chance 1000, and archipelago seed 73 pass the exporter and independent manifest/hierarchy audit. They reduce total physical differences by 18.91%, 22.26% and 22.20%; retain all 21,728 Old World location records and every original land-key parent; and lose no Old World contact or pixel outside the canvas. Of N0's 68 positional consumers, 61 use the scored land keys, two use only sea areas and five use individual locations. The method and measured limitations are in the [design and audit](../../docs/research/n5-region-keys.md).

The epoch-28 reference is `RNW1-0826C-SYW6B-MW73Y-C005G-80813-G0Q8H-SZ`, with 814 mod files apart from metadata, digest `a05a8d4a8fe252f683613fdbc0951e022f18c2c4cefd353ea9ed91ea16ef0b46`. The installed candidate is **RNW: Small continents 6RF2**, `rnw_exp_world_6rf2nzt4dv`; all 816 installed files match the source. Nine profile-root files and 10,256 existing mod files retain their recorded hashes or sizes/times. See [INSTALLED](../INSTALLED.md).

[V-EXEC C265] Locked sync and `make check` pass (1,344 Python tests, 16 skips; 23 Rust tests; format, lint and types clean). Read-only local checks pass 14 tests with two opt-in skips; the separate `PYTHONHASHSEED=7 RNW_REPRODUCE=1` reference check passes (165.66 s). The two layer rerolls preserve every physical key record and every map/graphics file: resources change exactly one resources file, peoples change 62 files owned by that layer, with story and exceptional-place ownership preserved.

Evidence stays under ignored `local_data/n5/`. The remaining campaign and engine verdict is **NOT-RUN**. No push or publication.

## Removal

With the game closed, remove exactly this candidate:

```sh
uv run rnw uninstall-mod rnw_exp_world_6rf2nzt4dv --user-dir "<steam-library>/steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V"
```

The staged bundle stays under the project's local data. Existing worlds and playsets are preserved.
