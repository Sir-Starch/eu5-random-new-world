# Known limitations

Current as of **28 October 2026 — RNW 0.13.18**. This is a development build;
the first public release, 1.0.0, is still pending.

- **Specific EU5 build only.** Current checks target EU5 **1.4.4, Steam build
  26142040**, with the fingerprinted 1.4.3 game data. Compatibility with other
  patches is not established; a `1.4.x` label is not a guarantee.
  [V-LOCAL C198, C408]
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
  remain imperfect and are not a release blocker (C411). The **0.13.18** visual
  workaround removal is verified offline and installed, but unobserved in game
  (C416). Neither campaign progress nor acceptance proves every mechanic.
- **World-edge terrain and rivers.** The owner reproduces a close-zoom terrain
  crack in mod-free vanilla at Kitagnaq. RNW accepts this rendering limitation;
  0.13.18 removes its visual source-extension workaround while retaining the
  mechanical wrap fixes. Rivers crossing the edge are currently serialized as
  separate networks and can visibly break. The intended river policy awaits the
  owner's decision. Earlier observations of disappearance remain valid; a
  historical comparison is planned in the [separate dossier](research/map-wrap-dossier.md).
  [V-GAME owner / V-EXEC C412–C416; exact engine cause UNKNOWN]
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
- **Platform testing is limited.** Linux and Windows-runtime checks under
  Wine/Proton exist; native Windows, macOS, signing and the public Workshop
  delivery route remain unverified. [V-EXEC/UNKNOWN C145, C392, C408]
- **Mod-list titles remain English.** The generator and world texts have all
  eleven official languages, but EU5 mod metadata carries a single title and
  description. Translation coverage is checked offline; language acceptance
  remains open. [V-LOCAL C276; V-EXEC C273–C275; UNKNOWN]

For operation, see the [Generator guide](generator-guide.md). Evidence IDs above
refer to the [claims ledger](research/claims-ledger.md); release gates are in
[Current readiness](release-process.md#current-readiness).
