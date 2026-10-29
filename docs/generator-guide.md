# Using the generator

RNW 1.0.0 targets EU5 1.4.5 / Steam build 26211608.

Run from source with `uv sync --locked --group dev` and `uv run rnw gui`.
The Linux folder package runs with `./RandomNewWorld`; its command line is
`./RandomNewWorld --cli --help`. The Windows folder has the launcher and `rnw.cmd`.
The Workshop layout uses the same Windows runtime, also usable through Proton.
The generator needs no Workshop installation. [V-EXEC C143, C145]

The window discovers EU5 and its profile. Choose missing folders in Settings; the
choices are remembered. Without EU5, open compact world files and view their maps.
Generating, rerolling, checking reproduction and importing a built world need EU5.
Generation can keep the mod in the library, copy it to a chosen folder, or retain
only a compact world file. Installing into the game's profile is a separate checkbox.
No profile is needed for the other destinations. [V-EXEC C143]

## Continent, resources and peoples

The World tab holds the type, broad balance and visibility before playing. Advanced
holds the seed, world code, land sources and exact values. Save and play holds the
destination, installation choice and queue; Generate stays available below the tabs.
Settings holds application paths, the window's language and diagnostics. [V-EXEC C147] The window speaks the language Steam runs EU5 in, unless another is chosen there; a choice applies at the next start, and every official language of the game is available (C275).

Choose a type and seed, or paste a code. The quick answers set the same values as
Customize. Choose a continent sketches six seeds without building complete mods;
selecting one restores its settings and seed. Sketches reveal land only, and the
final location boundaries can move the coast slightly. A supplied land image disables
this choice; use Save land template and Load land image for externally drawn land.
[V-EXEC C143, C144]

*Expand generation into the oceans* on the World tab is checked by default and
recommended. It gives the New World a wider, fixed ocean sector so continents can
grow beyond the original American silhouette. The Old World and protected islands
stay. Uncheck it to use the original distance band around vanilla America. The
choice is part of the world code and applies to sketches, land templates and layer
rerolls. Codes from before 0.12.0 choose the original canvas; their usual warning
about a different algorithm epoch still applies. [V-EXEC C282–C284]

On a finished world, New peoples and New resources keep the continent and roll only
the selected part. The previous version remains in the library. Versions replace
the installed mod by default; Keep both retains both installed mods. Undo roll
restores the previous version in the game. Previous version opens its library page.
[V-EXEC C142, C143]

Maps start covered. Reveal this world exposes the six atlas layers without exposing
its thumbnail in EU5. Show the New World belongs to each world: choose it before
generation or change it on the finished world's World tab. It updates that world's
picture and existing mod's selection cover without generating geography again. From
EU5's main menu, close and reopen the Mods manager to read that visibility update
(owner observation on 1.4.5, C429). Restart the game before switching actual worlds
or replacing a loaded map. The new-world choice remembers a default for future generations.
Old records inherit the previously saved global choice once, so changing the default
leaves existing worlds alone. Missing cover sources produce an explicit error. [V-EXEC C147]

Hover and search inspect locations; Compare draws two revealed worlds. Save picture
and Copy picture follow the world's visibility; layer export requires a revealed atlas.
Notes holds personal notes, a favourite and a tag. Versions and files groups rerolls,
sharing, world details, reproduction checks and deletion. [V-EXEC C143, C147]

Select several entries with Ctrl-click or Shift-click, or use Select all above the library.
Remove from game below the list takes out only selected installed mods, keeping their
codes and pictures. It also handles earlier mods without library records, and needs only
the profile, not the game installation. Delete from library asks once before deleting the
selected recorded worlds, their notes, kept files and installed mods. Both buttons show
how many entries they affect. Errors stop the batch and appear below the list; any changes
already made are reflected there. Selection survives list updates. [V-EXEC C266]

Add to queue captures the current settings, seed and destination. Change the seed or
settings and add another job. Run queue works sequentially; Cancel or a failure stops
before the next job and leaves unfinished jobs pending. [V-EXEC C143]

## Files and command line

A `.rnworld` carries the code, record, atlas, notes and optional drawn land. It carries
no built mod or game assets. A `.rnworld-mod` carries the built mod for transfer between
the player's own machines; its map fingerprint and input manifest must match the game.
Drag either onto the window or use Open world file. [V-EXEC C143]

Examples; commands use the normal platform data directory unless `--data-dir` or
`RNW_DATA` chooses another one:

```sh
uv run rnw world-code --preset small_continents --seed 42
uv run rnw world CODE --out /path/to/mods
uv run rnw world CODE --world-file /path/to/world.rnworld
uv run rnw reroll CODE --part peoples
uv run rnw worlds
uv run rnw export-world WORLD_ID /path/to/world.rnworld
uv run rnw import-world /path/to/world.rnworld
uv run rnw draw-map WORLD_ID countries countries.png --reveal
uv run rnw search-atlas WORLD_ID gold --reveal
uv run rnw annotate-world WORLD_ID --notes "Try with friends" --tag coop --starred
uv run rnw undo-roll WORLD_ID
uv run rnw world-visibility WORLD_ID --show-new-world
uv run rnw world-visibility WORLD_ID --hide-new-world
uv run rnw candidates candidates.png --code CODE --count 6
uv run rnw generate-queue codes.txt
uv run rnw verify-world WORLD_ID
```

`codes.txt` contains one code per line; the command keeps mods in the library and
stops on the first failure. `rnw --help` lists the generation, exchange, installation
and diagnostics commands. A `portable.txt` beside the packaged launcher keeps its
data in `data/` beside it, for both the window and CLI. [V-EXEC C143]

## Reproduction, cache and releases

Released 1.0.0 uses algorithm epoch 59. Exact reproduction needs the recorded
algorithm, resolved settings/rolls and game inputs; the version alone is not
sufficient for development builds. The local cache keys include the algorithm
and relevant inputs and are checked before use. Follow the [version policy](adr/0003-versioning.md)
when making new releases; older output is not silently migrated.

New input manifests also record directory listings, so a patch adding scripts is
detected as well as changed or removed files. Old manifests remain readable; those
without directory listings retain C141's limitation, and a full reproduction check
is the stronger test. [V-EXEC C143]

Release packages are available on [GitHub](https://github.com/Sir-Starch/eu5-random-new-world/releases)
and through the [Workshop hub](https://steamcommunity.com/sharedfiles/filedetails/?id=3829217331).
Tagged Linux/Windows CI, Windows package self-tests, owner Windows 11 smoke and
Linux/Proton use are recorded (C428, C438–C439, C441). Windows binaries are unsigned;
see [known limitations](known-limitations.md) for platform and campaign limits.

## Library shared by installed copies

The generator stores its library outside the application/mod folder: by default
`%LOCALAPPDATA%\RandomNewWorld` on Windows (inside EU5's prefix for Proton),
`~/.local/share/random-new-world` on Linux, or the platform equivalent. `RNW_DATA`
or `portable.txt` can choose a different location. The Workshop application can
therefore show records from an earlier local copy. It also recognises existing
local RNW world mods and can restore their library data from recovery metadata.
Those worlds are not bundled in the Workshop hub (C441).

**Code only** means that a library record remains, but the application currently
finds neither a matching installed mod nor a kept built-mod folder for it. Codes,
notes and available pictures can remain usable. Add to the game regenerates when
needed; retain the original game inputs/version when exact reproduction matters.
