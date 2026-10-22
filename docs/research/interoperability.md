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

Path: `game/in_game/gfx/map/spline_network/spline_network.splnet`, 31,615,438 bytes on build 26105915. Evidence: C161 (the log flood), C162 (the format and coverage), C163 (the generated file). Status: **not game validated**. 0.9.30's file loaded and drew no road ([experiment 029](../../experiments/029-spline-strips/README.md), C164); 0.9.31 is under test in [experiment 030](../../experiments/030-spline-probes/README.md) (C165). The vanilla folder also holds a baked navigation mesh, `navmesh2.cache` (281 MB), which this case neither reads nor writes.

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

## Earlier cases to record when they are next touched

Listed from the module names, not re-audited: the compressed object files of `in_game/gfx/map/map_objects` and the instance tiles (`rnw/lzav.py`, `rnw/eu5_objects.py`, `rnw/terrain_tiles.py`), the texture and terrain-decal files (`rnw/dds.py`, `rnw/eu5_terrain.py`), the derived `locations.png` and `rivers.png` (PNG is an open format; the content is derived), the shader and GUI files the cover modifies (text; `rnw/eu5_lobby.py`), and `nodes.dat`, which is not read or regenerated (opaque, [V-LOCAL] `eu5_export.UNCHANGED_INPUTS`).
