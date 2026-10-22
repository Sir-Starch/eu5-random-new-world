# Generator window

## 0. Reference

This documents the existing Qt Widgets interface, extracted from `gui/window.py`,
`gui/maps.py` and `gui/preview.py`. ADR 0007 chooses the platform's controls and theme.
The owner's 2026-10-22 screenshots authorize reorganizing the interface around generation,
world management and application paths. Keep Qt Widgets and platform typography.

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

## 7. Surfaces

Use native window chrome, frames and separators. No web styling or additional shadows.

## 8. Accessibility and verification

Keep labels and tooltips meaningful, preserve native keyboard navigation, and avoid
colour as the only status signal. Exercise empty, busy, failed and completed states in
offscreen Qt tests. Capture the desktop window in light and dark themes for layout review.
