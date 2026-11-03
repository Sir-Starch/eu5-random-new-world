# History core, societies and bootstrap

[V-EXEC, 2026-11-03] This implements the offline H2–H3 phases and H4's
bootstrap, population, final-plan construction and localized text writers in the accepted
[history plan](history-plan.md#17-phases-and-scope-control). It is not called by
the world exporter yet. The rest of H4 connects these adapters and the written-output checks to generation. Existing world bytes,
goldens, world codes, product version and epoch are unchanged.

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
| `history_population.py` | Conservative projection of historical migration into the original typed EU5 cohorts |
| `eu5_history_plan.py` | Surviving countries, governments, explicit group memberships, settlement centres, discovery, roads and the single `FinalStartPlan` |
| `eu5_history_values.py` | Installed ungated American axis ranges and bounded profile positions |
| `history_diplomacy.py` | Actual bargains, eligible engine relations and bounded directed opinion bundles |
| `history_plan_checks.py` | Independent agreement checks against the surviving history, including causal opinions and overlapping memberships |
| `history_text.py` | Typed chronicle rows, bounded event selection and original opinion/chronicle templates |
| `eu5_history_text.py` | Historical bias definitions, live-country trigger, voluntary decision/event and directed guarantee records |
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
held-out seeds. The existing exporter still calls the unchanged static entry point.

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
Their value is the surviving memory divided by 20, rounded up, capped at 50 with
its original sign; decay is 1–3. Selection admits at most four per direction and
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

This is an offline final-plan implementation. The exporter still calls H1's static
entry point. H4's remaining localized bias/chronicle writers and written-output
integration will enable it together and establish pending epoch 61 and new goldens.
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
exporter switch and integration with existing setup/archetype checks remain next
in H4; these independently callable adapters do not change current world bytes.
Game loading and F1–F3 retain their H7 scope.

## One round

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
