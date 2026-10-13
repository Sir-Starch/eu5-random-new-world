# Sonnet 5.5 bounded backlog

Tasks below are ordered by dependency and do not assume unverified EU5 geography support. Read [AGENTS.md](../../AGENTS.md), [feasibility](../feasibility.md) and [testing](../testing.md) first. Do not launch the game without renewed owner authorization; the current session's owner requested no further launches [V-GAME C12].

| ID / title | Depends on | Context | Deliverable and acceptance | Out of scope | Size |
|---|---|---|---|---|---|
| S01 — strict hierarchy parser | none | [inventory](../research/game-install-inventory.md), `src/rnw/geography.py` | Synthetic tests for BOM, comments, quoted tokens, malformed assignment, duplicate parent/key; `make check` and optional `EU5_GAME_DIR=... uv run pytest -q tests/test_local_install.py` pass | Full EU5 script grammar or rewriting vanilla files | M |
| S02 — named-color/raster audit | S01 | [findings](../research/findings.md), C03–C05 | Read-only streaming or array-based audit reporting missing/extra named colors and pixel counts to `local_data/`; synthetic raster fixtures; `make check` | Claiming game loadability or committing actual raster | M |
| S03 — script coupling graph v1 | S01 | C09–C10, `src/rnw/cli.py` | Replace lexical summary with syntax-aware extraction for selected setup/event fields, include path/line and confidence; aggregate report only committed; synthetic reference fixtures; `make check` | Classifying crash/gameplay effects without game evidence | L |
| S04 — reproducible metadata kit | none | [experiment 001](../../experiments/001-metadata/README.md), `src/rnw/cli.py` | Idempotence/safety tests for `prepare-mod`, no overwrite of existing user files, build/version fingerprint in a report; `make check` | Launcher/playset edits or game launch | S |
| S05 — log comparison v2 | none | [testing](../testing.md), `src/rnw/cli.py` | Detect incomplete baseline/current stages and group new errors with source path; synthetic logs verify; `make check` | Declaring runtime behavior from logs alone | M |
| S06 — offline build fingerprint | S01 | [architecture](../architecture.md), C01,C18 | Hash a minimal documented set of local contract files into gitignored output, refuse missing files with typed errors; synthetic install test; `make check` | Hardcoded compatibility claim for all `1.4.*` | S |
| S07 — deterministic settings prototype | S02, Opus R2 design | [product spec](../product-spec.md), [ADR](../adr/0001-python-research-tooling.md) | Versioned settings/seed schema, canonical JSON output and cross-platform golden tests; `make check` | Actual continent generator or EU5 exporter before experiments 003–005 | M |

Any experiment 002–006 implementation is a separate, owner-scheduled research task and must use its record's explicit pass criteria. Do not convert a “NOT-RUN” record to “PASSED” based on an offline test.
