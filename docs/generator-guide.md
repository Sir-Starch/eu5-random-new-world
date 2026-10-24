# Using the generator

> [!NOTE]
> Written for 0.9.24. Later releases added controls (for example *Extraordinary peoples*) without changing the workflow; see the [changelog](../CHANGELOG.md).

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
Settings holds application paths and diagnostics. [V-EXEC C147]

Choose a type and seed, or paste a code. The quick answers set the same values as
Customize. Choose a continent sketches six seeds without building complete mods;
selecting one restores its settings and seed. Sketches reveal land only, and the
final location boundaries can move the coast slightly. A supplied land image disables
this choice; use Save land template and Load land image for externally drawn land.
[V-EXEC C143, C144]

On a finished world, New peoples and New resources keep the continent and roll only
the selected part. The previous version remains in the library. Versions replace
the installed mod by default; Keep both retains both installed mods. Undo roll
restores the previous version in the game. Previous version opens its library page.
[V-EXEC C142, C143]

Maps start covered. Reveal this world exposes the six atlas layers without exposing
its thumbnail in EU5. Show the New World belongs to each world: choose it before
generation or change it on the finished world's World tab. It updates that world's
picture and existing mod's selection cover without generating geography again; restart
EU5 to read the change. The new-world choice remembers a default for future generations.
Old records inherit the previously saved global choice once, so changing the default
leaves existing worlds alone. Missing cover sources produce an explicit error. [V-EXEC C147]

Hover and search inspect locations; Compare draws two revealed worlds. Save picture
and Copy picture follow the world's visibility; layer export requires a revealed atlas.
Notes holds personal notes, a favourite and a tag. Versions and files groups rerolls,
sharing, world details, reproduction checks and deletion. [V-EXEC C143, C147]

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

The algorithm epoch remains 1 in 0.9.24: this release changes application presentation
and per-world preferences; the generation algorithm and its reference digest are unchanged.
The 0.9.23 reference world's 739 mod files match the recorded digest (C144).
The local land cache includes the epoch, seed, settings,
canvas and drawn mask in its identity and checks every cached file before use.
Corruption fails with the exact cache entry to remove. The two measured exports took
132 s cold and 105 s warm on this session's machine; this is a measurement, not a
promise of a particular speed on another machine. [V-EXEC C144]

New input manifests also record directory listings, so a patch adding scripts is
detected as well as changed or removed files. Old manifests remain readable; those
without directory listings retain C141's limitation, and a full reproduction check
is the stronger test. [V-EXEC C143]

The release workflow creates artifacts from a version tag, checks the tag against
`pyproject.toml`, runs self-tests and checks for game assets. It does not publish a
release or Workshop item. Linux and Windows-through-Wine self-tests were run locally;
macOS, native Windows, signing and GitHub Actions execution are still unverified.
See [ADR 0010](adr/0010-layered-worlds-and-a-generator-of-its-own.md) and
[legal](legal.md) before public distribution. [V-EXEC/UNKNOWN C145]
