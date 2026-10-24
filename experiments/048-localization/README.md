# 048 - The world's mod in every official language (L1)

2026-10-24, generator **0.11.5**, algorithm epoch **29**, EU5 1.4.4 executable (Steam build 26142040) on 1.4.3 data. **OFFLINE CHECKS; NOT GAME VALIDATED.** Claims C268-C274. No game launch or separate owner sitting is requested; what only the game can show is listed below and waits for the next sitting the owner holds anyway.

[V-EXEC C274] The world's mod writes its stories, formables and exceptional places in all eleven official languages from catalogs with source fingerprints, and every composed name per language: water and its parts, highlands, lakes, country adjectives, formables, colonial names, with generated proper names in Cyrillic, katakana, hangul and Chinese characters for those four languages ([localization](../../docs/localization.md)).

The epoch-29 reference is `RNW1-0826C-SYW6B-MW73Y-C005G-A0813-G0PJF-6F`: 814 mod files apart from metadata, digest `52e9668a5dab464dd910a03f97e07ae5f6f2e197da7204e9681d5c7415b8743d`. `make check` passes (1,369 Python tests, 14 skips; 23 Rust tests; format, lint and types clean); the local suite with `RNW_REPRODUCE=1` remakes the reference byte for byte (13 passed, the opt-in layer test skipped, 198 s).

The installed candidate is **RNW: Small continents 2O74**, `rnw_exp_world_2o74n3gmdn` (made by `rnw world RNW1-0826C-SYW6B-MW73Y-C005G-A0813-G0PJF-6F --install`). All 814 mod files are byte-identical to the reference export under `local_data/l1/reference/`. The nine profile-root files keep their hashes, and none of the 9,420 existing mod files changed size or time. See [INSTALLED](../INSTALLED.md).

## What only the game shows [UNKNOWN]

When the owner next plays in another language anyway (the game's language is Steam's per-game setting), the logs and a glance settle these; none blocks work:

- the map labels of long Russian and German names (*Западная часть моря Саумкейр*);
- that the Japanese, Korean and Chinese fonts draw every character written (they are the characters the game's own transliterations use);
- the event windows of the stories in a language other than English.

## Removal

With the game closed, remove exactly this candidate:

```sh
uv run rnw uninstall-mod rnw_exp_world_2o74n3gmdn --user-dir "<steam-library>/steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V"
```

The staged bundle stays under the project's local data. Existing worlds and playsets are preserved.
