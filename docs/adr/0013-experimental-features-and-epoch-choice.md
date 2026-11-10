# ADR 0013: Experimental features and the choice of an algorithm epoch

**Status:** Accepted 2026-11-10 (owner's request). Implemented on the first feature below.

## Context

A world code names the release that made it, and [ADR 0003](0003-versioning.md) groups releases
into algorithm epochs: two releases of one epoch make the same bytes from the same settings, seed
and game files. A newer epoch may make another world from the same code. Until now the generator
made worlds by the current epoch only and told the player when a code or a world came from another
one. A player who wants to carry on an old campaign's world, to compare two epochs, or to check a
world against an older game patch had to find and install the old generator.

The owner asked for a place for features that are not ready for everyone: a box in the settings
makes them available, and the first of them is the choice of an epoch.

## Decision

### The experimental box

`Preferences.experimental` (`preferences.json`, set by the Settings page of both windows) is off by
default and only a stored JSON `true` turns it on. It reveals features and changes nothing by
itself. Turning it off puts everything it revealed back to the default. An experimental feature is
a player-facing option of the window, not a command-line flag; it keeps the rule that one world is
one mod and writes no extra file.

### Epoch choice (the first feature)

- **The window.** The epochs from `epoch.OLDEST_SELECTABLE` (61, release 1.2.0) to
  `epoch.CURRENT` can make a world. `epoch.selectable()` lists them; `epoch.available(
  experimental=...)` is the current epoch alone when the box is off.
- **Where it is chosen.** On the new-world page, beside the seed and the code; the list is shown
  only while the box is ticked and its default is the current epoch. The choice is not stored: a
  new session, and unticking the box, return to the current epoch.
- **A code carries the epoch.** A world code is stamped with the first release of an older epoch
  (`epoch.stamp_of`): epoch 62 is `1.2.1`, epoch 61 is `1.2.0`. The code format does not change, a
  1.2.1 generator reads such a code and makes the same world, and the stamp **is** the identity.
  Pasting a code of a selectable older epoch with the box ticked follows it; without the box the
  window says the code came from another release, as before. Versions of a world (rerolled
  peoples or resources), candidates and queued worlds keep the epoch of their parent.
- **The carrier.** `Settings.algorithm` (default `epoch.CURRENT`) is the epoch a run makes. It is
  not part of `Settings.to_json_data()`, so presets, settings digests, records and `.rnworld`
  files are unchanged and a world of an older epoch has the settings of any other. `run_spec` and
  the world's `Record` name it, and `service.Request.algorithm` carries it from the window;
  `service` refuses an epoch that is not selectable, and a code whose stamp names another epoch
  than the one requested (except for the current one, whose stamp is any later release of it).
- **Verdicts.** `record.verdict` and `worldcode.reproduces` take the epochs the generator is set to
  make (`epoch.available`). A world of an older epoch is "the same algorithm" only then; without
  the box it is the "other algorithm" it always was. The command line is unchanged: it makes the
  current epoch only.
- **The gates.** A stage asks `settings.algorithm >= SWITCH`; the named switches are in
  `epoch.SWITCHES`. Epoch 63 → 62: subcontinents are cut at the waist (`hierarchy.neck_parts`)
  from 63 and by the earlier banded cuts (`hierarchy.banded_parts`) before it. Epoch 62 → 61: an
  exchange partner is a market centre and a town of its own before 62
  (`eu5_history_plan._centres`). Also epoch 63: a drawn land smaller than the canvas is stretched
  by a spline from 63 and by whole pixels with a box blur before it (`landmask._stretch_by_blocks`,
  verbatim from 1.2.1), a gate in the land stage through `fit` and `fit_drawing`; the land editor's
  own picture of a drawing is always the current epoch's. The land cache needs no epoch in its key
  for these: the sketch's land stage sits before the first two gates, and the world's key digests
  the fitted drawing itself, which the third changes. A future gate inside the cached land stage
  that leaves its inputs as they are must add the algorithm to the key.

### The rule for a new epoch

A change that opens a new epoch **keeps the behaviour it replaces behind a switch** and appends the
switch to `epoch.SWITCHES`. The epoch it follows needs its frozen reference world
(`tests/golden_world_epoch<N>.json`), and the generator must still make its bytes, which an opt-in
local test checks on the installed game (`RNW_REPRODUCE=1`, [testing](../testing.md)).

If keeping the old behaviour costs more than it is worth (it would copy a stage, or hold back a
fix), the cycle raises `OLDEST_SELECTABLE` past the epoch it drops, with a line in the changelog.
A dropped epoch is not selectable any more and its worlds are read as before: the window names
the other release. Nothing here promises an old epoch's **game inputs**: an older epoch run on a
newer game build makes that epoch's algorithm on the new inputs, and the record names both.

## Consequences

- The three epochs of today (61, 62, 63) make worlds equal to their frozen references; nothing in
  a world's bytes changed with this ADR, so it opens no epoch. [V-EXEC, 2026-11-10, local game
  files of the compatibility target: the installed-game reproduction of epochs 61 and 62 equals
  their goldens' digests and file counts; epoch 63 equals the pending golden.] The references are
  worlds of a generated sketch; the drawn-land gate is checked against the 1.2.1 module itself
  instead (`tests/test_landmask.py`: equal to the verbatim algorithm, and unequal to the spline).
- Each new epoch costs a switch and a reference. A fix that cannot be gated cheaply drops the
  oldest epochs instead of forking a stage.
- No new storage, dependency or distribution method: a preference, an integer in the run and the
  code's existing stamp.
