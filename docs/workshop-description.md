# Workshop description (draft)

Draft of the Steam Workshop text for release 1.0.0 ([ADR 0009](adr/0009-hub-mod-with-generator.md)). It is converted to Steam's markup when the item is published. Every statement must hold for the published build; the bracketed notes are for us and are removed.

---

## Random New World

A new Americas every campaign. Random New World replaces the New World of EU5 with generated continents, coasts, relief, climate, rivers, vegetation, provinces and native societies, and keeps the Old World as Paradox made it. Any seed gives a different world; the same world code gives the same world on every computer.

## Why there is a program in this mod

EU5 builds its map from files when it loads the mods. A mod is data: it cannot run code, and the game's script can change who owns what at the start, but it cannot make land, mountains or rivers. EU5 has no official way to add code to the game.

So the generation runs in a small program that comes with this mod. It reads your EU5 installation, generates the world and saves it as an ordinary local mod. It does not change the game, attach to it or run inside it. Paradox's user agreement counts programs among the content players may make and share for free.

## How to use it

1. Add **Random New World** to a playset. Its window in the main menu shows whether you have a world and repeats these steps. [Fallback if 016 fails: the rules screen.]
2. In the **Mods** window press **Open in folder** on Random New World and double-click **Random New World Generator**.
3. Choose a preset and a seed, or paste a world code, and press **Generate**. It takes two to three minutes.
4. Back in the game: the first time, add **Random New World: generated world** to the playset. Then restart EU5 and start a new game. [Until C113 is understood: a new game after reloading the mods in a running EU5 can crash.]

Your world code is shown in the game and in the generator. Keep it with your saves: the same code recreates the same world after a reinstall or on a friend's computer.

## What the program does and does not do

- It reads your EU5 installation and writes only two places: the generated world mod (`mod/rnw_world` in your EU5 documents folder) and its own data folder.
- It does not use the network, does not need administrator rights, does not touch the registry and does not change any game file.
- Its source code is public under the Mozilla Public License 2.0: [repository link]. Every release is built from a tagged commit by an automatic build, and the SHA-256 checksum of every file is published there.
- Whether you trust a program is your decision. You can read the code, compare the checksums, or build it yourself.

## Windows warnings

- Files that Steam downloads are not marked as coming from the internet, so Windows SmartScreen is not expected to ask. [Confirm in 020.]
- Antivirus programs sometimes flag new programs they have not seen before. The release page links a VirusTotal scan of every release.
- Windows 11 Smart App Control blocks programs without a known signature, and Windows offers no exception for single programs. [Until signed:] The generator is not signed yet, so with Smart App Control on it will not start. [Once signed:] The generator and its native module are signed by [signer].

## Linux and Steam Deck

The game runs through Proton. Open in folder then opens Wine's file explorer, and the same generator runs there inside the game's own Proton prefix. You do not need to install anything. [Steam Deck: confirm.]

## Limits

- **New campaigns only.** A world must be generated before the campaign starts.
- **Restart after generating.** Start EU5 again before the new campaign. Loading a different world into a running game can crash it (the crash is in the game engine; it happens after the mods are reloaded, not on a fresh start).
- **Game updates.** After an EU5 update, the generator may refuse to run until it is updated for the new build. It then offers to rebuild your world. Older saves need the world they were played on: generate their code again.
- **Multiplayer.** Every player uses the same world code with the same game version. [Confirm on a second computer.]
- **Memory.** About 7.5 GB of free memory for the two minutes of generation. EU5's recommended 32 GB is plenty.
- **Achievements.** Like other mods that change the game, it changes the game's checksum. [Confirm what EU5 allows.]

## Removing it

Unsubscribe, and delete the world in the generator (**Remove world**) or delete `mod/rnw_world` yourself.

## Licence and credits

Code and mod files: Mozilla Public License 2.0. The generated worlds are made on your computer from your copy of EU5 and are not shared through the Workshop. Europa Universalis V is a trademark of Paradox Interactive; this mod is not affiliated with Paradox Interactive.
