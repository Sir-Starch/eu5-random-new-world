# TR46 — Complete session diagnostic catalog

2026-10-25; EU5 1.4.4 / Steam build 26142040, generator 0.12.3.
[V-GAME logs/V-EXEC C302] Read alongside the [problem register](tr46-observer-audit.md).
All counts are from the archived current session. Rows are research summaries;
raw messages remain in ignored `local_data/tr46-observer-20261025/`.

## Current `error.log`: exhaustive origin accounting

**2,366 timestamped records, 61 origins, 2,368 physical lines.** The persistent
reader entry has two continuation lines. First/last lines are one-based in the
archived original. Repeated engine origins can cover several messages; the
local `error-catalog.json` retains every one. Counts are diagnostic records,
not deduplicated defects. Mirrors in other logs are excluded from these totals.

| Engine origin | Records | First line / clock | Last line / clock | Work ID | Research summary |
|---|---:|---|---|---|---|
| `gfx_caps.cpp:39` | 2 | 1 / 04:03:47 | 2 / 04:03:47 | TR46-L12 | Unrecognized llvmpipe vendor during graphics discovery |
| `pdx_mod_metadata.cpp:218` | 2 | 3 / 04:03:48 | 11 / 04:03:53 | TR46-L12 | Missing old physical-seam mod metadata |
| `dlc_reloadable.cpp:374` | 2 | 4 / 04:03:48 | 12 / 04:03:53 | TR46-L12 | Old physical-seam mod has no metadata |
| `virtualfilesystem.cpp:634` | 15 | 5 / 04:03:51 | 2366 / 06:58:03 | TR46-L11 | Situation icons or DLC thumbnails cannot be opened |
| `pdx_gui_texture.cpp:61` | 9 | 6 / 04:03:51 | 83 / 04:04:29 | TR46-L11 | Situation texture properties reference missing files |
| `pdx_mods.cpp:1102` | 1 | 13 / 04:03:53 | 13 / 04:03:53 | TR46-L12 | Missing old physical-seam mod skipped |
| `pdx_gui_glow.cpp:322` | 6 | 15 / 04:03:53 | 2368 / 06:58:03 | TR46-L11 | DLC thumbnail texture data cannot be loaded |
| `dnamodifier.cpp:342` | 6 | 20 / 04:03:55 | 51 / 04:04:17 | TR46-L11 | Missing Castilian portrait templates |
| `advance_definition.cpp:857` | 2 | 23 / 04:03:56 | 52 / 04:04:18 | TR46-L09 | Unknown levy_sometent unlock |
| `jomini_effect.cpp:557` | 38 | 24 / 04:03:57 | 76 / 04:04:20 | TR46-L09 | Unknown scripted effects |
| `map.cpp:1731` | 5 | 53 / 04:04:18 | 57 / 04:04:18 | TR46-L01 | River source missing; five failures, 698 pixels |
| `game_dlc.cpp:443` | 1 | 77 / 04:04:29 | 77 / 04:04:29 | TR46-L09 | d009 game DLC lacks matching descriptor |
| `jomini_trigger.cpp:275` | 2 | 84 / 04:04:30 | 85 / 04:04:30 | TR46-L09 | d009 achievement policy trigger postvalidation fails |
| `pdx_persistent_reader.cpp:289` | 1 | 86 / 04:04:31 | 86 / 04:04:31 | TR46-L09 | Key-reference parse error without a named source file |
| `database_object_reflection.h:694` | 10 | 89 / 04:04:31 | 98 / 04:04:31 | TR46-L09 | Database counts differ from static expected sizes |
| `persistence_tests.cpp:1068` | 24 | 99 / 04:04:31 | 127 / 04:04:31 | TR46-L09 | Missing effect-tooltip localization |
| `jomini_eventtarget.h:314` | 97 | 113 / 04:04:31 | 219 / 04:04:31 | TR46-L09 | Unresolved database links (27 distinct targets) |
| `jomini_effect.cpp:141` | 11 | 220 / 04:04:31 | 230 / 04:04:31 | TR46-L09 | Effect postvalidation fails |
| `jomini_effect.cpp:1165` | 17 | 231 / 04:04:31 | 315 / 04:04:32 | TR46-L09 | Flags referenced without a recorded setter |
| `jomini_effect.cpp:1207` | 76 | 232 / 04:04:31 | 326 / 04:04:32 | TR46-L09 | Possible-match suggestions accompanying script warnings |
| `jomini_effect.cpp:1160` | 3 | 239 / 04:04:31 | 321 / 04:04:32 | TR46-L09 | Unused script variables |
| `game_object_locators.cpp:1158` | 1 | 327 / 04:04:33 | 327 / 04:04:33 | TR46-L08 | Incomplete VFX locator |
| `manual_locators_database.cpp:212` | 2 | 328 / 04:04:33 | 329 / 04:04:33 | TR46-L08 | City/VFX transform override changes noticed |
| `dlc_setup_reader.h:18` | 12 | 330 / 04:04:35 | 341 / 04:04:35 | TR46-L09 | Unavailable d009 DLC used in setup |
| `static_modifier.cpp:537` | 9 | 342 / 04:04:48 | 350 / 04:04:48 | TR46-L09 | Unused modifier notices |
| `religious_order_manager.cpp:157` | 6 | 351 / 04:04:48 | 356 / 04:04:48 | TR46-L09 | Orders skipped because d009 DLC is unknown |
| `pdx_achievements_steam.cpp:298` | 12 | 357 / 04:04:59 | 368 / 04:04:59 | TR46-L09 | Unrecognized achievements |
| `pdx_gui_widget.cpp:3891` | 3 | 369 / 04:05:05 | 379 / 04:15:31 | TR46-L11 | Map-mode input action absent |
| `particle_event.h:114` | 5 | 370 / 04:14:50 | 386 / 04:30:33 | TR46-L11 | Missing waves effect entity |
| `state_event.h:391` | 5 | 371 / 04:14:50 | 387 / 04:30:33 | TR46-L11 | Boat foam-stop state-machine error |
| `expedition_manager.cpp:675` | 178 | 380 / 04:19:49 | 2352 / 06:57:17 | TR46-L03 | 177 mining surveys and one Pacific crossing exhaust waypoints without ending; corrected by C329 |
| `jomini_scriptvalue.cpp:275` | 3 | 381 / 04:20:24 | 534 / 05:02:28 | TR46-L04 | Division by zero in neighbouring expansion target |
| `expedition_effects.cpp:352` | 38 | 383 / 04:27:45 | 2010 / 06:46:12 | TR46-L03 | Resume requested for a non-stalled expedition |
| `jomini_custom_text.h:93` | 478 | 394 / 04:40:31 | 2204 / 06:49:27 | TR46-L11 | Invalid subunit text object for type/prefix |
| `jomini_custom_text.h:108` | 239 | 396 / 04:40:31 | 2205 / 06:49:27 | TR46-L11 | Invalid subunit text object for levy structure |
| `common_effects.cpp:3246` | 306 | 432 / 04:43:37 | 2139 / 06:48:54 | TR46-L10 | Resolution proposal rejected |
| `diplomacy.cpp:5979` | 1 | 464 / 04:44:38 | 464 / 04:44:38 | TR46-L10 | Required CB target character absent |
| `jomini_scriptlists.cpp:414` | 4 | 493 / 04:55:36 | 1845 / 06:42:49 | TR46-L10 | Requested list index capped to list size |
| `weather_effects.cpp:108` | 6 | 494 / 04:55:43 | 1842 / 06:42:45 | TR46-L10 | Insufficient weather-system path |
| `ticktasks_ai.cpp:82` | 1 | 519 / 05:00:16 | 519 / 05:00:16 | TR46-L10 | AI finds no good option for flavor_vol.1102 |
| `jomini_scriptvalue.cpp:1965` | 2 | 538 / 05:04:38 | 1453 / 06:19:33 | TR46-L10 | Wrong script-value type in HRE events |
| `expedition_effects.cpp:70` | 4 | 542 / 05:06:24 | 556 / 05:10:36 | TR46-L03 | Expedition type cannot start |
| `expedition_effects.cpp:76` | 38 | 559 / 05:11:02 | 917 / 05:28:51 | TR46-L03 | Expedition leader fails requirements |
| `jomini_effect_impl.cpp:381` | 2 | 869 / 05:21:14 | 919 / 05:29:22 | TR46-L10 | Unbounded script loop stopped after 1,000 iterations |
| `pdx_gui_layout.cpp:221` | 2 | 922 / 05:32:05 | 923 / 05:32:05 | TR46-L11 | Position set on widget inside a layout |
| `event_database.cpp:563` | 1 | 1121 / 05:53:17 | 1121 / 05:53:17 | TR46-L10 | flavor_vij.1203 has no valid country root |
| `pdx_text_formatter.cpp:807` | 40 | 1210 / 05:56:43 | 1268 / 05:56:44 | TR46-L06 | Unrecognized country-name formatting |
| `countryname.cpp:1135` | 20 | 1212 / 05:56:43 | 1269 / 05:56:44 | TR46-L06 | Country-name text data unavailable |
| `expedition_manager.cpp:67` | 3 | 1419 / 06:12:25 | 1553 / 06:30:52 | TR46-L03 | Pathfinding fails between expedition waypoints |
| `expedition_manager.cpp:801` | 3 | 1420 / 06:12:25 | 1554 / 06:30:52 | TR46-L03 | Western voyage discards unreachable waypoint |
| `event_target_links_to_country.cpp:1209` | 1 | 1423 / 06:13:16 | 1423 / 06:13:16 | TR46-L10 | Civil-war enemy scope evaluates to null |
| `war_manager.cpp:622` | 1 | 1424 / 06:13:19 | 1424 / 06:13:19 | TR46-L10 | Invalid civil-war recovery call |
| `common_effects.cpp:2498` | 6 | 1505 / 06:21:21 | 1750 / 06:38:24 | TR46-L10 | Migration source and destination are the same province |
| `movement.cpp:156` | 589 | 1523 / 06:27:09 | 2362 / 06:57:48 | TR46-L10 | No alternative religion for a movement |
| `pdx_assert.cpp:231` | 1 | 1574 / 06:32:02 | 1574 / 06:32:02 | TR46-L02 | Destination port/water assertion |
| `ai_tick_context.cpp:169` | 3 | 1622 / 06:34:36 | 2015 / 06:46:18 | TR46-L04 | Building-candidate truncation exceeds available count |
| `pdx_data_factory.cpp:1357` | 1 | 1730 / 06:37:42 | 1730 / 06:37:42 | TR46-L05 | Treaty text cannot find overlord data type |
| `pdx_data_factory.cpp:1367` | 1 | 1731 / 06:37:42 | 1731 / 06:37:42 | TR46-L05 | Treaty text cannot promote overlord data |
| `pdx_data_factory.cpp:1044` | 1 | 1732 / 06:37:42 | 1732 / 06:37:42 | TR46-L05 | Treaty text statement conversion fails |
| `pdx_data_localize.cpp:192` | 1 | 1733 / 06:37:42 | 1733 / 06:37:42 | TR46-L05 | Tordesillas option localization fails |
| `pdx_ecs_entity_3d_utils.cpp:608` | 7 | 1907 / 06:43:21 | 1913 / 06:43:23 | TR46-L11 | Cargo-locator entity attachment fails |

Total: **2366** timestamped records.

## AI command diagnostics

`ai.log`: **57,352 records**, split into **57,156 execution** warnings and
**196 posting** warnings. **42** categories distinguish the stage and command.
These records generally lack country/target context; totals cannot be assigned
to generated natives or used as a measured expansion rate. Work ID: TR46-L04.
[061's follow-up](tr46-ai-diagnostics.md), C333–C336, validates every line,
documents the inherited unguarded war-score division and binds the three
building clamps to Old World identities. Missing command actors/reasons and
division operands remain unknown; no native AI fix is inferred.

| Stage | Command identifier | Records |
|---|---|---:|
| execute | `set_cabinet_action` | 35724 |
| execute | `disband_subunit` | 5898 |
| execute | `build_road` | 3170 |
| execute | `change_trade_capacity` | 2396 |
| execute | `diplomaticactioncommand` | 2324 |
| execute | `transfer_occupation` | 2096 |
| execute | `toggle_can_attach_to` | 1602 |
| execute | `construct_building` | 939 |
| execute | `merge_army` | 834 |
| execute | `move_unit` | 479 |
| execute | `add_bureaucracy` | 397 |
| execute | `split_unit` | 264 |
| execute | `upgrade_rgo` | 259 |
| execute | `perform_generic_action` | 178 |
| posting | `diplomaticactioncommand` | 114 |
| execute | `set_unit_activity` | 90 |
| execute | `detach_unit` | 72 |
| posting | `move_unit` | 66 |
| execute | `consolidate` | 57 |
| execute | `asssume_siege_control` | 53 |
| execute | `hire_mercenary_from_leader` | 53 |
| execute | `production_methods` | 48 |
| execute | `refill_garrison` | 40 |
| execute | `use_unit_ability` | 33 |
| execute | `attach_unit` | 25 |
| execute | `embark_army` | 21 |
| execute | `raise_all_levies` | 20 |
| execute | `found_city` | 19 |
| execute | `construct_unit` | 14 |
| execute | `military_objective_unassign_unit` | 12 |
| execute | `upgrade_subunit` | 9 |
| posting | `destroy_building` | 8 |
| execute | `balance_army` | 8 |
| execute | `create_supply_depot` | 8 |
| posting | `cancel_movement` | 5 |
| execute | `take_over_siege` | 4 |
| execute | `marry_noble_command` | 3 |
| execute | `disband_unit` | 3 |
| posting | `transfer_occupation` | 3 |
| execute | `invite_scholars` | 2 |
| execute | `vote_on_resolution` | 1 |
| execute | `unembark_army` | 1 |

## Diagnostics outside `error.log`

These are additional families or context from `debug.log`, `game.log` and
`multiplayer.log`; do not add their mirrored messages to the error total.
Routine successful loading, transitions, political activity and zero-count
repair summaries are not failures. The local origin catalogs retain them too.

| Source / engine origin | Records | First / last line | Work ID | Research summary |
|---|---:|---|---|---|
| `debug.log` / `pdx_paths.cpp:69` | 1 | 7 / 7 | TR46-L12 | Missing checksummed-paths settings |
| `debug.log` / `gfx_vk_master_context.cpp:122` | 2 | 16 / 52 | TR46-L12 | Graphics-context game-version parse falls back to 1.0.0 |
| `debug.log` / `pdx_localize.cpp:257` | 226 | 20 / 30264 | TR46-L11 | Duplicate localization-key notices |
| `debug.log` / `pdxfilewatcher.cpp:197` | 1 | 387 / 387 | TR46-L12 | Filewatcher directories not yet mounted |
| `debug.log` / `defines.cpp:230` | 46 | 426 / 15464 | TR46-L12 | Missing define-macro notices |
| `debug.log` / `icondatabase.h:273` | 34 | 10230 / 30329 | TR46-L11 | Default-icon lookup falls back |
| `debug.log` / `pdxfilewatcher_windows.cpp:333` | 2 | 10241 / 25255 | TR46-L12 | Invalid tools_import path |
| `debug.log` / `savegameinfo.cpp:402` | 52 | 34539 / 34590 | TR46-L11 | Setup-file magic warning defaults to text |
| `debug.log` / `audio2_wwise.cpp:811` | 2 | 34685 / 34687 | TR46-L11 | Winter audio parameter absent |
| `debug.log` / `audio_state.cpp:184` | 2 | 34686 / 34688 | TR46-L11 | Winter audio state parameter absent |
| `debug.log` / `camera_state_ambience_node.cpp:47` | 5689 | 34735 / 50311 | TR46-L11 | MapHeight audio limits absent |
| `debug.log` / `rivers_ambience_node.cpp:20` | 5747 | 34736 / 50312 | TR46-L11 | River audio alias absent |
| `game.log` / `initialize_from_bookmark.cpp:1396` | 2 | 3570 / 3571 | TR46-L07 | DWS and generated GVQ start relation-budget warnings |
| `multiplayer.log` / `commanddispatcher.cpp:77` | 20 | 30 / 277 | TR46-L12 | Invalid preferred-map-mode commands; each has a separate data record |

## Limits of attribution

`ecs.log:2–67` additionally contains **66** global animation-variable deprecation
notices (`state_machine_parse_helpers.h:389`), assigned to TR46-L11. Its other
errors mirror the boat/cargo diagnostics above. `gui.log` mirrors the missing
textures and layout errors. The dedicated-server checksum and observer-return
warnings, graphics NVAPI check not performed, ordinary setup/hardware records,
and performance samples are context; see TR46-L12. No new error family is
claimed from normal state transitions or zero-count repair summaries.

[V-LOCAL C303] The event CSV is from 2026-10-23; rotated errors and the 02:53
crash folder predate TR46. The playset lists TR46 alone but VFS logs also mount
eight Workshop resources. Missing d009 DLC and some errors appear before the
TR46 mount. None of this replaces a same-build vanilla comparison. No diagnostics
were suppressed, no files repaired and no game/launcher changes made by this audit.
