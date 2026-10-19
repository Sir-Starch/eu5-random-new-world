# ADR 0003: One product version for the mod and its generated output

**Status:** Accepted 2026-10-19 (owner decision).

## Context

Versions had drifted apart. Three generated mods hard-coded their own `metadata.json` versions (0.1.0, 0.2.0, 0.3.0), and run specs carried a separate generator output version (0.1.0–0.9.1). None of them had been published. The Steam Workshop needs one meaningful version, and a seed must keep reproducing the same mod.

## Decision

- **One version.** The project uses one SemVer version, `version` in `pyproject.toml`. `rnw.__version__` reads it from the installed package metadata. Every generated mod's `.metadata/metadata.json` and every run spec and report carry it; no other version string exists.
- **Milestones.**
  - 0.0.x: development before the first publication. The scheme starts at 0.0.1.
  - 0.1.0: the first Steam Workshop publication.
  - 1.0.0: the complete product of the [product specification](../product-spec.md), validated in game.
  - Between 0.1.0 and 1.0.0, a published feature release raises MINOR and a published fix raises PATCH.
- **Reproducibility.** Any change of generated output for the same seed and settings raises at least PATCH and updates the golden digests. A version plus a seed and settings therefore names exactly one mod. Unpublished versions may be skipped on the Workshop.
- **Game version.** `supported_game_version` follows the fingerprinted game build and changes only after a regression pass on a new patch (AGENTS.md).

## Consequences

Before this ADR, run specs had a `generator_version` key (0.1.0–0.9.1, never published). From 0.0.1 the key is `version`, so the two schemes cannot be confused. The claims ledger and log keep the old generator numbers as history.
