# EU5 Random New World

Research and bootstrap repository for a future Europa Universalis V Random New World generator. The target is **genuinely generated geography and civilizations** with a historical Old World, not a shuffle of vanilla owners.

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

The coupling command performs a **broad lexical scan** with false positives; its raw output is gitignored [V-EXEC C10]. The fingerprint records hashes of the installed map-contract files without copying them [V-EXEC C20]. The corrected color audit finds 28,582 declarations, all 28,573 hierarchy keys covered, and nine declarations outside the hierarchy [V-EXEC C05]. A metadata-only validation kit is available with `uv run rnw prepare-mod generated/rnw_exp_001_metadata` and `uv run rnw install-mod generated/rnw_exp_001_metadata USER_DIR`. It does not edit playsets or launch the game. `rnw synth` writes a synthetic world (no game data). `rnw generate` refuses unknown build fingerprints (unless `--accept-build DIGEST`), existing outputs and paths outside `generated/`; it writes the mod plus `manifest.json`, `report.md`/`report.json`, `settings.json` and a local `preview.png`. Its outputs derive from game rasters and must stay local. `rnw newworld` takes about two minutes and 7 GiB of free memory on the continents preset: it reads the cores and the free memory of the machine and sizes its threads and working sets from them ([ADR 0006](docs/adr/0006-machine-resources.md)), refuses to start with less than 7 GiB free (`--ignore-memory` starts anyway), and gives the same files for any thread count (`RNW_THREADS`, `RNW_MEMORY` in MiB override the readings for benchmarks). Follow [testing](docs/testing.md) before any future in-game test and [INSTALLED](experiments/INSTALLED.md) for removal. No additional game launch is requested now.

## Document map

- [Findings](docs/research/findings.md), [claims ledger](docs/research/claims-ledger.md), [sources](docs/research/sources.md), [inventory](docs/research/game-install-inventory.md), [EU4 lessons](docs/research/eu4-rnw-analysis.md), [research log](docs/research/log.md)
- [Feasibility and tier matrix](docs/feasibility.md), [product spec](docs/product-spec.md), [architecture](docs/architecture.md), [ADR 0001](docs/adr/0001-python-research-tooling.md), [ADR 0002](docs/adr/0002-d0-generator-stack.md), [roadmap](docs/roadmap.md), [testing](docs/testing.md), [legal](docs/legal.md)
- [Implementation contract](docs/implementation-contract.md), [Opus handoff](docs/handoff/opus-5.5.md), [Sonnet backlog](docs/handoff/sonnet-5.5-backlog.md), [experiment records](experiments/)

The recommended direction is an **external deterministic generator emitting a complete per-build EU5 mod**, conditional on map override experiments. The runner-up is an ID-preserving geographic redraw if new IDs fail but boundary changes work [INFERRED C14]. Neither is yet proven in game.
