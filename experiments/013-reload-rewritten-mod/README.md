# 013 — A rewritten world without closing the game

- **Hypothesis:** When the installed `rnw_exp_new_world` is replaced on disk while EU5 waits in the main menu, the next new game loads the new world completely (locations, drawn terrain, rivers, natives), because every new game mounts the mod's `in_game` folder again (C83). This decides whether the generator application of [ADR 0004](../../docs/adr/0004-generator-application.md) needs a game restart.
- **Method:** World A is installed: continents seed 3717486232, version 0.9.4. World B is staged in `generated/rnw_exp_new_world`: continents seed 34378487, version 0.9.5; every export invariant passes (713 files, 1.3 GB).
  1. Start EU5 with the RNW playset, start a new 1337 game and note the New World outline (screenshots stay outside the repository). Return to the main menu. Do not close the game.
  2. Replace the installed mod with world B: `uv run rnw install-mod --replace generated/rnw_exp_new_world/rnw_exp_new_world USER_DIR`.
  3. Start a new game. **Rung a:** world B everywhere, with matching outline, drawn terrain, rivers and native names.
  4. If world A or a mixture shows, return to the main menu, switch to another playset and back to RNW, and start a new game. **Rung b:** world B everywhere.
  5. If it still fails, close and restart the game and start a new game. This is the control: world B must show.
  6. Look in `error.log` for lines naming the terrain cache, decals, the map or `rnw_` keys.
  World B also carries the open checks of experiments 011 (border lines at close zoom) and 012 (items 2–5), and the region map mode water of 0.9.5 (C79–C80).
- **Files/tools:** `generated/rnw_exp_new_world/` (`report.json`), `rnw install-mod --replace`, `rnw logdiff`.
- **Game version:** 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** None yet.
- **Remaining uncertainty:** Caches outside the mod (the profile's `shadercache`, a generated `flatmap.dds`) may keep parts of world A. Windows may lock files the running game holds open, so a Linux/Proton result does not prove in-place replacement on Windows.
- **Architecture implication:** With rung a or b, the application installs a world and the player starts a new game without a restart; with rung b the application tells the player to switch the playset. With the control alone, the application asks for one restart. A mixed world is a defect to explain before ADR 0004 promises either flow.
- **Status:** **NOT-RUN**.
