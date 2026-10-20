# ADR 0004: Deliver the generator as a local application with a window

**Status:** Accepted 2026-10-20 (owner decision).

## Context

The owner requires that a player sets up and generates the New World without a terminal or scripts, reuses seeds comfortably, restarts the game only if that cannot be avoided, and never sees the game look frozen (2026-10-20).

EU5 1.4.1 cannot compute a seed's geography itself [V-LOCAL/V-EXEC C83]. The executable has no random-map generator; its `CMapGenerator` builds the province map from the locations PNG. Mods are mounted as data folders, and no way for a mod to run its own code was found [INFERRED]. Script effects change the start state (countries, owners, pops, cultures, religions, ranks), but none changes land, sea, relief or climate. The game does switch playsets while it runs and mounts every enabled mod's `in_game` folder at each new game [V-GAME C82; V-LOCAL C83].

## Options

1. **Pool of pre-generated worlds**, chosen in the game's mod menu. Everything happens in the game, but there are finitely many worlds (about 1.3 GB each), and rasters derived from vanilla would be published.
2. **Pool plus societies rerolled by script** at every start. More variety, but it is a large rewrite of R6/R7 with untested speed and quality.
3. **Local application with a window** (chosen). Any seed, generated from the player's own installation.
4. **Native code in the game process.** Rejected: it breaks vanilla first and Workshop distribution.

## Decision

- RNW ships as a desktop application with a window for Windows and Linux. The player installs no Python and never uses a terminal.
- The application finds the game installation and profile and offers presets, settings and a seed: random by default, with copy, paste, history and reuse. It shows a preview, generates with visible progress per stage and a cancel button, validates the result and installs it in place as one local mod folder.
- The game takes the new world up without being closed: the player starts a new game from the main menu (C82). If experiment 013 shows that a mod rewritten on disk is not re-read, the application asks for one game restart and says so beforehand.
- Options that the engine can apply at game start, such as the visibility mode, are game rules of the mod and are set in the game's own setup screen [V-LOCAL C81]. The application computes only what the game cannot.
- Generated output stays on the player's machine; nothing derived from vanilla files is uploaded ([legal](../legal.md)).

## Consequences

- R9 packages the application with its own runtime; the GUI technology is chosen there from evidence, while [ADR 0002](0002-d0-generator-stack.md) stays for the generator core. The core must report progress by stage.
- R10 must make a full generation short enough to wait for in a window (about 11 minutes today).
- U1 has two parts: the application (setup, seed QoL, preview, progress) and the in-game part (game rules, visibility modes, the seed shown in game).
- P1: releases of the application go to a code host. Whether a Steam Workshop item carries anything, and what, is open, because delivering executables through the Workshop was not investigated [UNKNOWN].
- Option 1 stays the fallback if the application cannot be delivered.
