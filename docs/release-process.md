# Release process

## Published baseline

[RNW 1.0.0](https://github.com/Sir-Starch/eu5-random-new-world/releases/tag/v1.0.0)
is the first stable release, published 2026-10-29 from tag `v1.0.0` at
`73ba1bc992c3a6dea03efb26c5de68876097d8c2` (epoch 59). Its tagged CI passed;
uploaded asset digests and checksums were verified again after download (C439).
The owner completed product acceptance and the publication-rules review (C437).
The [Workshop hub](https://steamcommunity.com/sharedfiles/filedetails/?id=3829217331)
was subsequently installed and launched by the owner; its downloaded file set
matches the prepared hub (C441).

| Field | Stable value |
|---|---|
| Public name | Random New World (RNW) |
| Mod ID | `sirstarch.randomnewworld` |
| Maintained local hub folder | `rnw_exp_hub` |
| Workshop item | `3829217331` |
| Game target for 1.0.0 | EU5 1.4.5 / Steam build 26211608 |

The updater accepts the old internal `rnw_exp_hub` ID when replacing that local
hub; new packages write the public ID. The player enables a generated world,
not the hub. Workshop downloads do not include a world library.

## Prepare a release cycle

Use [ADR 0003](adr/0003-versioning.md) to choose the product target from the whole
batch: PATCH for compatible fixes, MINOR for new compatible capabilities, MAJOR
for public-contract breaks. Ordinary main commits collect Unreleased notes and
do not each increase the version. Documentation-only maintenance can keep the
published version. Frozen tags and downloads are immutable.

- Implement and verify the requested scope. Known limitations stay disclosed;
  historical experiment checkboxes are not outstanding acceptance requests.
- Keep `pyproject.toml`, lockfile and package metadata consistent. Refresh affected
  output goldens; freeze the cycle's pending epoch/reference when needed. Application
  or hub-metadata changes do not automatically change the world algorithm epoch.
- Run relevant local checks and `make check` for code/package changes. Recheck the
  installed-game contract when game inputs or serializers change. Do not ask for
  another game sitting solely because a historical detail is unobserved.
- Update changelog, player guidance and affected official-language catalogues.
  The README describes the product; release notes describe that release.
- Audit the actual package contents, licence notices and sources. Revisit terms
  only for a specific change affecting the accepted distribution boundary
  ([legal notes](legal.md)). Generated worlds and game assets remain local.

## Build, publish and verify

Push/release/account authorization is task-specific and persists through its
necessary steps. The owner's explicit request to publish a GitHub release covers
its source/tag push, release creation and asset upload. Workshop account actions
remain with the owner. Agents do not launch/control EU5 to publish or test.

1. Start the release workflow with numeric target `vMAJOR.MINOR.PATCH` and the
   **full candidate commit SHA** in `commit`; the tag need not exist. With `commit`
   empty, the workflow requires the actual tag. General Linux/Windows CI and the
   release workflow must pass on the candidate. Fix a failed candidate under the
   same unpublished target at a new SHA.
2. Inspect the archives and self-test results. Record exact source/run identities
   and SHA-256. Never infer which build an arbitrary same-version file came from.
3. After acceptance, tag the reviewed clean commit. Push the stable tag once and
   verify the tagged workflow. It builds native archives, the Windows standalone
   and Workshop/Proton layouts, and a Python source distribution; it does not
   publish automatically. A failed frozen release is fixed under another version.
4. Audit downloaded archives and embedded checksums. Include the full project
   source snapshot, application archives, `BUILD-INFO.json`, release notes and
   `SHA256SUMS`. The build manifest ties actual artifacts to the source/run.
5. Check the two project Windows binaries (launcher and `_native.pyd`) with
   VirusTotal for their **exact hashes**; reuse an existing report for unchanged
   bytes. Record engine failures/timeouts as unknown results. A whole-archive or
   every-file scan, API key, code signing or universal antivirus acceptance is not
   a publication prerequisite. Source/dependency audits and self-tests remain
   separate checks. Windows unsigned status is disclosed.
6. Create the GitHub release, attach the checked assets and notes, then publish.
   Download the posted assets once and verify checksums. Record the release URL
   and tag/commit. The CI-only macOS build is not an offered game/platform route.

Documentation-only status updates after publication do not require rebuilding the
released binaries, moving the tag, changing the version or rescanning them.

## Workshop page and updates

Upload the generator hub only. Use tag **Map**, the hub's `.metadata` preview and
the reviewed descriptions in `docs/workshop/<language>.bbcode`. Translation
`source:` headers are internal and omitted when pasting; the English file has none.
The release's Workshop-text bundle already strips those headers and has a README
for the publisher. The hub does not require a separate README to be usable: its
metadata gives the launch instruction, and the page carries the full guide.

For later updates preserve the public mod ID and existing Workshop item, use the
reviewed package for the new release and check the downloaded item. Do not upload
`rnw_exp_world_*`, game-derived data, local library records or diagnostics. The
owner manages the Steam page and its visibility; record only actions/results
actually observed. Completing an upload/download check is a publication step,
not a reason to declare the already-prepared product unready.
