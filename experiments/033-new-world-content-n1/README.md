# 033 - New World content, N1: official languages, neutralized identities, exceptional places

2026-10-23, generator 0.10.4, algorithm epoch 14. **NOT GAME VALIDATED.** Stage N1 of the [content plan](../../docs/content-plan.md); claims C186-C190.

What the candidate changes against the last installed world (6DIV, 0.10.1):

- [V-EXEC C186] The mod writes its name files in all eleven official languages of 1.4.3, Turkish included.
- [V-EXEC C187] Closed gates (`always = no`) switch off, on generated land: 82 events about American history (conquistadors, colonial incidents, companies, the Boston Massacre, Pocahontas and so on), the eight vanilla American scripted country names (New Spain, New Granada, Peru, New York, New Amsterdam, Nova Scotia, Jamaica, Rio de la Plata), the three colonial formables (USA, Canada, Mexico), the Panama canal's advance and decisions, and the pilgrimage to Cholula. The historical formables whose culture the world holds take that culture's places as territory: in this world `INC_f` (101 places), `MAY_f` (83 of 102), `IRO_f` (24) and `PUE_f` (8); `AZT_f` is closed (too few Nahua places), and no location has the Nahuatl religion as its main one, so the start effect for the Huitzilopochtli god can never hold.
- [V-EXEC C189] Five exceptional resource places: a great silver lode (`rnw_loc_05098`), a rich silver vein (`rnw_loc_02434`), a silver seam (`rnw_loc_04854`), a mercury lode (`rnw_loc_01788`) and a rich fishery (`rnw_loc_02070`), each with the size of the vanilla bonus it replaces.
- Not replaced yet, so **lost for now** (decided in N0, carried by later stages): the Cahokia river-city chain, the Aztec and Inca chains and the temple of Tenochtitlan (N3); the Haudenosaunee and Pueblo chains, colonial naming and the road to independence (N4).

Installed: `rnw_exp_world_fx2elamqlt`, **RNW: Continents FX2E**, code `RNW1-080G0-00003-EF38N-A0050-80813-BM0FB-H644` (continents, seed 3706823338, the same land as 6DIV with `empire_permille` 1000), 764 files; every file hashes to the export's own record (764 of 764, 26 records are not mod files). Installed beside `rnw_exp_hub`, `rnw_exp_world_6dive2c4l6` and `rnw_exp_world_cyhlrdiik7`, which are untouched. See [installed record](../INSTALLED.md).

## What to see (none of it is observed)

**The owner runs the [console sitting 036](../036-console-session/README.md), not the list below, which would take a campaign; the list stays as the record of what each point asks.** Point 1 is read from the logs by the agent, point 4 is row 9 of the sitting, points 2, 3 and 5 are not in the sitting (a colony and a foreign culture's state need play; they wait for N4 and L1).

1. Enable FX2E with the hub instead of 6DIV. Start any game. Keep `error.log` and `game.log` and compare with the 6DIV run: expect no new line about events, formables, scripted names, decisions, static modifiers or localization keys.
2. A Spanish and an English colony (found one of each, or look at a colonial nation): neither is called *New Spain*, *Peru*, *New York* and the like. What the game calls them instead is [UNKNOWN] (the engine's default for a colonial nation); note it.
3. Formables: as a state of a culture whose places carry a formable (Quechuan, Maya, Haudenosaunee or Pueblo cultures in this world), the formable appears in the formables list with a territory of that culture's places; as another culture it does not. USA, Canada and Mexico do not appear for any country.
4. Exceptional places: open the five locations (the keys above; find them with the console or the location search) and read the modifier: name, text and the output bonus. The fishery's bonus needs the fishing good.
5. A Turkish interface (if the game's language can be switched): no raw keys over the New World's names.
6. The Old World must be as before: events of the Old World countries (Castile, England, Portugal) still fire in their usual years except those about American history.

Not part of this run: replacements of the retired chains (N3, N4), the hook experiment of N2.

## Evidence

[V-EXEC] `make check` (format, lint, types; 994 tests; 23 Rust tests). The 12 local tests pass with `RNW_REPRODUCE=1`, the reference world of epoch 14 (762 files, `da8dbee7c7cf6bf04f135f6f5d6d44683967c0642e041da2b53de136d26d623f`, code `RNW1-0426C-SYW6B-MW73Y-C0050-801JF-ZT0`) reproduces, and `test_local_layers_keep_to_themselves` (`RNW_LAYERS=1`) shows that rerolling the peoples leaves the exceptional places and rerolling the resources leaves the countries.

[UNKNOWN] That the engine takes `always = no` in a formable's `potential`, a scripted name's `country_trigger` and an advance's `potential` as it does elsewhere; what a colonial nation without a scripted name is called; how the Turkish interface reads the new files.
