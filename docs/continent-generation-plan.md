# Optional continent generation

The owner confirmed the player-facing scope on 2026-11-18. The architecture below
is the proposed implementation. The end-to-end performance budget will be agreed
after measuring a prototype on the development machine. The
[geography prototype](../experiments/071-continent-geography/README.md)
records the initial timing cases, coastal calibration, the shared biome and
regional resource trial, and the installed 1337 data audit.

## What the player chooses

- America, Africa and Oceania each have a switch. Only America is enabled by
  default. Any nonempty combination makes one world and installs as one mod.
  The window disables generation when every switch is off.
- An enabled continent uses its own default preset immediately. The proposed
  starting defaults are Continents for America, Supercontinent for Africa and
  Archipelago for Oceania. Each continent has its own preset and applicable
  land, society and resource controls. The Wall is exclusive to America.
  Omerika, the land editor and the option to keep the real Americas retain
  their American scope. With the latter option, American geography is fixed
  and its societies are generated alongside any other selected continent.
- The Tauri and classic windows display the same settings through the common
  controller. A continent's land, society and resource settings are resolved
  against its own preset. A world code and a portable world file carry the
  enabled continents and their settings. Old codes and epochs remain readable.
- An America-only request uses the current generation behavior, including
  possible relocation of some vanilla Pacific islands. When Oceania is
  generated, the shared map planner reserves its vanilla footprint for Oceania
  before American land can displace those islands. Coastlines can change in a
  shared border area when the continents selected for generation change.

## Geography and the starting map

Africa covers the game's `africa` continent, including Egypt, Sinai and the
Atlantic islands it assigns to Africa. A land route between Africa and Asia can
form where the generated land reaches the existing boundary. Its presence is a
result of the geography. Asia keeps its land, locations and coastline.
The planner allows contact at the existing land interface and protects other
retained shores. A route is established by passable land in the final map.
At that interface the coast penalty eases over one ramp, so the ordinary
terrain field can reach the retained land. Local river routing treats the
retained terrain as a closed boundary. The composed climate uses the
installation's heights on the retained side.

Oceania covers the game's `oceania` continent, including Australia, New Zealand,
New Guinea and Hawaii. Indonesia stays vanilla. Preserve the distinction between
a continent's land footprint and the waters filed under its hierarchy by the
game. The common ocean planner assigns the latter according to the final coasts
and connections. Pacific location identities remain continuous across the wrap.

The game still has distinct `america`, `africa` and `oceania` hierarchies. Reuse
regional and area keys where their script meaning can be matched to the new
geography. Ports, straits, sea lanes, currents, trade paths and the rivers at the
wrap derive from the composed world. Apply the American overseas and Treaty of
Tordesillas rules to America, with a distinct contact policy for Africa's natural
boundary. Derive initial discovery from each region's role in 1337 and its actual
contacts, retaining the American discovery behavior for America-only worlds.

Vanilla setup outside an enabled footprint remains in place. A country holding
land on both sides keeps its surviving locations. The proposed handling keeps
its tag and institutions on that land and moves its capital to a valid surviving
location when required. This needs an explicit setup rule because the current
pruner can remove the entire record. On the installed EU5 1.4.9 build 26655995,
the 1337 records give Morocco four locations in Europe and the Mamluks 75 in
Asia, including one conquered location. Both records also hold African land. [V-LOCAL]
The regional setup pass binds character birthplaces and dynasty homes to
present locations, then trims optional kinship links when a character is
retired. Only named identities can propagate a retirement to other files.

### Morocco's Iberian holdings

When Africa is generated, the 1337 start offers four choices for Ronda,
Algeciras, Gibraltar and Marbella.

1. **Keep Morocco (default).** Morocco retains its Iberian holdings, its
   tag and its start government. It receives the 86 passable generated
   African locations closest to those four holdings. Distance compares
   centres on the wrapped raster and crosses water. Choose the location
   nearest vanilla Fez from those 86 as the African capital. Reserve the
   locations before building the other African polities.
2. **Independent Algeciras.** The four locations form a Sunni Andalusi
   emirate centred on Algeciras. The normal tag allocator assigns it a
   fresh tag. Morocco retires from this start.
3. **Join Castile.** Castile integrates the four locations and keeps its
   own capital. Morocco retires from this start.
4. **Join Granada.** The existing Emirate of Granada integrates the four
   locations under its existing ruler. Morocco retires from this start.

All four options use the existing population cohorts in Iberia. The
choice belongs to Africa's settings. The offline prototype exercises it
on one map, with player controls and mod serialization scheduled for the
combined exporter.

## One generation pipeline

1. **Plan the domains together.** Read and calibrate the installation once.
   Use a registry of continent definitions that supplies the vanilla footprint,
   coast and contact policy, supported presets and societal calibration. Resolve
   overlapping claims before generating land. Build compact, wrap-aware windows
   or row bands for the actual domains, with a halo only where a kernel needs
   surrounding geography. A bounding rectangle across all active continents
   would spend work and memory on the oceans between them.
2. **Build geography with shared algorithms.** Use the existing coast, relief,
   drainage and cell builders with each continent's settings and deterministic
   random streams. Calibrate preset scale and land budgets against each region's
   footprint and vanilla location density. This work scales with the active
   windows. Compose the surface before world-scale weather, ocean and connection
   planning. Run each world-scale stage once at its dependency boundary, including
   any distinct climate passes the geography and final biome stages need. Assign
   shared waters once and use one location, color and country-tag allocator.
   Budget stage and kernel workers together. Release regional scratch buffers as
   stages finish.
3. **Build the 1337 start.** Read the game's 1337 society data once and calibrate
   each continent from its own peoples, religions, naming patterns, population,
   technology and institutions. Use the shared society and history rules with
   regional controls and budgets. Create new settlement patterns, states and
   histories from the generated geography. Allow contacts, migration and exchange
   along actual routes, including historical influences from preserved neighbors
   where the available routes and identities support them. Use regional indexes
   and the existing bounded route search to keep unrelated actors out of each
   other's candidate sets. Use the common chronology for interactions between
   generated societies and retain the vanilla start outside the selected regions.
4. **Write and verify one world.** Generate the rasters, textures, vegetation,
   splines, atlas, campaign scripts and localization from the common plan. Audit
   the affected vanilla scripts and DLC content for both added continents,
   including decisions for removed tags and cross-border countries. Scope
   regional formations, discoveries and colonial content to the right continent.
   Validate the combined map and setup before staging the single output bundle.
   Check the existing global location cap against the final unique IDs.

## Prototype and performance measurement

Wire the shared map planner to the existing builders and writers. An early
geography measurement can identify hotspots. The end-to-end comparison requires
the production path through verified export, with normal map resolution, cell
density, history rounds and validators for the three-continent case.

Use one same-build America-only control and the following comparable runs with
the same seed, thread and stage budgets. Run the Africa and Oceania additions
individually before the combined case so that the cost of either is visible.

| Selection | Presets | Purpose |
|---|---|---|
| America | Continents | Control on the same machine and build |
| America and Africa | Continents and Supercontinent | Added African work and Atlantic/Red Sea interfaces |
| America and Oceania | Continents and Archipelago | Added Oceanian work and Pacific wrap |
| America, Africa and Oceania | Continents, Supercontinent and Archipelago | Combined elapsed time and peak memory |

Measure elapsed time from generation start to verified output, per-stage elapsed
time and call counts, peak RSS, generated pixels and land/sea cell counts. Report
empty application cache and reusable-input-cache runs on new geography separately.
Keep the filesystem-cache conditions consistent where possible and record their
limits. Repeat the control and combined case to distinguish added work from run
variance. Compare the common stage counts to verify that shared work really runs
once. The owner will set the acceptable elapsed-time increase from these results.

[V-LOCAL] The installed hierarchy and `default.map` give America 4,434 vanilla land
locations, Africa 2,433 and Oceania 790, classifying lakes, sea zones, non-ownable
locations and impassable mountains separately. This shows the relative starting
scale of the regions. Generated counts will depend on preset, land share and
terrain. See [previous timings](performance-plan.md) for the current baseline.

## Implementation and acceptance order

1. Extract the world-level orchestration and regional inputs, keeping the
   America-only reference byte-identical. Verify the combined domain planner,
   dry and wet Africa–Asia boundaries, and the Pacific wrap. Measure geography
   and world-scale stage counts as soon as those stages are connected.
2. Wire regional setup, audit affected script references and cross-border
   ownership, and bring the prototype through verified export. Check regional
   scope for countries, cultures, religions, trade and stories. Check ownership
   and population on retained land. Measure the control and combined runs and
   use those results to agree on the time budget before performance tuning.
3. Verify all seven nonempty selections. Connect both windows, the CLI, world
   codes, files, previews and layers to the same settings. Check repeatability
   across thread budgets, reopening and rerolls, old-code reproduction, and the
   case with the real Americas option. Run the
   [installed-game reference and package checks](testing.md) once the common
   path and user controls are complete.
