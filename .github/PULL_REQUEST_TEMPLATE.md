## What and why

<!-- What does this change, and which issue or roadmap item does it address? -->

## How it was verified

<!-- Tests added or run, offline checks, and in-game observations with the game version. Label claims as in CONTRIBUTING.md (V-EXEC, V-GAME, …). -->

## Checklist

- [ ] `make check` passes.
- [ ] Every commit is signed off (`git commit -s`, Developer Certificate of Origin).
- [ ] No game files or anything derived from them (rasters, logs, saves, screenshots, generated worlds) are included.
- [ ] If generated output changes: the version is raised, golden digests are updated, and, if a world's mod files change, a new epoch is added in `src/rnw/epoch.py` with a new `tests/golden_world.json`.
- [ ] Documentation and `CHANGELOG.md` (*Unreleased*) are updated where needed.
- [ ] Any new reverse-engineered EU5 format is recorded in `docs/research/interoperability.md`.
