# N5: physical meaning for American region and area keys

2026-10-24. Owner instruction: implement N5. Generator **0.11.4**, algorithm
epoch **28**. Implementation and verification are offline; engine behaviour is
**NOT-RUN**. The installation is the 1.4.4 executable (Steam build 26142040)
on 1.4.3 data. No game launch belongs to this work.

## Design

[INFERRED design] Geography owns the assignment, before societies, technology,
development and stories. Subcontinents keep the established positional partition.
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
