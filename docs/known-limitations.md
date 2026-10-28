# Known limitations

Current as of **28 October 2026 — RNW 1.0.0**, targeting EU5 1.4.5 / build 26211608.
The release preparation and publication status is tracked in [release process](release-process.md).

- **Specific EU5 build only.** Current checks target the public EU5 **1.4.5,
  Steam build 26211608**, including Across the Pillars script adaptation.
  Compatibility with later patches is not established; a `1.4.x` metadata label
  is not a guarantee. Worlds generated before 0.13.22 lack the new DLC overrides;
  use a newly generated world for this compatibility candidate. Existing saves
  are not migrated. [V-LOCAL / V-EXEC C425–C427; compatibility audit](research/compatibility-1-4-5.md)
- **New campaigns, one world at a time.** Start in 1337 with one RNW world mod
  enabled. Keep that exact mod for its saves: regenerating or rerolling a world
  is not a save migration. Restart EU5 before switching maps or replacing a
  loaded world's files; reloading within the same process has produced mixed
  map/setup data and a crash on EU5 1.4.2. [V-GAME C85; INFERRED from C85, C142]
- **A World Code alone does not preserve an old world.** Exact reproduction
  also needs the matching generator algorithm and game inputs. A newer generator
  or game patch can change the result; regeneration after an update does not
  guarantee that an old save remains usable. [V-EXEC C141; INFERRED from ADR 0003]
- **Verification has limits.** The owner reports QUXQ **0.13.17 / EU5 1.4.4**
  reached 1490 and accepts the previous work; some coastal current directions
  remain imperfect and are not a release blocker (C411). The **0.13.19** independent
  seam watersheds and **0.13.20** restored visual source extension have offline
  checks; the combined world was later observed in the owner’s 0.13.20 / EU5 1.4.4 campaign reaching 1768 (C419). Detailed seam-rendering acceptance remains unverified (C417–C419). Neither campaign
  progress nor acceptance proves every mechanic. The owner’s short **1.4.5**
  session reaches 1342 on 0.13.21; the newly adapted DLC expeditions and Golden
  Century interactions have offline verification, without an engine-completion
  observation. [V-GAME owner/logs / V-EXEC / UNKNOWN C425–C427]
- **World-edge terrain and rivers.** The owner reproduces a close-zoom terrain
  crack in mod-free vanilla at Kitagnaq. RNW accepts this rendering limitation.
  After the owner reported worse visibility with the workaround removed, 0.13.20
  restores its previous source extension while retaining mechanical wrap fixes.
  Since 0.13.19, independent river basins stop channels crossing the display edge and require genuine water outlets;
  detailed river-rendering acceptance remains unverified. Earlier observations
  of disappearance remain valid; a historical comparison is planned in the [separate dossier](research/map-wrap-dossier.md).
  [V-GAME owner / V-EXEC C412–C418; exact engine cause UNKNOWN]
- **Some campaign diagnostics remain unresolved.** QUXQ’s nine map-edge locator warnings place every object on its own identity;
  their reported distances match an unnormalized wrap-box comparison (C414).
  Gameplay consequences and absent minority-culture diagnostics remain uncertain. AI expansion and
  society balance are not fully validated. [V-LOCAL C391; UNKNOWN C328, C397]
- **Other mods and multiplayer are unverified.** Map overhauls and mods changing
  the Americas can conflict with RNW's files. No compatibility guarantee is made
  for UI or Old World mods either. Matching World Codes are not evidence of a
  successful multiplayer session. [INFERRED from overlapping files; UNKNOWN]
- **Generation can refuse a world.** Invalid sea routes, river drawings or
  location limits stop generation with an error. A different-seed retry is
  available; every seed/settings combination is not guaranteed to succeed.
  [V-EXEC C406]
- **Windows binaries are unsigned.** Smart App Control may block the generator.
  No signing, scanner verdict or universal antivirus acceptance is claimed; no
  administrator access is required. [ADR 0009](adr/0009-hub-mod-with-generator.md)
- **Platform testing is limited.** The owner smoke-tested the packaged generator's
  launch, generation and mod installation on Windows 11 (C428). Windows CLI/CI,
  memory and performance measurements, macOS, signing and public Workshop
  delivery remain unverified. [V-GAME owner C428; UNKNOWN]
- **Mod-list titles remain English.** The generator and world texts have all
  eleven official languages, but EU5 mod metadata carries a single title and
  description. Translation coverage is checked offline; language acceptance
  remains open. [V-LOCAL C276; V-EXEC C273–C275; UNKNOWN]

For operation, see the [Generator guide](generator-guide.md). Evidence IDs above
refer to the [claims ledger](research/claims-ledger.md); release gates are in
[Current readiness](release-process.md#current-readiness).
