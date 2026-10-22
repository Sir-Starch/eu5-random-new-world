# 026: Close-zoom cover and country selection

Date: 2026-10-22. **OWNER REPRODUCTION FAILED; FIX NOT GAME VALIDATED.**

[V-GAME owner C150] At close zoom the covered New World exposes trees, rivers,
resources and cities. The owner selected a New World country through the map and
started playing it despite the terra incognita cover.

[V-LOCAL C150] The latest profile debug log mounts `rnw_exp_world_dsllwsx2jw` at
16:49:49 and matches game version 1.4.3. Its metadata says generator 0.9.20.
The profile still names both retired probes, whose mod folders are absent.
No profile, installed mod, playset or game file was modified during investigation.

[V-LOCAL / INFERRED C150] The cover in 0.9.25 still patches only terrain, water,
borders and map names. Tree, river and city passes and GUI resource markers are
independent. The right-click Select guard does not intercept native map selection,
the country-list selection command or the Start actions in the lobby.
These omissions match the reported symptoms; runtime toggle proof is pending.

[UNKNOWN] The earlier C139 success covers the political lens and the campaign TI
check on 1.4.2 only. It leaves close-zoom detail and all selection/start routes open.
No agent EU5 launch is authorized in this session.

## Offline candidate 0.9.26

[V-EXEC C151] The cover now contains 19 files, including 12 shader/include overrides.
It adds tree leaves and billboards, ten tree shadow effects, river surface/bottom,
generated-city geometry, terrain-backed and standard meshes, decals and world text.
Opaque detail fragments are discarded wherever the existing unknown-New-World mask
is nonzero above 0.001. Existing alpha passes fade against that mask. The standard
mesh include uses the game's canonical province-overlay sampler declaration.

[V-EXEC C151] The lobby override hides American country cards and the selected-country
information panel for a hidden country, suppresses the unfiltered random-country
selector, and adds the country predicate to two CanStart and four CanJoin guards.
Resource and market markers are hidden only in the lobby for American locations.
All overrides are present only while the world's visibility option is off.
The library's existing saved-cover mechanism removes/restores all 19 files.

[UNKNOWN] Native map picking is not intercepted: the engine can still select a
country internally. The candidate hides that selection's information and gates the
local selected country's UI start/join controls. GUI expression evaluation, disabled
controls, keyboard routes, multiplayer participants and engine shader compilation
require game testing; source/parser acceptance is not runtime proof.

[V-EXEC C151] A synthetic regression exposed that the binding audit read an installed
include instead of its generated override, missing duplicate engine slots. It now
reads all generated includes first. All five installed shader consumers of the
standard mesh include resolve without duplicate slots or missing includes. Four
new tree-shadow HLSL variants compile through glslang with typed native-call stubs;
this checks their HLSL bodies, not EU5's effect compiler or resource binding.

[V-EXEC C151] The real application CLI exports the epoch-2 reference in 90.2 s,
passing every invariant, into
`local_data/close-zoom-cover/application/generated/rnw_exp_world_hgihw5wfjp/`:

```sh
uv run --no-sync rnw world RNW1-0426C-SYW6B-MW73Y-C004H-M03BP-D30 \
  --game-dir '<steam-library>/steamapps/common/Europa Universalis V' \
  --data-dir local_data/close-zoom-cover/application
```

No installation or copy to a profile was requested. Independently hashing its 749
non-metadata mod files gives
`e1654f67aa8fdae52b988bb96dc6dd75f16f289563ba448230dba9add85e708b`.
Relative to C149, ten files are added and only the scripted GUI changes; none are
removed. All existing geography, civilization and raster outputs are identical.
Inputs: 13,893 files and 3,750 directory listings. Because generated mod content
changes, the release is 0.9.26 and the algorithm epoch is 2, with a renewed reference.

[V-EXEC] `uv sync --locked --group dev --offline && make check` passes formatting,
lint, strict types, 835 Python tests (8 optional skips) and 23 Rust tests.
All eight local installation tests pass with `RNW_REPRODUCE=1` in 109.34 s,
including an independent full export matching the new epoch-2 reference digest:

```sh
RNW_REPRODUCE=1 \
EU5_GAME_DIR='<steam-library>/steamapps/common/Europa Universalis V' \
  uv run --no-sync pytest -q tests/test_local_install.py \
  --basetemp local_data/close-zoom-cover/reproduction
```

## In-game acceptance still open

With a newly generated covered candidate loaded on a fresh launch, check:

1. Every zoom and map lens hides trees, shadows, rivers, towns, resource/market markers
   and labels throughout the New World, including its coast and the map seam.
2. Clicking or double-clicking New World countries shows no country information and
   cannot start a campaign, including keyboard start; their country-list cards and
   the unfiltered random selector are absent. An Old World country starts normally.
3. Starting as an Old World country retains vanilla TI; discovering the New World
   restores its details. Revealing the world in the generator restores vanilla lobby
   behavior after the mod is reloaded.
4. Multiplayer selection/start and loading a second lobby in one process do not
   bypass the intended behavior. No such result is established by this offline pass.

## Installation after owner request

[OWNER / V-EXEC C152] The owner requested agent installation instead of manual copying.
With EU5 closed, `rnw install-mod` installed the candidate into the new normal-profile
folder `mod/rnw_exp_world_hgihw5wfjp`. Its displayed name is
`RNW: Small continents HGIH`, version 0.9.26. Every one of its 751 files, including
metadata, independently hashes identically to the prepared source. Earlier statements
about no installation describe the offline phase before this request. Existing worlds
and playset entries were outside the installation; HGIH must be enabled instead of
the older DSLL world in the game's playset. No game launch or runtime result is claimed.
