# 046 - Fixes from sitting 045 and the seed-210 regression

2026-10-24, generator **0.11.3**, algorithm epoch **27**. **OFFLINE CHECKS; NOT GAME VALIDATED.** Claims C257-C261. No game launch or separate owner sitting is requested.

## Changes

- [V-EXEC C257] Continents seed 210 failed in `plan_identities`: `atlantic_north_equatorial_area` had no generated provinces after the sea partition gave all its generated zones to the coastal regions. Its vanilla remainder still exists. The sea planner now emits this area only when it has generated cells; the vanilla remainder stays in the hierarchy. The hierarchy validator also rejects any empty generated area or province with `IdentityError`. The regression is covered on the actual seed and on an eight-cell synthetic graph with two ocean anchors.
- [V-LOCAL / V-EXEC C258] The lobby passes a potentially absent country as a saved `rnw_country` scope, with no typed country root. Its scripted GUI checks that the capital exists and enters it with the optional `?=` scope operator. The selected-country panel, every start/join control, country cards and the context menu use the same scope convention. The installed `scripted_guis.info` describes saved scopes; `economy_lateralview.gui` uses `GuiScope.AddScope` without a root. [UNKNOWN] Whether this eliminates the 214 engine errors of C254; offline structure checks do not establish that.
- [V-EXEC C259] Generated area and region names replace values in local copies of the installed `area_l_LANGUAGE.yml`, `region_names_l_LANGUAGE.yml` and `location_names/location_names_l_LANGUAGE.yml`, at their original mod paths. No extra `replace/` file defines the reused keys. Every other byte of those files, including the Old World's text, BOM and line endings, stays intact. A missing or multiply defined requested key stops generation. The export's localization check accepts a same-path override only if it keeps exactly the installed key set; generated keys must still avoid every vanilla hash, including under a `replace/` path. [UNKNOWN] The engine's final choice of the generated display names in this release.
- [V-EXEC C260] A full test run exposed a completion race in the window: `FINISHED` could become visible while the new world was still absent from the library. The worker now refreshes the library before publishing its terminal state and selected result. A deterministic regression holds the refresh behind a thread barrier and checks both sides of completion.

## Evidence and limits

Synthetic fixtures contain no game resources. Game-derived reproduction inputs, build records and logs stay under gitignored `local_data/sitting-fixes/`. Full-world build and installation details are recorded in [INSTALLED](../INSTALLED.md) and the [research log](../../docs/research/log.md).

[V-EXEC C261] `make check` passes: 1,326 Python tests and 23 Rust tests, format, lint and typing checks; the read-only local suite passes 14 tests (the two slow opt-in checks skip in that run). The reference world has 814 mod files excluding metadata, digest `abc021ed0a1a9211efdd72b2696832601273a1c839db5cefa8d4a343ddf2b4c7`. A separate reference test with `PYTHONHASHSEED=7 RNW_REPRODUCE=1` reproduces that digest (136.52 s). The complete seed-210 world has 813, digest `650d92e74ea63ec7b08f823e6e05aa1f9f77c0f16dd792f614e0fcc44dcb2945`; all file hashes of both bundles were independently checked against their manifests. Their 33 same-path localization files retain all original key counts and every byte outside the American name values. Installation added **RNW: Continents BDI5**, `rnw_exp_world_bdi5rrmfyp`, with all 815 files identical to the candidate. The nine profile-root files retain their hashes and the 9,441 existing mod files retain their sizes and modification times.

The map-mode errors of C255 remain unattributed: the installed `nobles_percentage` and `burghers_percentage` colour scripts compare ownership with `scope:actor`, which the observed session lacked. This change makes no claim about their cause or their runtime behaviour.

## Removal

With the game closed, uninstall only the candidate folder named in [INSTALLED](../INSTALLED.md): `uv run rnw uninstall-mod FOLDER --user-dir USER_DIR`. Existing worlds and playsets are preserved.
