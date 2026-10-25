# 059 — Native expansion in the frozen TR46 campaign

**2026-10-25.** Read-only follow-up to 053, TR46-05 and the attribution of L07.
Original world: generator 0.12.3 / epoch 33; EU5 1.4.4 executable on 1.4.3 data.
Current generator stays 0.12.8 / epoch 38; no new mod, install or game launch.

## Question and result

[V-LOCAL / V-EXEC C325–C327] Do generated extraordinary societies fail to grow,
and should native colonization occur under vanilla rules? **The broad claim is
not supported.** Both empires expand (53→121 and 86→142 locations), and WBU
expands 7→149 while becoming LIA. Ordinary state territory consolidates into
fewer countries; the league loses all land. Both saves use vanilla's default
`western_colonisation_only` rule. All native capitals remain American; ordinary
native AI charters are excluded by that rule even though the examined states
have the colonization advance. Frontier settlement is a distinct, partially
region-gated mechanism; it has no active action globally at either checkpoint.

The complete rules, all nine extraordinary countries' land/subject counts,
ordinary/pop cohorts, successor and civil-war handling, remaining questions and
private reproduction paths are in [the findings](../../docs/research/tr46-native-expansion.md).
Do not substitute the changed 0.12.8 society start for this frozen baseline.

## Evidence and verification

[V-EXEC C326] Checkpoints are **1497.4.1** (`_19`) and **1590.11.11**, not two
start/end snapshots beginning in 1337. ZIP CRCs and original evidence-manifest
hashes pass. Consume 68,108,132 / 75,749,957 tokens with no unknown tokens or
unbalanced container; check 30,565 location IDs, 201 retained original capitals,
738 initial native ownership records and every current country's ownership list
against location-owner counts, with zero mismatches. Explicitly bind the QDL
civil-war successor and preserve WBU/LIA's original object separately from its
civil-war copy. Histories can omit current civil-war transfers and are not used
as an exact current snapshot or proof of lifetime peaks. Interoperability R-005
records this limited read-only save interface; all raw material remains ignored.

[V-EXEC C328] Required full check passes: **1,969 Python tests, 14 skips,
23 Rust tests**, formatting/lint/types clean. The only source edit corrects an
unsupported comment that a two-alliance ring guarantees sufficient diplomatic
capacity. It changes no output. No AI/technology/rule/balance change is justified
by this investigation; native frontier selection and league resilience remain
explicit unknowns. L07 is attributed to league member GVQ, without attributing
its defeat to the conditional DIP-0 setup warning.

## Installation and removal

None. This is an evidence/documentation phase; no game-facing update candidate
was built. Existing LSI3 and the 0.12.8 generator stay installed. No files in the
profile or installation, saves, playsets or settings were modified. No game
launch, process control, push or publication.
