# TR46 — Tordesillas text and the wrapped western mainland

2026-10-25. Follow-up to [the problem register](tr46-observer-audit.md),
**TR46-L05** and **TR46-06b**; [experiment 062](../../experiments/062-tordesillas/README.md),
claims C337–C340. Original campaign: generator **0.12.3 / epoch 33**,
EU5 **1.4.4 executable / Steam 26142040**, on **1.4.3 data / 26105915**.
Current generator remains **0.12.8 / epoch 38**. Read-only investigation;
no new game run or generated-output change.

## 1. Findings and disposition

| Problem | Established evidence | Remaining limit |
|---|---|---|
| **L05: option text** | [V-GAME logs / V-LOCAL / V-EXEC C337–C338] One failed localization, four diagnostics; installed vanilla supplies the event and option text. The event saves `overlord` conditionally for a subject. | [UNKNOWN] Error-time recipient, subject status, saved scopes and viewing context are absent. A missing runtime scope is a supported investigation path; a universal syntax defect is not established. |
| **06b: western mainland shown as Britain's east** | [V-GAME owner, TR46 0.12.3] The owner clarifies that this is the **western continuation of the same generated mainland**, crossing the raster seam and drawn at the right edge. The treaty counted it as east for Britain. | [UNKNOWN] The specific affected location/claim and the line at the observation time are not identified. Keep the allocation defect open; do not reinterpret the report as merely a right-edge island or as geographically eastern America. |
| **Saved treaty state** | [V-EXEC C339] The 1590 checkpoint preserves **SPA west / GBR east**, the treaty's dates and line location **24717 / `rnw_loc_01224`**. This advances C305's earlier evidence limit. | [UNKNOWN] These are retained values after the treaty ended, not a capture of the reported allocation or L05's failed text evaluation. |

[V-GAME owner decision] Preserve full mainland crossing through the seam and
fix its support. The owner already rejected a prohibition on crossing land as
the goal. No further geographic-policy decision is pending in this block.

## 2. The localization failure and its inherited sources

[V-GAME logs / V-EXEC C337] Frozen `error.log:1730–1733`, **06:37:42**, records
failure to resolve/promote `overlord` in `overlord.GetNameWithNoTooltip`, then
failure to convert the statement and localize **`treaty_of_tordesillas.5.c`**.
The same four lines at `debug.log:48917–48920` are mirrors, not four more
incidents. No country, selected province, root or saved-scope payload is logged.

[V-LOCAL / V-EXEC C337] Installed sources are:

- `game/in_game/events/situations/treaty_of_tordesillas.txt`: event `.5` begins
  at **line 513**, conditional overlord capture at **535–540**, option `.c`
  at **637–646**.
- `game/main_menu/localization/<language>/events/situations/` and its
  `treaty_of_tordesillas_events_l_<language>.yml`: the option key is at English
  **line 38**, **line 34** in each other installed language.
- `game/in_game/common/generic_actions/treaty_of_tordesillas.txt`: the colony-
  transfer demand schedules `.5` for `selected_country` **seven days** later
  at **1873–1874**.

All **11** official languages, discovered from the installation, reference the
bare `overlord` identifier for this key: **10** call `GetNameWithNoTooltip`;
Russian calls `Custom('CL_DAT')`. This establishes the shared lookup dependency,
not eleven observed failures. The one logged expression does not identify the
effective UI language or prove every localized rendering fails.

[V-EXEC C337] The complete **807-file** original world inventory has no override
of that event or its vanilla localization files. Searching all **55** archived
world localization files finds no definition of the option key under another
filename. RNW therefore inherits these sources. C300's **eight Workshop mounts**
remain a limit on effective-content attribution; this is not a clean vanilla
reproduction or proof that another mounted resource made no change.

## 3. Scope availability, rather than an assumed spelling fix

[V-LOCAL C338] Event `.5` concerns a demand to transfer a colony, not the initial
choice of the division meridian. Its immediate effect saves the province
capital and saves `overlord` **only if the receiving country is a subject**,
using `top_overlord`. Options `.a` and `.b` require an independent country;
`.c` requires a subject and forwards `.5` to its top overlord after **two days**.
The event is also major, with `scope:actor` as its major-view trigger.

[V-LOCAL / INFERRED C338] The installed English localization of
`flavor_eng_diplomacy.1100` also uses the same bare
`overlord.GetNameWithNoTooltip` form, and its event script saves that scope.
The treaty itself uses bare named scopes such as `capital_scope` elsewhere.
Consequently, the L05 message does **not** establish that every bare saved-scope
reference is invalid or that adding an explicit scope accessor alone fixes it.
Source presence and engine resolution at a particular rendering are separate.

[INFERRED / UNKNOWN C338] A text evaluation without the conditional `overlord`
scope fits the diagnostic. Candidate contexts include rendering an unavailable
option for an independent recipient, a forwarded event or its major/observer
view, or a change in subject state before a delayed event. None is attributed
by the logs. The two save checkpoints retain no Tordesillas string in their
queued event records; they do not preserve the failed event's context or
selected option. A static source inspection cannot decide which context the
engine evaluated, or prove that the failure occurred while `.c` was available.

No generator spelling substitution, forced saved scope, global vanilla event
patch or warning suppression is justified by the evidence. L05 remains an
inherited-content/runtime-context issue with its missing state recorded.
The confirmed failure is the option's text resolution; no failed transfer,
blocked treaty or incorrect claim follows from that diagnostic alone.

## 4. What the saves now establish about the actual treaty

[V-EXEC C339] Reuse C326's read-only reader and independently validated complete
country handles/location IDs. The **1497.4.1** checkpoint has an empty treaty
situation. The **1590.11.11** checkpoint retains:

| Saved field | Value and binding |
|---|---|
| Status / outcome | `after` / `treaty_of_tordesillas_line_endures` |
| Start / end | **1549.10.2 / 1568.10.22** |
| West country | **910 / SPA** |
| East country | **161 / GBR** |
| Meeting location | **2819 / `madrid`** |
| West colony | **20158 / `rnw_loc_03269`**, `cuba_area` |
| East colony | **24722 / `rnw_loc_01352`**, `rnw_area_0052` |
| Retained line location | **24717 / `rnw_loc_01224`**, `rnw_area_0052`, `west_coast_region` |

The frozen original unit-stack locator for the line is **x 6229.5, z 6427.5**;
the east-colony locator is **x 6299.5, z 6308.5**, the west colony's
**x 3470.5, z 4033.5**. These are locator positions, not a newly decoded engine
comparison point. The line need not equal the initial east colony: the scripts
allow moving it. Retained post-treaty values do not reconstruct the full line
history. L05 occurs between the `NEW YEAR: 1563` and `1564` log markers; its
clock is not an exact recovered in-game date or proof of the observed map view.

[V-LOCAL / V-EXEC C339] The original world's situation differs from installed
vanilla only in two fallback colony-location rebindings:
`kururupu` → `rnw_loc_04114`, `lokono` → `rnw_loc_04054`.
The complete tooltip, primary-map-color and secondary-map-color blocks are
identical. The fallback keys are distinct from the two saved colony locations;
this does not prove whether a fallback was used earlier and later replaced.

[V-LOCAL / INFERRED C305, C339] Phase-one side shading and side tooltips use
`is_east_of` against `var_line_location`. Claim eligibility separately excludes
several Old World subcontinents. Actual province claims, ownership/top-owner
and conflicting area holdings can override or supplement the side shading;
the secondary color logic explicitly applies those overrides after its
east/west background. Whole-area/province claims are not equivalent to a
pointwise longitude split. Reusing a hierarchy name such as `west_coast_region`
does not itself select the west side of the meridian.

The previously traced `CIsEastOfTrigger` evaluator uses a map-dependent
positive/negative coordinate span (C305), rather than an established simple
linear comparison. A bounded follow-up traces the referenced global to
`CMap`/`CJominiMap`; it still does not establish the loaded span, exact comparison
point or affected western-mainland location. Do not substitute the unit-stack
locator for that unknown point, assume a half-world constant, or declare the
right edge correct/incorrect solely from raw x. The owner's clarified symptom
remains recorded even though its exact engine evaluation is unreconstructed.

## 5. Verification and remaining boundary

[V-EXEC C340] All **37** original evidence hashes and **732** copied world-file
hashes pass. Both saves pass ZIP CRCs and retain their frozen hashes. Cached
structure/extraction hashes match 059's research manifest. No save token or
writer is added. The current executable hash is
**`725a4c6ca50c0ef738f5ef0c00660637365ad01eebd462b39d61eac202714009`**,
Steam build **26142040**, map fingerprint **`592e8309…03009a`**.

Private helpers, exact source hashes, preserved-key save-root traversals and
reports stay under ignored **`local_data/tr46-treaty/`**; narrow binary notes
remain private and are registered in interoperability R-005. No raw scripts,
logs, saves, translated text, disassembly or substantial game excerpts enter Git.

Required locked sync and full checks pass: **1,969 Python tests, 14 skips,
23 Rust tests**, formatting/lint/types clean. Private `check.log` SHA-256:
**`1c783df9697a439f48403fc83775e0d4631d043df5eec022b40c767d7e3c7023`**.
No generator/output/version/epoch/install/profile/save/settings/playset change,
EU5 launch, process control, push or publication. LSI3 and hub 0.12.8 remain
installed. No new owner campaign is requested.

L05 stays open for the missing rendering context. TR46-06b stays open for the
reported western-mainland allocation, with the saved treaty identities/line
now recovered and the full-wrap policy settled. These are separate closure
conditions; solving text must not be reported as solving geography.

## 6. Generator implementation and candidate verification (0.12.9 / epoch 39)

[V-EXEC C341] `src/rnw/eu5_treaty.py` constructs continuous New World longitude
coordinates on the canvas axis across the raster seam for Tordesillas side
selection, line moves, side-swap estimates, map shading and final province
distribution. Coordinates are dry-land centroids, exposed via $O(\log(\text{width}))$
vanilla scripted geography bitmasks and script values:
- `in_game/common/scripted_geography/rnw_treaty_longitudes.txt`
- `in_game/common/script_values/rnw_treaty_longitudes.txt`
- `in_game/common/scripted_triggers/rnw_treaty_longitudes.txt`

Comparison predicates (`is_east_of`) in situations, events and actions are
rewritten to `rnw_treaty_is_east_of = { target = ... }` with exact count guards.
Province distribution iterators (`every_east_of_province_definition` /
`every_west_of_province_definition`) in `situation_effects.txt` are rewritten to
`every_province_definition` with `rnw_treaty_province_longitude > / < target`.
Vanilla claim gates, religion, ownership, existing claims and province effects
are strictly preserved without runtime variables, startup repair or engine changes.

[V-EXEC C342] Audit of continuous Tordesillas coordinates on TR46:
- The generated mainland wraps across the raster seam with 1 mainland crossing
  the boundary, containing **164 generated locations** across **30 provinces**
  at raster right (`x >= cut`).
- Under raw coordinate comparisons (`is_east_of`), all 164 locations evaluated
  as east of recovered line `rnw_loc_01224` (axis column 8335, world column 6228).
- Under the continuous axis, all **164 locations and all 30 provinces evaluate
  west of the line** in both predicate evaluation and final province distribution.
- Reversing the rewritten files restores source text byte-identically. All 7,324
  dry generated cells match physical centroids.

[V-EXEC C343] Generator 0.12.9 / epoch 39: all 1,978 Python tests pass, 14 skip;
23 Rust tests pass; format, lint and types clean. Golden reference world updated
(`RNW1-081WG-1HAWD-H0XFH-T0060-J0840-3C082-243AG-0C700-X3YQR`, digest
`3423df6d…cee01`, 837 files).
Comparing TR46 candidate 0.12.9 (**RNW: Continents QW6O**, 838 mod files, digest
`33ef2ed8…64bd`) against 0.12.8 (RNW: Continents LSI3, 833 files): all 831 other
nonmetadata files (geography, terrain, rivers, heightmaps, countries, pops,
diplomacy) are 100% byte-identical; only 5 added treaty files and 2 rewritten
situation files differ. Linux and Windows four-case parity matches, and the
Windows offscreen self-test passes. Runtime engine appearance and treaty events
remain unobserved [UNKNOWN].

[V-EXEC / V-LOCAL C344] With log and live checks confirming EU5 is closed,
candidate **RNW: Continents QW6O** was installed in `mod/rnw_exp_tr46_treaty`
(840 files checked) and the main hub was updated 0.12.8→0.12.9 in
`mod/rnw_exp_hub` (3,264 files checked). The old 3,262-file hub is externally
backed up under ignored `local_data/tr46-treaty-fix/hub-backup-before-0.12.9/`
and retained in `.rnw-install/retired/`. Nine profile-root hashes, 24,498
other-mod size/time records and nine prior folder entries are preserved.
No game launch, process control, push or publication.
