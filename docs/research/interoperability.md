# Interoperability register: closed formats and binary files of EU5

**Standing rule (owner, 2026-10-22).** Every time the project reverse-engineers a closed format of EU5 or writes a modified binary file of the game, this register records, before the change ships:

1. **Why it is necessary** for the mod to work.
2. **Why official APIs, tools or documented ways are not enough.**
3. **Which data and structures are studied or changed.**
4. **How compatibility is kept without distributing Paradox's protected resources.**

The aim is a checkable record of good-faith research for the interoperability of independently developed software under EU law, in particular Directive 2009/24/EC. Earlier cases are not rewritten in one sweep; they are added when next touched (see the list at the end).

**Legal source audit: 2026-10-22.** The primary texts below were read for this revision. This is project risk analysis, not legal advice or a finding that every recorded operation is lawful. It replaces the earlier memory-based account, including its incorrect article number. The technical observations in R-001 retain their original evidence and were not revalidated by this legal audit.

## Verified legal framework

### Computer programs: what the exceptions actually cover

[SOURCE L1] [Directive 2009/24/EC](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32009L0024), 23 April 2009, OJ L 111, 5 May 2009, pp. 16–22; in force at access:

| Provision | Scope and conditions |
|---|---|
| Art. 1(2) | Protects program expression, excluding underlying ideas and principles, including those underlying interfaces. |
| Art. 4(1)(a)–(b) | Reproduction and alteration are restricted acts, subject to exceptions. |
| Art. 5(3) | A person entitled to use a copy may observe, study or test its functioning during loading, displaying, running, transmitting or storing that they are entitled to perform. |
| Art. 6(1) | Code reproduction or translation must be indispensable for interoperability of an independently created program; performed by an entitled person or authorised representative; information not already readily available; necessary parts only. |
| Art. 6(2)–(3) | Information is restricted to interoperability; disclosure only where necessary for that program's interoperability; no substantially similar expression or infringement; no unreasonable prejudice or conflict with normal exploitation. |
| Art. 8, second paragraph | Contract terms contrary to Art. 6 or Art. 5(2)–(3) are void. **Not Art. 9**, which concerns communication of national legislation. |

### Formats, game assets and technical protection are separate questions

[SOURCE L2] **SAS Institute v World Programming**, C-406/10, 2 May 2012, ECLI:EU:C:2012:259, [judgment, paras. 39–46 and 50–62](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62010CJ0406): functionality, programming language and functional data-file formats are not program expression protected by software copyright. The Court nevertheless reserves possible protection under Directive 2001/29 for original works and distinguishes reproducing program code from independently implementing functionality. Lawful observation is conditional on entitled acts and respect for exclusive rights. The judgment interprets predecessor Directive 91/250/EEC; its Art. 9(1) is the source of the old numbering, mapped to Art. 8 by Annex II of L1.

[SOURCE L3] **Nintendo v PC Box**, C-355/12, 23 January 2014, ECLI:EU:C:2014:25, [judgment, paras. 21–23](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62012CJ0355): a videogame includes original graphic and sound elements protected under Directive 2001/29, beyond the program alone. Paras. 24–38 address technological protection, its purpose, proportionality and actual uses; they do not give blanket permission to bypass protection for interoperability.

[SOURCE L4] [Directive 2001/29/EC, consolidated 6 June 2019](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02001L0029-20190606), Arts. 2, 5(2)(b), 5(5), 6: reproduction is a separate right; private copying is an optional national exception with conditions, including fair compensation, rather than a general EU permission for any local copy. Effective technological measures have separate protection. The consolidation is a documentation aid; the authentic acts are linked from it.

[INFERRED from L1–L4] An independently written reader/writer for `.splnet` and the copying of vanilla road geometry into its output need separate analysis. A binary container is not automatically program code, and understanding its layout does not settle rights in its contents. Keeping output private reduces distribution exposure but does not itself establish permission to reproduce it. Likewise, a plaintext or compressed format is not by itself evidence of either a protection measure or its circumvention. The relevant facts must be recorded per case.

### Paradox and Steam terms actually reviewed

[SOURCE P1] [Paradox User Agreement](https://legal.paradoxplaza.com/eula), updated **21 January 2026**, §§1, 5, 7, 12. §5 authorises noncommercial UGC, including mods, scripts and programs, subject to rights and contractual restrictions; creator rights cover original additions only. §7 incorporates conduct rules. The reviewed text contains no express reverse-engineering or decompilation clause. That absence is not a separate permission. §12 selects Swedish law; it does not identify every mandatory law relevant to this project.

[SOURCE P2] [Paradox Community Code of Conduct](https://legal.paradoxplaza.com/rules-of-conduct?locale=en), updated **2 May 2022**, introduction, “Inappropriate content” and “Legal information”: official community-platform rules, incorporated into the agreement, prohibit hacks, malicious programs, unreleased/hacked data and unauthorised protected material. They do not define every binary mod as a hack or grant an interoperability exception. [INFERRED] Calling an output a mod, or calling an engine hook a hack, cannot substitute for examining its actual behaviour and applicable permission.

[SOURCE P3] [EU5's Steam EULA page, app 3450310](https://store.steampowered.com/eula/3450310_eula_0), accessed **22 October 2026**, points to P1 and the privacy policy; it displays no additional substantive EU5 licence text. [UNKNOWN] Additional forum, Workshop upload or other game-specific conditions have not been exhaustively established by this review.

[SOURCE S1] [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/), English live text accessed **22 October 2026**, §§1.B, 2.G, 6.A–B, 6.D:

- §2.G **expressly restricts reverse engineering, disassembly, decompilation, copying and modification**, but preserves exceptions permitted by the agreement/subscription terms or applicable law notwithstanding those restrictions.
- Workshop uploads grant rights to Valve and require sufficient contributor rights; app-specific terms may supplement or change Workshop conditions.

[INFERRED from P1–P3, S1] UGC permission and mandatory legal exceptions must be assessed together with contractual restrictions. Neither Steam's restriction nor Paradox's encouragement settles this case alone. This audit covers the named clauses; it is not publication clearance. It supersedes the earlier “Valve terms not reviewed” notes in [legal](../legal.md) only for these clauses.

### Application limits and the evidence each case needs

[UNKNOWN] The relevant national implementation, residence and territorial facts have not been established. A timezone is not jurisdiction evidence. This register therefore makes no country-specific legality finding and does not assume a directive alone resolves a private contractual dispute. Protection of particular data as an original work or database, and any relevant trade-secret duties, remains unassessed.

For each case, distinguish these factual questions from the legal conclusions:

1. Identify the independent program, the engine interface and the exact interoperability need.
2. Record the entitled copy, build and actual methods: data inspection, execution, string extraction, disassembly or code translation. Do not call all of these decompilation.
3. List documentation, APIs and tools checked, with dates and limits. An undocumented installed folder does not prove information is unavailable elsewhere.
4. If relying on Art. 6, explain indispensability, necessary parts and why information was not readily available; record intended use and disclosure. Do not presume Art. 6 applies to ordinary data parsing.
5. Separate independently authored code/specifications from copied or derived game content and from any access/protection mechanism. Record what remains private and what would be published, with the permission or unresolved question for each.

## Practices that hold for every case

- The researcher uses a lawfully obtained copy (EU5 on Steam, build 26105915 [V-LOCAL C148]) and reads it only from the player's own installation; the installation is never edited.
- What is learned is kept as a description of the format (documentation and code such as `rnw/splnet.py`) and checked with synthetic fixtures; no game bytes, extracts, dumps or derived rasters are committed. Raw material stays under `local_data/` (gitignored).
- A modified binary is written as a new file at the same path **in the mod**, made on the player's machine from the player's installation at generation time, and a format that has changed fails loudly instead of being guessed at.
- A built world holds copies and derivations of Paradox's data (for example the vanilla strips of kept Old World locations below). Project policy keeps it for the player's own use, without uploading or sharing ([legal](../legal.md), [ADR 0009](../adr/0009-hub-mod-with-generator.md), [ADR 0010](../adr/0010-layered-worlds-and-a-generator-of-its-own.md)). This is a distribution boundary, not proof that every local reproduction is authorised.

## R-001: `spline_network.splnet` (2026-10-22, generator 0.9.30)

Path: `game/in_game/gfx/map/spline_network/spline_network.splnet`, 31,615,438 bytes on build 26105915. Evidence: C161 (the log flood), C162 (the format and coverage), C163 (the generated file). Status: **not game validated beyond a first look**. 0.9.30 and 0.9.31 load with no strip error, a road network draws in the Roads lens (probably 0.9.31) and a 5.7-minute run at speed logged no strip error ([experiment 029](../../experiments/029-spline-strips/README.md), C166, C167); roads built in play are not confirmed. A defect in 0.9.30 is not an established fact. The vanilla folder also holds a baked navigation mesh, `navmesh2.cache` (281 MB), which this case neither reads nor writes.

**1. Why it is necessary.** The game draws and routes a road along a strip baked into this file, between the anchors of two locations. A road between generated locations has no strip: the game logged `Could not find spline network strip of type 0 between anchors a and b` 125,820 times in one 13-minute session, for the 83 generated royal-road pairs of the empires and for roads built in play, and the flood rotated `error.log` away every 15 to 20 seconds [V-GAME owner C161]. The mod replaces vanilla's America with generated locations, so every road there, set up by `road_network` or built later by the AI or the player, needs strips that exist only for vanilla locations. Without them the mod cannot have working roads and its log is unusable.

**2. Why the official means are not enough.**

- The format has no documentation or API that we know of: the folder holds textures and this file only, no readme [V-LOCAL], unlike systems such as `country_ranks` that ship one.
- The documented lever, the `road_network` pairs of `09_roads.txt`, says which locations are joined but supplies no strip; the road types and spline styles files name styles but not geometry [V-LOCAL C162].
- The engine's strings name a map editor with a spline network tool [V-LOCAL], but the installation holds no editor program beside `eu5.exe`, and whether the main program offers players an editor mode is [UNKNOWN]. Even if it does, a world needs about twelve thousand strips made again for every seed, which a manual tool cannot do [INFERRED].
- Writing no road pairs would drop the empires' roads but would not stop the roads built in play from logging the same error (six such pairs appeared within two minutes, C161), so it would leave the defect.

[UNKNOWN] These checks document the local information gap, not an exhaustive search of official documentation or proof of Art. 6 indispensability. A dated search for an accessible editor/API and an assessment of whether it can generate strips reproducibly remain necessary if Art. 6 is relied on.

**3. What is studied and changed.**

- *Studied:* the byte structure of this one data file, by observing the copy of the installed game: its tagged binary framing, its three lists (points, segments, strips), their numbering rules, and how they relate to the location index of `definitions.txt` and to the map's pixels (an anchor is a location's index from 1, at about four pixels from its centre; a strip id packs the two indexes; all 51,095 strips cover the 50,580 land-land contacts and all 1,646 roads of the setup) [V-EXEC C162]. The reader writes the vanilla file back byte for byte (local test), which checks the description against the file.
- *Also used:* a dump of printable strings of `eu5.exe`, kept only in `local_data/re/` and never committed, to read the texts of log messages and the names of subsystems. No executable code was disassembled or decompiled for this case.
- *Changed:* nothing in the installation. The mod gets a new file at the same path: the vanilla strips of locations that are still there, renumbered by the order of the mod's `definitions.txt`, plus a strip for every land contact of a generated location.

**4. Compatibility without distributing Paradox's resources.**

- The repository holds a format description (`src/rnw/splnet.py`, this register) and a generator (`src/rnw/eu5_splines.py`), with synthetic test networks; no byte of the game's file and no extract of it is committed.
- The generated file is made on the player's machine from the player's installed copy, at generation time, and is part of a built world that is not shared. It does contain copies of vanilla strips for the Old World locations the mod keeps; the engine reads one file per path and has no way to add strips beside the vanilla file, so this is the minimum that makes the file work [INFERRED]. It belongs to the same category as the derived `locations.png` ([legal](../legal.md)).
- The independent program is the RNW generator, whose reader/writer emits the spline interface consumed by EU5. The stated method is data-file inspection and printable-string extraction, with no code disassembly or decompilation. [INFERRED from that method and L1–L2] Art. 6 should not be asserted as the automatic legal basis: this record does not establish code reproduction/translation within its scope. Art. 5(3) concerns entitled observation of program functioning, not blanket permission to copy its data files.
- The public specification and reader/writer disclose information even without shipping vanilla bytes. [UNKNOWN] If any information were obtained under Art. 6, publication would need the necessity assessment of Art. 6(2)(b) for interoperability of **this independently created program**, not merely possible usefulness to other mod tools. Keeping game bytes out of source does not settle that test. Conversely, this condition must not automatically be attached to all independently learned format facts when Art. 6 was not the route used.
- [UNKNOWN] The record explains the technical reason for preserving Old World strips but does not resolve protection of those particular contents or the permission for their local reproduction. General UGC permission (P1) is relevant; technical necessity and private output alone do not establish the answer. No conclusion of infringement is made either.
- A game patch that changes the file stops the build (`parse` refuses an unknown format number, numbering or reference) and the file is made anew from the patched installation.

### R-001 follow-up: hierarchy assignment in N5 (2026-10-24, 0.11.4)

[V-EXEC] N5 changes the generated hierarchy order, which also changes the one-based
location indexes consumed by the existing spline writer. Rebuilding the network with
those indexes is necessary for the same road/anchor interface described above; no
additional official API or editor has been established, and no new format research or
binary layout is introduced. The existing reader/writer and local-generation boundary
remain the mechanism. `spline_problems` decodes the written file and checks retained
vanilla strips by location identity and exact polyline geometry, every generated land
contact and every setup road. The N5 reference export passes those checks. Its rasters,
climate templates, resources, shaders and other graphics match epoch 27 byte for byte;
the spline file is the sole changed graphics binary. The derived network stays in the
unshared world under `local_data/n5/`; only code, synthetic fixtures, identifiers and
verification digests enter the repository. See [N5](n5-region-keys.md).

## R-002 — Optional country scopes and localization text overrides

**2026-10-24, generator 0.11.3; EU5 1.4.4 executable (build 26142040) on 1.4.3 data (build 26105915), C258-C259; [experiment 046](../../experiments/046-sitting-fixes/README.md).** This records the text interfaces touched by this maintenance change. It introduces no binary format or executable analysis.

**Necessity.** The owner's optional concealment of the New World also prevents choosing its countries at selection. The existing lobby queried a typed country script with no selected country and logged 214 errors (C254). Separately, generated names for reused American areas and regions were defined alongside the installed keys, causing duplicate-key warnings (C256).

**Available documented mechanisms.** The installed `in_game/common/scripted_guis/scripted_guis.info` documents saved scopes, and `in_game/gui/economy_lateralview.gui` uses a `GuiScope.AddScope` builder without setting a root [V-LOCAL]. The generator uses these interfaces and an optional script scope; no new engine hook is inferred or patched. Localization is UTF-8 text. No working override precedence for the old extra `replace/` files had been established; the new output uses the original localization file paths, as the mod's other locally derived overrides do [INFERRED from the existing override mechanism; engine verdict for these texts remains UNKNOWN].

**What is studied or changed.** Only the installed scripted-GUI description, scope-builder usage and the name entries in three map-localization files per official language are inspected. The generated lobby copies keep their existing anchored edits and change the country-query arguments; the independent scripted GUI handles an optional saved capital. The generator copies installed map-localization files to matching mod paths and changes only the requested American name values, preserving every key and every other byte. It emits no duplicate name file. No shader, binary layout or game installation is changed by this phase.

**Compatibility and distribution.** Missing GUI anchors or missing/ambiguous requested localization keys stop generation. The localization validator requires original-path overrides to retain the installed key set and still rejects newly generated key hashes that collide with vanilla. Source and tests hold interface identifiers and synthetic text only. The installed GUI and localization copies are created on the player's machine, recorded in the world's input/output manifests, kept under ignored local paths and never committed or distributed. Existing shader generation is unchanged; its broader register entry remains a separate task when that rendering mechanism is next changed.

## R-003 — The languages of a mod's metadata

**2026-10-24, generator 0.11.6; EU5 1.4.4 executable (build 26142040) on 1.4.3 data (build 26105915), C276.** This records a read of the executable's printable strings. No file format is written, and no code was disassembled or decompiled.

**Necessity.** L1 requires everything a player sees in one of the game's official languages. The game's mod list shows the title and description of each mod's `.metadata/metadata.json`: the hub's and every generated world's. Whether that file can carry a text per language decides whether those two texts can be translated or stay English.

**Available documented mechanisms.** The installed game documents no metadata fields; the eight Workshop mods installed on this machine carry one `name` and one `short_description` each and no field for a language, and no `metadata.json` ships with the installation [V-LOCAL]. Steam's per-language title and description of a Workshop item are documented by Steam, but whether the game's list shows them is not.

**What is studied or changed.** The printable strings of the installed `eu5.exe`, read with `strings` in the terminal and not stored: the field names that stand beside `short_description` (`supported_game_version`, `relationships`, `game_custom_data`, `provider_id`, `rel_type`, `resource_type`), none of them for a language, and the place of `localized_name`, among the modifier-type fields. Nothing is changed.

**Compatibility and distribution.** The generator keeps writing the fields the game's own mods use, in English. Only the field names above enter the repository. Whether the Workshop's translations reach the in-game list is [UNKNOWN] until the item is uploaded.

## R-004 — Expanded geography through the existing visual-map interfaces

**2026-10-24, generator 0.12.0, epoch 30; EU5 1.4.4 executable / build 26142040 on
1.4.3 data; C282–C285.** This records the earlier binary interfaces when the ocean
expansion next changes their generated contents. It introduces no executable-code
analysis or new binary layout. Source inspection and synthetic round trips are
separate evidence from an engine result, which remains unverified for this domain.

**Necessity and official mechanisms checked.** `locations.png` describes gameplay
locations, while separate terrain, material, object and water assets draw the
land. Changing the first alone leaves old relief, trees, foam or lake meshes over
new geography (C45, C50–C52). Installed text templates classify locations and name
assets; they do not supply per-seed terrain tiles, object transforms or water
pixels. The existing map editor/API investigation is recorded in R-001. No
accessible documented batch interface that generates these layers from an arbitrary
seed has been established; this is the boundary of that investigation, not proof
that no official editor exists.

**Data and structures studied or written.**

- `in_game/map_data/locations.png`, `rivers.png`, preview and metadata PNGs use an
  open image format. RGB location colours resolve through named locations; indexed
  river pixels carry the game's observed water/land/channel codes. The generator
  keeps ancillary image chunks, writes the same dimensions and checks its decoded
  output against declarations and the permitted changes. Expanded ocean identity
  recolouring is restricted to explicit row runs of retained closed-ocean
  components; protected land and other continents' water are not recoloured.
- `gfx/terrain2` height/material decal `.info`/`.bin` pairs: the independent
  `terrain_tiles.py` reader/writer uses the observed south-up image, one-channel
  8/16-bit samples, 128-pixel tiles with a two-pixel border, mip levels and
  independently compressed LZAV tile streams indexed by offsets and lengths.
  `parse_info` rejects unsupported headers/channel/sample structures. The existing
  strip/band rebuild and native kernels now cover the wider domain; their equality
  tests remain the implementation evidence. The decal cache is JSON, not an
  executable or a new binary interface.
- Generated vegetation and ground-clutter `.bin` files under `gfx/map/map_objects`
  hold ten little-endian 32-bit floats per transform (position, quaternion, scale;
  40 bytes). The existing adapter keeps outside records, samples new instances from
  its calibrated fields and enforces the instance budget. Inline transform blocks
  are text. `lakes.bin` uses the same 40-byte transform size: records centred on
  replaced geography are omitted, retained records are byte-identical. Its writer
  now rejects an incomplete record instead of discarding a trailing byte; synthetic
  tests check exact retention and refusal.
- `gfx/map/water/watercolor_rgb_waterspec_a.dds` and `foam_map.dds` retain their DDS
  framing and use the existing reader/writer for changed water/coast pixels and
  compression blocks. Original shallow water and foam cannot remain where the new
  land/sea boundary moved; the new values derive from the local game's calibration.
- `spline_network.splnet` is rebuilt for the new location indexes and land contacts
  through the same R-001 reader/writer. No spline-format change is introduced;
  spline verification still checks carried Old World polylines and every generated
  land contact. The optional pre-play cover keeps its existing installed-file
  anchors and mechanisms; this phase changes its geographic grid, not its shader
  or GUI patch logic.

**Compatibility and distribution.** All source assets are read from the owner's
installation and written only into a locally generated world. Existing fingerprint,
input recording, format guards, native/reference equality tests, synthetic fixtures,
output validators and independent raster audits provide the compatibility evidence
for the named build; they do not promise the next patch will work. This register and
project-authored code contain structural descriptions and identifiers, not copied
assets. Derived rasters, binary files and raw audit material stay under ignored
`generated/`, `local_data/` or local build folders. They are not uploaded or committed.
The legal limits of observation, reproduction and distribution in the framework
above continue to apply; this technical record supplies no additional clearance.

### Follow-up: seed-positioned land fields (2026-10-25, 0.12.1 / epoch 31)

[V-EXEC C286] Moving the noise origin changes the generated land and the values
written through all the map, terrain, spline, object and water interfaces listed
in R-004 and R-001. The interoperability need and the official-interface limits
above still apply: each visual layer must depict the newly generated geography.
This change studies only our own integer noise and synthetic fixtures; it reads
the same fingerprinted local inputs and uses the existing serializers and format
checks. No new closed structure, executable analysis, engine patch, shipped game
asset or post-export correction is introduced. Derived binaries and diagnostic
rasters stay local under ignored paths. Engine results remain [UNKNOWN].

### Follow-up: cylindrical map continuity (2026-10-25, 0.12.2 / epoch 32)

[V-EXEC C289–C290] Removing the forced seam strait changes the contents written
through the R-004 interfaces, for the same interoperability need and official
interface limits recorded above. No binary layout or engine file is changed.
The existing height/material writer receives windows with wrapped horizontal
neighbours and crop-coordinate detail; the existing DDS writer receives wrapped
coast distances/blur and periodic detail. Synthetic decoded tiles are compared
against one continuous continent rendered before rolling it across the map edges.

R-001 now also writes generated strips for land contacts between the last and first
map columns. Curves use the short cylindrical displacement and store each point
inside the map's coordinate range. The format, anchor numbering and serializer
are unchanged. A read-only audit of the current vanilla network finds no
wrap-crossing segment and no out-of-range point, so it supplies no positive engine
example for these contacts. Read-back checks establish short cylindrical steps,
exact endpoints and unchanged retained Old World polylines; their engine rendering
remains [UNKNOWN]. No executable analysis or engine/shader patch is introduced.
All local source binaries, generated rasters, strips and audit outputs remain
unshared under ignored paths. This follow-up introduces no additional legal
clearance beyond the framework and limits above.

### Follow-up: world-edge decal coverage and coast precision (2026-10-25, 0.12.3 / epoch 33)

[V-GAME owner C293] A physical crack remains in 0.12.2 despite continuous decoded
height pixels. [V-LOCAL C295] The installed terrain compute shader tests decal
positions with an inclusive lower and exclusive upper bound and initializes an
new height page to zero before applying its decals. Original heightmaps end at the world boundary;
they do not describe periodic data beyond it. This follow-up uses the existing
terrain instance interface for a cylindrical world, without changing a shader.

**Necessity and method.** The generated land can cross the wrap; the corresponding
terrain placements must supply boundary vertices and page halos too. The text
mechanism is vanilla's repeated decal instances. For each first/last-column
heightmap, the generator makes a placement shifted by plus/minus the world width,
in `terrain_cache/ingame_decals.json` and a matching instance `.json` in the
original asset's folder. The same local height/material textures are reused and
all original placements remain. Cache rebuilding therefore has the same placement
records as the baked path. Geometry mismatches or missing source anchors stop the
build. No new binary format or layer that repairs generated heights is introduced.

Shader and data-file inspection establish the half-open sampling contract; a
small read-only executable xref/disassembly investigation of terrain render,
initialization and properties routines did **not** establish exact mesh extents
or CPU acceptance of outside placements. Those remain [UNKNOWN], as does the
candidate's engine appearance. No process was attached, code changed, memory
written or game launched. Only identifiers and our synthetic geometry tests are
committed; executable excerpts and screenshots stay ignored and local.

[V-EXEC C294] Raising the independent integer-noise interpolation precision also
changes the values written through the existing height, material, water, object
and spline interfaces of R-004/R-001. Their formats, necessity, official-interface
limits and local-only generation boundary are unchanged. Native/reference and
cross-platform comparisons verify the arithmetic, not engine behaviour. The legal
framework and its limits above continue to apply; no additional clearance is
inferred from this technical research.

### Follow-up: removed coast's offshore support (2026-10-25, 0.12.4 / epoch 34)

[V-LOCAL/V-EXEC C306–C307] TR46's remaining Alaska-shaped shelf is traced to the
location mask omitting the original coast's offshore visual support. The R-004
height/material writer now receives an input footprint that includes adjacent
original water within the existing shelf/material reach; water DDS synthesis
includes the support of changed distance and blur fields. The same serializers
write final assets directly. Formats, source asset ownership and distribution
limits are unchanged. Synthetic tests cover the removed-island rim, retained
land, decal/map edges and band/strip equality; decoded written-world checks keep
19,950,952 retained land samples exact on the affected tiles. This is no new
closed format, post-export repair pass or engine patch. All binaries and raw
measurements remain local. Engine appearance is not inferred from these checks.

[V-LOCAL executable / INFERRED C305] To assess the reported colonial east/west
allocation before changing content, a limited read-only trace follows the
installed `is_east_of` registration through factory/RTTI to `CIsEastOfTrigger`.
The evaluator compares coordinates with a map-dependent positive/negative span;
its exact numeric value is not established here. No code, process memory or
installation is changed; no executable excerpt is distributed. This static
investigation supplies evidence about an existing scripting interface, not a
new executable interface or permission to redistribute protected resources.

### Follow-up: planar river drawing fragments (2026-10-25, 0.12.5 / epoch 35)

[V-LOCAL executable / V-EXEC C309–C310] The same open PNG interface in R-004
needs an explicit planar drawing start for each fragment of a continuous river
crossing the map seam. Logical-network validation before world placement missed
five source-less fragments named in TR46's loader errors. The installed text/data
and observed palette describe river roles but do not establish whether component
discovery wraps. A limited read-only xref/disassembly trace of the specific
missing-source diagnostic establishes coordinate bounds and marker counting in
that routine. It does not establish every river-mesh rendering rule or engine
appearance. No executable byte, memory or installation is changed; no executable
excerpt, game raster or raw trace enters the repository.

The independent adapter constructs the final PNG codes directly from the logical
network: valid starts/joins on planar trees, original width classes, exact uncut
networks. It neither changes the PNG format nor patches an engine, shader or
already written world. Hydrology and carved valleys remain continuous. A point
with no remaining raster edge is explicitly counted as a non-line primitive,
without rerouting its physical river. Invalid topology fails loudly. Synthetic
cuts and independently parsed written images provide compatibility evidence for
the current fingerprint only. The necessity, distribution boundary and legal
limits above continue to apply; this is no additional clearance.

### Follow-up: primary heightmap source support (2026-10-25, 0.12.6 / epoch 36)

[V-LOCAL / V-EXEC C313–C315] The owner's 0.12.3 crack persists despite the
outside-only copies. Installed shader inspection separates the half-open decal
bounds test from its in-world, clamped grid lookup; earlier tests proved only
the bounds geometry, not CPU admission. The source virtual-texture interface
explicitly accounts for non-power-of-two source sizes. No new executable-code
trace establishes admission, and no such claim is made.

The existing R-004 writer now constructs each edge primary with periodic source
support: 9216×4096 height/material `.info`/`.bin` layers in the same tiled, bordered,
LZAV format. Cached size/position and the original active JSON instance change
in agreement; no outside-only copy remains. A header/sample-size mismatch fails
before serialization. The independent program needs this source domain to supply
boundary/halo terrain through the game's existing heightmap interface. Templates
and scripts do not populate these pixels; official-interface investigation and
its limits remain those of R-004. No new closed format, engine/shader patch,
installation edit or post-output repair is introduced.

Synthetic band/worker/wrap equality, Windows/native byte equality and decoded
TR46 read-back verify 536,870,912 unchanged original level-zero samples and
67,108,864 opposite-edge support samples. Source-size changes naturally alter
the mip pyramid; neither renderer equivalence nor disappearance of the crack is
asserted. Original/derived assets, executable excerpts and raw measurements stay
local and ignored. The existing compatibility fingerprint, local-generation
boundary and legal limits still apply, without additional clearance.

### Follow-up: maritime identities and script access (2026-10-25, 0.12.7 / epoch 37)

[V-LOCAL / V-EXEC C317–C319] TR46's inherited sea graph was globally connected
but left large local detours; arbitrary closed-water partitions created adjacent
unrelated ocean names. Script replacements also mapped vanilla port landfalls
to inland land. Initial geography construction now adds bounded local lanes,
folds connected closed water without a size partition and retains access roles
in the shared script remap. This uses R-004's existing locations PNG and text
interfaces (`default.map`, definitions, templates, ports, adjacency, locators
and scripts). No additional binary structure or engine modification is needed.

The existing R-001 spline writer renumbers anchors to the changed definition
order. Independent comparison by location keys and point coordinates verifies
unchanged road geometry, rather than requiring identical numeric anchor IDs.
Terrain, water-texture and river formats are unchanged; generated resources stay
local under the same installation-derived boundary. Synthetic fixtures cover
local routes, closed-component identity and port/passable-water replacement.

Limited read-only tracing of the port/water assertion in the current executable
locates a destination-change routine and its checks, but does not establish
the runtime caller, affected object or cause. Public text/data interfaces and
the log lack that information. No executable bytes are changed or distributed;
disassembly and raw measurements stay ignored. This incomplete trace is not
treated as a new engine movement contract. The engine outcome remains unknown.

### Follow-up: complete ocean courses (2026-10-26, 0.13.2 / epoch 41)

[V-EXEC C349–C352] 657Q reveals a passable lane interrupted by one internal
cell classified as closed ocean, and two other inherited courses ending in
open water. The independent generator needs to supply continuous navigation
data for its changed coastline: the inherited vanilla course and global
reachability alone cannot express this requirement. The existing R-004
location PNG and text interfaces carry the completed lanes, templates,
currents, closed-water lists and associated identities. No new file format,
executable study, engine patch or runtime repair is introduced.

Folding the newly separated closed-water components changes numeric location
indices. The existing R-001 spline reader/writer therefore reindexes the same
land-road strips through its already documented binary structures. No spline
format changes. Synthetic tests, installed-build fingerprinting and an
independent raster/template read-back verify the intended data. Original and
derived maps, binary files and raw reports remain local and ignored; only
project-authored code, synthetic fixtures, descriptions and digests are
distributed. The official-interface limits and legal uncertainty recorded in
R-004/R-001 remain unchanged. Engine movement after this correction is unknown.

### Follow-up: impassable units and mountain height sources (2026-10-25, 0.12.8 / epoch 38)

[V-LOCAL / V-EXEC / INFERRED C321–C323] Vanilla mountains include additive,
locally placed height sources in addition to the primary heightmaps. RNW removed
obsolete placements but did not generate their fine eroded-detail role. The
independent generator now reads the three ordinary installed mountain height
`.info`/`.bin` pairs through the existing R-004 reader, inspects cached scales
and strengths, and samples their heights into the initial primary source bands.
The shader's existing height-transform/addition semantics inform this research;
our overlapping-crest construction is explicitly not an exact simulation of the
vanilla decal stack. No shader, executable or game-installation file is modified.

Why these data are needed and the limits of accessible editor/batch interfaces
remain those of R-004: location templates alone cannot supply per-seed eroded
height samples. No new binary layout is inferred. Shape/range guards, synthetic
band/wrap equality, Windows/Linux sampling parity and full decoded-source
read-back check the writer. Primary source dimensions, mip levels, tile borders
and LZAV streams retain the existing contract. Mountain contributions use the
same continuous crop at both display edges and in periodic padding, without
new outside-only instances. Runtime appearance remains unobserved.

Impassable aggregation uses the existing PNG and text location interfaces.
Roads retain their semantic paths through R-001 while definition indices change.
All decoded game sources, composed rasters, raw measurements and built mod files
stay local and ignored. Only independently authored algorithms, synthetic fixtures,
identifiers and aggregate findings enter the repository; no protected mountain
source is distributed with the generator. Existing compatibility fingerprints,
input manifests and local-generation/distribution boundaries continue to apply.

## R-005 — Read-only TR46 save-state analysis

**2026-10-25; original generator 0.12.3 / epoch 33 campaign, EU5 1.4.4 executable
(Steam 26142040) on 1.4.3 data (26105915); C326–C328;
[experiment 059](../../experiments/059-native-expansion/README.md).** This is a
private diagnostic reader, not a new generator interface or save writer.

**Necessity.** The owner asks whether generated societies expand. Names in the
game log cannot distinguish a defeated state, a renamed formable, an unrelated
reused country slot and a civil-war successor. Current owners, direct subjects,
researched advances and the saved game rules are needed to distinguish a map
generation defect from vanilla AI restrictions. The owner already supplied a
long campaign; requiring another campaign or modifying its saves is unnecessary.

**Available mechanisms and their limit.** The frozen 1337 setup and text logs
are read with the existing script/text readers. They do not provide exact late
ownership. The two `.eu5` files expose standard ZIP entries, but `gamestate`
and `string_lookup` are binary rather than the script text accepted by that
reader. No applicable standalone official exporter was identified in the local
research; this does not assert that no official API exists anywhere. A live
console inspection would require a separately restricted game launch and is
not used. Standard-library ZIP decompression requires no game executable,
downloaded token database, third-party binary, key or change to access controls.

**Studied structures.** On the owner's frozen copies only: the ZIP framing and
CRCs; length-prefixed UTF-8 strings following the lookup's version/opaque header;
little-endian token framing for assignment, containers, scalar values and
per-save string references, including compact reference/number widths. The
reader understands only token forms actually encountered and rejects unknown
forms. Fixed metadata keys are narrowly enumerated. It traverses the selected
country, location, cabinet, colony, diplomacy, timeline and rule containers.
Country handles retain all generation bits; a matching low slot is not an
identity. Dates are checked against the recorded final date and the 1337
ownership baseline. The opaque lookup-header payload and unrelated save
semantics are not claimed to be fully understood.

**Validation and limits.** Both original file hashes and ZIP CRCs pass. All
68,108,132 / 75,749,957 tokens are consumed with balanced containers and no
unknown token; 30,565 definition IDs, 201 retained original start capitals and
738 initial native ownership records bind to the frozen setup. Every current
country's owned-location list agrees with independently counted location-owner
references. Private synthetic checks cover anonymous containers, reference
widths, complete handles, fixed-point values and invalid/truncated framing.
Timeline evidence handles QDL's successor separately from a reused
slot and WBU's civil-war copy separately from WBU/LIA. Ownership histories do
not always include current civil-war transfers: 172 / 102 disagreements with
current-owner snapshots, including 23 native locations in the earlier save.
Consequently they are not an exhaustive acquisition/event history. This
validation supports the reported aggregates, not arbitrary saves, future
versions, lifetime peaks or a generic save specification.

**Compatibility and distribution.** No save is changed, serialized or loaded
by the game, and no game/profile file is written. The independent diagnostic
helpers, raw saves, decompressed strings, scripts and detailed dumps remain in
ignored `local_data/tr46-expansion/`; the original evidence remains frozen under
053's local archive. Git receives identifiers, aggregate findings, hashes and
these interface notes only. No protected token table, substantial game-script
excerpt, executable code, assets or save content is distributed. There is no
generator version/epoch or installed-output change, no runtime hook and no
general save API. Any reuse against another format/build requires fresh
validation rather than assuming these two successful parses establish support.

### Follow-up: expedition lifecycle evidence (2026-10-25, 060)

[V-LOCAL / V-EXEC C329–C332] The same two frozen saves and private reader now
traverse the `expedition_manager` database and selected countries' capitals.
The interoperability need is to distinguish an active blocked route from a
failed expedition absent from the snapshots, without another game launch.
Text logs omit identities for anonymous starts/resumes and the port/water
assertion; the saves cannot recover a missing historical transition either.
No new token form is added. Tombstoned database slots are excluded; complete
object handles and the previously validated location-ID binding are preserved.
ZIP CRCs and all 37 original evidence-file hashes pass. Private helpers/results
stay under ignored `local_data/tr46-expeditions/`; no save writer or general
save API is shipped.

Installed text documentation/type/event/action files supply the lifecycle
contract and allow exact comparisons of the unchanged Pacific start/Dadinga
event blocks. They expose a no-travel mining start and an immediate resume
before a delayed return choice, but do not record runtime option selection or
the effective loaded content from other mounted mods. Limited read-only
string cross-references and disassembly inspect the exhausted-route diagnostic
and possible callers of the previously located destination-change routine.
This addresses the gap in the logs without translating code or adding an
engine hook. It does not establish a complete state layout, default-loading
behavior, runtime caller or cause for the anonymous errors. No bytes, memory,
installation or protection mechanism are changed. No executable excerpt,
substantial game-script block, token dictionary, save or derived dump is
distributed. Only aggregate findings and identifiers enter the repository;
no generated binary/output interface, version or epoch changes.

### Follow-up: AI diagnostics and named-country attribution (2026-10-25, 061)

[V-LOCAL / V-EXEC / INFERRED / UNKNOWN C333–C336] The interoperability need
is to distinguish defects in generated countries/map data from inherited or
unattributed AI diagnostics before changing the generator. The original text
log supplies no actor, target or failed condition for command rejection, and
no operands for the expansion-score division. Installed expansion-target
README/scripts explain the war-target interface but do not recover those
runtime values. The existing C326 read-only save extractions bind the three
named building-warning countries and check for shared landed-state capital
IDs; snapshots cannot recover the anonymous earlier commands or evaluations.
Both source saves pass original hashes and ZIP CRCs, cached extractions match
their research manifest, and no new save token or writing capability is added.

Narrow read-only string cross-references and disassembly of the installed
1.4.4 executable (Steam 26142040, SHA-256 recorded in 061) inspect only the
command gate/logging paths, building-count clamp and zero-divisor diagnostic
branch. This addresses what the log records and the observed list bound;
it does not reconstruct every command validator, final planner score, a
complete engine state layout or the missing runtime cause. No protection,
memory, executable, installation or engine behavior is altered, and no hook
or replacement binary is produced. Text files and the complete archived
RNW inventory supply the override/score evidence separately from this limited
binary inspection. The eight mounted Workshop directories remain an effective-
content attribution limit.

Helpers, per-line rows, hashes and derived disassembly remain private under
ignored `local_data/tr46-ai/`. Only aggregate findings, identifiers and
diagnostic addresses are documented in [061](../../experiments/061-ai-diagnostics/README.md)
and [the AI findings](tr46-ai-diagnostics.md). No proprietary executable
excerpt, script body, token dictionary, log or save data is distributed.
No generated output/binary interface, product version, epoch or installation
changes. These checks are specific to the hashed local build, not a general
AI API or compatibility claim.

### Follow-up: Tordesillas context and saved division line (2026-10-25, 062)

[V-LOCAL / V-EXEC / INFERRED / UNKNOWN C337–C340] The interoperability need
is to separate an inherited option-text failure from the owner's western-
mainland allocation report while preserving the chosen full map wrap. Logs
name the option but omit recipient, scopes and comparison operands. Installed
event/localization/situation/action/trigger/effect text supplies the conditional
scope graph and map-color precedence, but cannot recover the failed rendering
or observation-time line. The existing R-005 reader traverses only the two
validated saves' `situation_manager` and `event_manager` roots, preserving repeated
keys and anonymous lists. It recovers retained post-treaty sides/dates/line;
queued event records do not retain the failed event. No new token, save writer,
general reader API or game hook is added. Frozen hashes and ZIP CRCs pass.

The C305 static `CIsEastOfTrigger` trace is reused. A bounded read-only follow-up
checks references to its map global, the initialization path and RTTI identifying
`CMap`/`CJominiMap`. It does not establish the loaded coordinate span or engine
location point. Addresses are specific to the same hashed 1.4.4 executable:
global RVA **0xfb268a8**, inspected initialization **0x31b9950–0x31ba8f4**,
base-constructor entry **0x777f2f0**, vtable RVAs **0xc837848 / 0xcd42658**.
No protection, executable, memory or installation is changed; no replacement
engine code or binary output is produced. Exact excerpts, save roots, text
sources, hashes and diagnostic helpers remain ignored in
`local_data/tr46-treaty/`; only identifiers and aggregate findings are committed.
No protected token dictionary, substantial script/translation or disassembly is
distributed. The 0.12.9 generator export implements the continuous longitude
axis via vanilla scripted geographies and values (`rnw_treaty_longitudes.txt`)
and parsed script rewrites, introducing no new closed binary format or engine patch.
The exact runtime allocation and missing text context remain explicitly unknown;
neither uncertainty justifies a worldwide vanilla patch or warning suppression.

## Earlier cases still outside this phase

`nodes.dat` is not read or regenerated (opaque; `eu5_export.UNCHANGED_INPUTS`).
The cover's shader/GUI text interfaces retain their earlier evidence records and
have not been reverse-engineered again in this phase.
