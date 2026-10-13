# Agent instructions

- Goal: determine how to generate genuine EU5 New World geography and start state, then build only the validated path.
- Target the current 1.4 beta installation; recheck the exact build, file layout, and behavior after every game patch.
- Never edit the game installation or copy proprietary game files into this repository. Put local derived data and generated mods under gitignored paths.
- Label technical claims `[V-GAME]`, `[V-LOCAL]`, `[V-EXEC]`, `[SOURCE]`, `[INFERRED]`, or `[UNKNOWN]`; see `docs/research/claims-ledger.md`.
- Never treat script syntax, game loading, and playable behavior as equivalent evidence.
- Only install test mods as new `rnw_exp_*` directories and record them in `experiments/INSTALLED.md`.
- Read `README.md`, `docs/feasibility.md`, and `docs/handoff/opus-5.5.md` before making architecture decisions.
- Verification commands and source layout will be added after the stack ADR.
