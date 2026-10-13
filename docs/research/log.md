# Research log

## 2026-10-13

- Initialized the repository and evidence policy before inspecting the game. No game behavior has yet been verified.
- [V-LOCAL] Found Steam app 3450310 on branch `1.4-open-beta`, build 25905365, with a Windows executable run through Proton. Inventoried map rasters, hierarchy, setup and user paths; see `game-install-inventory.md`.
- [V-EXEC] `rnw inspect` counted 28,573 location keys and 6,174 in America. This is a syntax/hierarchy count, not a proof that all have map colors or playability.
- [V-GAME] A normal launch reached the EU5 1.4.1 main menu. A later isolated profile recognized the metadata-only test mod, but opened a first-run Select Language screen that did not respond to input. After the owner reported this, the game and input helper were stopped. No further launches are authorized in this session.
- [V-EXEC] Ran a lexical cross-reference scan. It found 104 candidate file categories and 106,418 summed distinct-key/file hits. This is a deliberately broad inventory with false positives; precise dependency and failure classifications remain open.
- [SOURCE] Reviewed Paradox terms, the EU4 Conquest of Paradise product page and two EU5 community repositories. Only the terms and product page support current claims; the 1.3.11 engine atlas is a lead, not 1.4.1 proof.
- [INFERRED] Revised the working architecture toward external generation conditional on a real map override test. The highest in-game geographic tier remains unverified, including T0.
- [V-EXEC] Built a metadata preparation/installation CLI, read-only hierarchy inspector, broad coupling scan and log diff. Added synthetic tests, optional local-install test, Linux/Windows CI and `uv` lockfile. `make check` passed with 4 tests and 1 local-only skip.
- [V-GAME]/[V-EXEC] Experiment 001 ended INCONCLUSIVE: version matching was logged, but complete comparable error-free startup was not established (900 baseline versus 898 current error-log lines). Recorded experiments 002–006 as NOT-RUN after the owner requested no more game launches.
- [INFERRED] Completed conditional external-generator recommendation, T2 runner-up, roadmap, product goals, legal/distribution risk and handoffs. These design documents preserve the distinction between local static files and in-game behavior.
- [V-EXEC] Cloned the committed repository into a fresh temporary directory and ran `uv sync --locked --group dev` followed by `make check`: 4 tests passed, 1 local-only test skipped, Ruff and basedpyright passed. Audited tracked file sizes (largest: 20 KiB lockfile), local Markdown links (none missing), ignored generated/local/third-party data and README/feasibility/handoff status agreement. The task brief remains local and ignored.

## Continued research, 2026-10-13

- [V-EXEC] Found and corrected an evidence error: the first color regex omitted inline-comment lines and mixed-case keys, yielding a false 22,314 count. The corrected read finds 28,582 color declarations, all 28,573 hierarchy keys covered, nine extra declarations, and no duplicate names/colors. Revised C05 and all dependent documents; no game behavior was inferred.
- [V-EXEC] Counted `default.map` class lists: 4,793 distinct sea, 918 lake, 1,868 impassable and 153 non-ownable tokens. American hierarchy intersects those lists in 984, 292, 460 and 7 keys respectively, with possible overlap. This ruled out a simple `continent = america` land mask for the generator.
- [V-EXEC] Added strict named-color parsing, stronger hierarchy errors and synthetic regression tests. Added a bounded-memory SHA-256 map-contract fingerprint command; its local raw output is ignored, and the ten-file aggregate digest is in C20. No game launch or game-directory write occurred.
- [SOURCE] Evaluated REA and a 1.4 map-mod Workshop lead. Neither was executed or treated as proof of EU5 1.4.1 topology support. No REA native provider is installed locally [V-LOCAL].
