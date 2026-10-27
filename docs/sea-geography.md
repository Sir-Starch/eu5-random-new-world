# Sea geography

**Crossing direction, 0.13.14 / epoch 51:** connected designed bands with a
clear principal axis carry currents along that axis. Their shared direction follows
the aggregate projection of the inherited currents; an exact tie uses a deterministic
axis direction. Broad junctions keep their interpolated flow. The axis is computed
from integer moments of the band and no source-less current is manufactured.
[V-EXEC; engine rendering and movement UNKNOWN]

**Continuous crossings, 0.13.13 / epoch 50:** the generator plans a water-only
network on a coarse sample of the finished land mask before it partitions sea
locations. Shore-to-shore crossings are added where the existing coastal and
inherited-current network requires a substantial detour. A crossing's centreline
is straightened only across water at full raster resolution, widened to a typical
sea-cell width and clipped to water. Sea cells are partitioned inside the designed
bands separately; only bands reachable from a real current source become currents.
The final graph still checks local connections and course ends. A small, detached
retained-ocean remainder joins an edge-adjacent navigable sea if the principal
vanilla identity remains; a fragment surrounded by protected land stays intact.
This cannot guarantee an engine-rendered appearance: [V-EXEC; game result UNKNOWN].

**Crossings and sea-cell geometry, 0.13.12 / epoch 49:** water-distance regions
grown from geographically spaced shore stretches and retained-water contacts identify
crossings between distant coasts. An available voyage longer than twice the water-only
crossing opens that crossing, provided it connects to a reachable current source. The
shore spacing derives from water area and shoreline length. Closed patches without an
interior in the sea-cell graph are navigable when reachable from a current; isolated
basins without a source remain closed. Connected closed water is still folded once and
uses its area's or body's name, rather than inventing an ocean for each fragment.
Sea cells use deterministic Euclidean nearest-site borders, split into connected pieces
where the coast or a current band cuts them. Land generation is unchanged. [V-EXEC;
engine rendering and movement UNKNOWN]

**TR46 follow-up, 0.12.7 / epoch 37 (2026-10-25):** local shipping routes,
connected closed-water locations and access-preserving script replacements
supersede the older size-based zoning and global-connectivity-only rule below.
See [experiment 057](../experiments/057-local-sea-routes/README.md), C317–C320.
The local criterion is a generator policy: coastal water and retained navigable
contacts within six typical sea-cell widths by water get a route at most twice
that water-only distance. Distances sum integer centroid lengths; they do not
predict engine travel time or modify retained geography. Inherited current
lanes follow the band geometry described below; necessary deep cells open before closed components are folded.
Every connected generated closed component is one physical location, with the
existing connected vanilla-identity planner still applying at the boundary.
Genuinely distinct retained vanilla waters keep their identities. A removed
port maps to a generated port; removed navigable sea maps to navigable sea.
The same replacement is used by waypoints and callbacks. Missing compatible
destinations fail export. [V-EXEC C318; engine outcome UNKNOWN]

**S2, 0.12.0 (2026-10-24):** the generator offers optional, recommended ocean
expansion alongside the original canvas. Its fixed sector, connected named-ocean
identities, protected waters and offline verification are recorded in
[canvas expansion](research/canvas-expansion.md). The American coastal-discovery
trigger is rebound to the finished world's sea areas, so a formerly coastal region
can become landlocked without dangling script references. This extends S1; it has
no new in-game result. [V-EXEC / UNKNOWN C282–C284]

Generator 0.11.1, epoch 25 (2026-10-24; claims C232–C250). The generated New World was land with a sea
poured round it: every sea cell was `<random word> Sea`, a coastal zone could have no port, and the
game's own kinds of water (deep ocean with its currents, inland sea, narrows) were not used. 0.10.12
fixed the ports, the names, the topography and gave the deep water currents; the owner's first sitting
with it (2026-10-24) showed what it had missed, that the game's open ocean is closed to ships: 0.10.13
adds lanes and impassable water and 0.10.14 the straits an army can cross. This page says what the water of a world is now, why, and what is not
known until a game reads it.

## What the game does with water

Read from the installation and from the owner's logs, not assumed:

- **Ports.** `ports.csv` gives a land location one port, a row that names one sea zone it touches
  (no land location twice in 1.4.3's file, every port to an adjacent sea [V-LOCAL C233]). The map
  checker logs `Coastal Seazone '…' has no ports connected to it` in three forms (`NO POSSIBLE
  CONNECTOR ONLY!`, `ONE CONNECTOR ONLY!`, `Possible ones …`) for a sea zone beside a land
  location that no row names, and `Location '…' is coastal but has no port setup` for a land
  location without a row. The owner's log of 2026-10-23 had 96 lines for 48 zones and 4 for Bermuda
  and Saint Helena, and the offline reproduction on the same land gives the same three counts
  (28, 17, 3) [V-GAME/V-EXEC C232]. A sea zone beside only wasteland is not named by the checker.
- **Topography of water.** `common/topography` has `coastal_ocean`, `ocean`, `deep_ocean` (navy
  attrition 10, at most 40; `is_deep_ocean`), `inland_sea` (may freeze) and `narrows` (movement
  cost 1.2, frontage −2, blocks vision from sea). In the 4,860 sea zones of 1.4.3 the rule is
  almost exactly the number of cells from land: 1,515 of 1,527 coastal zones touch land, 1,110 of
  1,123 ocean zones are one cell from it, 691 of 750 deep zones are two or more; enclosed waters
  (the Mediterranean 248 zones with 44 narrows, the Caribbean 187, the South China Sea 500, the
  Baltic, the Persian Gulf, Hudson Bay, the Great Lakes) are `inland_sea` whatever their depth, and
  the 290 narrows all touch land [V-LOCAL C234].
- **Currents.** 749 of the 750 deep-ocean zones, and no other zone, hold `movement_assistance = {
  east north }`, a vector of 79 to 105 (about 92) that follows the real gyres (the north
  equatorial currents run west at about 90, the counter-currents east, the Gulf Stream east-north-
  east) and that the *Sea Currents* map mode draws as an arrow [V-LOCAL C236].
- **Closed ocean.** Most of the open ocean is closed to ships. 46 great zones of the topography
  `ocean_wasteland` (all of them, and one atoll, in both the `sea_zones` and the
  `impassable_mountains` list, the list "that blocks unit movement") fill 56 per cent of the sea's
  area, a median of 445,000 pixels each against 20,000 for a deep zone and 3,500 for a coastal one.
  Between them the 750 deep zones run as lanes one or two cells wide, two to four cells from land,
  that the currents follow (a lane cell's current points at its neighbour in the lane within a
  median 4 degrees); round the lands the coastal and ocean zones form a band that touches the
  closed ocean as often as the lanes. Everything ships may enter, the Old World's and the
  New World's, is one connected water. The owner's maps of 1.4.4 show the same: grey where the
  topography map and the *Naval Range* map have the closed ocean, teal where ships may go
  [V-LOCAL C241; V-GAME owner's sitting of 2026-10-24].
- **Names.** All the zones of the Black Sea are the Black Sea, the five central Mediterranean zones
  the Central Mediterranean Sea, 64 zones the North Eastern Atlantic, 49 the South China Sea, 33 the
  Caspian; the coast is full of bays, gulfs, capes, straits and coasts (109, 43, 96, 53 and 46 of
  the 587 distinct names have the word). The open ocean is named after its current. Zones without a name key are
  most of the map (4,095 of 4,860), so the game has a fallback that is not read here [V-LOCAL C234].

## Ports (`rnw.ports`, `rnw.eu5_seas`)

A land cell has one port and a sea cell that touches land needs at least one: Hall's condition on
the graph of land cells and the sea cells they touch. `plan_ports` serves as many seas as any
assignment can, by augmenting paths (a land gives a sea up when that sea can be served by another
land), and gives every other land the sea it touches longest; where nothing competes the choice is the
old one. `settle_seas` makes the condition true by construction: a sea cell that cannot be served is
made one cell with a neighbouring sea cell (a served one first, then an unserved one that shares the
shortage, then any; the longest shared border first), and the world is relabelled and derived again.
Nothing about the land changes, and no land is turned into something else. In the reference world
16 cells of 1,942 merge; across the five presets 2 to 28 (C235).

The game's own land that touches generated water is in the same graph. Vanilla land whose port row
named a sea zone the canvas replaced (Bermuda, Saint Helena) gets a row to the generated sea cell
it is given, with its old coordinates, and takes part in the choice like land of the world; the cells
round such an islet share its one port, which is why Bermuda's two cells became one. Vanilla land
whose row stays (a sea zone the canvas trimmed) can serve nothing generated: a generated cell beside
only that land stops the export with `PortError`, never a repair. Land that is not a land location of
the game's lists (Greenland's Eiriksfjord, Ascension, Gough: non-ownable, no row in 1.4.3) is no
connector and needs none.

The export reads its own files back (`verify_seas`): every row is from a land cell to a sea it
touches and no land is named twice, every coastal land has a row, every sea beside land is named by
one, and every sea template has the topography and, when deep, the current that was planned. An
independent check that reads only the written `locations.png`, `named_locations`, `default.map` and
`ports.csv` (as the engine does) finds no sea zone beside land without a port and no land beside the
sea without a row, but the 4 Arctic zones and 37 Arctic locations that vanilla itself leaves (C233).

## The shape of the water (`rnw.seas`)

Everything is measured on a coarse picture of the world (a pixel is about a twelfth of a *scale*,
the width of a typical sea cell, 118 px in the reference world) so a measure does not depend on how
big a cell is:

- **Narrow water** is what a closing of the land at one scale of radius fills (a gap narrower than
  two scales): a cell with half its water in it is narrow. A narrow stretch of cells that joins two
  waters (cells that reach each other within four steps through wider water are one water) is a
  **strait** (one or two cells) or a **channel**; one that ends is an **inlet**.
- **Enclosed water** is the same at three scales (a mouth narrower than six): connected enclosed
  cells are a **body of water**; a hole of the sea with no way to the outside (an archipelago's
  lagoon) is enclosed however wide.
- **Coast.** A sea cell that touches land is the water of an **island** when it touches only
  landmasses of six cells or fewer, otherwise a **cape** where little land (at most 12 per cent of a
  square of two scales round its deepest point) lies round it, a **bay** where much (at least 38)
  and a plain **coast** between.
- **Depth.** The number of cells from land through water. The game's topography is: narrow →
  `narrows`; in a body → `inland_sea`; touches land → `coastal_ocean`; one cell → `ocean`; two or
  more (or water no land touches at all) → `deep_ocean`, which the lanes then divide into the
  lanes proper (`deep_ocean`, with a current) and closed water (`ocean_wasteland`, below).

The reference world has twelve bodies (99, 11, 10, 8, 6, 5, 5, 3, 3, 3, 2 and 2 cells), 13
passages, and 215 coastal, 368 ocean, 157 inland-sea and 30 narrows cells, 420 lanes and 36 closed
zones (1,226 sea cells, folded from 1,942); the five presets give from 22 to 221 narrows and from
123 to 715 inland-sea cells (the island world, whose archipelago is one great inland sea like the
South China Sea) (C235, C243).

## Names (`rnw.seanames`)

A name belongs to a stretch of water, as in the game:

| Water | Name | Cells |
|---|---|---|
| passage | `X Strait`, `X Channel`, `X Sound` | all its cells |
| body of 24 cells or more | `X Sea` | its open cells (its coastal cells keep their own) |
| body of 6 to 23 | `Gulf of X` | all |
| body of 2 to 5 | `X Bay` | all |
| a run of coast, bay or cape in one province | `X Coast`, `X Bay`, `Cape X` | the run |
| water round small islands | `X Island`, `X Islands`, `X Archipelago` | all cells that touch the same islands |
| a closed zone | its body's or area's name | the geographic body or area |
| everything else | the name of its area | |

An area of the game's own oceans keeps the game's name and the generated zones refer to it by its
key (`$pacific_north_area$`, which every language resolves to its own text; the key is in the area
files of all eleven languages). An area of coastal water is named for the sea that fills at least
half of it, with a compass point when a sea has several areas (`Northern X Sea`, `Central X Sea`),
else a `Coast` (at least 40 per cent coastal cells), an `Ocean` (at least 70 per cent deep) or a
`Sea`. A province takes the name that at least two of its cells share, else its area's. 1,226 sea
cells of the reference world have 244 names (the first generated worlds had one each); 366 of the
cells refer to a vanilla ocean area by key.

Names are phrases (a kind of water, a word, compass points), written in each of the game's
languages by `wording` since 0.11.5 (*Northern Gulf of Akaira*, *Северная часть залива Акайра*,
*アカイラ湾北部*; [localization](localization.md) §3.3). Names are drawn from the
land layer's seed and nothing else, so rerolling the peoples or the resources leaves them.

## Currents (`rnw.currents`, `rnw.sea_corridors`)

A lane continues the game's currents. Each lane cell blends its four nearest sources through
navigable water, weighted by inverse-square distance, bends away from nearby land, and is smoothed
twice over lane neighbours. On a two-sided, approximately straight stretch or designed crossing
corridor (`_follow_designed`), it follows the band's principal axis when supported by source-derived
projections along it; junctions, ends and near-perpendicular sources retain their interpolated
direction. It takes the mean strength of the sources. A lane without a source reachable through
navigable water, or a cancelled direction, stops export (`CurrentError`); neither closed water
nor land supplies a shortcut. Arithmetic is performed in a fixed order. [V-EXEC; in-game appearance UNKNOWN]

## Lanes and closed ocean (`rnw.lanes`, `rnw.sea_corridors`, `rnw.eu5_oceans`)

**Current bands, 0.13.11:** the generation canvas reads the footprints of the installed game's
replaced deep-ocean currents. The world generator partitions ocean inside and outside these bands
separately; sea-cell borders do not wobble across the band edges. Thus the old current's outline,
clipped by the new land, is built into the sea locations instead of approximated by whichever random
locations it happens to overlap. The band raster is part of the land cache key. Coastal settlement,
connections and completed ends may still alter or extend the outline. This is not a simulation of
new ocean gyres. Course completion also looks for cyclic deep-water ends attached to the navigable
network at only one junction: a wide tip can have no degree-one cell and still lead nowhere. The
block-cut check joins terminal water only for analysis; no artificial connections are written. A
synthetic two-coast loop remains unchanged, while a one-ended loop is extended to the opposite coast.
[V-EXEC C401; in-game appearance UNKNOWN]

**Course ends, 0.13.2 (2026-10-26):** 657Q exposed a gap between two inherited
lane fragments which both already reached retained water, and two courses
ending far from a new coast. Global connectivity and the bounded local-coast
criterion did not require their completion. The initial lane plan now continues
each open-ocean end through closed deep cells to another lane, coastal water or
retained navigable water. It excludes its incoming stem and junction from the
destinations, prefers a destination within 45 degrees of its outward heading,
and chooses the shortest water-only path by integer centroid length. A search
stops at the first existing navigable cell: it cannot walk existing water to
pretend a forward destination was reachable through the closed ocean. If land
blocks every forward destination, the shortest reachable turn is chosen; if no
destination is reachable, generation fails with `LaneError`. Each added path
opens cells and cannot disconnect existing water. An independent export check
rejects a deep lane tip which touches neither coastal water nor a retained-water
contact. In 657Q the four original tips become zero, with eleven additional
lane cells, including the one-cell Ruaziasleir gap. [V-EXEC C349–C351;
engine movement after the change UNKNOWN]

Generator 0.10.12 made every cell two or more cells from land deep ocean and gave each a
current: 1,193 cells of the reference world, a ship could go anywhere, and the Sea Currents map
was an arrow in every zone, where the game has lines of arrows between closed ocean (C241). Now
the deep cells are told apart as the game's are:

- **Courses.** The canvas replaced 390 of the game's 750 deep zones (14 stretches of lanes, each
  joining two to twelve of the lanes that stay), and with them the course of the gyres through the
  Atlantic and the eastern Pacific [V-EXEC C242]. A generated deep cell over which such a course ran
  by at least half of its pixels is a candidate lane, with the mean current of what ran there (`courses_over`);
  where generated land cuts a course the lane stops at the coast, as the current would. A deep
  cell that touches a lane of the game's continues it. So the generated gyres lie where the
  game's did, and the game's currents at the edge of the canvas meet lanes.
- **Linked.** Every stretch of passable water (coastal and ocean cells, inland seas, narrows, lanes)
  must reach the game's own, so that a ship can come from the Old World to every coast. A stretch
  that does not is joined to water that does by the cheapest string of deep cells, which become a
  lane; a cell costs one, and three more for every cell it lies from land beyond three (a lane keeps
  to the coast). The reference world needed one cell, the presets none to three. A stretch no
  deep water can join (a sea that the land closes) is counted, not joined.
- **Closed.** The other deep cells are closed to ships, as the game's. Since 0.12.7,
  each connected stretch is folded into one physical location (`ports.relabel`):
  `topography = ocean_wasteland` in its template, and its key in both lists.
  The former target of 48 cells per zone manufactured adjacent unrelated oceans
  in TR46 and is removed (C317–C318). In the older S1 reference, 1,193 deep cells became 420
  lanes and 36 closed zones of 746,000 pixels at most; across the five presets 262 to 352 lanes and
  29 to 36 zones.
- **Currents.** A lane cell's current is the blend of the nearest courses and anchors through the
  water, bent away from the land it flows towards (`currents`). Arrows are on lanes only; the
  current rules above explain when the flow can be aligned with a lane's axis.
- **Land of the game's.** A sea cell that touches land of the game's own (Bermuda, Saint Helena,
  the land at the canvas's edge) is on a coast, whatever the generated land does: it is coastal
  water, never a closed zone. (The first run of 0.10.13 closed the zone that holds Saint Helena's port.)
- **No units.** The game's closed zones have no `combat` and no `unit_stack` locator (every other location has both; its vfx locators cover all): the generated closed zones have none either. The first closed zones had them and the engine logged `map object locator is incomplete` (C250), which `verify_locators` now reads back.
- **Checked.** The export reads its files back (`verify_seas`): the impassable zones, and only
  they, are in the impassable list and have no current; every lane is deep and has its current;
  every sea cell that is not closed is reached from the game's water. Read back from the mod's
  `locations.png`, `named_locations` and `default.map` alone, as the game does, the 1,190
  passable generated zones are in the one water of 4,500 zones with the game's, the 36 closed zones touch no land
  and every coastal land and every coastal passable zone has its port [V-EXEC C243].

## Straits and crossings (`rnw.straits`)

The game links two land locations that a narrow sea zone separates, "close enough to each other so
armies can cross it without the need of a navy" (`adjacencies.csv`, type `sea`: the two locations, the
sea zone between, a point on each). Its own 184 rows say what close is: the two points lie 1 to 9
pixels apart (median 3), each on its own location, and the sea zone touches both; 100 rows join
different landmasses, 84 two places of one landmass; an army that crosses is the attacker, with a
combat penalty, and the sea zone's control can blockade the crossing [V-LOCAL, SOURCE C245]. The
generated landmasses lay a sea cell or more apart, 100 pixels and more, so there was nothing to
write (the reference world had two pairs of locations within 12 pixels). Two steps, both in the land
layer's seed and nothing else:

- **Pinch.** Two landmasses of at least 2,000 pixels that come within 36 pixels of each other are
  brought together at their nearest points to a channel of 5 or 6 pixels: each grows the same
  distance towards the other (a disk of that radius round the facing coast), the growth tapering off
  over twice the gap, so the shores keep their shape away from the strait. Nothing is merged, no third
  landmass is touched (nothing is added within 6 pixels of one), no water is cut off, and no land is
  added where the coast margin or the canvas border forbid it; otherwise the pinch is not made.
  The channel is narrow
  water (`narrows`) and is named for it, a strait or a sound.
- **Crossings.** On the finished cells, every pair of land cells of different landmasses that a run
  of at most 9 pixels (the game's widest) of one sea cell divides along a row or a column is a
  crossing; its two points are on the narrowest run, one on each location, written as the game writes
  them (`eu5_seas.crossings`, `eu5_nw_export._crossing_rows`). The reference world has six, the
  presets 0 (a supercontinent) to 78 (the islands). Places of one landmass are not joined: there
  is no row for a bay, as the generated world has no estuary a path does not go round.

The export reads `adjacencies.csv` back (`verify_crossings`): each row names two land cells of
different landmasses and a sea cell that touches both, its points lie on its two cells, at most 9
pixels apart, and the rows are exactly the world's crossings. Read back from the written files alone
the same six pairs are found, and the game's 135 rows outside the replaced Americas stay (C246).

## A fault this uncovered

The planner of sea areas gave each land region the water near its shore by growing parts from its
shore zones; a part whose zones another part reached first could end empty, and a region with a
handful of shore zones got water by luck. The reference world's Caribbean has 3 shore zones and five
areas named by the game's scripts; with the merged cells it got none, and the export (rightly) refused
the world. Now the shore zones of a region are pinned to it, and a region with fewer shore zones than
six for each of its areas takes the nearest free water to make up the need (`_reserve`), so every
vanilla coastal area has water on every preset tried (C237).

## What is not done, and what is not known

- A gyre is not closed: where the generated land cuts the course of a current, the lane ends at the
  coast and the flow does not go round the land to join the lane behind it. Ships go round by the
  coastal water, which is passable.
- River mouths are not named (the game has estuaries and deltas), and a few sea cells of a pixel or
  a few dozen pixels remain along the seam and the canvas edge, as before.
- [UNKNOWN C247] Whether the engine lets armies cross by a generated row, with the penalty and the blockade, and whether the points are only the crossing's picture or also its cost.
- [UNKNOWN] Whether `error.log` is free of the port lines after this; whether the engine takes
  generated `ocean_wasteland` zones listed as the game's are (and keeps ships out of them),
  `deep_ocean` lanes with their currents, `inland_sea` and `narrows`, a whole-value `$key$` as a
  location name and a province name, and how the map shows them; the Sea Currents map mode of the
  new water. The next sitting of a batch reads them (no sitting is asked for this) [UNKNOWN C244].
