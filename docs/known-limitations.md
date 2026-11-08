# Known limitations

These limits apply to **RNW 1.1.0**. For installation and everyday use, see the
[generator guide](generator-guide.md).

## Game compatibility and saves

- **EU5 1.4.*.** New patches in this branch are usually compatible without a
  generator update. The latest fully verified version is **EU5 1.4.7, Steam
  build 26377361**. This branch guidance does not migrate an existing map to a
  different game version.
- **New 1337 campaigns only.** A generated map cannot be added to an existing
  campaign. Keep the exact generated world mod used by each save and continue
  that campaign on the exact EU5 version used to generate its map. Updating the
  generator does not migrate saves or update their maps. A world code or compact
  `.rnworld` file stores the recipe, not a complete backup: a different generator
  algorithm or game files can produce a different world.
- **One world at a time; restart when switching.** Enable only the generated
  world you intend to play, with the Workshop generator item disabled. Fully
  restart EU5 before switching maps or replacing a loaded world's files;
  switching within the same game session can mix map data and cause crashes.
- **Other mods can conflict.** Map overhauls and mods replacing American
  geography or content are the main risk; compatibility with arbitrary mod
  combinations is not guaranteed. Refined Colonization is supported with this
  load order: **Refined Colonization → generated RNW world mod**. If the New World
  shows Clay everywhere and its climate, vegetation and topography map modes are empty,
  the game has not read the world's location data; see
  [troubleshooting](generator-guide.md#the-new-world-is-all-clay-or-its-map-modes-are-empty).
  The world's page warns when a mod after the world holds files at the same paths, or when
  another RNW world is ticked.
- **Worlds made by 1.0.0 can block colonial nations.** Their generated seas can touch
  European seas near Greenland, so the Americas no longer count as overseas for European
  countries (fixed in 1.1.0, issue #9). The fix does not change an existing world; make a
  new world with 1.1.0 or later.
- **Worlds made by 1.1.0 or earlier give *Settle the Frontier* to only part of the
  New World.** The game grants it by the region of a country's original capital, and
  these worlds kept the game's list of regions, so about half of their New World
  countries cannot settle the unowned land beside them. Fixed in 1.2.0; the fix does
  not change an existing world.
- **The game's own texts keep the real Americas' names.** The world names regions,
  areas and places after the peoples who live there. The game, though, writes *America*,
  *North America* and *South America* itself: in religion groups, pop diets and the timeline.
  Some of its texts also name real places, for example AI goals such as *Settle Alaska*,
  the history notes of the voyages, and religions such as *Caribbean Folk Religions*. These
  are the game's words for the real Americas, not for the generated land. The generator's
  map card names the base game's region whose rules apply to a place, for example *Counts as
  Alaska in the game's rules*.
- **Worlds made by 1.1.0 or earlier have regions with random names.** Their names come
  from no culture, and the generator's map labels those regions by the base game's names
  (Alaska, Canada) although the game shows the world's own. Fixed in 1.2.0; the fix does not
  change an existing world.
- **Institutions follow vanilla rules.** Feudalism and Legalism can appear only in
  Europe and reach the New World by spreading. The extraordinary-peoples setting gives
  technology and governments, not institutions.
- **Multiplayer needs matching files.** Multiplayer is supported and has been
  tested by the community. All players need the same game version, generated
  world mod and other mods. Sharing a world code alone is not enough if players
  regenerate it with different generator versions or game files.

## Generation and startup

- **Allow about 7.5 GB of free RAM for generation.** On a 16 GB system, close
  EU5 after opening the generator, or launch the generator directly from its
  folder.
- **Some seeds and settings cannot produce a valid world.** Generation stops
  with an error in that case. Use **Generate with a new seed** to retry.
- **A world made by an earlier algorithm gets no versions.** A version keeps the
  world's land, and the same seed gives other land under another algorithm. Since 1.2.0
  **New peoples**, **New resources** and **Same land, change settings** are off for such a
  world (a 1.1.0 world in 1.2.0), with the reason shown; before 1.2.0 these buttons
  made such a version without saying that its land came from the current algorithm. Use
  **New world with these settings** for a new land, or the release that made the world.
- **A world that keeps the real Americas (Omerika, 1.2.0) generates only their peoples.** The
  game's own map, names, resources and ports stay, so the New World is not covered in the lobby,
  there are no exceptional places and no resources to make again, and the Treaty of Tordesillas
  keeps its vanilla line. The foundation of the start is the same as in every world, but its
  behaviour on the real map has not been observed in the game; the stories name places by the
  game's own English words in every language.
- **Windows startup warnings.** The binaries are unsigned, so Smart App Control
  may block them. The 1.1.0 window also received one heuristic antivirus detection;
  the [release notes](releases/1.1.0.md#checksums-and-windows-binary-scans) list
  the exact files and scan results. The generator requires no administrator access.
- **The main window needs WebView2 on Windows or WebKitGTK 4.1 on Linux.**
  Without it, the classic window opens automatically, including in the usual
  Workshop/Proton setup. If the window is blank or draws incorrectly, select
  **Use the classic window** in Settings or launch with `--classic`.
  See [window troubleshooting](generator-guide.md#the-window-is-blank-or-does-not-draw-properly).
  Supported play routes are Windows and Linux/Proton; macOS is not supported.

## Visible map issues

- **A terrain fissure can be visible at the world-wrap seam when zoomed in.**
  This has also been observed in vanilla EU5.
- **Small islands can have a faint pale halo in the surrounding water.**
