# ADR 0011: A Tauri window over a Python bridge

**Status:** Accepted 2026-10-30. Implemented as a candidate on 2026-10-29; the owner made it
the generator's window on 2026-10-30, keeping the Qt window ([ADR 0007](0007-application-window-and-packaging.md))
as the classic fallback. The hub and the native packages carry it (Delivery below).

## Context

The owner asked for a complete interface rework on Tauri that looks the same on every system,
resolves the Qt window's usability problems and improves the interactive maps and lenses
([roadmap](../roadmap.md)). The generator, library, atlas, recovery and installation rules are
Python, and `rnw/gui/controller.py` already holds the window's state and lifecycle without Qt.
Rewriting those rules in Rust or TypeScript would duplicate tested behaviour.

## Decision

- **Shape.** `desktop/` holds a Svelte 5/TypeScript interface (Vite) and a Rust Tauri 2 shell
  (`desktop/src-tauri`). The shell starts `python -m rnw.gui.bridge` as a child process and
  relays JSON lines: the web view's `invoke("rpc", {method, params})` becomes a request, and the
  bridge's `state` events become `rnw://state` events. Closing the window closes the bridge's
  input; the bridge cancels running work and waits for it, as the Qt window did on close.
- **One controller.** `rnw/gui/bridge.py` maps each request to the same `Controller` method a Qt
  button calls and returns its problem string. `rnw/gui/view.py` serializes the state the window
  draws, with every displayed sentence already in the window's language; the static string
  table (`text.table()`) comes from the same `window` catalogues. A language change applies at
  once rather than at the next start.
- **Maps.** `atlas.lens()` gives per-location colours, legend classes and border values for
  every layer; the existing `render`/`legend` are unchanged byte for byte for the six original
  layers. Population, climate, terrain and areas are new layers available to both windows, the
  PNG export and the CLI. The viewer unrolls the atlas's run-length labels into a WebGL 2 integer
  texture and paints lenses, borders, search/legend isolation and hover/pin outlines per screen
  pixel; without WebGL 2 it draws the same colours on a canvas.
- **Locating the bridge.** `RNW_PYTHON` names an interpreter; else a packaged
  `generator/python` beside the program is run isolated (`-B -I`); else a source checkout runs
  through `uv`. `RNW_DATA` selects the library folder. `--self-test` starts the bridge, asks for
  the first state and exits without a window.
- **Self-contained look.** Noto Sans and JetBrains Mono are bundled; the web view makes
  no network requests (CSP allows only the app's own files, data images and Tauri IPC).
- **One map look.** The lenses' palettes, water and physical colours and per-lens profiles
  are `rnw/gui/lenses.json`, imported by the interface and read by `rnw.gui.mapstyle`, which
  draws the same maps for the classic window on the processor (the fallback under Proton).
- **Delivery.** `rnw.gui` (`rnw.gui.start`) opens the window and waits for it; it imports no
  Qt until it needs the classic window. The window is `generator/window/random-new-world.exe`
  in the hub (cross-built with the GNU toolchain, with Microsoft's `WebView2Loader.dll` beside
  it) and `window/random-new-world` in a native package, which serves the bridge as
  `RandomNewWorld --bridge`. The packages build it with `tauri build --no-bundle` (a plain
  `cargo build` makes a development program that looks for the dev server) and carry the
  licences of its crates and npm packages under `licenses/window`. The classic window opens
  when it is chosen (`--classic`, `RNW_WINDOW=classic`, or *Use the classic window* in either
  window's Settings, kept in `preferences.json`) or when the window cannot open: it is
  missing, cannot start (no WebKitGTK 4.1), exits with code 3 because there is no web view
  (it checks for WebView2 before making any window, so Tauri's own error box never shows) or
  stops with an error within 20 seconds. `--self-test` checks both windows; a package without
  the Tauri window fails it.

## Consequences

The window program is about 6 MB on Linux and 4.4 MB on Windows, with the interface built in;
the Python generator and the classic window's Qt stay in the packages. Linux needs WebKitGTK
4.1, Windows needs the WebView2 runtime, which Windows 11 and current Windows 10 have. EU5's
Proton prefix has no WebView2 runtime [V-LOCAL 2026-10-30], so the hub run through Proton opens
the classic window: under Wine 11.20 without WebView2 the window exits with code 3 and the Qt
window opens with no error box, and the hub's self-test passes both windows [V-EXEC C444].
Whether the window works in a Proton prefix with WebView2 installed is [UNKNOWN]; native Linux
players get it from the Linux package. The real window was checked on WebKitGTK 2.54 in a
headless KWin, from source and from the native package [V-EXEC C444]; Windows itself and
macOS are checked by CI's self-tests (bridge, no window).

The dev server (`npm run dev`) relays the same protocol over a local WebSocket for browser
testing; the packaged window opens no port.
