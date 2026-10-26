# Installed experiments

2026-10-27, **0.13.9 / epoch 46 Balanced baseline and contextual AI**, C396–C397:
installed **RNW: Supercontinent LQCS** into new `mod/rnw_exp_world_lqcst6xtaq`
(881 files), code `RNW1-081RF-FZCZT-X8CJN-T006G-J0870-2AG63-YG1W8-8G3GH-149XR-08TM0-31P0F-71BD0`.
All files match the prepared candidate. Its 850-file canonical digest is
`0a2314e9a314f639b3f20ddc16a50f84d719488b71ada7c115dcfcc7e8b292be`. In the
313-country reference, Balanced is the baseline for 222 (71%); the four great
empires are Expansionist, their 49 explicit targets Defensive, 29 subjects Cautious,
six confederates Friendly, and three market-focused sea-league members Opportunistic.
The candidate preserves the same four empires and personality decisions, with only
the resource layer rerolled. Reference digest: 850 files,
`003d59758186470cda2fd2ce531ed154cb5875a405316b92eb36ad121a10b55e`.

Updated only the generator hub `mod/rnw_exp_hub` **0.13.8→0.13.9** (3,270 files,
all hashes match the built candidate). The Windows-layout Wine self-test exits 0:
`Random New World 0.13.9: window, native kernels and world codes work`. The previous
hub is retained byte for byte at ignored
`local_data/ai-balanced-baseline-0.13.9/hub-backup-before-0.13.9/` (3,270 files).
All ten previously installed worlds, all other existing mod files, and
`playsets.json`, `pdx_settings.json`, `continue_game.json` are unchanged. No EU5
launch or playset change; in-game behavior remains unknown. Built wheel SHA-256
`8779d473201af9f88d5ea90634e8b5c9cabdf05f9a91b027a2f0e9451fa2dc95`; launcher
SHA-256 `0ab741888f9ccedf83c91e9f2438d1983ca92fb3611dbe7cf0f25be6796ef8e9`.

Exact removal with EU5 closed: `uv run rnw uninstall-mod rnw_exp_world_lqcst6xtaq --user-dir '/mnt/games/SteamLibrary/steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V'`.
The generator hub is separate; its previous version is retained in the backup above.

2026-10-26, **0.13.8 / epoch 45 context-based AI personalities**, C395:
installed **RNW: Supercontinent EK6O** into new `mod/rnw_exp_world_ek6og4sohg`
(881 files), code `RNW1-081JQ-69DVY-H34JE-P006G-G0860-2AG63-YG1W8-8G3GH-149XR-08TM0-350CQ-G`.
All files match the prepared candidate. Its 850-file canonical digest is
`70ba230197166fcc247ba1f34458bd85172a406327f1a18db7736a2e857ac813`. Country
personalities follow each generated country's power proxy, neighbors, diplomacy,
markets/coasts and society archetype; the report records each decision and reason.
The deterministic 313-country reference digest is
`2fb15ba6b2e6109d23cc1c6da9f4452b126ef9e8e95ecdaecbe8b47774d12b4e`.
Updated only the generator hub `mod/rnw_exp_hub` **0.13.7→0.13.8** (3,270 files,
all match the built candidate). Its offline Windows-layout Wine self-test passes.
The previous hub is retained byte for byte at ignored
`local_data/ai-personality-context-0.13.8/hub-backup-before-0.13.8/` (3,270 files).
The existing `rnw_exp_world_nwtsag67v6` world (881 files), every other pre-existing
mod file and `playsets.json`, `pdx_settings.json`, `continue_game.json` are unchanged.
No EU5 launch or playset change; in-game behavior is unknown.

Exact removal with EU5 closed: `uv run rnw uninstall-mod rnw_exp_world_ek6og4sohg --user-dir '/mnt/games/SteamLibrary/steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V'`.
The generator hub is separate; its previous version is retained in the backup above.

2026-10-26, **0.13.7 / epoch 44 generated-country AI personalities**, C393–C394:
installed **RNW: Supercontinent NWTS** into new `mod/rnw_exp_world_nwtsag67v6`
(881 files), code `RNW1-081RF-FZCZT-X8CJN-T006G-E0860-2AG63-YG1W8-8G3GH-149XR-08TM0-3EHEQ-T`.
The 850-file canonical reference has SHA-256
`3451a8ffc3b26633322101a96a445002631265b74c3f69c2b150be88ae6b1f2e`; the installed
world matches its prepared candidate in every file. It assigns 313 generated sovereign
countries across the eight personalities defined by the installed game and omits pop-only
tribes. Updated only generator hub `mod/rnw_exp_hub` **0.13.6→0.13.7** (3,270 files,
all match the built package). Its Windows-layout offscreen self-test passes under isolated
Wine: window, native kernels and world codes work. The previous **3,268-file** hub is
verified byte for byte at ignored `local_data/ai-personalities/hub-backup-before-0.13.7/`
(manifest SHA-256 `b813866c7b1a3db1515dce8991ec8f09fd256fa134f814cf154e64e3a67e4942`).
No EU5 launch, playset or save change, or replacement of an existing world. Engine behavior
of the new assignments remains unobserved.

Exact removal with EU5 closed: `uv run rnw uninstall-mod rnw_exp_world_nwtsag67v6 --user-dir '/mnt/games/SteamLibrary/steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V'`.
The generator hub is separate; its previous version is retained in the backup above.

2026-10-26, **0.13.6 / epoch 43 campaign mod corrections**, [069](069-campaign-mod-fixes/README.md), C390–C392: installed **RNW: Supercontinent EVXP RC** into new `mod/rnw_exp_evxp_release` (860 files checked), library id `hjni42sc2r` in both native and Windows libraries (29 kept files each, full 6,874-location atlas and verified recovery). Treaty scripts/labels, boundary river drawing, duplicate ocean VFX and initial guild capacities corrected; exact location raster and all 24 height files retained. Reference: 849 canonical files, `f544876d…457e7b`. Updated generator-only `mod/rnw_exp_hub` 0.13.5→0.13.6 (3,268 files/source/catalogs checked). Preserved 820 original EVXP hashes, 7,620 other-mod size/time records, nine profile-root hashes, 134 save-file stat records, sixteen prior library records and two preferences. EU5 is closed; no game launch, playset edit or existing-world/save replacement. These corrections apply to newly generated worlds, not the completed campaign.

Exact removal: Remove **Supercontinent EVXP RC** in the generator, or `uv run rnw uninstall-mod rnw_exp_evxp_release --user-dir USER_DIR` with EU5 closed. The hub is separate. Its verified backups remain under ignored `local_data/release-100/hub-backup-before-0136` and the profile's `.rnw-install/retired/rnw_exp_hub_before_release_0136`; no cleanup sweep is performed.

2026-10-26, **0.13.5 / epoch 42 continuous location identities**, [068](068-continuous-location-identities/README.md), C374–C379: installed **RNW: Supercontinent EVXP fixed** in new `mod/rnw_exp_evxp_identities` (848 files verified), same seed/settings as original EVXP with the forced raster-edge split removed. Registered library id `uj3emczw5t` in both native and Windows libraries, with the full 6,874-location atlas, full previews, record and 29-file recovery receipt. Epoch reference: 837 canonical nonmetadata files, `76c17c96…f4d5b0`. Normal revealed-world presentation applied before installation. Updated generator-only `mod/rnw_exp_hub` 0.13.3→0.13.5 (3,266 files/source/catalogs checked), retaining verified external and retired backups without a sweep. Preserved 820 original EVXP hashes, 4,225 other-mod size/time records, nine profile-root hashes, 111 save-file stat records, eleven prior library records and two preference files. Existing worlds, saves and playsets stay intact. Host check finds no EU5 process; stale forced-close log state is `played`. No game launch or post-fix runtime result. The changed identities require a new campaign; no save migration.

Exact removal: use Remove on **Supercontinent EVXP fixed** in the generator, or `uv run rnw uninstall-mod rnw_exp_evxp_identities --user-dir USER_DIR` with the game closed. The original EVXP and generator-only hub are separate. Hub backups are retained in ignored `local_data/seam-identities/hub-backup-before-0135` and the profile's `.rnw-install/retired/rnw_exp_hub_before_seam_0135`; no cleanup is performed.

2026-10-24, **0.12.0 / epoch 30 ocean expansion**, [049](049-ocean-expansion/README.md), C282–C285: installed **RNW: Small continents NDIW** in the new `mod/rnw_exp_ocean_release` folder (818 files, all hashes match the verified reference). Updated `mod/rnw_exp_hub` to 0.12.0 (3,254 files, all hashes match the final package); its twelve runtime versions match the lock, including cached Pillow 13.0.0. This corrects the older C278 entry's assertion about Pillow 12.3.0 matching the lock. The nine profile-root files and 796 existing non-hub mod files are unchanged; worlds and playsets remain. No EU5 launch. Exact removal: `uv run rnw uninstall-mod rnw_exp_ocean_release --user-dir USER_DIR`; the hub is separate and has no game content.

2026-10-24, hub generator update (owner request, C278): replaced `mod/rnw_exp_hub` version 0.9.14 with 0.11.6 in the normal profile while EU5 was closed (installed executable build 26142040). The Windows wheel `eu5_random_new_world-0.11.6-cp312-abi3-win_amd64.whl` was built from this checkout (SHA-256 `7140789efec327078c26642d57aefd7fe38812dcada1d0709c651d008e2c4765`); the twelve runtime package versions reused from the local 0.9.17 hub artifact match the current lock. Hub packaging checks passed. All 3,247 installed files are byte-identical to `build/windows/candidate/rnw_exp_hub`. A separate world folder, `rnw_exp_world_3zpnllmlrz`, is present after the update; the installer replaces only the named mod and its `.rnw-install` work area and does not edit playsets. EU5 was not launched, so this version has not been newly checked through Open in folder. Removal: with EU5 closed, `uv run rnw uninstall-mod rnw_exp_hub --user-dir USER_DIR`.

2026-10-23, 0.10.1 candidate (experiment 032, C173-C174): installed and verified in the new profile folder `mod/rnw_exp_world_6dive2c4l6`, title `RNW: Continents 6DIV`, code `RNW1-080G0-00003-EF38N-A0050-20813-BM0ET-6V5G`. Source bundle: `local_data/lobby-gap-20261023/candidate/generated/rnw_exp_world_6dive2c4l6/`; a byte-identical copy is in `~/.local/share/random-new-world/generated/rnw_exp_world_6dive2c4l6/`. All 754 installed files match the source. Against CYHL (0.10.0), only `in_game/gui/multiplayer_lobby.gui` and `.metadata` change; the ineffective filter and ten text files are removed. All other files, including the accepted TI shaders and every map/start file, are hash-identical. Hub, CYHL and every profile-root file remain byte-identical, including playsets. Enable 6DIV instead of CYHL for the next owner test; no game launch by the agent. Removal, with EU5 closed: `rnw uninstall-mod rnw_exp_world_6dive2c4l6 --user-dir USER_DIR`.

2026-10-23, 0.10.0 candidate (experiment 031, C172): with EU5 closed, `rnw world RNW1-080G0-00003-EF38N-A0050-00813-BM0ED-FRY0 --install` made the new profile folder `mod/rnw_exp_world_cyhlrdiik7`, title `RNW: Continents CYHL`, version 0.10.0 (the world of AMK4, J3ZE and BDWK with the cover's drawings of terra incognita and a filter that leaves the New World out of the lobby's list); 765 files. Against `rnw_exp_world_bdwkgaakvy` only `pdxterrain2.shader`, `pdxwater.shader`, `rnw_new_world_cover.fxh`, `rnw_new_world_drawings.fxh`, `in_game/gui/filters/99_rnw_new_world.txt`, ten `rnw_new_world_cover_l_<language>.yml` and `.metadata` (json, thumbnail) differ or are new. The other mod folders keep their file counts and the profile root files are byte-identical to before; the playset was not changed (tick this world and untick BDWK). Game not launched by the agent. To see in game: experiment 031.
Removal, with EU5 closed: `uv run rnw uninstall-mod rnw_exp_world_cyhlrdiik7 --user-dir USER_DIR`, or delete exactly that folder; drop its playset entry in the launcher afterwards.

2026-10-23, opinions candidate (C170, C171): with EU5 closed, `rnw world RNW1-080G0-00003-EF38N-A004J-20813-BM0ET-REZG --install` made the new profile folder `mod/rnw_exp_world_bdwkgaakvy`, title `RNW: Continents BDWK`, version 0.9.33 (the world of AMK4 and J3ZE; the holders of the empires' opinions now discover their partners' capital areas: 17 areas added to 16 countries); 753 files. Against `rnw_exp_world_j3ze425437` only `main_menu/setup/1337/10_countries.txt` and `.metadata` (json, thumbnail) differ. The other mod folders keep their file counts and the profile root files are byte-identical to before; the playset was not changed (tick this world and untick J3ZE). Game not launched by the agent. To see in game: `error.log` of a new 1337 game has no `have not discovered the capital` line (17 in AMK4 and J3ZE).
Removal, with EU5 closed: `uv run rnw uninstall-mod rnw_exp_world_bdwkgaakvy --user-dir USER_DIR`, or delete exactly that folder; drop its playset entry in the launcher afterwards.

2026-10-23, cover frame candidate (experiment 027 follow-up, C169): with EU5 closed, `rnw world RNW1-080G0-00003-EF38N-A004J-00813-BM0FJ-JT80 --install` made the new profile folder `mod/rnw_exp_world_j3ze425437`, title `RNW: Continents J3ZE`, version 0.9.32 (the world of AMK4 with the cover that no longer reaches beyond the map's north and south edges); 753 files. Against `rnw_exp_world_amk4jfomct` only `main_menu/gfx/FX/rnw_new_world_cover.fxh` and `.metadata` (json, thumbnail) differ. The other mod folders keep their file counts (hub 3,073, probe 753, 6WBN 753, AMK4 753, CANS 752, DSLL 741, HGIH 751, HU2B 732, QDUV 751) and the profile root files are byte-identical to before; the playset was not changed (tick the world and untick AMK4 in the launcher). Game not launched by the agent.
Removal, with EU5 closed: `uv run rnw uninstall-mod rnw_exp_world_j3ze425437 --user-dir USER_DIR`, or delete exactly that folder; drop its playset entry in the launcher afterwards.

2026-10-23, spline network candidate and probe (experiment 030, C164, C165): with EU5 closed, `rnw world RNW1-080G0-00003-EF38N-A004H-Y0813-BM0ET-JH64 --install` made the new profile folder `mod/rnw_exp_world_amk4jfomct`, title `RNW: Continents AMK4`, version 0.9.31 (the map of 6WBN below with the spline network that keeps vanilla's order); all 753 files hash like the manifest. `rnw_exp_probe_splnet_oldworld`, title `RNW: probe: Old World road strips only`, is a copy of it (753 files) whose spline network holds only the vanilla strips of the locations still there, made by a scratch script from the same installed files (`local_data/r7d/`, not committed). The other mod folders keep their file counts (6WBN 753, CANS 752, HGIH 751, HU2B 732, QDUV 751, DSLL 741, hub 3,073) and the profile root is byte-identical to before; the active playset was not changed. The earlier report that the 6WBN world made every road vanish came from the wrong lens (C166), so no defect in it is established; the probe and 6WBN are no longer needed and can be removed.
Removal, with EU5 closed: `uv run rnw uninstall-mod rnw_exp_world_amk4jfomct rnw_exp_probe_splnet_oldworld rnw_exp_world_6wbnuwo42f --user-dir USER_DIR`, or delete exactly those folders; drop their playset entries in the launcher afterwards.

2026-10-22, spline network candidate (experiment 029, C162, C163): installed with `rnw world RNW1-080G0-00003-EF38N-A004H-W0813-BM0EQ-NRTC --install` into the new profile folder `mod/rnw_exp_world_6wbnuwo42f`, title `RNW: Continents 6WBN`, version 0.9.30 (the world of CANS below with the generated spline network). EU5 was closed. All 753 installed files hash like the 753 of the world's manifest; the other `rnw_exp_world_*` folders keep their file counts (CANS 752, HGIH 751, HU2B 732, QDUV 751, DSLL 741, hub 3,073) and `playsets.json`, `pdx_settings.json` and the other files of the profile root are byte-identical to before. The active playset (hub + CANS) was not changed: enable 6WBN instead of CANS to try it. The library entry is in `~/.local/share/random-new-world/generated/rnw_exp_world_6wbnuwo42f/`.
Removal: with EU5 closed, `uv run rnw uninstall-mod rnw_exp_world_6wbnuwo42f --user-dir USER_DIR` (the window's Remove and Delete do the same for the mod and the library entry); drop its playset entry in the launcher afterwards.

2026-10-22, R7b and R7c candidate (experiment 028, C159, C160): installed with `rnw world RNW1-080G0-00003-EF38N-A004H-T0813-BM0F1-FXJ0 --install` into the new profile folder `mod/rnw_exp_world_canszr3phf`, title `RNW: Continents CANS`, version 0.9.29 (continents 3706823338, `empire_permille` 1000; it carries the 0.9.27 cover fix). EU5 was closed. All 752 installed files hash like the 752 of the world's manifest; the other `rnw_exp_world_*` folders keep their file counts (HGIH 751, HU2B 732, QDUV 751, DSLL 741, hub 3,073; QDUV, the 0.9.27 candidate of the next entry, was already in the profile and is not verified by this session), and `playsets.json`, `pdx_settings.json` and the other files of the profile root are byte-identical to before. The active playset was not changed: enable CANS in the game's playset to try it. The library entry (maps, record, report) is in `~/.local/share/random-new-world/generated/rnw_exp_world_canszr3phf/`.
Removal: with EU5 closed, `uv run rnw uninstall-mod rnw_exp_world_canszr3phf --user-dir USER_DIR` (the generator window's Remove and Delete do the same for the mod and the library entry); drop its playset entry in the launcher afterwards.

2026-10-22, scoped shader fix (experiment 027, C154): prepared new installation target
`mod/rnw_exp_world_qduvxguw6u`, title `RNW: Small continents QDUV`, version 0.9.27.
Source: `local_data/cover-scope-20261022/application/generated/rnw_exp_world_qduvxguw6u/rnw_exp_world_qduvxguw6u/`.
Installation and full-file verification are pending. Existing HGIH and other worlds
are preserved; enable QDUV instead of HGIH in the game's playset after installation.
Removal: with EU5 closed, `uv run rnw uninstall-mod rnw_exp_world_qduvxguw6u --user-dir USER_DIR`.
Offline reference-test artifacts stay under `local_data/cover-scope-20261022/reproduction/`.

2026-10-22, owner-requested installation of C151: target new profile folder
`mod/rnw_exp_world_hgihw5wfjp`, title `RNW: Small continents HGIH`, version 0.9.26.
Source: `local_data/close-zoom-cover/application/generated/rnw_exp_world_hgihw5wfjp/rnw_exp_world_hgihw5wfjp/`.
The game was closed and the target did not exist. [V-EXEC] Installed through
`rnw install-mod`; all 751 files, including metadata, independently hash-identical
to the source. Existing worlds and playset entries were outside the installation.
The active playset still enables the older DSLL world; enable HGIH instead in game.
Removal: with EU5 closed, `uv run rnw uninstall-mod rnw_exp_world_hgihw5wfjp --user-dir USER_DIR`.

2026-10-22, close-zoom cover (C150–C151, experiment 026): no mod was installed or
removed and no existing profile/mod/playset was changed. The new offline CLI bundle is
`local_data/close-zoom-cover/application/generated/rnw_exp_world_hgihw5wfjp/`.
The independent reference-test output is under
`local_data/close-zoom-cover/reproduction/`. Both are outside every game profile and
ignored by Git; either exact folder may be removed when its evidence is no longer needed.

Before 2026-10-14 no test mod was installed in the owner's normal EU5 user mod directory. Only new folders starting with `rnw_exp_` may be installed there, and each must be recorded here before use.

2026-10-22 patch 1.4.3 check ([025](025-patch-1-4-3/README.md)): no mod installed or
removed. The new offline bundle is exactly
`local_data/patch-1.4.3/application/generated/rnw_exp_world_yx2z7qw242/`, outside every
game profile; only that folder needs removal if the retained bundle is no longer wanted.

2026-10-22 continuation: no mod was installed or removed. Offline bundles
`generated/rnw_exp_resume_cold`, `generated/rnw_exp_resume_warm`, and package folders
`generated/rnw_exp_resume_hub`, `generated/rnw_exp_resume_hub_final` were created for C144–C145.
They are outside every game profile. The isolated Wine prefix is
`local_data/resume-20261022/wine`; stop only its services with
`WINEPREFIX="$PWD/local_data/resume-20261022/wine" wineserver -k` before removing that exact
prefix if desired. The retained bundles and packages may be removed individually when no
longer needed; no normal-profile removal command applies to them.

| Folder | Location | Purpose | Removal |
|---|---|---|---|
| `rnw_exp_001_metadata` | `/tmp/rnw_eu5_validation/mod/` (isolated temporary profile) | Metadata recognition, EU5 1.4.1 | With the game closed, delete only that exact folder and its temporary profile if desired. It is outside the normal user directory. |
| `rnw_exp_new_world` | Normal profile `mod/` | The single current RNW test mod. Every new build replaces it in place with `uv run rnw install-mod --replace generated/rnw_exp_new_world/rnw_exp_new_world USER_DIR` (installed 2026-10-15 at the owner's explicit request; tree verified byte-identical). Installed content (2026-10-20, installed by the owner with the game closed, verified identical, 728 files): version 0.9.12, continents seed 319218363 built for 1.4.2 (commit 4404ba1; C99, experiment 015), NOT GAME VALIDATED. Earlier contents: 0.9.10 of the same seed (commit 7b5a517; C95–C98, experiment 015: runs on a fresh launch, crashed after a vanilla game); 0.9.8 of the same seed (19:02, installed while RNW was active; commit 947d626; C93); 0.9.7 of seed 3717486232 (experiment 014, installed 18:08); 0.9.6 of seed 3717486232 (experiment 013 clean rerun, world A′, installed 17:30 with another playset active); 0.9.6 seed 34378487 for 1.4.2 (world B′, installed with the game closed); 0.9.5 of the same seed built from 1.4.1 files (commit 901216c; experiment 013); 0.9.4 seed 3717486232 (commit ea19973; experiment 012); builds 0.8.0–0.9.3 for experiments 010–012; a08883a V1b.1 seed-driven coastlines on seed 3706823338 (C65, experiment 009); 783b4b7 V1b rivers seed 3903742112 (C62; rivers accepted in game, C64); 80b0a2d V1a.1 seed 42 (C57; accepted in game, C58); 752ed03 V1a terrain and biomes (C53; loaded in game, C55); 305cb78 coasts, materials, water and lakes (C46); v2 (69de7b6) loaded in game (C45). Baseline logs: `local_data/baseline/2026-10-14-normal-no-rnw/`. Addition for experiment 019, part 3 (2026-10-21, copied by the owner, outside the generated bundle): `generator/probe.exe` (launch probe 1, sha256 `00fa341e…7007560b`, mode 644) and `generator/probe-result.txt`, written by the probe when the owner ran it from the game at 04:54 (C107). | Game closed: disable it in the playset, then `uv run rnw uninstall-mod rnw_exp_new_world --user-dir USER_DIR`. The probe alone: delete `rnw_exp_new_world/generator/`; the next `install-mod --replace` also removes it. |
| `rnw_exp_hub` | Normal profile `mod/` | Experiment 021 (approved by the owner on 2026-10-21 as the one exception to the single-mod policy, because the product itself has two mods, ADR 0009): the development stand-in for the Workshop item, with the launcher and the Windows generator, no game content; built by `uv run python packaging/hub.py --replace` (0.9.13, 147 MiB). The generator it carries replaces `rnw_exp_new_world` when it installs a world. Installed by the owner at 05:41 with the game closed, verified identical (3,064 files). Its generator then installed continents seed 319218363 (`RNW1-040G0-00000-9GDRN-V004G-T036F-9N0`, 0.9.13) into `rnw_exp_new_world` from inside the running game at 06:07 (731 files, equal to the reference) and left 596 files of the previous world in `mod/.rnw_exp_new_world.old`, without metadata, which the game held (C112); the owner deleted that folder at 06:26 with the game closed and installed the rebuilt hub with the fixed installer and affinity reading (commit fe786cd) with `--replace`, verified identical (3,064 files); `mod/` then held only `rnw_exp_hub` and `rnw_exp_new_world`. | Game closed: `uv run rnw uninstall-mod rnw_exp_hub --user-dir USER_DIR`; the generator's own files are in `AppData/Local/RandomNewWorld/` of the game's prefix and can be deleted with it. |
| `rnw_exp_world_*` | Normal profile `mod/` | From 0.9.14 the hub's generator makes one mod per world, named `rnw_exp_world_<id>` (owner's decision 2026-10-21: what to keep is the player's choice); the owner creates them by pressing Generate, and the generator lists, adds, removes and deletes them. The older `rnw_exp_new_world` then shows as a stray (an earlier world without a record). | In the generator: Delete world; or, with the game closed, `uv run rnw uninstall-mod <folder> --user-dir USER_DIR`. |
| `rnw_exp_probe_lobby` | Normal profile `mod/` | Experiment 022 ([record](022-lobby-terra-incognita/README.md)): a rule and two log lines to see what the new-game screen lets a mod do; five files, no map. Installed by the owner on 2026-10-21 (files of 14:28 and 14:48); still enabled in the RNW playset at experiment 024 (`debug.log`, 21:46), where it changes no shader; its rule's on-start line still logs. Its work is done (C129) and its rule, listed on the lobby's Game Rules tab, does nothing: **to be removed** (2026-10-22); its source was deleted from the repository the same day. | Game closed: untick it, then `uv run rnw uninstall-mod rnw_exp_probe_lobby --user-dir USER_DIR`. |
| `rnw_exp_probe_cover` | Normal profile `mod/` | Experiment 024 ([record](024-terrain-cover-probe/README.md)): the game's terrain shader with a tint over the world's cover grid; built locally into `generated/rnw_exp_probe_cover` (derived from the game, never committed); 2 files. Installed by the owner on 2026-10-21 and ticked in the game's playset manager at 21:47:32 (C135). Its work is done. **Removed from the profile by 2026-10-22** (the folder was gone from `mod/`; the RNW playset still named it, which the launcher drops), and `generated/rnw_exp_probe_cover` deleted. | Done; remove its playset entry in the launcher. |
| `rnw_exp_d0_coast_s42`, `rnw_exp_nw_continents_s42` | — | **Removed 2026-10-15** with `rnw uninstall-mod` at the owner's request (D0 coast test; first T3 build that crashed, C43). | Done; their playset entries can be dropped in the launcher. |

Policy (owner, 2026-10-15): keep one installed RNW world mod, `rnw_exp_new_world`, replaced in place by each build (since 2026-10-21 beside the one hub, `rnw_exp_hub`); staged bundles in `generated/` are replaced with `--replace` instead of accumulating.

The normal playset's existing Workshop mods were not intentionally modified. On 2026-10-14 the owner resumed in-game testing for experiment 004; the agent does not launch the game itself.

2026-10-23 cleanup, explicitly requested by the owner after testing 0.10.0: with EU5 closed, `rnw uninstall-mod` removed exactly `rnw_exp_probe_splnet_oldworld`, `rnw_exp_world_6wbnuwo42f`, `rnw_exp_world_amk4jfomct`, `rnw_exp_world_bdwkgaakvy`, `rnw_exp_world_canszr3phf`, `rnw_exp_world_dsllwsx2jw`, `rnw_exp_world_hgihw5wfjp`, `rnw_exp_world_hu2bwekork`, `rnw_exp_world_j3ze425437`, `rnw_exp_world_qduvxguw6u`. The only remaining folders at that point are `rnw_exp_hub` and `rnw_exp_world_cyhlrdiik7`; all their files and every profile-root file (including playsets) are hash-identical to before. Library bundles and saves were preserved. Earlier entries above describe historical installations, not mods still installed.

2026-10-23 N1 candidate ([033](033-new-world-content-n1/README.md)): with EU5 closed, `rnw world RNW1-080G0-00003-EF38N-A0050-80813-BM0FB-H644 --install` added exactly one folder, `mod/rnw_exp_world_fx2elamqlt` (**RNW: Continents FX2E**, 0.10.4, epoch 14, 764 files, every file hash-identical to the export's record). Existing mods, `rnw_exp_hub`, `rnw_exp_world_6dive2c4l6` and `rnw_exp_world_cyhlrdiik7`, and every profile-root file (playsets, settings) were not touched: the only entries of the profile newer than the install are `mod/` and the new folder. Removal: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_fx2elamqlt --user-dir USER_DIR`; the library entry stays as a code.

2026-10-23 N2 probe ([034](034-content-hooks-n2/README.md)): with EU5 closed, `rnw probe-hooks` wrote `generated/rnw_exp_probe_hooks` (21 files) and `rnw install-mod` added exactly one folder, `mod/rnw_exp_probe_hooks` (**RNW probe: content hooks**), hash-identical to the generated tree. Nothing else in the profile changed; no playset was edited (the owner enables the mod). Removal: with the game closed, `uv run rnw uninstall-mod rnw_exp_probe_hooks --user-dir USER_DIR`.

2026-10-23 N3 candidates ([035](035-new-world-content-n3/README.md)): with EU5 closed, `rnw world CODE --install` added exactly two folders, `mod/rnw_exp_world_eil2f6y6cf` (**RNW: Small continents EIL2**, the epoch 15 reference world, 784 files) and `mod/rnw_exp_world_ri4igjvamo` (**RNW: Continents RI4I**, the owner's land, 782 mod files), both 0.10.5; every file hashes to its export's record. Existing mods, `rnw_exp_hub`, `rnw_exp_probe_hooks`, `rnw_exp_world_6dive2c4l6`, `rnw_exp_world_cyhlrdiik7` and `rnw_exp_world_fx2elamqlt`, and every profile-root file were not touched. Removal: with the game closed, `uv run rnw uninstall-mod <folder> --user-dir USER_DIR`; the library entries stay as codes.

2026-10-23 N2 probe, rebuilt ([036](036-console-session/README.md)): with EU5 closed, `rnw probe-hooks` rewrote `generated/rnw_exp_probe_hooks` (21 files, now with the story start in miniature) and `rnw install-mod --replace` replaced exactly the one folder `mod/rnw_exp_probe_hooks`, hash-identical to the generated tree (21 of 21). No other mod, playset or profile-root file was touched. Removal as before: with the game closed, `uv run rnw uninstall-mod rnw_exp_probe_hooks --user-dir USER_DIR`.

2026-10-23 sitting 036 repair ([037](037-console-session-2/README.md)): with EU5 closed (no `eu5.exe` process), `rnw world RNW1-0426C-SYW6B-MW73Y-C0050-C075Q-E4G` made the epoch 16 reference world in the library and `rnw install-mod` added exactly one folder, `mod/rnw_exp_world_prj3zj4whq` (**RNW: Small continents PRJ3**, 0.10.6, 786 files, hash-identical to the library bundle); `rnw probe-hooks` rewrote `generated/rnw_exp_probe_hooks` (21 files, probe 0.2.0) and `rnw install-mod --replace` replaced exactly `mod/rnw_exp_probe_hooks` (21 of 21 identical). No other mod, no playset and no profile-root file was touched (their times are as before). The owner enables PRJ3 in place of EIL2 (`rnw_exp_world_eil2f6y6cf`, which stays installed). Removal: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_prj3zj4whq --user-dir USER_DIR`; the library entry stays as a code.

2026-10-23 sitting 037 repair ([038](038-lobby-list-and-colony/README.md)): with EU5 closed, `rnw world RNW1-0426C-SYW6B-MW73Y-C0050-E01PQ-P70` made the epoch 17 reference world in the library and `rnw install-mod` added exactly one folder, `mod/rnw_exp_world_kpjmspjsw3` (**RNW: Small continents KPJM**, 0.10.7, 786 files, hash-identical to the library bundle); `rnw probe-hooks` rewrote `generated/rnw_exp_probe_hooks` (21 files, probe 0.3.0) and `rnw install-mod --replace` replaced exactly `mod/rnw_exp_probe_hooks` (21 of 21 identical). No other mod, no playset and no profile-root file was touched (their times are as before). The owner enables KPJM in place of PRJ3 (`rnw_exp_world_prj3zj4whq` and EIL2 stay installed; both carry the list that flickers). Removal: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_kpjmspjsw3 --user-dir USER_DIR`; the library entry stays as a code.

2026-10-23 cleanup, requested by the owner after testing 0.10.7 (038): with EU5 closed, `rnw uninstall-mod` removed exactly `rnw_exp_world_6dive2c4l6`, `rnw_exp_world_cyhlrdiik7`, `rnw_exp_world_eil2f6y6cf`, `rnw_exp_world_fx2elamqlt`, `rnw_exp_world_prj3zj4whq` and `rnw_exp_world_ri4igjvamo`, worlds of 0.10.0 to 0.10.6 whose country list hid cards (flicker, C205). Left in `mod/`: `rnw_exp_hub`, `rnw_exp_probe_hooks` (0.3.0) and `rnw_exp_world_kpjmspjsw3` (0.10.7). Every profile-root file (playsets, settings) has the time it had; the library's bundles under `random-new-world/generated/` and the saves were not touched. The RNW playset still names the removed folders, which the launcher drops. Earlier entries above describe historical installations.

2026-10-23 N4 candidate ([039](039-new-world-content-n4/README.md)): with EU5 closed (no `eu5.exe` process), `rnw world RNW1-0426C-SYW6B-MW73Y-C0050-M00ZJ-9C0 --install` added exactly one folder, `mod/rnw_exp_world_r7phac72kg` (**RNW: Small continents R7PH**, 0.10.10, epoch 20, the reference world: 792 mod files and the two `.metadata` files; every mod file hashes to its export record, and the record's digest is the one pinned in `tests/golden_world.json`). It holds everything of 0.10.8 to 0.10.10: the six formable families, the eight story families, the colonial names. Existing mods, `rnw_exp_hub`, `rnw_exp_probe_hooks`, `rnw_exp_world_kpjmspjsw3` and every playset were left as they were; no playset was edited (the owner enables the mod). Removal: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_r7phac72kg` (or delete exactly that folder).

2026-10-23 probe 0.4.0 ([040](040-colonial-path-probe/README.md)): with EU5 closed (no `eu5.exe` process), `rnw probe-hooks` rewrote `generated/rnw_exp_probe_hooks` (21 files; the staged copy of 0.3.0 was removed first) and `rnw install-mod --replace` replaced exactly `mod/rnw_exp_probe_hooks` (21 of 21 identical). The mods in the profile are the same four folders as before, the times of `playsets.json`, `pdx_settings.json`, `continue_game.json` and `rnw_exp_hub` did not change. Removal as before: with the game closed, `uv run rnw uninstall-mod rnw_exp_probe_hooks`.


2026-10-23 audit candidate ([audit of N0 to N4](../docs/research/n0-n4-audit.md)): with EU5 closed (no `eu5.exe` process), `rnw world RNW1-0426C-SYW6B-MW73Y-C0050-P001G-B20 --install` added exactly one folder, `mod/rnw_exp_world_t3htedmcwr` (**RNW: Small continents T3HT**, 0.10.11, epoch 21, the reference world: 793 mod files and the two `.metadata` files; every mod file is byte-identical to the export made in the audit and the world's digest is the one pinned in `tests/golden_world.json`). It repairs what the audit found in the log of sitting 038 (the `province_definition:` scope, the titles of hidden events, the DLC monuments). Existing mods, `rnw_exp_hub`, `rnw_exp_probe_hooks`, `rnw_exp_world_kpjmspjsw3` and `rnw_exp_world_r7phac72kg`, and every profile-root file (`playsets.json`, `pdx_settings.json`, `continue_game.json`) were left as they were (their times did not change); no playset was edited (the owner enables the mod). Removal: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_t3htedmcwr` (or delete exactly that folder).

2026-10-24 sea geography candidate ([041](041-sea-geography/README.md), [design](../docs/sea-geography.md)): with EU5 closed (no `eu5.exe` process), `rnw world RNW1-0426C-SYW6B-MW73Y-C0050-R00KR-D6G --install` added exactly one folder, `mod/rnw_exp_world_mxhxetfs3r` (**RNW: Small continents MXHX**, 0.10.12, epoch 22, the reference world: 793 mod files and the two `.metadata` files; every mod file is byte-identical to the export made for the digest pinned in `tests/golden_world.json`). It gives every coastal sea zone a port (and Bermuda and Saint Helena theirs back), names the water for its shape, gives it the game's topography and continues the game's ocean currents. Existing mods, `rnw_exp_hub`, `rnw_exp_probe_hooks`, `rnw_exp_world_kpjmspjsw3`, `rnw_exp_world_r7phac72kg` and `rnw_exp_world_t3htedmcwr`, and every profile-root file (`pdx_settings.json`, `continue_game.json`) were left as they were (their times did not change); no playset was edited (the owner enables the mod). Removal: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_mxhxetfs3r` (or delete exactly that folder).


2026-10-24 lanes and closed ocean candidate ([042](042-lanes-and-closed-ocean/README.md), [design](../docs/sea-geography.md)): with EU5 closed (no `eu5.exe` process), `rnw world RNW1-0426C-SYW6B-MW73Y-C0050-T00YM-Q00 --install` added exactly one folder, `mod/rnw_exp_world_6rndxwdntf` (**RNW: Small continents**, 0.10.13, epoch 23, the reference world: 793 mod files and the two `.metadata` files; every mod file is byte-identical to the export made for the digest pinned in `tests/golden_world.json`). It closes the open ocean to ships as the game's is (36 zones of `ocean_wasteland`) and leaves 420 lanes of deep ocean with the currents of the game's replaced lanes. Existing mods (`rnw_exp_hub`, `rnw_exp_probe_hooks`, `rnw_exp_world_kpjmspjsw3`, `rnw_exp_world_mxhxetfs3r`, `rnw_exp_world_r7phac72kg`, `rnw_exp_world_t3htedmcwr`), `playsets.json`, `pdx_settings.json` and `continue_game.json` have the times they had. Removal as before: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_6rndxwdntf`.

2026-10-24 strait crossings candidate ([043](043-strait-crossings/README.md), [design](../docs/sea-geography.md)): with EU5 closed (no `eu5.exe` process), `rnw world RNW1-0826C-SYW6B-MW73Y-C0050-W0813-G0TR8-CG --install` added exactly one folder, `mod/rnw_exp_world_5zovefqzyg` (**RNW: Small continents**, 0.10.14, epoch 24, the reference world: 792 mod files and the two `.metadata` files; every mod file is byte-identical to the export made for the digest pinned in `tests/golden_world.json`). It brings near landmasses together to straits and writes 6 crossing rows for generated lands into `adjacencies.csv`; the closed ocean and lanes of 042 are in it. Existing mods (`rnw_exp_hub`, `rnw_exp_probe_hooks`, `rnw_exp_world_kpjmspjsw3`, `rnw_exp_world_mxhxetfs3r`, `rnw_exp_world_r7phac72kg`, `rnw_exp_world_t3htedmcwr`, `rnw_exp_world_6rndxwdntf`), `playsets.json`, `pdx_settings.json` and `continue_game.json` have the times they had. Removal as before: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_5zovefqzyg`.

2026-10-24 candidate 0.11.1 ([044](044-sea-sitting/README.md), C249-C250): with EU5 closed (no `eu5.exe` process), `rnw world RNW1-0826C-SYW6B-MW73Y-C005G-20813-G0HNQ-QV --install` added exactly one folder, `mod/rnw_exp_world_2lor7eti3p` (**RNW: Small continents**, 0.11.1, epoch 25, the reference world: 792 mod files and the two `.metadata` files; every mod file is byte-identical to the export made for the digest pinned in `tests/golden_world.json`). It gives the closed zones of the ocean no `combat` and `unit_stack` locator, as the game's own have none, and guards the lobby's scripted GUI against a country that is none; everything else is the 0.10.14 world's. Existing mods (`rnw_exp_hub`, `rnw_exp_probe_hooks`, `rnw_exp_world_kpjmspjsw3`, `rnw_exp_world_mxhxetfs3r`, `rnw_exp_world_r7phac72kg`, `rnw_exp_world_t3htedmcwr`, `rnw_exp_world_6rndxwdntf`, `rnw_exp_world_5zovefqzyg`), `playsets.json`, `pdx_settings.json` and `continue_game.json` have the times they had. Removal as before: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_2lor7eti3p`.

2026-10-24 candidate 0.11.2 ([045](045-varied-societies/README.md), C251-C253): with EU5 closed (no `eu5.exe` process), `rnw world RNW1-080G0-00000-00006-G005G-40813-BM0FH-9J88 --install` added exactly one folder, `mod/rnw_exp_world_2r7bql6dk3` (**RNW: Continents 2R7B**, 0.11.2, epoch 26, continents seed 208 with every hearth's domain raising an extraordinary society: 792 mod files and the two `.metadata` files, all 794 hash like the manifest of the export). It holds a sea league, a highland confederation, a fractured realm and a sacred centre beside 4 great empires; the reference world of the epoch (`RNW1-0826C-SYW6B-MW73Y-C005G-40813-G0TQW-2Z`) is not installed. Existing mods (`rnw_exp_hub`, `rnw_exp_probe_hooks`, `rnw_exp_world_kpjmspjsw3`, `rnw_exp_world_mxhxetfs3r`, `rnw_exp_world_r7phac72kg`, `rnw_exp_world_t3htedmcwr`, `rnw_exp_world_6rndxwdntf`, `rnw_exp_world_5zovefqzyg`, `rnw_exp_world_2lor7eti3p`), `playsets.json`, `pdx_settings.json` and `continue_game.json` have the times they had (05:07 to 05:13, the owner's sitting). Removal as before: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_2r7bql6dk3`.


2026-10-24 sitting fixes ([046](046-sitting-fixes/README.md), C257-C261): with EU5 closed (the session log records exit), added exactly one new folder, `mod/rnw_exp_world_bdi5rrmfyp` (**RNW: Continents BDI5**, 0.11.3, epoch 27, continents seed 210 with extraordinary chance 1000, code `RNW1-080G0-00000-00006-J005G-60813-BM0FX-JZYR`). All 815 installed files (813 mod files plus two metadata files) hash identically to the verified candidate under `local_data/sitting-fixes/app/generated/rnw_exp_world_bdi5rrmfyp/`; mod digest `650d92e74ea63ec7b08f823e6e05aa1f9f77c0f16dd792f614e0fcc44dcb2945`. Existing 9 profile-root files retain their hashes, and all 9,441 existing mod files retain their sizes and modification times; the old mod folders and playsets were preserved. No game launch. The epoch-27 reference world is recorded in `tests/golden_world.json` and stays local, uninstalled. Removal, with the game closed: `uv run rnw uninstall-mod rnw_exp_world_bdi5rrmfyp --user-dir USER_DIR`; the staged bundle stays under the project's ignored local data.


2026-10-24 N5 candidate ([047](047-region-keys/README.md), C262-C265): with EU5 closed, installed **RNW: Small continents 6RF2**, `mod/rnw_exp_world_6rf2nzt4dv` (0.11.4, epoch 28, reference code `RNW1-0826C-SYW6B-MW73Y-C005G-80813-G0Q8H-SZ`). All 816 files (814 mod files and two metadata files) hash identically to `local_data/n5/app/generated/rnw_exp_world_6rf2nzt4dv/rnw_exp_world_6rf2nzt4dv/`; mod digest `a05a8d4a8fe252f683613fdbc0951e022f18c2c4cefd353ea9ed91ea16ef0b46`. Nine existing profile-root files retain their hashes, and 10,256 existing mod files retain sizes and modification times; existing folders and playsets are preserved. No game launch. Exact removal command is in experiment 047; only `rnw_exp_world_6rf2nzt4dv` is removed, and the staged bundle stays local.

2026-10-24 probe retired (owner: *a third mod is too many; the player enables the map and nothing else*, [log](../docs/research/log.md)): with EU5 closed (no `eu5.exe` process), `rnw uninstall-mod rnw_exp_probe_hooks` removed exactly that one folder (0.4.0, 21 files) from `mod/`; `generated/rnw_exp_probe_hooks` was deleted and the code that wrote it (`eu5_probe.py`, `rnw probe-hooks`, `tests/test_probe.py`) with it. `playsets.json`, `pdx_settings.json` and `continue_game.json` have the hashes they had; the RNW playset still names the folder, which the launcher drops. Left in `mod/`: `rnw_exp_hub` and the eight `rnw_exp_world_*` folders. No probe is built or installed again: see the rule *One mod: the map* in `AGENTS.md`. The earlier entries about the probe describe historical installations.

2026-10-24 L1 candidate ([048](048-localization/README.md), C268-C274): with EU5 closed (no `eu5.exe` process), `rnw world RNW1-0826C-SYW6B-MW73Y-C005G-A0813-G0PJF-6F --install` added exactly one folder, `mod/rnw_exp_world_2o74n3gmdn` (**RNW: Small continents 2O74**, 0.11.5, epoch 29, the reference world). All 814 mod files are byte-identical to the reference export under `local_data/l1/reference/`. The nine profile-root files keep their hashes and none of the 9,420 existing mod files changed size or time; the folders left in `mod/` before were `rnw_exp_hub` and eight `rnw_exp_world_*` (the 0.11.3 and 0.11.4 candidates `bdi5rrmfyp` and `6rf2nzt4dv` were no longer there). No playset was edited (the owner enables the mod). Removal: with the game closed, `uv run rnw uninstall-mod rnw_exp_world_2o74n3gmdn`.


2026-10-25 seeded land origin ([050](050-seeded-land-origin/README.md), C286–C287): with EU5 closed, installed exactly two new folders: `mod/rnw_exp_seeded_land_release` (**RNW: Small continents BSB7**, 0.12.1, epoch 31, 816 files including metadata) and `mod/rnw_exp_generator_0121` (**Random New World: generator 0.12.1 (offline verified)**, 3,254 files). Both are hash-identical to their prepared candidates. The world uses epoch 31 (`RNW1-0826C-SYW6B-MW73Y-C0060-20813-R0JKE-XJ`, 814 non-metadata files, digest `d07aed4acb7690f15d70bed95ba6e1ff30d8f11c29e2be8c169cd9fb9172da15`) and needs no companion mod. The new generator folder holds no game content; launch its `Random New World Generator.exe`, without enabling it in a playset. The existing `rnw_exp_hub` and every existing mod remain: all 8,044 existing mod files keep sizes and modification times; all nine profile-root files keep hashes. No settings, saves, library entries or playsets were changed. The isolated Windows generator self-test passes; no EU5 launch. Remove exactly these candidates with `uv run rnw uninstall-mod rnw_exp_seeded_land_release --user-dir USER_DIR` and `uv run rnw uninstall-mod rnw_exp_generator_0121 --user-dir USER_DIR`, with the game closed. Raw audit and installation evidence stays in ignored `local_data/japan-island/`.


2026-10-25 main generator update (owner: “Собери в игру”, C288): updated the existing `mod/rnw_exp_hub` from 0.12.0 to **0.12.1**, rather than requiring the separate candidate folder. All **3,254** installed files match the prepared canonical hub; its metadata and embedded package version agree. The prior hub is backed up byte for byte outside the profile at ignored `local_data/japan-island/hub-backup-before-main-0.12.1/` (3,254 checked files). All nine profile-root hashes and the 3,254 other-mod file size/time records are preserved; the two existing mod folders stay the same. No world, library record, save, playset or game-installation file was changed. The installed Windows generator's offscreen window/native/world-code self-test passes in the isolated Wine prefix; EU5 was not launched. The separate `rnw_exp_generator_0121` folder was not removed. Exact removal of the main generator, if requested: `uv run rnw uninstall-mod rnw_exp_hub --user-dir USER_DIR`. Installation and self-test reports remain under ignored `local_data/japan-island/main-hub-*`.


2026-10-25 continuous map wrap ([051](051-wrap-continuity/README.md), C289–C291):
updated the existing main `mod/rnw_exp_hub` **0.12.1 → 0.12.2** (3,254 files,
all hash-verified against the canonical package), with a verified 3,254-file
backup at ignored `local_data/wrap-continuity/hub-backup-before-0.12.2/`. Added
only `mod/rnw_exp_wrap_continuity`, **RNW: Small continents SEOH**, epoch 32,
code `RNW1-0826C-SYW6B-MW73Y-C0060-40813-G11P6-36` (815 files including metadata;
813 non-metadata files, digest `1621ae318330529795f46ebd8a43e78e92b8e48c78b58925903edb5203a486cc`).
The world's final raster has a 2,109,356-pixel passable landmass crossing the seam
and 74 wrapped road strips. All nine profile-root hashes, 6,442 other-mod file
size/time records and six previous mod folders are preserved. The installed
Windows generator passes its isolated offscreen self-test; new cylindrical
sample bytes match Linux. No EU5 launch, playset edit, existing-world replacement,
library change or save change. Exact removal with EU5 closed: `uv run rnw
uninstall-mod rnw_exp_wrap_continuity --user-dir USER_DIR`; removing the main
hub, only if requested, is `uv run rnw uninstall-mod rnw_exp_hub --user-dir USER_DIR`.
The separate old generator candidate is preserved. Logs, backup and audit data
remain under ignored `local_data/wrap-continuity/`.


2026-10-25 physical seam / coast candidate ([052](052-physical-seam-and-coasts/README.md),
C293–C296): main `mod/rnw_exp_hub` **0.12.2 → 0.12.3** (all 3,254 files checked),
with a checked 3,254-file backup at ignored
`local_data/physical-seam/hub-backup-before-0.12.3/`. Added only
`mod/rnw_exp_physical_seam`, **RNW: Supercontinent MKEA**, epoch 33,
code `RNW1-081WG-1HAWD-H0XFH-T0060-60840-3C082-243AG-0C700-KHRXR`:
826 checked files including metadata, 824 non-metadata files, digest
`883e1abf7c211cdcefe2e6b822b1d56fcb5c3078ef23f13959094477197a0e7b`.
It retains the observed seed/shape/density/empire parameters, fixes noise precision
and includes eight periodic heightmap placements. Nine profile-root hashes,
4,052 other-mod file size/time records and three old folders are preserved.
The active old world is not patched; the hub carries no game assets. No game
launch, process control, playset/save/library edit or installation-file write.
Installed Windows self-test and precision sample pass; engine appearance remains
unverified. Exact removal with EU5 closed: `uv run rnw uninstall-mod
rnw_exp_physical_seam --user-dir USER_DIR`; main hub removal, only if wanted:
`uv run rnw uninstall-mod rnw_exp_hub --user-dir USER_DIR`. The local backup and
prepared candidate remain outside the profile.


2026-10-25 reinstallation at the owner's explicit request (C297): the profile no
longer contained `mod/rnw_exp_physical_seam`. Reinstalled **RNW: Supercontinent MKEA**,
0.12.3 / epoch 33, from the verified local export through an incoming copy and one
rename. All **826** installed files match the export manifest; non-metadata digest
remains `883e1abf7c211cdcefe2e6b822b1d56fcb5c3078ef23f13959094477197a0e7b`.
Nine profile-root hashes, 6,528 existing mod-file size/time records and three old
mod folders are preserved. A retired old world inside `.rnw-install/retired/`
was deliberately left untouched; no installer sweep was run. No game launch,
process control, playset, save, library or generator update. Exact removal with
EU5 closed remains `uv run rnw uninstall-mod rnw_exp_physical_seam --user-dir USER_DIR`.
Evidence: ignored `local_data/physical-seam/reinstalled.json`.


2026-10-25 TR46 removed-coast correction ([054](054-tr46-coast-footprint/README.md),
C304–C308): with EU5 closed, added exactly one visible world folder,
`mod/rnw_exp_tr46_coast`, **RNW: Continents 56AP**, generator **0.12.4 / epoch 34**,
code `RNW1-040XN-DR20S-1RQ4T-Z0060-801CM-6D0`. All **827** mod files, metadata
included, match the verified export; the 825-file non-metadata digest is
`b8a8417db97aec4e429d034b854f73575c3be296a5e57d5eadc5c175b958a853`.
This retains TR46's exact seed and settings and corrects the old coast's offshore
height/material and water-colour/foam footprint. It does not repair the dateline
crack or river serialization, and its appearance has not been observed in game.

Updated the existing main `mod/rnw_exp_hub` **0.12.3 → 0.12.4**, all **3,254**
files hash-verified against the final Windows package, with package and metadata
versions matching. The old generator's 3,254 files have a checked backup outside
the profile at ignored `local_data/tr46-boundary/hub-backup-before-0.12.4/`.
The swap also retains the old hub at
`mod/.rnw-install/retired/rnw_exp_hub_before_coast_0124/`; existing retired
content was not swept. The generator hub contains no game content.

Nine existing profile-root files retain hashes; 4,061 other-mod files retain
sizes and modification times; all three prior visible mod folders remain.
Original TR46, saves, playsets, settings and library records were preserved.
No game launch, process control or publication. Evidence and exact installed
paths: ignored `local_data/tr46-boundary/installed.json`.
Exact candidate removal, with EU5 closed: remove only the profile folder
`mod/rnw_exp_tr46_coast/`. Do not sweep other retired worlds. The generator can
be restored from the verified external backup if separately requested; no
rollback or removal was performed here.


2026-10-25 wrapped river serialization ([055](055-wrap-river-raster/README.md),
C309–C312): added new `mod/rnw_exp_tr46_rivers`, **RNW: Continents R7SE**,
version **0.12.5 / epoch 35**, code
`RNW1-040XN-DR20S-1RQ4T-Z0060-A01VN-AKG`. All **827** mod files match the
verified export; its 825-file nonmetadata digest is
`b392f2c9a5f29425f6765cdb2b43e84326af89697186a1a0ffdac22da95b972b`.
Only rivers.png differs from the 0.12.4 coast candidate, at 12 drawing markers.
No existing TR46 world or save was rewritten.

Updated main `mod/rnw_exp_hub` **0.12.4 → 0.12.5**, all **3,256** files checked
against the final Windows package. The old 3,254-file hub has a checked external
backup at ignored `local_data/tr46-boundary/hub-backup-before-0.12.5/` and is
retained at `mod/.rnw-install/retired/rnw_exp_hub_before_river_0125/`. No retired
sweep. Nine profile-root hashes, 8,142 other-mod file size/time records and all
five prior mod-directory entries (including the hidden staging directory) are
preserved. Playsets, settings, saves and library records are untouched.

A later owner session left an unterminated debug log: the log-only session helper
reports `played`, but repeated live-process checks find no EU5 or Wine process.
Installation uses that live absence; the stale log is not rewritten. The later
session's logs were copied separately under ignored
`local_data/tr46-boundary/later-session-20261025-1637/`; they are not substituted
for the original TR46 campaign evidence. No game launch or process control.
Exact installation audit: ignored `local_data/tr46-boundary/rivers-installed.json`.
Removal, with EU5 closed: remove only `mod/rnw_exp_tr46_rivers/`. Restoring the
old hub from the checked backup is a separate action; no rollback was performed.


2026-10-25 primary terrain wrap ([056](056-primary-terrain-wrap/README.md),
C313–C316): with EU5 closed (log and live-process checks agree), added new
`mod/rnw_exp_tr46_terrain`, **RNW: Continents KUIG**, generator **0.12.6 / epoch
36**, code `RNW1-040XN-DR20S-1RQ4T-Z0060-C05RD-5A0`. All **835** mod files,
metadata included, match the export; its 833-file nonmetadata digest is
`9b5a912ec9908dba4969164896b3a85844a151eeee53eecd8f8e1934cf15c3d2`.
It keeps the exact TR46 seed/settings and the 0.12.4 coast / 0.12.5 river fixes,
and uses padded primary heightmap sources across the boundary. Its rendered
seam remains unobserved; this is an offline-verified candidate.

Updated the main `mod/rnw_exp_hub` **0.12.5 → 0.12.6**, all **3,256** files
hash-verified against the Windows package, with matching source/dependency/
package/metadata versions. The old hub has a verified 3,256-file external backup
at ignored `local_data/tr46-boundary/hub-backup-before-0.12.6/` and is retained
at `mod/.rnw-install/retired/rnw_exp_hub_before_terrain_0126/`. No retired sweep.
Nine root-file hashes, 12,223 other-mod size/time records and six prior directory
entries remain exact. All prior worlds, saves, playsets, settings and library
records are preserved; no game launch or process control was performed.

Exact local audit: ignored `local_data/tr46-boundary/terrain-installed.json`.
Removal, with EU5 closed: remove only `mod/rnw_exp_tr46_terrain/`. Restoring the
old hub is a separate action; no rollback or removal was performed here.

2026-10-25 maritime geography ([057](057-local-sea-routes/README.md), C317–C320):
with EU5 closed (log and live-process checks agree), added new
`mod/rnw_exp_tr46_maritime`, **RNW: Continents BU2A**, generator **0.12.7 / epoch
37**, code `RNW1-040XN-DR20S-1RQ4T-Z0060-E02AN-B0G`. All **835** mod files
match the export, metadata included. Its 833-file nonmetadata digest is
`9bea353cf4d9b7ee7fee6500c944e45c39cd5e23b57454299fa61edf6d41746e`.
The exact TR46 seed/settings retain full mainland wrap and the coast/river/
terrain corrections, with local sea routes, connected closed-water zoning and
access-preserving script replacements. Engine navigation/voyage appearance
remains unobserved.

Updated main `mod/rnw_exp_hub` **0.12.6 → 0.12.7**, all **3,258** files
hash-verified against the Windows package and its source/dependency/metadata
versions. The previous **3,256** files are checked in the external ignored
`local_data/tr46-maritime/hub-backup-before-0.12.7/` and retained at
`mod/.rnw-install/retired/rnw_exp_hub_before_maritime_0127/`. No retired sweep.
Nine profile-root hashes, 16,314 other-mod file size/time records and seven
prior directory entries remain exact. Existing worlds, saves, playsets, settings
and library records are preserved. No game launch or process control.

Exact local audit: ignored `local_data/tr46-maritime/installed.json`.
Removal, with EU5 closed: remove only `mod/rnw_exp_tr46_maritime/`. Restoring
the old hub is a separate action; no rollback/removal was performed here.


2026-10-25 impassable highlands ([058](058-impassable-highlands/README.md), C321–C324):
with EU5 closed (log/live checks agree), added new `mod/rnw_exp_tr46_highlands`,
**RNW: Continents LSI3**, **0.12.8 / epoch 38**,
`RNW1-040XN-DR20S-1RQ4T-Z0060-G00F6-A2G`. All **835** files hash-verified;
833 nonmetadata files digest
`69cafca4b98adfcfaa8fd0fec8ea352be9ce0a6fb851ab5c9dbfdf77df1b6392`.
It retains exact TR46 seed/settings, the prior maritime/coast/river/wrap fixes,
and adds compatible impassable units and mountain height detail. Administrative
regrouping also rebinds generated native culture/religion and dependent setup;
this is a new start, not a modification of the original observer world/save.
Final game appearance remains unobserved.

Updated main `mod/rnw_exp_hub` **0.12.7 → 0.12.8**, **3,262** files checked
against the Windows package and source/dependency/metadata versions. The old
**3,258** files are externally backed up under ignored
`local_data/tr46-highlands/hub-backup-before-0.12.8/` and retained at
`mod/.rnw-install/retired/rnw_exp_hub_before_highlands_0128/`. No retired sweep.
Nine root-file hashes, 20,405 other-mod size/time records and eight prior folder
entries are preserved. Existing worlds, saves, playsets, settings and library
records remain intact. No game launch, process control or publication.

Exact audit: ignored `local_data/tr46-highlands/installed.json`.
Removal with EU5 closed: remove only `mod/rnw_exp_tr46_highlands/`; hub rollback
is a separate action, not performed. The final full check still has 18 unrelated
Workshop-text failures from `0735263`; all map tests and local reproduction pass
(058 records the precise scope).

2026-10-25 continuous Tordesillas longitude ([062](062-tordesillas/README.md), C341–C344):
with EU5 closed (log and live-process checks agree), added new `mod/rnw_exp_tr46_treaty`,
**RNW: Continents QW6O**, **0.12.9 / epoch 39**,
`RNW1-040XN-DR20S-1RQ4T-Z0060-J01KM-KKG`. All **840** files hash-verified;
836 nonmetadata files digest
`33ef2ed83f6e12cb6d074793bf274dfc492c967ea68bcfdcb3499ce299cf64bd`.
It retains exact TR46 seed/settings, the prior highlands/maritime/coast/river/wrap fixes,
and adds continuous New World longitude coordinates across the raster seam for Tordesillas
side selection, line moves, side-swap estimates, map shading and final province claims.
All 831 other nonmetadata files (geography, terrain, rivers, countries, pops, diplomacy)
are byte-identical to the previous candidate. Final game appearance and treaty events
remain unobserved.

Updated main `mod/rnw_exp_hub` **0.12.8 → 0.12.9**, **3,264** files checked
against the Windows package and source/dependency/metadata versions. The old
**3,262** files are externally backed up under ignored
`local_data/tr46-treaty-fix/hub-backup-before-0.12.9/` and retained at
`mod/.rnw-install/retired/rnw_exp_hub_before_treaty_0129/`. No retired sweep.
Nine root-file hashes, 24,498 other-mod size/time records and nine prior folder
entries are preserved. Existing worlds, saves, playsets, settings and library
records remain intact. No game launch, process control or publication.

Exact audit: ignored `local_data/tr46-treaty-fix/installed.json`.
Removal with EU5 closed: remove only `mod/rnw_exp_tr46_treaty/`; hub rollback
is a separate action, not performed.

2026-10-26 map object VFX locator completion ([tr46-observer-audit](../docs/research/tr46-observer-audit.md), C348):
with EU5 closed (process check confirmed), added new `mod/rnw_exp_tr46_vfx`,
**RNW: Continents 3TTE**, **0.13.1 / epoch 40**,
`RNW1-040XN-DR20S-1RQ4T-Z0060-J01KM-KKG` (same TR46 seed/settings). All **840** files
hash-verified. It retains all previous geography, terrain, relief, river, maritime, and
Tordesillas wrap fixes, and supplies the 21 missing `vfx` locators for `rnw_ocean_*`
locations in `generated_locators_vfx.txt` (30,565 locations total, 100% complete).
Updated main `mod/rnw_exp_hub` **0.12.9 → 0.13.1** via `packaging/hub.py --replace`
and `rnw install-mod --replace`. Existing worlds (`rnw_exp_tr46_treaty` and prior),
playsets, settings, saves and library records are preserved. No game launch or process control.
Removal with EU5 closed: `uv run rnw uninstall-mod rnw_exp_tr46_vfx --user-dir USER_DIR`.

2026-10-26 generator GUI update (owner request: "Обнови установленный генератор в игру"):
updated main `mod/rnw_exp_hub` (version **0.13.1**, **3,264** files) in the normal profile with the latest generator interface improvements from commit 59a052c (preview zoom and drag fix on World tab, About dialog with links and translations across all eleven languages). Built via `packaging/hub.py --replace` and installed via `rnw.app.install.install(..., replace=True)`. All 3,264 installed files match `dist/rnw_exp_hub` (19 files updated, 3,245 identical). The prior hub is backed up byte for byte outside the profile at ignored `local_data/hub-update-20261026/hub-backup-before-gui-update/` (3,264 checked files). All 9 profile-root hashes and 1,639 other-mod file size/time records across the two existing worlds (`rnw_exp_world_657q5j3q3n` and `rnw_exp_world_dsnlfhrxqb`) are preserved; no playset, save, or library record changed. The installed Windows generator passes its offscreen window/native/world-code self-test under isolated Wine (`Random New World 0.13.1: window, native kernels and world codes work`). No game launch or process control.


2026-10-26 completed ocean courses ([064](064-ocean-course-ends/README.md), C349–C352):
with EU5 closed (logs and live check), installed new `mod/rnw_exp_657q_lanes`,
**RNW: Supercontinent EVXP**, **0.13.2 / epoch 41**, same seed/settings as 657Q,
`RNW1-081RF-FZCZT-X8CJN-T006G-40860-2AG63-YG1W8-8G3GH-149XR-08TM0-33AGE-Y`.
All **820** installed files hash-verified. The owner's revealed-world preference
is retained; 818 nonmetadata files have digest
`2b9d21108311b1aa441313e63a7e093a94a32ce36115a7dab767c9c4cb60d196`.
The canonical covered export has 838 nonmetadata files, digest
`cc1ba4e7fe06c9cf11a15c5a6831057eb3e9671fbc71f8e3ee7b8d86fcac24ec`.

Updated only generator hub `mod/rnw_exp_hub` **0.13.1→0.13.2**, all **3,264**
files verified, including source/package/metadata versions. Prior hub is backed
up byte for byte at ignored `local_data/657q-lanes/hub-backup-before-0.13.2/`
and retained at `mod/.rnw-install/retired/rnw_exp_hub_before_lanes_0132/`;
no retired-folder sweep. Windows offscreen self-test and lane parity pass.
Preserved all **1,639** other-mod file size/time records across the original
657Q and DSNL worlds, **nine** profile-root hashes and **seven** library records.
No existing world, save, playset, setting or library entry was changed. No game
launch, process control or publication. Exact audit: ignored
`local_data/657q-lanes/installed.json`.

Removal with EU5 closed: remove only `mod/rnw_exp_657q_lanes/`, or use
`uv run rnw uninstall-mod rnw_exp_657q_lanes --user-dir USER_DIR`.
Hub rollback is a separate action, not performed.

2026-10-26 EVXP library-registration correction (C353): moved only the
unreferenced `mod/rnw_exp_657q_lanes/` to standard library folder
`mod/rnw_exp_world_rbsvu4fogp/` and registered the verified bundle, atlas,
previews, code and record in the active generator library. Display name stays
**Supercontinent EVXP**, version 0.13.2 / epoch 41. All 820 files checked;
only metadata id changed. Original 657Q/DSNL, seven prior library records,
4,903 other-mod size/time records and nine profile-root hashes preserved.
No save/playset/settings/map change or game launch.
Updated removal: `uv run rnw uninstall-mod rnw_exp_world_rbsvu4fogp --user-dir USER_DIR`.
Audit: ignored `local_data/657q-library/registered.json`.

2026-10-26 automatic installed-world recovery ([065](065-installed-world-recovery/README.md), C354–C356):
updated only `mod/rnw_exp_hub` **0.13.2→0.13.3**. All **3,266** installed files
hash-verified against `build/windows/world-recovery-installed/rnw_exp_hub`;
all Python sources, type stubs and translation catalogs match the current source.
The first source guard stopped before profile writes when a concurrently saved
maps-panel change differed; the final package includes that fix and passes its
Windows offscreen self-test and recovery parity.

Prior **3,264-file** hub is backed up byte for byte under ignored
`local_data/world-recovery/hub-backup-before-0.13.3/` and retained at
`mod/.rnw-install/retired/rnw_exp_hub_before_recovery_0133/`; no retired sweep.
The immediate installation baseline had **one library record**, **820 files**
in the existing EVXP mod and **nine profile-root files**; all remain exact.
These counts describe that snapshot. No map mod was created, renamed, removed
or edited by this update. Original EVXP is still `rnw_exp_world_rbsvu4fogp`.
A subsequent read-only check sees an independently generated native 0.13.3 world
with a matching 29-file recovery receipt. No game launch, process control,
playset/settings/save change or publication. Audit: ignored
`local_data/world-recovery/installed.json`.
Hub rollback is a separate action, not performed; EVXP removal stays as above.
