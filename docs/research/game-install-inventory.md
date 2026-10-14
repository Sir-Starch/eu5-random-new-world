# Local EU5 installation inventory

Observed 2026-10-13 on Linux x86_64 with a Wayland desktop. All game paths below are relative to `<steam-library>/steamapps/common/Europa Universalis V/` unless stated otherwise. No game files were copied into this repository.

| Item | Observation | Evidence |
|---|---|---|
| Steam identity | App 3450310, `1.4-open-beta` branch, build 25905365 | [V-LOCAL] `../appmanifest_3450310.acf` and Steam library metadata |
| Running version | 1.4.1 | [V-GAME] main menu and temporary-profile `logs/debug.log`, mod-version line, 2026-10-13 |
| Executable | Windows PE `binaries/eu5.exe`, running under Steam Proton | [V-LOCAL] `file binaries/eu5.exe`; [V-GAME] Proton process and logs |
| Display | Wayland desktop, Steam active; Vulkan renderer reported an NVIDIA GPU | [V-LOCAL] environment commands; [V-GAME] debug log |
| User data | `steamapps/compatdata/3450310/pfx/drive_c/users/steamuser/Documents/Paradox Interactive/Europa Universalis V/` in the same Steam library | [V-LOCAL] directory inspection |
| Normal mod/log/save directories | `mod/`, `logs/`, `save games/` under that user directory | [V-LOCAL] directory inspection |
| Isolated test profile | `/tmp/rnw_eu5_validation/`; launched with `-userdir Z:\tmp\rnw_eu5_validation` | [V-GAME] files and logs appeared there |

## Representative files

| Relative path | Observed format / size / role |
|---|---|
| `game/in_game/map_data/default.map` | UTF-8, 178 KiB; map references and `wrap_x = yes`, `equator_y = 3340` [V-LOCAL] |
| `game/in_game/map_data/definitions.txt` | UTF-8 BOM, 504 KiB; continent → subcontinent → region → area → province → location keys [V-LOCAL] |
| `game/in_game/map_data/named_locations/00_default.txt` | UTF-8 BOM; named key ↔ RGB color declarations [V-LOCAL] |
| `game/in_game/map_data/locations.png` | RGB 8-bit, 16384×8192, 8.4 MiB on disk [V-LOCAL] |
| `game/in_game/map_data/rivers.png` | Indexed 8-bit, 16384×8192, 1.5 MiB [V-LOCAL] |
| `game/in_game/map_data/adjacencies.csv`, `ports.csv` | 11 KiB and 152 KiB; connectivity and ports [V-LOCAL] |
| `game/in_game/map_data/nodes.dat` | Opaque 11 MiB data file; actual role unverified [V-LOCAL]/[UNKNOWN] |
| `game/in_game/map_data/location_templates.txt` | 3.6 MiB; location attributes including topography, vegetation, climate, religion, culture, raw material [V-LOCAL] |
| `game/in_game/gfx/terrain2/heightmap.png` | 16-bit grayscale 8192×4096, 6.0 MiB; not a global aligned layer, no Americas (C25) [V-LOCAL] |
| `game/in_game/gfx/terrain2/decals/heightmap_*_16*` | 16 decal height tiles with masks, ~965 MiB total; `terrain_properties.json` declares 65536×32768 terrain (C25) [V-LOCAL] |
| `game/in_game/gfx/map/map_objects/generated_*locators*.txt` | City, unit, combat, dock, VFX and volcano locators; `position = { x h z }` with flipped row (C26) [V-LOCAL] |
| `game/in_game/gfx/terrain2/biomes.png` | 8-bit grayscale 8191×4095, 56 KiB [V-LOCAL] |
| `game/main_menu/setup/1337/` | 26 setup files including pops, countries, markets, institutions, roads, locations, colonies [V-LOCAL] |

`rnw inspect` counted 9 continents, 23 subcontinents, 82 regions, 805 areas, 4,309 provinces and 28,573 location keys, of which 6,174 belong to `america`. A corrected parser counted 28,582 named-color declarations: every hierarchy key has one color, nine color keys are outside the hierarchy, and no duplicate keys/colors were found [V-EXEC]. Five of the nine extras occur in `default.map` class lists; their engine meaning is not established [UNKNOWN]. The first parser's 22,314 count was wrong because it skipped inline comments and mixed-case keys; see the research log.

No bundled map editor executable was identified in the inspected installation [V-LOCAL]. `-debug_mode` produces detailed logs [V-GAME]; a usable in-game console or map editor has not been verified [UNKNOWN]. Startup time comparison was not collected reliably. The isolated profile entered an unresponsive first-run Select Language screen; the game was stopped at the owner's request and will not be launched again for this research session [V-GAME].
