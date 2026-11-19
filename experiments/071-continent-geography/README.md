# Shared continent geography prototype

[V-EXEC 2026-11-18, EU5 1.4.9 / Steam build 26655995] The prototype runs the
current rivers-first geography kernels with distinct continent presets. It reads
the map and calibrates location sizes once, allocates replacement pixels before
generating land, and merges the regions into one map raster. One climate pass and
one wrapped adjacency scan read that composed raster. Africa and Oceania use
windows cropped in both axes. Their rows retain global latitude and polar bands.

## Timing

Seed 42, 31 threads and four stage slots for each run. Every case started in a
fresh process without an application cache. Filesystem caches and ambient
workload varied. Values are single observations. Land cells include wasteland.

| Selection | Seconds | Peak RSS (GiB) | Land cells in America | In Africa | In Oceania |
|---|---:|---:|---:|---:|---:|
| America | 95.9 | 9.0 | 7,708 | | |
| America and Africa | 121.0 | 9.0 | 6,998 | 2,782 | |
| America and Oceania | 114.4 | 8.0 | 5,800 | | 2,221 |
| America, Africa and Oceania | 140.7 | 9.2 | 5,430 | 2,782 | 2,221 |

The initial combined case adds 44.8 seconds to this geography measurement. The first
combined run with full-height windows and broader coastal bands took 174.8
seconds. The change to the coastal bands also changed the amount of generated
land, so the difference does not isolate the effect of cropping. The wider
Pacific replacement footprint in the America-only control accounts for part of
the work difference.

## Coastal and resource calibration

[V-EXEC 2026-11-18, same game build and worker budget] Entire vanilla footprints
still belong to their continent. Large connected landmasses get the whole
coastal band, 820 map pixels in Africa and 560 in Oceania at full width. Small
islands get up to 224 pixels, so remote islands reserve less open ocean from
neighboring domains. These are trial settings. The wide band starts at
131,072 connected pixels at full width.

| All three continents | Seconds | Peak RSS (GiB) | American land cells | African land cells | Oceanian land cells |
|---|---:|---:|---:|---:|---:|
| Seed 42, calibrated bands | 139.4 | 8.6 | 6,765 | 1,956 | 1,162 |
| Seed 43, calibrated bands | 138.0 | 8.3 | 6,516 | 1,984 | 1,209 |
| Seed 42, with shared biomes and regional resources | 144.2 | 9.2 | 6,765 | 1,956 | 1,162 |

Seed 42's American deficit against the original America-only control drops
from 30% to 12%. The composed rasters contain 30,990 populated IDs at seed
42 and 30,900 at seed 43, including retained vanilla IDs. This count precedes
final shared-water allocation. Compliance with the 32,000 location limit will
be checked on the written world.

The resource trial casts one biome vote on the composed climate and contact
graph, then draws from each continent's own weighted coastal and inland pools.
That stage took 1.04 seconds for the combined world. The extra vanilla input
statistics and climate for that vote took 1.3 seconds. At seed 42 it assigned
materials to 6,155 American, 1,780 African and 1,058 Oceanian passable cells.
Every draw came from the assigned continent's inventory. Regional weights cover
ordinary materials specific to the local pools, including coffee and rice in
Africa and millet and sugar in Oceania. This run uses preliminary geography
classes before the full wasteland, height and coastal export stages.

A separate seed-42 run enabled Africa with Continents and Oceania with
Archipelago, leaving America disabled. It took 60.2 seconds including the
biome and resource stage, with 6.6 GiB peak RSS. A scan of the composed
raster found zero changed non-marine pixels in the disabled continents.

```sh
RNW_TIMING=1 uv run --locked python experiments/071-continent-geography/profile_geography.py \
  /path/to/eu5 america africa oceania --seed 42 --materials
RNW_TIMING=1 uv run --locked python experiments/071-continent-geography/profile_calibration.py \
  /path/to/eu5
RNW_TIMING=1 uv run --locked python experiments/071-continent-geography/profile_geography.py \
  /path/to/eu5 africa oceania --seed 42 --preset africa=continents --materials
```

## One map and one 1337 setup trial

[V-EXEC 2026-11-18, EU5 1.4.9 / Steam build 26655995] With seed 17,
Continents for America, Supercontinent for Africa and Archipelago for
Oceania, the map planner assigns **27,881** final location identities against
the game's 32,000 limit. It plans 1,831 generated ports, 387 ocean lanes,
13 generated straits and 12,033 geographic location bindings. No unchanged
continent's land pixels were replaced. Generated cells were connected
across the map wrap and generated open seas reached retained water.
A cut offshore contact at the edge of the African canvas had a navigable
replacement through generated sea cells. The American overseas check
passed with broad ocean areas separating America from other continents.

The same game and map inputs supported all four Morocco outcomes. The
default reserves the first 86 passable African locations before the
African polity bootstrap and all 86 get populations. Independent
Algeciras, Castile and Granada each receive exactly the same four
Iberian holdings on the map. The setup trial recalculates each option
with the same geography and geographic bindings.

| Continent | Populated locations | Cultures | Religions | State territories | Tribal territories |
|---|---:|---:|---:|---:|---:|
| Africa | 1,757 | 87 | 23 | 134 | 119 |
| Oceania | 848 | 65 | 11 | 7 | 72 |

The preliminary societies use the installed continent's population profiles
and landed states' farming baseline. In Africa, 129 of the 131 local states
with a known starting technology have level 3. In Oceania, three have level 1
and one has level 3. These measurements describe the local bootstrap before
history, political serialization and game loading.

```sh
RNW_TIMING=1 uv run --locked python experiments/071-continent-geography/profile_geography.py \
  /path/to/eu5 america africa oceania --seed 17 --game-land --seas --societies \
  --morocco restore --morocco emirate --morocco castile --morocco granada
```

[V-EXEC 2026-11-19, same game build] The three saved histories project 630
American, 225 African and 74 Oceanian countries for seed 17. Their 929
chronicles share four history files. The common writer builds 116 files with
8,581 populated locations, including all 86 holdings reserved for Morocco.
Country definitions and the 1337 setup agree, with the same three tags without
start records as vanilla. Six reused African sea areas take their names from
the installed province catalogue, which the writer overrides in place.

With Africa (Continents) and Oceania
(Archipelago) alone, seed 42 yields 27,200 final identities and confirms
the independence of America's world map. On this coast, the port matcher
follows adjoining water to the nearest sea with an eligible port.

[V-EXEC 2026-11-19, EU5 1.4.9 / Steam build 26655995] The export adapter
wrote one complete offline mod for seed 42 with Africa and Oceania. It
validated 27,191 location definitions, 4,059 ports, 337 lanes, 298 new
countries and 1,080 content consumers, including installed DLC. The run
took about 128 seconds with 24 workers and reached 9.1 GiB peak RSS.
The America-only reference reproduced byte-for-byte after the export stages
were shared. This comparison has different continent selections and seeds.
The [implementation plan](../../docs/continent-generation-plan.md) describes the
matched trials for setting a performance budget.

### Full-export timing prototype

[V-EXEC 2026-11-19, EU5 1.4.9 / Steam build 26655995] Full exports at seed 17
used Continents for America, Supercontinent for Africa and Archipelago for
Oceania. Both runs used 24 threads, four stage slots and fresh processes with
no application cache. The table records the repeat pair after other generation
and build work finished. The operating-system file cache was left in place.

| Selection | Wall time | Peak RSS | Geography | Start | Terrain |
|---|---:|---:|---:|---:|---:|
| America | 165.0 s | 9.8 GiB | 71.0 s | 26.1 s | 46.9 s |
| America, Africa and Oceania | 227.6 s | 11.3 GiB | 107.3 s | 38.8 s | 52.3 s |

Stage durations overlap. The three-continent case has one instance each of the
climate and biome assignment, sea planning, terrain export and scenario writer.
Initial runs with overlapping development work took 186.3 and 310.6 seconds.
Those observations show the effect of ambient workload on comparisons.
The owner set a four-minute target for the combined case on this machine.

A separate production export kept the installed American geography while
regenerating its societies alongside Africa and Oceania. It passed the
shared start and map checks. A scan across the full raster found zero changed
pixels in the retained American land, lakes and wastelands.

The America–Africa run exposed part of the vanilla Pacific shelf inside the
expanded American canvas. The composed planner now keeps the retained shelf's
location pixels and scopes new ocean identities at the retained coast. Seed 17
passed the full export with 24 threads in 211.6 s at 10.4 GiB peak RSS.

All seven nonempty selections completed an offline export. A separate seed-17
world using The Wall for America, Supercontinent for Africa and Archipelago for
Oceania completed in 232.2 s with 10.9 GiB peak RSS.

### Final application timing

[V-EXEC 2026-11-19, same game build] The application's cold-cache generation of
the reference three-continent world took 261.0 s before concurrent regional
preparation and 214.7 s with it at 24 threads. The sequential run took another
0.5 s to install the world. The geography stage fell from 128.3 s to 89.9 s and
peak RSS rose from 10.9 GiB to 11.7 GiB. The two runs produced the same 1,436
recorded mod files. An independent uncached rebuild at 16 threads also matched
the installed world's record.

One background worker prepares the smaller domains in sequence while the main
thread prepares the first. They use the same native worker pool. Available
memory limits overlap and the compose step collects each result in continent
order. Climate, water, terrain, scripts and mod output still run on the single
composed map.

The resource reroll from the same application cache and at the same worker
budget took 128.9 s. The location raster, river raster and location hierarchy
matched byte for byte, and the resource templates changed. The
[installation record](../INSTALLED.md) identifies the verified world and hub.

### Africa and Asia

[V-EXEC 2026-11-18, same build and worker budget] The installed map has
168 candidate African border pixels next to passable Asian land. The
regular coastal margin left all of them under water. The coast model now
eases the penalty at the original dry interface over one coastal ramp.
The terrain field and the land budget still choose where land lies.
Retained dry terrain continues the local relief and receives no generated
river, including when a coarse drainage cell straddles the border.

| Prototype selection | Seed | Passable African border pixels | Retained non-marine pixels changed | Seconds |
|---|---:|---:|---:|---:|
| Africa | 42 | 0 | 0 | 41.7 |
| Africa | 43 | 0 | 0 | 42.5 |
| America, Africa and Oceania | 17 | 168 | 0 | 139.6 |

These runs include the shared climate, biome and material stages. The
combined run held 30,795 populated raster IDs and peaked at 9.2 GiB. Its
African rivers passed the genuine-outlet check during generation. A
passable prototype border records raster adjacency, with full export and
in-game traversal still to be checked.
Drawing the rivers again on the finished African prototype at seed 17
validated all 161 mouths and the river network. No river pixels lie on
the retained side.

[V-LOCAL] The non-marine African hierarchy contains five subcontinents,
16 regions and 97 areas. Oceania has two subcontinents, five regions and
54 areas. In both continents, the vanilla areas with non-marine locations
contain no sea zones. Oceania's Australasia and Pacific Islands span much
of the same latitude range, so their key matching needs longitude as well
as latitude. The existing north-to-south partition follows the American
hierarchy.

## Startup data

[V-EXEC] The 1337 population adapter reads population, country, city, naming
and language data once for the requested continents and calibrates local
cultures, faiths and naming corpora. Mixed territorial holdings count where
they lie. The America-only generator keeps its existing identity calibration.

| Vanilla continent | Land locations | Owned land | Population (pop units) | Cultures | Religions |
|---|---:|---:|---:|---:|---:|
| America | 4,434 | 493 (11.1%) | 30,113 | 730 | 70 |
| Africa | 2,433 | 1,079 (44.3%) | 42,893 | 287 | 57 |
| Oceania | 790 | 19 (2.4%) | 1,914 | 388 | 18 |

These are source distributions for calibrating the societal defaults. The
share of owned land differs by a factor of 18 between Africa and Oceania.
The local template pools also differ, with sub-Saharan and Muslim monarchies
in Africa and Polynesian and Indonesian precedents in Oceania.

[V-EXEC] A direct footprint scan on the installed game inventories 985 script
consumers for Africa and 60 for Oceania. Of those, 793 and 17 respectively have
no decision in the current table. The audit includes the original hierarchy
keys for each full region and direct tag retirement only. Counts can change
when a generated world reuses regional keys and the export resolves setup.

Filtering mixed ownership and reseating the capital preserves the Moroccan and
Mamluk country entries in the direct scan. The existing transitive setup pruning
then removes both tags through rulers and dynasties that refer to African places.
The same closure can reach unrelated countries. A character linked to other
French characters has a birth reference to Damietta. Removal propagates through
France and the Catholic saints list to Catholic populations. Regional setup
pruning now treats individual saints and modifiers as independent entries.
The installed Africa audit with mixed holdings trimmed retires 580 country
tags with that rule, compared with 965 using the legacy pruner. The religion
definitions and their unaffected entries survive. That earlier audit still
retired Morocco, the Mamluks and France through their personal and dynastic
dependencies. Oceania's 28 retirements were the same under either rule.

[V-EXEC 2026-11-18] The regional setup pass now rebinds birth and dynasty
home locations before calculating retirements and removes kinship fields
that point to retired characters. It also limits identity retirement to
the managers that declare identities. This keeps an `army` statement or
an area preference in one file from retiring valid countries in another.
With substitute location IDs, the installed audit retires 230 country
tags for Africa, 28 for Oceania and 258 for both. It retains Morocco's
four European holdings and the Mamluks' 75 Asian holdings. The audit uses
Algeciras and Damascus as their replacement capitals. France and the
Golden Horde remain in the resulting setup.
An additional African run at seed 17 mapped the 51 affected original
birth and home locations to 25 generated passable destinations with
the geographic remapper. It confirmed the same 230 retirements and
preserved all four named countries.

### Morocco's options

[V-EXEC 2026-11-18, EU5 1.4.9 / Steam build 26655995] All four choices
passed the ownership check using one generated African map at seed 17.

| Choice | Result in the 1337 setup |
|---|---|
| Keep Morocco | `MOR` owns 86 African and all four Iberian locations. Its capital is one of the 86. |
| Independent Algeciras | A new tag owns exactly the four Iberian locations, with its capital in Algeciras. |
| Join Castile | `CAS` integrates the four locations and keeps Valladolid as its capital. |
| Join Granada | `GRA` integrates the four locations and keeps Granada as its capital. |

The offline trial includes the input scan for the new tag and checks the
four setup variants in 9.4 seconds after one geography run. The default
selects one variant.

```sh
RNW_TIMING=1 uv run --locked python experiments/071-continent-geography/profile_geography.py \
  /path/to/eu5 africa --seed 17 --morocco restore --morocco emirate --morocco castile --morocco granada
```

## Loading 6HGZ with Across the Pillars

[V-GAME / V-LOCAL 2026-11-19, EU5 1.4.9 / Steam build 26655995] Two
owner-run 1337 starts of the original world 6HGZ ended with an access
violation at the same address. Both logs end with `unknown Location for
tunis`. The mounted DLC file `25_d009_town_rights.txt` names 14 historical
cities whose locations the world replaces. The offline audit also found 61
missing discovery references in effective country setup and templates.
The engine reported 846 failed lookups while applying the templates and
42 owned locations with neither a starting culture nor a religion.

[V-EXEC] The combined export now includes DLC setup in the territorial
prune, binds areas and provinces in country discoveries, writes local
culture and religion from the largest population cohort, and gives Castile
knowledge of Morocco's relocated capital if their rivalry survives. The
rebuilt world has zero dangling locations in city rights and zero dangling
discovery references in the effective 1337 files. All 42 reported locations
have both fields, matching their exported populations. The full export on 24
threads took 223.1 seconds. The original seed and settings reproduce the
same location raster, river raster and hierarchy. The installed build and
hub are recorded in [INSTALLED](../INSTALLED.md).

[V-GAME 2026-11-19, 11:43 CET] The owner-run retry enabled only
`RNW: 6HGZ Load Fix` with the same DLC. EU5 processed the DLC town-rights
file and reached the in-game state after 1337 initialization and startup
save serialization. The Tunis, discovery, missing identity and Moroccan
rivalry diagnostics did not recur. There was no new crash report. The
same river-source warnings and some law and parliament warnings remain
in the log. This observation covers startup.

## Ocean allocation and coastal contacts on 6HGZ

[V-EXEC 2026-11-19, EU5 1.4.9 / Steam build 26655995] The three continents
now share open-ocean space, with reach into southern waters. The shared
plan removes isolated scraps of water, leaves partially claimed zones
whole where a cut would sever the retained shore, and preserves installed
toll zones and the fixed naval positions used by retained events. A
scripted reference to an area that disappears follows the area binding.

Measured by counting land pixels in the written maps:

| Same seed and regional presets | America | Africa | Oceania | America / Africa |
|---|---:|---:|---:|---:|
| 6HGZ Load Fix | 18,091,960 | 7,097,617 | 2,324,672 | 2.55 |
| 6HGZ Regional Coasts | 10,937,548 | 10,396,079 | 3,772,957 | 1.05 |

The overlap with original Oceania falls from 0.468 to 0.050 by Jaccard
index. The new African land reaches the bottom raster row and Oceanian
land reaches within 54 rows. The combined exporter paints shelves and
enclosed seas from the finished shore and basin fields, fading into the
installed water texture beyond the changed geography.

The seed chooses an approach to Asia in 40% of the optional cases. The
required switch constructs an approach while planning the coast and
requires a passable foreign land contact during verification. This world
uses the required switch. It has 13 direct passable location adjacencies
to Asia along the southern Yemeni coast, including Aden, and one crossing
to Europe. The latter connects Esgueira on the Portuguese coast to the new
African shore across one six-pixel sea segment.
The map passed the retained-contact, port, and script checks with 27,421
locations. Cold generation took 234.5 seconds with 24 threads, and
all 1,461 canonical files were verified in the installed copy. The
America-only reference on the same installed build reproduced all 884
canonical files byte for byte.
[Installation details](../INSTALLED.md).
