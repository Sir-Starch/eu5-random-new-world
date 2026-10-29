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
- [x] **Languages:** run the L1 release check against every official language shipped by the target game build. Every player-visible string has a translation, and each translation is current against its English source ([roadmap L1](roadmap.md)).
- [ ] **Legal and file audit:** review [legal notes](legal.md) against the current package, confirm third-party notices and licences are present, and audit source and binary archives for game assets and derived map data. Generated worlds remain local ([ADR 0009](adr/0009-hub-mod-with-generator.md)).
- [ ] **Windows and Workshop route:** the owner-run Windows 11 generator smoke passed (C428); finish the remaining trust checks in [ADR 0009](adr/0009-hub-mod-with-generator.md) and verify Workshop acceptance, or state the verified limits plainly in player-facing text. Before upload, recheck and accept the current Steam and EU5 terms and confirm the rights to every file included; the current source review leaves the scope for this item [UNKNOWN C267] ([legal notes](legal.md)).
- [x] **Player text:** prepare release notes from the changelog. Keep the README as product documentation, not release notes. Remove internal bracketed notes from the [Workshop description](workshop-description.md), and verify every feature, game-build, installation, removal, warning, and support statement against the candidate.
- [x] **Images:** the screenshots of the generator's window in `docs/images/` may be published (owner, 2026-10-24; [legal notes](legal.md)). Take them again on a demo library, with the platform's plain light style and without paths or hardware of the machine, whenever the window changes. Game files, textures and rasters stay out; any upload to the Workshop is an owner action (P1 in the [roadmap](roadmap.md)).
- [x] **Version and reproducibility:** check `pyproject.toml`, `uv.lock`, generated mod metadata and run records use the same version. Choose the version from the whole release relative to the previous stable release, not per commit. Update output goldens when needed; if a world's mod changes outside `.metadata`, freeze the cycle's pending algorithm epoch and final reference world. Do not rewrite frozen epochs ([ADR 0003](adr/0003-versioning.md); [ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md)).

## Candidate artifact gate

Build pre-tag artifacts with `workflow_dispatch`: `tag` is the intended numeric target (for example `v1.0.0`) and `commit` is the full candidate SHA. The tag need not exist yet. With `commit` empty, the workflow requires the actual tag; tag pushes use this mode too. Both paths validate the package version and clean exact checkout, run `make check`, and pass the resolved SHA to both builders. Fix a failed pre-tag candidate at a new SHA under the same target. After acceptance, tag exactly the reviewed commit and verify the tagged build before publication. Keep stable tags immutable. For that candidate, verify:

- [x] CI is green on the release commit for the required Linux and Windows checks (P1). A run on another commit is not evidence for this candidate.
- [x] The release workflow's tag check matches `pyproject.toml`; package self-tests and archive audits pass ([release workflow](../.github/workflows/release.yml), [`packaging/release.py`](../packaging/release.py)).
- [x] The source archive and every platform archive are present, and the published SHA-256 files cover every archive being handed off. Verify each checksum against the downloaded candidate files.
- [x] The candidate contains the correct third-party notices and no game assets, generated-world files, local logs, saves, or unapproved screenshots. Approved documentation images may travel with the source archive.
- [x] Keep the workflow artifacts as a candidate until the maintainer accepts them. The workflow uploads build artifacts for review; it does not create a GitHub release or publish to the Workshop.

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

Preparation date: **2026-10-29**. **RNW 1.0.0 / epoch 59** is a built and
packaged candidate for **EU5 1.4.5 / Steam build 26211608**, including Across
the Pillars adaptation. The code, CI and archive gates are prepared; the release
is **not yet accepted for publication**. The roadmap still records full N0–N5
acceptance as open, N5 engine results as not run, R7d as offline-only, and broader
U1 controls/world gameplay review as open. The exact user-facing game acceptance
must be performed by the owner; EU5 was not launched or controlled here. The
current Workshop rights question in C267 also remains unresolved. Historical game
observations retain their recorded versions.

| Area | Evidence and remaining boundary |
|---|---|
| Product and player text | [V-EXEC C431] Version/lockfile and stable classifier are 1.0.0; dated changelog and release notes are prepared. README, contribution/security policy, limitations and all eleven Workshop descriptions state the supported build and unsigned-Windows limitation. Eight current GUI screenshots use the approved demo copy of the EVXP library. Future roadmap expansion is not a 1.0.0 inclusion promise. |
| Product acceptance | **Open:** the [roadmap](roadmap.md) says N0–N5 full acceptance remains open, N5 engine results are NOT-RUN, R7d is offline-only, and broad U1 controls/generated-world gameplay review remains open. Existing owner tests at older versions remain valid only for those versions. No campaign is requested; the project requires a bounded owner-run game acceptance before calling 1.0.0 complete. |
| Local checks | [V-EXEC C431] Locked sync and full checks pass: 2,140 Python tests (14 optional skips), 23 Rust tests, formatting, lint and strict typing. The full installed-game reference suite passes 13 tests; one opt-in layer check is skipped. The event expectation was corrected from 82 to 83 for the already adapted D009 diaspora gate; generator output is unchanged. |
| Languages and world output | [V-EXEC C431] All player-visible catalog keys/fingerprints and eleven Workshop texts pass the release checks against the installed game's official languages. The 1.0.0 exporter reproduces all **867** nonmetadata files of epoch 59, SHA-256 `23c0437734288ffa913061f627838855c97962185fe939da18b313ccb1bd9c85`; the frozen reference is unchanged. |
| Exact-source CI | [V-EXEC C435] On candidate commit `5645d763f81f23acd4f065ab110aab7a7c9165b1`, the [general CI](https://github.com/Sir-Starch/eu5-random-new-world/actions/runs/40781005641) and [release workflow](https://github.com/Sir-Starch/eu5-random-new-world/actions/runs/40781022865) completed with every job successful. The workflow ran Linux and Windows checks, packaged/self-tested both app variants, built the Linux and Windows release files, and validated the Windows packages on Windows. |
| Downloaded packages | [V-EXEC C435] Downloaded CI Windows standalone and Workshop/Proton ZIPs, Linux archive and Python sdist. Their embedded SHA256SUMS match; archive audits found no game assets or generated worlds. The Windows artifact contains only the two delivery ZIPs and checksum manifest. The complete source archive and Workshop text bundle are also present in the local hand-off folder. |
| Installed candidate | [V-EXEC C435] Installed the 3,272-file Windows hub from the CI artifact with package/source verification and a passing isolated Wine self-test. The prior hub is retained at `.rnw-hub-backups/1.0.0-1793232100930439192`. The separately installed 878-file world remains a local candidate with both library entries; it is not part of a public archive. No EU5 launch or control. |
| VirusTotal | [SOURCE / V-EXEC C432, C435] VirusTotal MCP examined the exact final CI launcher and native extension. The launcher completed with zero malicious/suspicious detections; per-engine totals and exact file hashes are in the [release notes](releases/1.0.0.md#windows-binary-scans). The launcher returned 65 undetected, four unsupported, one timeout and five engine failures; the native extension returned 66 undetected, four unsupported, one timeout and four engine failures. Neither had malicious or suspicious detections. Timeouts and failed engines are unknown results, not clean results. These file scans do not cover archives or every dependency and are not a safety guarantee. |
| Game and platform limits | Owner observations and Windows 11 smoke C428 remain valid at their recorded versions. Known wrap, DLC completion, balance and multiplayer limits remain disclosed. macOS is not an offered package or a verified game route. Current 1.0.0 game acceptance remains open as described above. |
| Source/licences | [V-EXEC / SOURCE C431] Third-party notices and licences travel with the packages; no game assets or generated worlds are included. A 2026-10-29 check found the Steam Subscriber Agreement revision dated 2026-09-10 and Paradox's 2026-01-21 agreement; public pages still do not settle item-specific EU5 Workshop rights (C267). Review and accept applicable terms and confirm rights before upload; this source review is not a legal clearance. Windows binaries remain unsigned and this is stated in player-facing text. |
| External publication | **Pending:** stable `v1.0.0` tag, GitHub Release and Workshop upload/download acceptance. CI uploads candidate artifacts only. No tag, release, account agreement or Workshop publication has been performed. |

The candidate packages, source, checksums and verification records are available
in the local `dist/release-1.0.0/` hand-off folder. Keep generated worlds out of
public distributions. The stable tag remains uncreated until the maintainer accepts the exact
candidate, completes the bounded game acceptance and resolves the Workshop
rights review.
