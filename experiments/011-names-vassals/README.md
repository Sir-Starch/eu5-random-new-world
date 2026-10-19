# 011 — R6b names, vassals and the terra incognita edge in game

- **Hypothesis:** The patched terra incognita shader compiles and softens the stepped edge (C69); natives see their coastal seas; places, provinces, areas, states and tribes carry names in their culture's language; generated vassal relations load; nothing from R6a or V1 regresses.
- **Method:** Build `rnw_exp_new_world` (generator 0.9.0) on a fresh random seed and verify it offline. The owner installs it in place and starts a 1337 campaign. Check: the terra incognita edge at close zoom (as in C69), as a European and as a native; place names on the map; a state with vassals (subjects view); a tribe (find it through a location's pops or the country search); `error.log` lines naming the shader, `rnw_` tags or locations.
- **Files/tools:** `generated/rnw_exp_new_world/` (`report.json` sections `natives` and `text_stats.terra_incognita_softened`), `rnw logdiff`.
- **Game version:** 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** Built and verified offline on fresh random seed 517130602: every invariant passes; 595 native countries (176 states, 419 tribes), 10 vassals, 7,721 places named in local languages, 476 natives know a coastal sea area, the shader patch is present; every native reference resolves against the 1.4.1 definitions; rivers have zero rule violations; 716 files, 1.33 GB. In-game run pending.
- **Remaining uncertainty:** shader compilation on the owner's system (Proton) and its cost; whether vassal setup between generated tags needs more than a dependency record.
- **Architecture implication:** If the shader fails to compile, remove the patch and accept the vanilla edge; `text_stats.terra_incognita_softened` records whether a build carries it.
- **Status:** **PENDING-HUMAN-VALIDATION**.
