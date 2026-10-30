"""Every string the window shows, in English, and the language the window speaks.

The English is here; the other official languages are the ``window`` catalogs
(``rnw.translations``). The window starts in the language the player chose in its settings, else
the language Steam runs the game in (``discovery.game_language``), else the system's, else
English (``docs/localization.md`` §2.2). ``set_language`` is called once before the window is
built; a change takes effect when the generator starts again.
"""

from __future__ import annotations

import locale
from functools import cache
from typing import Final

from rnw import translations
from rnw.languages import SOURCE
from rnw.messages import MESSAGES, Said
from rnw.progress import STAGES
from rnw.settings import SettingsError
from rnw.worldfile import WorldFileError

TITLE: Final[str] = "Random New World"
GAME: Final[str] = "Europa Universalis V"
STRINGS: Final[dict[str, str]] = {
    "undo_roll": "Undo roll",
    "task.undo": "Restoring the previous version",
    "copy_tag": "Copy tag",
    "copy_picture": "Copy picture",
    "destination.library": "Keep the mod in the library",
    "destination.mod": "Copy the mod to a folder",
    "destination.world": "World file only",
    "destination_choose": "Choose destination...",
    "destination_missing": "Choose where to save this world first.",
    "tab.notes": "Notes",
    "starred": "Favourite",
    "user_tag": "Your tag (up to 64 characters)",
    "notes_hint": "Notes about this world (up to 16,384 characters)",
    "save_notes": "Save notes",
    "notes_saved": "Notes saved.",
    "candidates": "Choose a continent...",
    "candidates_hint": (
        "Preview six continent sketches before making a world. This reveals their land. "
        "Pick one to use its seed and settings; its final coastline can shift slightly "
        "as locations are formed."
    ),
    "candidate_item": "{number} · {land:g}% land\nSeed {seed}",
    "enqueue": "Add to queue",
    "run_queue": "Run queue",
    "clear_queue": "Clear queue",
    "queue_empty": "Add a world to the queue first.",
    "queue_count": "{count} pending",
    # -- the game, the profile and the settings dialog --
    "game": "Game",
    "profile": "Profile",
    "language": "Language",
    "language.game": "As the game: {language}",
    "language.restart": "The generator speaks the new language from its next start.",
    "browse": "Browse…",
    "settings": "Settings…",
    "settings_title": "Settings",
    "game_status": "Europa Universalis V · build {build}",
    "new_tab.world": "World",
    "new_tab.advanced": "Advanced",
    "new_tab.output": "Save and play",
    "new_tab.queued": "Save and play · {count} queued",
    "world_identity": "Seed and world code",
    "land_tools": "Land sources and previews",
    "output": "Where to save",
    "output_hint": (
        "Every world stays in your library. Add its mod to EU5 now, keep it for later, "
        "or save a copy to another folder. A world file contains the recipe and maps."
    ),
    "queue_title": "Generate several worlds",
    "queue_hint": (
        "Add the current settings to the queue, then change the seed or options for the next "
        "world. Run the queue when you have added everything."
    ),
    "progress_details": "Show stage details",
    "retry_new_seed": "Generate with a new seed",
    "generation_sea_error": (
        "The generator could not build a consistent ocean for this world. "
        "Technical detail: {detail}"
    ),
    "generation_file_error": (
        "The generator could not read or write a file. Check its location, permissions and "
        "available disk space. Technical detail: {detail}"
    ),
    "generation_location_limit": (
        "This world has {count} locations, above the safety limit of {limit}. "
        "Increase the land or sea location size in Advanced, or try a different seed."
    ),
    "generation_river_error": (
        "The generator could not draw a valid river network for this world. "
        "Technical detail: {detail}"
    ),
    "generation_unexpected_error": (
        "An unexpected error stopped world generation. Technical detail: {detail}"
    ),
    "generation_install": "The finished mod will be added to your EU5 profile.",
    "generation_keep": "The finished world will stay in your library.",
    "generation_copy": "The finished mod will be copied to the selected folder.",
    "generation_file": "The world file will be saved to the selected destination.",
    "visibility": "Before you play",
    "world_visibility_hint": (
        "Applies to this world only. Updates its mod picture and country-selection map "
        "without generating it again. To reload the change in EU5, close and reopen the "
        "Mods manager from the main menu."
    ),
    "visibility_updated": (
        "This world's visibility was updated. Close and reopen the Mods manager from "
        "the main menu to reload it in EU5."
    ),
    "tab.tools": "Versions and files",
    "world_versions": "Create a version",
    "world_share": "Share and export",
    "world_details": "World details and checks",
    "close": "Close",
    "game_line": "EU5 build {build} · {game}",
    "game_line_unknown": "EU5 · {game}",
    "profile_line": "Profile · {profile}",
    "game_missing": (
        "EU5 was not found. You can still open world files and look at their maps here; making "
        "a world needs the game's own files. Open Settings and choose its folder."
    ),
    "profile_missing": (
        "No EU5 profile was found. Start the game once so it creates one, or choose its "
        "folder in Settings."
    ),
    "not_a_game": "That folder is not an EU5 installation (game/in_game/map_data is missing).",
    "not_a_profile": "That folder does not exist.",
    "show_new_world": "Show the New World before you play it",
    "show_new_world_hint": (
        "Off keeps this world's pictures and the country-selection map covered as terra "
        "incognita. You can change this later on the world's page without generating it again."
    ),
    "about_generator": (
        "Random New World makes New World maps for EU5. Every world it makes is a complete "
        "mod of its own: tick it in your playset to play it. Share its code or world file. "
        "This generator does not need to be enabled."
    ),
    "about": "About…",
    "about_title": "About Random New World",
    "about_tip": "About this application",
    "about_subtitle": "Procedural New World generator for Europa Universalis V",
    "about_description": (
        "Random New World generates genuine procedural geography, climates, "
        "biomes, rivers, societies, and native empires for Europa Universalis V, "
        "while preserving the Old World intact.\n\n"
        "Every generated world is a complete, self-contained mod: enable it in your "
        "playset to play. Share its world code or export file."
    ),
    "about_author": "Author",
    "about_license": "Licence",
    "about_links": "Links",
    "about_homepage": "GitHub Repository",
    "about_documentation": "Documentation",
    "about_issues": "Report an Issue",
    "about_changelog": "Changelog",
    "about_disclaimer": (
        "Europa Universalis V is a registered trademark of Paradox Interactive AB. "
        "This project is unofficial and not affiliated with Paradox Interactive."
    ),
    # -- the list of worlds --
    "worlds": "Worlds",
    "new_world": "New world",
    "new_world_running": "New world · {percent} %",
    "world_line": "{when} · {place}",
    "list.in_game": "in the game",
    "list.kept": "not in the game",
    "list.code_only": "code only",
    "stray_name": "Unregistered world",
    "stray_line": "{folder} · in the game",
    # -- a new world --
    "type": "World type",
    "type.supercontinent": "Supercontinent",
    "type.supercontinent.about": "One great landmass across the New World, with a few islands.",
    "type.continents": "Continents",
    "type.continents.about": (
        "Large continents, often joined by isthmuses as the Americas are, and islands."
    ),
    "type.small_continents": "Small continents",
    "type.small_continents.about": "Three or four separate continents of similar size.",
    "type.archipelago": "Archipelago",
    "type.archipelago.about": "Five to eleven large islands and many small ones: a world of ships.",
    "type.islands": "Scattered islands",
    "type.islands.about": "A sea full of small islands, with no great landmass.",
    "type.random": "Random",
    "type.random.about": (
        "One of the five world types, drawn at random when chosen and at each press of Random. "
        "The Advanced values are those of the type drawn."
    ),
    "type.chaos": "Total Chaos",
    "type.chaos.about": (
        "A world type drawn at random when chosen, and every Advanced value drawn at random "
        "within its playable range."
    ),
    "quick": "World basics",
    "quick_hint": "Choose the broad balance here. Advanced offers exact values.",
    "quick.custom": "custom",
    "quick.land": "Land",
    "quick.land.about": (
        "How much of the New World is land. More land makes the locations a little larger, "
        "so the world stays within the 32,000 locations EU5 takes."
    ),
    "quick.land.little": "Little",
    "quick.land.normal": "Normal",
    "quick.land.much": "Much",
    "quick.peoples": "Native peoples",
    "quick.peoples.about": (
        "How many peoples live in the New World, and how many centres of culture."
    ),
    "quick.peoples.few": "Few",
    "quick.peoples.normal": "Normal",
    "quick.peoples.many": "Many",
    "quick.states": "Native states",
    "quick.states.about": (
        "How much of the inhabited land is held by organized states rather than tribes."
    ),
    "quick.states.few": "Few",
    "quick.states.normal": "Normal",
    "quick.states.many": "Many",
    "quick.empires": "Extraordinary peoples",
    "quick.empires.about": (
        "How likely an extraordinary native society is to rise around each centre of culture. "
        "A great empire, as the fantasy setting of EU4's random New World: one state many times "
        "the size of the others, with an advanced government, the Old World's technology, a "
        "higher rank and royal roads, feared by its neighbours and resented by its vassals. "
        "Or a league of sea-trading republics, allied but divided by water; a confederation of "
        "highland tribes; a fractured realm whose centres are each other's rivals; or a "
        "sacred centre, a theocracy among rivals of its own faith."
    ),
    "quick.empires.never": "Never",
    "quick.empires.seldom": "Seldom",
    "quick.empires.sometimes": "Sometimes",
    "quick.empires.often": "Often",
    "quick.wealth": "Gold and silver",
    "quick.wealth.about": "How often gold, silver, gems and pearls occur.",
    "quick.wealth.scarce": "Scarce",
    "quick.wealth.normal": "Normal",
    "quick.wealth.rich": "Rich",
    "seed": "Seed",
    "random": "Random",
    "code": "World code",
    "copy": "Copy",
    "paste": "Paste",
    "code_hint": "Paste a world code to get the same world, made by a generator of the same kind.",
    "other_version": (
        "This code was made by generator {made}; this is {current}, which makes a different "
        "world from it. Generator {made} makes the original."
    ),
    "other_changes": "This code also changes settings the window does not show; they are kept.",
    "needs_land_image": (
        "This world is drawn on a land image. Choose the image with Land from an image."
    ),
    "land_image": "Land from an image…",
    "land_image_tip": (
        "Build the world on land you drew or made elsewhere: a picture with white for land and "
        "black for sea, in the proportions of the New World's area. The rest is generated on it."
    ),
    "land_template": "Save template…",
    "land_template_tip": (
        "Write a picture of the area the New World can fill, from your game's map, to draw "
        "your land on in any program: paint land white."
    ),
    "task.template": "Drawing the template…",
    "land_image_chosen": "The land is drawn in an image ({id}).",
    "land_image_clear": "Back to generated land",
    "land_image_title": "Choose the land image",
    "land_image_files": "Pictures (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
    "rolled_code": "This is a version of its continent: {parts} made again.",
    "bad_seed": "A seed is a whole number from 0 to 18446744073709551615.",
    "customize": "Customize",
    "customize_hint": (
        "Every value here still makes a playable world: strange shapes and scarce gold are "
        "yours to choose, and the ranges stop where the generator or the game would break."
    ),
    "customized": "changed from the world type: {count}",
    "untested": "untested",
    "untested_notice": "Some values are outside what was tested.",
    "reset": "Reset",
    "reset_all": "Reset all to the world type",
    "group.land": "Land and sea",
    "group.map": "Map",
    "group.peoples": "Peoples",
    "control.new_world.land_permille": "Land",
    "control.new_world.expand_oceans": "Expand generation into the oceans",
    "control.new_world.expand_oceans.about": (
        "Recommended: gives the New World more room, so its continents need not follow "
        "the outline of the Americas. Keeps the Old World and protected islands."
    ),
    "control.new_world.land_permille.about": "How much of the New World is land.",
    "control.new_world.feature_px": "Size of landmasses",
    "control.new_world.feature_px.about": ("Large: a few great landmasses. Small: many islands."),
    "control.new_world.min_island_px": "Smallest island",
    "control.new_world.min_island_px.about": "Islands smaller than this sink.",
    "control.new_world.persistence_permille": "Rough coasts",
    "control.new_world.persistence_permille.about": ("Higher: more jagged coasts and more islets."),
    "control.new_world.octaves": "Coast detail",
    "control.new_world.octaves.about": "Layers of detail in the coastline.",
    "control.new_world.max_lake_px": "Largest lake",
    "control.new_world.max_lake_px.about": "Enclosed water larger than this stays sea.",
    "control.new_world.wasteland_permille": "Wasteland",
    "control.new_world.wasteland_permille.about": "Share of the land nobody can settle.",
    "control.new_world.precious_permille": "Gold, silver and gems",
    "control.new_world.precious_permille.about": (
        "How often gold, silver, gems and pearls occur, against the vanilla New World."
    ),
    "control.new_world.location_px": "Location size",
    "control.new_world.location_px.about": (
        "Smaller: more locations. EU5 takes about 32,000 locations in all; the generator "
        "refuses a world with more."
    ),
    "control.new_world.sea_zone_px": "Sea zone size",
    "control.new_world.sea_zone_px.about": "Smaller: more sea zones.",
    "control.new_world.province_size": "Locations per province",
    "control.new_world.province_size.about": "How many locations make a province.",
    "control.natives.population_permille": "Population",
    "control.natives.population_permille.about": (
        "Native population, against the population of the vanilla New World."
    ),
    "control.natives.state_share_permille": "Land in states",
    "control.natives.state_share_permille.about": (
        "Share of the inhabited land that native states hold (vanilla: 11 %)."
    ),
    "control.natives.state_spread_permille": "Lone states",
    "control.natives.state_spread_permille.about": (
        "Share of the state land in small groups of states apart from the great centres "
        "(vanilla 1337: about 15 %)."
    ),
    "control.natives.organized_permille": "Organized peoples",
    "control.natives.organized_permille.about": "Share of the cultures organized into tribes.",
    "control.natives.hearths_per_10k": "Cultural hearths",
    "control.natives.hearths_per_10k.about": (
        "Old centres of culture per 10,000 locations; states grow around them."
    ),
    "control.natives.culture_locations": "Culture size",
    "control.natives.culture_locations.about": "Locations of a culture, on average.",
    "control.natives.religion_locations": "Religion size",
    "control.natives.religion_locations.about": "Locations of a religion, on average.",
    "control.natives.tribe_locations": "Tribe size",
    "control.natives.tribe_locations.about": "Locations of a tribe, on average.",
    "control.natives.empire_permille": "Extraordinary peoples",
    "control.natives.empire_permille.about": (
        "Chance, for each cultural hearth, that an extraordinary society rises around it: a "
        "great empire (one state many times the size of the others, with an advanced "
        "government, the Old World's technology, a higher rank and royal roads, feared by its "
        "neighbours and resented by its vassals), a league of sea-trading republics, a "
        "confederation of highland tribes, a fractured realm of rival centres or a sacred "
        "centre with rivals of its faith."
    ),
    "control.natives.state_locations": "State size",
    "control.natives.state_locations.about": "Locations of a native state, on average.",
    "unit.percent": " %",
    "unit.times": " ×",
    "unit.px": " px",
    "unit.": "",
    "install": "Add to the game when it is done",
    "generate": "Generate",
    "cancel": "Cancel",
    "cancelling": "Cancelling…",
    "progress": "Progress",
    "idle": "Ready.",
    "running": "Working: {stages}",
    "eta": "About {time} left",
    "finished": "Done in {seconds} s.",
    "failed": "It did not work: {message}\n\n{report_hint}",
    "report_hint": "To report it, open Settings and press Save diagnostics.",
    "error_world_file": "The file cannot be used: it is damaged or not a world file. ({detail})",
    "error_settings": "These settings cannot be used. ({detail})",
    "cancelled": "Cancelled. Nothing was changed in your game.",
    "ready_no_game": "Choose the game folder in Settings first.",
    "ready_no_profile": "Choose a profile in Settings, or turn adding to the game off.",
    "ready_busy": "The generator is busy.",
    "too_many_locations": (
        "This world would have about {count} locations; EU5 takes about 32,000, and the "
        "generator keeps below {budget}. Raise the location or sea zone size, or lower the land."
    ),
    "outside_range": "This code sets values beyond what the generator allows: {names}.",
    "estimate": "World total: about {count} locations (EU5 engine limit: ~32,000).",
    "estimate_tip": (
        "In EU5, locations include land provinces, sea zones, and lakes across the entire globe "
        "(~22,000 belong to the fixed Old World).\n\n"
        "The engine uses a 16-bit index (~32,767 maximum). To prevent crashes, the generator "
        "keeps the total safely below 31,200.\n\n"
        "Why “much land” can show fewer locations:\n"
        "Sea zones are also counted as locations. More land means less sea area (fewer sea "
        "zones), and the generator automatically scales up land location sizes for larger "
        "landmasses to stay within the engine limit. Total locations may decrease as a result; "
        "this is expected behavior, not an error."
    ),
    # -- a world --
    "name_hint": "Name of this world (up to {limit} characters)",
    "retitle_later": (
        "The name is saved. The game holds this world's files now, so its mod list shows the "
        "name after the world is added again."
    ),
    "preview_hidden": "The New World is hidden as terra incognita.",
    "preview_shown": "The New World is shown.",
    "preview_missing": "This world has no picture.",
    "zoom_hint": "Scroll to zoom, drag to move, double-click to fit.",
    "detail.code": "World code",
    "detail.type": "World type",
    "detail.seed": "Seed",
    "detail.custom": "Custom settings",
    "detail.made": "Made",
    "detail.build": "Game build",
    "detail.generator": "Generator",
    "detail.place": "Where",
    "detail.reproduce": "Made again",
    "repro.none": (
        "This world has no reproducibility record. Its original game build and exact output "
        "cannot be verified."
    ),
    "repro.same_algorithm": (
        "Generator {release} made it with the algorithm of this one: it comes out the same, "
        "byte for byte, if the game's files are the same. Check finds out."
    ),
    "repro.identical": "Checked: made again, all {count} of its files are the same.",
    "repro.differs": (
        "Checked: made again, {count} files are not the same, the first being {first}."
    ),
    "repro.other_algorithm": (
        "Generator {release} made it with an algorithm that differs from this one, so the same "
        "code gives a different world here. Generator {release} makes the original."
    ),
    "repro.other_inputs": (
        "The game's files have changed since it was made ({count} differ): the same code gives a "
        "different world on this game. Keep this world's mod to have it as it is."
    ),
    "repro.newer_format": (
        "Made by a newer generator ({release}) whose record this one cannot read."
    ),
    "part.peoples": "new peoples",
    "part.resources": "new resources",
    "part.peoples.button": "New peoples",
    "part.resources.button": "New resources",
    "part.peoples.tip": (
        "Make the countries, cultures, religions and names again on this very continent. "
        "The land does not change."
    ),
    "part.resources.tip": (
        "Make the raw materials, gold and silver again on this very continent. "
        "The land and the peoples do not change."
    ),
    "edit_same_land": "Same land, change settings",
    "edit_same_land_tip": (
        "Open this world's settings, with its seed, to change the peoples' or the resources' "
        "settings on the same land."
    ),
    "previous_version": "Previous version",
    "keep_both": "Keep this one in the game too",
    "keep_both_tip": (
        "A new version replaces this world in the game unless this is ticked. "
        "Each world in the game takes over a gigabyte."
    ),
    "not_world_file": "That is not a world file (.rnworld or .rnworld-mod).",
    "imported": "The world is in your list, covered. Reveal it to see its maps.",
    "imported_again": "You already had this world; it is as it was.",
    "no_mod_to_send": "This world has no mod here to send: add it to the game first, or make it.",
    "open_world_file": "Open world file…",
    "open_world_file_tip": "Take a world from a .rnworld file, or a built one from a .rnworld-mod.",
    "world_files": "World files (*.rnworld *.rnworld-mod)",
    "export_file": "Save world file…",
    "export_file_tip": (
        "Write this world's code, record and maps into one small file to post or send. "
        "It holds nothing of the game."
    ),
    "send_built": "Transfer built world…",
    "send_built_tip": "Write the whole mod into a file to carry to another of your machines.",
    "send_built_warning": (
        "This file holds the world's mod, about a gigabyte, with images derived from the game's "
        "map. It is for moving the world between your own machines, not for sharing. The other "
        "machine accepts it only with the same game files. Continue?"
    ),
    "copy_mod": "Copy mod to a folder…",
    "copy_mod_tip": "Copy this world's mod into a folder you choose, to manage it by hand.",
    "task.copy": "Copying the mod…",
    "task.receive": "Taking in a built world…",
    "task.send": "Writing the built world…",
    "file_saved": "Saved: {path}",
    "tab.world": "World",
    "compare": "Compare…",
    "compare_title": "Compare worlds",
    "compare_need_two": "Two worlds with revealed maps are needed to compare.",
    "save_picture": "Save picture…",
    "save_picture_tip": (
        "Save the picture shown as a PNG; it is covered unless the New World is revealed."
    ),
    "picture_saved": "Saved: {path}",
    "tab.maps": "Maps",
    "layer.land": "Land",
    "layer.countries": "Countries",
    "layer.cultures": "Cultures",
    "layer.religions": "Religions",
    "layer.resources": "Resources",
    "layer.development": "Development",
    "layer.land.tip": "Vegetation and climate; mountains darker, snow in the cold.",
    "layer.countries.tip": "Who holds which land; capitals are the white dots.",
    "layer.cultures.tip": "The culture of each location; lines where it changes.",
    "layer.religions.tip": "The religion of each location; lines where it changes.",
    "layer.resources.tip": "The raw material of each location; gold, silver, gems and pearls glow.",
    "layer.development.tip": "How developed each location starts: dark is low, bright is high.",
    "reveal_world": "Reveal this world",
    "reveal_world_tip": (
        "Show the maps of this world in the generator. The game's mod list still keeps it "
        "covered unless Settings says so."
    ),
    "covered_maps": (
        "The New World of this world is covered, so you can still meet it in the game. "
        "Reveal it to see its countries, cultures, religions and resources before you play."
    ),
    "no_atlas": "This world's atlas is missing. Open a world file with its maps to restore it.",
    "facts_hint": "Move over the map to see what lies there.",
    "search_hint": "Find a country, culture, religion, resource or place",
    "legend": "Legend",
    "legend.sea": "Sea",
    "legend.lake": "Lake",
    "legend.wasteland": "Wasteland",
    "legend.no_country": "No country",
    "legend.none": "None",
    "legend.uninhabited": "Uninhabited",
    "legend.lowest": "Lowest",
    "legend.middle": "Middle",
    "legend.highest": "Highest",
    "found.country": "Country",
    "found.culture": "Culture",
    "found.religion": "Religion",
    "found.material": "Resource",
    "found.place": "Place",
    "kind.land": "land",
    "kind.sea": "sea",
    "kind.lake": "lake",
    "kind.wasteland": "wasteland",
    "no_country": "none",
    "fact.country": "Country",
    "fact.culture": "Culture",
    "fact.religion": "Religion",
    "fact.material": "Resource",
    "fact.population": "Population",
    "fact.complexity": "Society",
    "summary": (
        "{countries} countries ({states} states, {tribes} tribes) · {cultures} cultures · "
        "{religions} religions · {locations} locations ({land} land)"
    ),
    "check": "Check",
    "check_tip": (
        "Make this world again and compare every file with the first time. Needs the game; "
        "takes as long as making a world."
    ),
    "custom_none": "none",
    "custom_some": "{count} changed",
    "place.in_game": "In the game: {path}",
    "place.kept": "Beside the generator, not in the game",
    "place.code_only": (
        "Not in the game. Adding it makes it again from its code (about {seconds} s)."
    ),
    "other_build": (
        "Made for game build {made}; you have {current}. Adding it makes it again for your "
        "build: the same code on another build is a world of its own."
    ),
    "other_build_same": (
        "Made for game build {made}; you have {current}, and none of the files it was made "
        "from has changed, so it works as it is."
    ),
    "standalone": (
        "This world is a complete mod: tick it in your playset to play it, on its own. "
        "Use Save world file to share its code and atlas."
    ),
    "add": "Add to the game",
    "remove": "Remove from the game",
    "select_all_worlds": "Select all",
    "selection_hint": "Ctrl-click to select several worlds; Shift-click to select a range.",
    "selection_count": "{count} selected · {installed} in the game",
    "remove_count": "Remove from game ({count})",
    "library_remove": "Remove ({count})",
    "remove_tip": "Remove the selected mods from EU5. Keep their world codes and pictures.",
    "remove_none": "Select an installed world first.",
    "remove_no_profile": "Choose the EU5 profile in Settings first.",
    "delete_count": "Delete from library ({count})…",
    "library_delete": "Delete ({count})…",
    "delete_tip": (
        "Delete the selected worlds from the library, with their saved maps, notes, kept mod "
        "files and installed mods."
    ),
    "delete_none": "Select a world in the library first.",
    "delete_many_title": "Delete {count} worlds?",
    "delete_many_question": (
        "Permanently delete these {count} worlds from the library and remove their installed "
        "mods from EU5? Their saved maps, notes and kept mod files will be deleted.\n\n{names}"
    ),
    "batch_delete_failed": "Could not delete “{name}” after deleting {done} worlds: {message}",
    "batch_removed": "Removed the selected mods from EU5. World codes and pictures are kept.",
    "batch_deleted": "The selected worlds were deleted.",
    "batch_cancelled": "Stopped. The list shows the changes already made.",
    "open_folder": "Open folder",
    "copy_code": "Copy code",
    "like_this": "New world with these settings",
    "delete": "Delete world",
    "delete_title": "Delete this world?",
    "delete_question": (
        "“{name}” is taken out of the game and out of the generator. Its world code can make "
        "it again."
    ),
    "task.add": "Adding to the game…",
    "task.remove": "Taking it out of the game…",
    "task.delete": "Deleting…",
    "task.check": "Checking…",
    "task_failed": "It did not work: {message}\n\n{report_hint}",
    "diagnostics": "Save diagnostics…",
    "diagnostics_tip": (
        "Pack the generator's logs and a report of this machine, the game and your worlds into one "
        "file for a bug report. Nothing is sent anywhere; your name and folders are blanked."
    ),
    "diagnostics_title": "Save diagnostics",
    "diagnostics_saved": (
        "Saved. Look through it if you like, and attach it to your report:\n{path}"
    ),
    "diagnostics_failed": "The file could not be written: {problem}",
    "stray_about": (
        "The generator could not recover this mod's library entry. It is in the game "
        "as {folder}. Its files have been left unchanged."
    ),
    # -- what to do in EU5 next --
    "tick_unknown": "Make sure only “{name}” is ticked among the RNW worlds in your playset.",
    "tick_self_untick": "Tick “{name}” and untick the other RNW worlds in your playset.",
    "tick_self": "Tick “{name}” in your playset.",
    "untick_others": "Untick the other RNW worlds in your playset.",
    "next_fresh": "In EU5: {tick} That reloads the mods. Then start a new 1337 game.",
    "next_fresh_switch": (
        "In EU5, switch to another playset and back to yours, which reloads the mods, then "
        "start a new 1337 game."
    ),
    "next_played": (
        "You have played in EU5 since you started it, and a different world started after "
        "that crashes the game. Close EU5 and start it again. {tick} Then start a new 1337 "
        "game."
    ),
    "next_start": "Start EU5. {tick} Then start a new 1337 game.",
    "next_unknown": (
        "{tick} Then, if no game was started since EU5 was launched, switch to another "
        "playset and back and start a new 1337 game; otherwise restart EU5 first."
    ),
    # -- the status bar --
    "resources": "{threads} threads, {free} GiB free memory",
    "resources_unknown": "{threads} threads",
    # -- the new lenses of the maps --
    "layer.population": "Population",
    "layer.population.tip": "How many people live in each location: dark is few, bright is many.",
    "layer.climate": "Climate",
    "layer.climate.tip": "The climate of each location, from arctic to tropical.",
    "layer.terrain": "Terrain",
    "layer.terrain.tip": "Flatland, hills, plateaus, mountains and wetlands.",
    "layer.areas": "Areas",
    "layer.areas.tip": "The areas the locations are grouped into; lines where one ends.",
    "found.area": "Area",
    "fact.area": "Area",
    "fact.terrain": "Land",
    # -- the Tauri window: its library --
    "library.filter": "Filter worlds",
    "library.all": "All",
    "library.in_game": "In the game",
    "library.empty": "No worlds yet. Make one, or open a world file.",
    "library.no_match": "No world matches.",
    "library.clear": "Clear",
    "library.no_game": "EU5 not found",
    "library.no_profile": "No EU5 profile",
    "copied": "Copied.",
    "shortcuts": "Keyboard shortcuts",
    "shortcut.new": "New world",
    "shortcut.open": "Open world file",
    "shortcut.generate": "Generate",
    "shortcut.settings": "Settings",
    "shortcut.paste": "Paste a world code anywhere",
    "shortcut.library": "Move through the library",
    "shortcut.lenses": "Map lenses",
    "shortcut.zoom": "Zoom in, out, fit the map",
    "shortcut.overlays": "Names and country borders on the map",
    "shortcut.clear": "Let go of a selection on the map",
    "settings.theme": "Appearance",
    "settings.theme.system": "System",
    "settings.theme.dark": "Dark",
    "settings.theme.light": "Light",
    "panes.library": "Show or hide the library",
    "panes.inspector": "Show or hide the side panel",
    # -- the Tauri window: a new world --
    "forge.drawn": "Drawn this time: {type}. A new seed draws again.",
    "dock.budget": "Locations",
    "dock.forging": "Making the world…",
    "dock.open_world": "Open the world",
    "candidates.use": "Use this continent",
    "candidates.chosen": "Chosen",
    # -- the Tauri window: a world --
    "stat.countries": "countries",
    "stat.split": "{states} states · {tribes} tribes",
    "stat.cultures": "cultures",
    "stat.religions": "religions",
    "stat.land": "land locations",
    "stat.locations": "{count} with seas and lakes",
    "world.terra_incognita": "Terra incognita",
    "world.versions_intro": (
        "A version keeps this continent and makes one part of it again. Versions stand under "
        "their world in the library."
    ),
    "world.like_tip": "Open a new world with this world's type and settings and a fresh seed.",
    "world.undo_tip": "Go back to the version this one was made from.",
    "compare.linked": "Move together",
    # -- the Tauri window: the maps --
    "map.loading": "Unrolling the atlas…",
    "map.political": "Country borders",
    "map.labels": "Names",
    "map.locations": "Location borders when zoomed in",
    "map.copy_view": "Copy this view as a picture",
    "map.copied": "The view is in the clipboard.",
    "map.focus": "Map only",
    "map.fit": "Fit the map",
    "map.zoom_in": "Zoom in",
    "map.zoom_out": "Zoom out",
    "map.minimap": "Overview: click to move there",
    "map.clear": "Clear",
    "map.no_results": "Nothing found.",
    "map.showing": "Showing {name}",
    "map.legend_hint": (
        "Click an entry to show only it, double-click to go there. Click a location to keep "
        "its card."
    ),
}


# Each official language by its own name, in the game's order of folders.
LANGUAGE_NAMES: Final[dict[str, str]] = {
    "braz_por": "Português (Brasil)",
    "english": "English",
    "french": "Français",
    "german": "Deutsch",
    "japanese": "日本語",
    "korean": "한국어",
    "polish": "Polski",
    "russian": "Русский",
    "simp_chinese": "简体中文",
    "spanish": "Español",
    "turkish": "Türkçe",
}
# The system's locales by their language code, for a window without a game to ask.
LOCALES: Final[dict[str, str]] = {
    "pt": "braz_por",
    "en": "english",
    "fr": "french",
    "de": "german",
    "ja": "japanese",
    "ko": "korean",
    "pl": "polish",
    "ru": "russian",
    "zh": "simp_chinese",
    "es": "spanish",
    "tr": "turkish",
}
# How each language groups the digits of a large number (30 871, 30.871, 30,871).
GROUPING: Final[dict[str, str]] = {
    "russian": "\u00a0",
    "french": "\u00a0",
    "polish": "\u00a0",
    "german": ".",
    "spanish": ".",
    "braz_por": ".",
    "turkish": ".",
}
STAGE: Final[str] = "stage."
ERROR: Final[str] = "error."
_language: list[str] = [SOURCE]


def sources() -> dict[str, str]:
    """Every English string of the window, by key: the sources of the ``window`` catalogs."""
    return {
        **STRINGS,
        **{STAGE + name: info.label for name, info in STAGES.items()},
        **{ERROR + key: english for key, english in MESSAGES.items()},
    }


def system_language() -> str | None:
    """The official language of the system's locale, or None."""
    code = (locale.getlocale()[0] or "").replace("-", "_").split("_")[0].lower()
    return LOCALES.get(code)


def choose_language(chosen: str, game: str | None, system: str | None) -> str:
    """The player's choice, else the game's, else the system's, else English; one with a
    catalog only (the window cannot speak a language it has no table for)."""
    for language in (chosen, game, system):
        if language and translations.has_catalog(translations.WINDOW, language):
            return language
    return SOURCE


def set_language(language: str) -> None:
    """Speak ``language`` from now on (before the window is built)."""
    _language[0] = language if translations.has_catalog(translations.WINDOW, language) else SOURCE


def language() -> str:
    """The language the window speaks."""
    return _language[0]


@cache
def _table(language: str) -> dict[str, str]:
    return translations.translate(translations.WINDOW, language, sources())


def table() -> dict[str, str]:
    """Every string of the window in its language, by key (for a window drawn elsewhere)."""
    return dict(_table(_language[0]))


def text(key: str, **values: object) -> str:
    """The string for ``key`` in the window's language, with ``{name}`` fields filled in."""
    return _table(_language[0])[key].format(**values)


def explain(error: BaseException) -> str:
    """What went wrong, for the player: a message of the generator in the window's language; a
    damaged world file or settings with a translated lead and the English detail; anything else as
    it reads (it goes to a bug report)."""
    said = error.args[0] if error.args else None
    if isinstance(said, Said):
        return text(ERROR + said.key, **said.values)
    if isinstance(error, WorldFileError):
        return text("error_world_file", detail=str(error))
    if isinstance(error, SettingsError):
        return text("error_settings", detail=str(error))
    return str(error) or type(error).__name__


def grouped(value: int) -> str:
    """A whole number with its digits grouped as the window's language groups them."""
    return f"{value:,}".replace(",", GROUPING.get(_language[0], ","))


def stage_text(name: str) -> str:
    """What the window calls a stage of the export."""
    return _table(_language[0]).get(STAGE + name, name)
