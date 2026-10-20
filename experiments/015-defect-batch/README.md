# 015 — Defect batch of C95 in game

- **Hypothesis:** The causes found for the 0.9.8 world's own error lines (C95) are the real causes: with the 0.9.10 fixes the 1337 start logs none of them, and the world loads and plays as before.
- **Method:** Build 0.9.10 of continents seed 319218363 (the world of C93) for 1.4.2 and verify it offline (C96). The owner installs it while RNW is the active playset (C93), applies the same RNW playset once and starts a 1337 game. Then `uv run rnw logdiff local_data/baseline/2026-10-20-142-no-rnw/error.log ERROR_LOG` (the new session's `error.log`, copied to a scratch path) lists the lines the vanilla baseline lacks. Expected gone:
  1. `Too many map objects` and the three `map object locator ... is incomplete!` lines.
  2. `heir-selection that does not match its government type` (0.9.9) and `Subject type 'vassal' is invalid`.
  3. `dynamic historical event, but it is for the unknown` (53 events), `Scripted geography Cuba`, `Formable Haudenosaunee`, `Location [..] for only_in_location does not exist` (DLC city data), `Attempting to read unknown location: mabuya`.
  4. `Building 'market_village' cannot be built in a 'City'/'Town'`, `isolated from all ports`, `same color as`, `Culture has no pops`, `Religion is enabled but has no pops`, `Modifier ... was not used`.
  Expected to remain (informational, in every map-changing mod): `Locator transform overrides modified` for `city` and `vfx`.
- **Also check in game:** vegetation looks thinner than the 0.9.8 world (the scale factor is in `report.json`, `terrain.objects.density_scale_permille`); the 3 former port-less locations are now wasteland; a vassal and its overlord start in the War/Diplomacy views; diaspora pops show as small minorities.
- **Files/tools:** `generated/rnw_exp_new_world/report.json`, `rnw logdiff`, owner's `error.log` and `debug.log` (read only).
- **Game version:** 1.4.2 open beta, build 26043558 (C84).
- **Result/evidence:** pending the owner's run.
- **Remaining uncertainty:** The vassal rank cause is inferred (C95): if `Subject type 'vassal' is invalid` remains, the rank is not the reason. The object budget (net zero against vanilla) is a safe bound, not the measured cap.
- **Status:** **PENDING**
