# TR46 — AI command rejection and expansion scoring

2026-10-25. Follow-up to [the problem register](tr46-observer-audit.md),
TR46-L04; [experiment 061](../../experiments/061-ai-diagnostics/README.md),
claims C333–C336. Original campaign: generator **0.12.3 / epoch 33**,
EU5 **1.4.4 executable / Steam 26142040**, on **1.4.3 data / 26105915**.
Current generator remains **0.12.8 / epoch 38**. Read-only investigation;
no new game run, AI adjustment or generated-output change.

## 1. Findings and disposition

| Subproblem | Established evidence | Remaining limit and disposition |
|---|---|---|
| **TR46-L04a: invalid commands** | [V-GAME logs / V-EXEC C333] All **57,352** records recounted; 57,156 execution and 196 posting warnings, 42 stage/command categories. Messages contain the command identifier, not its actor, target, action parameters or validation reason. | [UNKNOWN] Affected countries, rejected cabinet actions and consequences cannot be reconstructed. Keep open as unattributed diagnostics; no native AI fix follows from their count. |
| **TR46-L04b: expansion division by zero** | [V-LOCAL / V-EXEC C334] Installed vanilla divides a candidate's tax base by capital-to-capital distance without a script-side zero guard. RNW does not override this expansion-target content. | [UNKNOWN] Neither attacker nor target is logged; the reason the evaluated distance is zero is missing. An inherited unguarded calculation is established, a generated-capital defect or clean-vanilla reproduction is not. |
| **TR46-L04c: building-list truncation** | [V-GAME logs / V-LOCAL / V-EXEC C335] Three messages name NAV, ABA43 and IFA; inspected engine branch clamps the requested size to the available count. Both saves bind these identities to Old World countries outside the original native creation graph. | [UNKNOWN] The producer of the excessive requested size and exact error-time candidate lists are absent. The clamp is confirmed; no construction stall or generated-society failure is established. |

[UNKNOWN C336] The session mounted eight Workshop directories in addition to
the recorded world context (C300). RNW's absence of an override establishes
what **RNW** supplies; it does not establish the complete effective content of
the session or a clean vanilla control. No error family is dismissed as harmless
merely because it has no identified actor.

## 2. What the command warnings actually record

[V-GAME logs / V-EXEC C333] Every physical line of the frozen `ai.log` matches
one of its two diagnostic forms. Recounting agrees exactly with 053's
`ai-command-counts.json` and all 42 rows of the [log catalog](tr46-log-catalog.md).
First warning: **04:04:48**, last: **06:57:48**. The largest categories are:

| Stage / command | Records | First / last clock |
|---|---:|---|
| execute / `set_cabinet_action` | 35,724 | 04:13:45 / 06:57:48 |
| execute / `disband_subunit` | 5,898 | 04:14:09 / 06:56:44 |
| execute / `build_road` | 3,170 | 04:16:45 / 06:57:48 |
| execute / `change_trade_capacity` | 2,396 | 04:04:48 / 06:57:48 |
| execute / `diplomaticactioncommand` | 2,324 | 04:13:45 / 06:57:47 |
| execute / `transfer_occupation` | 2,096 | 04:14:23 / 06:57:45 |
| execute / `toggle_can_attach_to` | 1,602 | 04:14:19 / 06:57:33 |
| execute / `construct_building` | 939 | 04:19:58 / 06:55:56 |

[V-EXEC C333] Cabinet assignment makes up **62.29%** of all warnings. None of
the 196 posting warnings names `set_cabinet_action`; they are a separate set
of five command categories. The first **35** records are trade-capacity warnings
before the observer-control clearing at 04:13:33–04:13:38. The largest number
of one command at one logged second is **98** `disband_subunit` records at
06:08:37. None has an object handle with which to distinguish different
subunits, countries or retries. These are counts of messages, not unique
failed projects, monthly failure rates or fractions of all attempted commands.
The log supplies no successful-command denominator.

[V-LOCAL / INFERRED C333] Limited inspection of the installed executable finds
the execution-warning branch after a command object's boolean gate. The
false branch formats only the command name and continues the command loop;
it supplies no failed-condition text. A checked posting helper similarly
checks the gate, formats the command name and returns false. This supports
reading the messages as rejected commands; it cannot recover their omitted
runtime objects or distinguish stale planning, an invalid target, resource
shortage or another failed prerequisite. It does not establish a particular
engine race or the validity rules of all 42 categories. Necessary addresses
and private artifacts are recorded below and in interoperability R-005.

[UNKNOWN C333] `set_cabinet_action` is the command name, not the selected action.
Its 35,724 warnings cannot be labeled frontier-settlement failures. Likewise,
`perform_generic_action` does not identify colonization or an expedition,
and `diplomaticactioncommand` does not identify a rejected declaration of war.
The 3,170 road-command warnings are not missing spline-strip diagnostics:
the frozen `error.log` contains no `Could not find spline network strip`
message. That absence does not establish that every requested road was valid
or built. The post-campaign saves cannot reconstruct these anonymous commands.

## 3. The inherited expansion-score denominator

[V-GAME logs C334] Three records in `error.log` report the same source:

| Original line | Clock | Reported source |
|---|---|---|
| 381 | 04:20:24 | `common/ai_scripted_expansion_target/attack_neighbors.txt:40` |
| 533 | 05:02:25 | same |
| 534 | 05:02:28 | same |

[V-LOCAL C334] In the current installed file, **line 40 opens the score block**;
the division expression is at **line 42**. Its score is the target country's
tax base, divided by the distance from the target capital to the attacker
capital, then multiplied by ten. No `max`, minimum distance or conditional
guard encloses that division. The attacker trigger uses personality and time
since war; the candidate effect collects neighbors and neighbors reached
through neighboring subjects. The installed folder's README describes this
as adding targets when the AI evaluates **future wars**. It is separate from
the colonization game rule and the frontier cabinet action studied in
[059](tr46-native-expansion.md).

[V-EXEC C334] The complete **807-file** frozen world inventory contains no
`in_game/common/ai_scripted_expansion_target/` override, no cabinet-action
override and no loading-screen defines override. The examined installed
`attack_neighbors.txt` has SHA-256
`f54588972e8fe20dd27e4a9b4a8ec50bce4ba1e7a71701ed4cdc034b88c5c338`.
This is inherited content, subject to the mounted-mod attribution limit above.

[V-EXEC / UNKNOWN C334] The original **202** generated land-owning states have
202 distinct initial capital keys. The two validated save extractions have
**777 / 597** land-owning `location` countries with capital IDs in
1497 / 1590; none shares its capital ID with another country in that subset.
This excludes a simple shared-capital-ID explanation **at those checkpoints**.
It does not reconstruct any of the three failed evaluations. No claim is made
about the engine's distance precision, effective capital positions, an invalid
scope, countries outside that subset or their state at the error times.
In particular, zero distance is not proof that the generator put two active
state capitals in one location, or that the map seam caused it.

[V-LOCAL / UNKNOWN C334] The installed executable has an explicit zero-divisor
diagnostic branch for this script-value operation. The actor and target are
not arguments of the resulting log message. The limited inspection does not
establish the final war-planner score, which candidate was kept or discarded,
or whether another expansion target succeeded. No global minimum-distance
patch, capital relocation or AI bonus is justified by these three records.
L04b remains open for actor/target and error-time-state attribution; this does
not block unrelated generator work or require a new owner campaign.

## 4. Named building warnings belong to the Old World

[V-GAME logs / V-LOCAL / V-EXEC C335] The three original diagnostics are:

| Line / clock | Country | Requested size | Available candidates | Size after clamp |
|---|---|---:|---:|---:|
| 1622 / 06:34:36 | NAV | 232 | 2 | 2 |
| 1623 / 06:34:36 | ABA43 | 7 | 0 | 0 |
| 2015 / 06:46:18 | IFA | 9 | 0 | 0 |

The inspected installed branch compares the two counts, emits this message
when the requested truncation size is larger, and stores their minimum.
The warning is a bounded-list correction, not evidence of 232 missing
buildings or an out-of-bounds write. Its upstream count mismatch remains
unexplained; clamping does not prove correct AI selection or later construction.

[V-EXEC C335] Reuse C326's independently validated full object handles and
original location-ID binding. Both frozen snapshots identify the named tags:

| Tag / full handle | Saved identity and capital | Owned locations, 1497 / 1590 |
|---|---|---:|
| NAV / **916** | Navarre; cached capital `saint_jean_pied_de_port`, Europe; initial capital `pamplona` | 0 / 0 |
| ABA43 / **50334293** | Dynamic country with name key `vilkmerge_province`, capital `rokiskis`, Europe; explicit `Released` creation from handle **2164 / NOV** | 2 / 1 |
| IFA / **884** | Ifat; capital `dakkar` in 1497, `zeila` in 1590, Africa | 42 / 62 |

None is one of the 659 original generated tags, nor a member of their saved
explicit creation closure (**751 / 760** handles). ABA43's dynamic tag alone
therefore must not be treated as a generated New World country. NAV's zero
owned land and cached capital are checkpoint fields, not proof that it was
landless when the warning was emitted. IFA's growth does not make its warning
harmless. No original native country or extraordinary society is named by
these three rows; indirect effects of a modded world remain unmeasured.

## 5. Consequence for the native-expansion report

[V-EXEC / UNKNOWN C336] L04 provides no new evidence overturning 059's saved
land/subject counts: both empires and WBU expanded by conquest and consolidation,
while the three league members lost all land before the first checkpoint.
The vanilla western-only rule and the absence of active native charters remain
separate observations. Anonymous rejected cabinet commands cannot explain
the frontier action's lack of a saved active instance, and three anonymous
war-score errors cannot explain a campaign-wide native growth rate.

Keep the three L04 subproblems and their missing evidence explicit. Do not add
native AI bonuses, replace worldwide vanilla scripts, suppress diagnostics,
alter the selected game rule or relocate capitals to make the log quiet.
No attributable generated-data defect has been established in this block.
A clean vanilla control now supplies a second campaign's background counts
(C402, section 7). Comparable per-year rates, the actual rejected actions, the
source of zero distance and the building-list producer remain **[UNKNOWN]**.

## 6. Private reproduction and verification

[V-LOCAL / V-EXEC C336] Frozen input stays under
`local_data/tr46-observer-20261025/`; this phase's helpers/results stay under
ignored **`local_data/tr46-ai/`**:

- `audit.py`, `report.json`, `log-rows.json`: exhaustive line-pattern validation,
  counts/clock ranges, all source lines, named-country/creation bindings,
  capital checks, original evidence and current source hashes.
- `execute.asm`, `posting.asm`, `building.asm`, `division.asm`, cross-reference
  text: narrow read-only diagnostic paths, kept private. Execution warning
  string RVA **0xc82bd26**, routine **0x27bdb30–0x27be03a**; inspected posting
  helper **0x8055070–0x805537a**; building warning string **0xcda4a95**, routine
  **0x8053600–0x80545ec**; zero-division string **0xc4b0a88**, routine
  **0xf706f0–0xf70f18**. Addresses apply only to the hashed executable.
- Existing `local_data/tr46-expansion/` extractions are checked against their
  research manifest; both source saves retain their original manifest hashes
  and pass ZIP CRCs. No new token or save-reader interface is introduced.
- `research-manifest.json` pins the private artifacts and inputs; `check.log`
  records the project checks. No raw logs, save data, disassembly or substantial
  installed-script excerpt is committed.

All **37** original evidence hashes and **732** copied world-file hashes pass.
The current Steam manifest still identifies build **26142040**, executable
SHA-256 **`725a4c6ca50c0ef738f5ef0c00660637365ad01eebd462b39d61eac202714009`**;
the map fingerprint remains **`592e8309…03009a`**. The current generator and
installed LSI3 candidate remain 0.12.8 / epoch 38. No profile/save/settings/
playset modification, game launch, process control, push or publication.

[V-EXEC C336] Required locked sync and full check pass: **1,969 Python tests,
14 skips, 23 Rust tests**, formatting/lint/types clean. Private `check.log`
SHA-256: **`8a7af4d199f4b88f2dbce9950fc80ca70f928954a8fc1339546bf9fef99b9ca9`**.

## 7. Vanilla control through 1632

[V-GAME owner / V-EXEC C402] On 2026-10-27, the owner ran a campaign to 1632
with every mod disabled in the active `RNW` playset; the game showed standard
vanilla America. The full `game.log` records **47,935** script-system errors
across **343** `(source, error)` pairs. The largest are **27,579** invalid
`cabinet_action` comparisons at vanilla
`common/cabinet_actions/frustrate_annexation.txt:20` and **8,405** invalid
`is_situation_active` targets at vanilla `common/subject_types/tributary.txt:66`.
No located script-error pair names an RNW file. The complete list is retained
in the ignored [campaign audit](../../local_data/campaign-1632-20261027/audit.md)
and `script-errors-game-log.tsv`.

The same vanilla `ai.log` contains **88,540** invalid-command execution
warnings across **43** command names, including **55,771** `set_cabinet_action`
records (**62.99%**), plus **141** invalid-command posting warnings. The earlier
TR46 campaign had 57,156 execution warnings, of which 35,724 (**62.29%**) named
`set_cabinet_action` (C333). These raw totals come from campaigns of different
lengths and are not rates. The similar dominant command share establishes that
this warning family occurs without RNW; it does not identify which action failed,
which country attempted it, or why the engine rejected it.

C336's eight Workshop mounts remain a confounder for the original TR46 session.
C402 is an independent no-mod control and supersedes that limitation only for
the repeated base-game script errors and AI warning families observed here. It
does not settle the anonymous actors in the older campaign's division and
building diagnostics or establish their indirect effects.
