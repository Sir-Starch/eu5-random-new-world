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

The combined case adds 44.8 seconds to this geography measurement. The first
combined run with full-height windows and broader coastal bands took 174.8
seconds. The change to the coastal bands also changed the amount of generated
land, so the difference does not isolate the effect of cropping. The wider
Pacific replacement footprint in the America-only control accounts for part of
the work difference. The selected land budgets and coastal priority still need
calibration, especially for Oceania and its effect on the American canvas.

```sh
RNW_TIMING=1 uv run --locked python experiments/071-continent-geography/profile_geography.py \
  /path/to/eu5 america africa oceania --seed 42
```

The timing ends at geography, global climate and contact construction. The
production ocean identities, shoreline integrations, native histories, script
rewrites and texture export have yet to run against the combined world. The
experiment records where the African domain reaches Asia. The coastal and
drainage stages still need to support a passable boundary with valid river
outlets before the two possible Africa–Asia outcomes can be verified. See the
[implementation plan](../../docs/continent-generation-plan.md) for the scope of
the end-to-end measurement.

## Startup data

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
France and the Catholic saints list to Catholic populations. The prototype
fixes overlapping deletion spans when an organization loses its last remaining
member in a later pass. Regional export still needs a typed policy for these
references, preserving retained characters, dynasties and religions while
resolving the specific affected fields and records.
