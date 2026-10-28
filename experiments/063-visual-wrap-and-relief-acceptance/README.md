# 063 — In-game acceptance of cylindrical wrap, mountain relief and TR46 candidate

**2026-10-25.** Owner visual review in EU5 1.4.4 (Steam build 26142040 on 1.4.3 data 26105915).
Candidate: **RNW: Continents QW6O** ([`rnw_exp_tr46_treaty`](../INSTALLED.md)), generator **0.12.9 / epoch 39**, code `RNW1-040XN-DR20S-1RQ4T-Z0060-J01KM-KKG`.
Evidence: claims C345–C346; [TR46 register](../../docs/research/tr46-observer-audit.md), TR46-06a, TR46-01/02 and 06b.

> **2026-10-28 scope clarification (C412):** the recorded disappearance remains a
> valid owner observation for this sitting. The owner now reproduces a fissure in
> mod-free vanilla; a universal engine fix is not established. Reproducing the
> accepted historical candidate is planned in the [separate dossier](../../docs/research/map-wrap-dossier.md).

## Owner review and in-game findings

[V-GAME owner C345] The owner visually reviewed candidate `rnw_exp_tr46_treaty` in game and accepted the results:
1. **Physical seam at map boundary (TR46-06a):** confirmed absent in game ("шов отсутствует"). The texture/terrain crack at the horizontal map wrap is resolved. **TR46-06a CLOSED [V-GAME]**.
2. **Impassable mountain relief (TR46-01 / TR46-02):** confirmed improved ("горы стали лучше (не идеал и с красотой горных хребтов ваниллы не сравнится, но я откладываю это на пост-релиз), вся проделанная работа принимается"). The merged compatible units and mountain detail stamps are accepted for 1.0.0. Further aesthetic enhancements to vanilla-level ridge structures are deferred to post-release. **TR46-01 and TR46-02 ACCEPTED [V-GAME]**.
3. **Acceptance of completed work:** all done work on cylindrical wrap, river network continuity, local sea connections, and continuous Tordesillas allocation is accepted.

## Version and algorithm epoch

[V-EXEC C346] Product version rises from **0.12.9 to 0.13.0** under [ADR 0003](../../docs/adr/0003-versioning.md) (MINOR rises when a roadmap/campaign phase is accepted in game by the owner).
No world file or algorithm output changes, so the algorithm epoch remains **39** in `rnw/epoch.py` and the golden reference world is unchanged in `tests/golden_world.json`.
Full test suite passes: **1,978 Python tests, 14 skips, 23 Rust tests**; format, lint and types clean.
