# EU5 Random New World

**Shader regression, 2026-10-22:** the owner confirms full New World concealment in
0.9.26, but loading art and character backgrounds fail [V-GAME owner / V-LOCAL C153].
Generator **0.9.27** isolates the cover in a private map-mesh include and restores the
vanilla dependency graphs for loading and scene shaders; offline checks pass, while
the running-game retest remains open [V-EXEC / UNKNOWN C154]. See
[experiment 027](experiments/027-map-shader-scope/README.md).

Research and bootstrap repository for a future Europa Universalis V Random New World generator. The target is **genuinely generated geography and civilizations** with a historical Old World, not a shuffle of vanilla owners.

**Cover failure, 2026-10-22:** the owner's EU5 1.4.3 test of a 0.9.20 world reveals
trees, rivers, resources and cities at close zoom and allows starting as a covered
New World country [V-GAME owner / V-LOCAL C150]. The political-lens success of C139
does not cover these routes. Follow-up: [experiment 026](experiments/026-close-zoom-cover/README.md).
Generator **0.9.26** adds an expanded cover and lobby UI safeguards, verified offline
against the exact installed build [V-EXEC C151]. Native map picking is not intercepted;
the new concealment and UI start guards require an in-game retest [UNKNOWN].

**Patch check, 2026-10-22:** generator **0.9.25** accepts the locally checked **1.4.3 open beta, Steam build 26105915**. The installation tests and a full reference-world export pass offline; the output preserves pixels outside the canvas and loses no Old World contacts [V-LOCAL/V-EXEC C148–C149]. Worlds built from 1.4.2 should be regenerated because their full-file overrides can undo patch changes [INFERRED C148]. **1.4.3 loading and playability remain unverified**; EU5 was not launched. See [the patch record](experiments/025-patch-1-4-3/README.md). The dated entries below describe earlier milestones.

**Actual status, 2026-10-13:** Local EU5 is the Steam `1.4-open-beta` branch, build 25905365, running as **1.4.1** through Proton [V-LOCAL C01; V-GAME C02]. An isolated metadata-only `rnw_exp_*` mod was recognized and version-matched in the game log [V-GAME C11], but complete error-free loading, content override, changed start state, boundaries, new locations and playability remain unverified [UNKNOWN C13]. The isolated profile opened an unresponsive first-run Select Language screen, so the game was closed and **will not be launched again in this session** at the owner's request [V-GAME C12]. The full result of experiment 001 is **INCONCLUSIVE**; experiments 002–006 are **NOT-RUN**.

**Update, 2026-10-14:** the first deterministic geography generator exists offline. `rnw generate` stages an `rnw_exp_*` mod candidate that moves real land–sea boundaries between existing American location IDs while preserving the Old World and every cell contact; it is reproducible byte for byte and **NOT GAME VALIDATED** [V-EXEC C28–C30]. See [ADR 0002](docs/adr/0002-d0-generator-stack.md).

## Setup and checks

Python 3.12+ and [`uv`](https://docs.astral.sh/uv/) are required. From the repository root:

```sh
uv sync --locked --group dev
make check
uv run rnw --help
```

`make check` runs Ruff formatting/lint, basedpyright and pytest. CI runs the same checks on Linux and Windows. Without game files, the local-installation test skips automatically. With an installed game, read-only inspection is available:

```sh
EU5_GAME_DIR='/path/to/Europa Universalis V'
uv run rnw inspect "$EU5_GAME_DIR"
uv run rnw coupling "$EU5_GAME_DIR" local_data/coupling.json
uv run rnw fingerprint "$EU5_GAME_DIR" local_data/map-contract.json
uv run rnw synth --seed 1 --preset archipelago --output generated/rnw_synth_demo
uv run rnw newworld --game-dir "$EU5_GAME_DIR" --seed 42 --preset continents --output generated/rnw_exp_new_world --replace
uv run rnw install-mod --replace generated/rnw_exp_new_world/rnw_exp_new_world "$EU5_USER_DIR"
EU5_GAME_DIR="$EU5_GAME_DIR" uv run pytest -q tests/test_local_install.py
```

The coupling command performs a **broad lexical scan** with false positives; its raw output is gitignored [V-EXEC C10]. The fingerprint records hashes of the installed map-contract files without copying them [V-EXEC C20]. The corrected color audit finds 28,582 declarations, all 28,573 hierarchy keys covered, and nine declarations outside the hierarchy [V-EXEC C05]. A metadata-only validation kit is available with `uv run rnw prepare-mod generated/rnw_exp_001_metadata` and `uv run rnw install-mod generated/rnw_exp_001_metadata USER_DIR`. It does not edit playsets or launch the game. `rnw synth` writes a synthetic world (no game data). `rnw generate` refuses unknown build fingerprints (unless `--accept-build DIGEST`), existing outputs and paths outside `generated/`; it writes the mod plus `manifest.json`, `report.md`/`report.json`, `settings.json` and a local `preview.png`. Its outputs derive from game rasters and must stay local. `rnw newworld` takes about a minute and a half and 7.5 GiB of free memory on the continents preset: it reads the cores and the free memory of the machine and sizes its threads and working sets from them ([ADR 0006](docs/adr/0006-machine-resources.md)), refuses to start with less than 7.5 GiB free (`--ignore-memory` starts anyway), and gives the same files for any thread count (`RNW_THREADS`, `RNW_MEMORY` in MiB override the readings for benchmarks). Follow [testing](docs/testing.md) before any future in-game test and [INSTALLED](experiments/INSTALLED.md) for removal. No additional game launch is requested now.

The application window (Qt) opens with `uv run --group gui rnw gui`; `uv run rnw world-code --seed 42` prints a world code and `uv run rnw world CODE` makes that world headless (it installs into the game profile only with `--install`). `uv run --group packaging python packaging/build.py` freezes the window into `dist/RandomNewWorld` ([ADR 0007](docs/adr/0007-application-window-and-packaging.md)).

## Licence

Code and mod files are under the [Mozilla Public License 2.0](LICENSE) ([why](docs/legal.md)). Generated worlds are made locally from the player's own EU5 installation and are not covered by it; they are never distributed.

## Document map

- [Findings](docs/research/findings.md), [claims ledger](docs/research/claims-ledger.md), [sources](docs/research/sources.md), [inventory](docs/research/game-install-inventory.md), [EU4 lessons](docs/research/eu4-rnw-analysis.md), [research log](docs/research/log.md)
- [Feasibility and tier matrix](docs/feasibility.md), [product spec](docs/product-spec.md), [architecture](docs/architecture.md), [ADR 0001](docs/adr/0001-python-research-tooling.md), [ADR 0002](docs/adr/0002-d0-generator-stack.md), [roadmap](docs/roadmap.md), [testing](docs/testing.md), [legal](docs/legal.md)
- [Implementation contract](docs/implementation-contract.md), [Opus handoff](docs/handoff/opus-5.5.md), [Sonnet backlog](docs/handoff/sonnet-5.5-backlog.md), [experiment records](experiments/)

The recommended direction is an **external deterministic generator emitting a complete per-build EU5 mod**, conditional on map override experiments. The runner-up is an ID-preserving geographic redraw if new IDs fail but boundary changes work [INFERRED C14]. Neither is yet proven in game.
