"""Every string the window shows, in one place so a translation is one more table."""

from __future__ import annotations

from typing import Final

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
    "generation_install": "The finished mod will be added to your EU5 profile.",
    "generation_keep": "The finished world will stay in your library.",
    "generation_copy": "The finished mod will be copied to the selected folder.",
    "generation_file": "The world file will be saved to the selected destination.",
    "visibility": "Before you play",
    "world_visibility_hint": (
        "Applies to this world only. Updates its mod picture and country-selection map "
        "without generating it again. Restart EU5 to read the change."
    ),
    "visibility_updated": "This world's visibility was updated. Restart EU5 to read the change.",
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
    # -- the list of worlds --
    "worlds": "Worlds",
    "new_world": "New world",
    "new_world_running": "New world · {percent} %",
    "world_line": "{when} · {place}",
    "list.in_game": "in the game",
    "list.kept": "not in the game",
    "list.code_only": "code only",
    "stray_name": "Older world",
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
    "quick.empires": "Great empires",
    "quick.empires.about": (
        "How likely a great native empire is to rise around each centre of culture, as the "
        "fantasy setting of EU4's random New World: one state many times the size of the "
        "others, with an advanced government."
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
    "control.natives.empire_permille": "Great empires",
    "control.natives.empire_permille.about": (
        "Chance, for each cultural hearth, that a great empire rises around it: one state "
        "many times the size of the others, with an advanced government."
    ),
    "control.natives.state_locations": "State size",
    "control.natives.state_locations.about": "Locations of a native state, on average.",
    "unit.percent": " %",
    "unit.times": " ×",  # noqa: RUF001 - the multiplication sign is meant
    "unit.px": " px",
    "unit.": "",
    "install": "Add to the game when it is done",
    "generate": "Generate",
    "cancel": "Cancel",
    "cancelling": "Cancelling…",
    "progress": "Progress",
    "idle": "Ready.",
    "running": "Working: {stages}",
    "finished": "Done in {seconds} s.",
    "failed": "It did not work: {message}\n\n{report_hint}",
    "report_hint": "To report it, open Settings and press Save diagnostics.",
    "cancelled": "Cancelled. Nothing was changed in your game.",
    "ready_no_game": "Choose the game folder in Settings first.",
    "ready_no_profile": "Choose a profile in Settings, or turn adding to the game off.",
    "ready_busy": "The generator is busy.",
    "too_many_locations": (
        "This world would have about {count} locations; EU5 takes about 32,000, and the "
        "generator keeps below {budget}. Raise the location or sea zone size, or lower the land."
    ),
    "outside_range": "This code sets values beyond what the generator allows: {names}.",
    "estimate": "About {count} locations (EU5 takes about 32,000).",
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
        "Made before worlds kept a record of how they were made, so it may not come out the same."
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
    "no_atlas": "This world has no atlas: it was made before atlases, or its files are gone.",
    "facts_hint": "Move over the map to see what lies there.",
    "search_hint": "Find a country, culture, religion, resource or place",
    "legend": "Legend",
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
        "This world was made by an earlier version of the generator, which kept no record "
        "of it. It is in the game as {folder}. Remove it when you no longer play it."
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
}


def text(key: str, **values: object) -> str:
    """The string for ``key``, with ``{name}`` fields filled in."""
    return STRINGS[key].format(**values)
