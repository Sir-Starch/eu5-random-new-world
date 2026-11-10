# Installation history

These are dated installation, replacement and removal records, not a declaration
that every listed folder still exists. Inspect the filesystem for current state;
an old removal command is not an instruction to delete anything now. Current hub
identity is `sirstarch.randomnewworld` in local folder `rnw_exp_hub` (C438); the
actual Workshop download and separate local library were checked in C441.

2026-11-10, **1.2.1 hotfix / epoch 62 — market centres only where the plan puts them** (C527).
[V-EXEC] From `6fc23b7`, installed **`mod/rnw_exp_world_xmin7loaib`** ("Custom world XMIN") in the existing
Windows/Proton profile: code `RNW1-082JH-V212F-K325Z-E0410-20R10-2B020-N676J-G`, the code of world 3QFN
(`rnw_exp_world_3qfnncn4ld`, made by 1.2.0) re-encoded by generator 1.2.1, so the same land, peoples and
countries under a new world id. Its 127 generated countries hold 18 market centres and no exchange
partner a market of its own; the 1.2.0 world has 115 markets and 113 towns. The installed 1.2.0 worlds
are untouched (3QFN stays); the new folder carries its own library record. `make check` passes (3,137 Python tests,
19 optional skips, 29 Rust tests) and the installed-game reference check reproduces `f454b5f5` (884
files). The standard updater built and self-tested the hub under Wine (window, native, code, shell and
bridge) and installed it, retaining `.rnw-hub-backups/1.2.0-1794273869956681909`. Candidate:
`local_data/hub-updates/1.2.1-1794273812448306150/rnw_exp_hub`; Windows wheel SHA-256:
`f14b7ec210e23cff1794ee2ba7ce9f2f2a4b4bf3a62eb45df982eb6dbd34862b`; window
`dbe64c4ec81ed8742cbaedcd53c1b5219db98cb54a28e9ce78e1dc3dbaa0e63b` (rebuilt for 1.2.1, so a new hash
to scan at publication); launcher unchanged (`49674400…6932`). No EU5 launch/control, playset, save or
preference edit.

2026-11-08, **1.2.0 development / pending epoch 61 — steady time left during generation**.
[V-EXEC] Installed the generator-only hub from `6792916` in the existing Windows/Proton profile. The
ETA no longer cycles from 3:10 to 3:00 and back while a world is generated (vanilla reads after the
world in the forecast graph, pace-only small corrections, timing schema 2; see
[GUI design](../docs/gui-design.md)). `make check` passes (3,092 Python tests, 17 optional skips, 29
native Rust tests). World bytes are unchanged, so candidate L is reused. The standard updater built
and self-tested the hub under Wine (window, native, code, shell and bridge) and installed it,
retaining `.rnw-hub-backups/1.2.0-1794173130189934084`. Candidate:
`local_data/hub-updates/1.2.0-1794173077277333068/rnw_exp_hub`; Windows wheel SHA-256:
`36fa085d4c527e9586d34f33827a9801f5f09771d2747f65ee446cdbe5a32582`. `desktop/` is unchanged. No EU5
launch/control, playset, save or preference edit.

2026-11-08, **1.2.0 development / pending epoch 61 — candidate L, treaties within the diplomatic capacity** (C523).
[V-EXEC] From `f980833`, installed **`mod/rnw_exp_world_fcyp6eay6y`** ("ATDT candidate L (treaties within
capacity)") in the existing Windows/Proton profile: code `RNW1-08396-6JJMB-3X6KF-X0410-00813-C16WD-58`, candidate
K's code with its resources rolled again, so ATDT's land, peoples and countries under a new world id. Its generated
countries hold 12 alliances and 14 given guarantees (K: 29 and 21); the highest reckoned upkeep is 5.98 (K: 37.8,
nine countries over the game's limit). `make check` passes (3,088 Python tests, 17 optional skips, 29 native Rust
tests) and the installed-game reference check reproduces `a5c167c5`. The staged installer refused any existing
target; all 911 files match the prepared mod, both libraries hold the record, and the 19 other mod folders and 9
profile-root files are unchanged. The standard updater built and self-tested the hub under Wine (window, native,
code, shell and bridge) and installed it, retaining `.rnw-hub-backups/1.2.0-1794171779707176259`. Candidate:
`local_data/hub-updates/1.2.0-1794171728130281579/rnw_exp_hub`; Windows wheel SHA-256:
`490d54c089f0b84da5aff7148c590b28bc5ae7ec0491e18cd632af28a7cb2595`. `desktop/` is unchanged. No EU5
launch/control, playset, save or preference edit.

2026-11-08, **1.2.0 development / pending epoch 61 — candidate K, laws the game accepts** (C520–C522).
[V-EXEC] From `7982a91`, installed **`mod/rnw_exp_world_feajb6bim5`** ("ATDT candidate K (laws the game
accepts)") in the existing Windows/Proton profile: code `RNW1-08396-6JJMB-3X6KF-X0410-00813-C0X2X-P6`, the
owner's world ATDT (`rnw_exp_world_atdtnjyqkq`) with its resources rolled again, so the same land, peoples
and countries under a new world id. Its 51 generated monarchies of level 2 write cultural traditions and
slave conversion and no longer feudal de jure law or royal court customs; its 31 republics no longer write
the republican foundation; theocracies and level-1 monarchies are unchanged (Monahiton, RMP: slave
conversion, civil society). `make check` passes (3,086 Python tests, 17 optional skips, 29 native Rust
tests) and the installed-game reference check reproduces `5ded0387`. The staged installer refused any
existing target; all 911 files match the prepared mod, both libraries hold the record, and the 18 other
mod folders and 9 profile-root files are unchanged. The standard updater built and self-tested the hub
under Wine (window, native, code, shell and bridge) and installed it, retaining
`.rnw-hub-backups/1.2.0-1794167456059719272`. Candidate: `local_data/hub-updates/1.2.0-1794167408173755356/rnw_exp_hub`;
Windows wheel SHA-256: `717e19d635d630cf2bff30d80e59499f708fb117cfccd574645276fee2bd7b23`. `desktop/` is
unchanged, so the source window was not rebuilt. No EU5 launch/control, playset, save or preference edit.

2026-11-08, **1.2.0 development / pending epoch 61 — Total Chaos names and settings redraw**.
[V-EXEC] From `1e2be53`, the automatic name keeps **Total Chaos** for an untouched draw and
becomes **Custom world** after manual settings changes; naming provenance survives codes,
imports and new seeds without entering generation settings. Both windows have **Randomize
settings again**, keeping the seed. `make check` passes (3,083 Python tests, 17 optional skips,
29 native Rust tests); desktop types, 28 interface tests, five shell tests, the Linux window
build and the source/window self-tests pass. The standard updater built, self-tested under
Wine and verified the installed generator-only hub in the existing Windows/Proton profile,
retaining `.rnw-hub-backups/1.2.0-1794125024650911525`. Candidate:
`local_data/hub-updates/1.2.0-1794124971153988827/rnw_exp_hub`; Windows wheel SHA-256:
`b5b111f38a5ab3dedf35a19da75f7b460ad960788e24ee112fc0808a3059f1cd`.

The owner identified existing world **K67E** as an untouched Chaos draw (older codes have no
origin). Its library name, installed metadata and recovery receipt now say **Total Chaos K67E**;
its code is unchanged, and all 863 nonmetadata files are hash-preserved. Previous metadata and
record: ignored `local_data/chaos-naming-20261108/`. World bytes are unchanged, so this candidate
is reused. No EU5 launch/control, save or playset edit.

2026-11-08, **1.2.0 development / pending epoch 61 — responsive world switching**.
[V-EXEC] Installed the generator-only hub from `4a704dc` in the existing Windows/Proton profile.
Atlas preparation runs on a cancellable background worker; state/comparison listing reads file
metadata, and the bridge/viewer retain the four most recently used maps. The bounded replay on
13 copied library worlds and its timing scope are recorded in [the window guide](../docs/gui-design.md#9-the-tauri-window).
`make check` passes (format, lint, strict types, 3,070 Python tests with 17 optional skips, 29 native
Rust tests); the final focused suite passes all 41 bridge/library regressions, including the
additional concurrent game-change regression. Desktop types, 27 interface tests and five shell
tests pass. The source window was rebuilt with `npx tauri build --no-bundle --ci`; source and
Windows/Wine window, native, code, shell and bridge self-tests pass. The standard updater verified
and installed the hub, retaining `.rnw-hub-backups/1.2.0-1794123922216493721`. Candidate:
`local_data/hub-updates/1.2.0-1794123868987720128/rnw_exp_hub`; Windows wheel SHA-256:
`a4c47c278c154bd7e171e661698e7f1944b1a3c8c9e3c177b994ea432d4f2006`.
World bytes are unchanged, so existing candidates are reused. No EU5 launch/control, playset,
save or preference edit. The browser interaction review was unavailable (CUA host unavailable);
the mounted-viewer DOM regression and the real Python protocol replay establish their stated scope.

2026-11-08, **1.2.0 development / pending epoch 61 — substantial inland seas; small basins as lakes**.
[V-EXEC] From `d61b363`, installed **`mod/rnw_exp_world_qne7iu7ztf`** ("Inland water fix") in the
existing Windows/Proton profile, with records in both generator libraries. It is the reported failing
custom continents seed `2941179964665144373`: all 211 pixels of the former orphan are now lakes;
eight substantial closed seas (64,674–472,736 pixels, 85 zones) retain ports and inland-sea topography
without ocean currents. The independent written-map audit and normal export validators pass. All
892 installed files match the prepared candidate (881 nonmetadata files, SHA-256 `6ef512a7ac68eff8c7de63bc2b647c829a57e90f5d2297339fdcdd0e9fca2625`);
15 other mod folders and nine profile-root files are hash-preserved. `make check` passes (3,066 Python
tests, 17 optional skips; 29 Rust tests, format, lint and strict types), as do 15 installed-input tests
(two optional skips) and source window/native/code/shell/bridge self-tests. The reference export keeps
884 files and digest `7acf24cd`. The standard updater installed the generator-only hub after its
Windows/Wine self-tests, retaining `.rnw-hub-backups/1.2.0-1794121221262536123`. Candidate:
`local_data/hub-updates/1.2.0-1794121155450062438/rnw_exp_hub`; Windows wheel SHA-256:
`076c2552fac4c240658f42597222f630155a90c84d2efc784ee08eba8c86fe47`. No EU5 launch/control,
playset, save or preference edit. The [basin policy and reproduction](../docs/sea-geography.md)
distinguish this offline verification from engine loading.

2026-11-08, **1.2.0 development / pending epoch 61 — preserve the map during background progress**.
[V-EXEC] The Tauri atlas-loading effect compares world identity and language before resetting
its session. A Happy DOM regression mounts the actual viewer with a synthetic atlas, opens the
Society tab and keeps the same country card and highlight across fresh progress snapshots;
switching worlds and language still reloads. Desktop types, all 22 interface tests and five shell
tests pass; `make check` passes (3,055 Python tests, 17 optional skips; 29 native tests;
format, lint and strict types). The source window was rebuilt with `npx tauri build --no-bundle --ci`.
Source and Windows/Wine window, native, code, shell and bridge self-tests pass. The standard
updater installed the generator-only hub in the existing Windows/Proton profile and retained
its predecessor at `.rnw-hub-backups/1.2.0-1794119857578106614`. Candidate:
`local_data/hub-updates/1.2.0-1794119782357455231/rnw_exp_hub`; Windows wheel SHA-256:
`0bbae4d5d7d6b72262c08b24b6b1fedd2ef03510bf0a970f068aba15636cf767`.
World bytes are unchanged, so existing candidates are reused. No EU5 launch/control, playset,
save or preference edit.

2026-11-08, **1.2.0 development / pending epoch 61 — publish each completed queued world**.
[V-EXEC] The shared controller refreshes the library after each successful queued world,
before starting the next. A gated synthetic regression verifies publication while the next
world is still running, installation, notification and selection preservation. `make check`
passes (3,055 Python tests, 17 optional skips; 29 Rust tests; format, lint and strict types). Source and
Windows/Wine window, native, code, shell and bridge self-tests pass. The standard updater
installed the generator-only hub in the existing Windows/Proton profile, retaining the former
hub at `.rnw-hub-backups/1.2.0-1794118914264797681`. Candidate:
`local_data/hub-updates/1.2.0-1794118854086507986/rnw_exp_hub`; Windows wheel SHA-256:
`1f3eaa2474a439d92e30a441b57dd931d160bcd3690ccf317e17b8f7b7084118`.
World bytes and `desktop/` are unchanged: existing candidates are reused, with no new world
or source-window rebuild. No EU5 launch/control, playset, save or preference edit.

2026-11-08, **1.2.0 development / pending epoch 61 — candidate J, the owner's RLTM with laws, names and
the story** (C514–C517). [V-EXEC] Installed **`mod/rnw_exp_world_7qoul55qjp`** ("RLTM candidate J (laws,
names, story)") in the existing Windows/Proton profile: code `RNW1-081YN-N7GXQ-AGMC7-Y0410-00833-AG0C6-R196G-0CZX0-3W`,
the owner's world RLTM (`rnw_exp_world_rltmruw7gq`) with its resources rolled again, so the same land,
peoples and countries under a new world id, generated at `12cd63b`. Unichita (BQU) writes feudal de jure
law, royal court customs, slave conversion and cultural traditions; the world writes 128 memory-event
entries and names its formables' territories. RLTM itself, regenerated from its code at `12cd63b` into an
ignored folder, differs from the installed one only in its 22 localization files and `10_countries.txt`.
The staged installer refused any existing target. All 912 files match the prepared mod, both libraries hold
the record, and the 4 other mod folders and 9 profile-root files are unchanged. The standard updater
installed hub 1.2.0 with the generator of `12cd63b` after its Wine window, native, code, shell and bridge
self-tests and kept the former hub at `.rnw-hub-backups/1.2.0-1794115184121315550`. Windows wheel SHA-256:
`01ede982e52265f8ea9413c16835f56f9b4befff2c1a5a030351ba9025d42cf5`. The source-run Tauri window was
rebuilt (`npx tauri build --no-bundle --ci`) for the new Society and Chronicle tabs. No playset, save or
preference was edited; the agent did not launch or control EU5.

2026-11-08, **1.2.0 development / pending epoch 61 — candidate I, the D34 history** (R6 step 5).
[V-EXEC] Installed **`mod/rnw_exp_world_lk3aao5c5f`** ("History 1.2 candidate I (D34 history)") in the
existing Windows/Proton profile: code `RNW1-080J3-M4P7S-R656Y-R0410-00830-3SG46-R48Y1-G5YF8-BM`,
candidate H's code with the resources rolled again (candidate F's land, a new world id), generated at
`ba101a0` (the source of `94bf99b`: D33 classifier order and lord margin 6, unrest slope 350). The
staged installer refused any existing target. All 912 files match the prepared mod, both libraries
hold the record, and the 13 other mod folders and 9 profile-root files are unchanged. The installed-game
reference export reproduces the pending golden (884 files, `79dbf588`). Its `countries` layer: 806
countries on 7,282 land locations, 3,321 of them without an owner (a patchwork of small states with a
few larger realms). The standard updater installed hub 1.2.0 with the same generator after its Wine
window, native, code, shell and bridge self-tests and kept the former hub at
`.rnw-hub-backups/1.2.0-1794099700748274200`. Windows wheel SHA-256:
`def0c839a860b37027ae239c5bcdcf631db033f45cbd6135b8e361a88c02cfb4`. The source-run Tauri window needs
no rebuild (`desktop/` is unchanged since `e46d7a2`). No playset, save or preference was edited; the
agent did not launch or control EU5. The 24 held-out starts keep no world files, so no contact sheet
of them was drawn; the checks Q1–Q2 are diagnostics under D34.

2026-11-07, **1.2.0 development / pending epoch 61 — hub with the faster history engine**
(C506). [V-EXEC] No world was installed: the change writes no other world bytes (the reference
world reproduces `e1e4699e` with 31 threads and with one), so candidates C–H stay as they are.
The standard updater installed hub 1.2.0 with the generator of `823b662`, the source of the
renewed R6 freeze, after its Wine window, native, code, shell and bridge self-tests, and kept
the former hub at `.rnw-hub-backups/1.2.0-1794026228349261286`. Windows wheel SHA-256:
`1b0406b6e2caf04085fa2f12478db27f395191de69c66342b4576ef8730b11ab`. No playset, save or
preference was edited; the agent did not launch or control EU5.

2026-11-07, **1.2.0 development / pending epoch 61 — hub with the faster sketches and world**
(C505). [V-EXEC] No world was installed: the change writes no other world bytes (the reference
world reproduces `e1e4699e`), so candidates C–H stay as they are. The standard updater installed
hub 1.2.0 with the generator of `0545535` after its Wine window, native, code, shell and bridge
self-tests, and kept the former hub at `.rnw-hub-backups/1.2.0-1794015395777423135`. Windows wheel
SHA-256: `559859f25d283bfd92f4580cf1c0aead07c495c8deb80e7d5cdd6dfd07ccf00f`. The source-run Tauri
window needs no rebuild (its interface is unchanged). The generator's land cache now keeps four
continents, 24 sketches and four canvases; the next generation prunes older entries in the data
folder it runs from. No playset, save or preference was edited; the agent did not launch or
control EU5.

2026-11-06, **1.2.0 development / pending epoch 61 — candidate H, regions named by their peoples**
(W8 follow-up, C503). [V-EXEC] Installed **`mod/rnw_exp_world_3bzsntlyjn`** ("History 1.2 candidate H
(regions named by their peoples)") in the existing Windows/Proton profile: code
`RNW1-080J3-M4P7S-R656Y-R0410-00830-3SG46-R38Y1-G5NRC-XR`, candidate G's code with the resources rolled
again (so candidate F's land, with a new world id), generated at `e46d7a2`. Its written Russian
`region_names` calls `alaska_region` *Кехттигене* and `canada_region` *Синкачуа*. The Tauri window
was served by vite on a scratch copy of the candidate's library and driven in Russian in headless
Chromium. It labelled the regions with those names, and its card for location *Паца* reads
*Якконхна · Кехттигене* / *По правилам игры — регион «Аляска»*, as in the written files. The scratch
library was deleted. The staged installer refused any existing target. All 912 files match the
prepared mod, both libraries hold the record, and the 12 other mod folders and 9 profile-root files
are unchanged. The standard updater installed hub 1.2.0 with the generator of `e46d7a2` after its
Wine window, native, code, shell and bridge self-tests, and kept the former hub at
`.rnw-hub-backups/1.2.0-1794000273352878466`. Windows wheel SHA-256:
`bc2799e6310da9056b30d18f55b3c48104f118670c5818e92ad1ea66187e68bb`. The source-run Tauri window
(`desktop/src-tauri/target/release/random-new-world`) was rebuilt with `npx tauri build --no-bundle
--ci`. Candidates C–G stay installed. No playset, save or preference was edited; the agent did not
launch or control EU5. NOT GAME VALIDATED.

2026-11-06, **1.2.0 development / pending epoch 61 — candidate G, regions as the Americas lie**
(W8, C502: north-to-south subcontinent bands, regions by place first). [V-EXEC] Installed
**`mod/rnw_exp_world_lhlehi4i3d`** ("History 1.2 candidate G (regions as the Americas lie)") in the
existing Windows/Proton profile: code `RNW1-080J3-M4P7S-R656Y-R0410-00830-3SG46-R28Y1-G56S2-30`, made
from candidate F's code with the resources rolled again, so it has F's land and a new world id. It was
generated at `74b936b`. Its atlas puts Alaska in the north-west, Canada in the north-east, the West
Coast in the west and the East Coast in the east, with Meso- and Central America at the south of
North America, Colombia at the north of South America, La Plata at its south and Brazil on the
eastern island. In F, Central America lay beside Alaska and Colombia on that island. The staged
installer refused any existing target. All 912 files match the prepared mod, both libraries hold the
record, and the 11 other mod folders and 9 profile-root files are unchanged. The standard updater
installed hub 1.2.0 with the generator of `74b936b` after its Wine window, native, code, shell and
bridge self-tests, and kept the former hub at `.rnw-hub-backups/1.2.0-1793996994885394956`. Windows
wheel SHA-256: `3b5b87000e1bc73a2a611a89a9c3294d79b671f30e43bdd48807ea2b2550b972`. Candidates C–F stay
installed. No playset, save or preference was edited; the agent did not launch or control EU5. NOT
GAME VALIDATED.

2026-11-06, **1.2.0 development / pending epoch 61 — candidate F, frontier everywhere** (W7, C501:
`settle_the_frontier_advance` rebound to the whole New World). [V-EXEC] Installed
**`mod/rnw_exp_world_7frcq3x5oe`** ("History 1.2 candidate F (frontier everywhere)") in the existing
Windows/Proton profile: code `RNW1-080J3-M4P7S-R656Y-R040G-00830-3SG46-R18Y1-G4YZT-ZW`, the settings of
candidate E with a new seed, generated at `b1328b4`. Its written gate names `continent:america`, so all
193 of its American land countries qualify (72 would not under the vanilla regions). Candidate E's own
code regenerated at `b1328b4` (scratch, not installed: same id) differs from the installed E only by
`in_game/common/advances/3_cabinet_actions_unlocks.txt` outside `.metadata`. The staged installer
refused any existing target; 912 files match the prepared mod, both libraries hold the record, and all
10 other mod folders and 9 profile-root files are unchanged. The standard updater installed hub 1.2.0
with the generator of `b1328b4` after its Wine window, native, code, shell and bridge self-tests,
retaining the former hub at `.rnw-hub-backups/1.2.0-1793991294438766010`; Windows wheel SHA-256
`216cc0f7948814bba6c9c6f18449bd3d27aab3bf086a3ce1d968f3bf23e9ec26`. Candidates C, D and E stay
installed. No playset, save or preference edit; no EU5 launch or control by the agent. NOT GAME VALIDATED.

2026-11-06, **1.2.0 development / pending epoch 61 — candidate E, the game's measure** (plan D31:
historical opinions on the scale of their vanilla analogues, the game's river sizes in development, and
a window that shows what the game shows). [V-EXEC] Installed **`mod/rnw_exp_world_isank4awvu`**
("History 1.2 candidate E (the game's measure)") in the existing Windows/Proton profile: code
`RNW1-080KK-CJE30-JD57E-3040G-00830-3SG46-R18Y1-G5KER-2M`, the settings of candidate D with a new seed,
generated at `760c965` (the later commits change no world byte). The staged installer refused any
existing target; 913 files match the prepared mod, both libraries hold the record, and all 9 other mod
folders and 9 profile-root files are unchanged. The standard updater installed hub 1.2.0 with the
generator of `e60b77e` after its Wine window, native, code, shell and bridge self-tests, retaining the
former hub at `.rnw-hub-backups/1.2.0-1793954729662799455`; Windows wheel SHA-256
`03b93af98275afb93c3066356734255e4b053fe9decf73891cb28700f75a7005`. The source-run Tauri window was
rebuilt (`npx tauri build --no-bundle --ci`). Candidates C and D stay installed. No playset, save or
preference edit; no EU5 launch or control by the agent. NOT GAME VALIDATED.

2026-11-06, **1.2.0 development / pending epoch 61 — goals candidate D** (all of D29: N6–N9 and every
item of the plan's §22.4: adapted vanilla chains, naming choices, the fantasy layer, missions; keys
handed out by the key space). [V-EXEC] Installed **`mod/rnw_exp_world_3ccciukst2`** ("History 1.2
candidate D (goals, complete)") in the existing Windows/Proton profile: code
`RNW1-080GY-H0SM8-KPN19-P040G-00830-3SG46-R18Y1-G5YHM-DM`, the settings of candidate B with a new seed,
generated at `332c182`. It is the first candidate in which every content family is present, with no
recorded absence: 10 region realms, 4 restorations, a great league, the empire and all four
continental goals (two oceans among them), every story family including the declining centre, the
confederation council and the senior partner, and 108 memory events. All its RNW event, mission,
formable and geography scripts parse. The staged installer refused any existing target; 911 files
match the prepared mod, both libraries hold the record, and all 8 other mod folders and 9
profile-root files are unchanged. No playset, save or preference edit; no EU5 launch or control by the
agent. The standard updater installed hub 1.2.0 with this generator after its Wine window, native,
code, shell and bridge self-tests, retaining the former hub at
`.rnw-hub-backups/1.2.0-1793946916723989738`; Windows wheel SHA-256
`18080ff7ebdcac4df1fcb3a392c685a7368160c33b9df0adb9d37a779c39515c`. Candidate C (`anrfpxbsw3`) stays
installed. NOT GAME VALIDATED.

2026-11-06, **1.2.0 development / pending epoch 61 — goals candidate C** (D29, N6–N9: formable goals,
restorations, AI goals, events of the recorded past, family reforms). [V-EXEC] Installed
**`mod/rnw_exp_world_anrfpxbsw3`** ("History 1.2 candidate C (goals)") in the existing Windows/Proton
profile: code `RNW1-080QY-J4QP6-8R9H9-1040G-00830-3SG46-R18Y1-G5RZH-JR`, the settings of candidate B
(`27gtz46qpq`) with a new seed, generated at `d598f53`. It writes 9 region realms, the fantasy empire
of the continent, 3 restorations (5 fallen realms passed with their reasons), 2 nations of colonial
shores, unions, leagues, confederations and commonwealths, AI goals for every pursued formable and 110
memory events (61 lost lands, 24 kin, 19 old pacts, 6 heirs). The staged installer refused any existing
target; 907 files match the prepared mod, both libraries hold the record, and all 7 other mod folders and
9 profile-root files are unchanged. No playset, save or preference edit; no EU5 launch or control by the
agent. The standard updater installed hub 1.2.0 with the D29 generator after its Wine window, native,
code, shell and bridge self-tests, retaining the former hub at `.rnw-hub-backups/1.2.0-1793936328845191954`;
Windows wheel SHA-256 `c3bfdf26d330b83003461d97d37df4278a8f8f7b33b8ced09f186139fecba192`. NOT GAME
VALIDATED: the engine loading of the formables, the cores' casus belli, the reforms, the AI entries and
the events is for the R6 sitting.

2026-11-05, **1.2.0 development / pending epoch 61 — history candidate B** (naming and societal values).
[V-EXEC] Installed **`mod/rnw_exp_world_27gtz46qpq`** ("History 1.2 candidate B") in the existing
Windows/Proton profile: code `RNW1-080NJ-Q174Z-YVDXZ-C040G-00830-3SG46-R18Y1-G5YG2-B4`, the settings of
`frnstcvz2w` with a new seed (a world's id is a hash of its code and the build, so the same world
could not take a new folder). It is the first world whose archive keeps each country's societal values and
whose chronicle names a society that is a country by its map name. The staged installer refused any
existing target; 900 files match the prepared mod, both libraries hold the record, and all 6 other mod
folders and 9 profile-root files are unchanged. No playset, save or preference edit; no EU5 launch or
control by the agent. Checked against its written files for all 740 countries: government types,
technology levels, 59 vassal, 19 guarantee, 14 alliance and 24 rival pairs, 1,116 opinions, country
names and the seven written societal values per country all equal the archive. NOT GAME VALIDATED.
The hub (1.2.0, installed above) predates the window and presenter changes of this day.

2026-11-05, **1.2.0 development / pending epoch 61 — the audited history redesign** (R1–R6 step 1,
claim C492). [V-EXEC] Installed **`mod/rnw_exp_world_frnstcvz2w`** in the existing Windows/Proton
profile: code `RNW1-080KN-HKXKK-XB4AA-9040G-00830-3SG46-R18Y1-G5VR1-BG`, the land and peoples of the
latest installed world, now with the 1.2.0 history. The staged installer refused any existing target;
902 files (873 outside `.metadata`) match the prepared mod, both libraries hold the record, and all
5 other mod folders and 9 profile-root files are unchanged. No playset, save or preference edit; no
EU5 launch or control by the agent. Its history (60 rounds, 31,310 events): the great empire seeded
and realized (30 locations), regional powers 7 of 8, paramount 1 of 4, no league, confederation or
sacred centre was seeded. The generator marks it NOT GAME VALIDATED; the engine's load of the 1.2.0
history content has not been observed, and the held-out set (1005–1008) has not been run.

The source/native and Windows/Wine window/native/code and shell/bridge self-tests pass. The standard
updater installed the **3,530-file** generator-only hub 1.2.0, retaining the former hub at
`.rnw-hub-backups/1.1.0-1793910579640108258`. Candidate: ignored
`local_data/hub-updates/1.2.0-1793910528679676286/rnw_exp_hub`; Windows wheel SHA-256
`237ac7049194da4f27c1182131b11f8cc97aed33f274cefe0f4d728087862d46`. Unpublished 1.2.0 / pending
epoch 61.

2026-11-02, **physical strait throats and shortest trajectories on XNKG** (C467). [V-EXEC]
Installed **RNW: XNKG — narrow straits**, `mod/rnw_exp_world_akhvvjfa6f`, code
`RNW1-080KN-HKXKK-XB4AA-9040G-00850-3SG42-1N15W-1P0A7-GC160-FGW`, in the game and both libraries.
All 898 files match the candidate; 17 existing mod folders and nine profile-root files are preserved.
Its resolved settings and rolls equal original XNKG's, with unchanged defaults explicitly encoded
for a separate identity. Comparing all nonmetadata files with original XNKG finds only
`adjacencies.csv` changed. Its 11 sections exactly match an independent reconstruction from the
written location raster; the rejected candidate had 61. The Locsamsol line is a short diagonal,
the Moana/Wahilaki parallel pair and same-shore 8-pixel shortcut are absent. The full export reports
zero split cells, unreachable or cut-off generated seas, unported land and lost Old World contacts.
869 nonmetadata files, digest `4b19f0bc28d86119509153398212544689eade4e46c6896303e0694586138cb9`.

`uv sync --locked --group dev && make check` passes (2,449 Python tests, 15 optional skips;
strict types, format/lint and 23 Rust tests). The pending epoch-60 reference has two crossings,
868 files and digest `7171c89a5b179fac1fd75adae917961cbd85fa9479533031aa9a6b2bb9bf0181`,
predicted from the previous reference's written map and independently reproduced by a full fresh
installed-game export (one pass). The final long-channel duplicate regression leaves both verified
worlds' crossing bytes identical. Frozen epoch 59 is untouched. EU5 1.4.6 / build 26300913;
RNW 1.1.0 development. The final generator wheel is rebuilt with unchanged GUI/runtime binaries,
passes the Windows/Wine window/native/code and shell/bridge self-tests, and is installed by the
standard updater. Backup: `.rnw-hub-backups/1.1.0-1793577386521788430`; candidate
`local_data/strait-crossings-v2/hub-final/rnw_exp_hub`, wheel SHA-256
`438995a5545f0e61d67a2d4ff59b526fbe7e359f30b3e7b9ce74c5fd5960ee3a`.
Evidence: ignored `local_data/strait-crossings-v2/`. No agent EU5 launch/control or new engine
rendering observation; the owner's screenshots establish the preceding candidate's defects.

2026-11-02, **natural strait crossings on XNKG** (C466; placement rejected, superseded by C467).
[V-EXEC] Installed
**RNW: XNKG — strait crossings**, `mod/rnw_exp_world_a56qhjysy5`, code
`RNW1-080KN-HKXKK-XB4AA-9040G-00840-3SG42-1N3C0-MF0R2-DJ5QE`, with records in both the native
and Proton libraries. Its resolved settings, seeds and rolls equal XNKG's; an explicitly encoded
unchanged location spacing gives the candidate a separate identity. All 898 installed files match
the candidate. A comparison of every nonmetadata file with installed XNKG finds only
`in_game/map_data/adjacencies.csv` changed: all five former generated crossings remain, with 61
now written, including all three screenshot throats (17, 1 and 8 sea pixels). The other 15 mod
folders and nine profile-root files are unchanged. Output: 869 nonmetadata files, SHA-256
`faf816295c6c88d1514ab49cd124ec306842637289759f42aa5919db2bf7a979`; no split cells, unreachable
generated seas, cut-off seas, unported land or lost Old World contacts. EU5 1.4.6 / build 26300913;
RNW 1.1.0 development / pending epoch 60. The pending reference is refreshed to 868 files,
17 crossings, digest `7671b6f8…aaa58`, independently reproduced by the opt-in installed-game
reference test (one pass); epoch 59 is untouched.

Project format/lint (excluding other `.claude` checkouts), strict types, 2,437 Python tests
(15 optional skips), 23 Rust tests and the 13 installed-game read-only checks (two opt-in skips)
pass. The updated hub passed its Windows/Wine generator and window-shell self-tests. Its first
installation correctly stopped while EU5 was open; after the owner closed it, the standard updater
installed the prepared hub, retaining the previous copy at
`.rnw-hub-backups/1.1.0-1793574736007089025`. Candidate:
`local_data/hub-updates/1.1.0-1793574546523945747/rnw_exp_hub`; Windows wheel SHA-256
`35e0632260b0059a77a2ea63561e659f264bc414ae985ef78826224c156e91f9`.
Evidence: ignored `local_data/strait-crossings/`. No agent EU5 launch/control or observation of
engine rendering of the new crossings.

2026-11-01, **The Wall's width inside the land share**. [V-EXEC] Installed **RNW: The Wall NOVX** in new
`mod/rnw_exp_world_novxisa5pj`, the owner's J4VJ land (wall, seed 14046991261471717063, land 159‰,
position 100%, irregularity 100%) with the width raised from its 14% to 30%, code
`RNW1-083C5-W7G43-7GKDP-7040G-00840-2FG2G-NC091-YG1T4-X03NC-V6J`. EU5 1.4.6 / build 26300913; 1.1.0
development / pending epoch 60. 877 files in the mod folder, 18 existing world folders left in place.
Of the 894 manifest entries 847 match the installed bytes; the other 47 are what the application's
"show the New World" setting (on) withholds (selection cover, shaders, GUI), library-only files and the
revealed thumbnail. 27,593 locations; no split generated cells, unreachable generated seas, unported
land, cut-off seas or lost Old World contacts. A full export at the widest width, 44% (seed 1000), also
passes every invariant with 29,257 locations. The Wall is counted inside the land share, so a wide one
leaves few continents beside it ([terrain](../docs/terrain-biomes.md#the-wall)). Full Python checks
pass (2,414 tests, 15 optional skips; strict types, lint and formatting of the project's paths);
no native code changed. EU5 was running and was not launched or controlled; the hub was **not**
updated, because its updater stops while the game is open. Evidence: ignored `local_data/wall-width/`.

2026-11-01, **issue #7 native identity cores** (C459). [V-EXEC] Installed
**Native identity cores · 7007** in new `mod/rnw_exp_world_54bascq2vu`, code
`RNW1-081G0-00000-0006T-Z040G-00860-2AG63-YG1W8-8G3GH-149XR-08TX0-3G7VX-9`,
with records in both the native and Proton libraries. EU5 1.4.6 / build 26300913;
1.1.0 development / pending epoch 60. All 879 installed files match the prepared candidate;
868 nonmetadata files have SHA-256
`c6e0482fba56c79c482acaac00e8fe4f8810c868c40bf23fe132c3961eff163e`.
All 312 landed countries meet the existing 122‰/338-milli peasant floors (observed minima
129‰/1,391 milli), including five great empires of 70–88 locations. No split generated cells,
unreachable generated seas, unported land or lost Old World contacts. All 18 existing mod
directories and nine profile-root files were verified unchanged by the world installer.

The 1.1.0 hub passed its packaged Windows/Wine generator and window-shell self-tests and
was installed after the owner closed EU5. The first install attempt correctly stopped while
the game was open. The former hub is retained at
`.rnw-hub-backups/1.1.0-1793546784562452780`; candidate
`local_data/hub-updates/1.1.0-1793546393236476626/rnw_exp_hub`, wheel SHA-256
`6a4d976928736d4400edb2d1ee940788dd45dd67c73d43dc4e34d11a9303f0d8`.
Full checks pass (2,396 Python tests, 15 optional skips; 23 native Rust tests), as does the
read-only installed-game suite (13 tests, two opt-in skips). The refreshed pending epoch-60
reference has 870 files, digest `38aead72…9d02`, independently reproduced by the opt-in
installed-game reference test (one pass). The frozen epoch-59 reference is untouched.
Evidence: ignored `local_data/identity-core/`. No agent launch/control of EU5 or gameplay
validation; existing saves, settings and playsets are preserved.

2026-11-01, **issue #6 peasant population mix**. [V-EXEC] Installed code
`RNW1-080G0-00001-WC7Z4-T040G-00819-2G0D9-2XJC` (continents, seed 2026110106,
peasant peak 80%) in new `mod/rnw_exp_world_tsliolqa56`, with the matching local library
bundle under `~/.local/share/random-new-world/generated/`. The installed EU5 build is
1.4.6 / 26300913; the audited 1.4.5 map inputs remain compatible. Full export produced
867 files, SHA-256 `2c462ee02ad0b7aa1126f6083b72bc5c376107ce928be09f8037de0cab410264`.
The report records 6,609 inhabited locations, 44,878,394 milli-pops, and 10,136,818
milli-peasants. All 204 landed countries have peasants; the lowest serialized country
share is 277‰ (required minimum 122‰), and its least peasant count is 515 milli
(required minimum 338). EU5 was not launched; this is export evidence, not gameplay
validation. The 1.1.0 hub was rebuilt from this checkout, passed its Windows/Wine
generator and window-shell self-tests, and was installed as `mod/rnw_exp_hub` (3,478
files). The updater's EU5 process check passed. Its previous copy is retained at
`.rnw-hub-backups/1.1.0-1793544888926119831`; wheel SHA-256
`de4bb11a98df63cc9434c5cf17404e594e8fc5bee4ab7cec4df05ffe8d5ee657`. Candidate:
`local_data/hub-updates/1.1.0-1793544825184063225/rnw_exp_hub`.

2026-11-01, **issue #5 state-land target UI** (C457). [V-EXEC] Rebuilt the 1.1.0 hub from
this checkout, passed the Windows/Wine generator and window-shell self-tests, and installed
it as `mod/rnw_exp_hub` in the normal Proton profile. The installed hub has 3,478 files;
its previous 3,478-file copy is retained at
`.rnw-hub-backups/1.1.0-1793543572584125661`. Wheel SHA-256
`fc01a21b91ccd931e7a6bf3a969f64354021c96e3521a9abd82bf2a8cea528a6`. No EU5 process was
running and the game was not launched or controlled. No world mod was installed: the society
algorithm is unchanged for a resolved settings document, and the installed build 26300913
differs from the task's 26211608 reference.

2026-11-01, **thin zone remainders, on the land of the owner's The Wall J4VJ** (C456). [V-EXEC] The owner
asked whether the right thing had been fixed, because the screenshots were of J4VJ and the earlier candidates
were of QU3N. The J4VJ files in the profile (`rnw_exp_world_j4vjupn3zo`, left in place) indicate that the narrow
Pacific South location is `pacific_south_current2`, a zone of the game that the canvas trimmed to a needle (an
inference from the owner's description; see [sea geography](../docs/sea-geography.md)); the canvas now takes
such remainders. Installed
**`mod/rnw_exp_world_jslqa5uqtx`**, the land and seas of J4VJ (wall, seed 14046991261471717063) with the peoples
rolled once so that its id differs from the installed J4VJ; code
`RNW1-083C5-W7G43-7GKDP-7040G-00850-2FG27-018A6-02GZ8-0X2EG-1YXV3-T0`. Its 866 nonmetadata files have SHA-256
`06f1512a…1e2a`; 868 of the 894 manifest entries match the installed bytes (26 are selection-cover and
library-only files). 349 deep lanes, 238 with a current; zero split cells, unreachable generated seas, lost Old
World contacts, cut-off seas or land cells without port access. `pacific_south_current2` and
`atlantic_equatorial_countercurrent18` are no longer defined. Records are in the native library and the Proton
`AppData/Local/RandomNewWorld` library. Earlier candidates of the same day, including `7uwam7i5jh`, are
superseded and kept. Existing worlds, saves, settings and playsets were preserved; EU5 was not launched or
controlled.

The 1.1.0 hub was rebuilt, passed its Windows/Wine generator and window-shell self-tests and was installed over
its previous copy, retained at `.rnw-hub-backups/1.1.0-1793541873707636343` (wheel SHA-256
`7ad7465105ce1c62b351e57f36679041f3bc3d7104c3f80f83237041b35cff22`). The pending epoch-60 reference world is now a
new land of the same settings (`RNW1-081G0-00000-0KAA7-E040G-…-34JQ8-1`): the earlier land left its Caribbean
region one coastal sea cell away from the Old World boundary and failed its identity check as soon as the sea
cells changed. On build 26300913 the reference has 870 files and digest `45b91242…ea38`, reproduced by the
installed-game suite (13 passed, 2 opt-in skips) and `RNW_REPRODUCE=1`; continents 1000, archipelago 42, The
Wall 9 and islands 7 export with every sea invariant. Full Python checks pass (2,377 tests, 15 optional skips;
strict types, lint and formatting). Evidence: ignored `local_data/currents-20261101/`.

2026-11-01, **ocean currents as clear courses, and sliver sea locations** (C456). [V-EXEC] Installed three
worlds in the normal Proton profile, each the land of the owner's world QU3N (continents, seed
12037730821817090414) with the peoples rolled so that its id differs from the installed QU3N
(`rnw_exp_world_qu3nhnzsl6`, left in place). **`mod/rnw_exp_world_7uwam7i5jh`** (peoples roll 3, code
`RNW1-080TE-3MWCX-G2VGB-E040G-00813-G1ZGY-PF`) is the current one: 869 nonmetadata files,
SHA-256 `d966ed39…346ad2`; all 871 manifest entries that the reveal setting does not withhold match the
installed bytes (26 are selection-cover and library-only files). It has 248 lanes (deep ocean), 182 of
which carry a current. The earlier two, `rnw_exp_world_7224ct35fl` (roll 1: only continuations of the
game's currents) and `rnw_exp_world_lademjafjb` (roll 2: before the shallow-strip, wide-stretch and sliver
changes), are superseded and kept for comparison. The export reports zero split cells, unreachable generated
seas, lost Old World contacts or land cells without port access. Records are in the native library and the
Proton `AppData/Local/RandomNewWorld` library. Existing worlds, saves, settings and playsets were preserved;
EU5 was not launched or controlled. The owner's land cache (four entries) was cleared because it holds cells.

The verified 1.1.0 hub (3,478 files) was rebuilt with the final code, passed its Windows/Wine generator and
window-shell self-tests and was installed as `mod/rnw_exp_hub`; its previous copy is retained at
`.rnw-hub-backups/1.1.0-1793508902672489194`. Wheel SHA-256
`a069243e53757eb92d019b539b59ea57ef1f6bb1c8cf759287bf069f817de14c`. The pending epoch-60 reference on build
26300913 has 871 files and digest `c1a8abf0…6516f`, reproduced by the installed-game suite (14 passed, 1 opt-in
skip). Full Python checks pass (2,375 tests, 15 optional skips; strict types, lint and formatting). Evidence:
ignored `local_data/currents-20261101/`.

2026-11-01, **issue #9 colonial overseas border correction** (C455). [V-EXEC]
Installed a new continents/1001 world with ocean expansion off, code
`RNW1-080G0-00000-0000Z-9040G-00813-R03EY-AY`, at
`mod/rnw_exp_world_3qinptckwg` in the normal Proton profile. The 866
nonmetadata files have SHA-256 `34bb82e2…ba680d`; all 866 match the export
manifest. The full installed 16384 × 8192 map has eight raw and zero passable
America–Old World contacts. World checks report zero split cells, unreachable
generated seas, lost Old World contacts or land cells without port access.
Existing worlds, saves, settings and playsets were preserved; EU5 was not
launched or controlled. The verified 1.1.0 hub (3,478 files) was rebuilt and
self-tested under Wine, then updated in place; its previous copy is retained at
`.rnw-hub-backups/1.1.0-1793491133243031038`. Wheel SHA-256
`dbec4f0446d9531ee58e82de5272ad017bdba233fba1d3090a8ec2e0ca8890f6`.
The pending epoch-60 reference on build 26300913 has 871 files and digest
`da3ca2c0…26acf3`, with zero passable America–Old World contacts. Local
candidate and reference reports are in `local_data/issue9-candidate/` and
`local_data/issue9-reference/`.

2026-10-31, **1.1.0 development — polar map edges** (C454). [V-EXEC] Installed a new
continents world, seed 20261031, code `RNW1-040G0-00000-0KAA5-7040G-0053W-GG0`, at
`mod/rnw_exp_world_wqouzjuybf` in the normal Proton profile. Its 870 nonmetadata
output files have SHA-256 `6943b6ac…2d420c89`; the exporter reports zero split
generated cells, unreachable generated seas, land cells without port access or
lost Old World contacts. Of 872 manifest entries for the mod, 851 match installed
bytes; the app's reveal setting omits 20 cover-only files and changes the metadata
thumbnail. The installed candidate has one generated polar-edge land location,
an impassable mountain of 60,190 pixels touching 249 edge pixels. Earlier worlds,
playsets and saves were preserved; EU5 was not launched or controlled.

The pending epoch-60 reference on the installed EU5 1.4.6 / build 26300913
has 871 nonmetadata files / `03d0877d…194aa` and the recorded map fingerprint.
The current hub passed its Windows/Wine generator and window-shell self-tests and
was installed as `mod/rnw_exp_hub` (3,478 files); its previous copy is retained at
`.rnw-hub-backups/1.1.0-1793486745699007681`. Wheel SHA-256
`b8921da10101c10d017492839e86af394408dead7b4c966b72d94703d6d94498`.
Full checks passed (2,360 Python tests, 15 optional skips; 23 Rust tests; strict
types, lint and formatting). Local reports are in `local_data/polar-edge-20261031/`.

2026-10-31, **1.1.0 development — generation status and ETA**. [V-EXEC] The inspector now
shows the general generation/cancellation status and percentage; stage names remain in the main
list. ETA uses the remaining parallel dependency path, a stable deadline, current reference
costs and a bounded local history of successful comparable runs. The estimate is shared by both
windows and covers the current world in a queue. Full checks pass (2,315 Python tests, 15 optional
skips; 23 native Rust tests; strict types, lint and formatting), as do `make desktop` (15 frontend
and 5 shell tests) and native/Wine offscreen self-tests. The source window is rebuilt. The recorded
trace replay and its limits are in [window design](../docs/gui-design.md#9-the-tauri-window).

Installed the verified hub from `local_data/eta-ui/rnw_exp_hub` with all **3,472 files** matching;
the previous hub is retained at `.rnw-hub-backups/1.1.0-1793457561302695189` in the same
Windows/Proton profile. Wheel SHA-256 `3303611bf5d5891cb346fc046fdca9f58b016e214a645f2ee0e067981bfa126e`;
window SHA-256 `1bdd5b915b598bd548807f001ba9b5c2fb0864832b3ac33b8e02b00fa9183050`.
No world bytes change: reuse **Climate-consistent · 1001**, `rnw_exp_world_5devvifcrz`.
The updater's EU5 process check passed. No game launch, playset, save or preference edit.
Unpublished 1.1.0 / pending epoch 60 unchanged. Evidence: ignored `local_data/eta-ui/installation.json`
and self-test/build logs; full checks in `local_data/eta-check.log` and
`local_data/eta-desktop-verified.log`.

2026-10-31, **1.1.0 development — vegetation consistent with its climate** (C452, issue #4). [V-EXEC] The
biome classifier now smooths joint (climate, vegetation) votes and picks a cell's vegetation among the pairs
of its own climate, so no cell carries a pair outside the Old World calibration (3-14 per world before; no
climate changes; 3-4 % of cells change vegetation, nearly all on climate borders). Full checks pass (2,302
Python tests, 15 optional skips; 23 Rust tests; strict types, lint and formatting clean). The pending
epoch-60 reference world is refreshed to 866 files / `3ac94a79…b1fb`, reproduced by the installed-game suite
and its layer-reroll check; full exports of six presets (archipelago 42, islands 7, small continents 42,
wall 9, the supercontinent reference and the continents candidate) pass every invariant.

Installed new candidate `rnw_exp_world_5devvifcrz` (**Climate-consistent · 1001**, continents, seed 1001
with precious deposits at 99.6 % only to give it an identity of its own, code
`RNW1-080G0-00000-0000Z-9040G-00811-ZJ0E8-KF3C`; coasts, lakes and relief equal those of **Vanilla relief ·
1001**) in the same Windows/Proton profile, with records in both libraries. All 897 installed files match;
866 nonmetadata files have SHA-256 `29f9d448dfa5e037f43fd7343a2e55dd3f369d12605a7c650228e221ed9712c4`. The
earlier candidates are left in place. All sixteen existing mod directories and nine profile-root files are
preserved. No playset, save or preference edit by the agent, no EU5 launch/control.

The verified, self-tested hub is installed with the former hub retained at
`.rnw-hub-backups/1.1.0-1793455916109750848` (isolated Wine self-test of the window, native kernels, world
codes and window shell; 3468 files in `rnw_exp_hub`). Candidate:
`local_data/hub-updates/1.1.0-1793455853224152320/rnw_exp_hub`; wheel SHA-256
`e3e1f4ba900744f3de3c8ee470f8cdb36478a04b9aa85323150266ab8e8f22bf`. Unpublished 1.1.0 / pending epoch 60;
existing worlds are untouched. Evidence: ignored `local_data/biomes-110/`.

2026-10-31, **1.1.0 development — mountains with vanilla's relief** (C451). [V-GAME + V-EXEC] The owner's
in-game screenshots showed the generated mountains flat beside vanilla's; the loaded world's files
confirmed that their relief was that of vanilla's hills, because the benchmark had left out vanilla's
3,706 additive mountain stamps. The stamps are now placed at vanilla's density and sizes, added as the
game adds them, and the relief is retuned against vanilla with its stamps by height class. Full checks
pass (2,282 Python tests, 15 optional skips; 23 Rust tests; strict types, lint and formatting clean). The
pending epoch-60 reference world is refreshed to 866 files / \`eb1c9a23…89\`, reproduced by the
installed-game suite and its layer-reroll check; full exports of six presets pass every invariant (fresh
land cache).

Installed new candidate \`rnw_exp_world_lfizm3z72e\` (**Vanilla relief · 1001**, continents, seed 1001
with precious deposits at 99.7 % only to give it an identity of its own, code
\`RNW1-080G0-00000-0000Z-9040G-00811-ZJGEB-HP3G\`; coasts and lakes equal those of **Natural lakes · 1001**)
in the same Windows/Proton profile, with records in both libraries. All 897 installed files match; 866
nonmetadata files have SHA-256 \`f561a227cf020c18226b25733c47f8d5227ed5cb3932d7cae5cebf25873e4bec\`. The
earlier candidates are left in place. All fifteen existing mod directories and nine profile-root files are
preserved. The playset "RNW" still enables the earlier world \`rnw_exp_world_oxwlg445jz\`; no playset, save
or preference edit by the agent, no EU5 launch/control.

The verified, self-tested hub is installed with the former hub retained at
\`.rnw-hub-backups/1.1.0-1793405945281628151\` (isolated Wine self-test of the window, native kernels, world
codes and window shell; 3468 files in \`rnw_exp_hub\`). Candidate:
\`local_data/hub-updates/1.1.0-1793405884220793675/rnw_exp_hub\`; wheel SHA-256
\`8ef6938ba1abbac19b3bcaa04d23bdeb8509f35b068f1b51a7d127c823e2c5db\`. Unpublished 1.1.0 / pending epoch 60;
existing worlds are untouched. Evidence: ignored \`local_data/relief-110/\`.

2026-10-30, **1.1.0 development — fine grain and lake cones** (C450). [V-EXEC] The terrain's detail
noise follows the installed heightmaps' roughness from 64 down to 4 decal pixels (native kernel
parameters, equal to its NumPy reference), and the relief counts lakes as land for its distance to the
sea, so lakes no longer stand in cones of ground. Full checks pass (2,282 Python tests, 15 optional
skips; 23 Rust tests; strict types, lint and formatting clean). The pending epoch-60 reference world
is refreshed to 867 files / `0ac9e45b…a8`, reproduced by the installed-game suite and its layer-reroll
check; full exports of six presets pass every invariant (fresh land cache).

Installed new candidate `rnw_exp_world_oxwlg445jz` (**Grain and lakes · 1001**, continents, seed 1001
with precious deposits at 99.8 % only to give it an identity of its own, code
`RNW1-080G0-00000-0000Z-9040G-00811-ZK0FH-9A28`; coasts and lakes equal those of **Natural lakes ·
1001**) in the same Windows/Proton profile, with records in both libraries. All 897 installed files
match; 866 nonmetadata files have SHA-256
`a037ae7ee65b78c046d97f3050f234fc39e14f16c25a23da9a16abfebcc10de9`. The earlier candidates are left in
place. All fourteen existing mod directories and nine profile-root files are preserved. No playset,
save or preference edit; no EU5 launch/control by the agent.

The verified, self-tested hub is installed with the former hub retained at
`.rnw-hub-backups/1.1.0-1793400314955403666` (isolated Wine self-test of the window, native kernels,
world codes and window shell; 3468 files in `rnw_exp_hub`). Candidate:
`local_data/hub-updates/1.1.0-1793400230982266893/rnw_exp_hub`; wheel SHA-256
`3f32f0398809a12f80681ff44cce709466d06b508647d2655608ff086d67eed9`. Unpublished 1.1.0 / pending epoch 60;
existing worlds are untouched. Evidence: ignored `local_data/grain-110/`.

2026-10-30, **1.1.0 development — mountains and hills** (C449). [V-EXEC] Relief chains of one width
with massifs of varied height, ridged crests and hill country; the installed mountain stamps turned
along each range, sized and strengthened by height, with their material layers. Full checks pass
(2,279 Python tests, 15 optional skips; strict types and lint clean; Rust untouched). The pending
epoch-60 reference world is refreshed to 867 files / `4cf2b8bd…2a`, reproduced by the installed-game
suite and its layer-reroll check; full exports of six presets (continents 1001, wall 9, archipelago
42, supercontinent 42, islands 7, small continents 42) pass every invariant.

Installed new candidate `rnw_exp_world_wkjnw4er3y` (**Mountain ranges · 1001**, continents, seed
1001 with precious deposits at 99.9 % only to give it an identity of its own, code
`RNW1-080G0-00000-0000Z-9040G-00811-ZKGFM-NJAG`; coasts, lakes and relief inputs equal those of
**Natural lakes · 1001**) in the same Windows/Proton profile, with records in both libraries. All
896 installed files match; 865 nonmetadata files have SHA-256
`67d305fd59834ea274833919aa6257b84eba2b9d8140dc8f68c3d1591eea2b07`. The earlier candidates are left in place. All
thirteen existing mod directories and nine profile-root files are preserved. No playset, save or
preference edit; no EU5 launch/control by the agent (the installer waited until the owner had closed
the game).

The verified, self-tested hub is installed with the former hub retained at
`.rnw-hub-backups/1.1.0-1793396212639764219` (isolated Wine self-test of the window, native kernels,
world codes and window shell; 3,468 files now in `rnw_exp_hub`). Candidate:
`local_data/hub-updates/1.1.0-1793396134401021804/rnw_exp_hub`; wheel SHA-256
`6945bd693952f2134a384d4a9f26f574e4526a1b9fa20a65c2271857d8510580`. Unpublished 1.1.0 /
pending epoch 60; existing worlds are untouched. Evidence: ignored `local_data/mountains-110/`.

2026-10-30, **generator hub 1.0.0, classic window drawing the new maps**: updated
`mod/rnw_exp_hub` with `update_local_hub` from the working tree in which the classic Qt window
(the Proton fallback) draws the maps as the Tauri window does. The updater verified current
sources (now `.json` too), ran the isolated Wine self-test (both windows) and verified all
**3,460** installed files; its EU5 process check passed at installation, after the game's logs
had last been written. Under Wine, the installed hub's Python drew the classic maps offscreen
from a library copy: about one second per lens. The previous hub is retained at
`.rnw-hub-backups/1.0.0-1793355880481098759`. No EU5 launch, world mod, save, playset or
setting change by the agent. [V-EXEC]

2026-10-30, **generator hub 1.0.0 with the Tauri window**, C444: updated `mod/rnw_exp_hub`
with `update_local_hub` from the working tree that makes the Tauri window the generator's
window (classic Qt window as fallback). The hub now holds `generator/window/random-new-world.exe`
and its WebView2 loader beside the unchanged launcher; the updater verified current sources,
ran the isolated Wine self-test (classic window, native kernels and world codes; window shell
and bridge) and verified all **3,457** installed files. EU5's Proton prefix has no WebView2,
so launching the hub through Proton opens the classic window by itself. The previous hub
(3,272 files) is retained at `.rnw-hub-backups/1.0.0-1793353704689297103` under the same
normal profile. No EU5 launch, world mod, save, playset or setting change. [V-EXEC]

2026-10-28, **RNW 1.0.0 / epoch 59 release candidate**, C431: installed
**RNW: RNW 1.0.0 candidate** in the new `mod/rnw_exp_world_l2ukzb7ihj`, code
`RNW1-081RF-FZCZT-X8CJN-T0400-00860-2AG63-YG1W8-8G3GH-149XR-08TM0-37FSE-J`.
All **878** installed files match the candidate, including its recovery bundle;
both native and Windows libraries contain complete entries. Its **867** canonical
nonmetadata files retain epoch 59’s digest
`23c0437734288ffa913061f627838855c97962185fe939da18b313ccb1bd9c85`.
The independent full reference check passes on EU5 1.4.5 / 26211608 (13 tests,
one opt-in layer check skipped). Installation preserves **6,002** existing-world
file hashes, **3,272** updated-hub hashes and **nine** profile-root hashes.
No game, playset, save or existing world was changed or launched. With EU5
closed, removal is limited to `mod/rnw_exp_world_l2ukzb7ihj` or this candidate’s
Remove action in the generator; library deletion is separate.

Built, self-tested and installed the **1.0.0 generator hub** with build-machine
installer receipts omitted and relative bytecode filenames. The updater verified
all **3,272** installed files and its isolated Wine self-test. The original
0.13.23 hub is retained at `.rnw-hub-backups/0.13.23-1793224526723633799`; an
intermediate 1.0.0 build remains at `.rnw-hub-backups/1.0.0-1793224940439895089`
beneath the same normal profile. Exact local audits: ignored
`local_data/release-1.0.0/`; public packages contain neither these records nor
the installed world. No publication or account action other than the explicitly
requested VirusTotal OAuth/analysis (C432).

2026-10-28, **generator hub 0.13.23 / epoch 59**: updated `mod/rnw_exp_hub`
with the Total Chaos layout fix and the current working-tree sources. The
updater verified the package, its isolated Wine self-test and the installed copy.
The previous 0.13.22 hub remains at
`.rnw-hub-backups/0.13.22-1793223433182403940` under the normal profile.
No game was launched. [V-EXEC]

2026-10-28, **0.13.17 / epoch 54, viable native countries**, C410: installed
**Viable native states** as a separate `mod/rnw_exp_world_quxq5nsxpx`, code
`RNW1-081RF-FZCZT-X8CJN-T006H-20860-2AG63-YG1W8-8G3GH-149XR-08TM0-3F1EA-C`.
Its **862** installed files match the prepared revealed-world candidate, including
its complete recovery bundle. Complete atlas, preview, record and cover entries
are registered in both the native and Windows generator libraries. The canonical
covered export has **851** nonmetadata files, digest
`68212db87594d811dea01a2d120917ee6ad0d5919b492f52c3b41e28e6e58808`,
independently reproduced by a second complete export. The same reference settings
now produce 307 landed states, none without peasants, and five physically isolated
states instead of eleven; its location raster is byte-identical to 0.13.16.
Demographic support and local markets do not establish engine income or later AI
behavior. No game was launched.

Updated `mod/rnw_exp_hub` to **0.13.17**, with current-source, package and installed-copy
verification, a passing isolated Wine self-test, and Linux/installed-Windows society
parity on three seeds. The former 0.13.16 hub remains at
`.rnw-hub-backups/0.13.16-1793148121269931926`; an intermediate 0.13.17 build also remains
at `.rnw-hub-backups/0.13.17-1793148232746096052` under the same normal profile.
The world installation hash-preserved all **862 files in each of the three existing
world mods**, all **3,274** files of the updated hub, and **nine** profile-root files.
No existing world, playset, save, setting or game-installation file was edited.
Exact audit: ignored `local_data/state-viability/installed.json`.
With EU5 closed, removal is limited to `mod/rnw_exp_world_quxq5nsxpx`, or use the
generator to remove **Viable native states**; hub rollback is a separate action.

2026-10-27, **0.13.16 / epoch 53, 4TXC water correction**, C408: installed
**RNW: 4TXC water correction** as a separate `mod/rnw_exp_world_obnxpx65bd`,
code `RNW1-081CV-WXEC2-QHSVZ-G006H-00870-3X022-1K1Z8-0Y448-1R8GR-4YW04-DA01M-GT9HG`.
All **860** installed files match the prepared candidate, including its 29-file
recovery bundle. Complete entries with atlas, previews and cover files are present
in both the native and Windows generator libraries. The covered canonical export
has 849 nonmetadata files, digest
`f154e74785fc3d946b0350579aad61de3f5abc863b8a4ae50fbf8ed87c2da674`;
the installed copy follows the owner's revealed-world setting. All 860 files of
the original `rnw_exp_world_4txcca23uo` were hash-checked and preserved.
No playset, save or game installation was changed, and no game was launched.
With EU5 closed, remove only `mod/rnw_exp_world_obnxpx65bd`, or use the generator
to remove **4TXC water correction**.

Updated `mod/rnw_exp_hub` to **0.13.16**, with current-source checks, installed-file
verification and passing isolated Wine self-test. The previous 0.13.15 hub remains
at `.rnw-hub-backups/0.13.15-1793127129958169746`; the intermediate 0.13.16 copy
before final source formatting remains at
`.rnw-hub-backups/0.13.16-1793138480127917814`, under the same profile.

2026-10-27, **generator hub 0.13.15 / epoch 52**: the normal-profile
`mod/rnw_exp_hub` was updated from 0.13.14 with the local updater. Its isolated
Wine self-test passed and the installed copy matches the candidate. The previous
hub remains at `.rnw-hub-backups/0.13.14-1793124238391900973` in the same profile.

2026-10-27, **0.13.15 / epoch 52 failure-world candidate**: installed the owner's
previously failing seed and settings as a separate `mod/rnw_exp_user_fixed_01315`,
code `RNW1-0824F-DZ40R-9PZFC-2006G-Y0870-3VG42-1M1Z8-0Y448-1R8GJ-4YW04-DA01M-7B59G`.
All 852 original installed files matched the staged candidate; its 850-file canonical digest is
`2af33c948fd58481627f71f82a50344f8d4f380120e7417a3c7e0c9c9bb02c63`. The game
was not launched; in-game behavior remains unobserved. With EU5 closed, remove only
`mod/rnw_exp_user_fixed_01315`.

The initial manual install omitted the application recovery bundle. On the owner's
report, added the 29-file `.metadata/rnw-library` receipt, restored the full native
and Windows library entries (including atlas, both previews, reproducibility record,
input manifest and 20 cover files), and verified the 850 game files still match their
record. The partial native entry was backed up under ignored `local_data/` before the
upgrade; its name, notes and visibility preferences were preserved. A disposable
copy passed both visibility-switch directions. No EU5 launch. [V-EXEC C407]

2026-10-27, **0.13.14 / epoch 51 water candidate**, C405: installed a separate
world generated from KZWN's seed and settings as `mod/rnw_exp_kzwn_hydrology_01314`,
code `RNW1-08247-10EET-R73D8-Y006G-W0851-Z80Y4-481R8-GJ4YW-04DA0-1Q74N-A0`.
All 853 installed files match the staged candidate; its 851-file canonical digest
is `43485292984e47e9b3088afe4262c43359b1e93a313cc90b2ef69f9cf9b1897e`.
Existing worlds were not changed. No game was launched; in-game appearance and
movement remain unobserved. With EU5 closed, remove only
`mod/rnw_exp_kzwn_hydrology_01314`.

2026-10-27, **generator hub 0.13.14 / epoch 51**: updated the normal-profile
`mod/rnw_exp_hub` from 0.13.13 with the local updater; its isolated Wine self-test
passes and the installed copy matches the candidate. The previous hub remains in
`.rnw-hub-backups/0.13.13-1793080736711652959` under the same profile.

2026-10-27, **0.13.13 / epoch 50 water candidate**, C404: installed a separate
world generated from KZWN's seed and settings as `mod/rnw_exp_kzwn_hydrology_01313`,
code `RNW1-08247-10EET-R73D8-Y006G-T0851-Z80Y4-481R8-GJ4YW-04DA0-1MRFX-R0`.
All 853 installed files match the staged candidate; its 851-file canonical digest
is `6ae3c08617ec146ad28f4ad9671a1437f0cd77e3ffd6d2d2f6b8a9ca3caafcc8`.
The existing KZWN worlds were not changed. No game was launched; in-game appearance
and movement remain unobserved. With EU5 closed, remove only
`mod/rnw_exp_kzwn_hydrology_01313`.

2026-10-27, **generator hub 0.13.13 / epoch 50**: updated the normal-profile
`mod/rnw_exp_hub` from 0.13.12 using the local updater; its isolated Wine self-test
passes and the installed copy matches the candidate. The previous hub remains in
`.rnw-hub-backups/0.13.12-1793080188361834887` under the same profile.

2026-10-27, **0.13.12 / epoch 49 water candidate**, C403: installed a separate
world generated from KZWN's seed and settings as `mod/rnw_exp_kzwn_hydrology_01312`,
code `RNW1-08247-10EET-R73D8-Y006G-R0851-Z80Y4-481R8-GJ4YW-04DA0-1G21A-EG`.
All 853 installed files match the staged candidate; its 851-file canonical digest
is `3fb0b43ea2ddd7c34b1d3d997a5b01c5d3765fba7378e99d16362d60354e3e06`.
The original KZWN was not changed. No game was launched; appearance and movement
remain unobserved. With EU5 closed, remove only `mod/rnw_exp_kzwn_hydrology_01312`.

2026-10-27, **generator hub 0.13.12 / epoch 49**: the normal-profile
`mod/rnw_exp_hub` was updated from 0.13.11 by the verified local updater. Its
isolated Wine self-test passes, and the new sea Voronoi kernel agrees byte for
byte with Linux on the synthetic parity fixture. The previous hub remains at
`.rnw-hub-backups/0.13.11-1793079003526968561` under the same profile. EU5
was not launched by the updater; its running-process guard passed at installation.

2026-10-27, **0.13.11 / epoch 48 ocean-current candidate**, C401: installed
**RNW: Continents 7FUA** as `mod/rnw_exp_hydrology_final_01311`. It uses the
land settings and seed of FWL3, with code
`RNW1-080MP-B37XH-BH660-M006G-P0870-3T062-1V1Z8-0Y448-1R8GJ-4YW04-DA01N-BAGYG`.
All 853 installed files match the prepared candidate; the 851-file canonical
digest is `a32d513c592b0530973ee425a98902ac3fd88d93068b7e0a2a1e6baa63a88e6c`.
No existing world or playset was replaced and EU5 was not launched. In-game
appearance and navigation are unobserved.

Exact removal with EU5 closed: `uv run rnw uninstall-mod rnw_exp_hydrology_final_01311 --user-dir '/mnt/games/SteamLibrary/steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V'`.

2026-10-27, **generator hub 0.13.11**, C401: updated `mod/rnw_exp_hub` from
0.13.10 after the candidate/source checks and isolated Wine self-test. The
previous hub is retained in `.rnw-hub-backups/0.13.10-1793069444467045353`
under the same EU5 profile; the updater verified the installed files.

2026-10-27, **generator hub 0.13.10**, C400: updated the existing
`mod/rnw_exp_hub` from 0.13.9 to 0.13.10. All 3,270 installed files match the
built candidate; its isolated Wine self-test reports the window, native kernels
and world codes working. The previous hub is retained in
`.rnw-hub-backups/0.13.9-1793061576765973647` under the same EU5 profile.
No EU5 launch, world mod, save or playset change was performed.

The repeatable updater is `packaging/update_local_hub.py --profile PROFILE`;
it builds and self-tests the current version, checks sources, retains the old
hub and verifies the installed files. The normal-profile removal remains
`uv run rnw uninstall-mod rnw_exp_hub --user-dir USER_DIR` with EU5 closed;
the backup is separate and retained.

2026-10-27, **0.13.10 / epoch 47 sacred-centre correction**, C399: installed
**RNW: Continents DNIW** as `mod/rnw_exp_fwl3_01310` (853 files, all compared
with the generated candidate). It reproduces the settings and seed of FWL3 with
code `RNW1-080MP-B37XH-BH660-M006G-M0870-3T062-1V1Z8-0Y448-1R8GJ-4YW04-DA01Q-PE480`.
JOQ writes theocracy and technology level 2 without the monarchy template.
The canonical digest is `85a25456b48836f110030914f64967df0f5b964ee71a167f354f52c1ee71029e`
(851 files). No game launch was performed; game behavior is unobserved.

Exact removal with EU5 closed: `uv run rnw uninstall-mod rnw_exp_fwl3_01310 --user-dir '/mnt/games/SteamLibrary/steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V'`.

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

2026-10-27 owner-run campaign, **RNW: Continents FWL3**, generator **0.13.9 / epoch 46**:
the active world was `mod/rnw_exp_world_fwl3ibw2cf` (862 files), code
`RNW1-080MP-B37XH-BH660-M006G-J0870-3T062-1V1Z8-0Y448-1R8GJ-4YW04-DA01K-0VEM0`.
After loading this world, the campaign advanced from 1 May 1337 through 1 January
1366 and exited normally. The read-only log audit found an incompatible generated
government/template combination and 16 locator warnings; see C398. The stable
selected logs, installed metadata and generated report are preserved under ignored
`local_data/campaign-1366-20261027/` with SHA-256 manifest. This records the owner's
session; no game launch or profile change was performed by the agent.

Exact removal with EU5 closed: `uv run rnw uninstall-mod rnw_exp_world_fwl3ibw2cf --user-dir '/mnt/games/SteamLibrary/steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V'`.

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

2026-10-28, **0.13.18 / epoch 55 — visual wrap workaround removed** (C416;
[dedicated dossier](../docs/research/map-wrap-dossier.md)). Installed new
**RNW: Vanilla terrain placement**, `mod/rnw_exp_world_35yxpmsi2m`, **846 files
verified**, with complete entries in both native and Windows libraries. Canonical
reference: 835 files, SHA-256
`e694e0b479e29280afe1a40d50d3103c49237b932c28eb2306adad6ec44bbbd9`, code
`RNW1-081RF-FZCZT-X8CJN-T006H-40860-2AG63-YG1W8-8G3GH-149XR-08TM0-32CDS-0`.
Only terrain2 changes from the previous reference; river/location/route/setup files
are exact. Existing QUXQ's **862 hashes** and **nine profile-root hashes** remain
unchanged. No save or playset edit; the candidate is a separate world, not a campaign
migration.

Built and self-tested the Windows generator, then installed hub **0.13.18** after
EU5 was closed. Its actual pre-update metadata was **0.13.16**; its **3,274-file**
copy is retained at
`.rnw-hub-backups/0.13.16-1793160623899843015` beneath the profile. Installed hub
files and current Python/catalog sources were verified by `update_local_hub`.
The first installation attempt had correctly stopped while EU5 was running;
no process was launched, closed or controlled to complete delivery. The Windows
offscreen self-test runs the generator only, not EU5.

Audits and full check outputs remain ignored under `local_data/quxq-wrap/audit/`;
new candidate under `local_data/quxq-wrap/release/`. Local game contract tests:
12 pass, 2 optional long checks skip. Game appearance of this rollback is untested.
Exact removal, when requested:
`uv run rnw uninstall-mod rnw_exp_world_35yxpmsi2m --user-dir USER_DIR`.

2026-10-28, **0.13.19 / epoch 56 — independent seam watersheds** (C417;
[separate dossier](../docs/research/map-wrap-dossier.md#approved-watershed-policy-01319--epoch-56-c417)).
Installed new **RNW: Independent seam watersheds**, `mod/rnw_exp_world_nmi2sayogz`,
**846 files verified**, and complete entries in both native and Windows libraries.
Code: `RNW1-081RF-FZCZT-X8CJN-T006H-60860-2AG63-YG1W8-8G3GH-149XR-08TM0-311X4-9`.
Canonical reference: **835 files**, SHA-256
`30f266abefbdae047540bb6ed9329fd00229b403743c6ebe564f2dc6c6ee7586`.
Independent PNG read-back verifies 328 real river outlets and lossless serialization;
11 location/route/locator files match the previous reference.

Generator-only hub updated **0.13.18→0.13.19** by `update_local_hub`, with installed
source/catalog verification and a passing Windows offscreen generator self-test.
Backup beneath the profile:
`.rnw-hub-backups/0.13.18-1793161726304827036`.
Three synthetic river cases agree byte for byte between Linux and the installed
Windows generator. All **862 QUXQ hashes**, **846 previous-candidate hashes** and
**nine profile-root hashes** are preserved; both library copies load correctly.
EU5 was closed; no launch, game input, existing-world replacement, save or playset
change. In-game appearance of the new rivers is unobserved.
Audit: ignored `local_data/seam-watersheds/` (written-audit, full-check, local-check,
platform parity, candidate and installation reports). Exact removal when requested:
`uv run rnw uninstall-mod rnw_exp_world_nmi2sayogz --user-dir USER_DIR`.

2026-10-28, **0.13.20 / epoch 57 — prior visual wrap extension restored** (C418;
[dedicated dossier](../docs/research/map-wrap-dossier.md#visual-source-extension-restored-01320--epoch-57-c418)).
Installed new **RNW: Restored visual wrap**, `mod/rnw_exp_world_7yzo7v4bu5`,
**862 files verified**, and complete entries in both native and Windows libraries.
Code: `RNW1-081RF-FZCZT-X8CJN-T006H-80860-2AG63-YG1W8-8G3GH-149XR-08TM0-37C66-3`.
Canonical reference: **851 files**, SHA-256
`de9fa8ae001c436bf3a5b6fb90ea342787069da4c326cdf84e0c8ec8d98e9995`.
Only terrain2 differs from 0.13.19; river bytes/statistics and all other world
content remain exact. The eight periodic source extensions preserve every
original level-zero sample and reproduce their opposite halos exactly.

Generator-only hub updated **0.13.19→0.13.20** with source/catalog and installed
copy verification; Windows offscreen generator self-test passes. Backup beneath
the profile: `.rnw-hub-backups/0.13.19-1793163552140074180`.
The initial attempt stopped while EU5 was running; final delivery succeeded only
after it was closed, without agent process control. The four existing worlds
(**3,400 files**, including QUXQ and the owner's newer world) and **nine
profile-root hashes** are preserved. Both new library copies load correctly.
No existing-world, save or playset replacement, EU5 launch or game input.
Restored-candidate rendering remains unobserved.

Verification: 2,116 Python tests pass/14 skip, 23 Rust tests pass, clean format,
lint and types. Audit: ignored `local_data/wrap-visual-restored/` (written-audit,
full-check, Windows self-test, candidate, installation and delivery reports).
Exact removal when requested:
`uv run rnw uninstall-mod rnw_exp_world_7yzo7v4bu5 --user-dir USER_DIR`.

2026-10-28, **0.13.21 / epoch 58 — complete sacred-centre governments**
(C424; [correction evidence](../docs/research/observer-01320-audit.md#implemented-correction--01321--epoch-58-c424)).
Installed new **RNW: Complete sacred-centre governments**,
`mod/rnw_exp_world_5fpdl42jbl`, **862 files hash-verified**, with complete
recovery metadata and entries in both native and Windows generator libraries.
Code: `RNW1-081RF-FZCZT-X8CJN-T006H-A0860-2AG63-YG1W8-8G3GH-149XR-08TM0-3BKDH-D`.
The independently reproduced canonical reference has **851 files**, SHA-256
`f85cb19da0d6b78f5d93d8d15dad87d50c3bf5aa7edcf6023725fc31f71f5e25`.
Only UUV's two initial government blocks change; all **850** other canonical
file hashes match 0.13.20. This is a separate world, not a save migration.

Updated the existing generator-only hub **0.13.20→0.13.21** through
`update_local_hub`, with current-source/package/installed-copy verification
and a passing isolated Windows generator self-test. All **3,274** hub files
are verified. The former hub's **3,274 files** remain under the profile at
`.rnw-hub-backups/0.13.20-1793177280743500399`.
The installed Windows and Linux generators agree on actual installed-game
government calibration and the synthetic country writer's bytes.

World installation hash-preserved all **4,262 files** of the five existing
world mods, the updated hub and **nine profile-root files**. Both copied
library entries and the recovery bundle load correctly. EU5 was closed;
no EU5 launch/control, existing-world replacement, save, setting or playset
change. New in-game acceptance remains unobserved.
Audit: ignored `local_data/theocracy-init/` (full/local checks, output comparison,
independent reproduction, Windows parity, world installation and hub reports).
Exact removal when requested, with EU5 closed:
`uv run rnw uninstall-mod rnw_exp_world_5fpdl42jbl --user-dir USER_DIR`.


2026-10-28, **0.13.22 / epoch 59 — EU5 1.4.5 + Across the Pillars**
(C425–C427; [compatibility audit](../docs/research/compatibility-1-4-5.md)).
Installed **RNW: EU5 1.4.5 + DLC**, `mod/rnw_exp_world_jzrscmin4p`,
**878 files hash-verified**, with complete recovery metadata and complete entries
in both native and Windows generator libraries. Code:
`RNW1-081RF-FZCZT-X8CJN-T006H-C0860-2AG63-YG1W8-8G3GH-149XR-08TM0-33VNG-D`.
The independently reproduced covered reference has **867** nonmetadata files,
SHA-256 `23c0437734288ffa913061f627838855c97962185fe939da18b313ccb1bd9c85`.
All **851** former canonical files are exact; only sixteen DLC text overrides
are added. The installed candidate follows the owner's revealed-world setting.

Updated the generator-only hub **0.13.21→0.13.22** using `update_local_hub`,
with source/package/installed-copy verification and passing isolated Windows
generator self-test. Its **3,274 files** are verified. The previous hub remains
at `.rnw-hub-backups/0.13.21-1793214280813313914` beneath the normal profile.
Linux and the installed Windows generator agree on the complete current
655-consumer inventory and the synthetic expedition rewrite.

World installation hash-preserves all **5,124 files of six existing worlds**,
the updated hub and **nine profile-root files**. No game installation, existing
world, playset, save or setting was edited. EU5 was closed; no game launch or
control. Adapted DLC gameplay remains unobserved. This candidate is a separate
world, not a migration for old saves. Audits: ignored `local_data/compat-145/`.
Exact removal when requested, with EU5 closed:
`uv run rnw uninstall-mod rnw_exp_world_jzrscmin4p --user-dir USER_DIR`.

2026-10-29, **1.0.0 release candidate — final CI Windows hub** (C435).
Installed the hub from the [release workflow artifact](https://github.com/Sir-Starch/eu5-random-new-world/actions/runs/40781022865), pinned to candidate `5645d763f81f23acd4f065ab110aab7a7c9165b1`. The downloaded archive checksum and package/source audit passed. `update_local_hub.py --candidate` verified current Python/catalog sources, ran the isolated Windows GUI/native/world-code self-test under Wine, and installed **3,272 files**. The previous same-version local build is preserved beneath the normal profile at `.rnw-hub-backups/1.0.0-1793232100930439192`. This replaced only the generator hub; no EU5 launch/control, world, playset, save or setting change.

The separate **878-file** world candidate `rnw_exp_world_l2ukzb7ihj` and its entries in both generator libraries remain local to the profile. World code: `RNW1-081RF-FZCZT-X8CJN-T0400-00860-2AG63-YG1W8-8G3GH-149XR-08TM0-37FSE-J`. Its epoch-59 reference has 867 nonmetadata files and digest `23c0437734288ffa913061f627838855c97962185fe939da18b313ccb1bd9c85`. Neither this world nor its generated game data is part of a public archive. Audit and receipts remain under ignored `local_data/release-1.0.0/`.

2026-10-29, **1.0.0 public hub identity** (C438).
Updated the existing `mod/rnw_exp_hub` to display **Random New World (RNW)**
with permanent metadata ID **`sirstarch.randomnewworld`**. The folder remains
`rnw_exp_hub`. Reused the audited 0b34dbd CI runtime; only
`.metadata/metadata.json` differs from that candidate. The standard updater
passed its candidate/source audit and isolated Wine GUI/native/world-code
self-test, installed and verified all **3,272 files**, and retained the former
hub at `.rnw-hub-backups/1.0.0-1793234743835704438`. Future updates accept both
the former internal ID and the permanent ID. No EU5 launch/control or world,
playset or save edit.

2026-10-30, **1.1.0 development / pending epoch 60 — resource frequency sliders**.
Installed new **RNW: Resource frequencies**, `mod/rnw_exp_world_5o4wtpm757`,
**898 files hash-verified**, on EU5 1.4.6 / Steam build **26300913**. Its code sets
maize/iron to 3×, fish to 0.5× and coal to 0; all 34 ordinary resources have independent
controls in both windows and all eleven languages. The 867 nonmetadata files have
SHA-256 `18ded1367dc9155b4784773754d348d7f23b05bee2760fe7e9d8205ac52db2fc`.
Native and Windows/Proton libraries both contain complete records and recovery assets.
The candidate keeps the normal covered-world presentation. All eleven pre-existing
mod directories and nine profile-root files are preserved; no playset/save/setting
change, existing-world replacement or EU5 launch/control.

The full-export comparison changes only `location_templates.txt`, preserves all
non-resource template attributes and Old World resource assignments, and measures
maize **501→983**, iron **76→140**, fish **350→236**, coal **13→0**. The default-weight
867-file reference retains `23c04377…bd9c85`. Full checks pass: **2,215 Python tests**
(15 optional skips), **23 Rust tests**, format/lint/types; desktop checks pass **13
Vitest tests**, **5 Rust shell tests**, types and production build. The read-only
installed-game suite passes **13 tests** (two opt-in skips). Both native self-tests
and the Windows hub's offscreen window/native/code and shell/bridge self-tests pass.

The standard updater installed the **1.1.0** generator-only hub into this profile's
`mod/rnw_exp_hub`, after source/catalog/package and installed-copy verification.
Previous hub: `.rnw-hub-backups/1.0.0-1793357953112577661`. The cached local build's
Windows wheel SHA-256 is `70ba3585c83adfeb037e189d0e4d1993d78b588fda0c5b55272bfb1f73598a73`.
This is an unpublished development build, not a 1.1.0 release. Exact source and
working diff, export comparisons, screenshots, build/self-test logs and installation
receipt remain under ignored `local_data/resource-sliders/`; the hub candidate is
under `local_data/hub-updates/1.1.0-1793357868762179148/`.

Independent pending-epoch reference reproduction passes on build 26300913
(`RNW_REPRODUCE=1`, 867 files, `23c04377…bd9c85`). The installed Windows generator
also passes the specific 34-resource settings/code/weight/catalog parity check.


2026-10-30, **1.1.0 development — responsive world selection and refreshed README** (C446).
[V-EXEC] Full checks pass: **2,218 Python tests** (15 optional skips), **23 native Rust
tests**, **14 Vitest tests**, **5 Rust shell tests**, format/lint/types and the production
build. The installed-game read-only suite passes **13 tests** (two opt-in skips) on build
**26300913**. Native and Windows/Wine window/native/code and shell/bridge self-tests pass;
a Windows same-size rewrite with restored mtime also invalidates its file hash. See the
[window guide](../docs/gui-design.md#9-the-tauri-window) for scoped responsiveness measurements.

The current source/catalog/package audit and standard updater verified and installed all
**3,460 files** of the generator-only hub into the same Windows/Proton profile's
`mod/rnw_exp_hub`. The previous hub is retained at
`.rnw-hub-backups/1.1.0-1793359698627626863`. This remains an unpublished development build.
World bytes are unchanged by this interface work: the existing candidate
`rnw_exp_world_5o4wtpm757` is reused. No EU5 launch/control or world/playset/save edit.
Build, self-test, timing, screenshots and installation evidence remain under ignored
`local_data/gui-finish/`.


2026-10-30, **1.1.0 development — The Wall and polar-edge geography** (C447).
[V-EXEC] Installed new world `rnw_exp_world_plqlumps6g` (**RNW: The Wall**, seed 9)
into the existing Windows/Proton profile, recorded above, on EU5 1.4.6 / build
26300913. Its 864 nonmetadata files have SHA-256
`0cd08894e6806d0ba3ad296338924be0a1d888f21c3ec4857b6761fc579e8c7f`;
all 895 installed files match the prepared candidate. Both native and Proton
libraries have complete records/recovery assets. All 12 pre-existing mod directories
and nine profile-root files are preserved.

The preset uses one procedural density field for mainland, islands and natural
straits. Its optional continuity constraint, width, position, coasts and ridge controls
are available in both windows and all eleven official languages. Ordinary geography
and land images also permit polar land. Full offline/package and independent
reference checks are recorded in [terrain](../docs/terrain-biomes.md#the-wall).

The standard updater verified and installed the **3,462-file** generator-only hub
at `mod/rnw_exp_hub`, retaining the former hub at
`.rnw-hub-backups/1.1.0-1793364755135727114`. The current Windows wheel SHA-256 is
`f39bd1bd0a70575f5004da13fc803a13aafc9aef646fdd5adb6b0e727a9817a7`.
Native and Windows/Wine window/native/code and shell/bridge self-tests pass.
The default 867-file pending-epoch reference independently reproduces as
`94fcf2d49ecf9a38685b149d71175f796e22aeb658f955ea4fc0dc5b777a4bcc`.
This remains an unpublished development build. No EU5 launch/control or playset,
save or setting edit. Source snapshot, exports, screenshots, build/check logs and
installation receipt remain under ignored `local_data/the-wall/`; the hub candidate
is `local_data/hub-updates/1.1.0-1793364661080448021/rnw_exp_hub`.


2026-10-30, **1.1.0 development — compact progress and current source window**.
[V-EXEC] Removed the repeated running-stage sentence below the Tauri progress bar;
the ETA and stage table remain. Rebuilt the source checkout window as well as the
native package window: they now match, so source launches show the existing Wall
checkbox rather than the older numeric bar. Browser verification covers toggling
that checkbox and the production progress view with synthetic state. Full checks
pass (2,244 Python tests, 15 optional skips; 23 native Rust tests; 14 interface tests;
five Rust shell tests), as do source/native and Windows/Wine self-tests.

The standard updater verified and installed the current generator-only hub in the
same profile, retaining the former hub at
`.rnw-hub-backups/1.1.0-1793365531868830695`. The Wall candidate
`rnw_exp_world_plqlumps6g` is reused: this is an interface change with no world-byte
or epoch change. Evidence remains under ignored `local_data/wall-checkbox/`;
hub candidate: `local_data/hub-updates/1.1.0-1793365445154648166/rnw_exp_hub`.


2026-10-30, **1.1.0 development — secondary-continent placement beside The Wall** (C447).
[V-EXEC] Added a broad procedural density component for side land, retaining local
coast detail and one land budget. Full checks pass (2,246 Python tests, 15 optional
skips; 23 native Rust tests), as do native/Windows package self-tests and four-seed
Linux/Windows coast/region parity. Six full-resolution seed comparisons and a
regression that fails the former field cover continental composition.
The installed-game suite passes 14 tests (one opt-in skip), including the unchanged
867-file ordinary reference (`94fcf2d4…77a4bcc`).

Installed new candidate `rnw_exp_world_qh2eoqjmqu` (**The Wall · 1000**, seed 1000)
in the same Windows/Proton profile, with records in both libraries. All 896 installed
files match; 865 nonmetadata files have SHA-256
`e0bd506886c33cf3872ca896a12264e23b51b21d77d2c807b1a12fc3f1ca9ec7`.
Export checks report no split cells, unreachable seas, unported land or lost Old
World contacts. All nine existing mod directories and nine profile-root files
are preserved. No playset, save or preference edit; no EU5 launch/control by the agent.

The verified, self-tested hub is installed with the former hub retained at
`.rnw-hub-backups/1.1.0-1793367341020351311`.
Hub candidate: `local_data/hub-updates/1.1.0-1793367165919223097/rnw_exp_hub`;
wheel SHA-256 `8bac372109dbc3e6a4bdd7c4644b89978d086434a2b6216bc555513f3466512a`.
This remains unpublished 1.1.0 / pending epoch 60; existing worlds are untouched.
Evidence: ignored `local_data/wall-variety/`.

2026-10-30, **1.1.0 development — coasts, water bodies and drainage** (C448).
[V-EXEC] Bent coast density, vanilla-calibrated lakes, inland seas and spit-bounded gulfs,
isthmuses, and rivers that enter and leave lakes (see the
[terrain guide](../docs/terrain-biomes.md#coast-shape-water-bodies-and-drainage-110--epoch-60)).
Full checks pass (2,268 Python tests, 15 optional skips; 23 native Rust tests; strict types and
lint clean). The pending epoch-60 reference world is refreshed to 867 files / `a2474322…879c`
(the frozen epoch-59 reference is untouched), reproduced independently by the installed-game
suite (14 tests, one opt-in skip) and the layer-reroll check. Full exports of six presets with a
cleared land cache (continents 1000, wall 9, archipelago 42, islands 7, small continents 42,
supercontinent 42) report no split cells, unreachable sea zones, unported land or river-rule
violations; the land cache is keyed by epoch, not code, so earlier exports that reused it did not
count. An island world exposed a strait through the display seam, which is no longer written as a
crossing.

Installed new candidate `rnw_exp_world_xgmv2hwu7n` (**Lakes and seas · 1000**, continents,
seed 1000, code `RNW1-040G0-00000-0000Z-8040G-0000X-PG0`) in the same Windows/Proton
profile, with records in both libraries. All 898 installed files match; 867 nonmetadata files have
SHA-256 `d23f40c881ac81717e02227ca84b9c9363f2fc610308c978ce893c6c954c52a3`; it has 228 lakes
(28 in the 1.0.0 generator's world of the same code), 492 river mouths (365) and 6,482 land
locations (6,732). All ten existing mod directories and nine profile-root files are preserved.
No playset, save or preference edit; no EU5 launch/control by the agent.

The verified, self-tested hub is installed with the former hub retained at
`.rnw-hub-backups/1.1.0-1793379603295333383`. Hub candidate:
`local_data/hub-updates/1.1.0-1793379528074812039/rnw_exp_hub`; wheel SHA-256
`91987ac5961139a663c9755fcac871489ace3db8080d246897a238ee1c943d97`. This remains unpublished
1.1.0 / pending epoch 60; existing worlds are untouched. Evidence: ignored
`local_data/hydrology-110/`.

2026-10-30, **1.1.0 development — lake shapes and lakes on the physical map** (C448 follow-up).
[V-EXEC] The owner found the first lake build unrealistic: every lake a smooth oval, and on the
generator's physical map each read as a crater. Lakes are now bent bowl-plus-noise fields of exact
area (lobes, bays, arms, satellite ponds, islands; fingers), and both windows draw a lake as a
level surface in the land instead of a pit (same synthetic test in both languages: mean shade
deviation 0.69–0.70 before, about 0.25 after). Lake counts and sizes still match the installed
game (11.5 per million land pixels, quartiles 112/184/436). Full checks pass (2,270 Python
tests, 15 optional skips; 23 native Rust tests; 15 interface tests; strict types and lint clean).
The pending epoch-60 reference world is refreshed again to 867 files / `d748a5c7…5762`
(superseding `a2474322…879c`), reproduced by the installed-game suite (14 tests, one opt-in
skip); the layer-reroll check was not repeated after this change (it passed on the preceding
build). Full exports of six presets with a cleared land cache (continents 1000, wall 9,
archipelago 42, islands 7, small continents 42, supercontinent 42) report no split cells,
unreachable sea zones, unported land or river-rule violations.

Installed new candidate `rnw_exp_world_facvbksoul` (**Natural lakes · 1001**, continents, seed
1001, code `RNW1-040G0-00000-0000Z-9040G-007YM-A5G`) in the same Windows/Proton profile, with
records in both libraries. All 895 installed files match; 864 nonmetadata files have SHA-256
`9bac70f68e4dda41e1c8d056ec2e776fe95b02980e2dd0e0e8794edf644d849a`. The earlier candidate
`rnw_exp_world_xgmv2hwu7n` (oval lakes) is left in place. All twelve existing mod directories and
nine profile-root files are preserved. No playset, save or preference edit; no EU5 launch/control
by the agent.

The verified, self-tested hub is installed with the former hub retained at
`.rnw-hub-backups/1.1.0-1793385173426752451`. Hub candidate:
`local_data/hub-updates/1.1.0-1793385098281812890/rnw_exp_hub`; wheel SHA-256
`0b4e59f79a5ebb92f58d9d8a6eafb40d8749645f3a4283a94f4a0b8dc121c4d3`. Unpublished 1.1.0 /
pending epoch 60; existing worlds are untouched. Evidence: ignored `local_data/hydrology-110/`.

2026-11-01, **1.1.0 development / pending epoch 60 — native territorial variety** (issue #8).
[V-EXEC] Added geography-based polity growth; the controlled six-preset comparison and its
scope are in [native societies](../docs/natives.md#territorial-variety-issue-8-110--epoch-60).
Full checks pass: 2,406 Python tests (15 optional skips), 23 Rust tests, format/lint/strict
Python types. The 13 ordinary read-only installed-game checks and independent reference
reproduction pass on EU5 1.4.6 / build 26300913. The refreshed reference has 870 nonmetadata
files, SHA-256 `2397404c6627798ff5840b2c195aada7bfd07f3bb3397919347f01ee55855dde`.
All 36 game-derived graph cases preserve population/identity fields, state farming support
and connected, disjoint political ownership; Linux and the packaged Windows generator agree exactly.

Installed **Native territorial variety · 8008**, `mod/rnw_exp_world_2owqyzokrv`, in the existing
Windows/Proton profile. Code:
`RNW1-081G0-00000-0007T-8040G-00860-2AG63-YG1W8-8G3GH-149XR-08TX0-3VM27-4`.
All **880 files** match the candidate; its 869 nonmetadata files have SHA-256
`e35d3c80d0a9861d6296b4588a631d45c64c2600e954ce9d383d91a65db62044`.
Both generator libraries contain complete records/recovery assets. Export checks find no
split cells, unreachable seas, unported land, lost Old World contacts or unsupported landed
countries. All 19 prior mod folders and nine profile-root files were hash-preserved by the
world installation; no playset, save or preference edit, and no EU5 launch/control.

The source/native and Windows/Wine window/native/code and shell/bridge self-tests pass.
The standard updater verified and installed the **3,478-file** generator-only hub, retaining
the former hub at `.rnw-hub-backups/1.1.0-1793548847675452430`. Candidate:
`local_data/polity-outlines/rnw_exp_hub`; Windows wheel SHA-256
`c6ee84c55c67a0975cd5b6afa2c3057d4bc376a73f121afa01686910f7f4ab4f`.
This remains unpublished 1.1.0 / pending epoch 60. Evidence and installation receipts remain
under ignored `local_data/polity-outlines/`; game loading/rendering was not observed.

2026-11-01, **1.1.0 development / pending epoch 60 — water round new islands** (owner's screenshots of
discs round small islands; [claim C461](../docs/research/claims-ledger.md)). [V-EXEC] The water colour and
foam rebuild now paint the open water round each pixel plus the game's own shelf instead of the mean
of all coasts; see the [register entry](../docs/research/interoperability.md). Full Python checks pass
(2,409 tests, 15 optional skips; format, lint, strict types; Rust untouched). The installed-game
reference export passes every export invariant on EU5 1.4.6 / build 26300913 and reproduces the
new pending epoch-60 digest `7ad8a385a41d1731baeb5bcd01da598e997446e8a706f3ccd32fc235dedd144d`
(870 nonmetadata files); `tests/golden_world.json` carries it, epoch 59 is untouched.

Installed **Continents PLBW**, `mod/rnw_exp_world_plbwy7zcgo`, in the existing Windows/Proton profile.
Code: `RNW1-080SM-KW9WD-Y6R47-N040G-00823-AG0C7-0165Z-4E`: the owner's installed world
`rnw_exp_world_aszzsukifw` with its peoples rerolled. Its `locations.png` and `rivers.png` are
byte-identical to that world's, so the two differ only in water textures and identities. Of 898
manifest files, 872 are installed and match their hashes and 26 are library-only. Both libraries hold
the record (the native one was written by the running generator; the Proton copy is identical and
passes bundle verification). On this pair of real textures the mean difference from the original sea,
on vanilla open ocean 40–48 / 48–56 pixels from a new island, falls from 33.8 / 22.8 to 10.0 / 7.3
luminance units. No playset, save or preference edit; no EU5 launch/control by the agent.

The source/native and Windows/Wine window/native/code and shell/bridge self-tests pass. The standard
updater installed the **3,478-file** generator-only hub, retaining the former hub at
`.rnw-hub-backups/1.1.0-1793553634103161116`. Candidate: ignored
`local_data/hub-updates/1.1.0-1793553542958151419/rnw_exp_hub` of the `water-island-halo` worktree;
Windows wheel SHA-256 `b0413c8da582ef8bdc0b8839886a5b1c18c63fc686bd0244efb1e5e7c45d6d24`. Unpublished
1.1.0 / pending epoch 60; game loading/rendering was not observed.

2026-11-01, **1.1.0 development / pending epoch 60 — sea cells as chains, bolt remainders, water band**
(owner's screenshots of ruled strips and bent remainders in world `aszzsukifw`; branch
`sea-cell-voronoi`, commit a2c835a, not merged). [V-EXEC] The change and its measurements are in
[sea geography](../docs/sea-geography.md). Full Python checks pass (2,411 tests, 15 optional skips;
format, lint, strict types; Rust untouched). The 13 ordinary installed-game checks pass on EU5 1.4.6 /
build 26300913; the five presets (archipelago 42, islands 7, small continents 42, The Wall 9, the
reference supercontinent) and the owner's code export with every sea invariant, and the refreshed
pending epoch-60 reference digest `192e1f549d90b2063dc8a54eced7bbb3036e1dae306c9ec2aee547155e55570b`
(870 nonmetadata files) is reproduced by `RNW_REPRODUCE=1`; `tests/golden_world.json` carries it.

Installed **Continents (sea cells)**, `mod/rnw_exp_world_ibyicz5wy2`, in the existing Windows/Proton
profile. Code: `RNW1-080SM-KW9WD-Y6R47-N040G-00823-AG0C6-R1XRM-3T`: the land seed and settings of the
owner's `rnw_exp_world_aszzsukifw` with the resources rerolled, on the new generator (the land moves a
little inland from the join, so it is not the same continent outline). All 901 files match the
candidate; every file of the 22 other mod folders and the nine profile-root files were hash-preserved,
and both libraries hold the record. No playset, save or preference edit; no EU5 launch/control by the
agent. The hub was not updated: the code is on an unmerged branch.

Correction to the water-halo record above: a first install of this same land with the peoples
rerolled (`RNW1-080SM-KW9WD-Y6R47-N040G-00823-AG0C7-0165Z-4E`) has the world id of that record's
`rnw_exp_world_plbwy7zcgo` and replaced its folder in the profile for about ten minutes (the id is the
code's, and the install command does not refuse an existing folder). The folder was then rebuilt from
the water-halo commit and checked: its 870 non-metadata files match the record's manifest, its
`.metadata/rnw-library` is the record itself and its `locations.png` is again byte-identical to
`aszzsukifw`'s. The replaced copy is kept in ignored `local_data/sea-cells/profile-backup/`.

After merging `main` (The Wall's land budget) and the water-halo branch into `sea-cell-voronoi`, the
pending epoch-60 reference digest is `c59495b5b0a1fb096d8cb5c99f6233638b5a6a3d8227abf73946a7e1c3a9ddb1`
(870 nonmetadata files; the digest above is the sea-cell change alone, the water-halo one is
`7ad8a385…`); `tests/golden_world.json` carries the merged one.

2026-11-01, **1.1.0 development / pending epoch 60 — island groups under the selection cover**
(owner's in-game screenshot; [claim C464](../docs/research/claims-ledger.md)). [V-EXEC] The cover's
grid now also takes every pixel of the canvas before its island groups were placed
(`cover_grid(..., within)`), so the vanilla Polynesian groups that stay or move inside the canvas
and the water between them are covered at country selection, as the preview already showed. On a
test world the old rule left 42 open patches (662 cells) inside the covered ocean; the new grid has
two of five cells, both Old World coast at the northern edge. Full Python checks pass (2,431 tests,
15 optional skips; format, lint, strict types). With the mask disabled the installed-game reference
export reproduces the former digest `9ca88eb7…`, so the cover alone gives the new pending epoch-60
digest `4d92a80da65eccb764379430c541b8da367338fec10a88a1849d5bf0165206b3` (868 nonmetadata
files), which reproduces; `tests/golden_world.json` carries it.

Installed **`mod/rnw_exp_world_xnkgew4sje`** in the existing Windows/Proton profile. Code:
`RNW1-080KN-HKXKK-XB4AA-9040G-00830-3SG46-R18Y1-G5VR1-BG`: continents, the land of the newest world
of that day (`lwz7sshdjh`) with its resources rerolled, covered at selection. The staged installer
refused any existing target; 898 files match the prepared mod, both libraries hold the record, and
all 11 other mod folders and 9 profile-root files are unchanged. No playset, save or preference
edit (the active playset still names a mod folder, `gieoozmbka`, that was already absent before this
installation); no EU5 launch/control by the agent.

The source/native and Windows/Wine window/native/code and shell/bridge self-tests pass. The standard
updater installed the **3,478-file** generator-only hub, retaining the former hub at
`.rnw-hub-backups/1.1.0-1793569845117687009`. Candidate: ignored
`local_data/hub-updates/1.1.0-1793569763743820520/rnw_exp_hub` of the `water-island-halo` worktree;
Windows wheel SHA-256 `99ef30440a709ad6c07793fc0b573df652c04366a03e10b412c16cdf065028b6`. Unpublished
1.1.0 / pending epoch 60; engine drawing of the cover over the groups was not observed.

2026-11-02, **1.1.0 development / pending epoch 60 — water round islands, second correction**
(owner's in-game screenshot of pale discs round every island in `xnkgew4sje`; claim C465).
[V-EXEC] The first background-relative water rebuild left a shelf tail and small biases that the
game showed as pale discs (on that world's real textures +7 / +2 / -2 / -3 luminance units at
32-40 / 40-48 / 48-56 / 56-64 pixels from a new island). Now a shelf ends in the far sea, cells
with open water keep their mean, divisions round, and where the old map was open sea the pixel is
the original plus the halo, so the original stands from about 48 pixels out with its own detail. On
the real textures of the new candidate the same distances give +2.9 / -1.1 / -0.7 / -0.2. Full
Python checks pass (2,432 tests, 15 optional skips; format, lint, strict types). The installed-game
reference export reproduces the new pending epoch-60 digest
`dbc4dc987a95ad872b31b653570ca70e2f32a0f0fb1b20bb95d5015cfafc1c76` (868 nonmetadata files);
`tests/golden_world.json` carries it.

Installed **`mod/rnw_exp_world_wiuqek6boj`** in the existing Windows/Proton profile. Code:
`RNW1-080KN-HKXKK-XB4AA-9040G-00830-3SG46-R28Y1-G48S2-3W`: the land and seas of `xnkgew4sje` with its
resources rerolled, covered at selection. The staged installer refused any existing target; 898
files match the prepared mod, both libraries hold the record, and all 15 other mod folders (the
played `xnkgew4sje` among them) and 9 profile-root files are unchanged. No playset, save or
preference edit (the active playset still names `xnkgew4sje`); no EU5 launch/control by the agent.

The source/native and Windows/Wine window/native/code and shell/bridge self-tests pass. The standard
updater installed the **3,478-file** generator-only hub, retaining the former hub at
`.rnw-hub-backups/1.1.0-1793576623890075294`. Candidate: ignored
`local_data/hub-updates/1.1.0-1793576556798271660/rnw_exp_hub` of the `water-island-halo` worktree;
Windows wheel SHA-256 `70e08d7bcb99d7efdb8081071ef67c08661585d4fbdc2b0080d3b6c511c4bf0f`. Unpublished
1.1.0 / pending epoch 60; engine drawing of the water was not observed.

2026-11-09, **1.2.0 development / pending epoch 61 — Omerika and Keep the real Americas** (source
`48bc918c520835022a7352de548827700c52c402`; ADR 0012).
[V-EXEC] Installed two worlds in the existing Windows/Proton profile, each into a **new** folder:
**`mod/rnw_exp_world_y25smlinzi`**, Omerika (generated geography on the Americas' template; code
`RNW1-043G0-00000-00001-A0410-0041J-RZG`, seed 42; 910 files), and **`mod/rnw_exp_world_o325km6mz5`**,
Omerika with *Keep the real Americas* (the game's own map, only the societies generated; code
`RNW1-083G0-00000-00000-B0410-00819-G0HKP-KR`, seed 11; 123 files, no map file). The installer verified the
files; both mods carry the recovery data (`.metadata/rnw-library`), so the generator adopts them
on its next start. All 7 other mod folders and the profile's playset, saves and settings are
unchanged; no EU5 launch or control by the agent. The standard updater installed the 1.2.0 hub
(Windows wheel SHA-256 `1b1fc6115e9725193e22f4c7319bf2e08efd468094de608362c87b2a4af2065a`; window,
native kernels, world codes, shell and bridge self-tests pass) and kept the former hub in
`.rnw-hub-backups/1.2.0-1794180236167272394`. Offline checks: 3,134 Python tests, strict types, lint,
desktop tests; the reference world digest of epoch 61 is reproduced. Engine behaviour of both worlds,
and of the real-Americas start on the game's map, is **not observed**.

2026-11-09, **Omerika, natural isthmus and a real likeness** (source `0d8bdbabde1d4ac8374b198d89fd660c15e943fd`; owner's screenshot of
`rnw_exp_world_y25smlinzi`: the isthmus was a ribbon of one location over open sea, and 100% likeness
was not recognisable).
[V-EXEC] Installed **`mod/rnw_exp_world_jtvmtid347`** into a new folder: Omerika, seed 77, the new
default likeness of 50% (code `RNW1-043G0-00000-00002-D0410-00568-GC0`). The earlier
`rnw_exp_world_y25smlinzi` (same code family, seed 42, made by the previous Omerika algorithm of the
same pending epoch) stays as it was; a code of the default settings does not change when the
algorithm of an unreleased epoch does, so `y25smlinzi`'s own code now makes other land. Full exports of
seed 42 at 50% and at 100% pass every validator. The hub update was **not** done: EU5 was running and
the updater refuses then, as it must; the source-run generator already has the change, and the Windows hub
takes it with the next `update_local_hub.py`. Engine behaviour is **not observed**.

2026-11-09, **1.2.0 release hub** (tag `v1.2.0` at `c50ebda76bcd02ca9cc2b169dc209531a10a0369`, tagged workflow run 42551734576).
[V-EXEC] Installed the generator-only hub of the published `RandomNewWorld-1.2.0-Workshop-Windows-Proton.zip`
(SHA-256 `ab7c974f38fa277f0ac1e348929247059080d6fcb259a5cfd15dba5308cf2566`) in the existing Windows/Proton profile with
`update_local_hub.py --candidate`, so the local hub is the package that goes to the Workshop. The window, native kernels,
world codes, shell and bridge self-tests pass under Wine; the installed folder is identical to the posted zip (3,570 files);
its window (`2035b89e…8035`), native module (`89e51e4b…1ecd47`) and launcher (`49674400…6932`) are the files scanned on
VirusTotal. The former hub is retained in `.rnw-hub-backups/1.2.0-1794193456668297154`. All other mod folders (15 worlds
and 2 others), the playset, saves and settings are unchanged; no EU5 launch or control by the agent.
