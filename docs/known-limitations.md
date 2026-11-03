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
  load order: **Refined Colonization → generated RNW world mod**.
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
