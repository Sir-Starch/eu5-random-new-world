# Known limitations

Current as of **28 October 2026 — RNW 0.13.17**. This is a development build;
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
- **Latest changes still await game validation.** The latest long campaign
  reached 1849 on **0.13.5 / EU5 1.4.4**. Subsequent treaty, river, starting-building
  and AI changes, and the **0.13.11–0.13.16 ocean-route refinements**, and **0.13.17 agrarian and market changes**, have offline
  checks, but their current in-game behavior is unverified. That campaign does
  not validate the current build. [V-LOCAL/V-EXEC C389–C392, C397, C408, C410; UNKNOWN]
- **Some campaign diagnostics remain unresolved.** Warnings about map-edge
  city/unit placement and absent minority-culture populations appeared in the
  0.13.5 campaign; their gameplay impact and causes remain uncertain. AI expansion and
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
