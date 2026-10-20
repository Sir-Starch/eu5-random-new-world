# Installed experiments

Before 2026-10-14 no test mod was installed in the owner's normal EU5 user mod directory. Only new folders starting with `rnw_exp_` may be installed there, and each must be recorded here before use.

| Folder | Location | Purpose | Removal |
|---|---|---|---|
| `rnw_exp_001_metadata` | `/tmp/rnw_eu5_validation/mod/` (isolated temporary profile) | Metadata recognition, EU5 1.4.1 | With the game closed, delete only that exact folder and its temporary profile if desired. It is outside the normal user directory. |
| `rnw_exp_new_world` | Normal profile `mod/` | The single current RNW test mod. Every new build replaces it in place with `uv run rnw install-mod --replace generated/rnw_exp_new_world/rnw_exp_new_world USER_DIR` (installed 2026-10-15 at the owner's explicit request; tree verified byte-identical). Installed content (2026-10-20, installed by the owner, verified identical, 713 files, 1.3 GB): version 0.9.5, continents seed 34378487 (commit 01a755d; experiment 013), built from 1.4.1 files while the game is now 1.4.2 (C84), NOT GAME VALIDATED. Staged for the next install: 0.9.6, the same seed built for 1.4.2 (C87). Earlier contents: 0.9.4 seed 3717486232 (commit 8c76487; experiment 012); builds 0.8.0–0.9.3 for experiments 010–012; 02fe1ea V1b.1 seed-driven coastlines on seed 3706823338 (C65, experiment 009); 7c86a24 V1b rivers seed 3903742112 (C62; rivers accepted in game, C64); 123a907 V1a.1 seed 42 (C57; accepted in game, C58); 10e931f V1a terrain and biomes (C53; loaded in game, C55); eba14e0 coasts, materials, water and lakes (C46); v2 (034a58a) loaded in game (C45). Baseline logs: `local_data/baseline/2026-10-14-normal-no-rnw/`. | Game closed: disable it in the playset, then `uv run rnw uninstall-mod rnw_exp_new_world --user-dir USER_DIR`. |
| `rnw_exp_d0_coast_s42`, `rnw_exp_nw_continents_s42` | — | **Removed 2026-10-15** with `rnw uninstall-mod` at the owner's request (D0 coast test; first T3 build that crashed, C43). | Done; their playset entries can be dropped in the launcher. |

Policy (owner, 2026-10-15): keep one installed RNW mod, `rnw_exp_new_world`, replaced in place by each build; staged bundles in `generated/` are replaced with `--replace` instead of accumulating.

The normal playset's existing Workshop mods were not intentionally modified. On 2026-10-14 the owner resumed in-game testing for experiment 004; the agent does not launch the game itself.
