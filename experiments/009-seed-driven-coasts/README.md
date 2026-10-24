# 009 — V1b.1 seed-driven coastlines in game

- **Hypothesis:** With the coast model of generator 0.7.0 (C64) a new seed gives a visibly different New World outline, including the north-west next to the map wrap, and seam coasts and straits look natural; nothing else regresses.
- **Method:** The owner installs `rnw_exp_new_world` built from seed 3706823338 (continents, generator 0.7.0, C65) in place and starts a 1337 campaign. Compare the north-west and the overall outline with the previous build (seed 3903742112); check the seam strait at close zoom, the gulf around Bermuda, rivers, startup and error.log.
- **Files/tools:** `generated/rnw_exp_new_world/` (report and `preview.png`), `rnw logdiff` against the same-build baseline.
- **Game version:** 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** Built and verified offline (C65). Installed by the owner on 2026-10-19 (commit a08883a; 712 files verified byte-identical). The owner checked it in game on 2026-10-19 and accepted it: the outline follows the seed (C66).
- **Remaining uncertainty:** whether the wider, ragged seam strait still hides the wrap crack; whether the less saturated land budget leaves too much sea in some seeds.
- **Architecture implication:** If it passes, V1 physical geography is accepted and work moves to natives (R6).
- **Status:** **PASSED** (C66).
