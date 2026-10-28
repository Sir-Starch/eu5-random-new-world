# ADR 0003: Product releases and algorithm epochs

**Status:** Accepted 2026-10-19; revised 2026-10-28 at the owner's request for 1.0.0.
This revision replaces the rule that every output-changing commit raises PATCH.

## One product version

`version` in `pyproject.toml` is the source of truth. The installed package,
application, hub, generated mod metadata and run reports use it; `uv.lock` follows
it. Internal file-format numbers and the private Rust crate version are not
product versions. Published versions follow [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html)
[SOURCE, specification 2.0.0, accessed 2026-10-28].

1.0.0 is the first complete product release. Preparing it does not declare its
acceptance or authorize publication. The [release process](../release-process.md)
records the evidence and remaining gates. Historical 0.x versions and epochs stay
as recorded; do not renumber them.

## What compatibility means for RNW

The supported public contract is the documented generator CLI, settings and
presets, reading world codes and `.rnworld` files, library/recovery data, and
opening existing worlds without destructive migration. Private Python/Rust
functions are implementation details. Existing built world mods are preserved;
updating the generator does not rewrite a world's mod or migrate its EU5 saves.

Exact regeneration additionally requires the original algorithm epoch, resolved
settings, seed/rolls and game inputs. A new epoch may produce a different world
from the same settings; that alone is **not** a breaking product change. The
application must disclose the difference and keep existing data readable. EU5
save compatibility and support for a particular game build are separate claims.

## When each number changes

Select the largest required increase across the whole release, relative to the
last published stable release. Reset the lower digits when MAJOR or MINOR rises.

| Part | Trigger | Examples |
|---|---|---|
| PATCH: 1.0.0 → 1.0.1 | Compatible corrections and maintenance; no new player capability | Fix generation, a hang, translation, installation or packaging; adapt scripts to an EU5 patch within the supported environment; optimize with equal output |
| MINOR: 1.0.1 → 1.1.0 | Compatible new player capability or public option; deprecation with continued support | New preset, society/story family, atlas tool, optional setting, supported platform; announce a future CLI removal |
| MAJOR: 1.1.0 → 2.0.0 | Break the supported public contract without a compatible reader or migration | Remove/rename a documented CLI option; stop reading supported world/library formats; require destructive migration; drop a supported platform or raise its minimum requirements incompatibly |

A larger refactor, new UI toolkit, algorithm epoch, long changelog or EU5 major
patch does not automatically require MAJOR: assess its effect on this contract.
A game patch requiring only a compatibility correction is PATCH; a new optional
DLC mechanic is MINOR; abandoning a promised supported environment is MAJOR.
Documentation, tests, CI and refactors with no shipped behavior change do not
require a product release. If a shipped package itself must be corrected, use PATCH.

## Main, candidates and release commits

- **No per-commit version bumps.** Ordinary commits and merges into `main` collect
  changes under **Unreleased** in `CHANGELOG.md`. Use descriptive commit subjects;
  reserve a version prefix for the release commit.
- **One target per release cycle.** Reserve the next numeric version when starting
  a cycle that changes shipped code, and keep it across its implementation
  commits. Documentation-only work may keep the previous number. Choose PATCH,
  MINOR or MAJOR from the table; promote an unpublished target if the scope grows.
  Before the first stable release the next target is 1.0.0, once its preparation
  begins. This decision alone does not change the current 0.x package.
- **Development builds are identified by commit.** A working tree or untagged
  `main` build is not a stable release even if its package has a three-part number.
  Retain its full commit SHA and artifact checksum (and the diff if dirty) with
  any local candidate evidence. A version alone cannot reproduce these builds.
  Share world codes with players only from frozen releases. Never silently replace
  a published download with a development build of the same number.
- **Candidate numbers are not product versions.** Name internal candidates by
  target, full commit SHA and CI run/artifact identity. Manual release builds
  accept a full candidate SHA before a stable tag exists. Fixes at this stage
  keep the same target and use a new candidate SHA. Do not put `-rc`, `.dev`
  or `+sha` into `pyproject.toml`: current world codes encode three integers
  [V-EXEC: `rnw.app.worldcode.HEAD`, `_generator_parts`; `rnw.epoch.parse`]. Adding
  prerelease syntax requires a separate compatible format design first.
- **Freeze a release once.** Update the target and lockfile together if needed,
  move Unreleased notes to the dated version entry, complete the release gates,
  and make a signed-off release commit. Build and review candidate artifacts
  from its full SHA; a failed candidate does not consume a stable version. After
  acceptance, the local tag is `vMAJOR.MINOR.PATCH` on exactly that clean commit.
  A stable tag is immutable: fixes after tagging use another version/tag. Publication of the reviewed artifacts remains an
  explicit owner action; a merge or tag never publishes automatically.
- **Hotfixes** branch from the affected stable tag, take the next unused PATCH
  on that supported line, run the same gates, and bring the fix back to `main`.
  Never lower `main`'s target or move an existing tag to make a hotfix.

## Algorithm epochs and golden digests

Epochs describe generated world bytes, independently of the size of a product
release ([ADR 0010, G](0010-layered-worlds-and-a-generator-of-its-own.md)).

- An output change updates the relevant golden digests in the implementing change.
  A world's non-`.metadata` files changing (including game text, preset values,
  random stream order or cover shaders) requires a new epoch relative to the
  previous frozen release, with an `ALGORITHM_SINCE` entry for the cycle's target
  and a corresponding `tests/golden_world.json` reference world.
- All output work before the target is frozen may share **one pending epoch**.
  Refresh its goldens/reference when its bytes change. This does not promise
  reproduction of intermediate development worlds: retain their exact source
  commit and inputs. Never refresh a frozen epoch's goldens in place. If the
  cycle's target is promoted, retarget only its pending epoch entry.
- A metadata-only, application-only or byte-preserving optimization change keeps
  the epoch. A version-only transition to 1.0.0 also keeps the epoch when checked
  world bytes are unchanged. Several product releases may share one epoch.
- Before tagging, verify the final reference world against the target game inputs.
  Preserve the release tag, input manifest and checked digest. Exact game support
  changes only after fingerprinting and regression checks, not from a wildcard
  `supported_game_version` label. A new game build can change the inputs without
  changing RNW's epoch; record both identities.

This keeps published reproduction promises intact while allowing many buildable
commits to contribute to one release. It adds no version suffix or world-code
format change and needs no release for documentation alone.
