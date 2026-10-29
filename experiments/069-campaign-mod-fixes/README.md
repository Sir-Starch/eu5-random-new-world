# EVXP campaign: attributable mod corrections

2026-10-26; generator **0.13.6 / epoch 43**. Target: installed EU5 **1.4.4**,
Steam **26142040**, executable SHA-256 `725a4c6c…14009`, on fingerprinted
1.4.3 map data `592e8309…03009a`. No EU5 launch or save migration.

## Corrections

[V-LOCAL / V-EXEC / INFERRED C390] The [1849 campaign audit](../../docs/research/evxp-session-diagnostics.md)
separates attributable generated-output defects from inherited failures and
unresolved causes. This phase changes the initial generator output:

- **G01, treaty:** replace the rejected quoted dynamic custom-value comparison
  with the installed script language's scoped numeric-value block, for both
  location comparison and province distribution. Keep strict east/west tests,
  the continuous longitude axis and vanilla claim gates. Write BOMs and labels
  for every coordinate geography in all eleven installed official languages.
  Structural/coordinate checks and native syntax precedents support the remedy;
  acceptance of the corrected scripts by EU5 remains unobserved.
- **G02, rivers:** bounded component discovery and the adjoining line walker
  have different edge behavior. The walker normalizes an out-of-bounds neighbour
  to zero; a last-column channel can join the separately discovered first-column
  fragment. Vanilla has no outer-column channels. Construct drawing trees ending
  before the final column, explicitly accounting for boundary pixels and isolated
  points. Keep physical drainage and carved valleys. This is a raster adapter
  change, with no terrain corridor, location split, engine patch or output repair.
  The [interoperability register](../../docs/research/interoperability.md#follow-up-boundary-river-walker-2026-10-26-0136--epoch-43)
  records the limited read-only investigation and its limits.
- **G03, VFX:** retained ocean anchors were appended twice, once with the new
  oceans and once with their retained remainders. The previous set comparison
  hid duplicate instances. Write only extra ocean anchors in the first path;
  reject duplicate IDs and check VFX coverage against the entire final hierarchy.
  The output defect is established; the exact relationship between duplicates
  and the engine's incomplete-category message remains inferred.
- **G04, initial buildings:** historical town templates can exceed a generated
  settlement's native guild capacity (Rapampa: granary 2, cap 1). Read the installed
  guild formula and its positive aliases; use generated development/population
  and a conservative bound for any initial market access. Derive a template only
  when its levels differ. Refuse changed arithmetic and unsupported capacities
  in a used template. Keep population, development, ranks and vanilla building
  rules. Unknown unrelated scripted caps are not claimed exhaustively evaluated.

## Attribution limits

[V-LOCAL / V-EXEC / UNKNOWN C391] The two bounds warnings are not closed by an
arbitrary anchor move. Both written anchors fall on their own coloured identity.
The engine uses a linear rectangle which can lie in an unwrapped coordinate
frame; the reported right limits are 39 and 47 against right-edge anchors.
A portable choice of that frame is not established. No change ships from this
lead, and no claim of harmlessness or full engine attribution is made.

All five supposedly population-less cultures are explicitly written as 0.050
minority pops. Their actual initialization remains unexplained; no population
inflation or culture deletion is justified by this evidence. Hypothetical DIP-0
budgets, the Quillaqta mercenary failure and unattributed runtime errors retain
the audit's limits. Vanilla AI colonization defaults and observer-scoped disease
counters are not changed. These unresolved items are not reported as fixed.

## Verification and delivery

[V-EXEC C392] Locked dependency sync and `make check`: **2,012 Python tests
pass, 14 skip; 23 Rust tests pass**, formatting/lint/types clean. Local-install
checks with independent full reference generation: **13 pass, one skip**. A
further local check covers every urban template selectable by any retained
American culture, including those absent from EVXP. Windows/Wine's isolated
offscreen self-test passes; four geometry cases, 31 river cuts, treaty bytes
and guild-capacity cases match Linux exactly. No native-Windows machine or
remote CI run is inferred.

The reference is **849 canonical nonmetadata files**,
SHA-256 `f544876d3a0055a1a945a9d1be860b19936d7261e239bee43a8af275d8457e7b`.
Independent written-file inspection checks 877 bundle hashes, an exact location
raster and all 24 height files against 0.13.5, 28,475 unique VFX locators,
734 river components with one source each, 56 omitted final-column pixels,
unchanged surviving river widths, eighteen adjusted towns/three templates,
Rapampa's granary at one, eleven treaty languages and BOMs. No channel pixel is
added. Synthetic fixtures also reject malformed confluences, changed capacity
arithmetic and duplicate locators. Reproduction and structural checks establish
these offline properties, not the engine's complete river-mesh or script contract.

With EU5 closed, installed **RNW: Supercontinent EVXP RC** into the new
`mod/rnw_exp_evxp_release`, with **860 files** verified. Library id `hjni42sc2r`
is registered in both native and Windows libraries, each with 29 kept files and
the complete 6,874-location atlas; its recovery receipt reconstructs the entry.
Normal revealed-world presentation is applied. Updated the generator-only hub
0.13.5→0.13.6, **3,268 files/source/catalogs** verified and backups retained.
Preserved 820 original EVXP hashes, 7,620 other-mod size/time records, nine
profile-root hashes, 134 save-file stat records, sixteen prior library records
and two preference files. No playset or existing world is replaced.

The two Windows/Workshop-layout ZIPs and checksums are under ignored
`local_data/release-100/artifacts/`; both pass the distribution file audit.
The wheel's SHA-256 is `8229f410…a96858`. Generated worlds, logs, traces and
game-derived images stay ignored. Exact removal and hub backup locations are
in [INSTALLED](../INSTALLED.md).

The game-facing corrections remain an offline candidate, separate from the
completed 0.13.5 campaign. No EU5 launch, tag, push, upload or publication occurs.
The remaining 1.0.0 evidence boundary is recorded in
[release readiness](../../docs/release-process.md#published-baseline).
