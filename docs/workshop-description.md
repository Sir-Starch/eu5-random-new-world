# Workshop description (draft)

Draft of the Steam Workshop text for release 1.0.0 ([ADR 0009](adr/0009-hub-mod-with-generator.md)). It is converted to Steam's markup when the item is published. Every statement must hold for the published build; the bracketed notes are for us and are removed. Steam takes one description per language: the translations are in [workshop/](workshop/), each recording the fingerprint of the English text below the line it was made from (`tests/test_workshop.py` fails on a missing or outdated one).

---

## Random New World

A generator of New Worlds for Europa Universalis V. It makes the Americas anew: continents, coasts, relief, climate, rivers, vegetation, resources, provinces and native peoples, and keeps the Old World as Paradox made it. **Every world it makes is a complete map mod of its own.** Play it on its own, keep as many as you like, delete them, or share a world's code: the world plays without this generator, and anyone with the same game version makes the same world from its code.

You do not enable this item in a playset. It only carries the generator.

## Why there is a program in this item

EU5 builds its map from files when it loads the mods. A mod is data: it cannot run code, and the game's script can change who owns what at the start, but it cannot make land, mountains or rivers. EU5 has no official way to add code to the game.

So the generation runs in a small program that comes with this item. It reads your EU5 installation, generates a world and saves it as an ordinary mod. It does not change the game, attach to it or run inside it. Paradox's user agreement counts programs among the content players may make and share for free.

## How to use it

1. In the **Mods** window press **Open in folder** on Random New World and double-click **Random New World Generator**.
2. Choose a world type: Supercontinent, Continents, Small continents, Archipelago or Scattered islands. Keep the random seed or type one, or paste a world code. **World basics** answer the common questions in a word, as EU4's random New World did: how much land, how many native peoples and states, how often a great native empire rises (never, seldom, sometimes, often), and how rich the gold and silver. Under **Customize** you can change every value: land, coasts, map scale and the native peoples, from great empires to lone states; every value offered still makes a playable world.
3. Press **Generate**. In two or three minutes the world is a new mod in your mod list, named "RNW: <type> <tag>" (for example "RNW: Small continents 7K3Q"); you can rename it in the generator. While the New World is hidden, its picture in the mod list carries the same tag in red, so worlds can be told apart.
4. In the game, tick that world (only one world at a time) and start a new game. If you already played a campaign since starting EU5, restart EU5 first. The generator tells you exactly what to do.

The generator keeps every world you made, with its code. Until you choose to see it in Settings, the New World stays terra incognita everywhere before you play: in the generator's pictures, in the game's mod list, and on the map of the game's new-game screen. One setting turns all of that off. A world code recreates the same world, byte for byte, on any computer with the same game version.

The generator speaks every language of the game and starts in the one Steam runs EU5 in.

## What the program does and does not do

- It reads your EU5 installation and writes only two places: the world mods it makes (`mod/rnw_world_…` in your EU5 documents folder) and its own data folder.
- It does not use the network, does not need administrator rights, does not touch the registry and does not change any game file.
- Its source code is public under the Mozilla Public License 2.0: https://github.com/Sir-Starch/eu5-random-new-world. Every release is built from a tagged commit by an automatic build, and the SHA-256 checksum of every file is published there.
- Whether you trust a program is your decision. You can read the code, compare the checksums, or build it yourself.

## Windows warnings

- Files that Steam downloads are not marked as coming from the internet, so Windows SmartScreen is not expected to ask. [Confirm in 020.]
- Antivirus programs sometimes flag new programs they have not seen before. The release page links a VirusTotal scan of every release.
- Windows 11 Smart App Control blocks programs without a known signature, and Windows offers no exception for single programs. [Until signed:] The generator is not signed yet, so with Smart App Control on it will not start. [Once signed:] The generator and its native module are signed by [signer].

## Linux and Steam Deck

The game runs through Proton. Open in folder then opens Wine's file explorer, and the same generator runs there inside the game's own Proton prefix. You do not need to install anything. [Steam Deck: confirm.]

## Limits

- **New campaigns only.** A world must be generated before the campaign starts.
- **Generate before you play, or restart.** EU5 crashes when a different world starts after a campaign in the same session (the crash is in the game engine). Generating right after starting EU5 needs no restart; after a campaign, restart EU5 before the new world.
- **Game updates.** After an EU5 update, the generator may refuse to run until it is updated for the new build. It then offers to rebuild your world. Older saves need the world they were played on: generate their code again.
- **One world at a time.** Tick only one generated world in a playset.
- **Multiplayer.** Every player uses the same world code with the same game version.
- **Memory.** About 7.5 GB of free memory for the two minutes of generation. EU5's recommended 32 GB is plenty.
- **Achievements.** Like other mods that change the game, it changes the game's checksum. [Confirm what EU5 allows.]

## Removing it

Delete worlds in the generator (**Delete world**) or remove their folders yourself, then unsubscribe. Worlds you keep stay playable without the generator.

## Licence and credits

Code and mod files: Mozilla Public License 2.0. The generated worlds are made on your computer from your copy of EU5 and are not shared through the Workshop. Europa Universalis V is a trademark of Paradox Interactive; this mod is not affiliated with Paradox Interactive.
