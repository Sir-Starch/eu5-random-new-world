# Experiments

Each experiment checks one question about EU5 in the running game or offline: its setup, the game build, the result with evidence labels, and how to remove whatever it installed. Experiments are numbered in the order they were planned. Numbers without a folder (016–018, 020) have no record. Installed test mods are listed in [INSTALLED.md](INSTALLED.md).

Experiments in the running game are kept short: a console sitting of about fifteen minutes, with the logs read afterwards. Anything a sitting cannot reach is checked offline or with a probe mod.

| # | Experiment |
|---|---|
| [001](001-metadata/README.md) | metadata discovery |
| [002](002-start-state/README.md) | one-location start-state change |
| [003](003-cell-class/README.md) | existing-cell geography and class |
| [004](004-boundary/README.md) | move a boundary between two existing cells |
| [005](005-new-id/README.md) | genuinely new location ID |
| [006](006-island/README.md) | playable generated island |
| [007](007-terrain-v1/README.md) | V1a terrain and biomes in game |
| [008](008-rivers-random-seed/README.md) | V1b rivers on a fresh random seed in game |
| [009](009-seed-driven-coasts/README.md) | V1b.1 seed-driven coastlines in game |
| [010](010-natives/README.md) | R6a native societies in game |
| [011](011-names-vassals/README.md) | R6b names, vassals and the terra incognita edge in game |
| [012](012-development/README.md) | R7a development, harbours and market villages in game |
| [013](013-reload-rewritten-mod/README.md) | A rewritten world without closing the game |
| [014](014-tags-localization/README.md) | Removed tags and localization hashes in game |
| [015](015-defect-batch/README.md) | Defect batch of C95 in game |
| [019](019-linux-proton-launch/README.md) | Starting the generator from the game on Linux (Proton) |
| [021](021-hub-generator-in-game/README.md) | The generator of the hub, started from the game (Linux, Proton) |
| [022](022-lobby-terra-incognita/README.md) | What the new-game screen lets a mod do: a rule, a log line and terra incognita |
| [023](023-new-world-cover/README.md) | The New World covered at country selection |
| [024](024-terrain-cover-probe/README.md) | Can the terrain layer tell the selection screen from a campaign? |
| [025](025-patch-1-4-3/README.md) | EU5 1.4.3 patch regression |
| [026](026-close-zoom-cover/README.md) | Close-zoom cover and country selection |
| [027](027-map-shader-scope/README.md) | Keep the map cover out of loading and character scenes |
| [028](028-technology-and-empires/README.md) | R7b and R7c: technology, regional families and great empires in game |
| [029](029-spline-strips/README.md) | Generated spline network: strips for roads between generated locations |
| [030](030-spline-probes/README.md) | Roads reported missing in 0.9.30: the order-preserving spline network and an Old-World-only probe (premise retracted) |
| [031](031-cover-drawings-and-list/README.md) | The cover's drawings of terra incognita, and the lobby's list without a gap |
| [032](032-lobby-list-layout/README.md) | Collapse hidden lobby country rows |
| [033](033-new-world-content-n1/README.md) | New World content, N1: official languages, neutralized identities, exceptional places |
| [034](034-content-hooks-n2/README.md) | Content hooks, N2: a mod-defined tag, scripted names, start variables |
| [035](035-new-world-content-n3/README.md) | New World content, N3: the river and sacred pilots |
| [036](036-console-session/README.md) | One console sitting for N1 to N3 |
| [037](037-console-session-2/README.md) | The second console sitting: what 036 left open |
| [038](038-lobby-list-and-colony/README.md) | The lobby's list without hiding, and the colony's name |
| [039](039-new-world-content-n4/README.md) | New World content, N4: the formable families and the stories |
| [040](040-colonial-path-probe/README.md) | The colonial path: does the scripted name apply to a colony made the game's way? |
| [041](041-sea-geography/README.md) | Sea geography: ports, names, topography and currents of the water |
| [042](042-lanes-and-closed-ocean/README.md) | Lanes and closed ocean |
| [043](043-strait-crossings/README.md) | Strait crossings |
| [044](044-sea-sitting/README.md) | The sea sitting |
| [045](045-varied-societies/README.md) | Varied societies |
| [046](046-sitting-fixes/README.md) | Fixes from sitting 045 and the seed-210 regression |
| [047](047-region-keys/README.md) | Region and area keys chosen by physical content (N5) |
| [048](048-localization/README.md) | The world's mod in every official language (L1) |
| [049](049-ocean-expansion/README.md) | Optional ocean expansion, connected ocean names, both canvas policies and verified offline candidates |
| [050](050-seeded-land-origin/README.md) | Seed-positioned land-noise lattice: recurring former-Alaska islands, spatial bias and verified offline candidates |

- [051 — Continuous map wrap](051-wrap-continuity/README.md): remove the mandatory seam strait, continue terrain/water sampling and roads across the map edges; 0.12.2, epoch 32; offline verification, no game launch.

- [052 — Physical seam and coast teeth](052-physical-seam-and-coasts/README.md): exact owner-world regression, precise noise interpolation and periodic terrain placements; 0.12.3, epoch 33, offline candidate.

- [053 — TR46 long observer campaign](053-tr46-observer/README.md): retrospective documentation only; all seven owner problems, twelve log diagnostic groups and an exhaustive catalog; 0.12.3 / EU5 1.4.4, no new launch or fix.

- [054 — Removed coast footprint](054-tr46-coast-footprint/README.md): vanilla Alaska crosses the raster edges; treaty direction is wrap-aware; 0.12.4 / epoch 34 rebuilds the offshore visual support left beside removed Alaska, with exact TR46 read-back and retained-land checks.

- [055 — Wrapped river raster](055-wrap-river-raster/README.md): owner retains full mainland wrap; planar river starts/joins preserve the continuous network and remove the written-data cause of TR46’s missing-source errors; 0.12.5, epoch 35.

- [056 — Primary terrain wrap](056-primary-terrain-wrap/README.md): extend the primary edge sources across the boundary, preserve interior samples, replace outside-only duplicates and retain full mainland wrap; 0.12.6 / epoch 36, rendered seam still unobserved.

- [057 — Local sea routes](057-local-sea-routes/README.md): remove arbitrary closed-ocean size partitions, bound nearby-coast detours and retain ports/passable water in script replacements; exact TR46 BU2A, 0.12.7 / epoch 37, offline verification and installation.

- [058 — Impassable highlands](058-impassable-highlands/README.md): compatible impassable location units and continuous vanilla-derived mountain height detail; exact TR46 LSI3, 0.12.8 / epoch 38, offline read-back and installation.

- [059 — Native expansion](059-native-expansion/README.md): read-only binding of both original TR46 saves, vanilla AI colonization rule, conquest/consolidation and each extraordinary society's land/subjects; no balance or generated-output change.

- [060 — Expedition lifecycle](060-expedition-lifecycle/README.md): correct 177 mining surveys plus one Pacific crossing; inherited no-travel and delayed-return edges, saved active expeditions and unattributed starts/resumes/port assertion; no generated-output change.

- [061 — AI diagnostics](061-ai-diagnostics/README.md): exhaustive anonymous command warnings, inherited unguarded capital-distance division and three Old World building-list clamps; no attributable native AI defect or generated-output change.

- [062 — Tordesillas](062-tordesillas/README.md): continuous New World longitude axis across the raster seam, situation comparison and distribution rewrites, candidate QW6O, 0.12.9 / epoch 39.

- [063 — Visual wrap and relief acceptance](063-visual-wrap-and-relief-acceptance/README.md): owner in-game visual review confirms seam absence and improved mountain relief; all completed work accepted; product version rises to 0.13.0, epoch 39.

- [064 — Ocean course ends](064-ocean-course-ends/README.md): reconstruct 657Q's interrupted Ruaziasleir lane, complete ocean tips before folding closed zones, and independently reject reachable dead ends; 0.13.2 / epoch 41.

- [065 — Installed-world recovery](065-installed-world-recovery/README.md): recognize installed RNW codes in place, restore self-describing worlds after library loss, handle partial copies and update the open window automatically; 0.13.3 / epoch 41.

- [066 — EVXP hangs](066-1341-hang/README.md): preserve the 1341 session and recording, then inspect the live 1346 recurrence; unit-graphics path-refinement work is implicated, with its triggering input unresolved.
