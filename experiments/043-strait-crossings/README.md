# 043 - Strait crossings

2026-10-24, generator 0.10.14, algorithm epoch 24. **NOT GAME VALIDATED, NOT RUN.** Claims C245-C247; design in [sea geography](../../docs/sea-geography.md). It keeps everything of [042](../042-lanes-and-closed-ocean/README.md) and adds the straits an army can cross.

## Why

The owner asked for the strait crossings to be studied and improved (2026-10-24). Study: [C245](../../docs/research/claims-ledger.md). The game's 184 `sea` rows join two land locations 1 to 9 pixels apart; the generated landmasses lay 100 pixels and more apart, so no row could be written (C240).

## What a world holds

The reference world of epoch 24 (`RNW1-0826C-SYW6B-MW73Y-C0050-W0813-G0TR8-CG`, small continents with the peoples rolled once, installed as `mod/rnw_exp_world_5zovefqzyg`):

| What | Before (0.10.13) | Now |
| --- | --- | --- |
| Landmasses within 36 pixels | kept as they were, 100 pixels and more apart | brought together at their nearest points to a channel of 5 or 6 pixels (nothing merged, no water cut off) |
| Rows of `adjacencies.csv` for generated lands | none | 6 (the presets: 7, 25, 0, 78 and 4), each with its two points on its two locations, at most 9 pixels apart, through a sea zone that touches both |
| Rows of the game's | 135 stay (49 in the replaced Americas go) | the same 135 |

## What the log may show

Nothing new is expected; if the engine refuses a generated crossing (C247) it will be in `error.log`. Nothing is asked of the owner.

## Installed

[INSTALLED](../INSTALLED.md). Enabling it is the owner's choice.

## Offline evidence

[V-EXEC] `make check` passes (1,235 tests); the reference world's digest `c885bc0f…e220` (792 files) came out the same under `PYTHONHASHSEED` 1 and 7 from land made fresh, and the layers test passes; the written `locations.png`, `default.map` and `adjacencies.csv` read back alone give the same 6 crossings, every point on its location; 1,189 passable generated zones are in the one water with the game's.

The first reference world of this land (peoples roll 0) offers no sacred-centre story, which the reference world must; its peoples are rolled once. The land cache is keyed by epoch, not by code, so a change inside an epoch needs its entries deleted (the first digest of this phase came from a stale entry).
