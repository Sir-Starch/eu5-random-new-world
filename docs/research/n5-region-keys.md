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
both the subcontinents were cut wrong. North America was 87.0 % and 86.7 % of the land cells
where the vanilla Americas give it 68.5 % of their locations, and South America had three
pieces: the south-western peninsula and a strip of 25–29 cells on each of the two island arms
that lie across the band line, so a straight horizontal edge ran through both islands and the
mainland's neck. The cause is the C502 rule itself, not one input: a band is the cells ranked
by row, so its boundary is a row, whatever the land is. Two defects followed from it. A row
slices a landmass that lies across it, and the "one piece per landmass" repair then gave the
rest of the southern band, a whole peninsula of the same world, back to the north because it
was the smaller piece. The cut was also straight in worlds without a drawing: the
`supercontinent` (seed 11) and `continents` (seed 7) presets had a ruler-straight edge through
a continent.

The subcontinents are now cut from the north, one part at a time (`hierarchy.neck_parts`). The
part takes the shortest cut, in contacts, that lies in a **window of latitudes** around the
row that would give it its vanilla share:

- Cells are ranked by row, column and index; the first `count` are the banded answer. The
  `NECK_WINDOW` = 200 permille of the cells on either side of that rank are free; the cells
  beyond keep their side.
- Severing a contact between free cells costs `NECK_CONTACT` = 1000; a free cell costs up to
  `NECK_PULL` = 150 for lying on the far side of the banded line, in proportion to its
  distance from it. The cut that minimizes the sum is exact (maximum flow, Dinic, integers;
  the smallest minimum cut) and a pure function of the inputs.
- A landmass whose narrowest waist lies in the window is cut there, a landmass that lies
  inside it is joined whole to the side its latitude favours, and one that spans the window is
  cut where it is narrowest. The tie of equal cuts goes to the banded line through the pull.
- A cut can still leave a part two pieces on one landmass (a U open to the north). The old
  repair stays: a part keeps its largest piece there and the others join the part they touch
  most. A part is therefore smaller than its share where its land is split in pieces, and no
  longer takes a share it cannot hold in one piece.

[V-EXEC] Seven captured `_land_areas` inputs (the two image worlds, `supercontinent` seed 11,
`continents` 7, `small_continents` 7, `archipelago` 73, `islands` 73) all pass `_check_pieces`
and cover every cell. The length of the boundary (the sum of the centre distances of the
contacts between subcontinents) went 7,433 → 543 and 7,661 → 498 in the image worlds, 7,368 →
5,282, 5,463 → 1,812, 6,384 → 562, 3,780 → 0 and 2,339 → 86 in the others; the image worlds
have South America in one piece (219 and 221 cells) with both island arms whole in the north;
the archipelago has no cut island at all. South America's share is 11.8 % and 12.0 % in the
image worlds (its peninsula is the one piece the land allows; the other southern strip hangs
from the other side of the mainland and cannot join it), and 31.0 %, 28.5 %, 25.6 %, 28.9 %
and 34.0 % in the others against 31.5 % in vanilla. A sweep of the window (100, 200, 300) and
the pull (50, 150, 400) kept 200 and 150: a window of 300 with a pull of 50 let South America
take 53.7 % of the `supercontinent` world, and a window of 100 cut the image worlds along 11
contacts against 6. The cut of all seven takes 0.7 s together. Synthetic regressions: a two-blob land
whose neck lies a few rows above the row line is cut at the neck, and an island across the
line stays whole (`tests/test_hierarchy.py`; both fail with a window of one rank, which is the
row cut). The reference world (`supercontinent`, seed 20261102) changes 96 of its 884 files: the
location raster, the hierarchy, its localization in all eleven languages and the scripts that
name it; the 884-file digest `f454b5f5` of epoch 62 (reproduced from `HEAD` in the same
session) becomes `6536df49`, reproduced at 31 and 8 threads.

What the cut does not do: it does not look for natural features other than the land's own
shape (a broad landmass with no waist is cut along the shortest line, which can still be
nearly straight), and it does not restore a subcontinent's vanilla share when its land is
split in pieces. Regions, areas and provinces are unchanged algorithms on the new
subcontinents. The inputs were captured as for the W8 bench: monkeypatch `eu5_newworld._land_areas`
to pickle its arguments and cancel the export, then rerun the real function in about a second.
