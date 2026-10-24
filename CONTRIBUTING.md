# Contributing to Random New World

Thank you for your interest! The project is in pre-release development (0.x), so the design still moves. For anything larger than a small fix, please **open an issue first** so we can agree on the approach before you write code.

## Ground rules

These rules come from the project's working rules in [AGENTS.md](AGENTS.md). Pull requests that break them cannot be merged.

1. **No game files, ever.** Do not commit anything from an EU5 installation, and do not commit anything derived from one: rasters, script excerpts, logs, saves, screenshots or generated worlds. Tests use **synthetic fixtures**. The gitignored folders `local_data/` and `generated/` exist for local material. In issues, share a **world code** rather than a world.
2. **Vanilla first, no crutches.** Use the game's own mechanisms and data wherever they fit, and generate only what the New World needs. Fix the generator so its output is correct by construction. Never add a layer that repairs or hides the generator's own output. Validators fail loudly; nothing silently falls back.
3. **Never edit the game installation**, and never touch existing mods, saves, settings or playsets outside a new `rnw_exp_*` folder.
4. **Deterministic output.** The same code, version and game build must produce identical bytes on every platform and with any thread count.
5. **Reverse-engineered formats are documented.** Every closed EU5 format the generator reads or writes is recorded in the [interoperability register](docs/research/interoperability.md) before it ships.

## Development setup

You need Python 3.12+, [uv](https://docs.astral.sh/uv/) and a stable Rust toolchain.

```sh
uv sync --locked --group dev    # builds the Rust extension (maturin) and installs the tools
make check                      # everything CI runs
```

`make check` runs `ruff format --check`, `ruff check`, `basedpyright` (strict), `pytest`, and `cargo fmt --check`, `cargo clippy -D warnings` and `cargo test` in `native/`. CI runs the same steps on Linux and Windows.

If you own the game, these optional read-only tests run against your installation and skip in CI:

```sh
EU5_GAME_DIR=/path/to/game uv run pytest -q tests/test_local_install.py
RNW_REPRODUCE=1 EU5_GAME_DIR=/path/to/game uv run pytest -q tests/test_local_install.py -k reference
```

The second test rebuilds the reference world and compares its digest. It takes about two minutes and needs 7.5 GiB of free memory.

## Changes to generated output

A change that alters what the generator writes must, **in the same commit**:

- raise at least the PATCH part of `version` in `pyproject.toml` ([ADR 0003](docs/adr/0003-versioning.md));
- update the golden digests the tests pin;
- if any file of a world's mod other than `.metadata` changes, start a new **algorithm epoch** in [`src/rnw/epoch.py`](src/rnw/epoch.py) and record the new reference world in `tests/golden_world.json` ([ADR 0010](docs/adr/0010-layered-worlds-and-a-generator-of-its-own.md)).

Add a [`CHANGELOG.md`](CHANGELOG.md) entry under *Unreleased*.

## Performance

Generation must run within EU5's minimum system requirements. A pass over the whole map is a regression: write it as a strip, a band or a kernel instead. A Rust kernel in `native/` must give the same bits as its Python reference in `tests/reference/`, with a test that proves it. A speed or memory change is proved by equal file hashes against a fresh reference export ([ADR 0005](docs/adr/0005-native-core.md), [ADR 0006](docs/adr/0006-machine-resources.md)).

## Evidence labels

Technical claims in the documentation say how they are known:

| Label | Meaning |
|---|---|
| `[V-GAME]` | Observed in the running game (name the game version) |
| `[V-LOCAL]` | Read from local game files (name the version) |
| `[V-EXEC]` | Result of our code or tests |
| `[SOURCE]` | External source (URL, date read, target version) |
| `[INFERRED]` | Reasoned from named premises |
| `[UNKNOWN]` | Not yet established |

Consequential claims get an entry in the [claims ledger](docs/research/claims-ledger.md). Syntax, loading and playable behaviour are separate claims, and one successful test on one game patch does not establish compatibility with the next.

## Documentation

- Record architectural decisions as an [ADR](docs/adr/). Mark a replaced ADR as superseded instead of deleting it.
- Keep design documents in [`docs/`](docs/) and in-game experiment records in [`experiments/`](experiments/).
- Write in English. Before 1.0.0, every player-facing string is translated into each of the game's official languages, which are read from the installed game ([roadmap](docs/roadmap.md) L1).

## Commits and pull requests

- Keep commits coherent and buildable, and make sure `make check` passes on each one.
- Write commit subjects in the imperative mood. Generator releases are prefixed with their version, for example `0.11.4: …`.
- **Sign off every commit** (`git commit -s`) to certify the [Developer Certificate of Origin](https://developercertificate.org/). The project accepts contributions under its licence (MPL-2.0) on that basis.
- Fill in the pull request template. Say how the change was verified, and whether it changes generated output.

## Reporting bugs

Use the [issue templates](https://github.com/Sir-Starch/eu5-random-new-world/issues/new/choose). The most useful information is:

- the generator version and the **world code**;
- the EU5 version and Steam build, the operating system, and whether the game runs through Proton;
- the diagnostics file: run `rnw diagnostics-file`, or use *Settings → Diagnostics* in the window. It packs the generator's logs, the tail of the game's logs and a short machine report. The home folder, user name, Steam account numbers and e-mail addresses are replaced with placeholders, and nothing is sent anywhere. Read it before you attach it.

Security problems are reported privately. See [SECURITY.md](SECURITY.md).

## Code of conduct

Everyone taking part is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
