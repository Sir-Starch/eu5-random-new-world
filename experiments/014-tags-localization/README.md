# 014 — Removed tags and localization hashes in game

- **Hypothesis:** With the definitions of the 544 removed American tags gone (C89–C90), a 1337 start logs no `invalid government type` line, and with collision-free keys `pdx_localize` logs no `Localization key hash collision`. Nothing else regresses: generated states, tribes and names show as before.
- **Method:** Build 0.9.7 of continents seed 3717486232 for 1.4.2 and verify it offline (C90). The owner installs it while RNW is not the active playset, switches RNW on **once**, and starts a 1337 game. Check:
  1. `error.log`: no `invalid government type` line.
  2. `debug.log`: no `Localization key hash collision` line, and the mod line after the single switch names version 0.9.7.
  3. The New World shows its states, tribes and local names; vanilla Old World countries look as usual.
  4. Whether one switch loaded the new build (the open question of C88): the mod name in `debug.log` and the world itself.
- **Files/tools:** `generated/rnw_exp_new_world/` (`report.json`: `country_tags_without_setup`, `localization_keys`), `rnw logdiff`.
- **Game version:** 1.4.2 open beta, build 26043558 (C84).
- **Result/evidence:** None yet.
- **Remaining uncertainty:** Whether some vanilla script needs one of the removed tags to be defined, not just referenced (none was found offline; formables are referenced the same way, C89).
- **Architecture implication:** If a removed tag must stay defined, that tag needs a dead-at-start setup entry in vanilla's style instead (C89); if collisions remain, the key hash differs per language and the key space must cover it.
- **Status:** **NOT-RUN**.
