# ADR 0009: One Workshop mod that explains, configures and carries the generator

**Status:** Proposed 2026-10-21 (owner's three requirements; the experiments below decide the details). Replaces [ADR 0008](0008-workshop-worlds.md), whose finite pool of worlds does not meet requirement 2.

## Requirements (owner, 2026-10-21)

1. The mod is published on the Steam Workshop.
2. It is the full mod with real generation, not a cut-down one with fixed worlds.
3. It is set up in the game and explained there; ideally the game opens the generation window, or opens the folder where it can be started, or explains how.

## What the engine offers (read from the game files and `eu5.exe`, 1.4.2; no launch needed)

- A mod can add windows to the main menu and to the game: scripted widgets, declared in `gui/scripted_widgets/*.txt` and drawn from the mod's own `.gui` files [V-LOCAL: `main_menu/gui/scripted_widgets/_scripted_widgets.info`]. Where such a widget is shown is not settled [UNKNOWN].
- The game's own mod manager has an **Open in folder** button for every mod, local or Workshop (`LocalMod.OpenInFolder`, `ModsPlaysetEntry.OpenInFolder`, which end in `ShellExecute`) [V-LOCAL: `main_menu/gui/mods_gui/mods_gui.gui`].
- A script effect `debug_log = message` writes a line to the game's log, with a localization string and the scope [V-LOCAL: engine help text in `eu5.exe`]. It is the one channel from a running game to a program beside it.
- There is no way for a mod to run a program or to write files, and no random map in the engine (C83; this session's search of the binary for plugin hooks found none).

## Decision

**The Workshop item is a mod that contains the generator and teaches the player to use it, from inside the game.**

- **In the item:** the data mod (in-game window, game rules where a mod may define them [UNKNOWN: C81], localization of the instructions) and a `generator/` folder with the packaged generator (the PyInstaller folder of ADR 0007, built for Windows; on Linux it runs in the game's Proton prefix, see below). The generator needs no installation.
- **In the game:** a window of the mod (scripted widget) states whether a generated world is present (a localization key that only the generated mod defines), shows its name, seed and generator version, and gives the steps: open the Mods window, press **Open in folder** on Random New World, start the generator, press Generate, switch the playset off and on to reload the mods, start a new game. The visibility modes and the other options the engine applies at the start of a campaign are game rules of the mod [V-LOCAL C81].
- **In the generator window:** the choices that need the map (preset, seed, size of the continents), which the engine can only read from files; the generator finds the game and the profile, lists the generated world as a second, local mod (`rnw_exp_new_world` in the profile's `mod/` folder, never in the Workshop folder, which Steam rewrites) and says what to do back in the game. Where the Workshop item sits is known to it from its own path.
- **Settings in the game that reach the generator:** a button of the in-game window runs a script effect that writes the player's choices as one `debug_log` line; the generator reads the newest such line from the game's log and starts with them filled in [UNKNOWN: needs experiment 016].
- **If the Workshop refuses an executable:** the item keeps the data mod and the instructions, the generator is a release on a code host, and the window says where to get it (text; the engine opens URLs only for DLC links [V-LOCAL]). Nothing else changes.

## Linux

The installation is the Windows build (`binaries/eu5.exe`, no native Linux binary) and runs through Proton. **Open in folder opens Wine's own explorer at the mod's folder** [V-GAME owner, 1.4.2, Proton 11.0 (a community build); experiment 019], so a Linux player stands inside the game's Wine prefix, and the program to start there is the **Windows build** of the generator. One build serves both systems:

- Under the Proton build the game uses, in a prefix made by the `proton` script, the Windows build's window passes its self-test, and started from a Workshop item folder (`S:\steamapps\workshop\content\3450310\<item>`, or the same folder under `Z:\`) it finds the game beside it and the profile in `C:\users\steamuser\Documents` [V-EXEC experiment 019]. The same build writes the same 733 files as the Linux build under Wine, about 50 % slower (2 min 24 s against 1 min 34 s) [V-EXEC]. The game's logs are in the same profile, so the `debug_log` channel is unchanged.
- In the running game, a Windows program placed as `<mod>/generator/probe.exe` without the executable bit starts by double-click from that explorer, shows its window on the desktop, runs in the game's own prefix and sees the profile, Proton's Steam stub list and the game on `S:\`; the game mounts only `main_menu` and `in_game` and logs nothing about the folder [V-GAME owner, experiment 019 part 3]. So whether Steam keeps the executable bit on Workshop files does not matter for this path.
- A program started there inherits the game's affinity mask (16 of 32 processors on the owner's machine), and the generator uses that many threads [V-GAME; `rnw.parallel`].
- A native Linux build (made on Ubuntu 22.04, glibc 2.35; PySide6 needs 2.34) is not needed for the in-game path; whether to ship it as well for players who start the generator from their desktop is a size decision (about 250 MB more) for later.
- Open: the full generator in that place (Qt window, 7.5 GiB beside the running game, time with the inherited threads) [UNKNOWN].

## Experiments before building

- **016 (owner in game):** a test mod with a scripted widget in the main menu and one in the game: does it show, can it print a localization key defined by another mod, and does the mod manager's Open in folder work for it.
- **017 (owner in game):** a `debug_log` line from a button in a campaign: does it reach `debug.log` or `game.log`, with the text.
- **019 (owner, Linux with Proton):** [experiment 019](../../experiments/019-linux-proton-launch/README.md). Done: Wine explorer opens; the Windows build runs there and finds game and profile; a probe in `<mod>/generator/` starts from the running game. Next: the packaged generator in the same place.
- **018 (owner, Steam account):** upload a private test item with a harmless executable and see whether it is accepted and downloads into the Workshop folder. I take no account action.
- **Offline (mine):** the generator finds its own folder, reads the settings line from a log, writes the world mod; the world mod carries the loc key; both are tested without the game.

## Consequences

The generator program is part of the mod, started from the game's mod list; it is no longer an application the player has to find. ADR 0007's window stays as the generator's window (it reads game and profile, shows progress and offers Cancel), now opened from the mod folder, and its text points back to the in-game window. The package size (about 250 MB measured for the Linux build; the Windows build is still to be measured) becomes the size of the Workshop item; a smaller native generator is a later optimisation. The world mod is local and not shared on the Workshop; a player shares a world code instead of files, which also keeps derived vanilla files out of the Workshop (the legal question of ADR 0008 falls away for the Hub; it remains for the generator's use of the player's own installation, which is local).
