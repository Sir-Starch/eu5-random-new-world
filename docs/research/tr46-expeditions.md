# TR46 — Expedition lifecycle and the port/water assertion

2026-10-25. Follow-up to [the problem register](tr46-observer-audit.md),
TR46-L02/L03; [experiment 060](../../experiments/060-expedition-lifecycle/README.md),
claims C329–C332. Original campaign: generator **0.12.3 / epoch 33**,
EU5 **1.4.4 executable / Steam 26142040**, on **1.4.3 data / 26105915**.
Current generator stays **0.12.8 / epoch 38**. No new game run or output change.

## 1. Corrected accounting

[V-GAME logs / V-EXEC C329] The original catalog grouped one engine origin by
its first message and mistakenly described all 178 records as mining surveys.
Reading every message gives this split. Total origin/record counts are unchanged;
mirrors in other logs are not additional incidents.

| Diagnostic | Records | Evidence and disposition |
|---|---:|---|
| Mining survey exhausts its route | **177** | 46 owner tags and 46 locations; all destinations in the Old World; inherited lifecycle edge cases below |
| Pacific crossing exhausts its route | **1** | `error.log:1824`, **06:41:55**, SPA, location **16084 / dadinga_bay**; separate from the western voyage |
| Resume of a non-stalled expedition | **38** | No type, owner, leader, location or event is logged; exact callers remain unknown |
| Start with an ineligible leader | **38** | Same missing context; no specific type or RNW country can be assigned |
| Start of an unavailable type | **4** | Same missing context; do not merge with the leader failures |
| Western voyage pathfinding/discarded waypoint | **3 + 3** | Previously diagnosed port-role remapping defect; offline candidate in 0.12.7, runtime result still unobserved |
| Port/water assertion | **1** | `error.log:1574`, **06:32:02**; affected object and caller remain unknown |

[V-EXEC C329] Locations use the original frozen definition order, independently
bound to both saves in C326. All **177** mining destinations are retained:
**136 Europe, 34 Asia, 7 Africa**. None of their logged owner tags is one of
the 659 original generated tags. These are not failed journeys between the
generated American oceans. This does not exclude an indirect mod interaction
or prove that the effective session was clean vanilla: C300's eight mounted
Workshop resources remain a confounder.

## 2. Mining surveys: an inherited route with no travel

[V-LOCAL / V-EXEC C330] The complete archived world inventory contains no
override for `common/expedition_types/mining_survey.txt`,
`events/expeditions/mining_survey_events.txt` or
`common/scripted_effects/expedition_effects.txt` (all under `in_game/`). They
are inherited from the installation, subject to the other mounted resources.
RNW does not rewrite their lifecycle.

[V-LOCAL C330] The installed mining type starts at the capital. Both eligibility
blocks accept a country whose only suitable hill/mountain mineral location is
that capital. Route construction then excludes the capital from its up-to-four
survey stops and appends the capital as a return waypoint. There is no explicit
end effect in the type; its arrival callback handles owned noncapital highlands
only. It also has no failure cleanup for its two country variables. The installed
expedition README says a waypoint equal to the current final path entry is
silently discarded, and explicitly requires a no-travel dynamic start to end
or fail itself.

[V-EXEC / INFERRED C330] With only the capital eligible, the constructed route
has **zero transitions**: the sole proposed destination is the current origin.
A private script/readme model reproduces that construction, not engine execution.
Using the frozen **1337** ownership and terrain/resource templates, **33 of the
46** logged country tags already have this capital-only eligible set. Examples
include RAG/Dubrovnik, LCA/Bellinzona and CEB/Singhapala. Those 33 tags account
for **138 of the 177** later failures. This is a concrete inherited content
edge case matching the diagnostic, not proof that all 138 later launches still
had that ownership/resource state. Captured data cannot reconstruct every launch.

[V-EXEC C330] **136** failed rows name their country's frozen starting capital.
Comparing to the later snapshots, **166 / 162** rows name their country's
1497 / 1590 capital (**41 / 40** distinct countries). These comparisons support
capital arrival/no-travel as an investigation lead; later capitals are not the
runtime capitals at every error. Dynamic country tags and subsequent capital
changes explain why a starting-capital comparison is incomplete.

[V-LOCAL / UNKNOWN C330] The same installed README documents
`should_end_at_last_waypoint` as defaulting to yes. The mining type omits it.
That does not rescue the separately documented no-travel start case. It also
does not establish the loaded default, every callback/wait interaction or a
binary regression: a limited trace of the exhausted-route diagnostic does not
decode those semantics. Do not claim that a normal completed journey must fail,
or that adding an explicit default fixes all 177 messages.

**Disposition [INFERRED C330]:** a generated-ocean or native-expansion fix is
not justified by these rows. Preserve this inherited lifecycle finding and its
limits. Do not change Old World resources, globally replace the mining type,
grant completion rewards or silence errors as a workaround. Absence of failures
in a clean matching-build run is not established, and none is requested here.

## 3. The separately missed Pacific failure

[V-GAME logs / V-EXEC C331] One of the 178 exhaustion messages is Spain's
`pacific_crossing_expedition` at **Dadinga Bay in Asia**, not a generated location
or the western voyage's inland landfalls. Both saves' validated location-ID
contract maps **16084** to `dadinga_bay`.

[V-LOCAL / V-EXEC C331] The original rewritten Pacific type's complete
`on_start` block is byte-identical to installed vanilla. It selects an American
departure port and queues that port, Pago Bay, Samar Sea and finally Dadinga
Bay. The Dadinga arrival branch calls `pacific_crossing_events.5`. That event's
complete block is also byte-identical to installed vanilla. Its first two
options schedule event `.6` **ten days later**, add no waypoint and add no
pause; the event's `after` resumes the expedition. Option three adds a
30-day pause as well as the same delayed event; option four ends the run and
is assigned zero AI weight.

[V-LOCAL / INFERRED C331] Event `.6` supplies the return-route choice and its
waypoints. Consequently the first two `.5` options expose a gap at the current
last waypoint: resume now, provide the next route later. This violates the
README's documented requirement to have a route, an end/failure, or an active
wait/stall at the last waypoint. It fits the observed failure at Dadinga and
is inherited unchanged in this part of TR46. The callback and its event target
remain unchanged; later American return destinations are the remapped part.

[UNKNOWN C331] The log does not record which option Spain selected, whether
the delayed event later resolved, or the exact expedition state. Therefore
this is a strong static lifecycle explanation, not a replay or proof of the
specific selected option. Neither checkpoint retains an active Pacific crossing
or western voyage. The 0.12.7 access-role correction addresses a different,
previously proven remapping defect; it does not close this inherited lifecycle
gap. No global vanilla expedition patch is added.

## 4. Unattributed resumes, launches and L02

[V-LOCAL / UNKNOWN C332] The installed generic expedition action checks type
availability in `allow`, filters its leader selector and then calls the start
effect with the selected objects. Separate pilgrimage and treasure-voyage
actions also call that effect. None of those three action files is overridden
by the archived world. Their existence does not identify which path produced
the **4 / 38** rejected starts or prove a cached-target race. The rejection
messages contain no country, type, leader, event or call stack. The **38**
resume messages are likewise anonymous. The fact that many expedition events
resume after options is insufficient to assign all resumes to mining, Pacific
crossing, another event, an engine defect or RNW.

[V-GAME logs / V-LOCAL / UNKNOWN C332] The lone L02 assertion's only recorded
invariant is that a new destination must have a port or be water. C317's
read-only trace locates a destination-change routine with recursive handling
of associated objects. Looking at its possible static call sites still does
not supply the runtime caller, object, location or transport state. Nearby
log timestamps are not causal evidence. No saved assertion record or matching
active voyage reconstructs the event. **L02 stays open and unattributed.**

[V-EXEC C332] The 1497 checkpoint contains **three** active expedition objects:
one mining survey waiting on construction and two relic expeditions. The 1590
checkpoint contains **two** cartographic surveys. Tombstoned database slots
are excluded. These are snapshots, not a list of every expedition that ever
ran, and do not retain the missing lifecycle transitions. Save reading reuses
C326's private fail-on-unknown reader, including complete object handles.

## 5. Reproduction, preservation and remaining work

[V-EXEC C329–C332] Private results and independently authored diagnostic helpers
are under ignored `local_data/tr46-expeditions/`:

- `audit.py` / `log-audit.json`: every named failure, definition mapping,
  continent, owner frequency, installed source hashes and current fingerprint.
- `flow.py` / `flow-audit.json`: complete-inventory absence checks, exact vanilla
  block comparisons, the no-travel script model and the 33 initial country cases.
- `saves.py` / `save-expeditions.json`: limited expedition/capital traversal of
  both frozen saves; cached structure and reader from `local_data/tr46-expansion/`.
- `finalize.py` / `final-report.json`, `research-manifest.json`: aggregate
  consistency and original evidence hashes. Limited disassembly stays private;
  it is not a distributed executable interface or a generalized engine model.

[V-EXEC C332] Current map fingerprint remains
`592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`.
All 37 original evidence-file hashes and 732 archived world-file hashes match.
Required locked sync and full check pass: **1,969 Python tests, 14 skips,
23 Rust tests**, formatting/lint/types clean. Check log SHA-256:
`4f3808bcb6acdd5ab18cb6c90ed48ad7a66a02bdc2b499b2a8efa73728314b9e`.
No save, installed game, profile, playset or existing world is edited.
Interoperability R-005 records the narrow
extension of the read-only investigation. No new generation or installation
is necessary for these documentation findings.

The remaining L03 gaps are exact attribution of anonymous calls and confirmation
of the inherited lifecycle behavior in the engine. They remain recorded unknowns,
not a request for another campaign. L02 needs an identified runtime case before
an appropriate generator correction can be designed. The next independent
diagnostic block is L04's AI command rejections and expansion arithmetic.
