# ADR 0009: One Workshop mod that explains, configures and carries the generator

> Historical delivery investigation, consolidated into the current ADR 0009
> on 2026-10-29. Original alternatives and experiments are retained below;
> they are not a new release checklist.

**Status:** Accepted 2026-10-21. The owner asked for the final scheme with the most convenience for the player, legal and safe, honestly described, and left the decision and the licence to me. Experiments 016, 017, 018 and 020 settle details; each has a fallback that keeps the scheme. Replaces [ADR 0004](../adr/0004-generator-application.md) and [ADR 0008](../adr/0008-workshop-worlds.md).

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

The Workshop item is a **generator of map mods**, not a mod to play with (owner, 2026-10-21): every world it makes is a complete, independent mod of the New World, which the player plays on its own, keeps, deletes, or shares (as their own Workshop map, for example, under Paradox's rules for mods). The generator's own item is never enabled in a playset; it is only opened.

0. **Subscribe** to Random New World: one Workshop item. It holds `Random New World Generator.exe` at the top of its folder and the generator's runtime in `generator/` (147 MiB, C111), the avatar as its picture, and the explanation in its description and metadata. It needs no place in a playset.
1. **Mods → Open in folder** on Random New World, double-click the generator. On Windows Explorer opens; on Linux and the Steam Deck Wine's explorer opens inside the game's prefix, and the same Windows program runs there (C106, C107).
2. **The generator window** finds the game and the profile by itself. On the left, the worlds made before, each with its covered picture, date and place (in the game, beside the generator, or code only); on the right, the page of the one selected.
   - *New world:* a world type (supercontinent, continents, small continents, archipelago, scattered islands: C116), a seed or a pasted code, five *World basics* in a word each (land, native peoples, native states, great empires, gold and silver: C126), and, folded away, *Customize*: twenty-one settings of land, map and peoples, among them gold and silver, lone states and great empires, each a slider within a playable range (C118). The estimated number of locations is shown; Generate refuses a world above the engine's budget. Generate makes the world (90-150 s) with progress and Cancel, and adds it to the game as a **new mod of its own** (`mod/rnw_exp_world_<id>`, named in the game "RNW: <type> <tag>", [ADR 0010](../adr/0010-layered-worlds-and-a-generator-of-its-own.md)); no world is ever replaced by another, except the same code on the same game build, which is the same world.
   - *A world:* its name (the player may rename it), its picture with zoom and pan, **covered as terra incognita unless the player's setting shows the New World**, its code, type, seed, changed settings, date, game build and place, what to do in EU5 now, and Add to the game / Remove from the game, Open folder, New world with these settings, Delete world (asked first). A world out of the game is its code and pictures; adding it again makes it again from the code, byte for byte.
   - *Settings:* game and profile, and one box, *Show the New World before you play it* (off by default), that decides the generator's pictures, the pictures in the game's mod list and the cover at country selection (C133).
3. **Back in the game:** if no game was started since EU5 was launched, tick the new world (and untick any other world) or switch playsets, which reloads the mods, and start a new game; no restart is needed (C115). After a game in this session, restart EU5 first (C97, C113, C114). The generator reads the game's log and playsets and says which applies, naming the world to tick and the others to untick. The installer moves an old world aside instead of deleting a file the game holds, and waits with an instruction where the system refuses even that (C112).
4. **Saves and sharing:** a world code reproduces a world byte for byte, on Linux and Windows alike (735 of 735 files, C120); codes with changed settings stay short (format 2, a few bytes a change). Players of one multiplayer game use one code and one game version.
5. **Game patches:** Steam updates the item; the generator refuses a game build it does not know and, once updated, makes worlds for the new build (a world is named by its code and build).
6. **In-game options:** what the engine applies when a campaign starts (visibility, exploration) can be game rules of a world mod (C81, U1); an in-game window of the generator item is not needed, since that item is never enabled (016 becomes optional). The cover of the New World at country selection could not be one: EU5 1.4.2 refuses `defines` in a rule and a rule's flag reaches no shader (C132). It is the generator's setting *Show the New World before you play it* (0.9.17, C133; off by default), which also decides the generator's pictures and the mod-list picture: off, every world's mod covers the New World and the ocean wastelands around it on the map of the country-selection screen with the look of the game's terra incognita, in the four layers drawn there (terrain, water, borders, names), and leaves *Select* out of its countries' context menu (C136; the lobby's country list ignores mod filters, C134); a change applies to every world at once and the game reads it at its next start. Achievements are left to the game's own verdict (C130).

Known limits the description states: new campaigns only; restart EU5 before a different world after a campaign in the same session; one world ticked at a time; about 7.5 GiB of free memory during generation.

## Linux

The installation is the Windows build (`binaries/eu5.exe`, no native Linux binary) and runs through Proton. **Open in folder opens Wine's own explorer at the mod's folder** [V-GAME owner, 1.4.2, Proton 11.0 (a community build); experiment 019], so a Linux player stands inside the game's Wine prefix, and the program to start there is the **Windows build** of the generator. One build serves both systems:

- Under the Proton build the game uses, in a prefix made by the `proton` script, the Windows build's window passes its self-test, and started from a Workshop item folder (`S:\steamapps\workshop\content\3450310\<item>`, or the same folder under `Z:\`) it finds the game beside it and the profile in `C:\users\steamuser\Documents` [V-EXEC experiment 019]. The same build writes the same 733 files as the Linux build under Wine, about 50 % slower (2 min 24 s against 1 min 34 s) [V-EXEC]. The game's logs are in the same profile, so the `debug_log` channel is unchanged.
- In the running game, a Windows program placed as `<mod>/generator/probe.exe` without the executable bit starts by double-click from that explorer, shows its window on the desktop, runs in the game's own prefix and sees the profile, Proton's Steam stub list and the game on `S:\`; the game mounts only `main_menu` and `in_game` and logs nothing about the folder [V-GAME owner, experiment 019 part 3]. So whether Steam keeps the executable bit on Workshop files does not matter for this path.
- A program started there inherits the game's affinity mask (16 of 32 processors on the owner's machine) [V-GAME C107]; the generator reads it with `GetProcessAffinityMask` and uses that many processors (until experiment 021 it read no mask on Windows and took all 32) [V-EXEC C112].
- The running game holds files of the installed world open, and Windows rules (Wine's too) forbid deleting them; the installer therefore retires the old world into `mod/.rnw-install` by one rename and deletes it when the game lets go, and if the system refuses even the rename, it waits and tells the player to untick the world or close the game [V-GAME C112; V-EXEC].
- A native Linux build is not needed for the in-game path. The Steam Deck runs the same Proton path [INFERRED; not tried].
- Open: the full generator in that place (Qt window, 7.5 GiB beside the running game, time with the inherited threads) [UNKNOWN].

## Trust on Windows

### Owner-run smoke — C428 (2026-10-28)

[V-GAME owner] The packaged 0.13.22 generator launched from EU5's **Open in folder**
path on Windows 11 via Steam, generated a world and installed it as a world mod.
The owner reported no antivirus or other warning pop-ups, and that the generator
opened immediately. The antivirus product and Windows security settings were not
recorded. The exact EU5 build was not captured. The run did not identify the
SmartScreen/Mark-of-the-Web or Smart App Control state, and it was not an observed
Workshop download.

A program in a Workshop item meets three Windows checks, each with its own trigger:

- **SmartScreen** ("Windows protected your PC") looks only at files that carry the Mark of the Web, which browsers and some other downloaders write; the Steam client is reported not to write it for the games it installs [SOURCE: Lawrence 2024; AssetHoard; nothing from Valve, and nothing about Workshop items]. Expected: no prompt for the generator from the Workshop [INFERRED; check with `dir /r` in experiment 020].
- **Antivirus heuristics** (Defender and others) flag PyInstaller programs often, because the stock bootloader is shared with malware; PyInstaller's own documentation names a self-built bootloader as a way out [SOURCE: PyInstaller 6.22.2 docs].
- **Smart App Control** (Windows 11, on by default in most cases) checks every program, not only downloaded ones: what its cloud service cannot vouch for must carry a valid signature, or it is blocked, with no per-app exception [SOURCE: Microsoft support]. An unsigned program of ours with no history is blocked there [INFERRED].

Hence:

- **No PyInstaller on Windows.** The package is the official embeddable Python, the wheels as they come from PyPI and our code. That is the layout already tested under Wine and Proton (733 files, self-test, discovery: C106, C107). Python itself is signed by the Python Software Foundation and every Qt file by The Qt Company; NumPy, OpenBLAS and Pillow are unsigned but are the files millions of installations carry [V-EXEC: certificate subjects read from the PE files, chains not verified]. Our own binaries are two: the small launcher (`Random New World Generator.exe`, of the kind of experiment 019's probe, which starts `generator\pythonw.exe -m rnw.gui` and says plainly what is wrong if it cannot) and `_native.pyd`.
- **Those two are signed** once a signing route is open. The free one for open-source projects is the SignPath Foundation (an OSI licence, which [MPL-2.0](../legal.md) is; the owner's own repository with MFA; signing in CI with manual approval per release; the certificate in SignPath Foundation's name; a released project with some reputation); the paid one is Azure Artifact Signing [SOURCE: signpath.org/terms]. Unsigned delivery is accepted for 1.0.0 (owner, 2026-10-29, C437); the description discloses that Smart App Control may block it. Signing is a future improvement, not an outstanding release gate. Applying and the accounts are the owner's; I take no account action.
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

- **016 (optional since the generator item is never enabled):** a scripted widget in the main menu or the game, for a world mod that wants to show its code in game.
- **017 (owner in game):** a `debug_log` line from a button: does it reach `debug.log` or `game.log` with the text, and how soon. Fallback: no phase 2; all map choices stay in the generator window.
- **018 (owner, Steam account):** upload a private test item with a harmless executable at the top of the folder and in `generator/`: is it accepted, does it download, does the game log anything about a file at the top. Fallback: the generator moves into `generator/` only (019 showed the game ignores that folder), or, if the Workshop refuses programs, the generator comes from a code host and the description says so. I take no account action.
- **019 (owner, Linux with Proton):** [done](../../experiments/019-linux-proton-launch/README.md).
- **021 (owner, Linux):** [the hub's generator from the game](../../experiments/021-hub-generator-in-game/README.md): `packaging/hub.py` builds the hub; offline under Proton its launcher passes the self-test and its Python generates the 733 reference files (C111).
- **020 (partial, C428):** the owner confirmed the current generator launches and runs on Windows 11, with no antivirus warning reported. Still unknown: Defender identity/settings, Mark of the Web on Workshop files, SmartScreen and Smart App Control state, and behavior after signing. Workshop delivery itself remains untested.
- **Offline (mine):** the Windows layout builder and the launcher (done, C111), the hub mod's in-game files, the world mod's status keys and the product name `rnw_world` (development builds keep `rnw_exp_*`), tested without the game.

## Consequences

The generator is part of the mod, started from the game's mod list; the player never has to find a program. ADR 0007's window is the generator's window; its PyInstaller package stays for development on Linux, the Windows delivery is the embeddable layout. The world mod is local and never on the Workshop; players share world codes, which keeps derived vanilla files off the Workshop. Code and mod files are under MPL-2.0 ([legal](../legal.md)).
