# 050 — Seed-positioned land-noise origin

2026-10-25; generator **0.12.1**, epoch **31**. EU5 1.4.4 executable,
Steam build 26142040 on 1.4.3 data; unchanged map-contract fingerprint
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
Claims C286–C287. Offline work only; no game launch or owner sitting requested.

## Problem and correction

[OWNER] Worlds repeatedly show a similar island in the former-Alaska part of the
New World, near Japan at the right edge of the unrolled maps. Islands are welcome
there if they arise randomly; the area must not receive compulsory land.

[V-EXEC C286] The land stage already uses one land threshold for the entire crop:
there is no per-component land quota. All American land is inside the canvas in
both canvas modes on the current installation. The seam's water guard cuts the
narrow northern lobe off from the main land. The original noise, however, always
started at `(0, 0)`: its lattice nodes have higher variance at fixed map positions.
In a synthetic one-octave field over seeds 0–255, the maximum/minimum variance
ratio at two lattice nodes and a cell centre is **4.2385**. [INFERRED] This fixed
spatial bias, together with the clipped lobe, contributes to recurring silhouettes;
there was no explicit rule guaranteeing an island for every seed.

[V-EXEC C286] Each noise stream now draws one deterministic origin from its own
`origin` substream, in `[0, 2**24)` on each axis. Its range spans many periods so
changing feature size also leaves the original handful of lattice nodes. Every
strip uses that same origin plus its absolute row. One continuous field covers
both sides of the seam and every disconnected canvas component. The domain,
land budget, seam safety margin and drawn-land path keep their existing rules;
there is no coordinate-specific island ban or deletion step.

The same variance ratio is now **1.0822**. A synthetic lobe across the seam stays
entirely ocean for 3 of 16 sequential seeds and holds different amounts of land
for the others; the main canvas still holds land and every pixel is classified.
Strip heights 1, 7 and 64 match a whole-field calculation exactly. Native noise
also matches the independent Python reference near the largest new origins.
Small diagnostic comparisons of all five presets are local, not game evidence.

## Initial candidate and verification

[V-EXEC C287] Installed candidate code:
`RNW1-0826C-SYW6B-MW73Y-C0060-20813-R0JKE-XJ`.
Its **814** mod files excluding metadata hash to
`d07aed4acb7690f15d70bed95ba6e1ff30d8f11c29e2be8c169cd9fb9172da15`.
The full export completes in 163.4 seconds. A separate export under
`PYTHONHASHSEED=7` reproduces this digest exactly. The first local-reference run
failed its additional all-story-families assertion: the new geography has no
placed holy site, so `sacred_centre` is correctly absent. The world is valid;
the reference therefore uses a different peoples roll while retaining that coverage check. It has 30,344 definition locations;
all generated sea cells are reachable, every land cell has port access, and
no retained Old World contact is lost.

An independent reading of the written palette, hierarchy, location raster and
ports verifies 21,728 protected hierarchy records, 66,634,570 protected location
pixels, 62 connected changed/new closed-ocean locations and 4,629 valid port rows.
The five pre-existing Arctic portless sea exceptions retain their original contacts.
The canvas still has 53,240,944 pixels. The binary-writing follow-up is recorded
in [interoperability R-004](../../docs/research/interoperability.md).

The Linux window/native/world-code self-test and the rebuilt Windows package's
same self-test under an isolated Wine prefix pass. Package source equality,
locked dependency versions, executable inventory and game-file exclusion pass.
Raw reports, logs, packages and game-derived pictures stay under ignored
`local_data/japan-island/`, `generated/` and `build/`.

## Epoch-31 reference

[V-EXEC C287] The reference keeps the same seed, preset and physical settings,
with `rolls.peoples = 2` to cover every story family. Code:
`RNW1-0826C-SYW6B-MW73Y-C0060-20813-G126N-VS`.
It has **815** non-metadata files, digest
`a6a257f4a26137539ec128481093ed9129d38e34ddea0b863e4df41c552b20ad`.
All **667** map-data and graphics files are byte-identical to the installed
candidate's; three holy sites now provide two sacred-centre stories, and every
other story/formable family is offered. Selection inspected the normal planners
in memory and stopped before serialization; no probe mod was written. A subsequent
ordinary full export completes in 126.1 seconds and is kept local, uninstalled.
No production fallback or content-generation rule was changed to select it.

Locked dependency sync and `make check` pass: **1,862 Python tests**, 14 skips,
**23 Rust tests**, formatting/lint/types clean. The read-only installed-game
checks pass (12 tests); the optional layer reroll run was not requested.
The new reference reproduction test passes under `PYTHONHASHSEED=7` in **152.48 s**,
including the unchanged all-story-families assertion and the exact mod digest.

## Installed candidates

[V-EXEC C287] With EU5 closed, installed two **new** folders:

- `mod/rnw_exp_seeded_land_release`, **RNW: Small continents BSB7**, 816 files
  including metadata, all hash-identical to the audited export.
- `mod/rnw_exp_generator_0121`, **Random New World: generator 0.12.1 (offline verified)**,
  3,254 files, all hash-identical to the prepared package. Open its folder and run
  `Random New World Generator.exe`; enabling the generator as a game mod is unnecessary.

The existing `rnw_exp_hub` is preserved, as are all other existing mods: 8,044
existing mod files retain sizes and modification times, and nine profile-root
files retain hashes. No playset, save, setting or library entry is edited.
The generated world is complete and needs no companion mod. Existing worlds keep
their previous maps; new worlds made by 0.12.1 use the new algorithm.

Exact removal, with EU5 closed:

```sh
uv run rnw uninstall-mod rnw_exp_seeded_land_release --user-dir USER_DIR
uv run rnw uninstall-mod rnw_exp_generator_0121 --user-dir USER_DIR
```

[UNKNOWN] Engine rendering and campaign behaviour of the epoch-31 world. No EU5
launch, push, publication or request for a manual check is part of this phase.
