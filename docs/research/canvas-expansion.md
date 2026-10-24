# Expanding the New World into the oceans

2026-10-24. The assessment below describes 0.11.6; the approved implementation
is in **0.12.0, epoch 30** (C282–C285), recorded after it.
Claims C280–C281. The owner proposes a fixed, wider generation domain, including
the American side of the Atlantic and Pacific, while retaining the Old World,
important islands and the names of surviving vanilla oceans.

## What currently constrains the land

[V-EXEC C280] `eu5_canvas.select_canvas` starts with the installed `america`
continent and adds eligible Atlantic/Pacific sea pixels within `ocean_band_px`
(1,600 in both base presets). It excludes a 96-pixel guard around all other
continents, including their sea locations. The envelope still depends on vanilla
America's outline.

For every cut ocean location, the selector labels its remainder. If two remaining
components have at least 3,000 pixels each, it withdraws **every pixel of that
location** from the canvas. This preserves the retained location's connectivity
but makes a large closed ocean an obstacle even inside the distance band.

[V-LOCAL / V-EXEC C280] Read-only audit of the current installation: Steam manifest
build 26142040 (the previously recorded 1.4.4 executable on 1.4.3 data), map-contract
SHA-256 `592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
The final canvas is 37,978,627 pixels. These installed `ocean_wasteland` locations
all lose their proposed contribution:

| Location key | Pixels in the initial band/guard proposal | Remainder components of at least 3,000 px | Pixels in the final canvas |
|---|---:|---:|---:|
| `north_pacific_ocean` | 4,068,052 | 2 | 0 |
| `south_pacific_ocean` | 2,426,942 | 3 | 0 |
| `pacific_capricorn_tropic` | 2,315,750 | 3 | 0 |
| `atlantic_capricorn_tropic` | 2,900,548 | 2 | 0 |

This is a diagnostic of the existing algorithm, **not** a new boundary. Its script,
counts and downsampled map remain in ignored `local_data/canvas-expansion/`; no
derived raster is committed. [INFERRED C280: selector and audit above] Increasing
the band alone is not a reliable solution: it still follows America and the
whole-location rejection can still exclude the desired ocean pixels.

## Feasible direction

[V-EXEC C281] `newworld.generate_new_world` already accepts an arbitrary domain
mask. The exporter writes the final locations raster and derives the world from
it. `eu5_newworld` joins generated open-ocean **areas** to retained vanilla areas
through boundary contacts. `eu5_seas` and `lanes` account for retained islands,
ports, passable lanes and currents.

[INFERRED C281: those interfaces] This proposal fits the existing architecture.
It needs a new canvas policy and ocean-identity planning, with checks of dependent
layers; it does not establish a need to modify the engine. Proposed contract:

1. **A fixed envelope per supported map contract.** Define the American ocean
   sector independently of seed and coastline, with broad longitudinal limits.
   Its main latitudes can approach a rectangle, with exceptions near Alaska and
   protected lands. Derive the mask from the player's installation and versioned
   rules; do not distribute a vanilla raster.
2. **Protected lands and ocean separation.** Preserve the Old World and retained
   islands, including Hawaii and Polynesia, with required surrounding water and
   contacts. A local island guard and the broad ocean separating the continents
   are separate constraints: the existing 96-pixel guard alone does not establish
   a suitably wide intercontinental sea.
3. **Ocean cuts are intermediate bookkeeping.** Plan a connected retained
   remainder or explicit separate identities where needed. Do not drop a whole
   ocean because the first cut leaves several large fragments, and do not remove
   that rejection without replacing its connectivity guarantee.
4. **Land grows within the new domain.** The old coastline is no internal
   boundary. Retain water along the domain's outer edge and the terrain-wrap guard.
5. **Ocean identity follows final water.** Preserve or reshape surviving closed
   ocean locations as below. Derive coasts, lanes, currents and ports from the
   finished geography, connecting them to retained navigation routes. Plan the
   final labels before serialization; do not repair the exported mod afterward.

[V-LOCAL C281] `south_pacific_ocean` reaches across the x wrap and far outside
the American coast. Its name alone is not a safe rule for complete inclusion.
Check every proposed whole-ocean inclusion geometrically against the protected
Pacific sector, islands and their water, even where they interrupt a rectangle.

## Preserving the right ocean identity

[V-LOCAL C281] The **location** `north_pacific_ocean` belongs to **area**
`pacific_north_equatorial_area`, under **region** `north_pacific_ocean_region`.
Its localized name is distinct from the identity of its parent area.

[V-EXEC C281] The name planner references vanilla **area** names for generated
open-ocean zones, whose locations receive new keys and colours. Area reuse alone
does not reconstitute the single vanilla ocean location requested by the owner.

[INFERRED C281] Keep the original location key, colour and localization for the
connected union of its retained and regenerated **closed** water. The result is
one location with a changed outline, potentially containing islands or bordering
a new continent; the two temporary halves need not be separate final locations.
Coastal water and navigable lanes must remain separate passable locations. Reuse
the installed localization in every official language.

If land or lanes disconnect that union, use separate location identities while
retaining the shared ocean name or geographic parent as appropriate. Do not force
disconnected geometry into one location for its identifier. If a wholly replaced
ocean has no suitable water left, its location and emptied hierarchy nodes need
explicit removal/reference decisions. The current sea-area planner reserves a
source for every wholly replaced ocean area; this must change for an ocean to
disappear without reserving water solely to preserve its name.

## Verification and limits

[INFERRED C281] Verify the domain is identical across seeds; protected pixels,
islands and contacts survive; retained and merged ocean locations are connected;
ports and the **passable** water network work; names, colours, hierarchy and script
references resolve; and the domain fits the location/resource budget. Exercise
continents, island presets and high land, including fully consumed and fragmented
oceans. An implementation changes output, requiring a new version, epoch,
reference world and verified installed candidate under the normal project rules.

[UNKNOWN C281] No expanded world was generated, installed or loaded in game.
The exact envelope, whole-ocean inclusion list and merged-location engine result
are unverified. Country-selection terra incognita also paints water in its cover
colour, so the covered screenshot alone cannot measure the actual land footprint;
C280 is established independently from installed labels and the selector. No
owner sitting is requested.

[V-EXEC] Verification of this documentation phase: locked offline dependency sync
passes; 53 existing canvas, New World, sea-adapter, sea-name and lane tests pass;
audit assertions and `git diff --check` pass. `make check` passes formatting and
lint, then stops at the pre-existing interpreter-discovery problem in basedpyright
(reports Python 3.14 and cannot resolve the Python 3.12 environment's packages).
The complete suite is not claimed to pass for this phase. No implementation,
version, epoch or generated-world digest changed.


## Approved implementation: 0.12.0, epoch 30

[V-EXEC C282] Both policies are available. `new_world.expand_oceans` is an integer
0/1 in the settings and the append-only world-code fields. It defaults to 1; the
World tab's translated checkbox and recommendation control it. 0 calls the old
selector unchanged. Codes predating 0.12.0 resolve an absent flag to 0, and seed
changes and layer rerolls preserve it. A new epoch still means an old code is not
promised to reproduce the old release's complete output.

The expanded policy adds the fixed x sector [1600, 6500) on the 16384-wide reference
map, scaled proportionally by map width, to the original northern extension at the
reference 1600-pixel band. These limits leave Hawaii and the western Pacific on the
protected side and Atlantic room before the African waters; protected Oceania and
other non-American continents' waters and their 96-pixel guards take precedence.
Only eligible Atlantic/Pacific sea pixels are added. On the fingerprint above the
mask has **53,240,944 pixels**, 40.19% more than the legacy **37,978,627**, and is
identical for every seed. Both sketches and saved land templates use the chosen
policy. The sector does not ingest `south_pacific_ocean` wholesale.

[V-EXEC C283] Closed-ocean remnants are labelled locally and encoded by row runs
(`Canvas.ocean_parts`). `eu5_oceans` assigns generated closed cells by installed
closed-water overlap and boundary contacts, then finds connected components of
generated cells and retained remainders. Each source's largest retained component
(or largest generated one when nothing remains) keeps its vanilla key and colour;
other components get collision-free new keys with `$original_key$` localization.
Several internal cells may be one final location through connected retained water.
New passable coasts and lanes are excluded from these unions. Serialization emits
each identity once and relocates retained locators to valid final points. No exported
mod is repaired afterward, and no water is reserved to keep a closed location alive.

Ocean identity splits can recolour retained ocean pixels outside the geography
canvas, while preserving their water and their name. The report therefore records
`outside_canvas_identical` truthfully and separately verifies
`outside_canvas_except_ocean_identities_identical`. The final identity cap includes
new remainder locations and counts aliases once. For the audited expanded reference,
329,005 outside pixels change only their closed-ocean identity; all 66,634,570
protected pixels and 21,728 protected hierarchy records remain unchanged. Each
changed/new closed-ocean location is connected. The independent port audit compares
the vanilla Arctic exceptions by source identity and exact old coastline contacts;
a 58-pixel `chukchi_sea` remainder beside `indigiir` retains an existing vanilla
port omission rather than constituting a new one.

[V-EXEC C284] Wider land exposed two old assumptions. The crossing planner now
requires its chosen through-zone to touch both land endpoints, including when a
short gap contains two sea zones. The N0 decision for
`discovered_any_in_americas_trigger` is explicitly REBIND/coast/S2; it is generated
from the finished American sea areas, so an old coastal region can become landlocked
and new coastal areas count. The installed OR/area shape is checked and missing or
changed anchors fail. Default land spacing is 53 px for continents, 47 for small
continents and 61 for supercontinents (island presets keep 46); the location-budget
estimate uses separate coefficients for the wider canvas. It rejects overcrowded
settings, and both physical and final identity counts retain the 32,000 cap.

The 60%-land supercontinent check (seed 99, location spacing 70) has 29,098 locations
before ocean aliases against an estimate of 29,340; physical connectivity, ports and
Old World contacts pass. This is a physical-model check, not a full export or an
engine result. No new material, object or spline binary layout is used; [R-004 of the
interoperability register](interoperability.md#r-004--expanded-geography-through-the-existing-visual-map-interfaces)
records the interfaces whose output now covers the expanded domain.

[UNKNOWN] No EU5 launch or owner sitting accompanies this phase. Expanded geography,
merged ocean identities and the newly rebound discovery trigger have offline
evidence only. Packaging and installation evidence is recorded in experiment 049.
