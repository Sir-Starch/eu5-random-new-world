# Using the generator

**Random New World creates a new map for your next Europa Universalis V campaign.**
It replaces the Americas with new continents, islands, resources and native societies,
while keeping the Old World intact. Each world becomes its own mod that you enable in EU5.

If you came here from Steam, start with the steps below. The default settings are enough
for your first world; you can explore the other options whenever you want.

**Current compatibility:** RNW supports **EU5 1.4.***. New patches in the 1.4 branch are usually compatible without a generator update; the latest fully verified version is **1.4.7** (Steam build 26377361). Continue each generated map's campaign on the exact EU5 version used to create it.
See [known limitations](known-limitations.md) for game updates, saves and mod compatibility.

## Quick start: from Steam to your first campaign

1. **Open the generator.** Subscribe to [Random New World on the Steam Workshop](https://steamcommunity.com/sharedfiles/filedetails/?id=3829217331).
   In EU5's **Mods** menu, find **Random New World**, choose **Open in folder**, and launch
   **Random New World Generator**. On Linux or Steam Deck, the Workshop version runs
   through Proton. You can also download a standalone package from
   [GitHub Releases](https://github.com/Sir-Starch/eu5-random-new-world/releases).
   The packaged generator needs no Python or Rust installation.
2. **Check that EU5 was found.** The generator normally finds your game and profile
   automatically. If it asks for a folder, open **Settings** and choose it there.
   The game folder contains EU5 itself; the profile folder contains your EU5 user data
   and local mods. Your choices are remembered.
3. **Choose a world.** Select **New world**, then choose a **World type** on the **World**
   tab. **Continents** is a straightforward first choice. Keep the other settings as they
   are, or paste a friend's **World code** (under **Advanced** in the classic window).
   Leave **Expand generation into the oceans** checked to give your continents more room.
4. **Generate it.** On **Save and play**, choose **Keep the mod in the library** and tick
   **Add to the game when it is done**. Click **Generate** and wait for it to finish.
   Generation usually takes a few minutes; allow about 7.5 GB of free RAM.
   Maps stay hidden by default so you can discover the New World during your campaign.
5. **Enable your world in EU5.** In the game's Mods menu, enable the newly created world
   mod, for example **RNW: Small continents 7K3Q**, and start a **new 1337 campaign**.
   Enable **one RNW world at a time**. The Workshop generator item itself stays disabled
   in your playset; your generated world contains everything needed to play.

**Keep the generated mod for that campaign's saves and stay on the exact EU5 version used to generate the map.** A world code is useful for making the world again, but a newer generator or game update can change the result.

**Restart EU5 before switching worlds or replacing a map you have already loaded.**
This includes switching after playing a campaign in the same session. For a visibility
change alone, see [keeping maps hidden](#keep-maps-hidden-or-take-a-look).

## Find your way around

The main window has three parts:

- **Left: your library.** Select a saved world or **New world**. Hide or show this panel
  with **Ctrl+B**.
- **Middle: the map and previews.** This is where continent sketches, maps and generation
  progress appear.
- **Right: settings and world details.** For a new world, **World** holds the main choices,
  **Advanced** holds exact values, and **Save and play** controls saving, installation and
  visibility. **Generate** stays below the tabs. Hide or show this panel with **Ctrl+I**.

After generation, select your world to find its **World**, **Maps** and **Notes** tabs.
The World tab includes adding it to the game, creating versions, sharing and exporting.

**Settings** holds game and application paths, language and diagnostics. The generator
normally uses the language Steam runs EU5 in. You can choose any official game language
there; restart the generator to apply a language change. Button names in this guide are
the English ones.

If your window has a different layout, it may be the **classic window**, which opens
automatically on systems that need it, including the usual Proton setup. Its **Advanced**
tab holds the seed, world code, land previews and **Customize** controls. New-world
visibility is on **World**; saving and installation are on **Save and play**. The same
generation and library features are available. See
[window troubleshooting](#the-window-is-blank-or-does-not-draw-properly) if you need to switch.

## Continent, resources and peoples

### Choose a world type

A world type gives you a starting set of settings. Choose the shape you like, then
adjust the broad choices on the World tab or individual values in Advanced.

| World type | What to expect |
|---|---|
| **Supercontinent** | One great landmass with a few islands. |
| **Continents** | Large continents, sometimes joined by narrow land bridges, plus islands. |
| **Small continents** | Three or four separate continents of similar size. |
| **Archipelago** | Several large islands and many smaller ones. |
| **Scattered islands** | A sea of small islands with no great landmass. |
| **Omerika** | A familiar New World, reimagined: the general shape of the Americas, entirely different geography. [More below](#the-omerika-preset). |
| **The Wall** | A long north-south barrier, with optional sea passages. [More below](#the-wall-preset). |
| **Random** | Picks one of the world types for you. |
| **Total Chaos** | Picks a world type and randomizes its detailed settings within the allowed ranges. |

The quick choices for land, native peoples, native states, extraordinary peoples and
precious resources adjust the same settings you can change individually in **Advanced**
(**Customize** in the classic window).

In **Total Chaos**, **Randomize settings again** draws another world type and another set
of Advanced values, keeping the seed. **Random** beside the seed changes only the seed.
An untouched draw is named **Total Chaos <tag>**; changing its settings by hand names it
**Custom world <tag>**. Its code keeps this distinction. A personal name overrides both.
Older codes did not record the random mode: changed geography in such a code is called
**Custom world**, rather than claiming to have the shape of its original preset.

### Seeds and world codes

The **seed** is the number used to make a world. Change it, or press **Random**, to try
another world with your chosen settings.

A **world code** includes the seed and generation settings. Copy it to keep or share a
world's recipe; paste one into **World code** to use it. For the same result, use the
same generator release and game files. If a code comes from a different generation
algorithm, the application warns you that the result may change.

For a world with custom-drawn land, share a **`.rnworld`** file to include the land image.

### Preview continents or draw your own

**Choose a continent** shows six land sketches before you build a complete world mod.
Pick one to use its seed and settings. These previews reveal the land shape only;
the final coastline can shift slightly when the game's locations are created.
The sketches are drawn side by side, as many at once as your processor and free memory
allow, and the land of each is kept: the world you make from a sketch starts from that
land instead of drawing it again.

To draw your own land, use **Save template** to get an image of the available area.
Paint land white and sea black in an image editor, then load it with **Land from an image**.
The rest of the world is generated on that outline. Loading a land image disables
the six-sketch choice. The Wall cannot use a land image.

### Give your continents more room

**Expand generation into the oceans** is on by default and recommended. It gives the
New World a wider area, so continents can grow beyond the original outline of the
Americas. The Old World is preserved; protected islands are kept, with islands in the
way kept in place or moved to free water as needed.

If you want land farther from the Old World's shores, raise **Advanced → Land and sea →
Distance from the Old World**. Higher values move land toward the middle of the ocean
without reducing the amount of land. The Wall ignores this setting.

Turning ocean expansion off confines generation to the original band around the
Americas. Hover over the option's information mark for a reminder of the difference.
The choice is saved in world codes and used by sketches, land templates and later
versions of a world. Codes from before 0.12.0 use the original area; the usual warning
about an older algorithm still applies.

### Reveal the New World at the start (multiplayer)

**Reveal the New World at the start** is off by default. Switched on, the country of every
human player discovers every area of the generated New World, land and sea, when the
campaign begins, so that every player sees it from the first day. The computer's countries
do not get it: they find the New World by exploring, as in the game. It is a world setting
like the oceans option: it is saved in world codes and kept by later versions of the world,
and a world made with it off has none of its files. The world writes one file,
`in_game/common/on_action/rnw_reveal.txt`, which runs the game's own `discover_area` effect
for each area at the `on_game_started_after_lobby` hook, once the players have chosen their
countries (the earlier `on_game_start` hook runs before the lobby, when no country is human
yet); no country record of the game is changed. On the classic window the option is at the
foot of the **World** page, a scroll below *Before you play*.

The game's own announcement that the New World was discovered (an exploration event that
rewards the first Old World country to explore, and tells every human player in range) is not
shown, because the discovery is already made; the world sets the flag that event sets (a
global flag, set for the computer's countries too). The expedition *Western Ocean Voyage* is
not offered to the players' countries, since it needs an undiscovered New World; the
computer's countries keep it, as in the game. Other content that reads the discovery (the
Pacific crossing, the circumnavigation, a few events of Castile and the merchant republics)
follows its own conditions for each country, as it would after a discovery. Only the
countries that a human plays at the start know the New World: a player who joins or changes
country later, and a country created later, do not. Whether the hook runs for every start of
a campaign (a new game, a multiplayer table) has not been observed in the game with this file.

### Adjust native societies

Use **Native states** on the World tab for a broad choice, or **Advanced → Peoples**
for more control:

- **Land in states** sets the target share of inhabited land held by states, from
  **3% to 60%**. The quick choice **Many** requests **44%** on the default presets.
  Actual coverage can be lower where farming and population cannot support states.
  The generator does not add population just to meet the target.
- **Peasant share** sets the upper share of peasants in an inhabited location at full
  social complexity, from **30% to 80%**, with **60%** as the default. It applies across
  inhabited land, including outside states. Areas with poorer farmland or less complex
  societies remain more tribal.

**Historical turbulence** sets the frequency of conflict and political change in the
three centuries before 1337: **Calm**, **Varied** (default) or **Turbulent**. Advanced
allows values from 0 to 1000. History remains active at every value. Extraordinary
peoples seeds possible paths; their survival follows from the simulated history.

### Adjust resources

**Advanced → Resources** has a frequency slider for each ordinary New World resource,
alongside the precious-resource slider. These control how often resources appear:

- **1×** uses the base game's weights.
- **0** excludes that resource.
- Raising one resource's weight leaves fewer locations for others.

Climate and terrain still guide placement. These settings change resource distribution;
production per location stays the same. If none of the enabled resources suits a
location, generation stops and explains the problem.

**Reset** restores one slider to 1×. **Reset all to the world type** restores the chosen
world type's settings. Resource settings are included in the world code.

### The Omerika preset

**Omerika** is a New World you seem to know: the general shape of the Americas, with North
and South America joined by a Central American isthmus, and everything else new. The coasts, bays,
peninsulas, straits and inland seas are generated, and so are the mountains, plains, climate,
rivers, lakes, resources and peoples, as in every other world type.

The shape comes from the installed game's own map, read when the world is made, and is used only
as a low-frequency guide: where the great landmasses lie, how large they are and that a neck of
land joins them. No coast of the Americas is copied. Each seed bends the guide in its own way, so
the continents shift, swell and lean differently from seed to seed.

In **Advanced → Omerika** you can adjust **Likeness to the Americas**. A low value leaves a loose
echo of the layout; a high one keeps the places and sizes of the continents. The default is 60%.
At 0% the guide is switched off and the world is made like any other with these settings. Land
amount, landmass scale and coast detail work as in the other world types; the land amount starts
at the share the Americas hold.

The two great landmasses are joined by a corridor of land along the guide's neck, raised above
the noise, so North and South America stay one landmass at every setting. If land ever fell
apart anyway, generation stops with a message rather than producing it. Omerika cannot use a drawn
land image or share a world with The Wall.

### The Wall preset

**The Wall** creates a long, narrow north-south continent or island chain. Depending on
the seed and settings, its coast can include islands and narrow sea passages.

**Allow gaps in the wall** is on by default. Turn it off for a continuous land barrier
that ships cannot cross or sail around. Its polar ends reach the map edges and contain
impassable locations. The continuous land route can bend and change width along the way.
Extra continents and islands can appear on either side.

In **Advanced → The Wall**, you can adjust:

- **Width:** from **4% to 44%** of the generation area's width; **14%** by default.
- **Position:** move the Wall west or east. It bends around protected islands in its way.
- **Coastal irregularity** and **Mountain spine:** change its shoreline and central mountains.
- **Allow gaps in the wall:** choose whether sea passages are permitted.

The Wall and the land beside it share one land budget. A wider Wall uses more of that
budget, leaving smaller continents or just a few islands beside it. If the Wall is wider
than the land budget allows, it keeps its land and the world exceeds the requested land
amount. Raising the land amount also widens the Wall itself. Landmass scale and coast
detail settings affect both the Wall and the extra land.

This preset always uses the expanded ocean area. Other presets and custom land images
can also reach the polar map edges; they have no mandatory ocean strip there.

## Keep maps hidden or take a look

Worlds start covered so you can discover them while playing. There are two separate
ways to reveal a world:

| Option | What it reveals |
|---|---|
| **Reveal this world** | The maps inside the generator. The mod picture and EU5 country-selection map keep their own visibility setting. |
| **Terra Incognita in the lobby** (on by default) | Covers the New World as terra incognita on that world's preview picture, mod thumbnail and EU5 country-selection map; clear the box to show them. Choose it on the **World** tab before you generate, or change it later on the finished world's **World** tab. |

Changing the second option updates the existing mod's picture and selection-map cover
without generating the geography again. From EU5's main menu, close and reopen the
**Mods** manager to refresh the change. This refresh was observed on EU5 1.4.5; changing
the actual world still requires a game restart.

The new-world visibility choice becomes the default for future worlds. Each existing
world keeps its own setting. Older library records inherit the previously saved global
choice once. If files needed to update the cover are missing, the application shows an error.

Once revealed, the atlas offers **ten map views**, including physical geography,
countries, cultures, religions and resources. Hover over locations or use search to
inspect them. **Compare** displays two revealed worlds side by side.

**Save picture** and **Copy picture** respect the world's visibility. Exporting an atlas
map layer requires revealing the atlas first.

## Manage worlds and versions

For worlds made with 1.2.0, click a land location to read its society and history. The
location's card has four tabs. **Place** holds the location's facts, its start development as
the game computes it among them, and the history of its region: whether the extraordinary
peoples set for the world took shape and survived to 1337, the inheritances its societies
share, and the years its land changed historical owner. **Society** shows the country's
government and country rank, its origin and the societal values EU5 shows for it, all as the
game names them, with the event that last shaped each value. A world made before the values
were recorded says so; make a new world to see them. **Chronicle** is a timeline of the country's most
significant recorded events, oldest first. **Relations** shows the country's opinion of
other countries on the first day, line by line as the game lists it: the opinions its
treaties give (*Allied*, *Rival*, *Our Liege*, *Our Vassal* and the guarantees, under the
game's names) and the historical opinions the world writes, under their names in the game,
each with its value, its yearly fade and their sum. The game adds its own opinions for
culture, religion, language, borders and more. The classic window opens the same facts
through **Society and history**.
Place links move the map to the recorded place. History travels in compact
world files and works without the game installed. Earlier worlds show **No recorded
history**; they are not assigned an invented past. Covered worlds keep history hidden.

### Try new peoples or resources on the same land

Select a finished world and open **Create a version** on its **World** tab
(**Versions and files** in the classic window):

- **New peoples** generates new countries, cultures, religions and names on the same land.
- **New resources** changes resources while keeping the land and peoples.

- **Same land, change settings** opens the world's seed and settings on the new-world page.

The previous version stays in your library. A new version normally replaces the installed
one. Tick **Keep this one in the game too** to retain both installed mods, and enable only
one in your EU5 playset. **Previous version** opens the earlier library entry; **Undo roll**
restores it in the game. Keep the version used by an existing campaign's saves.

A world that an earlier generator algorithm made (see [epochs](#reproduction-cache-and-releases)) has these
three buttons off, and the page says why: the same seed would give other land here, so a
version would not be on the same land. Make **New world with these settings** for a new land
with the same settings, or use the generator release that made the world. The page goes by
the world's record, which says what made its files. In the command line, which has only the
code and so only the release stamped in it, `rnw reroll CODE --part peoples` or
`--part resources` stops with the same words; `--part land` makes a code for a new seed.

### Notes and favourites

Use **Notes** for personal notes and a tag. Mark a world as a **Favourite** to find it
again easily. World details, reproduction checks and file actions are on the World tab;
the classic window groups these under **Versions and files**.

### Remove or delete worlds

Select several library entries with **Ctrl-click** or **Shift-click**, or use **Select all**.
The buttons below the library show how many entries they will affect:

- **Remove** removes the selected installed mods while keeping their library
  records, codes and pictures. It can also remove earlier RNW mods that have no library
  record. This needs the EU5 profile folder, but not the game installation.
- **Delete** asks for confirmation, then deletes the selected recorded
  worlds, their notes, kept files and installed mods.

If an error occurs, the batch stops and shows the error below the list. Changes already
made appear in the library, and your selection survives list updates.

## Generate several worlds in a queue

1. Choose the settings, seed and destination for your first world, then click **Add to queue**.
   You can also queue a continent directly from its sketch.
2. Change the seed or settings and add another world. The same world cannot be queued twice.
3. Click **Run queue**. Worlds are generated one at a time.

You can keep adjusting settings and adding worlds while generation runs. New jobs follow
automatically when the current one finishes, without another click on Run queue.

Each job remembers the settings, seed and destination it had when you added it.
You can remove pending jobs individually; the running job stays in the list until it
finishes. A world that cannot be made does not stop the queue: it stays in the list,
marked with its error, and the next world starts. When the run ends, the status line counts
the worlds that stay, and **Run queue** tries them again (the ones that failed too);
remove a failed world from the list, or **Clear queue**, to forget it. If every world of a
run fails, the run ends with the last error. **Cancel** still stops the queue before the next
world, leaving unfinished jobs pending. A world you started with **Generate** is not in the
queue: if it fails, it shows its error with **Retry**, and the worlds queued behind it wait
for **Run queue**.

## Save and share worlds

To share a world, copy its **world code** or use **Save world file** under **Share and
export**. You can open world files by dragging them onto the window or choosing
**Open world file**.

| File | What it contains | When to use it |
|---|---|---|
| **`.rnworld`** | The world code, generation record, atlas, notes and any custom land image. It contains no built mod or game assets. | Share a world, keep its maps, or view it without EU5 installed. Making its playable mod still needs EU5. |
| **`.rnworld-mod`** | The complete built mod. | Move a world between your own machines using **Transfer built world**. It contains game-derived data and is for personal transfer. The receiving machine's game map fingerprint and input manifest must match. |

In **Save and play**, you can keep the built mod in your library, copy it to a chosen
folder, or save only a compact world file. Adding a library mod to the game is a separate
checkbox. You can save to the other destinations without an EU5 profile.

EU5 must be installed to generate worlds, make new peoples or resources, check exact
reproduction, or import a built world. You can open compact `.rnworld` files and view
their maps without the game.

## Library shared by installed copies

Your library lives outside the generator and mod folders. This lets different installed
copies of the generator use the same saved worlds. The default locations are:

- **Windows:** `%LOCALAPPDATA%\RandomNewWorld`.
- **Linux:** `~/.local/share/random-new-world`.
- **Proton:** the Windows location inside EU5's Proton prefix.

Seeing worlds from an earlier local copy after installing the Workshop generator is
normal. Those worlds come from your local library. The generator also detects existing
local RNW world mods and can rebuild their library entries from recovery information
stored in the mods.

**Code only** means the library still has a record, but the generator cannot find a
matching installed mod or a kept built-mod folder. Your code, notes and available
pictures can still be used. **Add to the game** regenerates the mod when needed.
Keep the original mod and game inputs if an exact copy matters for a campaign.

For a portable setup, place a file named **`portable.txt`** beside the packaged launcher.
The generator will keep its data in a **`data/`** folder beside it, for both the window
and command line. You can also choose another data directory with `RNW_DATA` or the
command-line option `--data-dir`.

## Troubleshooting

### EU5 or its profile was not found

Open **Settings** and choose the missing folder. If you have never started EU5, launch
it once so it creates a profile, then reopen the generator. A profile is needed to add
mods to the game; the game installation is needed to generate them.

### The window is blank or does not draw properly

Open **Settings**, select **Use the classic window**, and restart the generator.
If you cannot use the window, start the packaged launcher with **`--classic`** instead.
From source, use `uv run rnw gui --classic`. The environment variable
`RNW_WINDOW=classic` also selects it.

The main window uses **WebView2** on Windows and **WebKitGTK 4.1** on Linux. WebView2 is
normally available on Windows 11 and current Windows 10 installations. When the required
web view is missing, the generator opens the classic window automatically. This is
expected when running the Workshop version through a Proton prefix without WebView2.

### Generation stopped with an error

Read the message first: it explains whether the problem concerns game files, a destination,
settings or the generated map. Some seed and settings combinations cannot produce a
valid world; use **Generate with a new seed** to try another one. See
[known limitations](known-limitations.md) for compatibility and platform issues, including
unsigned Windows binaries that Smart App Control may block.

To report a failure, include the message's technical detail and the file from
**Settings → Save diagnostics**.

### "The generator stopped"

The Tauri window shows this when the generator's own process has ended, so no explanation of
a failed world can come with it. In 1.1.0 it happened whenever **New peoples** or **New
resources** began to make a version, because the line under the world had no words for that
work; update to a release that has the fix. If it happens again, the cause is in
`generator.log` and `last-error.log` of the generator's data folder, which
**Settings → Save diagnostics** puts in its file: send that file with the world code.

### The New World is all Clay or its map modes are empty

If every generated location has Clay and the climate, vegetation and topography map
modes show nothing there, the game has not read the world's location data. Check that:

- only one generated world is enabled in the playset;
- no mod after the world replaces `in_game/map_data/location_templates.txt` or other map
  files, such as a resource or map mod;
- the world's mod folder is complete: remove the world from the game in the library,
  then add it again.

The world's page warns about the first two causes while the world is in the game and ticked:
it names a mod after the world that has files at the same paths as the world's, and any
other ticked RNW world. Put that mod before the world in the load order, or untick it.
The diagnostics file lists the load order and the same check.

Restart EU5 after changing the playset. If the problem remains, report the world code
with EU5's `error.log` and the diagnostics file.

## Files and command line

The remaining sections are for players who want to use commands, run from source or
understand exact reproduction.

### Launch from a package or source

- **Linux package:** launch `./RandomNewWorld`; use `./RandomNewWorld --cli --help`
  for commands.
- **Windows package:** use the included launcher for the window and `rnw.cmd` for commands.
  The Workshop package uses the same Windows runtime and can run through Proton.
- **Source checkout:** run `uv sync --locked --group dev`, then build the window with
  `npx tauri build --no-bundle` inside `desktop/`. Return to the repository root and run
  `uv run rnw gui`. See the [source setup instructions](../README.md#build--run-from-source)
  for requirements.

Standalone packages work without a Workshop installation.

### Command examples

These examples run from a source checkout. With a packaged version, replace
`uv run rnw` with `./RandomNewWorld --cli` on Linux or `rnw.cmd` on Windows.
`CODE` and `WORLD_ID` are placeholders for your world code and library world ID;
replace the example paths with your own.

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

For `generate-queue`, put one world code per line in `codes.txt`. The command keeps
the mods in the library and stops on the first failure. Run `uv run rnw --help`
(or your package's equivalent) for generation, world-file, installation and diagnostics
commands. Commands use the normal application data directory unless you set
`--data-dir`, `RNW_DATA` or portable mode as described above.

## Reproduction, cache and releases

**For an ongoing campaign, keep its built world mod.** A code or compact world file
stores the recipe; making exactly the same world again also needs the original
generation algorithm, resolved settings and rolls, and game inputs.

RNW 1.1.0 uses **algorithm epoch 60**; 1.0.0 used **epoch 59**. An epoch identifies a
generation algorithm, so the same code can produce different worlds after an epoch
change. For development builds, a version number alone is not enough to identify the
algorithm. Older output is not silently migrated. The [version policy](adr/0003-versioning.md)
explains the technical rules.

The local cache checks the algorithm, the generator's own code and the relevant game
inputs before reusing work. It lives in `cache/land` of the data folder and keeps the four
most recently used continents (for rerolling resources or peoples), the land of the last
24 sketches and the area of the game's map that a New World replaces; older entries are
removed on their own. Deleting the folder is always safe: the next world makes them again.
Newer input records also track directory listings, so they detect game patches that
add scripts as well as changes to existing files. Older records still open, but records
without directory listings may miss added files; a full reproduction check is stronger.

Get released packages from [GitHub Releases](https://github.com/Sir-Starch/eu5-random-new-world/releases)
or the [Steam Workshop hub](https://steamcommunity.com/sharedfiles/filedetails/?id=3829217331).
For platform and campaign limits, see [known limitations](known-limitations.md).
Implementation details and dated verification evidence are kept in the
[GUI design](gui-design.md) and [claims ledger](research/claims-ledger.md).
