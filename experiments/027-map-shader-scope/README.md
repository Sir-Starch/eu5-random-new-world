# 027: Keep the map cover out of loading and character scenes

Date: 2026-10-22. **0.9.26 GAME REGRESSION; 0.9.27 OFFLINE CANDIDATE.**

## Owner observation and runtime evidence

[V-GAME owner C153] The owner reports that 0.9.26 fully conceals the New World, but
loading artwork and character backgrounds turn black. Three supplied screenshots
show black loading illustrations and a black background behind the Portuguese ruler.
This establishes the reported concealment result, not every selection/start route.

[V-LOCAL C153] The latest EU5 1.4.3 profile log records 122 compile failures with
`use of undeclared identifier 'RnwVisibility'`, all in
`gfx/FX/pdxmesh_without_terrain.shader`. Failed materials include loading-screen
layers, illustration planes, event/unit scenes and other no-terrain meshes.
The cached HLSL contains the RNW cover call but no declared visibility sampler.

[V-LOCAL / INFERRED C153] The 0.9.26 mod overrides the shared
`loading_screen/gfx/FX/pdxmesh_base.fxh`, injecting a map-only dependency into every
consumer. The no-terrain shader includes this base, so the patch reaches unrelated
scenes. The runtime compile errors and failed scene materials explain the black
artwork. The earlier offline sampler scan did not test this engine compilation path.

## Scoped candidate

[V-EXEC C154] Version 0.9.27 no longer emits an override of the shared base. It derives
`main_menu/gfx/FX/rnw_map_mesh.fxh` from the installed original and redirects only
`main_menu/gfx/FX/pdxmesh.shader` to that private covered copy. The main shader still
declares the cover samplers directly. The exporter separates the installed source
path from the override destination and preserves source encoding and anchor checks.

[V-LOCAL / V-EXEC C154] Leave pulse/rotate/emissive variants untouched: native asset
definitions use these for portrait attachments and ship/expedition effects. Their
complete include graphs (51 files each) remain byte-identical to vanilla; the
no-terrain/loading graph (29 files) also remains byte-identical. None contains RNW
references. The map's 62-file graph uses the private base and excludes the shared one.

[V-EXEC C154] A regression fails on 0.9.26's output contract because the shared base
is overridden, then passes after isolation. A second test locks the map-only redirect,
installed source path and unchanged no-terrain/pulse/rotate/emissive destinations.
Required checks pass: formatting, lint, strict types, 837 Python tests (8 optional
skips) and 23 Rust tests.

[V-EXEC C154] The real application CLI exports the epoch-3 reference in 86.9 s,
passing every invariant:

```sh
uv run --no-sync rnw world RNW1-0426C-SYW6B-MW73Y-C004H-P00AJ-2AG \
  --game-dir '<steam-library>/steamapps/common/Europa Universalis V' \
  --data-dir local_data/cover-scope-20261022/application
```

The candidate is
`local_data/cover-scope-20261022/application/generated/rnw_exp_world_qduvxguw6u/`.
Independently hashing all 749 non-metadata mod files gives
`798ffdbdc901aba081fdb5fda9d2a69f1d5236a8a5047d8b8993fd10b9809b3a`.
Against 0.9.26 only `pdxmesh.shader` changes, the shared-base override is removed,
and the private base is added. Geography, civilizations and all other cover files
are byte-identical. Inputs remain 13,893 files; the output change starts epoch 3.

## In-game acceptance still required

[UNKNOWN] The scoped candidate has not been launched by the agent. On a fresh EU5
launch with only the new world active, verify loading artwork, ruler/character/event
backgrounds, portrait attachments and ship effects; retain full New World concealment
at every zoom and map lens. Check normal Old World rendering and discovered New World
detail in a campaign. Do not treat restored vanilla include graphs as a running-game result.
