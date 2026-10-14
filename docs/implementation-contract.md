# First development slice: generated geography mod candidate

This is an implementation task for Opus, not another research plan. Target the installed EU5 1.4.1 beta map contract [V-LOCAL C01–C09; V-EXEC C20]. Build a **deterministic, seed-driven geographic change** and export an isolated `rnw_exp_*` mod candidate. Do not claim game compatibility until the owner later permits a controlled in-game validation [UNKNOWN C13]. Keep the long-term model capable of T3 new locations; use existing IDs for the first candidate to limit unknowns.

## Concrete vertical slice

1. **Model and settings.** Implement an integer-coordinate world model with land/sea class, cell IDs, parent hierarchy and graph edges. Add a versioned seed/settings schema and an explicitly specified integer PRNG. Support at least two presets that yield measurably different coast/island shapes, not merely changed names or ownership. The model must allow future new IDs even though the first exporter preserves existing IDs [INFERRED C03–C06,C14].
2. **Geographic generator.** On committed synthetic fixtures, generate connected land groups, sea routes and coastlines from a seed. Keep a protected boundary set untouched, reject disconnected or vanished cells, and report land/sea topology metrics. Assign one unique color to each generated semantic location; preserve every protected pixel/key and the nine observed extra color declarations unless their role is resolved. The user's installation is read-only.
3. **EU5 1.4.1 candidate exporter.** Read the local game map and named colors only at generation time; refuse an unexpected [map-contract fingerprint](research/claims-ledger.md) unless the user explicitly selects a new build. Emit a new `generated/rnw_exp_*` folder with metadata, a modified location raster and the smallest relevant EU5 data files justified by local evidence. Start with a bounded American coast/sea region and **move a real land–sea pixel boundary between existing IDs**; keep those IDs, the Old World and Atlantic/Pacific anchor zones unchanged. Report exactly which files changed and which engine behaviors remain untested. All vanilla-derived output remains gitignored and local [INFERRED C03–C15].
4. **Offline validation.** Verify color/key coverage, no unexpected colors, nonempty connected cells, land/sea boundary change, preserved protected pixels, graph reachability where modeled, repeatable hashes for the same seed/settings/build and meaningfully different geometry for different seeds. Include synthetic negative fixtures. Tests must fail on a deliberate orphan sea, duplicate color, broken parent or changed protected pixel. No game launch is part of this slice.

## Interfaces and safety

- Provide one CLI entry point that takes `--game-dir`, `--seed`, settings/preset and a new output directory under `generated/`; it must refuse overwrites, output inside the game installation and unsupported fingerprints. The result is **staged**, not automatically installed or enabled in a playset.
- Keep game-specific parsing/serialization separate from the world model. Preserve BOM/encoding and line endings deliberately; never round-trip broad vanilla files just to alter one value. Every copied or derived file must be listed in a local manifest with original input hash and generated output hash, but no source bytes embedded in the manifest.
- Do not modify existing mods, saves, settings or Steam account state. No real game asset, generated raster, cache or log enters Git. Use only original/synthetic fixtures in CI.
- REA is an optional later binary-analysis lead [SOURCE C21]. It is not required for this implementation slice and was not installed or run here.

## Acceptance for handoff back to the owner

`uv sync --locked --group dev && make check` passes from a clean clone. The synthetic generator produces byte-identical outputs for repeated seed/settings/version runs on Linux and Windows CI; distinct seeds change coastline metrics. A local command against the fingerprinted 1.4.1 installation emits one `rnw_exp_*` candidate and a report proving changed New World coastline pixels and unchanged protected pixels. The report states **NOT GAME VALIDATED**. The eventual engine validation, when separately authorized, follows experiments 002–004 in order with a complete same-build vanilla baseline; [testing](testing.md) defines evidence needed to call each rung passed.

This slice is genuine mod development: it produces a geography-changing package candidate. It does not require an unproven T3 loader contract, and it does not redefine the final product as T2. If the 1.4.1 engine later rejects T2, retain the model and adapt the exporter based on that failure; if new IDs work, extend the exporter to T3.

## Delivery status, 2026-10-14

Delivered offline; **NOT GAME VALIDATED**. See [ADR 0002](adr/0002-d0-generator-stack.md) and claims C23–C33.

| Contract item | Result |
|---|---|
| 1. Model and settings | `rnw.model.World` (label raster, cells with key/colour/class/five parents, ocean anchors, graph edges); settings schema 1 with `continents` and `archipelago` presets; SplitMix64 RNG v1 [V-EXEC C31,C33] |
| 2. Geographic generator | `rnw synth` generates land, seas, lakes, new cells, hierarchy and unique colours around a protected synthetic Old World; byte-identical bundles with committed golden digests; presets differ measurably [V-EXEC C31] |
| 3. EU5 1.4.1 exporter | `rnw generate` refuses unknown fingerprints, overwrites, non-`generated/` and in-game outputs; stages `locations.png` + `rivers.png` with metadata, manifest, report and preview; moves 16,205 land–sea pixels between existing American IDs for seed 42 [V-EXEC C28–C30] |
| 4. Offline validation | Typed failures for orphan sea, duplicate colour/key, broken parent, changed protected pixel, vanished/split cells, unexpected labels, new contacts and ineligible changes; written files are re-decoded and compared with the installation [V-EXEC] |

Deviations: the visual heightmap was not edited because `terrain2/heightmap.png` does not cover the Americas (C25). The nine extra colour declarations are now known to be zero-pixel declarations (C23) and remain untouched. Linux byte identity is observed; Windows identity waits for CI.

Local reproduction: `uv run rnw generate --game-dir "$EU5_GAME_DIR" --seed 42 --preset continents --output generated/rnw_exp_d0_coast_s42`. The expected hashes are in C28.
