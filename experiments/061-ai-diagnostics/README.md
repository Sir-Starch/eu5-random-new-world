# 061 — TR46 AI diagnostics and expansion scoring

**2026-10-25.** Read-only follow-up to 053 and 059, TR46-L04. Original
campaign: generator 0.12.3 / epoch 33, EU5 1.4.4 executable / build 26142040 on
1.4.3 data / 26105915. Current generator remains 0.12.8 / epoch 38.

## Result

[V-GAME logs / V-LOCAL / V-EXEC / UNKNOWN C333] Recount all **57,352** AI
warnings: 57,156 execution and 196 posting, 42 stage/command categories.
Every message omits actor, target and reason. The inspected validation/logging
branches explain that information limit; they do not identify failed frontier
actions or a generated-country defect. Counts are not failure rates.

[V-LOCAL / V-EXEC / UNKNOWN C334] Installed vanilla's neighboring-war-target
score divides by capital distance without a script guard. RNW does not
override it. Three errors omit attacker/target. The 202 generated starting
states and 777/597 landed location countries at the saved checkpoints have
no shared capital IDs within each set; these snapshots cannot supply the
error-time distance or establish the cause. No global vanilla patch or capital
relocation follows.

[V-GAME logs / V-LOCAL / V-EXEC / UNKNOWN C335] Three building-list warnings
clamp **232→2**, **7→0**, **9→0**. Their actors NAV, ABA43 and IFA bind to
Old World countries, outside the original native creation closure. ABA43 is
an explicitly released Novgorodian country, not an original generated tag.
The upstream count mismatch and runtime construction outcome remain unknown.

[UNKNOWN C336] Preserve C300's eight Workshop mounts as an attribution limit.
L04 remains open in three explicit subproblems; no measured link to native
frontier selection, league defeat or a campaign-wide expansion rate. No new
manual campaign, probe mod or owner test is requested.

Full findings, source locations, retained evidence and remaining questions:
[TR46 AI diagnostics](../../docs/research/tr46-ai-diagnostics.md).

## Verification and installation

[V-EXEC C336] All 37 original evidence hashes and 732 copied world-file hashes
match. Both saves retain their manifest hashes and pass ZIP CRCs; cached
extractions match their research manifest. No new save token/reader behavior.
Current Steam build and map fingerprint remain unchanged. Limited executable
inspection is recorded in interoperability R-005; raw artifacts stay ignored.

Documentation only: no source/output/version/epoch change or installation.
LSI3 and the 0.12.8 generator remain installed. No game launch, profile/save/
settings/playset edit, process control, push or publication.

[V-EXEC C336] Required locked sync and full check pass: **1,969 Python tests,
14 skips, 23 Rust tests**, format/lint/types clean. Private `check.log` SHA-256:
`8a7af4d199f4b88f2dbce9950fc80ca70f928954a8fc1339546bf9fef99b9ca9`.
