# EU5 1.4.6 compatibility check

Audit date: 2026-10-30. The owner reports version 1.4.6; [V-LOCAL] the
installed Steam manifest identifies build **26300913**, last updated 30 October
at 11:22 CET. No game was launched or controlled for this check.

[V-LOCAL] All ten map-contract files match the 1.4.5 baseline byte for byte.
Comparison against the 1.4.5 reference world's recorded inputs covers 14,915 files
and 4,145 directory listings: none is missing, and 82 files changed. These are
78 Japanese localization files, one English localization file and three scripts:
`D009_across_the_pillars/in_game/common/generic_actions/iberian_union.txt`,
`in_game/events/DHE/flavor_MOR.txt` and
`in_game/events/character/court_flavor_events.txt` (paths under `game/`). No
recorded directory listing changed. The 1.4.5 reference world contains no
file with any of these three script names; it does not mask their updates.

[V-EXEC] The installed-game read-only suite passed 12 tests, with the two
opt-in long checks skipped. The content inventory reports 655 consumers, no
undecided or stale decisions, and the same complete report SHA-256 as the
1.4.5 audit (`d36b7e9c3d00411c2e4f84b8b3b78bd582d3c5dc6aca39c3fbd01bb8150ff067`).
Thus the checks found no new geographic consumer requiring a disposition.

[INFERRED] These results support compatibility of the existing map interface
and the audited content bindings. They do not establish identical generated
world bytes: localization and script inputs changed, and no new full export or
reference reproduction was run. [UNKNOWN] Loading and gameplay on build 26300913
were not observed in this audit. The version label comes from the owner; the
Steam manifest independently establishes the build number.
