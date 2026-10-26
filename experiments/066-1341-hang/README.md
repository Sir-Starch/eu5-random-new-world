# 066 — EVXP hangs in 1341 and 1346

2026-10-26. Read-only investigation of an owner's existing session, without
launching or terminating EU5. The second episode includes brief debugger
attachments, with execution restored afterwards. Claims C358–C363. World: **RNW: Supercontinent
EVXP**, installed **0.13.2 / epoch 41**, folder `rnw_exp_world_rbsvu4fogp`.
Research checkout: **0.13.4 / epoch 41**.

## Result

[V-GAME owner / V-GAME recording C358] The first session stopped displaying
progress on **22 December 1341** and the owner terminated it manually. During
the investigation the owner independently restarted the same world and
reported normal play **past that date**. The restart was not requested or
performed by the agent. Identical simulation state, random state and input
sequence between sessions are not established.

[INFERRED C359, from the recording and owner's subsequent run] An immediate
freeze at the captured screenshot and an invariably failing world/date are
not supported. A transient game, rendering or compatibility-layer hang is
possible. Neither a specific subsystem nor the mod's innocence is established.
This did not establish a dated mod failure or a screenshot defect. The later
episode below establishes recurrence; the successful restart is not a
resolution. No separate owner test was requested.

## Evidence

All wall times below are **Europe/Amsterdam, UTC+01:00**.

| Time | Observation |
|---|---|
| 05:24:22 | [V-LOCAL logs] EU5 session begins. Steam manifest is build **26142040**; executable is the existing **1.4.4** build, 272,043,640 bytes, SHA-256 `725a4c6ca50c0ef738f5ef0c00660637365ad01eebd462b39d61eac202714009`. Map contract is `592e8309b7ed9bef1cc0df3eaccd798896d75cd3c3d7ecf9ed525bb6aca3009a`, matching the reference's **1.4.3 data**. |
| 05:24:24 | [V-LOCAL Steam log] Recording begins using **Game Vulkan NV12 + NVENC HEVC**. Proton log identifies **cachyos-11.0-20261015-slr**, built 2026-10-20. These identify the running stack, not a faulty component. |
| 05:27:28 | [V-GAME screenshot / V-LOCAL file time] `Screenshot_20261026_052728.png` shows **30 May 1341**. Recording subsequently shows June, July, August, September, October, November and December. |
| 05:27:36.522 | [V-LOCAL desktop journal] Spectacle reports `QWaylandDataSource: peer closed pipe`. This records a data-transfer diagnostic; it does not identify EU5 as the peer or prove a rendering failure. Steam records focus changes around the capture. |
| About 05:27:40 | [V-GAME recording] Date display reaches **22 December 1341** and remains there in subsequent sampled frames, including the recording's final seconds. Approximate wall time uses the recording start and presentation timestamps. |
| 05:28:34 | [V-LOCAL Steam/desktop log] Window title becomes **Not Responding — Window Manager**. |
| 05:28:38 | [V-LOCAL Steam log / V-GAME owner] `Apps.TerminateApp`, process removal and recording termination agree with the owner's forced close. No new EU5 crash directory was created. |

[V-LOCAL / UNKNOWN C359] `error.log` ends at **05:25:35**, before the freeze.
It contains actual load diagnostics: malformed/unprocessed wrap-edge rivers,
an incomplete VFX locator set, and three `Unknown trigger type` records naming
`common/scripted_triggers/rnw_treaty_longitudes.txt:4`. They remain separate
content issues; none is tied by the available evidence to the hang. The active
playset and enabled-mod list name EVXP alone, but the VFS log also lists other
installed world/Workshop mounts; effective-content isolation is not proved.

[V-LOCAL / UNKNOWN C359] `game.log`, `ai.log` and `debug.log` end in partial
lines, last timestamped **05:27:35**, **05:27:37**, and **05:26:45**. Their
buffered tails cannot identify the exact stopped operation. AI command
rejections omit their actors and parameters, as already documented in C333.
The queried kernel interval has no entries; no recorded GPU reset or OOM
explains this session. Absence of a logged failure does not exclude one. The
process had already been terminated when host-process inspection ran, so no
live thread state or hang dump was available. No causal claim about Spectacle,
Proton, the driver, vanilla EU5, a particular event or generated geography
follows from these artifacts.

## Preservation and verification

[V-EXEC C360] Before the owner's restart, copied **28 log files**, the playset,
world metadata and screenshot into ignored `local_data/hang-1341-20261026/`
with hashes and source times in `snapshot.json`. Preserved relevant Steam and
desktop logs, map/executable hashes, recording source hashes and two short
video excerpts (segments 62–68 and 84–85), plus inspected date-strip and full
frame extractions. Raw game material, logs and images remain uncommitted.
Only standard video decoding and existing map fingerprinting were used; no
closed-format investigation, EU5 binary write or engine change was made.

[V-EXEC C360] Locked dependency sync and `make check` pass: **1,999 Python
tests, 14 skips, 23 Rust tests**, format/lint/types clean. These verify the
unchanged generator, not freedom from runtime hangs. Used a temporary uv cache
because the sandbox's default cache was read-only. No source, generated output,
version, epoch, reference world, installed mod, save, settings or playset was
changed. No game launch, termination, push or publication. Nothing was
installed, so there is no removal step.

## Live follow-up: 2 March 1346

[V-GAME owner C361] During the same conversation, the owner reported a second
hang on **2 March 1346**, leaving the process open. Captured a separate set of
28 game logs in ignored `local_data/hang-1346-20261026/` before inspection.
PID **3476421**, named `MainThread`, has **95 threads** and about **10 GiB RSS**.
Two-second thread measurements before debugging show the main thread and
four workers each consuming about one CPU core. This is active CPU work,
not evidence of a normally progressing simulation behind a stale picture.

[V-LOCAL / V-EXEC C362] Ordinary GDB/elfutils backtraces cannot reliably unwind
the Windows executable with the available DWARF information. Bounded register
and stack captures plus its documented PE x64 unwind metadata recover the hot
worker's chain. Representative image-relative addresses:

`70d2045 → 7079f46 → 707ebde → ac047d → d1371d → d1254b → 705a407 → 72fac2a`.

The **70d2010** function scans/updates a priority structure used by
**70793b0**; **707b6e0** calls that function, and the enclosing
**7058eb0–705d0ee** update references `unit_graphics.cpp` and its
`UpdateInternal`/`UpdateMovement` markers. Nearby registered commands identify
`Units.PathRefiner.*`. Direct return sites agree with the decoded calls;
indirect call sites remain indirect, not invented symbol names.

[V-EXEC C362] After explicitly restoring execution, captures at
**05:45:05** and **05:45:54** find the same hot worker respectively at RVA
**707a100** and **70d2045**, with the same caller frame/stack region. A fresh
two-second measurement after restoration again shows five active cores,
including essentially two seconds of user CPU on `Task_N 8`. These advancing
instruction locations in the same refinement task support a prolonged CPU
path calculation in the unit-graphics update. They do not prove a formal
infinite loop, identify the unit or establish valid/invalid route endpoints.

[INFERRED / UNKNOWN C362] The second hang is localized to game-side work for
unit graphics/path refinement, with other workers in task scheduling and
the main thread in Wine synchronization. A screenshot, GPU-driver failure,
specific event, generated-map defect or Proton defect is not established as
the trigger. A map-triggered engine pathfinding problem remains possible;
the exact input and why this calculation fails to complete remain open.
The earlier session has no thread capture, so the same cause cannot be
asserted for 1341. The second session's last `error.log` assertion about a
positive `Position` is at **05:34:39**, well before its last AI records at
**05:36:07**; it cannot be assigned to this task from timing alone.

### Debugger-state correction and preservation

[V-EXEC C363] An early attachment left a group stop after detach. The
**05:40:38 / 05:42:10** register snapshots are therefore **not evidence of
unchanging execution over that interval**. The error was reported to the
owner, the process was explicitly continued, and subsequent capture wrappers
always continued it in a `finally` step. Final recorded process state is
**R (running), TracerPid 0**. This restores the pre-inspection execution state;
it does not claim to recover the hung game. No debugger remains attached,
no game process was terminated, and no game memory edit or breakpoint-based
workaround was applied. GDB's ordinary loader bookkeeping and temporary
thread stops are not represented as a completely nonintrusive observation.

[V-EXEC C363] Small stack/register copies, thread measurements, maps, tool
outputs and bounded executable disassembly stay ignored. No full-memory
dump, installation change or test mod was made. The necessary read-only
binary analysis is documented in [interoperability R-006](../../docs/research/interoperability.md).
The completed generator checks above remain applicable because only research
documentation changed; they do not validate the game's path-refinement code.
