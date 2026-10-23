# EU5 Random New World

**0.10.8, 2026-10-23:** four more families of formable countries (N4 of the [content plan](docs/content-plan.md), first version): beside the river-basin union a world now offers, where its land and peoples allow, a *Highland confederation* (connected valleys on high ground), a *Maritime league* (ports joined by land or by a shared sea, with at least three ports), a *Cultural commonwealth* (the places of one culture group) and a *Regional realm* (a large region under several states). Each is a formable of a new tag with its own territory, level, rank, flag and founding modifier copied from a vanilla one (C212-C214). Epoch 18; not yet seen in game.

**0.10.7, 2026-10-23:** [V-GAME C205-C208] the owner's second sitting showed that the flicker of the lobby's country list was not the percentage size: the list as a vertical list of every card still flickered and a search brought back blank stretches. The list is now the game's own fixed grid again and the countries of the New World are **dimmed and cannot be chosen** instead of hidden (their names show in the list). The start hook through `on_actions` works beside the game's start (C206), and a plain vassal keeps the name of its location (C207): the probe now founds a `colonial_nation`. Epoch 17, reference world of 784 files. [V-GAME C209-C211] the owner's third sitting: the countries no longer flicker, and a colony founded by a decision is a *Colony of Interlaken* (the game's own name, not a scripted one); [experiment 038](experiments/038-lobby-list-and-colony/README.md).

**0.10.6, 2026-10-23:** [V-GAME C198-C204] the owner's console sitting on **1.4.4** (the game's executable was updated that morning; its data is 1.4.3's and the generator accepts it unchanged) showed which hooks a mod has (a formable of a new tag, a dynamic start, the yearly pulse) and found faults of ours, fixed here: the lobby's country cards had a percentage size that the engine refuses in a `vbox` (flags flickered; cause [INFERRED]), two DLC picture files compared with removed locations 79,000 times in a session, the river story removed a location modifier in the wrong scope, and the unions and the probe's decisions lacked the keys the game looks up. The probe's own `on_game_start` had replaced the game's start in that sitting; it now hooks it as the game does. Epoch 16, reference world of 784 files. [UNKNOWN] whether the flicker is gone: [experiment 037](experiments/037-console-session-2/README.md).

**0.10.5, 2026-10-23:** the content model and the first stories (N3 of the [content plan](docs/content-plan.md)): each world offers, where its land and peoples allow, a *River centre* (a river city turned against by its river), a *Sacred centre* (a shrine and its high priest) and a *River-basin union* (a formable of a new tag), each with choices, costs and endings, and records why a family has none; original texts and mechanics copied from the retired historical chains (C193-C196). Epoch 15; not yet seen in game.

**0.10.4, 2026-10-23:** the five historical natural-resource bonuses that vanished with the Americas (Potosí's silver, the mercury mine, the fisheries) come back as five rare places of the generated land: silver in the mountains, a mercury lode, a rich fishery, each with a modifier and names of the mod's own and the vanilla bonus size; they belong to the resources part of the world (C189, C190). This completes N1 of the [content plan](docs/content-plan.md) offline; not yet seen in game.

**0.10.3, 2026-10-23:** the decisions of N0 are carried out: the American historical events, colonial names (New Spain, Peru, New York and others), the three colonial formables and the Panama canal are switched off on generated land by closing the gates vanilla gives them; the historical formables whose culture the world holds (Inca, Aztec, Maya, Iroquois, Pueblo) take the places of that culture as territory, and close when the culture is thin (C187, C188). Epoch 13; not yet seen in game. The exceptional resource places of the same stage follow.

**0.10.2, 2026-10-23:** [OWNER] the mod uses exactly the game's official languages, taken from the installation; the world's name files are now written in all eleven of 1.4.3, Turkish included, which the fixed list of ten missed (C178, C186). [V-EXEC] Epoch 12, reference world of 754 files; the first step of N1 of the [content plan](docs/content-plan.md), not yet seen in game.

**0.10.1, 2026-10-23:** [V-GAME owner C173] the 0.10.0 cover shows vanilla terra-incognita drawings, including dragons, but its country-list filter did not remove the large blank region. [V-EXEC C174] The new candidate replaces fixed country rows with a vertical list that excludes invisible widgets from layout and removes the ineffective filter. [UNKNOWN] The engine's layout behavior awaits the owner's run of [experiment 032](experiments/032-lobby-list-layout/README.md); no agent game launch. The earlier undiscovered-capital warnings are gone from the owner's log (C171).

**Opinions, 2026-10-23:** the opinions of the great empires named capitals that their holders had not discovered, 17 warnings per start (C170); generator **0.9.33** makes each holder discover its partner's capital area and checks it on the written records (C171); not yet seen in game.

**Map frame, 2026-10-23:** at country selection the cover of the New World reached beyond the map's north and south edges and cut the wooden table of the frame black over the New World's longitudes (C169); generator **0.9.32** (epoch 8) keeps the cover on the map; not yet seen in game ([experiment 027](experiments/027-map-shader-scope/README.md)).

**Roads, 2026-10-23:** 0.9.29 logged 125,820 missing-road-strip errors (C161). Generator **0.9.30** writes the spline network for the generated locations (C162, C163; [interoperability register](docs/research/interoperability.md) R-001); **0.9.31** keeps vanilla's segment and point order as a precaution (C165). The owner's tests load it with no strip error and show a road network in the Roads lens (C166); an early report of vanished roads in 0.9.30 was an observation error: the owner's screen recording shows the proximity lens in observer mode, not Roads, and roads drawn on the map at zoom, so 0.9.30 drew roads too (C168). A 5.7-minute run at maximum speed logged no strip error (C167); roads built in play are not yet confirmed ([experiment 029](experiments/029-spline-strips/README.md)).

**R7 offline complete, 2026-10-22:** generator **0.9.28** gives each native state a technology level from its society and keeps cultures in the regional family of their land (R7b, C159); **0.9.29** gives great empires the Old World's level, a vanilla rank, royal roads, feared neighbours and resentful vassals (R7c, C160). Offline checks pass; nothing is validated in game. [Experiment 028](experiments/028-technology-and-empires/README.md) is installed as `rnw_exp_world_canszr3phf` and awaits the owner's test.

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
