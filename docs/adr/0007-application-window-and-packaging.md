# ADR 0007: The application window is Qt, packaged with PyInstaller

**Status:** Qt window choice implemented and current in 1.0.0. Windows delivery is governed by [ADR 0009](0009-hub-mod-with-generator.md), replacing this record's earlier packaging scope. Native/development builds still use PyInstaller. The earlier owner-direction history is in [the archived roadmap](../archive/roadmap-through-1.0.md).

The existing application still uses Qt. On 2026-10-28 the owner requested a transition to Tauri; [ADR 0011](0011-tauri-window.md) records the implemented candidate. This decision stays current until the owner accepts that window and its delivery.

## Context

ADR 0004 requires a window for Windows and Linux with game and profile discovery, presets, a seed that can be copied and pasted, a preview, progress per stage with a cancel button, validation and installation, and no terminal and no Python for the player. The core for all of that exists without a toolkit (`rnw/app/`: discovery, world codes, history, installation, a generate service with progress and cancel). What remains is a window and a package.

## Evidence (Linux, 2026-10-21; Windows is for CI to repeat)

- **Package.** PyInstaller 6 builds the command line (`rnw`, with the Rust extension, NumPy, Pillow and Typer) as a folder of 102 MB that starts in 0.16 s and, run as `rnwcli world RNW1-…`, writes the same 733 files as the Python build (97 s, 7.8 GiB peak) [V-EXEC].
- **Qt.** A window with a progress bar, a list and a button built with PySide6-Essentials runs offscreen, and frozen with PyInstaller is a folder of 214 MB that starts in 0.4 s [V-EXEC]; with the generator in the same folder the window application built by `packaging/build.py` is 246 MB (Qt 97 MB, NumPy and its BLAS 41 MB, Python 31 MB, a second ICU 32 MB and Pillow's libraries 11 MB), starts, and passes `--self-test` (window, native kernels, world codes) from the folder [V-EXEC].
- **Tk.** `tkinter` 8.6 is in the interpreter that `uv` provides [V-EXEC]; it adds about 10 MB to a package, has no image zoom and no per-monitor scaling without work, and its look on Linux is dated.
- Not measured: Dear PyGui (immediate-mode, own look, no accessibility), a web page served on localhost (not a window; browsers, ports and firewalls become the player's problem), pywebview (needs WebView2 or WebKitGTK on the player's system).

## Decision

- **Toolkit: PySide6 (Qt for Python), the Essentials wheel.** It gives native file dialogs and clipboard, high-DPI handling, an image view with zoom for the preview, threads with queued signals for progress, and the same behaviour on Windows and Linux. Its LGPL-3.0 licence allows an application that ships the Qt libraries as separate files in the package, with the licence text and a link to the Qt sources in the package ([legal](../legal.md)); the project's own licence is still the owner's decision.
- **Layers.** `rnw/app/` (no toolkit) holds every rule; `rnw/gui/controller.py` holds the window's state and the generation lifecycle without importing Qt, so it is tested without a display; `rnw/gui/window.py` draws it. The generation runs in a thread of its own; progress reaches the window by signal; the window never waits on the generator.
- **Package: PyInstaller, folder mode,** built by a script in `packaging/` and by CI jobs on Windows and Linux (artifacts only; nothing is published). Windows ships a folder with `RandomNewWorld.exe`; Linux a folder or tarball. An installer, an AppImage and code signing (without it Windows SmartScreen warns on first start) wait for the publication decision (P1) [UNKNOWN].
- **Dependencies.** `PySide6-Essentials` is an optional group `gui` of the project and is in the `dev` group so the window is tested in CI; the generator and the command line need none of it.

## Consequences

The package is about 250 MB (PyInstaller folder, Qt included). `packaging/layout.py` already leaves out the Qt modules the window does not import and the build machine's GTK libraries; the translations (7 MB), a second ICU copy that the system `libxml2` pulls in (32 MB) and the Wayland plugins are the next candidates once Windows sizes are known. Every behaviour of the window is a call of a tested core function, so a different toolkit would replace one file. Strings live in one module so a translation can be added. A world preview before the 90-second generation is a core feature still to build; until then the window shows the finished preview image.
