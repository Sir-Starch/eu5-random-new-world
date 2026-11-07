# History core, societies and bootstrap

[V-EXEC, 2026-11-03] This implements the offline H2–H3 phases and H4's
bootstrap, population, final-plan construction and localized text writers in the accepted
[history plan](history-plan.md#17-phases-and-scope-control). H4 now connects them to
normal generation for the **1.2.0 development target / pending epoch 61**. The
frozen 1.1.0/epoch-60 reference is preserved. H5 portable reading/controls and [H6 story continuity](content-plan.md#history-continuity-h6-120-development)
are implemented. H7's technical checks and local package audits are complete,
but held-out S4 sweep, S5 and S7 thresholds fail; the candidate is not accepted.
See the [final calibration report](research/history-120-calibration.md#final-held-out-acceptance-and-local-delivery).
The 2026-11-05 [audit](history-plan.md#21-independent-audit-and-redesign-2026-11-05)
keeps this model, replay and projection. [R1–R5](#audit-redesign-r1r5-2026-11-05)
have replaced the fixed integration ceiling, causeless submission, aimless
proposals, uniform founding authority and chronicle selection. Sections below
describe earlier phases in their own dated scope, where the redesign section
overrides them. R6 calibration, held-out validation and delivery remain open.

## Ownership and entry points

| Module | Owns |
|---|---|
| `history_model.py` | Frozen integer records: geography, cohorts, founding actors, lifecycle/lineage, holdings, agreements, directed memories, proposals, sparse effects and events |
| `history_checks.py` | Physical-route, partition, seat, agrarian support, lifetime and dependency invariants; sparse graph index |
| `history_context.py` | Immutable round lookup, physical contacts, travel, coordination and integration burden |
| `history_actions.py` | Prior-snapshot prerequisites, conflict resolution, commitments, directed memory and joint inheritance |
| `history_societies.py` | Eight-dimensional profiles, repeated-problem reforms, conservative migration and local inheritance |
| `history_trajectories.py` | Eligible per-hearth ambitions, recognition of actual structures and seeded/realized counts |
| `history_engine.py` | Canonical bootstrap, local proposal policy, arbitration, atomic rounds, simulation through 1337, causal replay and semantic digest |
| `history_routes.py` | Bounded physical routes from actual generated cell contacts and water paths, including seam edges |
| `eu5_history.py` | Post-diaspora population roots, installed prerequisites and the fixed landed/tribal/community partition |
| `eu5_history_build.py` | Normal construction bridge: physical routes, ordinary roots, installed technology, simulation and final projection |
| `history_population.py` | Conservative projection of historical migration into the original typed EU5 cohorts |
| `eu5_history_plan.py` | Surviving countries, governments, explicit group memberships, settlement centres, discovery, roads and the single `FinalStartPlan` |
| `eu5_history_values.py` | Installed ungated American axis ranges and bounded profile positions |
| `history_diplomacy.py` | Actual bargains, eligible engine relations and bounded directed opinion bundles |
| `history_plan_checks.py` | Independent agreement checks against the surviving history, including causal opinions and overlapping memberships |
| `history_text.py` | Typed chronicle rows, bounded event selection and original opinion/chronicle templates |
| `eu5_history_text.py` | Historical bias definitions, live-country trigger, voluntary decision/event and directed guarantee records |
| `history_archive.py`, `history_archive_checks.py` | Bounded portable facts, compact ancestor references and independent atlas/lifetime/ownership checks |
| `history_content.py` | Surviving historical cooperation and dependencies for existing stories, including landed confederates |
| `history_presenter.py` | Shared localized society, chronicle, relationship and regional reading for both windows |
| `history_output_checks.py` | Parsed artifact checks for bias values, live scopes, decision/event effects and localization bindings |

`create(geography, foundings, seed=..., empire_permille=250, checkpoint=...)`
validates the caller's complete inhabited partition and records each founding and
eligible extraordinary ambition. It does not fill missing holdings, create
countries or invent population. The adapter must supply only generated New World
actors; the core has no game tags, installed inputs, resource roll or localization.

`advance(history, proposals, checkpoint=...)` runs one five-year round.
`simulate(history, turbulence=500, policy=None, checkpoint=...)` runs all remaining
rounds from 1037 through 1337. Its optional policy supplies proposals, not outcomes:
it passes through the same eligibility, arbitration and transition rules. The
normal policy ranks at most three eligible local choices per living actor.

`validate_history(history)` reconstructs the bootstrap and replays every recorded
proposal through those rules, then compares every event and final fact. It rejects
missing/future/cyclic causes, changed outcomes, unexplained holdings, profiles,
population, ambitions, memories or agreements, and inconsistent lifecycle data. `digest(history)` hashes canonical
semantic data; no text, timing or process hash order enters it. The dataclasses are
an internal interface, not the portable history format planned for H5.

## EU5 bootstrap boundary (H4, first part)

`societies.bootstrap_societies` reuses the existing population, identity-zone,
agrarian-seat and territorial construction. It gives no polity an extraordinary
outcome. The extraordinary control goes to the history engine's per-hearth
ambitions instead. Its provisional size factor is 1; the accepted 0.4–1 interval
changes ordinary partition size while leaving the state-land budget/pocket size,
food, population, identity zones and hearths unchanged. It is not fitted on the
held-out seeds. The exporter calls this bootstrap through `eu5_history_build`;
the old static constructor is retained explicitly as a diagnostic helper.

`physical_routes(PhysicalMap(...))` reads actual world edges. Land contacts include
explicit wrap edges. A maritime path travels only through SEA cells and stops
after at most four water cells, counted from the departure coast. Lake cells,
shared sea-zone names and routes that walk through an intervening land cell
cannot manufacture a maritime connection. Duplicate alternatives choose the
shortest passage; a direct land contact takes precedence. `routed_graph` supplies
these same passages to society construction before any polity is made. History
uses the individual passage costs; the existing society partitioner retains its
conservative common sea-link cost.

`bootstrap_history(BootstrapInputs(...), seed=..., empire_permille=...)` receives
the typed population **after diaspora**. Its immutable roots include every
culture/faith and every peasant or elite, retain the calibrated/diaspora totals
separately, and fail explicitly on missing population, technology or geography.
Every inhabited location belongs to a state, pop-type tribe or unorganized
community. Communities are connected components of the same dominant identity,
with no exported country tags. Founding authority has its own random stream,
independent of donor identities and government templates. Existing seeded empires
or already-landed confederates are rejected at this boundary.

`installed_rules` supplies the actual installed agrarian floor, minimum overlord
technology, republic level and confederate density. [V-LOCAL, 2026-11-03] The
installed Steam manifest is build 26377361 (EU5 1.4.7); the read-only native
calibration check exercises this adapter. No game is launched. Food headroom is
provisionally `post-diaspora population * farming potential / 4000`, or 0–25%.
This permits conservative movement without reading an RGO or inventing a
demographic growth estimate; its calibration belongs to H7.

`project_population(bootstrap, history)` follows accepted migration effects from
those exact roots. Farmers move in the recorded amount; non-farmer types move
proportionally with deterministic largest-remainder rounding. It checks every
consumed population change, agreement with the final settlements, and exact
global totals for each `(pop type, culture, religion)`. Conquest, unions and
division never retype, assimilate or recreate the inhabitants. Missing capacity
or cohorts fail in construction, rather than a later repair.

This bootstrap feeds the final-plan construction below. The new localization,
decision/event writers, exporter switch and written-output checks remain the next
H4 part. No new EU5 text format is written yet; pending epoch 61 starts when that
integration first changes world bytes. Candidate/hub delivery remains H7.

## Final start projection (H4, second part)

`project_start(ProjectionInputs(...))` replays the supplied history, projects the
exact typed population, and constructs one `FinalStartPlan`. Only living landed
actors and pop-type tribes receive fresh country tags. Extinct predecessors and
unorganized communities retain their facts in history. Country holdings, seats,
capital identities and inherited technology come from that history; a realized
empire alone receives the calibrated empire level and rank. Every result passes
the independent `validate_projection` checks before being returned.

Profiles map to positions read from the installed ungated American template
ranges. Missing definitions or malformed ranges fail. Unobserved axes remain
internal. Authority selects among usable calibrated governments: councils use the
republic when they meet its technology floor; a sacred state uses the compatible
theocracy when it can use its institutions. A sacred overlord retains a template
that meets C99's proven overlord prerequisite. Lower-technology councils and
customary landed authority retain the ordinary template; their exact society
profile remains available to H5's summary. Donor style cannot impose a republic
on a ruler, or provide an institutional advantage.

`HistoricalGroup` retains full actor membership, exported country membership,
hearths and actual causes separately. Countries can participate in several
structures. A sacred centre's visitors do not acquire the host's government or
host role. Identical groups supported by more than one hearth combine their
causes. Overlapping highland groups project their actual connected pact network
to one organization, preserving the installed rule that a country can join only
one tribal confederation. Confederates keep the aggregate agrarian prerequisite.

Engine treaties and startup opinions use living landed countries with an
explicitly written capital. Pop-type and community bargains remain in history;
recognizing a qualifying highland confederation enables its landed projection.
Named opinions retain their actual memory factor, cause, year and recorded place.
Each factor copies a vanilla event opinion (`rnw.opinions.ANALOGUES`, plan D31):
the analogue's decay, and its value times the surviving share of the factor's full
weight (`FULL`), rounded away from zero. Selection admits at most four per direction and
2,000 per world. An allied direction selects trust and only grievances its budget
can carry. World limiting keeps each selected direction together, so it cannot
remove trust while leaving its grievance. No cause, sign or value is rewritten.

Alliances follow actual pacts; rivalries require surviving recorded hostility.
Protection projects only where the guarantee's subjecthood/rank prerequisites
allow it. Exchange creates centres and physical land roads within the participants'
territories; a water route never becomes a road. Markets, calibrated settlement
ranks, population totals and discoveries are recomputed from surviving outcomes.
The AI adapter reads full historical threat/competition facts and actual group
roles independently of which opinions fit the display limit; guarantees also
enter its context.

The exporter now reads this plan through the H4 bridge. No static empire,
archetype, ring-alliance or vassal selector adds relations after simulation.
No full-world calibration or game loading is inferred from this construction.

## Localized history artifacts (H4, third part)

`history_text.chronicles(plan)` selects at most eight distinct recorded events
per living country and orders them by year and canonical key. Its own origin and
surviving relationship causes take priority; recorded predecessors supply context.
Refused proposals and seeded ambitions are omitted. A quiet founding gets one
entry marking the **beginning of the record**, not an invented foundation date.
Failed attacks and resisted reforms have their own factual templates. Directional
bargains and migration read roles from typed effects, while conflict prose stays
neutral about the participants' sides. No battle names, casualties or personalities
are invented. Rows retain event/year/family, one to three actors and an optional
recorded place. Two original templates per displayed family vary independently
of simulation draws, using the existing names renderer and translation catalogues.

`eu5_history_text.build(plan, keys)` writes each causal `rnw_hist_*` bias with its
bounded value and decay; its name gives the memory family, actual cause, year and
optional place. It also writes a live-generated-tag trigger, one repeatable
**Our History** decision with `ai_will_do = { value = 0 }`, and one country event.
The decision's only effect opens that event. Conditional descriptions choose the
country's chronicle. The closing option has no effect; no startup hook or cost is
written. Pop-type tribes have chronicles too. Extinct predecessors occur in prose,
never as live script scopes. An empty country set writes no trigger/decision/event.
Dynamic chronicle keys use the shared collision-aware `KeySpace`; a collision of
the fixed interface keys fails explicitly. `guarantee_lines` writes the already
projected provider → client pairs for setup diplomacy.

`game_texts.localize` renders nested typed sentences and chronicles through the
existing catalogue checks. All 59 new English source texts have current translations
and fingerprints in the other ten official languages. `history_output_checks.verify_text`
reads the written files back and checks exact bias values/decay, live country scopes,
decision/event activation and effects, unique description bindings and localization
coverage. It rejects added effects, startup hooks and changed AI access. The
normal export includes these artifacts and renders their entries into each official
language. `verify_diplomacy` checks the written provider/client direction and
counts while preserving the Old World's directed relations. Game loading and
F1–F3 retain their H7 scope.

## Export integration (H4, fourth part)

`eu5_history_build.build_history_start` replaces the static constructor in normal
generation. It supplies bounded physical contacts before ordinary society
construction, adds identity-completeness diaspora, reads founding technology from
the installed templates/quantiles, places holy sites, simulates all 60 rounds and
projects the survivors. A tribal template with no technology declaration counts
as zero, using the existing calibrated template rule; no explicit tribal level
is written. Profiles use ranges read from the installed ungated American templates.
All history calls receive the generator's cancellation callback. The resource
roll does not enter this bridge; the new synthetic 64-location flow verifies that
changing RGOs leaves history, countries and population identical, both with states
and at zero state share.

The output boundary revalidates historical facts and then reads back technology,
governments, institutions, ownership, ranks, roads, opinions, alliances, rivals and
confederations. The proven installed prerequisites remain: usable templates,
eligible lord technology, proper confederate institutions and discovered partner
capitals. Legacy diagnostics alone retain monotone final-capital technology,
disjoint archetypes, ring alliances and reciprocal static rivals. New roads may
follow actual exchange agreements as well as realized empires. Additional
written-setup cases exercise the divided valley, a star-shaped sea alliance,
overlapping confederate hearths, rejected fabricated roads/changed capitals and
wrong, missing or repeated guarantees, including Old World preservation.

The product target and lockfile are 1.2.0, with a pending epoch-61 entry and new
synthetic bundle/preset pins. `golden_world_epoch60.json` preserves the prior
reference byte for byte; no published golden or release is overwritten. H7 still
owns calibration, held-out seeds, package/candidate/hub delivery and its one
bounded engine observation. The reference measurement below records the actual
scope of this development export, without claiming H7's statistical thresholds.

The first large reference exposed two repeated traversals. Migration eligibility
now reads the round's indexed set of actors with active fear/grievance, rather
than rescanning all memories for each possible move. Ancestry-root lookup visits
each actor once when division/reunion paths reconverge. Independent full-scan and
recursive references verify equal results, including expired memories and a
16-generation shared ancestry DAG. Existing semantic/text digests remain equal.
This removes redundant work without changing proposals or outcomes; it is not
an H7 performance acceptance result.

The same indexes retain current subjects, pact participants and recent exchanges.
Candidate pacts/protection are enumerated only for a threat both parties actually
remember; an exhaustive reachable-triple reference verifies that the eligible set
is unchanged. Installed government handling distinguishes country overrides from
the effective type/heir inherited through templates. The historical projection
uses the latter; the legacy serializer's minimal override table stays unchanged.

### H4 integration evidence

[V-EXEC/V-LOCAL, 2026-11-04, EU5 1.4.7 / build 26377361] Locked sync and
`make check` pass: 2,674 Python tests, 17 optional skips, strict types, format/lint
and 23 Rust tests. All 15 installed-game read-only checks pass. Two complete
synthetic physical-bootstrap cases (64 locations, including zero state share)
preserve history under resource changes. Written setup tests cover historical
groups, changed country records, unsupported roads and direction/count/Old World
checks for guarantees and vassals. Existing synthetic semantic/text digests agree.

The real 5,903-location native stage completes all 60 rounds, full causal replay
and independent final-plan checks: 324 states, 412 tribes, 255 subject pairs and
2,000 bounded named opinions; exact population is 72,176,637 milli-pops, including
22,500 diaspora. A full output run reuses that independently constructed stage
**after exact relevant-input comparison**, claims its generated keys in the same
key space, and passes all output verifiers. Its 872 nonmetadata files have digest
`5b2d5940693639f50ce551f8ca21a9a5951abfd311cd5108ea4af7a04abdf526`.
This is model/writer agreement, not an uncached end-to-end timing or an engine
loading claim. `tests/golden_world.json` records the pending reference; the exact
tagged 1.1.0 file is preserved in `golden_world_epoch60.json`.

Profiling the standalone native stage observes about 1.08 billion calls and
149,550 events; its 134 MiB private pickle and 2.31 GiB profiled process peak show
that H7's time/memory limits are **not yet established**. Early instrumented runs
were interrupted or failed before output; one diagnostic traceback run exited
139. They are not passed references. The completed model and plain cached-stage
output checks are recorded separately in ignored `local_data/history-120/h4-export/`.
Normal final-source reproduction, performance calibration, reading, content
continuity and delivery remain the next phases; EU5 was never launched.

## One round

### Compact causal state (H5 foundation)

The current snapshot retains only memories whose value is still positive at its
year. Original memory effects remain in the immutable event journal. A participant's
causes use a temporal frontier: a current fact from an event that already cited
that participant's prior facts covers older facts through the same ancestor chain.
Same-round facts remain explicit. Combat events are not such witnesses because
their participant list may include supporting allies. Reform experience and
restored founding institutions retain their explicit references.

The proposal and arbitration steps reuse the same immutable context, and reform
candidates are cached against the complete actor value. Canonical JSON visits
dataclasses directly instead of first making a recursive copy. Independent tests
compare full ancestor closure and all outcomes against the previous all-facts
reference, fresh contexts and uncached reform candidates; the digest matches the
recursive JSON reference. The current divided-valley digest is
`5847d16874fbf80e11198f913fda5d57d09bf247d54a0eda320f4801470061c0`;
the earlier H3 digest below retains its dated scope.

[V-EXEC, 2026-11-04] The real 5,903-location case preserves every H4 country,
cohort, projected relation, rank/market/road, proposal and event outcome. Direct
causal edges fall from 19,441,390 to 1,821,134; 50,203 active memories remain in
the final snapshot. Its private pickle falls from 134 to 49 MiB. A standalone,
unprofiled native-stage run takes 97.944 s and peaks at 906.5 MiB (inputs captured
from the real export); this is not a paired end-to-end S8/S9 result, and H7's
limits remain outstanding. Full checks pass: 2,683 Python tests, 17 optional
skips, strict types, format/lint and 23 Rust tests. Evidence and exact H4 parity
assertions are in ignored `local_data/history-120/h4-export/native-compact.*`.

### Round execution

All proposals read the same immutable snapshot. Physical contacts come from actual
land links or explicit coast-to-coast routes with a bounded number of sea steps.
A shared region or sea name grants no access. A direct exchange can open one
physical intermediary; an indirect agreement cannot fabricate another route.

Arbitration orders action priority, proposal rank and a seed-derived tie draw.
Each actor has 1,000 commitment units. Contacts cost 50, exchange/access 100,
protection 300, defence pacts/submission 400, migration 200, and a conflict or
pressure episode 600 plus up to 200 integration units from each principal;
unions and divisions reserve the participants' full budget. An allied or subject
contribution uses up to 300 of its remaining units. Conflicting obligations never
let one ally contribute to both sides. The journal records the actual allocations.
A subject gets one overlord; a new submission cannot also create an independent
pact in the same round. The next round starts with fresh commitments.
Reform costs 300 plus half the current tradition and one tenth of the combined
centralization/integration scores (at most 1,000). Only one reform and one movement
per participant can commit in a round. A movement cannot share a participant with
a territorial conflict: both evaluate the old agrarian support, so combining them
could otherwise spend that support twice.

The constructor accumulates all accepted effects and builds the round's fact
tables once. Two independent unions can occur together: inherited knowledge and
memory are computed using both successor mappings. The joint consequence belongs
to the later transition in canonical journal order and cites the earlier one;
neither proposal evaluates that consequence. This keeps the causal graph acyclic
without sequentially exposing new countries to other proposals in the round.

Invalid inputs raise `HistoryError`. Ordinary refusals and failed conflicts are
recorded with typed outcomes/reasons. A refused action changes no facts and spends
no commitments; a repelled attacker spends its commitment and leaves a different
directed memory. Every committed round checks the fixed tenure partition,
connected territory, viable seats, agrarian support, acyclic dependencies and
exact population/peasant conservation for every culture–faith pair.
No finished-territory repair or silent fallback follows the transition.

The callback can be `Progress.checkpoint`; it is called within graph construction,
actor evaluation, travel searches, arbitration and replay. Cancellation raises
before publishing a new immutable result and leaves the caller's history intact.
The core writes no files or existing worlds.

## Current action contracts

- **Contact/exchange:** verified access precedes knowledge; both partners must
  already know one another before an exchange. Kept exchange renewals create
  trust in both directions, with a minimum 15-year renewal interval.
- **Union:** landed neighbours, no subject commitments at either endpoint,
  sufficient mutual recorded trust and no strong grievance. It retires the
  predecessors and creates a council union with a viable existing seat and
  explicit lineage. It never converts tribal/unorganized districts into land.
- **Conflict:** a known, reachable landed neighbour, a grievance or a real power
  opportunity, and a valid proposed transfer. Strength combines population,
  farming support, technology, seat-to-frontier travel, defensive approaches,
  coordination, posture, actual allied/subject contributions and bounded integer uncertainty. Partial
  conquest cannot remove the surviving opponent's seat or farming support;
  complete annexation retires the defeated actor. A multi-district annexation
  resolves at an actual reachable frontier, rather than the first sorted interior
  place. New, heterogeneous and distant holdings consume integration capacity;
  a proposed conquest beyond that capacity is refused. Conquest changes no cohort.
- **Pressure/resistance:** an offensive landed actor can confront a known,
  physically bordering tribe/community when its power is at least twice theirs.
  It uses the same bounded contest, defensive approaches and allied commitments,
  but can never transfer tribal/unorganized territory. Its recorded threat or
  repelled attempt supplies a reason for common defence; a large neighbour alone
  still grants no fear or pact.
- **Submission/protection/pacts:** submission needs a power imbalance, a capable
  lord and an acyclic graph. Independent pacts require free participants and a
  reachable third party they have actually feared or fought; mere different
  faith or a large neighbour is not enough. Existing pacts cannot be silently
  discarded to accept submission. Protection also needs a recorded common threat.
- **Division:** a real former union, at least 25 years of continuity, a concrete
  distance/institutional obligation problem, and a complete disjoint partition
  into connected, supported successors with viable seats. The current automatic
  policy offers viable original founding territories only when they cover the
  current holding exactly; it does not repair a failed partition.
- **Sacred access:** both parties know each other, the real centre belongs to
  the host, and hostility does not rule out a bargain. The agreement records its
  place and cause; it is not yet a written EU5 opinion.

## Society profiles and reform

Each actor holds one immutable `Society`, with a cause pointing to its last
profile transition. Foundings can supply a profile; otherwise named peoples-seed
streams and the existing farming/coastal opportunity supply it. Donor culture and
faith names grant no profile score. Numeric dimensions are integer permille;
categorical dimensions are typed values. No EU5 position is written in this phase.

| Dimension | Current consequence |
|---|---|
| Centralization | Mobilization/coordination and travel efficiency, with continuing administrative overhead and reform cost |
| Authority | Union inclination, eligible institutional responses, sacred-centre and council-network recognition |
| Livelihood | Food-supported mobilization and the propensity to move; it never converts a tenure class or creates peasants |
| Exchange orientation | Contact/exchange inclination; overland/coastal reform requires the corresponding physical opportunity |
| Religious authority | Sacred-access inclination and credibility, caused sacred reforms and centre recognition |
| Military posture | Offensive/defensive contest tradeoff, conflict/common-defence inclination; pressure requires offensive intent |
| Integration | Cost of distant, heterogeneous and recent conquests, admission of new minorities, and reform overhead |
| Institutional tradition | Credibility of kept bargains, reform cost and resistance, and the propensity to retain institutions |

A reform changes exactly one dimension: a numeric step of 100 or an eligible
categorical response. It needs experience in at least two distinct prior rounds
within 75 years, after the current profile was established, and a 15-year interval
since the last reform attempt. Cooperation can support councils, exchange and
institutional continuity; repeated confrontation/displacement can support defence,
coordination or changed institutions; incorporation can support integration;
actual repeated sacred access can support religious authority. Each reform cites
the recorded experience. Deterministic resistance can fail the reform while
spending its commitment; ordinary ineligibility spends nothing. A quiet actor
does not reform to fill a quota.

Unions inherit population-weighted numeric experience and the seat's livelihood,
exchange and posture, with council authority as their explicit bargain. A division
combines the common experience with each local predecessor's last recorded
profile and the partition's authority; local pre-union reforms are retained in that
inheritance. Neither transition alters culture, faith or the fixed tenure partition.

## Conservative migration

`Geography` retains the bootstrap cohorts; `Snapshot.settlements` holds the current
cohorts and the last movement cause. Capacity is the original population plus the
district's explicit nonnegative `headroom`. Its default zero grants no spare space.
The H4 adapter must derive any headroom from physical/food opportunity, not RGOs.

A move needs two known, nonhostile holders and a direct verified physical route
between inhabited locations. No settlement expansion or uninhabited destination
is introduced. The origin must be at least 90% full, recently conquered or under
a recorded threat/grievance. A destination needs space; a new culture–faith
minority also needs integration of at least 500. At most 10% of one existing
cohort moves, with its proportional integer peasant count. Both countries and
seats must remain agrarian-viable. Population, farmers and every identity total
are conserved, including through conquest, union and division. Commitments and
participant reservations prevent simultaneous movements from overfilling a place
or spending the same population twice. There is no assimilation, mortality,
demographic growth or hidden redistribution.

## Extraordinary trajectories

The caller supplies actual hearths/domains and the installed technology and
density floors. One independent chance/choice stream per hearth seeds at most one
eligible ambition. Great-empire opportunity needs a connected landed domain of
the calibrated minimum size and a complex centre; sea leagues need three to five
eligible coastal states, a real bounded sea connection and land separation;
highland confederations need three to six touching, sufficiently populous tribes
of one faith with at least 60% highland locations; sacred centres use the most
populous place of their faith, an upper-quartile host and neighbouring peers.

The ambition records institutional inclinations only: central/ruler ambition,
coastal council cooperation, highland common defence or sacred authority. It grants
no ownership, population, technology, rank, pact or automatic rival. At chance zero
none is seeded and ordinary history still runs. Domains may overlap through
explicit memberships; a common sea name supplies no physical reach.

`realizations(context)` recognizes the current supported empire, connected actual
pact/exchange network, or negotiated sacred access. The centre must still be held
by a seeded actor or its recorded successor. Failed ambitions remain recorded;
`report(context)` counts seeded and realized structures separately. A fractured
realm is never seeded: it requires a real division of a recorded union, three or
four living, connected, complex, same-faith successors of comparable populations
and sufficient combined territory. A later conquest or dominance can end that
recognition. These facts will feed the calibrated EU5 adapters in H4.

The coefficients and action propensities remain provisional, not fitted S1–S11
results. H7 calibrates the automatic policy, event density and full-generator
performance on the prescribed seed sets.

## Verification evidence

The synthetic [divided-valley fixture](../tests/history_fixtures.py) runs all
60 rounds and records 21 events. Three farming polities across six land locations cooperate, unite in
1087/1112, divide in 1227, transfer a border district in 1282, and negotiate sacred
access in 1317. In 1337 there are three related polities with distinct authority
settlements, one directed grievance of 165 internal units, and a sacred-centre
agreement. All original cohorts are unchanged. The fixture's choices are scripted;
the dates/outcomes are not claimed to emerge from the automatic policy.

Its H3 pinned semantic digest, including the new profiles and settlement facts, is
`3537b74d8cff778fe32c799647c50ab5e418aac829aba1c1cd32a23fc4cad103`.
Reversed input/proposal order and interpreter hash seeds 1/927 reproduce it.
The regression matrix also runs autonomous 60-round histories for five synthetic
seeds at turbulence 0/500/1000 and replays each result. Dedicated cases cover
simultaneous unions, double submission, contested annexation, bounded sea access,
failed attacks, shared allied budgets, subject support, empty/tribal islands,
cancellation and corrupted causal records. This is offline model evidence;
in-game names, opinions and chronicles remain H4/H5 work.

H3's additional synthetic scenarios exercise all eight caused reform dimensions,
costly resistance, finite experience, minority movement and refusal conditions,
competing moves/conquest, identity conservation, profile/ambition tampering and
permuted autonomous histories. Each seedable extraordinary type starts as an ambition;
recognition follows actual expansion, access bargains or a connected pact network.
No full-world trajectory survival rate or game behavior is claimed.

H4's first part adds 41 boundary cases and five bootstrap-size cases. The
256-location synthetic flow constructs societies, adds diaspora, runs all 60
rounds, replays history and projects the typed population with exact budgets.
Other cases exercise physical maritime bounds, lake exclusion, seam contacts,
invalid inputs, conservative elite rounding, changed political ownership and
tampered population effects. Input permutations and hash seeds 1/927 agree.
Full checks pass: 2,578 Python tests, 15 optional skips, strict types, format/lint
and 23 Rust tests; 13 read-only installed-game checks pass on build 26377361.
This does not establish final EU5 projection, engine loading or H7 calibration.

H4's second part adds 35 final-plan cases and two AI cases. They cover actual
conquest and rank, a star of sea pacts, landed confederates, overlapping sacred and
fractured roles, community participants, usable governments, protected vassal
technology, memory limits, untouched signs and rejection of changed final facts.
The 256-location constructed flow now reaches the complete final plan. Full checks
pass: 2,615 Python tests, 16 optional skips, strict types, format/lint and 23 Rust
tests. All 14 read-only installed-game checks pass on EU5 1.4.7 / build 26377361,
including the seven current American projection ranges. New localized game text,
export activation and the H7 engine observation remain outstanding.
Full semantic plans for the sea league and two-hearth confederation also agree
under interpreter hash seeds 1/927.

H4's third part adds 38 synthetic text/artifact cases, including eleven-language
rendering, two templates per displayed family, predecessor context, quiet history,
failed actions, migration direction, collision handling and rejection of changed
script effects/scopes. Full checks pass: 2,653 Python tests, 17 optional skips,
strict types, format/lint and 23 Rust tests. All 15 read-only installed-game checks
pass on EU5 1.4.7 / build 26377361, including the bias/decision/conditional-description
and guarantee precedents. Complete script/text/binding digests in all eleven
languages agree under hash seeds 1/927 for the divided valley, sea league and
two-hearth confederation. Logs and semantic hashes stay in ignored
`local_data/history-120/h4-text/`. This is offline writer evidence, not an engine
loading claim; no world reference, candidate or hub rebuild is needed before activation.

[V-EXEC, 2026-11-03] All 77 history cases pass as part of locked sync and
`make check`: 2,532 Python tests, 15 optional skips; strict types, format/lint and
23 Rust tests. The generated content reference and changed-document links pass.
Hash seeds 1/927 also reproduce the autonomous migration/pressure fixture's digest
`67c0c7cf650f502eeb91517121129b25a1024b99a5e652ef0d20a9267fc72873`.
No world export was rerun for these unconnected modules; the H1 reference result
retains its recorded scope. Candidate and hub delivery remain H7 work.

The **H2 implementation** (before society behavior was added) measured a local
1,000-district/200-actor mixed landed/tribal grid producing 13,807 events
over 60 rounds (seed 42). Changing event-by-event fact copying to one round
construction preserves digest
`28ea4ae97425dbbd456767523c7b2323d4f4958d9550381e5cb17538dec58954`.
Observed elapsed time changes from 33.425 to 19.111 seconds and process peak RSS
from 82.2 to 83.3 MiB. These single local measurements are not load-controlled or
paired full-generator S8/S9 results; they identify event density and round work
for further measurement. Scripts and raw data stay in ignored
`local_data/history-120/h2/`.

## Portable reading and controls (H5)

Atlas **format 3** adds a history schema 1 inside `atlas.json`; formats 1/2 remain
readable and explicitly have no recorded history. Format 2 was already used for
structured names, so reusing it would have let old readers silently discard history.
There is no new world-file member and no game dependency for reading a chronicle.

The portable record keeps living and predecessor actors, final eight-axis profiles
with individual causes, projected country/diplomacy facts (including each country's societal values as written to
the government block, an optional section that archives made before it lack), current living memories
and bonds, up to eight chronicle rows per country, actual memberships and sparse
ownership changes. It keeps the complete ancestor closure of these facts. A direct
reference already reachable through another direct cause can be omitted without
losing any ancestor; game outcomes and the model digest are unchanged.

Integer-indexed columns are canonical ASCII JSON compressed with standard-library
XZ and encoded with base85. Imports cap the wrapper at 8 MiB, expansion at 24 MiB,
decoder memory at 64 MiB, actors at 25,000, events at 250,000, other table rows at
500,000, strings at 128 characters, JSON depth at 24 and causal depth at 256.
Before presentation, validation checks chronological/backward references, lineage
and lifetimes, society causes, country capitals and tenure, relationships and
chronicles, then replays sparse ownership against the outer atlas. Hostile expansion,
trailing streams, invalid columns and broken references fail explicitly.
The existing 32 MiB atlas / 100 MiB compact-world limits remain.

Both windows obtain the same `history_presenter.Reader` through the controller.
A country exposes origin, government/technology and all eight axes with causes,
relationships that separate memory from actual EU5 treaties/opinions, and the
chronicle. Regional summaries show major transfers, seeded aims and the shared
predecessor periods or surviving groups. Place links select and center the named
location. The classic window renders `Reader.country`/`Reader.region` as text sections
in a scrollable dialog. The Tauri window has no country card: the pinned *location*
card has tabs (Place, Society, Chronicle, Relations) drawn from the structured
`Reader.dossier`/`Reader.place` (`desktop/src/components/history/`). The year of each
chronicle row is drawn apart from its sentence, so every translation of a chronicle
template must open with its year (`tests/test_history_dossier.py`). Relations lists the
viewed country's opinion of others as the game lists it: the engine's treaty opinions
(`rnw.opinions.TREATIES`; `vassal` pairs are overlord-first, `guarantee` guarantor-first,
`rival` rivalling-first) and the written historical opinions under their game names, which
the same tests compare with the written localization. A society that is a country on the map is
named by its country's name in the chronicle, in the game's text and the window's alike
(`history_text.chronicles`, `Reader.society`); a predecessor, which is no country, keeps the
name of its seat. The Society tab shows the societal values EU5 shows, as the game names them
and as written to the government block (`-100`..`100`, with the generator's own trait as their
cause); five of the generator's traits project onto eight values, of which seven are written:
`mysticism_vs_jurisprudence` has no ungated American range in the game and is never written. The values a country has are the *position within the American range* the
generator found in the game, not the generator's internal 0–1000 scale, so a highly centralized
society still reads as decentralized in absolute terms (the American range of centralization
is 60..100). Under plan D31 the card shows only what the game shows: government and rank under
the game's names, no technology level and none of the model's traits, the opinions of the
Relations tab, start development, and on the Place tab only the trajectories of the
*Extraordinary peoples* setting (`history_presenter.EXTRAORDINARY`). Templates and labels are translated in all eleven official languages. Covered worlds yield no
history reader/bundle, totals or political summary; the existing reveal action
opens history with the maps. An older world displays “No recorded history”.

`natives.turbulence_permille` defaults to 500, spans 0–1000 and is passed to the
normal simulation. Quick choices are Calm 200 / Varied 500 / Turbulent 800; the
advanced control and Total Chaos use the same native field. Its compact world-code
field number is appended; older recipes resolve the new field to 500. Extraordinary
peoples now describes an ambition whose realization and survival depend on history.
Only pending epoch-61 preset/synthetic pins change; released epoch-60 pins stay intact.

[V-EXEC, 2026-11-04] Full checks pass: 2,716 Python tests, 17 optional skips,
strict types/format/lint and 23 Rust tests. The Tauri interface passes strict checks,
15 tests and production build. Synthetic import and installed-world recovery retain
history; legacy readers, hostile records and the classic dialog/place link are
covered. The actual browser flow passes covered → reveal → profile/chronicle →
relationship/regional summaries → place selection, with no console errors. The
classic dialog was also inspected offscreen in Russian. Evidence is local in
`local_data/history-120/h5-ui/` and the `h5-reader-check-final-3.log`.

[V-EXEC] With the independently simulated H4 reference native plan and its actual
atlas key order, the portable record has 1,055 actors, 111,813 events and 813,239
nonredundant direct references. Its canonical wrapper is **2,050,865 bytes** (1.956 MiB)
and round-trips exactly; expanded columns are 10,932,253 bytes. This establishes the
reference payload size on that plan, not a completed H7 seed-set/performance result.
No game-facing candidate or package was installed during this reading phase.

## Calibrated action policy and client capacity (H7)

The [published calibration report](research/history-120-calibration.md) records
all 24 prescribed native starts at three turbulence levels and all 32 slider
cases at those levels. Their 168 complete model/projection results also pass the
affected writers, eleven-language bindings, population round trips and portable
decoder checks. The bootstrap factor is 1; no world is corrected to a target.

Each actor first draws admission by action family, independently of its contact
degree, then ranks one eligible alternative per admitted family, up to three in
all. Early family filtering equals filtering the complete eligible set. Normal
base propensity is 180 per mille; conflict/pressure use 50 + turbulence/2 and
separation uses turbulence³/1,000², followed by society-orientation adjustments.
Separation still requires the existing real-union and support predicates.

Great ambitions prefer the eligible centre with the greatest existing model
strength and incline centralization/integration to at least 900. They grant no
land, population, technology, rank or relationship. Realization keeps its actual
twelve-owned-location, authority, burden and lineage requirements.

New dependency admissions account for the incoming actor's whole client realm
at every ancestor ruler. Client population is bounded by own population ×
centralization × integration × 4 / 1,000². Administrative lines can commit to
one admission in a round; a competing refusal cites the earlier event. The
capacity's population/profile/bond facts are included in the causal context.
Existing treaties are not removed by a repair pass. No landmass share enters
this rule. It addresses the observed oversized Wall client networks.

The full normal reference producer and writers pass for 872 files, with pending
epoch-61 digest `435074c7…68577fb`. Its 505,104-byte history survives real compact
import and receipt recovery, covered by default. Complete-export cancellation
during reference simulation, including sibling work and cleanup, takes 0.207 s
after the request. C488 passes reference reproduction, S8–S11 and Linux/Windows
portable parity. Held-out S4 sweep, S5 and S7 fail; the complete observations and
source provenance are in the [calibration report](research/history-120-calibration.md#final-held-out-acceptance-and-local-delivery).

## H7 measurement foundation

Round indices reuse immutable physical adjacency and capacities, while ownership,
settlements and population totals stay local to each new snapshot. Both simulation
and independent replay use that boundary. Mutual contact minima are updated once
in each direction; their single-intermediary exchange rule is unchanged. Migration
and defence enumeration skip only candidates that cannot pass existing pressure
or threat prerequisites. Independent uncached/contact/enumeration references check
whole histories; real full-plan equality and performance scopes are in the
[calibration report](research/history-120-calibration.md#equal-output-performance-follow-up).

Necessary-condition pruning avoids constructing impossible local actions; the
remaining candidates still pass the complete eligibility rules. An independent
unpruned enumerator gives equal eligible multisets and complete simulations on
eight fixtures at five turbulence levels. On the real reference inputs, every
`FinalStartPlan` field, round and event remains equal to H5. The normal native
stage takes 90.856 s in this run; this is not a paired S8 result.

Canonical digest encoding now calls the supplied cancellation checkpoint for
each record. A cancellation requested after 50 ms on the real reference is
observed after 0.000311 s; previously that operation returned without observing
it after 2.151 s. Digest bytes are unchanged. The existing archive construction
also observes cancellation (0.289 s); it needs no speculative replacement.

`history_metrics.py` supplies read-only raw counters. The fixed LAND polity
envelope defines S1's denominator and S5's qualifying twenty bootstrap states;
tribal/community founders and all projected landed holdings are reported
separately. Physical components include wasteland and wrap edges, never maritime
routes. S1 excludes refused actions, includes failed conflicts, counts only
actual transfers and accepted separations, and uses the current polity/union's
birth for continuity. S2 counts written treaties and named opinions, not an
internal exchange alone. S6 resolves inherited government defaults and installed
ungated positions. S7 counts model realizations before projected group deduplication.
S11 counts the entire canonical JSON wrapper. Synthetic tests exercise these
definitions independently of the calibration policy.

[V-EXEC, 2026-11-04; initial H7 checkpoint] Full checks pass: 2,734 Python tests,
17 optional skips, strict types/format/lint and 23 Rust tests. The first full normal pilot
(continents/3, defaults) passes both versions' output checks but takes 307.494 s
against 1.1.0's 204.024 s, including separately recorded capture overhead. This
identifies an S8 performance problem; no seed-set acceptance is claimed. Action
frequency calibration remains provisional and uses only published seeds. Held-out
seeds were untouched at this checkpoint. Private measurements are in
`local_data/history-120/h7/`.

## Boundary-only coast construction correction (H7, 2026-11-04)

[V-EXEC] The complete published full-normal matrix passes S8: on 23 successful
original-baseline pairs the median added time is 13.27% and p95 16.60%; including
the explicit islands/1000 matched-static sensitivity gives 13.14% and 16.57%.
See the [calibration report](research/history-120-calibration.md#full-normal-s8-timings-and-boundary-only-coast-correction)
for scope and held-out details.

The held-out Wall/1001 input exposed a coast that only touched the Old World sea
boundary. Neither the pinned 1.1.0 generator nor the pre-correction candidate
could build its `mesoamerica_region` hierarchy. The corrected builder omits only
regions without an independent nonboundary shore from regional-sea allocation;
their generated water remains in the protected, connected ocean hierarchy. It
does not create a strait, inland mouth, or repair after export. The complete
Wall/1001 export passes all normal writers and checks (870 files,
`57851ca328cec5ba8fd8a97a2056be76f488aaf8c325e406279934a5cd3a596b`). Synthetic
hierarchy tests cover this boundary and ocean assignment, and locked full checks
pass (2,788 Python tests, 17 optional skips, strict format/lint/types and 23 Rust
tests). The initial held-out source freeze was superseded before the remaining
rows; no historical policy parameter was changed.

## H7 final validation (2026-11-05)

[V-EXEC] C488 completes corrected full-normal S8 timing, the held-out model and
sweep artifact checks, the reference reproduction, paired reference S9, export
cancellation, wrapper limits, Linux/Windows full-plan equality and local Linux
and Windows package audits. The pending epoch-61 reference matches all 872
nonmetadata files. The held-out acceptance record fails S4 sweep, S5 and S7, so
the 1.2.0 candidate does not pass H7. No profile install, hub replacement,
playset change or EU5 session occurred. The held-out results remain validation
data; further policy fitting requires a newly defined calibration/validation
cycle or an owner decision that changes the acceptance thresholds.

## Audit redesign (R1–R5, 2026-11-05)

[V-EXEC, 2026-11-05] This section implements the plan's
[audit decisions](history-plan.md#21-independent-audit-and-redesign-2026-11-05) D21–D28,
with the [§21.5 refinements](history-plan.md#215-implementation-refinements-2026-11-05-before-any-held-out-run).
The model, causal replay, projection and portable format stay. These pieces change:

| Piece | Where | Rule |
|---|---|---|
| Seeded aims | `history_trajectories.seed_events`, `Trajectory.strategy/region`, `TrajectoryKind.REGIONAL_POWER/PARAMOUNT` | Extraordinary aims per hearth as before; then one feasible setting per political region (≥ 8 landed foundings) from `SETTINGS`, interpolated by turbulence. Centres border two landed polities and have connected state land for their aim's share and scale; a paramount must have room against inaccessible founding rivals. Prudent share `PRUDENT` |
| Policy | `history_engine._bases`, `_preference`, `_keeps_aim` | An aim's holder contests persistently, preferring gains in its domain and the largest eligible gain from the same opponent. A paramount prefers to leave a defeated neighbour standing. Fearful neighbours favour pacts, protection and submission to it. League and confederation members favour pacts; sacred peers favour access. Holders do not reform away from their inclination |
| Administration | `Context.capacity`, `strain`, `limit`, `unrest` | 1,000 at or below centralization + integration 1,100; the surplus doubles every 200 and grows with technology above level 1. Coordination and contest effort use burden relative to capacity; overload increases secession propensity. Overreaching aims conquer up to twice capacity. Provinces may break away above the unrest threshold: 93%, 82% or 72% of capacity at Calm, Varied and Turbulent |
| Breakaway | `Action.SECESSION`, `history_actions._secession_allowed` | One conquered founder's province becomes a new parentless state at its founder's or largest seat, with mutual grievance. The realm keeps its seat and lineage. The core and the province must each remain connected and supported |
| Dependencies | `_submission_cause`, `Action.INDEPENDENCE`, `Effects.ended` | Submission needs fear of the lord, or a recorded threat the lord can face, plus a lord with 2× the locations and 4× the strength. Independence needs a setback for the lord, a lord below 2× the subject's strength, or a lord over capacity. Direct resubmission after independence needs a new defeat; old fear stays in memory but cannot itself undo the exit |
| Contests | `history_actions.adjudicate`, `history_engine._advance` | A defender pays what it has left; one contest per participant per round; a seceding realm's land cannot change hands twice. Without a grievance an ordinary society needs 2.5×, 1.5× or parity of strength at Calm, Varied and Turbulent (`OPPORTUNITY`); an aim holder accepts parity against ordinary targets and keeps the ordinary margin against another aim; contest propensity rises faster beyond Varied (`ESCALATION`) |
| Institutions | `eu5_history.traditions`, `history_societies.emulated` | Regional weights with a dominant authority; councils from collective bargains; a new authority only where at least half of the land neighbours hold it |
| Chronicles | `history_text.chronicles` | Ranked by `SIGNIFICANCE`; `REPEATED` caps exchange 1, contact 0, migration 1, reform 2 (authority changes only); a routine entry only fills a life with fewer than `ROUTINE_FILL` (3) significant ones |
| Groups | `history_trajectories._realized_group`, `history_actions._union_allowed`, `_league_allowed`, `history_engine._preference` | Partners of one seeded league never unite; confederates bargain on mutual trust after an exchange, or under fear; partners' pacts and exchanges rank first. Recognition reads the living descendants of the seeded members: the largest pact network of at least three that holds the anchor (leagues: council authority and an exchange network; confederates: agrarian, with the density prerequisite). A sacred centre needs its landed holder, a sacred anchor, sacred authority and two access partners |
| Reading | `history_archive.AimFact`, `history_presenter.region` | Every seeded aim with its outcome appears under the region's **Ambitions** |
| Measurement | `history_metrics.structure`, `history_acceptance.evaluate` | Region classes, recent turmoil, aim outcomes, subjects, institutions and chronicles; §18's thresholds as frozen constants. Fractured regions follow the recorded source realm of successive secessions, separately from the actor ancestry that governs aim inheritance |

**Calibration knobs**, adjustable on development seeds only (plan §17):

- `SETTINGS`, `PRUDENT`, `POLITICAL_REGION`, `FRONTIER`, `RIVAL_COUNT` and the recognition shares (`REGIONAL_SHARE`, `LEAD_HALVES`, `PARAMOUNT_SHARE`);
- `AIM_CONFLICT`, `HEGEMONY_CONFLICT`, `FEAR_RESPONSE`, `GROUP_BOND`, `SACRED_VISIT`, `ESCALATION`, `OPPORTUNITY`;
- `CAPACITY_THRESHOLD`, `CAPACITY_DOUBLING`, `OVERREACH_FACTOR`, `UNREST_SLOPE`;
- `LORD_LOCATIONS`, `LORD_POWER`, `ORDINARY_LORD_POWER`, `LEAVE_POWER`;
- `TRADITION`, `COASTAL_COUNCIL`, `DOMINANT_TRADITION`;
- `ROUTINE_FILL`.

The values after the development calibration are in the
[calibration report](research/history-120-calibration.md#r6-development-calibration-of-the-audited-redesign-2026-11-05).

The acceptance thresholds in `history_acceptance` are not knobs.

**Evidence.** These changes were checked on one world only, the captured physical
input of development world continents/3 (native stage, defaults):

| Measure | Calm | Varied | Turbulent | Before the audit (Varied) |
|---|---:|---:|---:|---:|
| 1337 states | 148 | 174 | 217 | 175 |
| Ordinary median / 1.1.0 | 3 / 3 | 3 / 3 | 2 / 3 | 3 / 3 |
| Largest bloc (state with subjects) | 66 | 55 | 50 | 55 (largest state 14) |
| Recent turmoil (100 years) | 11.4% | 14.5% | 17.5% | — |
| Polities ≥ 100 years | 86.5% | 82.2% | 74.7% | 100% |
| Subject pairs | 36 | 49 | 68 | 91 |
| Alliances | 12 | 16 | 3 | 3 |
| Republics | 16.9% | 16.1% | 10.1% | 46% |

The 1.1.0 empire on this world holds 78 locations. Exchange agreements fell from
76% to under 23% of chronicle entries, and about a fifth of countries have at most
three entries. The native stage takes 25–28 s, against 91 s before. That
single-world table is the R5 state. The full development calibration (144 starts,
48 sweeps) that followed is in the
[calibration report](research/history-120-calibration.md#r6-development-calibration-of-the-audited-redesign-2026-11-05);
its table values supersede this one. It is development evidence, not acceptance.

[V-EXEC] Locked checks pass (see the commit). At R5 the pending epoch-61 reference
export passed every writer and output check: 872 files, SHA-256
`fc29c0e24b4360a617e8a0a2abb7e62deaa4ce2584e3eff612e931c15dfc7da5`, with a
565,034-byte history wrapper. The R6 calibration changed the world; its digest is
`40596d56ad63929bb14830a99d2d19a19c9edd9f14007a7e1d4003ebff6127d9`. `tests/golden_world.json` is refreshed; the frozen
epoch-60 reference is unchanged. Naming a society that is a country by its country's name
(chronicle sentences, below) changed only the eleven localization files; the reference
digest is now `1dc426fd416fcdea90074fe464b2f5cac68684b181583837452384668d239f8c`
(872 files). The divided-valley digest is now
`99a0ee7ce9f0e0097d44a6753d6cf38934372b25e7839a4cf0166498769e6bd0`: the
schema gained fields, and the story is unchanged.

### R6 runbook

**Status, 2026-11-07:** R6 steps 1–4 are complete. On the active freeze at commit `ea4b676`
(source SHA-256 `3a125fed…3d048d2`, EU5 build `26377361`), step 3 captured all 24 held-out
physical inputs and produced 24 ordinary plus 24 sweep baselines from the saved v1.1.0 source.
Step 4 completed all 120 starts (72 worlds, 48 sweeps), each with the frozen source hash.
The held-out evaluation passes 12 of 14 checks: Q1 fails on fractured-region share (1.74% vs
3% minimum), and Q9 fails on median subjects (42 vs maximum 40). Q4 passes at the D30 recognition
scale; its Q1-scale diagnostic is 66.7%. No knob or threshold changed after the run. Per the
runbook, stop before step 5 pending the further decision required by plan D28. Full results are
in the [calibration report](research/history-120-calibration.md#r6-held-out-run-2026-11-07).

The record of 2026-11-06 follows. Step 1 (2026-11-05): all fourteen statistical checks pass on the
development set (144 starts, 48 sweeps); the evidence and every adjustment are in the
[calibration report](research/history-120-calibration.md#r6-development-calibration-of-the-audited-redesign-2026-11-05).
D29 (N6–N9) feeds no history input ([plan §22.4](history-plan.md#224-scope-and-cut-order)),
so that calibration stands. Q4 gates as written (plan D30). Step 2: the source of
commit `e60b77e` was frozen, source SHA-256 `96706763…1b4587`, in the ignored
`local_data/history-120/r6/heldout-freeze-e60b77e.json` (written by `freeze.py` beside it,
which refuses a second freeze). It supersedes the freeze of `b36915f`, kept beside it,
because D31 changed the opinions before any held-out run: the whole development matrix
was rerun on the new opinions (`R6_OUT=dev-d31`, all fourteen checks pass), and the 48
Varied starts of the final source equal that rerun. `matrix.py heldout` and
`evaluate.py heldout` check the active freeze record. Later commits that touch only
documentation keep the hash. The hub installed on 2026-11-07 is built from `823b662`;
this development calibration does not replace it. The frozen candidate's package
and hub update belong to delivery step 5.

R6 is long batch work, meant for a separate agent. The scripts are in the ignored
`local_data/history-120/r6/`. Run from the repository root, in the foreground, with
bounded workers (ADR 0006). Check the installed build first; nothing launches EU5.

1. **Development calibration.** `uv run python local_data/history-120/r6/matrix.py dev`
   runs the 48 development worlds × Calm/Varied/Turbulent and the 48 continents and
   archipelago × 3/42 sweeps, about four minutes on the reference machine. Without
   `--workers N` it takes one start per spare core that free memory allows (512 MiB each).
   It resumes and keeps complete outputs. Then
   `uv run python local_data/history-120/r6/evaluate.py dev` writes `dev/acceptance.json`.
   Adjust only the knobs above, delete the outputs that the change affects, rerun,
   and record each adjustment with its evidence in the calibration report.
2. **Freeze.** Commit the source and write a held-out freeze record (source commit,
   source SHA-256 as `observe.py` computes it, knob values, seeds 1005–1008)
   before any held-out run.
3. **Held-out inputs.** For each preset and seed 1005–1008, run
   `uv run python local_data/history-120/h7/capture_world.py --preset P --seed S --output local_data/history-120/r6/captures/P-S`.
   Pinned 1.1.0 baselines come from `h7/run_baseline_native.py` (sweeps:
   `--changes`). They go to `r6/baselines/P-S-baseline-500.json` and
   `r6/sweep-baselines/P-S-control-value/baseline-500.json`.
4. **Held-out run, once.** Run `R6_SAVE_START=1 uv run python local_data/history-120/r6/matrix.py heldout`,
   then `evaluate.py heldout`. Report Q4 at both recognition scales (D30) with
   `q4_scales.py local_data/history-120/r6/heldout/worlds`; on the development starts
   (`r6/final/worlds`) it reproduces the caveat's 102/133 and 11/25.
   If it fails, record the result and stop; plan D28 requires a further decision.
5. **S8–S10 and delivery.** Pair full normal timings as in H7
   (`h7/timed_heldout_c488.py`, adapted to the frozen source). Then: the reference
   reproduction (`RNW_REPRODUCE=1`), `make check` and `make desktop`, packages and
   self-tests. Render the `countries` atlas layer of every held-out world into a
   local contact sheet and review it against Q1–Q2. Install the candidate as AGENTS
   describes and prepare the owner's fifteen-minute sitting: the checks of
   [plan §18](history-plan.md#18-acceptance-criteria), each with its console line
   (the formable's tag for the formation, a country of its ladder to look from).
6. **W2 version matrix** ([roadmap W2](roadmap.md#workshop-feedback-in-120)), run with the
   candidate's source, in the foreground and one cell at a time (about 25 minutes a cell):
   `uv run python local_data/w2/matrix.py local_data/w2/out --mask` drives the real bridge
   process, as the Tauri window does, over a temporary data folder and profile. A cell is one
   new world, then new peoples and new resources twice each with the world in the game
   (one of them with *Keep this one in the game too*), then the world taken out of the game
   and a version of it made from the library. Presets × seeds 3 and 42, and one cell on a
   painted land image (`--mask`). A cell that stops is read from its transcript
   (`out/<cell>.out`), `bridge.stderr` and `generator.log`; fix the cause, add a test for it,
   delete the cell's `.done` and rerun. The classic window shares the controller and is
   covered by `tests/test_window.py`; no live Qt matrix is run.
7. **W6 reveal** ([roadmap W6](roadmap.md#workshop-feedback-in-120)). The candidate that step 5
   installs for the owner's sitting is made with the setting on: the same settings with
   `new_world.reveal_at_start` = 1 (for example `rnw world-code --preset P --seed S --settings F`
   with `F` holding `{"schema":1,"new_world":{"reveal_at_start":1}}`; the world's id follows its
   code, so it is a folder of its own). Before the sitting, check the written
   `in_game/common/on_action/rnw_reveal.txt` against the candidate's `definitions.txt` (the export
   already refuses a difference) and that no other mod of the profile defines `on_game_start` with
   an `effect`. The last check of the sitting is that the whole New World, sea included, is
   visible from the first day without fog for the country played; read `debug.log` for any line
   naming `rnw_reveal.txt`. A failure cuts W6 and turns the setting off, with no further sitting.
8. **W7 frontier** ([roadmap W7](roadmap.md#workshop-feedback-in-120)). Before the sitting,
   pick from the candidate's `10_countries.txt` a land country whose capital lies in a region
   the vanilla gate leaves out (Canada, the Caribbean, Mesoamerica or the West Coast) and has
   unowned land beside it. In the sitting, played as that country, its advances list
   *Settle the Frontier* and, once it is researched, the cabinet offers the action with a
   bordering province to pick; read `error.log` for lines naming
   `3_cabinet_actions_unlocks.txt`.
