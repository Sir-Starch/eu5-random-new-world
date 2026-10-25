# 060 — TR46 expedition lifecycle diagnostics

**2026-10-25.** Read-only follow-up to 053 and 057, TR46-L02/L03. Original
campaign: generator 0.12.3 / epoch 33, EU5 1.4.4 executable / build 26142040 on
1.4.3 data / 26105915. Current generator remains 0.12.8 / epoch 38.

## Result

[V-GAME logs / V-EXEC C329] Correct the initial subtype accounting:
`expedition_manager.cpp:675` contains **177 mining surveys plus one Pacific
crossing**, not 178 mining surveys. All mining destinations are Old World:
136 Europe, 34 Asia, seven Africa; 46 owner tags/locations. The separate Pacific
failure is SPA at Dadinga Bay, ID 16084, `error.log:1824`, 06:41:55.

[V-LOCAL / V-EXEC / INFERRED C330–C331] Installed mining content allows a
capital-only eligible set but constructs no travel in that case. Thirty-three
logged tags have that set in frozen 1337 data; later error-time state is not
reconstructed. Spain's Dadinga event resumes before the return-route event
scheduled ten days later. Both the original Pacific `on_start` and complete
Dadinga event are byte-identical to installed vanilla. These are inherited
lifecycle edge cases, with engine/default/option-selection limits. No change
to generated oceans or worldwide vanilla content is justified by those rows.

[UNKNOWN C332] The 38 invalid resumes, 38 invalid-leader starts, four unavailable
type starts and lone port/water assertion omit the identities/callers needed
for exact attribution. Both save snapshots contain no active western/Pacific
voyage. Anonymous messages and static call sites do not prove the missing
runtime cause. Preserve the original eight-Workshop-mount confounder.

Full evidence, control flow, corrected counts, private reproduction paths and
remaining questions: [findings](../../docs/research/tr46-expeditions.md).

## Verification and installation

[V-EXEC C332] Reuse the validated read-only save reader and original definition
binding; CRCs pass, all 37 frozen evidence hashes match, current map fingerprint
is unchanged (`592e8309…03009a`); all 732 archived world-file hashes also match.
The complete world inventory establishes that mining content and the examined
generic actions are not overridden by RNW.
No executable source, substantial game-script excerpt, save, log or asset is
committed. No save writer, runtime hook, new output or installed candidate.
No game launch, profile/settings/playset modification, process control, push
or publication. Existing LSI3 and the 0.12.8 generator remain installed.

[V-EXEC C332] Required locked sync and full check pass: **1,969 Python tests,
14 skips, 23 Rust tests**, formatting/lint/types clean. Private `check.log`
SHA-256: `4f3808bcb6acdd5ab18cb6c90ed48ad7a66a02bdc2b499b2a8efa73728314b9e`.
