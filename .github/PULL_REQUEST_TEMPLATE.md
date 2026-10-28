## What and why

<!-- What does this change, and which issue or roadmap item does it address? -->

## How it was verified

<!-- Tests added or run, offline checks, and in-game observations with the game version. Label claims as in CONTRIBUTING.md (V-EXEC, V-GAME, …). -->

## Checklist

- [ ] `make check` passes.
- [ ] Every commit is signed off (`git commit -s`, Developer Certificate of Origin).
- [ ] No game files or anything derived from them (rasters, logs, saves, screenshots, generated worlds) are included.
- [ ] If generated output changes: golden digests and the cycle's pending epoch/reference world are current (ADR 0003); frozen epochs are preserved. Ordinary commits do not bump the product version.
- [ ] Documentation and `CHANGELOG.md` (*Unreleased*) are updated where needed.
- [ ] Any new reverse-engineered EU5 format is recorded in `docs/research/interoperability.md`.
