# N5: physical meaning for American region and area keys

2026-10-24. Owner instruction: implement N5. Generator **0.11.4**, algorithm
epoch **28**. Implementation and verification are offline; engine behaviour is
**NOT-RUN**. The installation is the 1.4.4 executable (Steam build 26142040)
on 1.4.3 data. No game launch belongs to this work.

## Design

[INFERRED design] Geography owns the assignment, before societies, technology,
development and stories. (Superseded for subcontinents and regions on 2026-11-06:
[place first](#place-first-for-regions-2026-11-06-c502).) Subcontinents keep the
established positional partition.
Within each subcontinent, compact connected regions are built without identities;
their keys are then chosen together by physical similarity. Within each resulting
region, the same matching gives its original area keys to compact areas. Extra
areas get new keys. Original parent relationships are retained: an area cannot
leave its vanilla region, and a region cannot leave its vanilla subcontinent.
Coastal sea areas still follow their region's shore and ocean areas their vanilla
remainder; their keys are outside the land matching.

[V-EXEC] The first implementation exposed a pre-existing limitation of positional
weighted region partitioning: the reference world's Chaco part had three cells
for four original land areas. The old planner omitted `moqoit_area` (C261).
Regions now start as comparable-sized parts, using the existing `split` kernel.
The matcher only permits a region where all its original land areas fit. There is
no post-export repair, dropped land key, arbitrary substitute or retry seed.
An impossible assignment fails with `RegionKeyError`.

### Child-capacity construction correction, 2026-11-04

[V-EXEC, RNW 1.2.0 development / pending epoch 61; EU5 1.4.7 / 26377361]
The H7 published islands/1000 case exposed a remaining construction defect. A
North American region shrank to one cell during Lloyd movement, while every
eligible vanilla region needs at least three child areas. The exact pinned 1.1.0
constructor rejects the same captured inputs. This finding does not change the
scope or acceptance of that release.

Region construction now supplies the multiset of original child counts to the
bounded partition optimizer. Capacity deficit precedes size error when choosing
handicaps; the optimizer selects its latest feasible Lloyd layout before keys or
physical profiles are assigned. If the search constructs no feasible layout it
fails explicitly. This adds no post-export repair, omitted key or seed retry;
the physical matcher retains its independent capacity check and parent tree.
Unconstrained partition calls retain their previous result.

Five synthetic regressions cover a 32-node irregular graph, complete child-key
assignment, coverage, connected parts, input permutation and impossible minima.
On the real failing input, all 184 areas cover the 4,761 land units and pass
contiguity checks. A fresh normal pipeline passes physical world checks and
reaches the native stage on the corrected islands/1000 case. Every captured
reference native input, including the complete hierarchy/name plan and key space,
remains equal to H4's reference. This comparison uses compact input captures, not
a new complete output reproduction or performance claim. Local evidence is in
`local_data/history-120/h7/hierarchy-islands-1000/` and `hierarchy-reference/`.

### Place first for regions, 2026-11-06 (C502)

[V-EXEC, RNW 1.2.0 development / pending epoch 61; EU5 1.4.7 / 26377361] The owner
found the window's region names absurd on candidate F: Central America beside Alaska,
West Coast on the east shore, East Coast inland, Colombia on an eastern island. The
assignment below let place break ties only, so no displacement could outweigh a
physical improvement, and the optimum of the whole parent group could send a key across
the continent: F's `central_america_region` had a climate difference of 935‰. The
subcontinent split had a second defect, seen on archipelago 73: two sources, on the two
largest islands, with every other island joined to the nearest of them, put the Andes
and Colombia north of Canada. This **replaces** the "position breaks physical ties
only" rule for regions and the positional subcontinent partition. Areas keep it. (The
subcontinent *bands of rows* below were replaced on 2026-11-10 by cuts at a landmass's
waist: [C529](#subcontinents-at-the-waist-not-along-a-row-2026-11-10-c529).)

- **Subcontinents** are bands of rows from north to south, in their vanilla order (by the
  row of their vanilla centre) and with their vanilla shares of locations
  (`hierarchy.banded_parts`). On each landmass a band keeps its largest piece; every
  other piece joins the band it has the most contacts with. Bands settle in order, and a
  settled band has one piece per landmass, so the result never has two pieces of a
  subcontinent on one landmass. Latitude alone decides: on a tall continent, both axes
  weighted equally gave South America the east side and left Mesoamerica in the
  south-west.
- **Places** are standardized point clouds (`eu5_regionkeys.standard`): each vanilla key
  and each generated part is one point, measured from its cloud's mean in its cloud's
  standard deviation on each axis, in integers. Location-weighted frames failed: Canada
  and the East Coast hold most vanilla locations, which pushed the southern keys to +2.7σ
  against +1.4σ for the southernmost of equal generated parts.
- **Regions** are equal compact parts with room for every child area, as before, grown
  from sources laid out as the vanilla regions lie in the subcontinent (`_placed`):
  `spread_sources` fixes how many sources each landmass gets, an exact assignment gives
  each region a source, and the source moves on its own landmass to the cell nearest the
  region's place. A region's cost is its physical difference plus **8** × the distance
  of the standardized points in permille. One σ of displacement then costs twice a
  complete climate mismatch, so physical similarity chooses only among parts in
  comparable places. On four captured worlds, every region key was the same at weights
  8–16; at 2 and 4, one subcontinent of one world differed.
- **Areas** keep `split` and physical-first matching, with place breaking ties (weight 0).
  Their layout inside a region is invisible (the world names them), while scripts read
  their land. Weight 8 at this level raised the reference's area physical difference by
  a third, 437,859 → 587,829; weight 0 gives 459,564.

Every report row now records `cost`, `physical_cost`, `place_permille` and
`place_weight` (`cost = physical_cost + place_weight × place_permille`). The
`positional_cost` and `moved` fields are gone.

[V-EXEC] Seven captured `_land_areas` inputs were tested: candidates F and B, the reference
(supercontinent), archipelago 73, islands 73, The Wall CWYS and small continents 7. All
cover every land unit and pass `_check_pieces`, in 0.8–2.2 s each, with identical results
under hash seeds 1, 7 and 12345. In every world Alaska lies north-west, Canada
north/north-east, West Coast west, East Coast east, Meso- and Central America at the
south of North America, Colombia at the north of South America and La Plata at its south.
The Caribbean takes the south-east of North America and can reach the north shore of the
southern landmass. A synthetic regression mirrors the climates of four vanilla quadrants:
every key stays in its quadrant, while the previous code put all four in the wrong one
(`tests/test_hierarchy.py`). Pictures and scripts: `local_data/region-layout/`.

| Reference (supercontinent 20261102) | Previous (epoch 61, efb4c82d) | Place first (8ceb035e) |
| --- | ---: | ---: |
| Physical difference, 14 regions | 42,238 | 45,768 (+8 %) |
| Physical difference, 135 areas | 437,859 | 459,564 (+5 %) |
| Worst region climate | 936‰ `central_america_region` | 906‰ `caribbean_region` |
| `central_america_region` / `colombia_region` climate | 936 / — | 79 / 86 |

The reference's northern landmass has no tropics. Whichever region takes its south-east
still lacks a tropical counterpart, which is the limit stated below, not a wrong place. Two
independent exports give `8ceb035e…` (884 files). Against `HEAD` (reproduced as
`efb4c82d`), 93 of 912 files differ, because location keys follow hierarchy order. The
pixel partition of `locations.png` is identical (29,371 colours, a bijection): only 28
closed-ocean remainders changed colour. No file or contact count changed.

### Profiles and assignment

[INFERRED design; V-EXEC implementation] A profile is the distribution of template
climates and relief, the share of surface in locations touching sea, and surface
area. Every location contributes its existing pixel count, not one vote. Lakes
belong to the land hierarchy and have lake relief; lake contact is not sea contact.
Wasteland relief is compared with the corresponding relief (`mountain_wasteland`
with `mountains`, mesa with plateau, high lakes with lakes).

Vanilla profiles are measured from the installed American templates and the
biome model's already computed contact pairs. Generated profiles read the final
biome tables, cell sizes and contacts. No extra raster pass, population, culture,
religion, resource field, random stream or source of entropy enters this step.

Each cost has four integer components in permille:

1. Half the L1 difference of climate shares.
2. Half the L1 difference of relief shares.
3. Difference in coastal shares.
4. Difference in surface shares of the respective parent.

Weights are **4 : 3 : 2 : 1**. These are explicit design weights, not a measured
game balance. A rectangular Hungarian assignment minimizes the total cost with
one distinct generated part per vanilla key. At equal physical cost, keeping
more positional assignments wins; remaining ties use sorted keys and stable part
order. No centroid or distance can outweigh a physical improvement. Boundaries
are final before scoring, so no rebalance invalidates the selected profiles.

Every world report's `generated.physical_keys` records each key, both profiles,
four differences, final cost, positional comparison cost and whether it moved.
R7b reads the final region and area keys as before; it needs no new trigger or
technology exception. N1's historical identity neutralizations remain mandatory.

## Verification

Synthetic tests cover global optimality against exhaustive permutations,
rectangular assignments, negative and tied costs, all four physical dimensions,
extra areas, pixel weights, relief normalization, required child capacity,
missing data, stable parents and connected boundaries. A regression represents
the reference's small region with four area keys. The adapter test excludes Old
World templates and proves that changing only resources changes no profile.

Full-world evidence, input/output manifests, positional consumer reconciliation
and installation records stay under ignored `local_data/n5/`.

### Three-world gate (C262-C264)

[V-LOCAL EU5 1.4.3 data; V-EXEC] N0 still counts 68 positional consumers in 27
files. Of these, 63 name a region or area: **61** name land keys scored by N5,
**two** name sea areas only. The other five name individual locations. All 14
American regions and 135 land areas receive one key each in every tested world;
every referenced region/area exists in the serialized definitions. Sea anchoring
and individual-location remapping retain their existing rules.

[V-EXEC] Costs below compare semantic and positional assignments on the **same
final partitions**, with the weights above. They do not compare gameplay quality
or imply that N5 reproduces the old region boundaries.

| World | Moved keys / 149 | Positional cost | Physical cost | Reduction | Land-key consumers: lower / equal / higher cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Reference, small continents, seed 7379108625698230220 | 121 | 761872 | 617770 | 18.91% | 53 / 7 / 1 |
| Continents, seed 210, extraordinary chance 1000 | 138 | 683823 | 531622 | 22.26% | 60 / 1 / 0 |
| Archipelago, seed 73 | 128 | 649803 | 505579 | 22.20% | 30 / 28 / 3 |

No parent group's total cost exceeds its positional comparison in any of the
three worlds. A consumer can still get a higher cost because it uses a subset of
the globally assigned keys. In the archipelago, `mesoamerica_region` has 896
permille tropical climate; in the reference it has 857 permille subpolar climate:
that world's northern subcontinent offers cold regions, and the parent constraint
does not allow taking warm land from the south. The Andes key likewise has only
69 permille mountains in the reference, against 388 in vanilla. These measured
limits remain visible in the report; historical names and identities stay
neutralized. The gate establishes complete and inspectable physical matching,
not an exact analogue for every historical mechanic.

[V-EXEC] Every full export passes its map, setup, content, localization and spline
checks. An independent audit verifies every written mod-file hash against its
manifest, all **21,728 Old World location records** equal as parsed records,
every original land-key parent, zero Old World contacts lost and identical
pixels outside the canvas. Against epoch 27, the reference changes 66 mod files:
among map-data files only `definitions.txt`; among graphics only the spline
network whose anchor indexes follow hierarchy order. Rasters, physical templates,
resources and the remaining graphics are byte-identical.

| World | Files except metadata | Output SHA-256 |
| --- | ---: | --- |
| Reference | 814 | `a05a8d4a8fe252f683613fdbc0951e022f18c2c4cefd353ea9ed91ea16ef0b46` |
| Continents 210 | 813 | `9fea7de59c138a3616cb7dd657be23bea74e09332d545bd6d8e23ee17884c9e2` |
| Archipelago 73 | 814 | `19509b61234c15cd5f31634ce4caecb877543d8865d29ffdfe31d49bb70f9d15` |

The reference code is `RNW1-0826C-SYW6B-MW73Y-C005G-80813-G0Q8H-SZ`.
The candidate is installed as `rnw_exp_world_6rf2nzt4dv`: all 816 installed files
match the source; nine profile-root files retain their hashes and 10,256 existing
mod files retain sizes and modification times. Existing folders and playsets are
preserved. Removal is recorded in [INSTALLED](../../experiments/INSTALLED.md).

### Reproducibility, layers and completed checks (C265)

[V-EXEC] `uv sync --locked --group dev && make check` passes: **1,344 Python
tests** (16 local/opt-in skips), **23 Rust tests**, formatting, lint and typing.
The read-only local suite passes **14 tests** with its two slow checks skipped.
The separate `PYTHONHASHSEED=7 RNW_REPRODUCE=1` reference test passes in 165.66 s
and reproduces the golden digest, including its N5 completeness/cost assertions.

Two further exports reroll the reference's layers and compare every non-metadata
mod file. Resources change exactly `in_game/map_data/location_templates.txt`,
leaving story starts unchanged. Peoples change 62 files under the existing
peoples-owned prefixes, change story starts, and preserve the resources file and
exceptional places. Neither reroll changes any physical key/profile/cost record,
map or graphics file. Evidence is in `local_data/n5/layers.json`; the three
complete land worlds and their independently checked manifests are in `audit.json`.

## Limits

This assigns the closest available generated territory under the hierarchy
constraints; it does not recreate historical America or promise that every key
has an exact environmental twin. An individual key can get a worse match so that
the complete assignment gets a better one. Position-based location remaps and
sea-area anchoring keep their existing rules. Three offline worlds cannot prove
campaign balance or engine behaviour. No separate owner sitting is requested.

No new closed format or binary-writing mechanism is introduced. This step reads
the existing text hierarchy and template interfaces; generated binary assets
continue through the existing exporters and stay local under the project's
distribution boundary.

### Subcontinents at the waist, not along a row, 2026-11-10 (C529)

[V-LOCAL, V-EXEC; RNW 1.2.2 development / pending epoch 63; EU5 1.4.7 / 26377361] The owner
generated two worlds from one drawn image with different seeds (preset supercontinent) and in
both the subcontinents were cut wrong, then said of a first fix that left South America at 12 %
of the land that nothing in the generator should make it smaller. Two defects, not one:

1. **The row.** A band is the cells ranked by row, so its boundary is a row, whatever the land
   is: a ruler-straight edge through two island arms (a strip of 25–29 cells of each became
   "South America") and through the mainland's neck. The `supercontinent` and `continents`
   worlds without a drawing show the same edge (`continents` 1001: 19,292 by the length below).
2. **One piece per landmass at the top level.** `_check_pieces` has demanded since 0.9.4 (C77,
   the owner's report of regions and areas in pieces) that no group at any of the four levels
   has two pieces on one landmass, subcontinents included, and C502's repair enforced it by
   giving the smaller piece back to the other part. The drawing has two peninsulas hanging south
   of the body: South America kept one and the other went to North America, so South America had
   13.0 % and 13.3 % of the cells against 31.5 % of the vanilla locations. Nothing asked for a
   smaller South America; it was the invariant's side effect, and a first version of C529 kept the
   invariant and documented the shortfall as a limit (12 %). The owner's report that it is not
   acceptable is right, and vanilla itself has 15 groups with two pieces on one landmass (0.9.4).

**Now** (`hierarchy.neck_parts`, `eu5_newworld._bands`): the subcontinents are cut from the
north, one part at a time. For a part the shortest cut (exact minimum cut, Dinic maximum flow on
integer capacities, the smallest one) in a window of latitudes around its share:

- Cells are ranked by row, column and index; the first `count` are the banded answer. The
  `NECK_WINDOW` = 200 permille of the cells on either side are free, the rest keep their side. A
  severed contact costs `NECK_CONTACT` = 1000; a free cell costs up to `NECK_PULL` = 150 on the
  far side of the banded line, in proportion to its distance from it.
- The size of a side moves in steps (a peninsula or an island comes whole), so the cut is taken
  at `count` and at lines up to `NECK_REACH` = 150 permille away (every 5 steps of `NECK_STEP` =
  10 permille, then every step around the best) and the cut whose side is nearest the share wins,
  scoring the distance in cells plus `NECK_CELLS_PER_CONTACT` = 4 cells per severed contact
  (`_closest_north`). A side is measured as settled: its small pieces have left it and the
  other side's have come.
- **A subcontinent may hold several pieces of one landmass**, for instance two peninsulas that
  hang south of a body. A piece smaller than an average region of that subcontinent (its share of
  the cells divided by its regions) beside a larger one on its landmass joins the part it touches
  most (`_settle_pieces`): it could not hold a region, and regions, areas and provinces keep the
  one-piece rule (`_check_pieces(depth=3)`, which skips the subcontinent level). A piece without
  a source in `spread_sources` would otherwise join a region across the landmass.

[V-EXEC] Twelve captured `_land_areas` inputs (the two image worlds; `supercontinent` 11 and 5,
`continents` 7 and 1001, `small_continents` 7 and 42, `archipelago` 73, `islands` 73, `wall` 9,
`omerika` 42), South America's share of the cells and the length of the boundary (sum of the
centre distances of the contacts between subcontinents), 1.2.1 → now; the vanilla share is
31.5 %:

| world | South America | boundary | landmasses cut |
|---|---|---|---|
| image, seed A | 13.0 → 32.9 % | 7,433 → 1,125 | 3 → 1 |
| image, seed B | 13.3 → 30.4 % | 7,661 → 1,187 | 3 → 1 |
| supercontinent 11 | 29.6 → 31.8 % | 7,368 → 5,196 | 2 → 1 |
| supercontinent 5 | 31.5 → 26.2 % | 7,160 → 1,446 | 1 → 1 |
| continents 7 | 34.1 → 28.5 % | 5,463 → 1,812 | 1 → 1 |
| continents 1001 | 31.5 → 26.2 % | 19,292 → 4,761 | 1 → 1 |
| small_continents 7 | 31.5 → 34.6 % | 6,384 → 3,523 | 3 → 2 |
| small_continents 42 | 34.7 → 37.0 % | 2,314 → 0 | 1 → 0 |
| archipelago 73 | 31.5 → 32.2 % | 3,780 → 0 | 2 → 0 |
| islands 73 | 30.3 → 34.0 % | 2,339 → 86 | 4 → 1 |
| wall 9 | 29.1 → 29.5 % | 4,612 → 2,131 | 2 → 2 |
| omerika 42 | 31.5 → 36.7 % | 4,093 → 469 | 1 → 1 |

Every input passes `_check_pieces` at the region level and below and covers every cell;
`_land_areas` takes 0.9–5.3 s per world (0.7–2.5 s with the single cut before the scan). In the
image worlds South America is both south-hanging peninsulas and the two island arms that lie on
the line, whole; the other worlds stay within 6 points of the vanilla share. A sweep of the
window (100–400), the pull (50–1,600) and the reach found the shares of the image worlds
bounded by the necks (19–24 %) until the scan was added; it, not a wider window, closes the
gap, and a window of 300 with a pull of 50 took 53.7 % of `supercontinent` 11 in the first
version. Synthetic regressions (`tests/test_hierarchy.py`): a two-blob land whose neck lies a few
rows above the row line is cut at the neck; an island across the line stays whole; both legs
that hang south of a body are one part; a leg too small to hold a region joins the other part
(the waist and island tests fail with a window of one rank and no scan, which is the row cut). The reference world
(`supercontinent`, seed 20261102) goes `f454b5f5` (epoch 62, reproduced from `HEAD` in the same
session) → `43dfd7ec` (884 files, reproduced at 31 and 8 threads and by the installed-game
reference check).

What it does not do: it does not look for natural features other than the land's own shape (a
broad landmass without a waist is cut along the shortest line, which can stay nearly horizontal:
`continents` 1001), and it reaches the vanilla share only as far as whole peninsulas and islands
allow. Regions, areas and provinces are unchanged algorithms on the new subcontinents. The inputs
were captured as for the W8 bench: monkeypatch `eu5_newworld._land_areas` to pickle its arguments
and cancel the export, then rerun the real function.
