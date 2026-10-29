# Known limitations

Current release: **RNW 1.0.0 / epoch 59**, targeting **EU5 1.4.5 / Steam build
26211608** (2026-10-29). These are the accepted scope and operational limits;
they are not an uncompleted release checklist. See [release process](release-process.md)
for the published artifacts and [roadmap](roadmap.md) for future work.

- **Specific game build.** Other patches need their own input-contract and
  compatibility checks. The metadata's `1.4.*` match does not prove future patch
  compatibility. Worlds made before 0.13.22 lack the 1.4.5 DLC adaptations; use
  a newly generated world for a new 1.4.5 campaign. Existing saves are not migrated.
  [V-LOCAL / V-EXEC C425–C427]
- **New campaign and one world at a time.** Start in 1337 with one RNW world
  enabled. Keep that exact world mod for its saves. Restart EU5 before switching
  maps or replacing a loaded world's files: earlier in-process reloads mixed map
  data and crashed. Closing/reopening the main-menu Mods manager can refresh
  metadata/visibility (C429); that is not evidence for safely swapping a loaded map.
  [V-GAME C85, C429]
- **A code alone is not a complete old-world backup.** Exact regeneration needs
  the original algorithm, settings/rolls and game inputs. A newer game or generator
  can produce another result from the code. Preserve a built world used by saves.
  [V-EXEC C141; ADR 0003]
- **World-edge rendering.** The owner reproduced a close-zoom terrain fissure in
  vanilla. RNW retains the accepted periodic source extension for visual concealment,
  continuous identities and route/hang fixes, with independent river watersheds
  and real outlets. Remaining engine/rendering questions are tracked in the
  [wrap dossier](research/map-wrap-dossier.md). [V-GAME / V-EXEC C412–C419]
- **Balance and unusual worlds.** Campaign and regression evidence is scoped to
  the worlds/builds tested, not every seed or every mechanic. Known diagnostic
  uncertainties and inherited engine warnings need attribution before being called
  RNW defects. AI expansion and society balance remain areas for refinement.
  [C391, C397, C410–C411, C419, C425]
- **Other mods and multiplayer.** Map overhauls or mods changing the Americas can
  conflict. Other combinations and multiplayer sessions have no general validation
  claim. Matching world codes do not establish multiplayer compatibility.
- **Generation may refuse an invalid result.** Sea routes, river drawings,
  location limits and content checks reject failed invariants explicitly.
  The application offers another-seed retry; every settings/seed combination is
  not promised to succeed. [V-EXEC C406]
- **Unsigned Windows binaries.** Smart App Control may block them. The generator
  needs no administrator access. Scanner reports cover specific files and are
  not a signature or universal acceptance by antivirus software. The limitation
  is disclosed and accepted for 1.0.0. [ADR 0009; C437–C439]
- **Platform scope.** Windows and Linux/Proton are the offered routes; native Linux
  and Windows package/CLI self-tests pass in CI. The owner has run the generator
  on Windows 11 and through Workshop/Proton. macOS has a CI build but no offered
  game/platform support claim. Measurements from one machine are not performance
  guarantees for another. [C428, C438–C439, C441]
- **Mod-list text.** EU5 metadata has one title and short description, so mod-list
  titles remain English. The generator and world text use all official languages
  discovered from the game; catalogue coverage is checked before shipping. [C276, C431]

Existing local **code only** library records after installing from Workshop are
expected application data, not worlds bundled in the download. The
[generator guide](generator-guide.md#library-shared-by-installed-copies) explains
storage, recovery and what the label means (C441).
