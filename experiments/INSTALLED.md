# Installed experiments

Before 2026-10-14 no test mod was installed in the owner's normal EU5 user mod directory. Only new folders starting with `rnw_exp_` may be installed there, and each must be recorded here before use.

| Folder | Location | Purpose | Removal |
|---|---|---|---|
| `rnw_exp_001_metadata` | `/tmp/rnw_eu5_validation/mod/` (isolated temporary profile) | Metadata recognition, EU5 1.4.1 | With the game closed, delete only that exact folder and its temporary profile if desired. It is outside the normal user directory. |
| `rnw_exp_d0_coast_s42` | Normal profile: `steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V/mod/` | Experiment 004: D0 land–sea boundary candidate, NOT GAME VALIDATED. Installed 2026-10-14 12:35 by the owner with `uv run rnw install-mod generated/rnw_exp_d0_coast_s42/rnw_exp_d0_coast_s42 USER_DIR` (the agent may not write to the game profile); the installed tree was verified byte-identical to the manifest (`locations.png` `50c09a67…`, `rivers.png` `2e00a25c…`). Enable it only in a new separate playset. Baseline logs: `local_data/baseline/2026-10-14-normal-no-rnw/` | With the game closed, disable it in that playset (or delete the playset), then delete only `mod/rnw_exp_d0_coast_s42`. The `mod/` folder did not exist before; remove it too if empty. |

D0 candidates from `rnw generate` are staged in the gitignored project `generated/` folder; only the one listed above is installed. Removing one means deleting that exact folder.

The normal playset's existing Workshop mods were not intentionally modified. On 2026-10-14 the owner resumed in-game testing for experiment 004; the agent does not launch the game itself.
