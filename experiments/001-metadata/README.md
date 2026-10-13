# 001 — metadata discovery

- **Hypothesis:** A generated mod with `.metadata/metadata.json` and an `rnw_exp_*` folder is recognized by EU5 1.4.1.
- **Method:** `uv run rnw prepare-mod generated/rnw_exp_001_metadata`; `uv run rnw install-mod generated/rnw_exp_001_metadata /tmp/rnw_eu5_validation`. An isolated temporary playset enabled this one mod; EU5 was launched through Steam with `-userdir Z:\tmp\rnw_eu5_validation -debug_mode`. The owner's normal mod directory and playset were not intentionally edited. Baseline was a separate isolated-profile startup without this mod.
- **Files/tools:** generated `.metadata/metadata.json`, Steam/Proton, isolated `logs/debug.log` and `logs/error.log`, `rnw logdiff`. Game assets were not modified or copied.
- **Game version:** 1.4.1 open beta, Steam build 25905365 [V-GAME C02; V-LOCAL C01].
- **Result:** Debug log explicitly reports that `rnw_exp_001_metadata` with `supported_game_version` `1.4.*` matched game 1.4.1 [V-GAME C11]. The mod contains no game subdirectories. `rnw logdiff` found zero new lines against the captured isolated baseline (900 baseline lines, 898 current lines), but collection times/stages differ [V-EXEC]. The isolated profile stopped at a first-run Select Language screen that did not respond to input [V-GAME C12]. No reliable startup-time comparison was recorded.
- **Remaining uncertainty:** A comparable complete baseline/current log, actual gameplay content mounting, launcher UI enablement, and game behavior. “No new errors” is not established.
- **Architecture implication:** Metadata generation and version matching can be automated; no map export contract follows from this result.
- **Status:** **INCONCLUSIVE** for the full rung; metadata recognition **observed**. No further game launches in this session at the owner's request.

Local artifacts remain gitignored under `local_data/`, `generated/` and `/tmp/rnw_eu5_validation/`. The game-written log sentence is described above rather than committed verbatim.
