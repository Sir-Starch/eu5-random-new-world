# Sea geography

Generator 0.10.12, epoch 22 (2026-10-24; claims C232–C240). The generated New World was land with a sea
poured round it: every sea cell was `<random word> Sea`, a coastal zone could have no port, and the
game's own kinds of water (deep ocean with its currents, inland sea, narrows) were not used. This
page says what the water of a world is now, why, and what is not known until a game reads it.

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
sea without a row, but the 4 Arctic zones and 37 Arctic locations that vanilla itself leaves (C238).

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
  more (or water no land touches at all) → `deep_ocean`.

The reference world has twelve bodies (99, 11, 10, 8, 6, 5, 5, 3, 3, 3, 2 and 2 cells), 13
passages, and 204 coastal, 342 ocean, 1,193 deep, 157 inland-sea and 30 narrows cells; the five
presets give from 29 to 247 narrows and from 136 to 590 inland-sea cells (the island world, whose
archipelago is one great inland sea like the South China Sea) (C235).

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
| everything else | the name of its area | |

An area of the game's own oceans keeps the game's name and the generated zones refer to it by its
key (`$pacific_north_area$`, which every language resolves to its own text; the key is in the area
files of all eleven languages). An area of coastal water is named for the sea that fills at least
half of it, with a compass point when a sea has several areas (`Northern X Sea`, `Central X Sea`),
else a `Coast` (at least 40 per cent coastal cells), an `Ocean` (at least 70 per cent deep) or a
`Sea`. A province takes the name that at least two of its cells share, else its area's. 1,926 sea
cells of the reference world have 233 names (the first generated worlds had one each).

The words are English while the mod is written (the owner's rule of 2026-10-23); `seanames.TERMS`
is one pattern per kind of water, so the translation of L1 is one table. Names are drawn from the
land layer's seed and nothing else, so rerolling the peoples or the resources leaves them.

## Currents (`rnw.currents`)

The generated deep water continues the game's currents. Each generated deep zone takes the blend of
the currents of the game's zones that touch the generated water (79 generated cells touch the game's deep zones, in 126 contacts, in the reference
world), weighted by the inverse square of the distance through the water over
its four nearest sources, bent away from land within six scales (the part of a current that flows
into the nearest land is taken out, more the nearer it is), smoothed twice over its deep neighbours
and given the mean strength of the sources. Integer geometry and IEEE `+ - * /` and square root in a
fixed order: byte-identical on every platform. Deep water that no current reaches through water
(a pocket) takes the nearest one over the land; no source at all stops the export (`CurrentError`).

## A fault this uncovered

The planner of sea areas gave each land region the water near its shore by growing parts from its
shore zones; a part whose zones another part reached first could end empty, and a region with a
handful of shore zones got water by luck. The reference world's Caribbean has 3 shore zones and five
areas named by the game's scripts; with the merged cells it got none, and the export (rightly) refused
the world. Now the shore zones of a region are pinned to it, and a region with fewer shore zones than
six for each of its areas takes the nearest free water to make up the need (`_reserve`), so every
vanilla coastal area has water on every preset tried (C237).

## What is not done, and what is not known

- Crossings of straits (`adjacencies.csv` rows of type `sea`: 135 in the game, for the narrowest
  straits only) are not generated: how the engine uses them and whether a generated crossing would
  change the balance of islands is not known, and a crossing joins two lands that the geography
  separates [UNKNOWN C240].
- River mouths are not named (the game has estuaries and deltas), and a few sea cells of a pixel or
  a few dozen pixels remain along the seam and the canvas edge, as before.
- [UNKNOWN] Whether `error.log` is free of the port lines after this; whether the engine takes
  generated `deep_ocean` zones with their currents, `inland_sea` and `narrows`, a whole-value
  `$key$` as a location name and a province name, and how the map shows them; the Sea Currents map
  mode of the new water. The next sitting of a batch reads them (no sitting is asked for this).
