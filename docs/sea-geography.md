# Sea geography

Sea geography, optional ocean expansion and the route/current refinements below ship in the accepted 1.0.0 scope (C437). Dated observations describe their particular revisions; an UNKNOWN engine detail does not automatically require a new owner sitting. See [known limitations](known-limitations.md) for current player scope.

**Crossings as chains of cells, thin remainders and the water at the join, pending 1.1.0 / epoch 60
(owner's report on world `aszzsukifw`, 2026-11-01):** four screenshots of the owner's world showed sea
locations with no reason to be shaped as they were. [V-GAME owner; matched to files V-LOCAL] Measured in
the owner's installed files: (1) a perfectly rectangular strip one sea-cell wide (120 px), 1,000 px long,
in open ocean, with cells ruled by its straight sides (`rnw_sea_00271` and its neighbours); (2) a
diagonal strip of the same kind, with arrows; (3, 4) remainders of the game's current zones that the
canvas's boundary cut along their length (`atlantic_north_equatorial_current10`: 6,400 px, 23.9 px
thick, a bent bolt with a long tail). The causes are three rules that no longer hold:

- `designed_corridors` drew each crossing as a band of one sea-cell width and the sea cells were
  partitioned inside the bands and outside them separately, so a crossing's borders were the band's
  ruled edges and the cells beside it were cut against them. The crossing's planning is unchanged
  (`sea_corridors.corridor_paths`: the coarse water graph, the detour test, line-of-sight straightening)
  but its cells are now made like every other: `newworld._sea_cells` partitions all the water once, the
  jittered-grid sites that lie within 0.75 sea-cell widths of a crossing's centre line are dropped, and
  one site every sea-cell width along the line (moved by at most 17 % along it and 12 % across it) takes
  their place (`corridor_sites`, `clear_of_corridors`). The cells of the chain are Voronoi cells whose
  sides are the bisectors with their neighbours, as in the game's own lanes. A cell belongs to a crossing
  (and so is a lane when a current can reach it) when the one-pixel centre line runs at least 24 px inside
  it (`eu5_seas.DESIGNED_MIN_PX`), no longer when half of its area lies in a band.
- `eu5_canvas.MIN_THICKNESS_PX` is 30 (it was 20): a remainder thinner than that, less than two thirds of
  the thinnest core of a zone of the game (50-80 px), goes to the canvas whole. Twelve zones of the
  installed map are replaced instead of trimmed (`atlantic_north_equatorial_current10`, `11`, `12`,
  `atlantic_south_sainthelenacurrent9`, `atlantic_southcurrent42`, `pacific_north_current84`,
  `pacific_polynesia_current28`, `north_pacific_high_sea42`, `clarence_gulf`, `shishmarev_inlet`,
  `sevuokuk_point`, `kongkok_bay`); the canvas grows by 68,000 px (0.1 %). A morphological opening that
  would have taken only the tails of the remainders was tried first and gained 1,376 px: the bolts are
  strips as wide as 40-50 px, not tails.
- The land stage keeps the land `newworld.EDGE_WATER_PERMILLE` (30 ‰, 302 px on the installed canvas, about
  two and a half sea cells) away from the canvas's boundary with the game's map, the Old World and the
  waters kept whole (the polar edges of the map are not such a join and get none). The band joins the
  coast ramp's guard, so the coast ramp starts at its inner edge; the land share is kept by raising the
  share of the narrower interior. The Wall passes the real boundary, not its own cleared course.

Measured on the owner's world code (`continents`, seed 11119257615139082485, the epoch-60 build): land
33.0 % of the canvas before and 33.1 % after; the land's least distance from the boundary 150 → 476 px
and its first percentile 267 → 632 px; sea cells longer than three times their width 34 → 15 and thinner
than 25 px 34 → 35 (the rest are narrows and the great closed zones, whose long coasts make them
thin by the perimeter measure); thin remainders (under 30 px) of the game's zones 12 → 0; deep-ocean
cells 241 → 337, lane cells with a current 174 → 200 (more open water far from land). The export
passes every sea invariant. [V-EXEC; in-game appearance UNKNOWN]

**Currents as clear courses, pending 1.1.0 / epoch 60 (owner's QU3N report, 2026-11-01):** the
owner's screenshots of world QU3N showed currents where the generated canvas meets the Old World that
no one could read: a current of three locations that pointed sideways beside a coast, a stub of one
cell next to a lane, a cluster of arrows pointing different ways, and one current in which two opposite
directions met. The cause is measurable on the world (`continents`, seed 12037730821817090414, the
epoch-60 build): of 265 current cells in 18 connected pieces, 11 pieces (including a 48-cell one) had no
zone of the game touching them at all, 14 pairs of neighbouring cells pointed at each other and 8 pointed
away from each other. The old rule interpolated every lane cell from its four nearest sources *through
any navigable water* (inverse-square weights, bent away from land, smoothed, then aligned to a straight
corridor's axis), so nothing required the arrows to form a path. [V-EXEC; engine drawing UNKNOWN]

The rule is now the one the owner stated: **either a clear, logical current, or none** (a first
version of this change also dropped the long straight currents through the generated oceans, which
the owner wants; they are back, below). The lane planner still decides which deep water is
navigable (routes, crossings, completed ends); a navigable deep cell carries a current only when
the cells form a *course* (`rnw.currents`, below). Every other lane cell stays navigable deep
ocean without `movement_assistance`, as one of the game's 750 deep zones is [V-LOCAL 1.4.3 C234];
nothing about ships, ports, routes or names changes. There are two kinds of course: a
*continuation* of a current of the game into the generated water, and a *crossing* of open water,
whose direction is that of the game's gyres at its place. In QU3N (the owner's world, rebuilt with
a peoples roll) 182 of the 248 lane cells keep a current; no two neighbours point at each other and
no arrow points against a zone of the game that touches its cell. Exports of continents 1000,
archipelago 42, The Wall 9 and islands 7 with the same code pass every sea invariant and keep 164, 89,
135 and 80 current cells. [V-EXEC]

A second report of the same day (the owner's The Wall J4VJ, 2026-11-01) found a long straight line
of prepared lane with no current beside a cluster of arrows, and a wide cluster of arrows pointing
every which way round retained islands. The first was a straight crossing whose deep cells are split
by shallow strips: each deep piece was too short to be a course, and a small side twig at a junction
then ate the end of the crossing as a "short branch". The second is a stretch of lane several cells
wide, a sea of deep cells and not a lane. Courses now run through the shallow strips of a crossing
(only its deep cells get the arrow), lengths are measured along the path in typical cells, a short
chain that continues the straight path through a junction is the course and not a branch, and a cell
with eight or more lane cells within 2.2 typical cells (a wide stretch) carries no arrow. [V-EXEC]

**Sea-cell slivers, pending 1.1.0 / epoch 60 (same report):** some generated sea locations are long
and narrow, like a needle or a crescent round a retained island's footprint. A coast, a crossing band
or a footprint cuts a Voronoi cell into pieces that were merged only by area, so thin pieces survived.
Measured on J4VJ, 42 of 1,547 sea cells were thinner than 20 pixels (twice area over perimeter; a
square cell of 118 pixels is 59), the longest needle 212 × 20. A cell thinner than a fifth of the
sea-cell spacing whose perimeter is at least 40 % other sea cells now joins the neighbour it shares
most with (`synth.merge_slivers`), unless the neighbour touches the edge of the generated world and it
does not; a strait, bordered by land, stays. Long cells that are not thin (a strip 222 × 55) and the
thin tails of otherwise fat cells are not changed. [V-EXEC]

**Thin remainders of trimmed zones, pending 1.1.0 / epoch 60 (same report):** the "tall narrow
triangle touching six neighbours" in the owner's Pacific South was not one of those cells. In the
owner's installed J4VJ files the only location that fits (tall, tail, six neighbours) is
`pacific_south_current2` [INFERRED from the description], a location of the game that the canvas
trimmed to 29 % of its area (3,963 of 13,889 pixels): a strip 219 × 47, 12.6 pixels thick, with a
long tail, touching six neighbours. `merge_slivers` works on generated cells and never saw it. A
remainder is now taken into the canvas, with the zone it belongs to, when it is smaller than 3,000
pixels (the old rule) or thinner than 20 pixels (`eu5_canvas.MIN_THICKNESS_PX`, 30 since the report above; the game's zones are
50–80 pixels thick at their cores). The canvas does not depend on the preset, so every world loses the
same two zones, `pacific_south_current2` and `atlantic_equatorial_countercurrent18` (3,723 of 19,542
pixels, 16.9 thick, five neighbours); the next thinnest remainders are 20.4 and 22.2 thick and stay.
J4VJ then has 1,500 generated sea cells, 11 thinner than 20 pixels (jagged coastal cells, not
needles; 33 before) and none of the old needles. [V-EXEC]

**Colonial overseas boundaries, pending 1.1.0 / epoch 60 (issue #9):** in wide ocean canvases,
coastal sea areas assigned to generated American land regions could directly touch passable Old World
sea zones. The EU5 engine's colonial overseas rules check sea connectivity: coastal borders between
American and Old World passable water can break colonial nation formation and overseas territory
status for North and South America. Connected ocean-area boundaries now separate passable American
coastal sea areas from Old World seas, preserving continuous naval routes while keeping American
regions strictly overseas. Final-map export validation explicitly verifies that no passable American
coastal area borders an Old World sea area. [V-EXEC C456]

**Routes on the actual geography, 0.13.16 / epoch 53:** the owner's 4TXC
example exposed a defect in the preceding acceptance criteria. A copied crescent
of current had only six pixels of contact at one end, while its arrows pointed
across the passage into closed water. Reachability and an edge count did not
establish a complete, correctly directed current. [V-GAME owner / V-EXEC C408]

Internal vanilla current footprints are now directional samples, not mandatory
lane outlines. Continuous routes are selected from actual generated shores and
currents entering the replacement boundary. An unowned canvas boundary is not
treated as a coast. Deep-route interfaces require a shared opening of at least
half the typical sea-cell width, measured from the final raster in strips; this
is a generator geometry policy, not an engine movement limit. Natural shallow
channels retain all their contacts. A one-location passage without another
current location or a live boundary current is ordinary, navigable sea. The
current direction of a clear two-sided passage follows its actual exits,
including exits into ordinary sea. These choices precede final zoning and are
checked again on the folded water graph. [V-EXEC; engine result UNKNOWN]

**Crossing direction, 0.13.14 / epoch 51** (superseded in pending 1.1.0: arrows follow the course
above, and the band-axis computation was removed): connected designed bands with a
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
(Superseded in pending 1.1.0: a crossing is a chain of ordinary cells along its centre line,
see above.)
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

## Currents (`rnw.currents`)

A current is a **course**: a directed path of lane cells. A *continuation* is a piece of lane that a
zone of the game touches along its direction; a *crossing* is a piece that none touches (the long
straight lanes through the generated oceans). The planner (`flow`) works on the lane cells only and
draws no random number; ties go to the lower cell.

1. **Evidence.** For every edge between neighbouring lane cells, the zones of the game that touch
   either cell vote by the cosine between their vector and the edge's heading; a lane that ran over
   the cell before the canvas replaced the sea (`courses`, at least half the cell) votes at half
   weight and can direct a course but never anchor one.
2. **Field of gyres.** At every lane cell, the interpolation of its four nearest sources (the touching
   zones and the old lanes that covered at least a quarter of a cell; inverse square of the distance
   in typical cells), fading over twelve typical cells into the zonal current at the cell's latitude
   (the sources within a Gaussian of four typical cells of its row: westward in the trades, eastward
   in the westerlies, as the game's own run). Its length is how much the sources agree. It votes on
   each edge at a twentieth of a contact, so it directs open water and never outweighs a zone of the
   game.
3. **Spanning tree.** Each connected piece of lane cells becomes a minimum spanning tree by centroid
   distance, so a band two cells wide is one chain with short twigs.
4. **Orientation.** Exact dynamic programming directs every edge to agree with the evidence as well
   as any orientation can, with the structural rule that water that enters a cell also leaves it.
   A cell where it cannot (a spring or a sink in the middle of a course) is *cut* out at a cost; a
   stretch that one cell in the middle or two at an end support is reversed instead, so a lone zone
   never splits a course, while a stretch that three or more support is a course of its own and the
   cut keeps both.
5. **Heading.** Each cell's direction is the heading from two cells upstream to two cells downstream
   along the longer way, so the arrow follows the path round bends and never points across its lane.
   The strength is the mean of the game's currents it continues.
6. **Shape.** Lengths below are in typical cells along the path (a crossing's cells are long strips).
   The navigable cells of a straight crossing that are not deep (*connectors*, the designed cells that
   are not lanes) are nodes of the course but carry no arrow. A cell with eight or more lane cells
   within 2.2 typical cells (a sea of deep cells, not a lane) is not on any course.
7. **Pruning**, repeated until nothing changes: a cell that the zones touching it oppose (sum of
   cosines below −0.5); a side branch shorter than five typical cells that no zone anchors and that is
   not the straight continuation of the path through its junction; neighbours whose
   arrows point at each other or more than 120° apart (the cell that disagrees with most of its
   neighbours gives way); then each piece. A piece that a zone touches along a lane stays only if a
   zone *anchors* it (a summed cosine of 0.5) and it runs six or more cells, or it joins two zones
   of the game (an anchored source and an anchored sink) at any length of two or more. A piece that
   no zone touches along a lane is a crossing: each straight run of it (until its heading has turned
   60°) needs at least four cells, a field of mean length 0.3 and a mean cosine of 0.25 with it
   (within about 75° of the gyre); a run that fails is dropped, so a crossing that runs across the
   flow, or lies where the gyres disagree (the equatorial counter-current belt of the game), has no
   current.

The export refuses a world whose finished vectors have two neighbours driven head-on
(`check_courses`) and one whose currents lie on a cell that is no lane. [V-EXEC; in-game appearance
UNKNOWN]

## Lanes and closed ocean (`rnw.lanes`, `rnw.sea_corridors`, `rnw.eu5_oceans`)

**Current bands, 0.13.11:** the generation canvas reads the footprints of the installed game's
replaced deep-ocean currents. The world generator partitions ocean inside and outside these bands
separately; sea-cell borders do not wobble across the band edges. Thus the old current's outline,
clipped by the new land, is built into the sea locations instead of approximated by whichever random
locations it happens to overlap. (Since pending 1.1.0 the bands only give the planner its offshore
terminals and the sea cells are one partition; see "Crossings as chains of cells" at the top of this
page. Sea-cell borders still do not wobble.) The band raster is part of the land cache key. Coastal settlement,
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
- **Currents.** Arrows are on the cells of a clear course only (`currents`, above); the rest of the
  lanes are navigable deep ocean without one.
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
- **Crossings.** `crossings.sections` finds opposite physical shores inside bounded windows,
  independently of location borders, and chooses their shortest water-only segment, including
  diagonals. Its complete raster supercover must contain one sea cell between two distinct,
  passable land locations. A land walk shorter than eight location edges excludes the link;
  eight is the generator's utility policy, informed by the installed game's
  `AI_CIRCULAR_STRAIT_DISTANCE_THRESHOLD`, not a file-format restriction. Vanilla-width links
  between different landmasses remain eligible. Wider or same-landmass links must be real
  throats: cutting the water segment in a local window separates two substantial waters, each
  reaching clearance at least the throat width from land. A uniform channel or a coastal nick
  fails this test. Nearby candidates connecting the same physical landmasses collapse to the
  shortest section (centres within 72 pixels). The maximum section length is 37 pixels between
  land pixel centres. A vanilla-width link without a physical throat is kept only once per
  landmass pair, with a real throat preferred, so a long uniform narrow channel cannot get
  another link at each location border. The pinch construction retains its original 9-pixel
  cutoff: coasts are unchanged.

**XNKG corrections (C466 → C467), EU5 1.4.6 / build 26300913.** [V-LOCAL] The original
missing mouths have axis-aligned runs of 17 sea pixels (`rnw_loc_04853`–`rnw_loc_04867`,
through `rnw_sea_00610`) and 1 (`rnw_loc_05265`–`rnw_loc_05290`, through `rnw_sea_00673`).
The 8-pixel run previously called a third mouth (`rnw_loc_05860`–`rnw_loc_05926`) is a nearby
coastal indentation with a short land walk; that attribution is corrected here. C466's broad
36-pixel rule wrote 61 crossings instead of 5 and changed only `adjacencies.csv`, but its
offline validity did not establish sensible placement. [V-GAME owner, 2026-11-02] The owner
rejected it after seeing lines along shores, parallel duplicates and same-shore shortcuts.

[V-EXEC C467] Applying the physical-throat rule to XNKG's written raster gives 11 crossings.
The two parallel Moana/Wahilaki lines (`rnw_loc_00375` to `00397` and `00404`) disappear,
as does the false 8-pixel coastal shortcut. The Locsamsol line (`00379`–`00401`) moves from
a 37-pixel horizontal run along the shore to the diagonal `(1300,3198)`–`(1303,3191)` in
raster row/column coordinates, length √58 ≈ 7.6 pixels, entirely in `rnw_sea_00120`.
The missing 17-pixel mouth similarly becomes a √29-pixel diagonal section; the 1-pixel
mouth stays. The geometry is computed from the physical shores, with no change to their
shape and no shader or define override. Local evidence: ignored `local_data/strait-crossings-v2/`.
New engine rendering is not claimed by these raster checks.

[V-EXEC] A full fresh XNKG export agrees exactly with the independently reconstructed raster
sections. Compared with original XNKG, only `adjacencies.csv` changes outside `.metadata`.
The installed candidate is **RNW: XNKG — narrow straits**, `rnw_exp_world_akhvvjfa6f`.

The export reads `adjacencies.csv` back (`verify_crossings`): each row names two land cells
and a sea cell that touches both, its points lie on their respective cells, the Euclidean length
is bounded, the entire segment stays in its named sea, and its coordinates exactly match the
planned section. The rows are exactly the world's crossings. The game's surviving rows outside
the replaced Americas stay. C246's six reference crossings and 135 retained rows record the
original 2026-10-24 world and build, not fixed counts for later geography.

## A fault this uncovered

The planner of sea areas gave each land region the water near its shore by growing parts from its
shore zones; a part whose zones another part reached first could end empty, and a region with a
handful of shore zones got water by luck. The reference world's Caribbean has 3 shore zones and five
areas named by the game's scripts; with the merged cells it got none, and the export (rightly) refused
the world. Now the shore zones of a region are pinned to it, and a region with fewer shore zones than
six for each of its areas takes the nearest free water to make up the need (`_reserve`), so every
vanilla coastal area has water on every preset tried (C237).

## Original S1/S2 research limits (2026-10-24)

These statements record the C244–C247 snapshot. C248 subsequently records the
owner's positive sitting and disappearance of the port errors. Later route and
current planning at the start of this page supersedes the old lane-end model;
the remaining engine questions retain their observed scope, not a new test request.

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
  new water [UNKNOWN at that revision, C244; later observations C248, C419].
