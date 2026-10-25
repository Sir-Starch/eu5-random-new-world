# 053 — TR46 long observer campaign: retrospective audit

2026-10-25; owner-played EU5 1.4.4, Steam build 26142040;
**RNW: Continents TR46**, generator 0.12.3, epoch 33.

## Scope and result

The owner played a long campaign and requested documentation only. The full
[problem register and evidence boundaries](../../docs/research/tr46-observer-audit.md)
retain all seven reported problems, split the visual seam from the colonial
east/west question, and add twelve diagnostic groups from the logs. Stable
`TR46-*` IDs are the work list for subsequent phases. Every item remains open.
The [log catalog](../../docs/research/tr46-log-catalog.md) accounts for every
timestamped record in the current error log and all AI rejection categories.

[V-GAME logs/V-LOCAL C298] The campaign reaches 1590.11.11, saves and exits
normally. [V-GAME owner C299] Impassable fragmentation/relief, ocean partitioning,
sea-route detours, low native expansion, persistent wrap crack, colonial-side
allocation and Chukotka remnants remain reported problems. [V-GAME logs C300]
Five seam-adjacent rivers fail to load; a port/water assertion fires once; three
western-voyage waypoints cannot be reached. [V-EXEC C301] Native starting-name
matches give 137 attacking war declarations and zero of 210 colony starts;
these are activity counts, not a vanilla comparison or proof of border growth.

## Preservation and boundaries

[V-EXEC C298] Logs, all three screenshots, two untouched autosaves, metadata,
selected written world files and hash inventories are retained under ignored
`local_data/tr46-observer-20261025/`. No raw logs, game files or screenshots are
committed. [V-LOCAL C303] The event CSV predates the session; Workshop VFS mounts
and missing-DLC diagnostics limit attribution. The previous 02:53 crash is not
part of this run.

No mod was created, generated, installed, removed or altered. No game launch,
save/playset/settings write, engine change, fix, version/epoch bump or manual
test request. There is no installation removal step for this audit.
