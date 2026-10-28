# Release process

This is the maintainer's checklist for the publication phase (P1). It describes the hand-off from a verified source tag to separately reviewed GitHub and Steam Workshop artifacts. It does not authorize or perform a push, GitHub release, Workshop upload, or account action.

## Release boundaries

- The project has one product version, read from `pyproject.toml`. Under [ADR 0003](adr/0003-versioning.md), ordinary main commits keep one target per release cycle and collect Unreleased notes. PATCH fixes, MINOR compatible new capabilities, MAJOR public-contract breaks. The first product release is 1.0.0 after acceptance; a target version is not a published release.
- A GitHub release carries the source and application packages for the same version ([roadmap P1](roadmap.md)). A Steam Workshop item carries the hub mod and generator ([ADR 0009](adr/0009-hub-mod-with-generator.md)). These are separate distributions with separate gates.
- Generated world mods are built locally from the player's EU5 installation. Do not attach a generated world, game files, or files derived from the game's data to a repository release or Workshop item ([legal notes](legal.md); [ADR 0009](adr/0009-hub-mod-with-generator.md); [INFERRED C15]).
- CI builds and audits candidate artifacts from a pinned commit or tag; it uploads artifacts but does not publish them ([V-EXEC C145]). Keep CI implementation and its run evidence in the workflow and CI records.

## Before tagging 1.0.0

Complete each gate and retain its evidence before making a stable release tag.
Build pre-tag candidates by full commit SHA as described below, so a failed
candidate can be fixed without consuming the 1.0.0 version.

- [ ] **Product gates:** P1 dependencies R9, R10, U1, N0–N5 and L1 are accepted as described in the [roadmap](roadmap.md). The 1.0.0 product is complete and validated in game, as required by ADR 0003.
- [ ] **Game compatibility:** record the exact EU5 version and Steam build tested. Recheck the map-contract fingerprint and game-facing behavior for that build; a matching `1.4.*` metadata value alone is not compatibility evidence ([AGENTS.md](../AGENTS.md), [claims ledger](research/claims-ledger.md); [INFERRED C18]).
- [ ] **Languages:** run the L1 release check against every official language shipped by the target game build. Every player-visible string has a translation, and each translation is current against its English source ([roadmap L1](roadmap.md)).
- [ ] **Legal and file audit:** review [legal notes](legal.md) against the current package, confirm third-party notices and licences are present, and audit source and binary archives for game assets and derived map data. Generated worlds remain local ([ADR 0009](adr/0009-hub-mod-with-generator.md)).
- [ ] **Windows and Workshop route:** the owner-run Windows 11 generator smoke passed (C428); finish the remaining trust checks in [ADR 0009](adr/0009-hub-mod-with-generator.md) and verify Workshop acceptance, or state the verified limits plainly in player-facing text. Before upload, recheck and accept the current Steam and EU5 terms and confirm the rights to every file included; the current source review leaves the scope for this item [UNKNOWN C267] ([legal notes](legal.md)).
- [ ] **Player text:** prepare release notes from the changelog. Keep the README as product documentation, not release notes. Remove internal bracketed notes from the [Workshop description](workshop-description.md), and verify every feature, game-build, installation, removal, warning, and support statement against the candidate.
- [ ] **Images:** the screenshots of the generator's window in `docs/images/` may be published (owner, 2026-10-24; [legal notes](legal.md)). Take them again on a demo library, with the platform's plain light style and without paths or hardware of the machine, whenever the window changes. Game files, textures and rasters stay out; any upload to the Workshop is an owner action (P1 in the [roadmap](roadmap.md)).
- [ ] **Version and reproducibility:** check `pyproject.toml`, `uv.lock`, generated mod metadata and run records use the same version. Choose the version from the whole release relative to the previous stable release, not per commit. Update output goldens when needed; if a world's mod changes outside `.metadata`, freeze the cycle's pending algorithm epoch and final reference world. Do not rewrite frozen epochs ([ADR 0003](adr/0003-versioning.md); [ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md)).

## Candidate artifact gate

Build pre-tag artifacts with `workflow_dispatch`: `tag` is the intended numeric target (for example `v1.0.0`) and `commit` is the full candidate SHA. The tag need not exist yet. With `commit` empty, the workflow requires the actual tag; tag pushes use this mode too. Both paths validate the package version and clean exact checkout, run `make check`, and pass the resolved SHA to both builders. Fix a failed pre-tag candidate at a new SHA under the same target. After acceptance, tag exactly the reviewed commit and verify the tagged build before publication. Keep stable tags immutable. For that candidate, verify:

- [ ] CI is green on the release commit for the required Linux and Windows checks (P1). A run on another commit is not evidence for this candidate.
- [ ] The release workflow's tag check matches `pyproject.toml`; package self-tests and archive audits pass ([release workflow](../.github/workflows/release.yml), [`packaging/release.py`](../packaging/release.py)).
- [ ] The source archive and every platform archive are present, and the published SHA-256 files cover every archive being handed off. Verify each checksum against the downloaded candidate files.
- [ ] The candidate contains the correct third-party notices and no game assets, generated-world files, local logs, saves, or screenshots.
- [ ] Keep the workflow artifacts as a candidate until the maintainer accepts them. The workflow uploads build artifacts for review; it does not create a GitHub release or publish to the Workshop.

## GitHub release hand-off

The maintainer performs the external publication after accepting the candidate:

- [ ] Create the GitHub release for the reviewed version tag and attach the matching source archive, application archives, and their checksum files.
- [ ] Use the prepared release notes and link to the source tag. Do not add generated worlds or derived game files.
- [ ] Download the posted assets once and recheck their checksums against the candidate.

## Steam Workshop hand-off

Workshop publication is a separate owner action and is gated on the tested delivery route and current legal review:

- [ ] Upload only the hub mod and generator package. Never upload a generated world or a package containing derived vanilla map data.
- [ ] Use the reviewed Workshop description (`docs/workshop/<language>.bbcode`, one per language, pasted without its first `source:` line), preview image, and approved screenshots. Remove every editorial bracketed note before upload.
- [ ] Confirm the item is free, the required dependency notices travel with it, and the installation/removal instructions match the published build.
- [ ] Verify the Workshop page and downloaded item after publication. Record the item identifier and exact product/game versions in the project notes.

## Current readiness

Audit date: **2026-10-28**. The inspected working tree targets **0.13.23 / epoch
59**, including the already pending visibility instructions; it is not a frozen
1.0.0 candidate. This audit changes the release rules and packaging checks,
without changing generated world bytes. The compatibility target remains public
**EU5 1.4.5 / Steam build 26211608**, including Across the Pillars
([compatibility audit](research/compatibility-1-4-5.md), C425–C427).

| Area | Evidence and remaining action |
|---|---|
| Source checks | [V-EXEC C430] Locked sync and `make check`: formatting, lint, strict typing, 2,140 Python tests passed (14 optional skips), Rust format/clippy and 23 tests passed. This is local working-tree evidence, not remote CI on a release tag. |
| Installed game and languages | [V-EXEC C430] The read-only local suite passes 12 tests against EU5 1.4.5, including its own official language list, content decisions and map/lobby contracts. Two opt-in full-world/layer checks skip. Catalog source fingerprints, window and Workshop translations also pass the full suite. No new game launch or campaign is required by this audit. |
| Reproduction | [V-EXEC C427] Epoch 59's 867-file reference digest was independently reproduced during the 1.4.5 adaptation. No world-byte change in this phase; no new epoch. Retain that reference at the final version-only transition and verify it as part of the final candidate. Intermediate main builds additionally need their exact source commit. |
| Existing local hub | [V-EXEC C430] `dist/rnw_exp_hub` passes file/binary safety checks but its metadata is **0.13.1** and its sources differ from the checkout. It is stale, unrelated to the updated installed profile hub; do not upload this folder as 1.0.0. Build the final hub from the pinned release commit. |
| Source archive | [V-EXEC C430] A working-tree 0.13.23 sdist builds, passes the archive audit and has a SHA-256 manifest. It is an audit sample under ignored `local_data/`, not a release asset. Final archives must come from the frozen release commit. |
| Release pipeline | [V-EXEC C430] Added clean exact-tag/full-candidate-SHA gates, pinned both builders to its resolved SHA, added source checksums, retained Windows checksums and checked them before the Windows smoke. Synthetic tests cover mismatched HEAD, modified/staged/untracked files and invalid tags/SHA selectors, including a pre-tag build. The edited workflow still needs a successful remote run on the final tag. |
| Platform route | [V-GAME owner C428] Windows 11 launch, generation and mod installation passed for 0.13.22 without reported warnings. Linux/Proton has earlier owner evidence (C111–C115). Neither is an exact-1.0.0 artifact check. macOS is unverified; its build job is not a support guarantee. |
| Acceptance and known limits | [V-GAME / UNKNOWN C411, C419–C428] Existing owner acceptance and campaigns stand; the DLC completion, balance and wrap limits stay in [known limitations](known-limitations.md). These unknowns do not demand another campaign or automatically block the release. Future hydrology, society, content and Tauri work in the roadmap is not silently added to 1.0.0. Record the owner's final scope acceptance with the candidate. |
| Public metadata and text | **Not prepared as 1.0.0 yet:** package/lockfile still say 0.13.23; the classifier is Alpha; README and limitations still say pre-release, and no dated 1.0.0 changelog entry exists. Set these together in the final release-preparation commit. Recheck screenshots against its window and all Workshop languages against the final English. Keep the private-package classifier unless PyPI publication is separately intended. |
| Trust and Workshop | **Owner publication boundary:** signing, scanner submissions, Workshop acceptance/download and the item-specific Steam/EU5 rights review remain as recorded in [ADR 0009](adr/0009-hub-mod-with-generator.md) and [legal notes](legal.md), C267. Before shipping unsigned binaries, state the Windows trust limitation in player text as ADR 0009 requires; a no-warning smoke is not a signing or Smart App Control result. Verify actual upload/download acceptance at publication, not by pretending it can be established offline. |

**Disposition:** the local code, translation and source-archive checks pass. A
publishable 1.0.0 still needs its final version/text commit, matching tagged
platform artifacts and checksums with successful CI, and the owner-controlled
publication/trust decisions above. No tag, push, GitHub release, scanner upload
or Workshop action is performed by this audit. Detailed policy is in ADR 0003;
this table is the single current readiness record.
