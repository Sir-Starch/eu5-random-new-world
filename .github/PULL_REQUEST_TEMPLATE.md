## What and why

<!-- What does this change, and which issue or roadmap item does it address? -->

## How it was verified

<!-- Tests added or run, offline checks, and in-game observations with the game version. Label claims as in CONTRIBUTING.md (V-EXEC, V-GAME, …). -->

## Checklist

- [ ] Appropriate checks pass: `make check` for code/package changes; content/link checks for documentation only.
- [ ] Every commit is signed off (`git commit -s`, Developer Certificate of Origin).
- [ ] No game files, derived rasters, logs, saves or generated worlds are included. Documentation screenshots follow the approved policy in `docs/legal.md`.
- [ ] If generated output changes: golden digests and the cycle's pending epoch/reference world are current (ADR 0003); frozen epochs are preserved. Ordinary commits do not bump the product version.
- [ ] Documentation and `CHANGELOG.md` (*Unreleased*) are updated where needed.
- [ ] Any new reverse-engineered EU5 format is recorded in `docs/research/interoperability.md`.
