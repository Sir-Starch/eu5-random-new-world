# EU5 1.4.7 compatibility check

Audit date: 2026-11-03. [SOURCE] [Patch 1.4.7 notes](https://steamdb.info/patchnotes/26377361/),
published 3 November 2026, identify Steam build **26377361** (checksum `66ac`) and link the
official Steam Community announcement. The notes describe gameplay, script, localization and
UI fixes; they do not list map-data changes. [V-LOCAL] The installed public-branch Steam
manifest identifies build **26377361**. EU5 was not launched or controlled.

[V-LOCAL] All ten map-contract files match the preceding 1.4.6 baseline byte for byte. The
fingerprint is `592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`, which the
generator recognizes as its known map contract. Its displayed contract label still names the
1.4.5 reference build; that label identifies the map-contract baseline, not the installed
Steam build.

[V-LOCAL] Compared with the recorded inputs of the latest inspected 1.4.6 / build 26300913
epoch-60 world, all 14,919 recorded files and 4,145 directory listings were checked: none is
missing, 129 files differ and eight directory listings differ. The changed files comprise 95
localization files and 34 game scripts, including Across the Pillars. Three changed script
sources also have corresponding outputs in that inspected world:
`in_game/common/on_action/_hardcoded.txt`, `in_game/events/DHE/flavor_por.txt` and
`in_game/events/expeditions/pacific_crossing_events.txt`. The last two match fixes named in
the 1.4.7 notes. Such an existing world can therefore retain its generated copies of those
1.4.6 scripts and may not receive the corresponding patch fixes.

[V-EXEC] `tests/test_local_install.py` passed **13 tests** on the installed build; its two
opt-in long reference/layer checks were skipped. The suite is read-only and does not establish
engine loading or gameplay. [INFERRED] This supports compatibility of the 1.4.7 map interface
and current generator inputs. It does not establish identical output bytes or full gameplay
compatibility; no full 1.4.7 reference export or in-game observation was run.
