# Generator window

## 0. Reference

This documents the existing Qt Widgets interface, extracted from `gui/window.py`,
`gui/maps.py` and `gui/preview.py`. ADR 0007 chooses the platform's controls and theme.
The owner's 2026-10-22 screenshots authorize reorganizing the interface around generation,
world management and application paths. Keep Qt Widgets and platform typography for the current implementation. The candidate Tauri window ([ADR 0011](adr/0011-tauri-window.md)) is described in §9; §1–§8 describe the Qt window, which stays current until the owner accepts the replacement.

## 1. Structure

A compact header identifies the game build; complete paths live in Settings. A horizontal
splitter holds the library and the selected page. New-world configuration tabs separate
world choices, exact values and delivery. Each tab owns one vertical scroll area. Only the
primary Generate action and a short status remain fixed below them; queue controls and
stage details are disclosed when requested. The library scrolls independently.
Worlds have an overview, maps, and personal notes. Secondary operations use dialogs.
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
accept and cancel actions. PreviewView handles map fit, zoom and pan. MapsPanel owns
layer selection, legend, search and location inspection. SettingsDialog owns application
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
The active world's Remove and Delete actions also apply to a multiple selection and show
its count. Batch errors remain visible below the list, including after a row disappears.

## 7. Surfaces

Use native window chrome, frames and separators. No web styling or additional shadows.

## 8. Accessibility and verification

Keep labels and tooltips meaningful, preserve native keyboard navigation, and avoid
colour as the only status signal. Exercise empty, busy, failed and completed states in
offscreen Qt tests. Capture the desktop window in light and dark themes for layout review.

## 9. The Tauri window (candidate)

**Look.** One design on every system: dark ink with brass accents, or parchment in light mode
(System/Dark/Light in Settings, kept per machine). Inter for text, Fraunces for titles and map
names, JetBrains Mono for codes; all bundled. Tokens live in `desktop/src/app.css`; components
use them rather than literal colours. Motion is short and disabled by `prefers-reduced-motion`.

**Structure.** A library sidebar (filter, All/In the game/Favourite, thumbnails, versions drawn
as branches under their world, Ctrl/Shift/checkbox multi-select with a batch bar, a global task
line and the game/profile chip) beside one page. The new-world page reads top to bottom (type
cards, world basics, seed and code, land sources, Customize, where to save) with a fixed dock:
location budget meter, summary, Generate, progress with ETA and stage timeline, outcome and
retry, queue. A world page has a picture banner, inline rename and favourite, the add/remove
action, and tabs: World (stats, next step, details and check, visibility, delete), Maps,
Create a version, Share and export, Notes. Messages that the Qt window wrote under a page are
toasts; questions are in-window dialogs.

**Maps.** Ten lenses (keys 1–0), country borders, names and location borders as overlays,
search over countries, cultures, religions, resources, areas and places, a legend that previews
on hover, isolates on click and zooms on double-click, a hover card and a pinned location card
whose values isolate their country, culture, religion, resource or area, a minimap, zoom
controls, map-only focus, PNG export of the exact lens and copying the current view. Compare
shows two worlds with linked cameras.

**Keyboard.** Ctrl+N, Ctrl+O, Ctrl+Enter, Ctrl+, , Ctrl+V of a world code anywhere, arrows in
the library, `?` for the list. Every control is a native button/input with a visible focus
ring and a text label or `aria-label`; state is never shown by colour alone.

**Verification.** `make desktop` (types, unit tests, build, Rust shell); `tests/test_bridge.py`
covers the protocol, state, atlas transfer and that every interface string key exists in the
window catalogues. Screens are reviewed in a browser through `npm run dev` with
`RNW_DATA=<copy of a library>` and in the built window on WebKitGTK.
