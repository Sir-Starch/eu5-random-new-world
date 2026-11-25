# Generator window

## 0. Reference

This documents the existing Qt Widgets interface, extracted from `gui/window.py`,
`gui/maps.py` and `gui/preview.py`. ADR 0007 chooses the platform's controls and theme.
The owner's 2026-10-22 screenshots authorize reorganizing the interface around generation,
world management and application paths. The Tauri window ([ADR 0011](adr/0011-tauri-window.md)), the generator's window since 2026-10-30, is described in §9; §1–§8 describe the classic Qt window, its fallback, which keeps Qt Widgets and platform typography and, since 2026-11-21 (owner: Qt must not fall behind Tauri), the same functions: the land tools and editor of every continent, the queue's rows, the made world's title and button, and the map's kept lands and continent names (§6, *Parity with the Tauri window*).

## 1. Structure

A compact header identifies the game build; complete paths live in Settings. A horizontal
splitter holds the library and the selected page. New-world configuration tabs separate
world choices, exact values and delivery. Each tab owns one vertical scroll area. Only the
primary Generate action and a short status remain fixed below them; queue controls and
stage details are disclosed when requested. The library scrolls independently.
Worlds have an overview, maps, and personal notes. Secondary operations use dialogs.
The library has the Tauri window's filter (words, and All/In the game/Favourite) and keys
(Ctrl+N, Ctrl+O, Ctrl+Enter, Ctrl+, , Ctrl+B for the library, Ctrl+V of a world code); a
meter under the location estimate turns amber near the budget and red over it.
Minimum supported window: 1080 by 760; desktop testing also covers 1440 by 900.

## 2. Colour

Qt's QPalette supplies background, text, selection and focus in light and dark themes.
Descriptions inherit Qt's foreground for live theme changes. Controls retain the native
style and palette; unreadable disabled text is normalized against its native surface.
Inactive actions are disabled with an explanatory tooltip, and errors include text.
Maps have their own legend and colours, independent of the interface theme.

## 3. Type

Use the platform font. World titles use the existing 1.4 times body-size bold style.
Labels wrap; paths, codes and explanatory details are selectable.

## 4. Spacing

Use a 4px spacing unit: 8px between related controls, 16px between sections and 16px page
margins. Interactive buttons and text inputs have a font-derived minimum height (at least
32 logical pixels); dialogs size to their content instead of compressing controls.
Nested structural layouts use zero margins.
Existing library icons are 96 by 48; candidate icons are 192 by 96, twice that size.
The library's initial width is 250; the remainder stretches. Dialogs use native buttons.
Path selectors shrink independently of path length and expose full paths in tooltips.

## 5. Reusable primitives

QPushButton, QToolButton, QComboBox, QLineEdit, QCheckBox, QListWidget and QGroupBox
retain Qt's normal, hover, pressed, focus and disabled states. QDialogButtonBox supplies
accept and cancel actions. PreviewView handles map fit, zoom and pan. MapsPanel draws the maps as the Tauri window
does (`rnw.gui.mapstyle`, palettes and profiles shared through `rnw/gui/lenses.json`): the
physical map under every lens, Show tribes, names written at every zoom, cities, capitals and
riches, values up close, a legend that lights an entry under the pointer, isolates it on a
click and zooms to it on a double-click, one search, a pinned location card whose values
isolate what they name, lens keys 1–0, copying the view and saving the lens as drawn. It
draws with NumPy and the native kernels on the processor and Qt Widgets, so it needs no web
view or OpenGL and runs under Proton as it is. SettingsDialog owns application
paths and diagnostics. Visibility belongs to each world's configuration and overview;
the new-world choice remembers a default but never changes existing worlds.
Candidate selection reuses QListWidget icons and native buttons. World actions are grouped
by purpose: Play, Versions, Share and Files; deletion is separated from ordinary actions.

## 6. Interaction

Total Chaos has **Randomize settings again** beside the world-type choice in both windows.
It redraws the type and Advanced values without changing the seed, and is available while
preparing the next queued world. The seed's Random button keeps a Chaos draw's settings.
Naming provenance travels in the world code: an untouched draw is **Total Chaos**, manual
settings make it **Custom world**, and a fresh draw restores **Total Chaos**. Personal names
take precedence; see [the generator guide](generator-guide.md#choose-a-world-type).

Long work runs through Controller's cancellable worker and reports completion or an
error. A failed or cancelled queue stops before the next item. While a world is made the
new world's choices and Add to queue stay available (`Controller.can_prepare`); worlds added
meanwhile follow by themselves (`queue_follows`). Candidate previews are
shown only after the player explicitly requests them. World maps start covered.
Keyboard focus and activation use Qt's native controls; no custom animation is added.
The library uses native extended selection (Ctrl-click, Shift-click, Ctrl+A) and a visible
Select all button. Its footer counts selected entries and installed mods, with separate
Remove from game and Delete from library actions. Removal keeps codes and pictures;
deletion asks once for the selected library worlds. Installed RNW worlds with a readable
code or recovery bundle enter the library automatically, without renaming their mod
folders. Worlds without either stay visible as unregistered, rather than being called
old. Missing provenance is shown explicitly. The visible window polls small metadata
and library-record changes every two seconds; unchanged polls do not reload or redraw.
Generation suspends polling; the queue explicitly refreshes the library after each successful
world, before starting the next, without changing the current selection. Metadata-first copies
can gain their verified atlas/record when the rest arrives, preserving personal fields.
Refreshing or renaming preserves selection and unsaved notes.
Game-build comparisons run on one background worker with a visible checking note. Unchanged
file hashes (where change timestamps are available) and the game's name catalogue are reused.
Classic maps are drawn only when their tab is visible, on one drawing worker; while it works,
only the latest requested picture waits.
A loading notice stays over the map until that picture arrives; stale deliveries are ignored.
The active world's Remove and Delete actions also apply to a multiple selection and show
its count. Batch errors remain visible below the list, including after a row disappears.

**Parity with the Tauri window (2026-11-21).** The classic window does what the Tauri window does,
with Qt's controls and the platform's palette (it follows the system theme; the Tauri window's
own appearance choice (Dark, Light, Terra Incognita) is not copied). Both call the same `Controller`; the Qt side adds no rule
of its own.

- *Land tools* (`gui/land_tools.py`): on the World tab, under Continents, a group with the
  sketches button, the land editor button and a row for each continent that can be drawn: Edit in
  the editor, Land from an image, Save template, the picture chosen and Back to generated land.
- *Land editor* (`gui/land_editor.py`, `land_canvas.py`, `land_sheet.py`, `land_pictures.py`): a
  maximised dialog for the sheet of any continent, drawn by the processor (a `QWidget` painted
  with NumPy, no web view, no OpenGL, so it runs under Proton as it is). The sheet logic
  (`land_sheet.py`) is pure NumPy: pencil, eraser, line, rectangle, ellipse, fill (by the native
  flood fill), pipette, terrain-on-ground and filled shapes, undo kept as changed pixels. Cutting
  the area, the generator's check, Add terrain and Use run on worker threads and are asked of
  `studio` and the controller, exactly as the bridge asks them; ready, famous and sketched
  lands are galleries; a drawing is kept as a draft in the data folder for each continent and
  restored; keys, zoom, drag-and-drop and import/export follow the Tauri editor.
- *Queue* (`gui/queue_list.py`): a row for each world waiting (▶ the one being made, ⚠ a failed
  one with its error as the tip, ✕ to take any waiting world out).
- *Progress*: the continents of the world being made as its title; when it is made, Open the
  world selects it.
- *Maps*: the lands kept from the game in one grey under the open sea (`mapstyle.kept_alpha`,
  blurred and stepped so that the edge is soft), keyed in the legend as a row that is not
  isolated, and the names of the continents (`mapstyle.continent_names`), written upper case and
  bold between the zooms 0.32 and 0.55 and faded out, for a world of several continents only.
  Both are read from `Controller.surroundings` on the drawing worker, once for an atlas; a world
  whose surroundings cannot be read is drawn without them.
  The atlas records its position on the full map so retained land aligns across the Pacific wrap.
  If an older atlas has no position or records the crop's width, the viewer aligns it with that
  world's overview before drawing the retained land.

## 7. Surfaces

Use native window chrome, frames and separators. No web styling or additional shadows.

## 8. Accessibility and verification

Keep labels and tooltips meaningful, preserve native keyboard navigation, and avoid
colour as the only status signal. Exercise empty, busy, failed and completed states in
offscreen Qt tests. Capture the desktop window in light and dark themes for layout review (the
Tauri window also in Terra Incognita, section 9).

## 9. The Tauri window

**Look.** A workbench that sits beside the game, the same on every system (owner reviews
2026-10-30: the first candidate read as a website, the second as the old layout repainted).
Neutral greys with one blue accent for selection, focus and the primary action; light and dark
(System/Dark/Light in Settings, kept per machine; Terra Incognita is a fourth, below). Noto Sans 13 px for text and map names,
JetBrains Mono for codes; both bundled. Every pane starts with a 32 px header, so the library's
title, the view's title and tools and the inspector's tabs read as one band. Controls are 24–26 px
high with 3 px corners; panels are flat and divided by hairlines, without cards, gradients, glows
or blur (the Dark and Light looks; Terra Incognita dresses them differently); the middle is a darker canvas. An exact value is a bar filled to its value with a tick at
the world type's value: drag it, click to type, step with the arrow keys, Backspace resets.
Icons are a small 16-unit, one-pixel set used only in toolbars and icon buttons; other buttons
carry text. Tokens live in `desktop/src/app.css`; components use them rather than literal
colours. The only motion is the busy spinner. Default window 1160×740, minimum 860×560.

**Terra Incognita appearance.** The fourth choice of Settings → Appearance (`data-theme="incognita"`
on the root, kept per machine in the web view's storage like the others; the classic window
keeps the system palette). A palette alone read as the old window aged (owner review 2026-11-21),
so the look is carried by surfaces and ornament, an aged chart under lamplight: the tokens in
`desktop/src/app.css` give leather-dark panels, vellum text and antique gold; `desktop/src/incognita.css`
adds one baked, seamless 512 px JPEG tile for each of the ground, the panes, the dialogs and the
canvas (paper grain and foxing in the tile), double gilt frames with engraved corners, brass-plate
buttons, a gilded primary action, serif small-cap headings (the system's book serifs; no font is
added) and, where a view is empty, a graduated chart with rhumb lines and compass roses
(`desktop/src/assets/incognita/`). Every picture is our own drawing; nothing comes from the game.
The list a web view opens for a `<select>` is the platform's widget and cannot be styled, so in
this appearance `desktop/src/lib/selectMenu.ts` takes the click and draws the same options in a
menu of the window's own; the `<select>` stays the single source of truth (choosing sets it and
fires `input` and `change`), and the arrow keys on a focused select stay the browser's.
Decoration must stay cheap; measured by tracing raster work in headless Chromium (CDP, repeated
four times as runs differ by about 8 ms): one opaque tile per big surface, not stacked layers or
`feTurbulence`; grain only on large static surfaces; a scroller over a textured parent takes
`background-attachment: local` (a transparent one costs about ten times the raster); no blur,
large shadow or full-size overlay over the WebGL map or the land editor, which repaint on every
pointer move (the frame lies round them as margin, border and an outer shadow; the corners are two
thin strips); and a theme rule is scoped (`.stage.scroll`) so that it does not hit a class of the
same name in another component. The tiles were baked from FFT noise with NumPy and are kept as
the images they are (no baking script is kept); a new one must be seamless at its edges. A change
to the theme is checked in a screenshot of the window.

**Structure.** Three panes over a status bar: the library (filter with All/In the game/Favourite,
New world as its first row, thumbnails, versions drawn as branches under their world,
Ctrl/Shift/Ctrl+A multi-select with Remove/Delete below), a view in the middle and an inspector.
Both side panes are resizable and hide (Ctrl+B, Ctrl+I, the buttons at the ends of the status
bar); their widths are kept per machine. The status bar shows the game and profile, the running
task and the machine's resources. For a world, the middle is its map, or its mod picture with
Reveal while the map is covered; the inspector's tabs are World (name, favourite, place in the
game with add/remove and folder, advice, then folding sections for details and check,
visibility, Create a version, Share and export; delete last), Maps and Notes. For the new world,
the middle shows its land: continent sketches to pick from (the chosen one is marked, each has
Add to queue; with Africa or Oceania switched on each sketch is the whole map, the generated
continents in the colours of a world's picture over the darker lands kept from the game, planned
and coasted by the export's own code for that seed), the land image (with Edit in the editor), or
a blank sheet ruled like a map with **Sketch continents…** and **Land editor…**, the two land
buttons that also stand in the page's header, whose subtitle lists the continents and their types.
A disabled button says why in its tooltip (no game, no continent to draw, the real Americas, a
drawn continent without its picture). The land editor draws the land of any continent the world
generates (America, Africa, Oceania): a switch in its header changes the continent, each with
its own sheet (cut from the game's map as the export plans it for the world's seed, so a drawing
fits what is made), draft and picture, and the new world's page lists each drawn continent with
its own Edit in the editor and Back to generated land. It covers the whole window
while it is open (ADR 0011) and holds the rest (In the world: the whole map turned to put the
sheet's frame in its middle, the chosen sketch of several continents when there is one, else the
game's map with the areas of the other generated continents in a darker grey; its own sketches of
America alone, or the chosen sketch's land of the continent drawn as a place to start from, the
template, importing and using a picture; a picture dropped on the window is imported): a toolbar of
brush, eraser, fill, line, rectangle, ellipse and hand on the left, the six kinds of ground and the
brush options over the sheet, and on the right the starting lands in three groups (ready lands, famous lands, sketched continents), Add terrain, the generator's check
and the picture's import, save and clear; the status line repeats the check's worst line. The sheet
is the area at an eighth of the map's size, zoomed and panned in the window; undo keeps changed
pixels only. While a world is made, its
progress, stages, ETA and Cancel, with the queue under them; afterwards the outcome with Open
the world or a retry. The queue (its worlds, Run queue, Clear queue, a remove button for each)
sits below the sketches at rest, so that the grid does not move with each world added. The inspector's tabs are World
(Continents: a row for each continent with its switch and, while on, its type and its own choices:
the basics as lists (land, native peoples, native states, extraordinary peoples, historical
turbulence, gold and silver), asked of every continent in its own block and answered from that
continent's own type (`quick.py`, `set_quick` for America, `set_region_quick` for the others; the Qt
window has a group of them for each continent that is on); America's real Americas and oceans;
Africa's Morocco, Mamluks and connection to Asia; and each continent's reveal at the start; then The whole world: the sea route around it
and the lobby cover, shown while any land is generated; then seed and code), Advanced (a switch
between the continents that are on, each with its count of changed values; the exact values of
the chosen continent by group; Reset all gives back every continent's exact values and keeps the
World tab's choices) and Save and play (destination, install, queue); under every tab stay the location budget, Add to
queue and Generate. Folded sections stay folded. Messages that the Qt window wrote under a page
are toasts; questions are in-window dialogs.

**Maps.** The physical map is the default lens and the ground under every other (owner review
2026-10-30: the physical map had become less beautiful, tribes were mixed with countries and
resource names hung anywhere). It is drawn from the atlas, which holds no heightmap: vegetation
and climate colours softened across locations, relief shaded from each location's topography
and roughened where it is mountainous (lit from four sides with a bounded, hue-keeping grade, so
no coast goes black or burns out; rock and snow by height and by each climate's snow line; the
numbers are `relief` in `lenses.json`, read by both windows), wetlands, water darkening from the
coast into the open ocean around the New World, region and sea names, cities and towns. The map
is a sheet on the window's own ground, not a piece of an endless sea (2026-11-22, owner report: a
land cut by the picture's edge read as an island): beyond the edge lie the theme's ground (`--map-bg`)
with a faint graticule that moves with the map, a soft shadow and a hairline along the edge in the
colour of the window's rules (`--line-3`), drawn by the map's shader, by the canvas fallback and,
from the window's palette, by the Qt view. Around what it
generated the map shows the lands the world keeps from the game in one grey, read on this machine
from the world's own picture and placed by the atlas's recorded origin (a world made before it was
recorded is placed by matching its atlas to that picture, exactly or not at all); a world of
several continents names America, Africa and Oceania large while the map is seen whole, each by
its regions' continent in the installed game, and the legend keys the grey (2026-11-21, owner
report: which continent is where, and where the game's own world lies). The other lenses
lay their colours over it as strongly as each needs, so the relief shows through; land that
holds nothing of a lens shows the physical map faded. Countries colours states only, as the
game's political map does; Show tribes in its legend adds them (kept per machine). Cultures,
religions and areas are coloured so that neighbours differ and named where each is broadest.
Resources are coloured by family (crops, animals, the sea, cash crops, wood and stone, metals,
riches), mark gold, silver, gems, pearls and amber, and name each location's resource up close;
development and population fade into the physical map at their low end and write their values
up close; climate and terrain keep the full relief. Country borders come in on other lenses as
the map is brought closer. Ten lenses (keys 1–0; chosen in the inspector, or in the toolbar
while the inspector is hidden), country borders, names and location borders as overlays, one
search field over countries, cultures, religions, resources, areas and places, a legend that
previews on hover, isolates on click and zooms on double-click, a hover card and a pinned
location card whose values isolate their country, culture, religion, resource or area, a
minimap, zoom in the toolbar, map-only focus that keeps the view's centre, a PNG of the whole
lens as it is drawn (names included, one pixel per atlas pixel) and copying the current view.
Compare shows two worlds with linked cameras. The Qt window draws the same maps (kept lands and continent names included, §6).
The Tauri bridge reads and prepares the requested atlas on one cancellable background worker;
state snapshots and comparison eligibility inspect file metadata without decoding the library's
maps. Each viewer releases obsolete work when it switches or closes, including its relief and
region/sea-label Web Worker. Comparison panes can share a pending map without cancelling each
other. The bridge and viewer keep bounded LRU caches of four maps, keyed by file revision,
language and game; small inspector counts are kept separately. The loading indicator remains
live during that work; errors show the map's failure state and a later load can retry.
Progress snapshots for the same world keep its map, camera, pinned place/country card and
highlight. A change of world identity, atlas files, language or game restarts atlas loading.

[V-EXEC 2026-11-08] On the owner's 13-world library, a state snapshot took about 6.7 seconds
before removing the full-library atlas reads, and a median 2.9 ms afterwards. A bounded
protocol replay on a copy of that library delivered first atlas bundles in 0.35/0.75 seconds
and retained bundles in 0.16/0.21 seconds (including JSON serialization); six rapid requests
with cancellation delivered the last selection in 0.39 seconds and its bundle in 1.63 seconds.
These measure the Python protocol, excluding browser drawing and Tauri IPC. Synthetic tests
cover continued input/state delivery during a blocked load, cancellation, one reply per RPC,
shared comparison loads, LRU eviction, file/game/language invalidation and failure/retry.
Local evidence: `local_data/world-switching/measurement.json`.

**Keyboard.** Ctrl+N, Ctrl+O, Ctrl+Enter, Ctrl+, , Ctrl+B, Ctrl+I, Ctrl+V of a world code
anywhere, arrows in the library, `?` for the list. Every control is a native button/input or a
labelled slider role with a visible focus ring and a text label or `aria-label`; state is never
shown by colour alone.

**Verification.** `make desktop` (types, unit tests, build, Rust shell); `tests/test_bridge.py`
covers the protocol, state, atlas transfer and that every interface string key exists in the
window catalogues. Screens are reviewed in a browser through `npm run dev` with
`RNW_DATA=<copy of a library>` and in the built window on WebKitGTK.
After interface edits, rebuild the source window with `cd desktop && npx tauri build --no-bundle`
before `uv run rnw gui`. Package builds use separate output directories and do not refresh
the source checkout's window executable. Generation progress lists the phases of
`rnw.gui.phases` in the order they begin, each with its state (waiting, running, partly done while
it waits for another phase, done), the count of its stages that are done of those this world runs,
and the stages that run now; the world's kind (America alone, several continents, the real
Americas) and whether it is installed decide which stages count, and stage keys stay those of
`rnw.progress` (time estimate, timings, log). The line below the progress bar holds the phase
number, the time estimate and the queue count. The inspector's
bottom status uses the general generation/cancellation label and percentage, leaving stage names
in the main view.

**Time estimate.** `eta.py` predicts the remaining dependency path through the export's parallel
terrain and script branches, including the work between named stages and the optional installation.
Its initial costs are calibrated against the successful 230.9-second epoch-60 Linux generation
logged on 2026-10-31 (build 26300913), replacing the older fixed 120-second total. A stage's
cost runs from the end of its inputs, so the forecast places a stage that has not announced
itself yet at that moment too, never at "now". The vanilla reads follow the generated world (they
need its moved island groups), and the slot tables wait for the world checks. The shared
`Progress` owns a shown completion deadline and forecasts again on each poll. A forecast within
max(15 s, 10 % of the time left) changes only the pace: a later one holds the shown time still
until they meet, an earlier one counts down at double speed. A larger revision is shown at once.
An overdue stage therefore holds the countdown and then lets it fall slowly with its diminishing
tail; it no longer saws between two values. The timer does not claim completion before the
terminal stage finishes. Reading the map and choosing the canvas do not calibrate the machine's
speed: one waits for the disk, the other costs a few seconds or half a minute by preset.
The service stores the median of up to five successful stage costs in `generation-times.json` in
the application's data folder (up to sixteen schema/preset/build/epoch/platform/thread-limit
contexts). Input waits are excluded, and cache hits of the canvas or world, cancellation,
failure and waits for the game do not train expensive work. Timing data never enters generated
worlds or their reproducibility record. Both windows use this model, including the current world
in a queue; cancellation and waiting for the game hide ETA.

[V-EXEC 2026-11-08] The owner's continents generation (266.9 s, epoch 61, build 26377361)
showed the time cycling from 3:10 to 3:00 and back while the world was generated. A replay of its
logged stage ends reproduced the cycle (14 rises): the old graph started the vanilla reads beside
the world generation, so their forecast began "now" on each poll, and timing schema 1 had learned
them with the generation's time included (about 52 s instead of 2 s). Replaying the 93 fresh
generations in the owner's log (begins synthesized from the code's order, one poll per second):
rising ticks per run fell from 4.8 to 1.0 cold and from 5.3 to 0.5 when trained on the previous
run; mean absolute error went from 23.2 to 21.9 s and from 17.8 to 16.3 s. Excluding the map and
canvas from calibration took the cold error from 24.9 to 21.9 s. Timing schema 2 discards the
schema 1 history. Local evidence: `local_data/eta-sawtooth/`.

[V-EXEC 2026-10-31] Deterministic regressions cover overlapping inputs, slow machines, overruns,
cache hits, resets and optional timing storage. An offline replay of the recorded 245.6-second
The Wall export reduced mean absolute remaining-time error from 80.5 to 16.0 seconds and
increasing one-second ticks from 69 to 9 before training. Its stage starts/ends came from the
timing log; the final write interval was inferred from the terrain end and reported total.
Replaying that same trace after learning gives 0.4 seconds mean error, demonstrating calibration,
not cross-seed accuracy. No new world or EU5 session was needed. Local evidence:
`local_data/eta-ui/replay.json`; full checks and package installation are recorded in
[INSTALLED](../experiments/INSTALLED.md).

[V-EXEC 2026-10-30, 1.1.0 development] A Chromium comparison on the same 6,594-location
atlas measured a maximum 10 ms timer gap of 592 ms for synchronous relief/region names and
68 ms with the worker (total preparation 542/587 ms respectively). In the offscreen Qt window,
switching across four library worlds completed the last map in 3.98 s with a maximum timer
gap of 268 ms. These are local responsiveness observations, not loading-time guarantees.
Synthetic regressions cover deferred drawing, replacement of pending requests, nonblocking
build notes, hash invalidation and equality of prepared atlas fields. Evidence stays under
ignored `local_data/gui-finish/`; package verification and installation are in
[INSTALLED](../experiments/INSTALLED.md).
