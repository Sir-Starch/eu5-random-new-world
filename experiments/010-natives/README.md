# 010 — R6a native societies in game

- **Hypothesis:** EU5 1.4.1 starts a 1337 campaign with the generated natives: new tags load with engine-drawn coats of arms, landed states own their locations, `type = pop` tribes hold the pops of generated locations, towns and markets exist, and colonisers can still settle unorganised land. Nothing in the V1 physical geography regresses.
- **Method:** Build `rnw_exp_new_world` (generator 0.8.0, fresh random seed) and verify it offline (C68). The owner installs it in place and starts a 1337 campaign. Check: political map mode over the New World; a state and a tribe (name, flag, ruler, culture, religion, government); pops in a capital; a town; a market; the religion view; one colonial nation's options; `error.log` lines that name `rnw_` tags or locations.
- **Files/tools:** `generated/rnw_exp_new_world/` (`report.json` section `natives`), `rnw logdiff` against the same-build baseline.
- **Game version:** 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** Built and verified offline on fresh random seed 3200056429 (C68). The owner ran it on 2026-10-19: the start loads, generated states appear with names, flags and rulers (C69). Defect: pixel steps along the terra incognita edge (C69); fixed for the next build by a softened terra incognita shader and coastal seas known to natives.
- **Remaining uncertainty:** whether new tags need more than a definition and a name, whether pop-type tribes need an owner or capital, and whether religions with special mechanics break on generated geography.
- **Architecture implication:** If it passes, R6 continues with R6b (culture-specific place names, diplomacy between states). If new tags fail, fall back to the vanilla American tags whose culture matches.
- **Status:** **PASSED** for loading and states (C69); the terra incognita fix and the remaining checks (tribes, pops, towns, colonisation, error.log) go into the next build.
