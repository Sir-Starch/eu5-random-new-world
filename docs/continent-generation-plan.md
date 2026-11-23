# Optional continent generation

The owner confirmed the player-facing scope on 2026-11-18 and set a four-minute
target for the combined configuration on the development machine after the
prototype timing on 2026-11-19. The
[geography prototype](../experiments/071-continent-geography/README.md)
records the initial timing cases, coastal calibration, the shared biome and
regional resource trial, and the installed 1337 data audit.

## What the player chooses

- America, Africa and Oceania each have a switch. Only America is enabled by
  default. Any nonempty combination makes one world and installs as one mod.
  The window disables generation when every switch is off.
- An enabled continent uses its own default preset immediately. The
  starting defaults are Continents for America, Supercontinent for Africa and
  Archipelago for Oceania. Each continent has its own preset and applicable
  land, society and resource controls, and the same six quick questions that America's
  block asks (land, peoples, states, extraordinary peoples, turbulence, gold and silver),
  answered from the continent's own type. The Wall is exclusive to America.
  Omerika, the land editor and the option to keep the real Americas retain
  their American scope. With the latter option, American geography is fixed
  and its societies are generated alongside any other selected continent.
- The Tauri and classic windows display the same settings through the common
  controller. A continent's land, society and resource settings are resolved
  against its own preset. A world code and a portable world file carry the
  enabled continents and their settings. Old codes and epochs remain readable.
- An America-only request uses the current generation behavior, including
  possible relocation of some vanilla Pacific islands. With all three
  enabled, outlying islets of regenerated continents belong to their
  surrounding canvas. The replacement geography covers their old sites.
  Retained islands filed under the open ocean use the existing island
  placement rules. Coastlines can change in a shared border area when
  the continents selected for generation change.

## Geography and the starting map

Africa covers the game's `africa` continent, including Egypt, Sinai and the
Atlantic islands it assigns to Africa. A seed can select a dry approach to
western Asia, along its nearby coastline or at the existing land interface.
The **Require a land connection to Asia** option always constructs a passable
approach, a land bridge (`land_bridge.py`). Its axis is the cheapest route from
a site on the interface to the continent over a noisy landscape that keeps clear
of the domain's coast margin, on coarse blocks and with sixteen moves so that no
direction is preferred. A route of more than a few locations is made to wind:
it is routed again through waypoints, one every few locations, a location or two
to its left and right in turn, so that no stretch of it stays straight for long.
It is then
smoothed until no corner is left. Its body is
a union of discs along the axis whose radius swells and narrows, flares at both
ends, narrows to the room beside the coast margin and has the same irregular
edge as every other coast; a one-location spine is always kept. A site whose
bridge does not touch the interface, join the continent and cover the site is
dropped for the next candidate, and none at all fails explicitly. So is a site whose
bridge would shut a bay of water off round a retained islet or leave a pocket of the
Levant's coast with no sea of its own to lead out of it (`newworld.py`): of seven seeds of
the all-continents selection five stopped at export with "Sea cutout at cell N has no coast
or retained sea" or a sea-reach error before this guard, and all seven generate with it.
Two export checks that failed sound worlds were corrected with it: the removed-locations
check read a native people's culture Pende or Teke as the location of that name, and a land
location whose only way to a port lay through the retained land beside it was rejected
(`eu5_nw_export.py`). The bridge's
construction is all integer arithmetic, so a seed gives the same bridge on every platform. The
generated shore and land cells follow the resulting terrain.
The final adjacency check requires a direct border between passable locations.
Nearby European shores can admit a separate approach with a short navigable
strait, built the same way at a smaller scale. Only a crossing validated
against the pixels on both shores and the
single sea zone between them enters the game map. Local river routing treats
retained terrain as a closed boundary. The generated land approaches the
installed relief before drainage and the painted detail fades to the same
heights at the junction. The retained height is carried in as averages of the
retained ground over wider reaches the farther the pixel lies from the seam,
not as the nearest shore pixel's height (which left streaks and straight steps
where two such pixels' reaches met), and the conditioning gives way to the
generated coast away from the seam. Retained ground that the generated sea has
cut through high land (water whose installed height is above the coast's, never
an installed coast or sea) rises over the new shoreline only as steeply as the
steep installed coasts do (the cap follows the installed coasts' 90th percentile,
`RIM_BASE` at the first pixel and `RIM_SLOPE` for each after it; what is above it
saturates to at most `RIM_MARGIN` over it), so the cut is no wall. The cap is
applied to the retained heights before they are carried into the generated side,
so both sides of the seam agree, and the target, its weight and the cap reach
the decals by interpolation (two samples a location pixel), not as repeated
whole pixels, so no pixel grid shows where the height slopes.
Retained climate and vegetation supply a joint vote
that weakens inland. Border materials follow the new shoreline.

With all three continents enabled, Eurasia and Greenland form a fourth
canvas with their installed coastal and inland seas. It also keeps the open
water that its shores enclose: a block of sea belongs to it when Eurasian
land lies on both sides along some line within about 1,100 pixels, no
generated continent's land is in the way, and Eurasian land is nearer than any
generated continent's. Whole installed locations that are mostly enclosed and
that join the retained map keep their water, so the Bay of Bengal, the South
China Sea and the passage between Greenland and Britain stay vanilla. The
open Indian and Atlantic oceans remain available to the three generated
canvases. Africa retains its share of the Mediterranean and may approach
southern Iberia and western Asia. The
African mainland's northern latitude sets a limit for both its generated
land and its claim on open water, so no African canvas lies beside northern
Europe. Water that Africa would have claimed beyond that limit stays
retained, whole locations at a time, so the Celtic Sea and the Bay of Biscay
remain European. With fewer continents, the same two rules apply to the
African and Oceanian claims: water that retained shores enclose and water
beyond Africa's limit stays vanilla.
The three generated regions share borders across the Pacific, Atlantic and
Indian oceans. Their coasts and intervening deep water form during generation.
The sea plan checks the common borders for deep water and keeps small residual
pieces with adjacent navigable water. **Keep a sea route around the world**
(default on for regional worlds, omitted for The Wall) is a step of the
generation (`rnw.circuit`, `eu5_nw_export._open_sea_route`): once the continents
are composed it looks for a route of passable water that winds round the map's
wrap, with the locations that straddle the wrap counted as two pieces. If there
is one nothing changes. If not, the cheapest generated location that closes a
route is turned into sea (a wasteland costs its pixels, land four times as
much; the land link to Asia and the Wall's barrier stay) and the drainage plan
of its continent lets the rivers that ran into it end there. After the sea
zones are planned the route is checked again on the finished water and the
export fails without one. An earlier version reserved a southern strip of the
map for it (1.3.0 development, 2026-11-20); the owner rejected that on
2026-11-23 as a crutch.

Oceania covers the game's `oceania` continent, including Australia, New Zealand,
New Guinea and Hawaii. Indonesia stays vanilla. Preserve the distinction between
a continent's land footprint and the waters filed under its hierarchy by the
game. The common ocean planner assigns the latter according to the final coasts
and connections. Pacific location identities remain continuous across the wrap.

**Coasts the game files under another continent (2026-11-22, owner's report on `qpktias5fw`, 1.3.0 /
epoch 64).** The game files the Red Sea, the Gulf of Aden, the delta mouths and Morocco's Atlantic coast
under `asia` or `europe`, and the Mediterranean bays of the African shore under `africa` although
the enclosed-water rule leaves them out of Africa's claim. Such a zone washes only land that is replaced,
yet the plan kept it whole, so its border with the generated water was the replaced coast itself
(3,963 px of it with all three continents), and the islets of the replaced land inside it stood as
generated sea locations of 1 to 151 px with no neighbour (11 of them, all in the Red Sea; the two
screenshots of the report). Three construction rules, no repair:

- `continent_domains._released_coasts` gives a coastal zone that touches replaced land and no retained
  land (and is no Sound toll or naval anchor) whole to the canvas of the continent whose land it touches
  most, so its border with the zones that stay is a border of vanilla zones. All three continents do it
  in `_shared_water`; a selection of fewer continents does it in `_claim` (`_coastal_zones` are the zones
  filed under a continent, not an ocean; America's legacy canvas, `_claim_america`, takes no released
  zone, as in an America-only world).
- A small piece of replaced land that no canvas water joins up stays out of every canvas.
  `_rejoin_fragments` (all three continents) leaves out a fragment of a location that has a body in the
  canvas; `_without_islets` (fewer) leaves out every piece of the union of the canvases below
  `ocean_speck_limit` that holds replaced land and no island site: American pockets of America with
  Africa or Oceania among them, and a small island lying wholly among retained waters (the retained
  shores keep a guard of open water, so such an island has no shelf: Raja Ampat's Maden in an
  Oceania-only world).
- `continent_world.absorb_land_fragments`, now run for every composed world, gives the pixels of those
  pieces the colour of the retained location round them (recorded among the ocean identities' patches, the
  only changes allowed outside the canvas), the inverse of `absorb_ocean_specks`. A location with no
  pixel left is `Canvas.drowned`, and `relocated_canvas` counts it as removed.

The export fails (`enclosed_small_sea_locations`) on a generated sea location under the least size with
no generated neighbour, in every composed world. Measured on the plans: with all three continents,
retained zones touching replaced land 34 → 7, border 3,963 → 641 px (the zones that also touch a retained
shore stay and still show the old coast along part of their edge), small generated sea locations 11 → 0.
With fewer continents, zones that touch replaced land and no retained land 50 → 0 (Africa alone), 70 → 0
(Africa with Oceania) and 54 → 2 (America with Africa; the two are Alaskan bays filed under the Pacific,
which America's legacy canvas leaves out as it does in an America-only world), and canvas pieces below
the limit 16 → 0, 29 → 0 and 20 → 0 (Oceania alone had two); the exports of Africa, Oceania, Africa with Oceania, America with
Africa and America with Oceania at seeds 101 and 202 pass every validator. The all-continents world
installed on 2026-11-22 and the America-only epoch-64 reference come out byte for byte. [V-EXEC]

The game still has distinct `america`, `africa` and `oceania` hierarchies. Reuse
regional and area keys where their script meaning can be matched to the new
geography. Ports, straits, sea lanes, currents, trade paths and the rivers at the
wrap derive from the composed world. Apply the American overseas and Treaty of
Tordesillas rules to America, with a distinct contact policy for Africa's natural
boundary. Derive initial discovery from each region's role in 1337 and its actual
contacts, retaining the American discovery behavior for America-only worlds.

Vanilla setup outside an enabled footprint remains in place. The 1337 setup of
EU5 1.4.9 build 26655995 has 1,566 countries with land. Only Morocco and the
Mamluks own locations both in Africa and abroad. This counts all starting
ownership entries, including conquered land. [V-LOCAL]
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

All four options use the existing population cohorts in Iberia. The choice
belongs to Africa's settings and is available in both windows and the CLI.
The offline setup trial exercised all four choices on the same map.

### The Mamluks' Asian holdings

**Keep Mamluks** is the default when Africa is generated. The Mamluks keep
their tag, government and all 75 Asian holdings, including conquered Iskenderun.
Their 68 original African holdings are replaced by the 68 passable generated
locations closest to their Asian territory, using the same wrapped distance
as for Morocco.
Morocco's reservation takes priority if both claims reach the same location.
The 54 holdings nearest the original Cairo become cores, including the new
capital, and the other 14 start integrated. Both reservations are made before
African societies claim land. The 1337 setup binds references to Cairo to the
new capital where a location replacement is called for.

**Independent Sultanate of Damascus** gives those 75 Asian locations to a
new Sunni Levantine monarchy with a fresh tag and capital in Damascus. The
Asian populations remain in place. The Mamluks retire from the start and
African societies can settle the land that would have been reserved for them.

[V-EXEC] Both options exported on the same geography with EU5 1.4.9 build
26655995. The location and river rasters and location hierarchy match between
the two worlds. The exported 1337 setup gives the chosen country every Asian
holding under a single owner and preserves the Asian population records.
The restoration gives the Mamluks 68 populated passable African locations
outside Morocco's reservation. The independent sultanate has a fresh tag and
its name and adjective in all 11 official languages.

## One generation pipeline

1. **Plan the domains together.** Read and calibrate the installation once.
   Use a registry of continent definitions that supplies the vanilla footprint,
   coast and contact policy, supported presets and societal calibration. Resolve
   ocean claims by wrapped distance from substantial land, with a seed-based
   displacement of the ocean fronts. Assign the entire open ocean when all
   three continents are enabled. Keep the original geography of the
   fourth canvas, including named tolls and the Eurasian shore. Build
   compact, wrap-aware windows or row bands with a halo where a kernel
   needs surrounding geography.
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
once. The confirmed target applies to the combined export at the reference
presets and worker budget.

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
