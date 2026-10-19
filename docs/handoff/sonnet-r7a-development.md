# R7a: development and market villages from the generated world (Sonnet task)

**Designed by Opus 5.5 on 2026-10-19 for Sonnet 5.5 to implement.** It is the first slice of roadmap phase R7. It changes generated output and is NOT GAME VALIDATED. Do not launch the game; the owner batches in-game tests (experiment 012 below). Read [AGENTS.md](../../AGENTS.md), [natives](../natives.md), claims C67–C74 and this page before starting.

## Problem

In EU5 1.4.1, 1337 start development is the sum of the rules in `main_menu/setup/1337/14_development.txt` [V-LOCAL C73]:

- `base = -2`;
- `coastal = 5` × natural harbour suitability;
- `river = 0.5` × river size;
- `road = 2`; `city = 5`, `town = 2`;
- a value per vegetation, climate and topography;
- entries keyed by region, area, province or location.

The `development` static modifier scales with this value from 0 to 100. Per point it gives +2.5% population capacity, +2% supply limit and institution growth, among other effects.

The vanilla Americas use the keyed entries as a civilisation level. Mesoamerica gets 12, the Andes 10 and Central America 9. Aridoamerica and Colombia get 7 and the Great Plains 5. Cahokia gets +7, and the Haudenosaunee provinces get +1 or +2 [V-LOCAL C73]. Their 1337 setup has no institutions (`08`) and no roads (`09`) [V-EXEC C73]. Beyond the 25 ranks, `07_cities_and_buildings.txt` gives the Americas 88 buildings on 86 locations, all of level 1:

- 79 `market_village` buildings, in 79 of the 223 state capitals: 30 of the 34 Andean capitals and 48 of the 160 Mesoamerican ones;
- 4 `terraces`;
- Tenochtitlan's `calmecac`, `telpochcalli` and `warrior_temple`;
- one `mason` and one `city_walls`.

Population barely predicts which capitals get a market village: the 79 most populous capitals include 31 of them, against 28 by chance [V-EXEC C73]. Development and these buildings make up the economic start state of the vanilla Americas beyond pops, ranks and markets.

The generator keeps the 14 American region entries. Generated regions reuse vanilla keys by position, so these bonuses land on whatever land lies there. The pattern of the generated societies plays no part [V-EXEC C74]. On the 0.9.1 build of seed 517130602:

- `colombia_region` gives +7 to 165 locations, none of them in a state.
- `aridoamerica_region` gives +7 to 118 locations, none of them in a state.
- `east_coast_region` gives 0 to 278 locations, 41% of them state land.
- Generated cities get no society bonus. 55% of all keyed development goes to unorganised land.
- The Spearman correlation between the keyed bonus and population is 0.30. In vanilla it is 0.51.

Generated natives have no buildings: the vanilla records were pruned together with their tags [V-EXEC C74].

Every generated coastal land location (each has one port) also gets `natural_harbor_suitability = 0.50`, which adds 2.5 development [V-EXEC C74]. In the vanilla Americas 1,092 locations carry the field: 828 (758‰) are 0.00, 13 are −0.10, and the mean is 0.101 [V-EXEC C73]. Harbour suitability also feeds port buildings, naval actions and expeditions [V-LOCAL].

## Goal

Generated development comes from the same model as the societies. The vanilla rules stay as they are. Only their inputs change: the keyed society term follows complexity, and harbour values follow the vanilla distribution. The most complex states start with the vanilla share of market villages. Vanilla engine and interface files are not changed.

## Design

### A. Drop positional entries

Remove every entry of the `development = { ... }` block whose key is a region, area, province or location of the vanilla New World. Locations and provinces are already pruned as removed keys. Regions and areas survive because the generated hierarchy reuses them.

Add a span-preserving helper to `eu5_rewrite.py`, for example `drop_block_entries(text, path, keys) -> str`. It removes the entries keyed by `keys` from the block at `path` (whole lines, as `_delete` does) and keeps every other byte.

Guard the step with an invariant that fails loudly: no kept vanilla location may lie under a dropped key, so no Old World development changes. On 0.9.1, American regions hold no kept vanilla location [V-EXEC C74].

### B. Society term from complexity

`societies.Societies.complexity` already holds a permille level (0–1000) per land location. It falls with travel cost from each hearth and is damped on poor land.

For each generated land location, set the term to `(B × level + 500) // 1000`, which rounds halves up in integer arithmetic. The level is `min(1000, complexity × 1000 // full)`, with `full` fitted per world (see the revisions below). Write the locations where the term is at least 1 as `<key> = <n>` lines in the same block. Vanilla also keys locations there (for example `cahokia = 7`). Write them in plan order so the output is deterministic.

`B` is calibrated at build time, not hard-coded. It is the largest keyed sum (region + area + province + location) that any vanilla American land location receives. On 1.4.1 that is 12 (Mesoamerica, and Cahokia at 5 + 7) [V-EXEC C73].

Why not copy vanilla's per-class distribution? The generator places hearths on the best farmland. Generated state land therefore has a physical part of about −0.8, against −5.6 for vanilla state land in jungles and highlands. Copying would give states a mean development of 8.7–10.6, against 4.1 in vanilla [V-EXEC C74]. The linear term keeps the physical rules working. On seed 517130602, estimated with complexity = peasant share / 0.6 [INFERRED from `PEASANT_PEAK`], it gives these results [V-EXEC C74]:

| Class | Estimated mean development | Vanilla mean |
|---|---|---|
| State capitals | 5.6 | 4.6 |
| State land | 5.6 | 4.1 |
| Towns | 6.5 | 6.1 |
| Cities | 4.0 | 12.2 |
| Tribes | 0.4 | 1.1 |
| Unorganised land | 0.3 | 0.7 |

It also gives a Spearman correlation of 0.63 with population. 32% of land gets a positive term (vanilla: 38%), which is about 1,900 lines.

Generated cities stay low because they stand on poor land. This is a watch item, not a criterion.

**Revision after the first build (2026-10-19).** The estimate above overstated the generated physical part, because it still counted the old constant harbour 0.50 (+2.5 on every coast). With real harbour values (mean 0.10) the first full build (continents 3706823338, purely linear term) gave state capitals 2.90 and other state members 3.03 against the vanilla 4.60 and 4.13 (0.63× and 0.73×), which misses the 0.75× criterion (C75). Vanilla state land holds the full keyed maximum (median 12), so the term now saturates: complexity of 800 permille or more counts fully. On that build's complexities the saturation gives capitals 3.88, members 4.09, towns 6.15 and cities 8.43, with tribes and unorganised land unchanged at 0.09. 

**Second revision (2026-10-19).** A fixed saturation of 800 passed on continents 3706823338 (state members 4.11, capitals 3.89) but failed on archipelago 5 (members 6.39 = 1.55×, capitals 6.42): island state land gets about 2 more development from its physical rules, and no single constant satisfied both worlds (continents needed `full` ≤ about 880, archipelago ≥ about 825). Vanilla's keyed entries compensate terrain in the same way (Mesoamerica +12 on jungle, Great Plains +5), so `full` is now fitted per world: `fit_full` takes the smallest candidate in 250…3000 (step 5) for which the estimated mean development of state capitals and members together is closest to the vanilla mean. On archipelago 5's complexities it gives `full` = 1115 and capitals 4.42, members 4.30.

**Audit revision (2026-10-19, Opus, product version 0.9.3).** The owner rejected the remaining weaknesses. An audit on cached worlds found: (1) rivers are not spread alike in vanilla and generated land (generated cities have a river in 857–1000‰ of cases, vanilla cities in 111‰), so leaving the river term out biased the calibration; the estimate now includes it with river size taken from `rivers.png` [INFERRED]. (2) Generated cities and towns stand on poorer land than the rest of generated state land, while vanilla cities stand on better land than vanilla state land, so one state-land curve cannot reach both class means; the saturation is now fitted per settlement class (cities, towns, other state land). (3) A new invariant keeps every Old World development entry identical to vanilla. Tribes and unorganised land stay below vanilla for reasons of land and authored vanilla bonuses (see [economy](../economy.md)); they are not fitted. Cities and towns join the acceptance criteria (0.75–1.5× vanilla).

### C. Harbour suitability

Replace the constant 0.50 in `eu5_nw_export._template_lines` with one value per generated port location. Land without a port keeps no harbour field, as in vanilla, where every harbour entry has a port.

1. **Vanilla distribution.** Read `natural_harbor_suitability` from the template of every vanilla American location that has the field. On 1.4.1 there are 1,092 such locations, 13 of them at −0.10. Keep the values as integer hundredths, sorted, with their sign.
2. **Shelter score.** `_ports` already returns the dock pixel of each port. On the final full-map raster (`_final_labels`, with vanilla classes from `game_map.classes` and generated classes from `world.classes`), cast 48 rays of 64 px from the dock pixel. Columns wrap and rows are clamped. The score is the number of rays that reach a land or wasteland pixel. Count lakes as water.
3. **Quantile mapping.** Sort the ports by (score, key). The port at 0-based rank `i` of `n` gets the vanilla value at index `floor((2i + 1) × m / (2n))` of the `m` sorted values. Write the value with two decimals (`0.25`, `-0.10`), as vanilla does.

Shelter predicts the vanilla values only weakly: the Spearman correlation is 0.10–0.12 on the Americas and 0.18–0.19 on the whole map. The vanilla values look hand-authored [V-EXEC C74]. The distribution is what matters here; shelter only sets the order, in the right direction. Do not claim more.

### D. Market villages

`market_village` is a rural peasant building with no potential or allow condition (`in_game/common/building_types/rural_buildings.txt`) [V-LOCAL].

1. **Vanilla share.** Divide the number of vanilla American state capitals that have a `market_village` by the number of vanilla American state capitals. On 1.4.1 that is 79 / 223, or 354‰. Read both counts at build time.
2. **Choice.** Give `(count × permille + 500) // 1000` generated state capitals one level-1 `market_village`, choosing the capitals with the highest complexity first. Break ties by population, then by key.
3. **Output.** Write one line per building into `building_manager`, in the vanilla format: `market_village = { tag = <owner> level = 1 location = <capital> }`.

The choice by complexity is an [INFERRED design]. In vanilla, market villages cluster in the most complex civilisation, the Andes, rather than following population. Culture-specific buildings (Tenochtitlan's three), terraces, masons and walls stay out of R7a.

### E. Report and invariants

Add `_verify_development` to `eu5_nw_export.py` and call it next to `_verify_natives`. It raises `NewWorldExportError` if any of these fail:

- no development entry is keyed by a vanilla New World region, area, province or location, and no kept vanilla location lay under a dropped key;
- every generated entry is keyed by a generated land location, once, with an integer value from 1 to `B`;
- every generated port has a harbour value from the vanilla set, and no other generated location has one;
- every generated building stands in the capital of the state whose tag it names, at most one per location.

Add a `development` section to `report.json` with:

- `B`;
- the number of entries and the share of land with a positive term;
- the Spearman correlation between the term and population;
- the harbour histogram for generated and vanilla ports;
- the number of market villages and the share of state capitals that have one;
- the estimated mean development per class for the generated world and for the vanilla Americas. The classes are exclusive: city, town, other state capital, other state member, tribe, unorganised.

The estimate uses: base + coastal × harbour + rank + vegetation + climate + topography + keyed entries, clamped at 0. It leaves out the river term because the engine's river size is unknown. Compute it for both sides with the same function, and label it an estimate. (Since the audit revision the estimate includes the river term with an inferred river size, C76.)

## Code placement

| Where | What |
|---|---|
| `src/rnw/eu5_development.py` (new) | `DevelopmentCalibration` (frozen: `society_max`, `harbours` in hundredths, `market_village_permille`, the parsed rules for the estimate); `vanilla_development(...)` as a pure function of the parsed setup texts, hierarchy and templates; `society_terms(complexity, keys, society_max)`; `shelter(water, docks, rays=48, reach=64)` (vectorised); `harbour_values(scores, keys, harbours)`; `market_villages(states, complexity, population, permille)`; `development_lines(terms)`; `building_lines(buildings)`; `estimate(...)` |
| `src/rnw/eu5_natives.py` | `NativeWorld` gains `complexity: dict[str, int]` (permille) and `population: dict[str, int]` (milli-pops), both per generated land key, from `societies`. Natives code makes no other change |
| `src/rnw/eu5_rewrite.py` | `drop_block_entries` |
| `src/rnw/eu5_nw_export.py` | Calibrate once; insert development lines via `SETUP_INSERTS["14_development.txt"] = ("development",)` and buildings via a second insert into `07_cities_and_buildings.txt` at `("building_manager",)`. `SETUP_INSERTS` holds one path per file, so extend it or insert twice; keep it simple. Also drop the entries, set a harbour per port in `_template_lines`, add `_verify_development` and the report section |
| `AGENTS.md` | Add `eu5_development.py` to the code layout and `docs/economy.md` to the document map |

There are no new settings. A development control belongs to the presets (R8). Keep integer arithmetic and the existing style. Follow `eu5_natives.py` for calibration from the local installation.

## Tests

Use synthetic fixtures only (new `tests/test_development.py`):

- Calibration parses a small `14_development.txt` and hierarchy and returns the largest keyed sum. Entries for Old World keys are ignored.
- `society_terms`: 0 → no entry, 1000 → `B`, monotone, halves round up, deterministic order.
- `harbour_values`: with `n == m`, it reproduces the vanilla multiset exactly; otherwise the share of zeros stays within one value; ties break by key.
- `shelter`: a dock inside a bay scores higher than one on a cape. A ray that crosses the horizontal wrap sees the land on the other side.
- `market_villages` picks the vanilla share of capitals, highest complexity first, with deterministic ties. The lines parse with `rnw.pdx.parse` and name the owner's tag.
- `drop_block_entries` removes only the named keys; comments and other bytes stay.
- `_verify_development` rejects each of these: an entry for a vanilla region, a duplicate key, a value above `B`, a harbour value on a location without a port, and a building outside its owner's capital.

In `tests/test_local_install.py`, add an optional test that asserts on 1.4.1: `B == 12`, 1,092 American harbour values (828 of them zero), and market villages in 79 of 223 American state capitals.

## Acceptance (offline)

1. `uv sync --locked --group dev && make check` passes, and the optional local tests pass.
2. Raise PATCH per [ADR 0003](../adr/0003-versioning.md): 0.9.1 → 0.9.2, or the next PATCH if the owner has accepted R6 in the meantime. Update golden digests only if they change; `rnw synth` output should not change.
3. Build three worlds, one at a time, each in the foreground under `timeout 1200` and each into `generated/rnw_exp_new_world --replace` (the CLI accepts only `rnw_exp_*` outputs; do not create other bundles). Build continents 3706823338 first, then archipelago 5, then a fresh random continents seed. Copy each `report.json` to gitignored `local_data/` before the next build, so the bundle that remains is the fresh seed for the owner. Confirm with `pgrep -af rnw` that nothing is left running. On each world:
   - every invariant passes;
   - estimated mean development of cities, towns, state capitals and state members is each within 0.75–1.5 × the vanilla value (cities and towns since the audit revision);
   - the tribe and unorganised means are each at most the vanilla value + 0.5;
   - the Spearman correlation between the term and population is at least 0.5;
   - at least 85% of the land that a hearth reaches (complexity above 0) has a positive term. Until the audit revision this read "the share of land with a positive term is 25–45%"; that bound measured the number of hearths, not the development model: on a world with 3 hearths (continents 3717486232) only 230‰ of land has any complexity, so no term can reach 250‰ (C76);
   - the harbour zero share is 758‰ ± 10 and the mean 0.101 ± 0.01;
   - the share of state capitals with a market village is 354‰, up to rounding.

   If a criterion fails, change the model, not the threshold, and record why.
4. Documentation:
   - new `docs/economy.md` (the R7 page: mechanism, method, settings, checks, open work);
   - claim C75 with the three builds;
   - a [research log](../research/log.md) entry;
   - a status line on the [roadmap](../roadmap.md) R7 row;
   - record `experiments/012-development/README.md` with status NOT-RUN.
5. One commit for the phase.

## Experiment 012 (owner, when the next game test is batched)

**Hypothesis:** EU5 honours `14_development.txt` entries keyed by new location keys. Development on generated land then follows the societies, harbour values show in the location window, and generated market villages stand in their capitals.

**Method:**

1. Use the development map mode. Hearth regions should be the bright areas, with no bright patch left where vanilla Mesoamerica or Colombia lay.
2. Compare the development in the tooltips of one city, one state member and one tribe location with the report's estimate. This tests the clamp and the inferred river size.
3. Check the harbour suitability of three ports.
4. Check one market village in a state capital's building list.
5. Look for `error.log` lines that name `14_development`, `building_manager` or `rnw_` keys.

## Out of scope

- institutions and roads (the vanilla Americas have none in 1337);
- buildings other than market villages;
- technology and advances, alliances and rivalries, extraordinary societies, presets;
- any change to engine, define or interface files;
- launching the game or writing to the profile.
