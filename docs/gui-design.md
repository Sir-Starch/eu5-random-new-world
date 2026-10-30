# Generator window

## 0. Reference

This documents the existing Qt Widgets interface, extracted from `gui/window.py`,
`gui/maps.py` and `gui/preview.py`. ADR 0007 chooses the platform's controls and theme.
The owner's 2026-10-22 screenshots authorize reorganizing the interface around generation,
world management and application paths. The Tauri window ([ADR 0011](adr/0011-tauri-window.md)), the generator's window since 2026-10-30, is described in §9; §1–§8 describe the classic Qt window, its fallback, which keeps Qt Widgets and platform typography.

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

Long work runs through Controller's cancellable worker and reports completion or an
error. A failed or cancelled queue stops before the next item. Candidate previews are
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
Generation suspends polling. Metadata-first copies can gain their verified atlas/record
when the rest arrives, preserving personal fields. Refreshing or renaming preserves
selection and unsaved notes.
Game-build comparisons run on one background worker with a visible checking note. Unchanged
file hashes (where change timestamps are available) and the game's name catalogue are reused.
Classic maps are drawn only when their tab is visible, on one drawing worker; while it works,
only the latest requested picture waits.
A loading notice stays over the map until that picture arrives; stale deliveries are ignored.
The active world's Remove and Delete actions also apply to a multiple selection and show
its count. Batch errors remain visible below the list, including after a row disappears.

## 7. Surfaces

Use native window chrome, frames and separators. No web styling or additional shadows.

## 8. Accessibility and verification

Keep labels and tooltips meaningful, preserve native keyboard navigation, and avoid
colour as the only status signal. Exercise empty, busy, failed and completed states in
offscreen Qt tests. Capture the desktop window in light and dark themes for layout review.

## 9. The Tauri window

**Look.** A workbench that sits beside the game, the same on every system (owner reviews
2026-10-30: the first candidate read as a website, the second as the old layout repainted).
Neutral greys with one blue accent for selection, focus and the primary action; light and dark
(System/Dark/Light in Settings, kept per machine). Noto Sans 13 px for text and map names,
JetBrains Mono for codes; both bundled. Every pane starts with a 32 px header, so the library's
title, the view's title and tools and the inspector's tabs read as one band. Controls are 24–26 px
high with 3 px corners; panels are flat and divided by hairlines, without cards, gradients, glows
or blur; the middle is a darker canvas. An exact value is a bar filled to its value with a tick at
the world type's value: drag it, click to type, step with the arrow keys, Backspace resets.
Icons are a small 16-unit, one-pixel set used only in toolbars and icon buttons; other buttons
carry text. Tokens live in `desktop/src/app.css`; components use them rather than literal
colours. The only motion is the busy spinner. Default window 1160×740, minimum 860×560.

**Structure.** Three panes over a status bar: the library (filter with All/In the game/Favourite,
New world as its first row, thumbnails, versions drawn as branches under their world,
Ctrl/Shift/Ctrl+A multi-select with Remove/Delete below), a view in the middle and an inspector.
Both side panes are resizable and hide (Ctrl+B, Ctrl+I, the buttons at the ends of the status
bar); their widths are kept per machine. The status bar shows the game and profile, the running
task and the machine's resources. For a world, the middle is its map, or its mod picture with
Reveal while the map is covered; the inspector's tabs are World (name, favourite, place in the
game with add/remove and folder, advice, then folding sections for details and check,
visibility, Create a version, Share and export; delete last), Maps and Notes. For the new world,
the middle shows its land: continent sketches to pick from (the chosen one is marked), the land
image, or a blank sheet ruled like a map; while a world is made, its progress, stages, ETA and
Cancel; afterwards the outcome with Open the world or a retry. The inspector's tabs are World
(type and basics as lists, oceans, seed and code), Advanced (exact values by group) and Save and
play (destination, install, visibility, queue); under every tab stay the location budget, Add to
queue and Generate. Folded sections stay folded. Messages that the Qt window wrote under a page
are toasts; questions are in-window dialogs.

**Maps.** The physical map is the default lens and the ground under every other (owner review
2026-10-30: the physical map had become less beautiful, tribes were mixed with countries and
resource names hung anywhere). It is drawn from the atlas, which holds no heightmap: vegetation
and climate colours softened across locations, relief shaded from each location's topography
and roughened where it is mountainous, wetlands and snow, water darkening from the coast into
the open ocean around the New World, region and sea names, cities and towns. The other lenses
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
Compare shows two worlds with linked cameras. The Qt window keeps its own flat pictures.
The Tauri atlas cache prepares relief and region/sea labels in one Web Worker before handing
the atlas to its renderer. The loading indicator remains live during that work; errors show
the map's failure state and a later load can retry.

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
the source checkout's window executable. Generation progress lists stage names in its stage
table; the line below the progress bar holds the time estimate and queue count.

[V-EXEC 2026-10-30, 1.1.0 development] A Chromium comparison on the same 6,594-location
atlas measured a maximum 10 ms timer gap of 592 ms for synchronous relief/region names and
68 ms with the worker (total preparation 542/587 ms respectively). In the offscreen Qt window,
switching across four library worlds completed the last map in 3.98 s with a maximum timer
gap of 268 ms. These are local responsiveness observations, not loading-time guarantees.
Synthetic regressions cover deferred drawing, replacement of pending requests, nonblocking
build notes, hash invalidation and equality of prepared atlas fields. Evidence stays under
ignored `local_data/gui-finish/`; package verification and installation are in
[INSTALLED](../experiments/INSTALLED.md).
