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

The production ocean identities, shoreline integrations, native histories, script
rewrites and texture export still need the combined export path. See the
[implementation plan](../../docs/continent-generation-plan.md) for the scope of
the end-to-end measurement.

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
