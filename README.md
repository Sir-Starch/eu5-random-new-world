# EU5 Random New World

Research and bootstrap repository for a future Europa Universalis V Random New World generator. The target is **genuinely generated geography and civilizations** with a historical Old World, not a shuffle of vanilla owners.

**Actual status, 2026-10-13:** Local EU5 is the Steam `1.4-open-beta` branch, build 25905365, running as **1.4.1** through Proton [V-LOCAL C01; V-GAME C02]. An isolated metadata-only `rnw_exp_*` mod was recognized and version-matched in the game log [V-GAME C11], but complete error-free loading, content override, changed start state, boundaries, new locations and playability remain unverified [UNKNOWN C13]. The isolated profile opened an unresponsive first-run Select Language screen, so the game was closed and **will not be launched again in this session** at the owner's request [V-GAME C12]. The full result of experiment 001 is **INCONCLUSIVE**; experiments 002–006 are **NOT-RUN**. No RNW generator exists yet.

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
EU5_GAME_DIR="$EU5_GAME_DIR" uv run pytest -q tests/test_local_install.py
```

The coupling command performs a **broad lexical scan** with false positives; its raw output is gitignored [V-EXEC C10]. A metadata-only validation kit is available with `uv run rnw prepare-mod generated/rnw_exp_001_metadata` and `uv run rnw install-mod generated/rnw_exp_001_metadata USER_DIR`. It does not edit playsets or launch the game. Follow [testing](docs/testing.md) before any future in-game test and [INSTALLED](experiments/INSTALLED.md) for removal. No additional game launch is requested now.

## Document map

- [Findings](docs/research/findings.md), [claims ledger](docs/research/claims-ledger.md), [sources](docs/research/sources.md), [inventory](docs/research/game-install-inventory.md), [EU4 lessons](docs/research/eu4-rnw-analysis.md), [research log](docs/research/log.md)
- [Feasibility and tier matrix](docs/feasibility.md), [product spec](docs/product-spec.md), [architecture](docs/architecture.md), [ADR](docs/adr/0001-python-research-tooling.md), [roadmap](docs/roadmap.md), [testing](docs/testing.md), [legal](docs/legal.md)
- [Opus handoff](docs/handoff/opus-5.5.md), [Sonnet backlog](docs/handoff/sonnet-5.5-backlog.md), [experiment records](experiments/)

The recommended direction is an **external deterministic generator emitting a complete per-build EU5 mod**, conditional on map override experiments. The runner-up is an ID-preserving geographic redraw if new IDs fail but boundary changes work [INFERRED C14]. Neither is yet proven in game.
