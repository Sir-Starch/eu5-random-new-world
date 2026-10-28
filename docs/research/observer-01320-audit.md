# Completed observer campaign — RNW 0.13.20

2026-10-28; C419–C423. Read-only audit of the owner's campaign on EU5
**1.4.4 / Steam 26142040**, using **RNW: Restored visual wrap**,
`rnw_exp_world_7yzo7v4bu5`, generator **0.13.20 / epoch 57**.

## Verdict and evidence boundary

[V-GAME logs / V-EXEC C419] The campaign advances from 1337 through
**5 October 1768**, with all 431 successive new-year records from 1338 to
1768. The process records **Quit from inside game** at 09:19:18 CET and
completes its exit transition at 09:19:24. No fatal/crash record or river
processing, missing spline-strip, generated treaty-parser, RNW story-script,
port-assertion or excessive starting building-level error appears in the
captured current error files. This is substantial campaign-duration evidence
for this world, not proof of every mechanic, story outcome or generated seed.

[V-GAME logs / V-LOCAL / V-EXEC C420] **No severe defect attributable to RNW
is established by these logs. The run is not error-free:** the sacred-centre
theocracy still lacks three initial government fields. The known nine
generated locator warnings also recur. The generic failures below remain
unattributed where their runtime operands are absent; they are not declared
harmless or assigned to vanilla merely because their source is inherited.

## Session identification and counting

[V-LOCAL / V-EXEC C419] The unchanged Steam manifest reports build 26142040;
the debug log explicitly identifies game 1.4.4. Installed metadata and the
world's recovery record agree on release 0.13.20, algorithm 57 and canonical
851-file digest `de9fa8ae001c436bf3a5b6fb90ea342787069da4c326cdf84e0c8ec8d98e9995`.
This identifies the world; it is not a new full game-installation integrity
audit or a new reconstruction of the export.

The process initially loads QDZS, then switches playsets and reloads
**Restored visual wrap at 06:01:45**, before building the campaign state at
06:02:21. The final playset enables only that world. VFS enumeration also
mentions the other installed RNW worlds; enumeration is not evidence that
their gameplay content participated in the campaign.

The frozen `error.1.log` and `error.log` contain **7,524 timestamped records**,
**55 origins** and **398 exact message variants**, including continuation
lines in their parent record. Of these, 41 precede the final world's reload;
**7,483** are at or after it. `error.2.log` through `error.5.log` predate this
process and are excluded. Mirrored records in debug/game/GUI/ECS logs are
not counted twice. The event CSV is dated 23 October and cannot establish
this campaign's event firings.

Original log snapshots, sizes, timestamps and SHA-256 hashes, the complete
per-origin catalog and numerical location bindings remain ignored under
`local_data/observer-campaign-20261028/`. No game was launched or controlled;
no mod, save, playset, setting or game-installation file was changed.

## Findings that affect RNW

### A01 — Incomplete sacred-centre government: confirmed output defect

[V-GAME logs / V-LOCAL / V-EXEC C420] At 06:02:25 the engine reports that
**UUV / Viakna** lacks `marriage_law`, `heir_religion_law` and
`parliament_type`. Its installed country setup at
`main_menu/setup/1337/10_countries.txt:56314` explicitly supplies theocracy,
theocratic elective succession and the two government axes, but has neither
a template nor those three fields. Its capital is `rnw_loc_04985` and its
starting technology level is zero.

This repeats C411's incomplete sacred-centre setup in a new world. C399's
removal of incompatible inherited monarchy fields did not establish complete
theocracy initialization. Correct the generator's initial government setup
using compatible vanilla precedents and validation. **[UNKNOWN]** These logs
do not establish a broken succession, marriage action or parliament during
the campaign, and do not justify a severe gameplay-impact claim.

### A02 — Same seam locator warnings: no new displacement evidence

[V-GAME logs / V-EXEC C420] At 06:02:15 there are nine warnings for
`rnw_loc_00821`, `rnw_loc_00873` and `rnw_sea_00398`, with exactly the
coordinates/distances studied in C414; two additional VFX warnings concern
retained Atlantic locations. Keep the geometry interpretation and its limits
in the [dedicated dossier](map-wrap-dossier.md#nine-quxq-locator-warnings-c414).
This audit supplies no new positional measurement or rendering conclusion.

## Other errors and attribution limits

[V-GAME logs / V-LOCAL / V-EXEC / UNKNOWN attribution C421]

| Group | Established evidence and disposition |
|---|---|
| Mining surveys | All **247** exhausted-waypoint records name `mining_survey_expedition`: **161 Europe, 60 Asia, 7 Africa, 19 generated America**. The American records concern four destinations, including 14 repeated failures at `rnw_loc_02975` for QJH. RNW does not override this expedition type or its mining events. These are real failed surveys; the logs do not establish RNW causation. **61** anonymous resume errors cannot be bound to those surveys. See the existing lifecycle investigation, C330/C383. |
| Heavy-infantry mercenaries | **Three** creation failures bind to **Koksala / `koksala`**, ID 6149, twice, and **Konildi / `konildi`**, ID 12257, once. Both are in Asia, not generated America. One-based hierarchy order independently reproduces both names printed by the engine; that binding is used for the survey counts too. Do not carry C411's American mercenary attribution into this run. Eligibility and callers remain unknown. |
| AI expansion score | **Seven** divisions by zero in inherited `attack_neighbors.txt:40`. The installed score divides by capital distance, and RNW supplies no override. The log omits attacker, target and evaluated distance: neither a generated-capital error nor clean-vanilla reproduction is established (C334). |
| Position assertions | `Bad position` at **09:13:02** and positive-x/y assertion at **09:13:13**. No object, map coordinate or caller is logged. Nearby pause/camera/audio activity cannot identify the cause. The campaign continues afterwards. Keep open; neither an RNW routing regression nor a harmless camera issue is proved. |
| Tag-change assertion | One rejected `ChangeTag` at **07:59:32** coincides with the Chinese dynasty crisis ending in CHI in `game.log:15419`. This is an Old World context lead, not proof of the attempted tag or caller. No RNW formation is named. |
| AI commands | `ai.log` contains **152,186** invalid-command execution warnings and **495** posting warnings. The largest group is **101,162** cabinet-action execution rejections. These omit actor, target, selected action and failed prerequisite. Their count is not a failure rate or proof that generated countries cannot develop; preserve C333's attribution limits. |
| Inherited script/DLC loading | Missing Across-the-Pillars objects/effects, prototype portrait templates, DLC thumbnails, achievements and tooltip references occur in installed content. Some cited files are RNW-rewritten copies, including Castilian/Portuguese events: file ownership alone is insufficient attribution. The failed crypto-community modifiers and Golden Century references are inherited content, not RNW identifiers. No current RNW-specific parser/reference failure was found. This session is not a clean vanilla control. |
| Remaining runtime/UI messages | **4,401** invalid subunit localization records; **1,061** movement-religion warnings; **502** rejected resolution proposals; **53** list-index clamps; **28** same-province migration refusals; **20** wrong-type script values, plus GUI context failures, three building-list clamps, an artist-type refusal, a Chinese event-target failure and entity/animation notices. Their sources/contexts identify inherited actions or UI; their underlying runtime causes are not established as RNW defects. Same-province migration and UI failures are not evidence that all generated colonial content works. |

[INFERRED from C419–C421] The run supports continued development without a
new owner test sitting. The actionable RNW correction is A01. A02 retains its
existing evidence boundary; generic AI and position failures remain open
diagnostics. There is no evidence here requiring replacement of the owner's
campaign or an engine/interface patch. Generator output, version and epoch
are unchanged by this audit.

[V-EXEC] Repository checks pass: formatting, lint, types, **2,116 Python
tests / 14 skipped** and **23 Rust tests**. Snapshot hashes, successive-year
coverage and local documentation links were checked independently. These
offline checks do not resolve the runtime attribution limits above.

## Fix assessment, 2026-10-28

The owner subsequently asks which findings need a correction. This assessment
does not implement or install a generator update.

### A01 requires a generator correction, not a warning filter (C422)

[V-LOCAL / V-EXEC] Both installed vanilla precedents used to select
`theocratic_elective` also supply **`monogamous_marriage`** and
**`heir_special_succession`**: Tibet explicitly, Venda through its
`subsaharan_theocracy` template plus an explicit succession-policy override.
The succession definition has `empty_heir_religion_law`; the special policy's
potential requires exactly that tag. Reusing the American monarchy's
`heir_any_religion` would reintroduce the incompatible-law problem of C398.

The parliament needs separate selection: Tibet uses `council`, whose potential
requires `allow_council_parliament`, while Venda uses `assembly`, also used
by the American country templates. Copying Tibet's parliament solely because
it is the first theocracy is not justified. Viakna's actual faith is
`tain_feyentun_religion`, not Catholicism; vanilla's monogamy allowance excludes
Catholic theocracies, not this faith. These source conditions support the
targeted combination **monogamy / special succession / assembly** for this
case. Other generated faiths must be checked against the installed rules.

[INFERRED from these source contracts and C420] This is a **normal-priority
output-correctness fix**, warranted even without a demonstrated campaign
failure. These policies carry real effects; absent initialization is not merely
a misspelled diagnostic. Implement the nested `laws` and `parliament` records
in the initial country model/writer, calibrate from installed compatible
precedents, and reject incomplete or incompatible sacred-centre output.
Keep the selected technology, native societal axes and template-free setup;
do not import a whole Old World template, restore monarchy inheritance or add
a post-start repair event. Verify nested-policy compatibility, written output
and unaffected non-sacred countries. A completed implementation changes world
files and therefore requires the normal version/epoch/golden/delivery cycle.
It is **not implemented by this investigation**. The logs still do not prove
a broken succession, and this finding alone does not require abandoning the
existing campaign.

### A02 and anonymous runtime failures: no supported RNW patch yet (C423)

[V-EXEC] A fresh read of the installed 0.13.20 output checks **25,033**
`id`/`position` records naming generated map objects in the map-object files
and generated port-locator file. All coordinates are finite, and every
horizontal x/z pair lies strictly inside the 16,384 × 8,192 map bounds.
All **307** generated land-owning states have city anchors; their capital
keys and city x/z pairs are pairwise distinct. This excludes missing, zero,
out-of-range or coincident **initial** anchors in that checked set, not an
invalid runtime path or zero evaluated distance centuries later.

| Finding | Decision |
|---|---|
| Nine seam locator warnings | No anchor relocation or identity split. The current raster and all four relevant city/combat/unit-stack/VFX files are SHA-256-identical to C414's measured QUXQ files; see the [dossier follow-up](map-wrap-dossier.md#01320-locator-follow-up-c423). That existing own-pixel evidence applies directly to these bytes. |
| Seven AI-score divisions | Do not clamp the denominator or move capitals. The missing attacker/target prevents connecting the failed runtime calculation to generated data; the initial-state checks above find no shared capital or city point. A blanket vanilla-score override changes Old World AI without a demonstrated RNW correction. Keep the diagnosis open (C334). |
| Two position assertions | Keep unresolved and do not dismiss. The new initial-anchor checks pass, but the messages contain no failed runtime point, route or caller. They do not justify a coordinate offset, a map-edge strait, disabling expansion or reverting the verified seam-route correction. |
| Mining surveys / mercenaries | No RNW patch justified by this run. The inherited mining callback omits a capital-completion branch, retaining C330's concrete lifecycle lead, while the three mercenary failures are in Asia. Neither relocating native capitals nor granting technology/units would address an established generated-data fault. |
| Generic AI, tag and UI failures | Retain the attribution limits above. Counts, temporal proximity and a dynamic tag alone do not identify the failed RNW object or a corrective generator invariant. No global script/interface workaround follows. |

[V-EXEC] Machine-readable coordinate and government checks remain ignored in
`local_data/observer-campaign-20261028/fix-assessment/`. No current save-state
or error-time runtime reconstruction is claimed. This investigation changes
documentation only; the prior full checks apply to unchanged generator code.

## Implemented correction — 0.13.21 / epoch 58 (C424)

[V-LOCAL / V-EXEC] At the owner's request, A01 is implemented in the initial
country model and writer. Sacred centres receive typed nested laws and
parliament records. Calibration resolves the selected vanilla theocracies'
template inheritance and explicit overrides, requires agreement on the two
laws, checks the succession policy's tag and the marriage-policy restriction,
and selects an American template's parliament without a special eligibility
potential. Missing, conflicting or unsupported calibration stops generation;
an excluded faith also fails before serialization. Other countries keep their
templates and initial records. No startup repair, game-rule override or
engine/interface patch is added. A02 and the unattributed diagnostics retain
their existing dispositions.

[V-EXEC] Synthetic regressions cover inherited-law overrides, missing and
conflicting policies, incompatible succession tags, marriage restrictions,
restricted parliaments, excluded faiths, and missing/wrong written institutions.
The final validator also rejects an incompatible plan even when its writer
faithfully serializes it. Full checks pass: **2,132 Python tests / 14 skipped**,
**23 Rust tests**, formatting, lint and types; the installed-game read-only
suite passes **12 / 2 optional skips**. The built and installed Windows
generator passes its offscreen self-test and produces the same calibrated
institutions and synthetic country bytes as Linux.

[V-EXEC] The new reference retains the previous seed and settings. Its
canonical **851-file** digest is
`f85cb19da0d6b78f5d93d8d15dad87d50c3bf5aa7edcf6023725fc31f71f5e25`.
Only `main_menu/setup/1337/10_countries.txt` changes from 0.13.20; **850**
canonical file hashes are identical, including geography, rivers, locators,
routes and the cover. Removing the two newly written nested blocks restores
the entire previous country file exactly: only **UUV / Viakna** changes.
The revealed candidate separately has **830** other nonmetadata files unchanged.
An independent complete export reproduces the canonical digest exactly,
with no changed game inputs or differing output files.

The reference, output comparison, checks and platform parity reports remain
ignored under `local_data/theocracy-init/`. Delivery is recorded in
[INSTALLED](../../experiments/INSTALLED.md). **[UNKNOWN]** New engine acceptance
of these complete fields has not been observed; no EU5 launch or control is
performed, and the owner's existing campaign is preserved.
