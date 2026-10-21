# ADR 0009: One Workshop mod that explains, configures and carries the generator

**Status:** Accepted 2026-10-21. The owner asked for the final scheme with the most convenience for the player, legal and safe, honestly described, and left the decision and the licence to me. Experiments 016, 017, 018 and 020 settle details; each has a fallback that keeps the scheme. Replaces [ADR 0004](0004-generator-application.md) and [ADR 0008](0008-workshop-worlds.md).

## Requirements (owner, 2026-10-21)

1. The mod is published on the Steam Workshop.
2. It is the full mod with real generation, not a cut-down one with fixed worlds.
3. It is set up in the game and explained there; ideally the game opens the generation window, or opens the folder where it can be started, or explains how.
4. The scheme is legal and safe, the description says honestly what EU5 allows and why it is done this way; whether a player trusts the program is the player's choice, but we break no rule.

## What the engine offers (read from the game files and `eu5.exe`, 1.4.2)

- A mod can add windows to the main menu and to the game: scripted widgets, declared in `gui/scripted_widgets/*.txt` and drawn from the mod's own `.gui` files [V-LOCAL: `main_menu/gui/scripted_widgets/_scripted_widgets.info`]. Where such a widget is shown is not settled [UNKNOWN].
- The game's own mod manager has an **Open in folder** button for every mod, local or Workshop (`LocalMod.OpenInFolder`, `ModsPlaysetEntry.OpenInFolder`, which end in `ShellExecute`) [V-LOCAL: `main_menu/gui/mods_gui/mods_gui.gui`]; under Proton it opens Wine's explorer, from which a program in the mod starts [V-GAME C107].
- A script effect `debug_log = message` writes a line to the game's log, with a localization string and the scope [V-LOCAL: engine help text in `eu5.exe`]. It is the one known channel from a running game to a program beside it.
- No confirmed way for a mod to run a program or to write files, and no random map in the engine; script effects change the start state, not terrain, relief, rivers or vegetation (C83). A static search of the binary found no plugin hook; that does not exclude dynamic loading [UNKNOWN].
- Paradox's User Agreement counts "scripts and programs" as user-generated content, to be shared for free and non-commercially; hacks, cheats and malicious programs are forbidden (C109, [legal](../legal.md)).

## Options weighed

| Option | For the player | Rules and safety | Verdict |
|---|---|---|---|
| **Hub mod with the generator inside** | One subscription; the game opens the folder; one double-click; worlds of any seed | A program that reads the game and writes a data mod: UGC by Paradox's wording; no change to the game | **Chosen** |
| Data mod on the Workshop, generator from a code host | A second download outside Steam, by browser | Browser downloads carry the Mark of the Web, so SmartScreen warns | Fallback if 018 refuses the program |
| A pool of generated worlds (ADR 0008) | No program at all | Fails requirement 2; derived vanilla files on the Workshop | Rejected |
| A DLL loaded into the game | Generation "inside" the game | Needs a file in the game folder that the Workshop cannot place; hooks break each patch; looks like a cheat | Rejected (below) |
| Generation by script | Would be ideal | The engine cannot make terrain from script (C83) | Not possible as known |
| Generator in the browser (WebAssembly) | No program to trust | The export peaks at 7.8 GiB, a 32-bit WebAssembly memory holds 4 GiB; the folder API is Chromium-only | Rejected for now; reopen if the generator fits in 4 GiB |
| A separate free Steam app | Installed and updated by Steam, no warnings | Steamworks fee and review, Paradox's consent for a product built on its game, and still outside the game | Rejected |
| World written into the Workshop item's folder | One mod in the playset | Steam owns that folder and replaces it on every item update; the world would vanish | Rejected |
| Generator adds the world to the playset | No tick in the mod list | Writes the game's launcher database, a file of the game that we do not own | Rejected: one tick, once |
| Generator that stays open and answers an in-game Generate button | Everything chosen in the game after one start | The same program, the `debug_log` channel | Phase 2, if 017 passes |

## Decision: the player's way

0. **Subscribe** to Random New World: one Workshop item. It holds the data mod (in-game window, game rules, localization), `Random New World Generator.exe` at the top of the folder and the generator's runtime in `generator/` (about 140 MB unpacked: Python 22, Qt 43, NumPy 46, Pillow 16 MB and the rest [V-EXEC: measured parts of the Windows layout; INFERRED: total after leaving out unused Qt modules]).
1. **In the game**, the player adds Random New World to a playset like any mod. Its window in the main menu (016) says whether a generated world is present (a localization key only the world mod defines) with its world code, preset, seed and generator version, and gives the steps below; the Workshop description repeats them ([draft](../workshop-description.md)). The options the engine applies when a campaign starts (visibility, exploration and the like) are game rules of the mod, set in the game (C81, U1).
2. **Mods → Open in folder** on Random New World, double-click the generator. On Windows Explorer opens; on Linux and the Steam Deck Wine's explorer opens inside the game's prefix, and the same Windows program runs there (C106, C107).
3. **The generator window** finds the game and the profile by itself; the player picks a preset and a seed or pastes a world code and presses Generate (94 s on 32 threads natively, 2 min 24 s under Wine; with progress per stage and Cancel). It installs the world as a second, local mod, **Random New World: generated world** (`mod/rnw_world`), replacing the previous world in place, and writes nowhere else but its own data folder.
4. **Back in the game:** the first time only, tick the generated world in the playset; each time, apply the playset again (the game reloads the mods without a restart, C82, C93) and start a new game.
5. **Saves and sharing:** the world code reproduces a world byte for byte (733 equal files across thread counts, memory budgets and the Windows build under Wine [V-EXEC]), so the generator's history and the in-game window keep the code, and an old campaign's world comes back in two minutes. Players of one multiplayer game use one code and one game version [INFERRED: equality on a second CPU model is still to be shown].
6. **Game patches:** Steam updates the item; the generator refuses a game build it does not know, says so, and once updated offers to rebuild the current world for the new build (validators fail loudly).
7. **Phase 2 (if 017 passes):** the generator, once started, keeps watching the log; the in-game window's Generate button writes the choices as a `debug_log` line, the generator makes the world and the window says when to apply the playset.

Known limits the description states: new campaigns only; if a campaign without the mod ran in the same session, restart the game before playing the generated world (C97, C98); about 7.5 GiB of free memory during the two minutes of generation.

## Linux

The installation is the Windows build (`binaries/eu5.exe`, no native Linux binary) and runs through Proton. **Open in folder opens Wine's own explorer at the mod's folder** [V-GAME owner, 1.4.2, Proton 11.0 (a community build); experiment 019], so a Linux player stands inside the game's Wine prefix, and the program to start there is the **Windows build** of the generator. One build serves both systems:

- Under the Proton build the game uses, in a prefix made by the `proton` script, the Windows build's window passes its self-test, and started from a Workshop item folder (`S:\steamapps\workshop\content\3450310\<item>`, or the same folder under `Z:\`) it finds the game beside it and the profile in `C:\users\steamuser\Documents` [V-EXEC experiment 019]. The same build writes the same 733 files as the Linux build under Wine, about 50 % slower (2 min 24 s against 1 min 34 s) [V-EXEC]. The game's logs are in the same profile, so the `debug_log` channel is unchanged.
- In the running game, a Windows program placed as `<mod>/generator/probe.exe` without the executable bit starts by double-click from that explorer, shows its window on the desktop, runs in the game's own prefix and sees the profile, Proton's Steam stub list and the game on `S:\`; the game mounts only `main_menu` and `in_game` and logs nothing about the folder [V-GAME owner, experiment 019 part 3]. So whether Steam keeps the executable bit on Workshop files does not matter for this path.
- A program started there inherits the game's affinity mask (16 of 32 processors on the owner's machine), and the generator uses that many threads [V-GAME; `rnw.parallel`].
- A native Linux build is not needed for the in-game path. The Steam Deck runs the same Proton path [INFERRED; not tried].
- Open: the full generator in that place (Qt window, 7.5 GiB beside the running game, time with the inherited threads) [UNKNOWN].

## Trust on Windows

A program in a Workshop item meets three Windows checks, each with its own trigger:

- **SmartScreen** ("Windows protected your PC") looks only at files that carry the Mark of the Web, which browsers and some other downloaders write; the Steam client is reported not to write it for the games it installs [SOURCE: Lawrence 2024; AssetHoard; nothing from Valve, and nothing about Workshop items]. Expected: no prompt for the generator from the Workshop [INFERRED; check with `dir /r` in experiment 020].
- **Antivirus heuristics** (Defender and others) flag PyInstaller programs often, because the stock bootloader is shared with malware; PyInstaller's own documentation names a self-built bootloader as a way out [SOURCE: PyInstaller 6.22.2 docs].
- **Smart App Control** (Windows 11, on by default in most cases) checks every program, not only downloaded ones: what its cloud service cannot vouch for must carry a valid signature, or it is blocked, with no per-app exception [SOURCE: Microsoft support]. An unsigned program of ours with no history is blocked there [INFERRED].

Hence:

- **No PyInstaller on Windows.** The package is the official embeddable Python, the wheels as they come from PyPI and our code. That is the layout already tested under Wine and Proton (733 files, self-test, discovery: C106, C107). Python itself is signed by the Python Software Foundation and every Qt file by The Qt Company; NumPy, OpenBLAS and Pillow are unsigned but are the files millions of installations carry [V-EXEC: certificate subjects read from the PE files, chains not verified]. Our own binaries are two: the small launcher (`Random New World Generator.exe`, of the kind of experiment 019's probe, which starts `generator\pythonw.exe -m rnw.gui` and says plainly what is wrong if it cannot) and `_native.pyd`.
- **Those two are signed** once a signing route is open. The free one for open-source projects is the SignPath Foundation (an OSI licence, which [MPL-2.0](../legal.md) is; the owner's own repository with MFA; signing in CI with manual approval per release; the certificate in SignPath Foundation's name; a released project with some reputation); the paid one is Azure Artifact Signing [SOURCE: signpath.org/terms]. Until then the description says that Smart App Control blocks the generator. Applying and the accounts are the owner's; I take no account action.
- **Behaviour that can be read from the code and is enforced by tests:** no network modules in the package, no administrator rights (`asInvoker`), writes only to the profile's `mod/rnw_*` folders and the generator's data folder (already enforced by `rnw.app.install`), no registry writes, nothing unpacked to temporary folders, no change to the game's files.
- **Each release:** built only by CI from a tagged commit, SHA-256 of every file published beside the source, a VirusTotal scan and false-positive reports to the vendors before it goes to the Workshop (the owner's actions: uploading a file to a scanner shares it).

## Alternative rejected: a DLL mod with generation inside the game

The owner asked (2026-10-21) whether a DLL mod is allowed and would give real built-in generation.

- **Rules.** Paradox's User Agreement (updated 2026-01-21) counts "scripts and programs" as UGC that may be made and shared for free and non-commercially, and its conduct rules forbid cheats, hacks, malicious programs and "hacked data files"; neither names DLLs, code mods or reverse engineering [SOURCE]. A DLL that hooks the engine is a hack in the plain sense of the word, so the rules give it no cover; a separate program that only reads the game and writes a data mod is not [INFERRED].
- **Engine.** EU5 has no confirmed official code-mod interface. Static analysis found no path that loads a library from a mod: the import table lists only system, graphics, Paradox and Steam libraries, and the `LoadLibrary` strings name only NGX/DLSS, Wwise and system files [V-LOCAL C83, C109]. Imports and strings do not exclude a library loaded by a computed path or through `PDXSDK.dll` [UNKNOWN]; a session traced with `WINEDEBUG=+loaddll` while a mod holds a DLL would show what is loaded at run time. An undocumented loading path, if one exists, would be engine internals all the same. The known ways to bring code into the process are a proxy DLL beside `eu5.exe` (it imports `VERSION.dll` and `WINMM.dll`, the usual targets) or an injector, as Anvil does for EU4 with a `version.dll` that the player copies into the game folder by hand or with a separate manager program [SOURCE: Anvil README]. Workshop items land in `workshop/content/3450310/`, so the Workshop cannot deliver such a loader; under Proton the player would also set `WINEDLLOVERRIDES` in the launch options [INFERRED: Wine prefers its built-in `version.dll`].
- **What it would buy.** The map is still read from files when the mods load (C83), so a DLL would run the same generator inside the game and write the same files; skipping the playset reload or drawing its own window means hooking engine functions found by reverse engineering, which every patch moves (1.4.1 to 1.4.2 took a week, C84).
- **Cost.** A manual step into the game folder, which the Workshop-only requirement excludes; a crash for every player after each patch until the hooks are fixed; the worst antivirus profile (an unsigned DLL loaded into a game is how cheats and malware work, and Smart App Control would block it [INFERRED]); the product rule against patching the engine.

If Paradox ever publishes a code-mod interface for EU5, as Cities: Skylines II has, this is reopened.

## Gates and fallbacks

- **016 (owner in game):** a test mod with a scripted widget in the main menu and one in the game: does it show, can it print a localization key defined by another mod. Fallback: the steps live in the Workshop description and in the descriptions of the mod's game rules, which the game shows on its rules screen [INFERRED].
- **017 (owner in game):** a `debug_log` line from a button: does it reach `debug.log` or `game.log` with the text, and how soon. Fallback: no phase 2; all map choices stay in the generator window.
- **018 (owner, Steam account):** upload a private test item with a harmless executable at the top of the folder and in `generator/`: is it accepted, does it download, does the game log anything about a file at the top. Fallback: the generator moves into `generator/` only (019 showed the game ignores that folder), or, if the Workshop refuses programs, the generator comes from a code host and the description says so. I take no account action.
- **019 (owner, Linux with Proton):** [done](../../experiments/019-linux-proton-launch/README.md).
- **021 (owner, Linux):** [the hub's generator from the game](../../experiments/021-hub-generator-in-game/README.md): `packaging/hub.py` builds the hub; offline under Proton its launcher passes the self-test and its Python generates the 733 reference files (C111).
- **020 (owner or a tester, Windows 11 with Defender's defaults and Smart App Control on):** does the launcher start, do Workshop files carry the Mark of the Web (`dir /r`), what Defender says; then again once the two binaries are signed.
- **Offline (mine):** the Windows layout builder and the launcher (done, C111), the hub mod's in-game files, the world mod's status keys and the product name `rnw_world` (development builds keep `rnw_exp_*`), tested without the game.

## Consequences

The generator is part of the mod, started from the game's mod list; the player never has to find a program. ADR 0007's window is the generator's window; its PyInstaller package stays for development on Linux, the Windows delivery is the embeddable layout. The world mod is local and never on the Workshop; players share world codes, which keeps derived vanilla files off the Workshop. Code and mod files are under MPL-2.0 ([legal](../legal.md)).
