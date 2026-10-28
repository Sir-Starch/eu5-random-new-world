# ADR 0010: Layered worlds, a page of pictures, world files, and a generator that stands on its own

**Status:** Accepted 2026-10-22 with the owner's answers (at the end). Offline implementation through G4 and the G5 artifact workflow is present in 0.9.23 (C143–C146); game acceptance, broader native Windows/macOS validation and remote CI remain separate gates. The first packaged Windows 11 launch/generate/install smoke passed by owner report (C428). See the [generator guide](../generator-guide.md), [log](../research/log.md) and [claims ledger](../research/claims-ledger.md). Builds on [ADR 0009](0009-hub-mod-with-generator.md) (the hub mod and the generator window) and [ADR 0007](0007-application-window-and-packaging.md) (the window).

## Requirements (owner, 2026-10-22)

1. Regenerate only a part of a world (the states, the resources) when the player likes the continent but not the rest.
2. Show several pictures, not only the geography: a version with the countries and whatever else matters when judging a map before playing it.
3. Load by hand a generation made elsewhere, for example by a player who uses the generator outside the game as a program of its own.
4. The generator must work as an independent program, not necessarily installed as a mod through the Workshop.
5. The names of the map mods must be more convenient and shorter.
6. And the quality-of-life that follows from these.

## What exists (read from the code, 0.9.20)

- **One seed drives everything, through named streams.** A world is a preset, a 64-bit seed and changed settings, written as a world code (`rnw.app.worldcode`). Every stage draws from `derive_seed(seed, "<stream>")`; the land (`newworld`, `relief`, `rivers`), the raw materials (`eu5_biomes._raw_materials`, stream `raw_material`) and the peoples (`eu5_natives.build_natives`: societies, cultures, religions, tags, colours, countries and place names) each take the seed as an argument [V-LOCAL: `grep derive_seed`]. No stage after the land reads `raw_material` except the texts that write it [V-LOCAL: grep]. So the parts are separable by giving each its own seed [INFERRED; the acceptance tests below prove it].
- **A world code is append-only.** Format 2 writes a change as the number of its field in `CHANGE_FIELDS` and an unsigned LEB128 value; a number, once given, names its field for good. A code also carries the generator version.
- **One preview.** The export draws the whole map at an eighth of its size (2048 × 1024) with the New World by class (land, wasteland, sea, lake), and the same with it covered (`pictures.py`, `eu5_nw_export._previews`). The library keeps both beside `world.json`, with the cover's files.
- **A world is a mod of its own, and a heavy one:** 1.2 GB on disk, of which 1.1 GB is `in_game/gfx` (terrain decals, vegetation, water); the start state, texts and scripts are about 15 MB, `map_data` 15 MB [V-LOCAL: the owner's profile, 0.9.20]. By the stage weights of `progress.py` (reference seconds, 176 in all) the land's own stages are 112, what is read from the game 42, and what only the peoples and the texts need 22 [V-LOCAL; the weights are timings on the reference machine].
- **Names.** The mod's name in the game's list is built at export: `Random New World: Small continents, seed 7379108625698230220 (NOT GAME VALIDATED)` (`eu5_nw_export`, line 1804), about 80 characters with a 19-digit seed; the window shows `Small continents #73791` (`gui.controller.name`). The player's rename lives only in `world.json`; the game's list never sees it [V-LOCAL].
- **The program already runs without the Workshop:** `rnw gui`, `rnw world CODE [--install]`, discovery of the game and the Proton or Windows profile through Steam's libraries, a data folder of its own, a PyInstaller folder on Linux (C104, C105). What ties it to the hub is the delivery (the Windows layout of ADR 0009) and the texts, not the code.

## Decisions

### A. Layers and rerolls (requirement 1)

Three **layers**, each with its own seed:

| Layer | Holds | Depends on |
|---|---|---|
| **Land** (the code's seed) | shape, relief, climate, rivers, biomes, vegetation, locations, areas, regions and their names in the files | nothing |
| **Resources** | the raw material of every location, gold and silver (`new_world.precious_permille` belongs here) | land |
| **Peoples** | societies, cultures, religions, countries, their tags and colours, place names, the native start state, and the development that follows from them | land |

- **Rolls.** The code gains two counters, `rolls.resources` and `rolls.peoples`, as new fields at the end of `CHANGE_FIELDS` (a roll of 0 is not written). A layer's seed is the code's seed while its roll is 0 and `derive_seed(seed, "roll", layer, roll)` after. Every existing code therefore decodes to the same world [INFERRED; test: the golden digests of today's seeds do not move]. A generator that meets an unknown field says the code comes from a newer generator.
- **What the player sees.** On a world's page, *Change a part*: **New continent** (a new seed, rolls back to 0, as today's new world), **New peoples**, **New resources**. Each makes a **variant**: a world of its own with its own code and mod, whose land files are byte for byte those of the world it came from [acceptance test: equal hashes of `map_data` and `gfx`]. The library groups variants under their land (the land's id is the hash of the seed and the land's settings) and shows them as one continent with its versions. Settings of a part (the *Customize* sliders for the peoples or the resources) are changed on the same page and also make a variant.
- **Disk.** Every variant in the game is another 1.2 GB. The page therefore offers **Replace** (the new variant goes in, the old one comes out, the old one stays in the library as a code) beside **Keep both**; Replace is the default.
- **Speed.** Phase one makes a variant by a full generation (90-150 s) and proves the bytes. Phase two keeps the land's state and what is read from the game per build, so a variant needs about the 22 reference seconds of its own stages plus copying the land's files [INFERRED from the weights]; no result is claimed until measured.
- **Not layers (yet):** names apart from peoples, development apart from peoples, culture apart from states. They can be split later by the same device without touching older codes.

### B. Pictures (requirement 2)

- A new export stage, **pictures**, draws from the data the export already holds, in integer arithmetic (the same bytes on every machine, like today's): **Land** (the present picture, with shaded relief and biome tints), **Countries** (each country in its colour from the mod, borders, capitals), **Cultures**, **Religions**, **Resources** (the raw material of each location, gold and silver marked), **Development** (population and development as a scale). Each is the New World's box at a quarter of the map's size, not the eighth of the whole map, so a province is visible.
- Beside them `atlas.json`: the legend of every picture and one record per location (key, name, owner tag, culture, religion, raw material, development), so the window answers a hover or a click with the name and the facts, and finds a country, a culture or a material by name. It is the same data the world file carries (C).
- The library keeps the pictures and the atlas with `world.json`, so a world that is only a code, or whose mod is out of the game, can still be looked at. The mod list in the game keeps its own picture, covered unless the player's setting says otherwise.
- **Spoilers.** The *Show the New World before you play it* setting (C133) keeps its meaning for the game's mod list and the country-selection cover (C136). For the generator's own pages see open question 2.

### C. World files and generations from elsewhere (requirement 3)

- A **world file** (`.rnworld`, a ZIP with a fixed layout and no code) holds `world.json` (code, name, notes, generator version, game build), the pictures and the atlas. It is small (a few megabytes). Whoever opens it gets the world made again from the code, byte for byte, by the same generator version on the same game build (C120); the pictures are there at once, before anything is generated. Paste a code, drop a file on the window, `rnw import-world FILE`, `rnw export-world`: the same operation.
- **Untrusted input.** A file is data. The reader accepts only the names of the fixed layout, refuses paths that leave the folder, links and any size or count over the limits, and checks the hashes the file lists before it uses a byte. Nothing in a file is run.
- **The world file stays compact (owner, 2026-10-22).** No built mod goes into it, and it never will: it is the thing a player posts, mails or pastes beside a code.
- **Moving a built mod is a function of its own**, not a mode of the world file: *Transfer a built world* writes the mod, with the world file's record, into one archive (`.rnworld-mod`) that the other side installs without generating, for example from a stronger machine to a weaker one. It is 1.2 GB and holds rasters derived from the game's map, which the legal notes keep out of anything shared (C15, [legal](../legal.md)); so it is offered as a transfer between the player's own machines, says so, and the same game build is checked before it installs. Phase G3b.
- **A map from another tool** (a land-and-sea image or a heightmap from a painter or another generator) is a second thing, and a larger one: a land mask enters at the one stage that makes the land (`newworld._land`), is checked against the canvas (size, margins, smallest island, connectivity), and the rest is generated on it. A code cannot reproduce it, so the world's identity includes the mask's hash and the file carries the mask. Phase G4; whether it is wanted is open question 1.

### D. A generator of its own (requirement 4)

**The project is first of all an independent generator** (owner, 2026-10-22). It runs natively from the command line and from its window, on Linux first, then Windows and macOS. A binary is not part of the generator; it is one way to deliver it. The Workshop mod of ADR 0009 is part of the project, not its centre: it packages the generator with a launcher for the players who take it from the Workshop, and for them everything works as it does now. Nobody is obliged to use the generator through an `.exe` in the game's mod manager.

Distribution (owner's table, 2026-10-22); every GitHub release is built from one tagged commit:

| Channel | Format |
|---|---|
| Steam Workshop | the mod with the universal Windows generator, for Windows and Proton |
| GitHub, Windows | the native generator (the layout of ADR 0009, embeddable Python, no PyInstaller there) |
| GitHub, Linux | the native generator; it reads the Proton profile directly, no Windows program involved |
| GitHub, macOS | the native generator, planned; that EU5 runs on macOS, where its profile lies and how an unsigned app passes Gatekeeper are [UNKNOWN] |
| GitHub, source | the sources and a package (`uv tool install`, `pipx`), with no binary required; the reference form, from which every other is built |

The EU5 mod with its program, which the owner named earlier the same day among the repository's releases, is also attached to the release as the Workshop item's file, for players who take it from the repository. The owner's table does not list it; it stays unless struck.

What the program itself needs, whatever the release:

- **A first-run page:** where is EU5? Found by discovery; otherwise a folder chosen by hand and remembered. Which profile. Nothing assumes the program lies in the game's folder or in a Workshop item.
- **Three destinations for a world:** *into the game's profile* (today), *a mod folder* of the player's choice, *a world file only* (no profile needed; the game's files are still read, since the New World is cut from the installed map and cannot be made without it).
- **Viewer mode** on a machine without the game: codes, world files and their pictures open; nothing generates.
- **Portable mode:** a `portable.txt` beside the program keeps the data in its folder.
- **The command line is complete:** everything the window does has a command.
- **No network** stays (ADR 0009): no update check; *Releases* opens the repository's page in the browser.
- The mod prefix `rnw_exp_` remains the development prefix; the product prefix `rnw_world_` comes with the first publication.

### E. Names (requirement 5)

- **In the game's list:** `RNW: <name>`, 30 characters at most [the list's width is UNKNOWN; check in game]. The separator is a plain colon, which the old names already used in game; a middle dot is untested in the game's font [UNKNOWN]. `<name>` is the player's name when there is one (cut to fit), else `<Type> <TAG>` (`RNW: Small continents 7K3Q`). `TAG` is four characters of the world's id, so the same world has the same tag on every machine, and a multiplayer group can say "play 7K3Q". The seed no longer appears in the name (it stays in the details and the code).
- **The status goes to the description.** *NOT GAME VALIDATED* is in the description until 1.0 and is dropped then; a title is not the place for it.
- **Rename reaches the game.** The generator writes the new name into the mod's metadata (a replace of one small file) and says it shows after the next playset reload; if the system refuses while the game holds the file, it says so and keeps the name for the next install.
- **The window shows the name** without the `RNW: ` (the default `<Type> <TAG>`, or the player's), so what the player reads in the generator is what the game lists after the prefix.
- **The tag on the picture (owner, 2026-10-22).** Worlds whose New World is covered all have the same picture in the mod list. On those, the tag is drawn in the middle of the picture in red, large, with a dark outline, in a fixed bitmap font (no font file, so the same bytes everywhere). Where the picture shows the real New World the tag is not drawn: those pictures differ already. Turning the setting *Show the New World* on or off redraws the picture with or without the tag.
- The folder (`rnw_exp_world_<id>`) is not meant to be read and stays.

### G. Reproducibility (owner, 2026-10-22: a seed alone does not give the same world in a year)

What the world's files hold today [V-EXEC: the `report.json` of a 0.9.20 export; `rnw.app.worldcode`, `rnw.app.library`]: the code has the preset, the seed, the changes and the **product version**; the report has the generator, the product version, the RNG's version, the seed, the **fully resolved settings**, the game's fingerprint with the label of its build, and 15 map files with their hashes; the library's `world.json` has the code and the Steam build id. The gaps:

1. The code names a release, not what the release computes: a release that only changes the window looks like another generator, and one that changes the output is told apart only by a notice, after which a different world is made.
2. The code names a preset and its changes, not the settings: if a release retunes a preset, the same code is another world.
3. The inputs are under-recorded. The export reads more than the 15 map files: the setup files, the country, culture, language and holy-site definitions, the templates, the localization keys, the terrain's decals and water files, the scripts it rewrites, and the files it copies for the cover (`grep` of the export). The fingerprint covers the map contract only, so a patch that changes a definition but not the map passes it and still changes the world.
4. The Steam build id keys a world (`world_id`) and changes with every patch, whether or not a file the world read changed: too strict, where the fingerprint is too loose.
5. Nothing checks that a world made again equals the first.

A hash proves a file is whole; it does not make a rebuild a reproduction. So each world carries a **reproducibility record** (in `world.json`, in the bundle, and in the `.rnworld`):

| Field | What it fixes |
|---|---|
| `format` | the version of the record's own layout, so an old record is always readable |
| `algorithm` | the **epoch**: an integer raised whenever the files a world is made of change for the same inputs (one pending epoch per release cycle; frozen epochs never change, per revised ADR 0003). The code carries the epoch, not the release |
| `release` | the product version, and for repository releases the tag and the commit, so the player is told which release makes the original |
| `settings`, `seed`, `rolls` | every resolved value; the preset is only a label, and the epoch fixes what a short code resolves to (the preset tables are part of the algorithm) |
| `game` | the EU5 version and the Steam build id (labels), the mod's `supported_game_version`, and an **inputs manifest**: every game file the export read, with its hash, kept in the bundle and as one digest in the record. The world's id still comes from the Steam build id: changing the scheme would orphan every library made so far. The inputs digest, not the id, says whether a patch touched what a world read (phase G0b: a patch that touched nothing keeps its mod instead of making it again) |
| `output` | a digest of the files that make the map and the start (everything but `.metadata/` and the cover's files, which follow the player's settings), so reproduction can be *checked* |

- **Opening a world** compares the record with the running generator and game and says one of five things, never a silent sixth: *identical* (same epoch, same inputs digest: made again byte for byte); *same algorithm, inputs not compared yet* (what the window says before a check: hashing the game's files takes a second, a rebuild two minutes); *other inputs* (the game changed files the world read, which are listed; what is made is a world of its own, not a reproduction); *other epoch* (names the release that made it; this generator would make a different world from the same code, and says so first); *newer format* (cannot be read). The record, the atlas and the pictures open in every case: they are data.
- **Check reproducibility:** make the world again and compare its output digest with the record, naming the first differing file. It is the check CI already makes on a reference world (C120), offered to the player.
- **Releases stay.** The last release of every epoch stays published and the program links to it. After an EU5 patch that changes inputs not even the old release reproduces a world [INFERRED]; the program says so, and offers to archive a world that matters as a built mod (the transfer function, G3b).
- **Development cycles (ADR 0003, revised 2026-10-28).** Ordinary main commits keep the cycle's product target and may refine its pending epoch/reference. Only frozen releases promise reproduction by version/epoch; development candidates additionally require the exact source commit and inputs.
- **Tests.** Golden digests are keyed by epoch; the digest of a released epoch never changes, and a changed digest without a new epoch fails. A fixture per verdict. The inputs are recorded by the interpreter's audit hook (`rnw.inputs`), which sees every open of every thread, so the list is complete by construction; a game file opened after the record is made is an error.

### H. What needs the game, and what does not (owner, 2026-10-22)

Three kinds of data, kept apart:

- **Ours:** the code, the settings, the record, the atlas (our names, tags, colours, topology, numbers), the pictures of the New World's box, the notes. Free to share and to ship.
- **Keys:** identifiers of game objects (goods, cultures, religions, tags of the Old World). They name things and may stand in the atlas; the viewer shows the game's own text for one if the game is there, else our English name or the key.
- **Derived from the game:** the built mod's rasters, copies of game text and shaders (the cover), the cache of vanilla reads, the canvas cut from the map. **Local only**: never in a public release, never in a `.rnworld` (C15, [legal](../legal.md)).

| Without the game | Only with the game installed (a build the generator knows) |
|---|---|
| Read, check and convert a code | Generate a world (the mod) |
| Open a `.rnworld`: the record, atlas, pictures, legend, hover, search, compare, notes | A new continent, new peoples, new resources (they build on the canvas and on the game's calibration) |
| The reproducibility verdict from the record: the epoch and the release that made it | The comparison of inputs, and *Check reproducibility* |
| Export a picture; `rnw synth` (the synthetic D0 world, for tests and demonstrations) | Install into the profile; transfer a built world; Candidates (G4: the canvas comes from the map) |

Why generation cannot be game-free [V-LOCAL: the reads above; INFERRED for the rest]: the New World replaces the Americas of the installed map, so the canvas, the Old World's locations and keys, the setup and scripts, the localization keys, the terrain's materials and the cover's shaders all come from the installation. Making it independent would mean shipping data derived from the game, which is excluded.

Enforced, not promised:

- **A boundary in the code:** the modules of the viewer and the files (code, record, atlas, `.rnworld`, library) never import the game readers (`eu5_*`); a test imports the viewer with the readers blocked and walks the import graph.
- **A boundary in the releases:** a test lists each release's files against an allowlist of our own sources and wheels, and fails on any path under `game/`, `jomini/` or `clausewitz/`, on any shader or game raster. The cache of vanilla reads lives in the player's data folder and in no release.
- **A boundary in the window:** without the game the program opens in viewer mode and says on *Generate* that it needs EU5 and why.

### F. Quality of life that follows

Per world: a note, a star, a tag of the player's; compare two worlds side by side on any picture; search of a country, a culture or a material across a world; copy the code, the tag, the picture; save a picture (spoiler-safe by default); a history of the rolls with undo; open the folder; a summary line (countries, tribes, empires, gold and silver, land share). Per session: **Candidates**, a contact sheet of several continents rolled from the land stage alone (a sketch is cheaper than a world: no vegetation, no decals), to pick before generating; drag and drop of codes and files; a queue of worlds to generate, one after another. Every operation also exists as a command (`rnw reroll CODE --part peoples`), for scripts and for players without the window.

## Phases (release target per ADR 0003, golden digests, [claims ledger](../research/claims-ledger.md), owner's review)

| Phase | Contents | Gate |
|---|---|---|
| **G0** (built in 0.9.22; Windows not yet checked, C141) | G (the reproducibility record, the epoch, the inputs manifest, the verdicts, *Check reproducibility*) | Every world has the full record; a fixture per verdict; the check passes on the reference world on Linux and Windows; goldens keyed by epoch |
| **G0b** | G (a patch that touched nothing a world read keeps its mod) | The world made for one build is installed on another without being made again when its inputs compare equal |
| **G1a** (built in 0.9.21, offline; the game's rendering of the title and the picture is [UNKNOWN], C140) | E (names, the tag on covered pictures) | The game's name is `RNW: <name>` of at most 30 characters, built from one function the window also uses; rename rewrites the mod's metadata; covered pictures carry the tag and revealed ones do not; the world's files are byte-identical but for `.metadata` |
| **G1b** | D and H (first run, three destinations, viewer and portable modes, a complete command line, the boundaries) | A world can be made with no profile and with no Workshop item anywhere on the machine; the viewer opens a `.rnworld` with no game; the import-graph and release-allowlist tests pass |
| **G5** | D (releases): native Linux and Windows builds, macOS if it can be made to work, the Workshop mod as one release | Each built by CI from a tag; the self-test passes on each |
| **G2** | A (layers, rolls, variants, Replace) | Old codes give old bytes; a variant's land files equal its source's; rolling resources changes only the files that carry raw materials; rolling peoples changes none of the land's and none of the resources' |
| **G3** | B (pictures and atlas) and C (the compact `.rnworld`: import, export) | Pictures are the same bytes on two machines; a hostile file fixture is refused; the atlas agrees with the mod's files (every tag and culture in a picture exists in the mod) |
| **G3b** | C, the separate transfer of a built world (`.rnworld-mod`) | The other side installs it byte for byte without generating; a different game build is refused; the legal note is in the window |
| **G4** | The land mask from another tool; Candidates; the cache for fast variants | Mask checks fail loudly on bad images; a variant takes the time measured, not the time hoped |

## The owner's answers (2026-10-22)

1. *A generation from elsewhere* is (a): a world the same generator made elsewhere, carried as a code or a file. A map from other tools (b) stays phase G4.
2. *Spoilers:* the pictures of the generator's own pages are covered by default; a world is revealed by the player.
3. *The name:* informative (`<Type> <TAG>`), with the tag in red on the covered pictures (E).
4. *Distribution:* the repository publishes the independent generator, natively on Linux, Windows and macOS, with the EU5 mod and its program as one release among them (D).
5. *Workshop:* only the universal Windows and Proton build goes there; native builds are on the repository.
6. *A built mod:* `.rnworld` stays compact; moving a built mod is a separate function (C, G3b).
7. *Reproducibility:* the version of the generator, of the world format, the compatibility with EU5 and all parameters are kept in the world; hashes alone are integrity, not reproducibility (G).
8. *Independence from EU5:* what works without the game is defined strictly, the viewer first; generation needs the game; no game file goes into a public release (H).

## Consequences

The world code stays the only thing a player needs to share a world, and grows by two small numbers. A variant is a world like any other: nothing in the mod, the library or the installer needs to know it is one, except the library's grouping. The pictures make the generator useful before the game is opened, which is also what a viewer without the game needs. The cost is code in the export (a pictures stage, the seeds of the parts) and in the window (a pictures page, the part buttons, a first-run page), and a new kind of file to read as hostile.

## Installed-world recovery (owner request, 2026-10-26)

The owner identified automatic recognition of installed RNW mods as basic library
functionality after a direct export appeared as an “Older world” (C353–C356).
The application now adopts readable world codes in place. A nonstandard mod
folder is a validated local alias; the library keeps its normal id-based folder.
Alias matching checks the code (and a recorded build when available) before
binding a mod in another profile, so a generic folder name cannot remove an
unrelated world. Transfers normalize aliases in their private extracted copy.

New application-generated mods carry `.metadata/rnw-library/`: the public world
record, original input/output manifests, atlas, pictures, optional drawn-land
image and saved selection cover. These are existing locally generated artifacts,
not a second mod or game content repair. Notes, favourites and private user tags
are omitted. Receipt records, settings and bundle hashes are checked in staging;
publication into the library is atomic. A code-only adoption can be upgraded
when a copied receipt finishes arriving, preserving personal fields and its
local id. Complete existing records are not replaced, and unrelated bundle
files are never overwritten by adoption.

For an older code-only mod the original game build and exact output remain
unknown; the current installation is not substituted as historical evidence.
Legacy thumbnails can supply a preview but are not presented as a restored atlas.
Mods lacking readable identification remain visible as unregistered. Polling
small metadata files lets an open window notice external changes while retaining
selection and unsaved notes. No map raster is hashed on the UI thread. The
algorithm epoch stays 41: this feature changes application/library data and
`.metadata` only. The canonical reference world is still the one of 0.13.2.
