# Release process

This is the maintainer's checklist for the publication phase (P1). It describes the hand-off from a verified source tag to separately reviewed GitHub and Steam Workshop artifacts. It does not authorize or perform a push, GitHub release, Workshop upload, or account action.

## Release boundaries

- The project has one product version, read from `pyproject.toml`. Under [ADR 0003](adr/0003-versioning.md), 0.x is development and is not published; the first product release is 1.0.0 after the complete product is accepted.
- A GitHub release carries the source and application packages for the same version ([roadmap P1](roadmap.md)). A Steam Workshop item carries the hub mod and generator ([ADR 0009](adr/0009-hub-mod-with-generator.md)). These are separate distributions with separate gates.
- Generated world mods are built locally from the player's EU5 installation. Do not attach a generated world, game files, or files derived from the game's data to a repository release or Workshop item ([legal notes](legal.md); [ADR 0009](adr/0009-hub-mod-with-generator.md); [INFERRED C15]).
- CI builds and audits candidate artifacts from a tag; it uploads artifacts but does not publish them ([V-EXEC C145]). Keep CI implementation and its run evidence in the workflow and CI records.

## Before tagging 1.0.0

Complete each gate and retain its evidence before making a release tag.

- [ ] **Product gates:** P1 dependencies R9, R10, U1, N0–N5 and L1 are accepted as described in the [roadmap](roadmap.md). The 1.0.0 product is complete and validated in game, as required by ADR 0003.
- [ ] **Game compatibility:** record the exact EU5 version and Steam build tested. Recheck the map-contract fingerprint and game-facing behavior for that build; a matching `1.4.*` metadata value alone is not compatibility evidence ([AGENTS.md](../AGENTS.md), [claims ledger](research/claims-ledger.md); [INFERRED C18]).
- [ ] **Languages:** run the L1 release check against every official language shipped by the target game build. Every player-visible string has a translation, and each translation is current against its English source ([roadmap L1](roadmap.md)).
- [ ] **Legal and file audit:** review [legal notes](legal.md) against the current package, confirm third-party notices and licences are present, and audit source and binary archives for game assets and derived map data. Generated worlds remain local ([ADR 0009](adr/0009-hub-mod-with-generator.md)).
- [ ] **Windows and Workshop route:** settle the pending Windows trust and Workshop acceptance checks in [ADR 0009](adr/0009-hub-mod-with-generator.md), or state the verified limits plainly in player-facing text. Before upload, recheck and accept the current Steam and EU5 terms and confirm the rights to every file included; the current source review leaves the scope for this item [UNKNOWN C267] ([legal notes](legal.md)).
- [ ] **Player text:** prepare release notes from the changelog. Keep the README as product documentation, not release notes. Remove internal bracketed notes from the [Workshop description](workshop-description.md), and verify every feature, game-build, installation, removal, warning, and support statement against the candidate.
- [ ] **Images:** the screenshots of the generator's window in `docs/images/` may be published (owner, 2026-10-24; [legal notes](legal.md)). Take them again on a demo library, with the platform's plain light style and without paths or hardware of the machine, whenever the window changes. Game files, textures and rasters stay out; any upload to the Workshop is an owner action (P1 in the [roadmap](roadmap.md)).
- [ ] **Version and reproducibility:** check `pyproject.toml`, `uv.lock`, generated mod metadata and run records use the same version. If output changes, raise PATCH at minimum and update golden digests; if a world's mod changes outside `.metadata`, create a new algorithm epoch and reference world ([ADR 0003](adr/0003-versioning.md); [ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md)).

## Candidate artifact gate

After the gates above are complete, run the repository release workflow against the exact version tag. If using `workflow_dispatch`, verify that the checked-out commit is the commit named by the selected tag as well as checking the version string. For that tag, verify:

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

As of 2026-10-28, the current product is **0.13.22 / epoch 59**, a development
candidate rather than a 1.0.0 release (`pyproject.toml`, [changelog](../CHANGELOG.md)).
The current compatibility target is the public **EU5 1.4.5 / Steam build
26211608**, including Across the Pillars. The map contract is unchanged from
1.4.3/1.4.4, while the new DLC requires explicit script adaptation. The
[compatibility audit](research/compatibility-1-4-5.md), C425–C427, distinguishes
fixed historical geography from dynamic colonial mechanics and records offline
checks and delivery.

The owner's 1.4.5 session loads 0.13.20 then 0.13.21, reaches 1342 and exits
normally; it exposes missing DLC waypoints that 0.13.22 addresses. It does not
validate completion of the newly adapted expeditions or Golden Century content
[V-GAME owner/logs / UNKNOWN new engine result C425–C427]. The latest recorded
long-campaign evidence is Restored visual wrap / **0.13.20 on EU5 1.4.4**, reaching
1768, with the limits of C419–C423. It predates the complete-government and DLC
corrections. The 1.0.0 product, language, compatibility, legal, packaging and
platform gates above therefore remain separate acceptance boundaries; this patch
is not a declaration that 1.0.0 is ready to publish.

Publication, native-Windows trust and Workshop acceptance remain separate
boundaries under ADR 0009; no upload, signing or remote CI result is inferred
from a local Wine check. The Steam/EU5 terms review and its remaining rights
limits are recorded in [legal notes](legal.md), C267. These are recorded limits,
not requests for another campaign or a new game sitting.
