# 049 — Optional ocean expansion

2026-10-24; generator **0.12.0**, epoch **30**. EU5 1.4.4 executable / Steam build
26142040 on 1.4.3 data; unchanged map-contract fingerprint
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
C282–C285; [design and audit](../../docs/research/canvas-expansion.md).

## Scope and status

[V-EXEC] The owner approved expansion into the nearby oceans, then requested both
policies and a recommended checkbox. The World tab now defaults to expansion;
unchecking it selects the old canvas. The flag travels in codes, sketches, drawn
land templates and rerolls. No separate probe mod exists. This is an offline
implementation record; **no game launch or owner sitting** occurred.

## Offline results

| World | Mode | Locations in definitions | Mod files excluding metadata | Mod digest |
|---|---|---:|---:|---|
| Small continents, reference seed 7379108625698230220 | Expanded | 30,383 | 816 | `5a5f4ed95144b0a30ce71a0ea32aa3ec5161ddbabc9579f6127a7858031464ab` |
| Continents, seed 210 | Expanded | 30,586 | 814 | `6dc40d4d111d7527ed4b4000b8e4a0a147cf92177369d524006fb434928c45d9` |
| Archipelago, seed 73 | Expanded | 29,252 | 815 | `19430924ac558cc46ceb63ae5161907d7f97228bea695167b55ebc88dc83a026` |
| Continents, seed 210 | Original | 28,079 | 814 | `58c9ad120cbf537e95a5ed92b93a4e33b2bb77370a5bcfeb94d9b8966ae25029` |

[V-EXEC] Independent manifest, hierarchy, palette, raster-component, protected-pixel,
contact and port checks pass for these exports. Every expanded world preserves
21,728 protected hierarchy records and 66,634,570 protected location-map pixels.
Expanded masks have 53,240,944 pixels; the original has 37,978,627. Outside identity
recolouring affects closed ocean water only and retains its source's localized name.
The existing vanilla Arctic port omissions are compared by source identity and
unchanged coast contacts, rather than counted as new errors after an ocean split.
The original mode retains its pre-existing vanilla component exceptions; newly
created or changed closed oceans in expanded mode are connected.

The 60%-land supercontinent physical check, seed 99 and 70-pixel land locations,
passes connectivity, port reachability and Old World contacts at 29,098 total
locations before ocean aliases (estimate 29,340). It is not a full mod export.
The final identity cap separately includes added ocean remainder locations.

[V-EXEC] Locked sync and `make check`: 1,445 Python tests, 14 skips, 23 Rust tests;
format, lint and typing pass. Read-only installation suite: 12 passed, 2 opt-in
skips. Separate reference reproduction under `PYTHONHASHSEED=7` passes (163.32 s).
The Russian checkbox was rendered and clicked offscreen; all official-language
catalog and window-layout checks pass. The Linux folder package self-test and CLI
help pass. The owner renumbered this phase to 0.12.0 before publication. The
release boundary and reference code follow 0.12.0; epoch 30 and its map digest stay the same.
`make check` was repeated successfully after the renumbering; package self-tests
and byte checks cover the rebuilt generator and updated world metadata.
Raw scripts, reports, logs and derived pictures stay in ignored
`local_data/canvas-expansion/` and `generated/`.

## Installed candidate

[V-EXEC] Installed **RNW: Small continents NDIW** as the new folder
`mod/rnw_exp_ocean_release`: **818 files**, each hash-identical to the checked
candidate. Code: `RNW1-0826C-SYW6B-MW73Y-C0060-00813-R0YRS-TK`.
This world is complete and declares no companion-mod relationship.

Updated the existing generator hub `mod/rnw_exp_hub` to **0.12.0** with **3,254
files**, each hash-identical to the prepared package. All twelve runtime package
versions now match the lock. Correction to C278's runtime assertion: its old hub
had Pillow 12.3.0 while the lock specifies 13.0.0; this update uses the cached
Windows 13.0.0 wheel. No dependency download was needed. The final own wheel's
SHA-256 is `d31f78e4d53633b2282f3d1a85c27965bb39c10f1ffc56dbcc46c640935e9b81`.

All nine profile-root files retain their hashes, and the 796 existing non-hub mod
files retain sizes and mtimes. Existing worlds and playsets remain. The generator
hub has no game content; the player enables the world's mod alone.

Removal of this candidate, with EU5 closed:

```sh
uv run rnw uninstall-mod rnw_exp_ocean_release --user-dir USER_DIR
```

The hub can be removed separately with the same command for `rnw_exp_hub` if the
player wants to remove the generator. No settings or playset edits accompany either
installation. [UNKNOWN] Expanded-map engine behaviour and the new hub's Open in
folder flow were not newly exercised. No owner check is requested here.
