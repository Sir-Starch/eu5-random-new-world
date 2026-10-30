# Verification during development

Use the checks that establish the behavior changed by the task. Historical
experiment statuses retain their date/build; they are not an instruction to
rerun all experiments or reopen release acceptance. The owner has accepted 1.0.0
(C437); its tagged CI and published downloads are checked (C439).

## Choose checks by change

| Change | Useful verification |
|---|---|
| Documentation only | Read the changed current guidance, validate local links/anchors and examples; generated documentation checks if relevant |
| Application or packaging code | Relevant regression tests, then locked sync and `make check`; packaged generator self-test for affected layouts |
| Generated world output | Synthetic regressions, affected goldens, installed-game reference/output checks and epoch policy in ADR 0003 |
| Performance or parallel kernels | Equality with `tests/reference/`, thread-count parity and a relevant resource measurement |
| Game patch or serializer input contract | Installed version/build, input fingerprint and changed-file inspection; relevant read-only game tests |
| A specific engine-only question | Existing owner logs/saves first; one bounded owner sitting only if the task depends on evidence unavailable offline |

Run the full code/package checks once after the implementation stabilizes. Repeat
when new code, failures or unresolved concerns justify it. A documentation edit
needs no binary rebuild, VirusTotal resubmission, reference export or profile update.

## Commands

```sh
uv sync --locked --group dev
make check
uv run rnw --help
```

`make check` runs formatting, lint, strict Python types, Python tests, Rust format,
clippy and tests. `make desktop` checks the Tauri window (ADR 0011): Svelte/TypeScript types, Vitest, the
production build and the Rust shell's format, clippy and tests. Run
`RNW_DATA=/path/to/library-copy npm run dev` in `desktop/` to review it in a browser. After
`npx tauri build --no-bundle` in `desktop/`, `uv run rnw gui` opens that build and
`QT_QPA_PLATFORM=offscreen uv run python -m rnw.gui --self-test` checks both windows; package
self-tests require the Tauri window. The real window can be captured without a display in
`dbus-run-session kwin_wayland --virtual` with `spectacle -b -n -f`. CI runs Linux/Windows checks and package self-tests. The 1.0.0
verification passed 2,142 Python tests with 14 optional skips and 23 Rust tests
(C438); these are a dated baseline, not permanent expected test counts.

Optional read-only game-input checks:

```sh
EU5_GAME_DIR=/path/to/game uv run pytest -q tests/test_local_install.py
RNW_REPRODUCE=1 EU5_GAME_DIR=/path/to/game uv run pytest -q tests/test_local_install.py -k reference
RNW_LAYERS=1 EU5_GAME_DIR=/path/to/game uv run pytest -q tests/test_local_install.py -k layers
```

The reference export compares the current epoch's output with
`tests/golden_world.json` (pending epoch 60 for the 1.1.0 cycle). The frozen
epoch-59 reference is preserved in `tests/golden_world_epoch59.json`. The layer check compares land/resources/peoples
rerolls. They take substantially longer than synthetic tests and need the local
game inputs; use them when those outputs are affected. Do not rewrite a frozen
epoch's reference to make a failure pass. See [ADR 0003](adr/0003-versioning.md).

Tests use synthetic fixtures in Git. Actual game rasters, saves, logs and exports
stay local. `tests/test_native.py` compares native kernels with independent
references. Content, localization, world-code, library/recovery, path safety and
packaging have subsystem tests in `tests/`; consult current test files rather
than a historical catalogue of file names. `docs/build_content_reference.py --check`
checks the generated content reference.

## Packages and engine observations

The generator's `--self-test` exercises the window, native kernels and world
codes without launching EU5. The release workflow runs native and Windows-layout
self-tests and archive allowlist/checksum checks. Self-tests do not establish all
engine behavior; owner sessions and their logs supply that separate evidence.
Synthetic cross-platform goldens are checked in CI. Real-world reproduction also
records the game inputs and image encoding/pixel digests; do not broaden a result
beyond what its actual comparison measured.

Agents must not launch or control EU5, its console or its playsets. If new game
observation is necessary, prepare a normal generated world with its library and
recovery receipt. Give the owner a short combined sitting, with console shortcuts
where practical, then read the complete relevant logs yourself. Capture the exact
RNW version/code, EU5 build and scope of the observation. Preserve existing worlds
and saves. No standalone probe/companion mods, campaign-length requests or automatic
owner-test to-do list follows from an `UNKNOWN` entry.

A log warning is a lead until attributed: compare a suitable vanilla/session
baseline and reproduce the affected behavior. A concrete failing invariant or
reproducible RNW defect needs a fix; an unrelated inherited warning does not prove
one. Historical reproductions remain in [experiments](../experiments/README.md),
[research](README.md#research-and-evidence) and the
[archived validation protocol](archive/validation-protocol-0.x.md).
