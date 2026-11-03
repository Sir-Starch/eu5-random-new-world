# More Locations Mod: potential RNW compatibility

Audit: **2026-11-03**. Scope: the released RNW 1.1.0 / epoch-60 export
architecture and **[1.4] More Locations Mod beta**, Workshop item
[3809335454](https://steamcommunity.com/sharedfiles/filedetails/?id=3809335454),
by Naaku. This is a source/output compatibility assessment, **not a combined
engine-loading or gameplay test**.

## Verdict and evidence boundary

**Do not advertise the two unmodified mods as compatible. Changing load order
cannot reliably retain both More Locations' added Old World locations and RNW's
generated New World. The combination is technically feasible through generation
against an explicitly supported More Locations input layer.**

- [SOURCE] The author's description identifies a map/setup expansion, including
  additions in South America, and explicitly excludes compatibility with other
  location-adding mods and with climate/topography/vegetation replacements. Its
  largely unchanged province borders do not imply unchanged location topology.
- [V-LOCAL] RNW writes complete map files and rewritten complete setup files,
  starting from the installation, rather than reading the game's active mod list.
  The preserved Old World in an ordinary RNW export is therefore the installation's
  Old World, not More Locations' Old World.
- [INFERRED] Those two data models require reconciliation, regardless of whether
  the engine happens to reach country selection with both enabled. A successful
  launch alone would not establish preservation of both mods' features.
- [UNKNOWN] More Locations' actual payload is not installed in either discovered
  Steam library. Its individual filenames, changes to existing location keys,
  colour assignments, binary layouts and setup-file organization were **not**
  inspected. The table below describes confirmed RNW outputs and the necessary
  interfaces of a location expansion; it is not an exact two-payload diff.

The public page and unauthenticated Steam metadata were retrieved without account
actions. The metadata reports update time **2026-10-06 13:40:25 UTC**, content handle
`2242350688620691806`, and size **284,518,670 bytes**; no direct payload URL is
provided. Source snapshots, hashes and the local output inventory are retained
in ignored `local_data/mod-compatibility/3809335454/`. No third-party code was
executed or incorporated, and no game, playset, installed mod or save was changed.

[V-LOCAL] The currently installed Steam manifest is **build 26377361**, newer
than RNW's documented 1.4.6 / 26300913 baseline. All ten map-contract files match
the recorded inputs of the inspected epoch-60 reference. This establishes that
the map-interface comparison below remains relevant; it is **not** a complete
audit or compatibility approval for the newer patch. The reference's embedded
map label says 1.4.5 because that fingerprint is shared across patches; that label
does not independently identify its executable build.

## Where the data meet

Paths are relative to a generated mod. RNW ownership is verified in
`src/rnw/eu5_nw_export.py` and an existing 1.1.0 development / epoch-60 reference,
nonmetadata digest `7171c89a5b179fac1fd75adae917961cbd85fa9479533031aa9a6b2bb9bf0181`.

| Interface | Confirmed RNW behavior | Consequence for More Locations |
|---|---|---|
| `in_game/map_data/locations.png` | Writes one complete global raster with generated geography and preserved input Old World pixels | A location raster cannot be combined by choosing a later mod. The result needs More Locations' retained pixels and RNW's generated pixels in the same image |
| `in_game/map_data/named_locations/00_default.txt`, `definitions.txt` | Rewrites colour/key declarations and the complete hierarchy | Colours, keys and parents must agree with the combined raster; additional uniquely named files alone cannot supply the missing geometry |
| `in_game/map_data/default.map`, `location_templates.txt` | Rewrites class lists and templates, keeping the input's surviving records | New retained locations need their classes, climate, topography, vegetation and resources; removed American records must not be reintroduced |
| `in_game/map_data/ports.csv`, `adjacencies.csv` | Rewrites ports and crossings against the final geography | Ports, endpoints and sea references must correspond to the same combined map |
| `in_game/gfx/map/map_objects/generated_*`, map-data port locators | Writes map placement for cities, armies, battles, docks and other objects | Missing or stale positions can affect only some locations even when country selection looks plausible |
| `in_game/gfx/map/spline_network/spline_network.splnet` | Rebuilds road strips and renumbers retained anchors against the final hierarchy | Copying either pre-existing network unchanged is insufficient when location order/topology differs |
| `main_menu/setup/1337/` | The inspected export replaces pops, buildings, countries, markets, roads, development and several further setup files | New locations must retain appropriate initial state; vanilla-American content must be removed or rebound consistently |
| Terrain, water, vegetation and map objects | Emits world-wide resources derived from the installed input with local changes | Pixel geometry and rendered layers must be coherent; exact additional overlap requires More Locations' files |

The key distinction is **geographic preservation versus file preservation**.
RNW preserves Old World content inside many files that it replaces in their
entirety. Separate geographic intent does not create separate file ownership.
Renaming global files or adding metadata dependencies does not perform a merge.

## What load order can and cannot achieve

Here, **A → B means B has priority for overlapping files**. These are expected
outcomes under ordinary file override behavior, not observed runs of this pair.
The unavailable More Locations payload prevents an exact list of surviving
non-overlapping records.

| Order | Expected result | Can it count as compatibility? |
|---|---|---|
| More Locations → ordinary RNW world | RNW's global map and tables win where paths overlap. Added Old World geometry is lost; independent More Locations setup/localization files may survive | No: a launch could succeed while the principal More Locations feature is absent, or leave references to absent locations |
| Ordinary RNW world → More Locations | More Locations' overriding global map resources win; generated RNW setup/scripts may still survive | No: generated locations, country ownership and geography can cease to agree; the exact symptom could be missing content, errors or a failed load |
| Supported combined export | One coherent map, hierarchy, placement, road network and start state | Feasible in principle; needs an actual payload audit and verification |

Thus **it may appear to work**. One mod might effectively erase most of the other,
or errors might concern locations not yet visited. No evidence here establishes
a deterministic crash, and no evidence establishes full compatibility either.
There is no justified recommendation to use one of the two ordinary orders as
a supported solution. The existing Refined Colonization load-order recommendation
does not extend to this map expansion.

Enabling More Locations before pressing Generate is insufficient: the application
passes `request.game.directory` to the exporter (`app/service.py`); it does not
resolve active mods into its inputs.

## Adaptation options and likely scope

### Preferred: a supported generation input layer

Build an isolated effective input tree from **installed game → pinned More
Locations files**, then generate RNW from that coherent tree. Never patch the
game installation. Keep the resulting gameplay content in the generated world,
consistent with RNW's single-world-mod architecture.

The present architecture already supplies useful pieces: the canvas selects
American geography while protecting other continents; text writers preserve
surviving input records; road generation remaps retained keys; key allocation
avoids known localization hashes. These are reasons for feasibility, **not proof
that an unmodified generator already accepts this alternate map**.

Necessary work:

1. Inspect the actual More Locations payload and resolve its file/object merging
   rules, dependencies, source patch and any changes to existing identifiers.
2. Validate and fingerprint the effective map as an explicit compatibility
   profile. The normal map fingerprint guard will change; blindly accepting an
   unknown fingerprint is not an implementation of compatibility.
3. Preserve the expansion's Old World raster, hierarchy, templates, start state,
   placements, names and other affected resources; replace its American portion
   consistently. Audit any new consumers of removed American keys, including
   province/area keys that RNW's current vanilla disposition table never saw.
4. Check the combined road network's input anchor conventions and all retained
   contacts. Add construction support where the expansion's data differ from
   the current assumptions.
5. Make the UI location estimate account for the effective Old World rather
   than its fixed vanilla baseline. Keep the final location cap enforced.
6. Record the external input version/hashes in reproducibility and recovery;
   verify unchanged Old World data against the effective input, internal
   references and deterministic output. Engine loading/gameplay remain separate
   evidence after the offline checks.

This is **bounded integration work**, not a new geography algorithm or a redesign
of both mods. Its exact effort cannot be estimated honestly without the payload.
An initial experiment may reuse much of the exporter, but a supported feature
needs more than a load-order setting or a few edited lines.

### Work on the More Locations side

An Old World-only edition, stable location keys/colours, documented map inputs
and consistent start/locator/road data would reduce RNW's integration burden.
However, an Old World-only edition still has to supply a global location raster:
**removing its American changes alone does not make two global map mods stack**.

A post-generation merger is another technical possibility, but it must reconcile
all the interfaces above for **each generated world**. A static universal file
replacement cannot know RNW's seed-dependent locations, colours and anchors.
Construction through RNW is the better fit for this project's invariants; a
separate enabled companion patch is not the proposed delivery model.

### A concrete capacity constraint

[V-LOCAL] RNW currently enforces **32,000 total location identities** in
`eu5_nw_export._check_identity_budget`. The inspected reference has **29,380
named-colour entries** (29,371 hierarchy locations), leaving **2,620 identities**
before that cap. Retaining more than 2,620 extra identities with that otherwise
unchanged final world would exceed the cap. This is an illustration for this
world, not a count of More Locations' retained additions or a claim that all
presets exceed the cap. A coarser generated map can leave more capacity.

The author's approximate location totals cannot be added blindly to RNW's:
the current vanilla named-colour table already contains 28,582 identities, so its
counting scope differs from the page's approximate vanilla total. The integration
needs the actual surviving Old World additions, including any removed/renamed
identities, and the final total including water and wastelands.

## Result of this assessment

- Direct unmodified stacking: **unsupported, with a structural map conflict**.
- Load-order-only remedy preserving both main features: **not supported by the
  architecture or evidence**.
- A launch that appears successful: **possible; full compatibility does not
  follow**.
- A merged generated world retaining More Locations' Old World: **technically
  plausible**, with input-profile, topology/start-state and capacity work.
- Small fix entirely in the other mod: **insufficient if it only changes order,
  filenames or removes American additions**; useful preparatory changes exist.
- Exact conflicting-file list, integration size and engine behavior: **unknown
  until the actual payload is inspected**. No owner game sitting is required
  merely to establish these structural findings.
