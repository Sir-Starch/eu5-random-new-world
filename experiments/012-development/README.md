# 012 — R7a development, harbours and market villages in game

- **Hypothesis:** EU5 1.4.1 honours `14_development.txt` entries keyed by generated location keys. Development on generated land then follows the native societies (hearths bright, wilderness dark), harbour values show in the location window, and generated market villages stand in their state capitals. Nothing from R6 or V1 regresses.
- **Method:** Build `rnw_exp_new_world` (the R7a version, see [economy](../../docs/economy.md)) and verify it offline (C75). The owner installs it in place and starts a 1337 campaign. Check:
  1. The development map mode. Hearth regions should be the bright areas, with no bright patch left where vanilla Mesoamerica or Colombia lay.
  2. The development shown in the tooltips of one city, one state member and one tribe location, compared with the estimate in `report.json` section `development`. The estimate clamps at 0 and takes river size as the rank of the widest river pixel [INFERRED]; a difference on river locations measures the engine's river size.
  3. The harbour suitability of three ports, one of them sheltered and one on an open coast.
  4. One market village in the building list of a state capital.
  5. `error.log` lines that name `14_development`, `building_manager`, `market_village` or `rnw_` keys; `rnw logdiff` against the same-build baseline.
- **Files/tools:** `generated/rnw_exp_new_world/` (`report.json` section `development`), `rnw logdiff`.
- **Game version:** 1.4.1 open beta, build 25905365 [V-LOCAL C01].
- **Result/evidence:** [V-GAME owner, 2026-10-20] the 0.9.3 build loads, and the world map looks right visually (C77). The owner noticed generated areas and regions in pieces inside other regions, a fault of the identity planner since T3, not of R7a; fixed in 0.9.4 (C78). Items 2–5 were not reported one by one. Three offline builds pass every criterion (C75, revised by the audit in C76); the 0.9.3 bundle of continents seed 3717486232 was byte-identical on rebuild. The staged bundle is now version 0.9.4 of the same seed, with the compact connected hierarchy (C78).
- **Remaining uncertainty:** whether the engine reads development entries for new location keys, whether a `market_village` of a generated tag loads in a generated capital, and how the engine sizes rivers.
- **Architecture implication:** If entries for new keys are ignored, put the society term into a scripted static modifier or into the location templates; if market villages fail to load, drop them and keep development and harbours.
- **Status:** **PARTIAL** — loads and looks right; the item checks remain open and can be done on the 0.9.4 build.
