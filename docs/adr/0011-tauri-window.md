# ADR 0011: A Tauri window over a Python bridge

**Status:** Implemented as a candidate on 2026-10-29 at the owner's request; not yet the
shipping window. Qt ([ADR 0007](0007-application-window-and-packaging.md)) remains current
until the owner accepts the Tauri window and its delivery. Hub/Workshop packaging is not
changed by this record.

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
- **Self-contained look.** Inter, Fraunces and JetBrains Mono are bundled; the web view makes
  no network requests (CSP allows only the app's own files, data images and Tauri IPC).

## Consequences

The Linux release binary is about 6 MB plus about 0.8 MB of interface files, against Qt's
roughly 100 MB of libraries; the Python generator is still required beside it. Linux needs
WebKitGTK 4.1, Windows needs WebView2. The Workshop hub currently runs through Proton for some
players; WebView2 under Wine/Proton is an unmeasured risk [UNKNOWN] and must be checked before
the hub switches windows. Cross-building the Windows shell, the launcher change and the hub
layout are follow-up delivery work, decided with that evidence.

The dev server (`npm run dev`) relays the same protocol over a local WebSocket for browser
testing; the packaged window opens no port.
