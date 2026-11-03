# History core (H2)

[V-EXEC, 2026-11-03] This implements the offline H2 phase of the accepted
[history plan](history-plan.md#17-phases-and-scope-control). It is not called by
the world exporter yet. H3 supplies the remaining society dimensions, trajectories
and migration; H4 supplies the bootstrap/projection adapter. Existing world bytes,
goldens, world codes, product version and epoch are unchanged.

## Ownership and entry points

| Module | Owns |
|---|---|
| `history_model.py` | Frozen integer records: geography, cohorts, founding actors, lifecycle/lineage, holdings, agreements, directed memories, proposals, sparse effects and events |
| `history_checks.py` | Physical-route, partition, seat, agrarian support, lifetime and dependency invariants; sparse graph index |
| `history_actions.py` | Prior-snapshot prerequisites, strength/travel/defence, commitments, directed memory and joint inheritance |
| `history_engine.py` | Canonical bootstrap, local proposal policy, arbitration, atomic rounds, simulation through 1337, causal replay and semantic digest |

`create(geography, foundings, seed=...)` validates the caller's complete inhabited
partition and records each founding. It does not fill missing holdings, create
countries or invent population. The adapter must supply only generated New World
actors; the core has no game tags, installed inputs, resource roll or localization.

`advance(history, proposals, checkpoint=...)` runs one five-year round.
`simulate(history, turbulence=500, policy=None, checkpoint=...)` runs all remaining
rounds from 1037 through 1337. Its optional policy supplies proposals, not outcomes:
it passes through the same eligibility, arbitration and transition rules. The
normal policy ranks at most three eligible local choices per living actor.

`validate_history(history)` reconstructs the bootstrap and replays every recorded
proposal through those rules, then compares every event and final fact. It rejects
missing/future/cyclic causes, changed outcomes, unexplained holdings, memories or
agreements, and inconsistent lifecycle data. `digest(history)` hashes canonical
semantic data; no text, timing or process hash order enters it. The dataclasses are
an internal interface, not the portable history format planned for H5.

## One round

All proposals read the same immutable snapshot. Physical contacts come from actual
land links or explicit coast-to-coast routes with a bounded number of sea steps.
A shared region or sea name grants no access. A direct exchange can open one
physical intermediary; an indirect agreement cannot fabricate another route.

Arbitration orders action priority, proposal rank and a seed-derived tie draw.
Each actor has 1,000 commitment units. Contacts cost 50, exchange/access 100,
protection 300, defence pacts/submission 400, and a conflict 600 from each principal;
unions and divisions reserve the participants' full budget. An allied or subject
contribution uses up to 300 of its remaining units. Conflicting obligations never
let one ally contribute to both sides. The journal records the actual allocations.
A subject gets one overlord; a new submission cannot also create an independent
pact in the same round. The next round starts with fresh commitments.

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
connected territory, viable seats, agrarian support and acyclic dependencies.
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
  actual allied/subject contributions and bounded integer uncertainty. Partial
  conquest cannot remove the surviving opponent's seat or farming support;
  complete annexation retires the defeated actor. Culture and faith stay put.
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

These numeric propensities and the initial authority choices are H2 primitives.
They are not fitted S1–S11 results. H3 must add coordination, institutional costs,
integration and conservative migration; H7 must calibrate the automatic policy,
event density and end-to-end performance on the prescribed seed sets.

## Verification evidence

The synthetic [divided-valley fixture](../tests/history_fixtures.py) runs all
60 rounds and records 21 events. Three farming polities across six land locations cooperate, unite in
1087/1112, divide in 1227, transfer a border district in 1282, and negotiate sacred
access in 1317. In 1337 there are three related polities with distinct authority
settlements, one directed grievance of 165 internal units, and a sacred-centre
agreement. All original cohorts are unchanged. The fixture's choices are scripted;
the dates/outcomes are not claimed to emerge from the automatic policy.

Its pinned semantic digest is
`087c98c431878ebcb82146211056fb9ec3978fe9c418cd7d21be40ca6f56219c`.
Reversed input/proposal order and interpreter hash seeds 1/927 reproduce it.
The regression matrix also runs autonomous 60-round histories for five synthetic
seeds at turbulence 0/500/1000 and replays each result. Dedicated cases cover
simultaneous unions, double submission, contested annexation, bounded sea access,
failed attacks, shared allied budgets, subject support, empty/tribal islands,
cancellation and corrupted causal records. This is offline model evidence;
in-game names, opinions and chronicles remain H4/H5 work.

A local 1,000-district/200-actor mixed landed/tribal grid produces 13,807 events
over 60 rounds (seed 42). Changing event-by-event fact copying to one round
construction preserves digest
`28ea4ae97425dbbd456767523c7b2323d4f4958d9550381e5cb17538dec58954`.
Observed elapsed time changes from 33.425 to 19.111 seconds and process peak RSS
from 82.2 to 83.3 MiB. These single local measurements are not load-controlled or
paired full-generator S8/S9 results; they identify event density and round work
for further measurement. Scripts and raw data stay in ignored
`local_data/history-120/h2/`.
