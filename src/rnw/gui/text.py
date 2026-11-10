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

from rnw import history_presenter, translations
from rnw.languages import SOURCE
from rnw.messages import MESSAGES, Said
from rnw.progress import STAGES
from rnw.settings import SettingsError
from rnw.worldfile import WorldFileError

TITLE: Final[str] = "Random New World"
GAME: Final[str] = "Europa Universalis V"
STRINGS: Final[dict[str, str]] = {
    "control.natives.turbulence_permille": "Historical turbulence",
    "control.natives.turbulence_permille.about": (
        "How often conflict and political change occur during "
        "the three centuries before the campaign."
    ),
    "quick.turbulence": "Historical turbulence",
    "quick.turbulence.about": "Conflict and political change before 1337.",
    "quick.turbulence.calm": "Calm",
    "quick.turbulence.varied": "Varied",
    "quick.turbulence.turbulent": "Turbulent",
    "undo_roll": "Undo roll",
    "task.undo": "Restoring the previous version",
    "task.reroll": "Making a new version…",
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
        "Pick one to use its seed and settings, or add the ones you like to the queue. "
        "A final coastline can shift slightly as locations are formed."
    ),
    "candidate_item": "{number} · {land:g}% land\nSeed {seed}",
    "enqueue": "Add to queue",
    "run_queue": "Run queue",
    "clear_queue": "Clear queue",
    "queue_empty": "Add a world to the queue first.",
    "queue_count": "{count} pending",
    "queue_added": "Added to the queue: seed {seed}.",
    "queue_duplicate": "This world is already in the queue or being made.",
    "queue_follows": "The queue starts by itself when the world being made is done.",
    "queue_remove": "Remove from the queue",
    "queue_making": "Being made now",
    "queue_failed_count": "{count} could not be made",
    "queue_failed_hint": (
        "A world that could not be made stays in the queue with its error, and the next one "
        "starts. Run the queue to try it again, or remove it."
    ),
    "queue_all_failed": "None of the {count} worlds could be made. The last error: {message}",
    "finished_queue_failed": (
        "Done in {seconds} s. {count} could not be made; they stay in the queue with their errors."
    ),
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
        "world. While a world is being made you can prepare and add the next ones: the queue "
        "goes on by itself. Otherwise, run the queue when you have added everything."
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
    # The box is "covered" where the stored preference (`show_new_world`) says "shown": checked
    # means the New World is hidden, which is the default.
    "lobby_cover": "Terra Incognita in the lobby",
    "lobby_cover_about": "Hides the New World before you play",
    "lobby_cover_hint": (
        "Covers the New World as terra incognita on the country-selection map and in this "
        "world's pictures, so that you do not see it before you play. Unchecked, the New World "
        "is shown there. You can change this later on the world's page without generating it "
        "again."
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
    "about_workshop": "Steam Workshop",
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
    "control.new_world.wall_allow_gaps": ("Allow gaps in the wall"),
    "control.new_world.wall_allow_gaps.about": (
        "Let the density field form islands and sea passages. Disable to require a "
        "continuous land core. Land amount, scale and coastal irregularity shape the "
        "result."
    ),
    "type.wall": "The Wall",
    "type.wall.about": (
        "A straight north-south continent with a mountain spine and side land. Procedural "
        "shores may form islands and narrow straits when gaps are allowed."
    ),
    "group.wall": "The Wall",
    "control.new_world.wall_width_permille": "Wall width",
    "control.new_world.wall_width_permille.about": (
        "Maximum width as a share of the canvas. The Wall takes its land out of the Land amount "
        "first, so a wider Wall leaves less for the continents beside it, down to a few islands."
    ),
    "control.new_world.wall_position_permille": "Wall position",
    "control.new_world.wall_position_permille.about": (
        "Position from west to east. The Wall goes around protected islands in its way."
    ),
    "control.new_world.wall_coast_permille": "Coastal irregularity",
    "control.new_world.wall_coast_permille.about": (
        "Strength of bays, islands and coastal variation within the straight continental envelope."
    ),
    "control.new_world.wall_ridge_permille": "Mountain spine",
    "control.new_world.wall_ridge_permille.about": "Height of the longitudinal mountain chain.",
    "type.omerika": "Omerika",
    "type.omerika.about": (
        "A familiar New World, reimagined. Same general shape, entirely different geography."
    ),
    "group.omerika": "Omerika",
    "control.new_world.template_permille": "Likeness to the Americas",
    "control.new_world.template_permille.about": (
        "How closely the land follows the layout of the real Americas, North and South America "
        "joined by an isthmus. A low value leaves a loose echo; a high one keeps the places and "
        "sizes of the continents. Coasts, seas, mountains and rivers are new at any value."
    ),
    "type.islands": "Scattered islands",
    "type.islands.about": "A sea full of small islands, with no great landmass.",
    "type.random": "Random",
    "type.random.about": (
        "One of the world types, drawn at random when chosen and at each press of Random. "
        "The Advanced values are those of the type drawn."
    ),
    "type.chaos": "Total Chaos",
    "randomize_settings": "Randomize settings again",
    "randomize_settings.about": "Draw a new world type and Advanced settings, keeping the seed.",
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
        "Chance of an extraordinary trajectory around each cultural hearth. History determines "
        "whether a great empire, sea league, highland confederation, divided realm or sacred "
        "centre takes shape and survives until 1337."
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
        "black for sea, in the proportions of the New World's area. Colours mark the ground: "
        "brown for mountains, gold for highlands, light green for lowlands and blue for lakes. "
        "The rest is generated on it."
    ),
    "land_template": "Save template…",
    "land_template_tip": (
        "Write a picture of the area the New World can fill, from your game's map, to draw "
        "your land on in any program: paint land white, or in the ground colours of Land from "
        "an image. The lighter grey is the game's Americas and the darker grey the Old World's "
        "island groups."
    ),
    "task.template": "Drawing the template…",
    "land_image_chosen": "The land is drawn in an image ({id}).",
    "land_image_clear": "Back to generated land",
    "land_image_title": "Choose the land image",
    "land_image_files": "Pictures (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
    "editor.open": "Draw land…",
    "editor.open_tip": (
        "Draw the land of the new world in the editor: start from a ready land, paint sea, land, "
        "mountains, highlands, lowlands and lakes, and see what the generator will make of it."
    ),
    "editor.edit": "Edit in the editor",
    "editor.title": "Land editor",
    "editor.preparing": "Cutting the area from the game's map…",
    "editor.preparing_hint": (
        "The first time takes several seconds; the area is kept for the next time."
    ),
    "editor.loading": "Opening the sheet…",
    "editor.failed": "The area could not be cut.",
    "editor.close": "Close",
    "editor.cancel": "Cancel",
    "editor.use": "Use this land",
    "editor.use_tip": "Build the new world on this drawing.",
    "editor.use_blocked": (
        "The generator cannot make a world of this drawing yet; see what it says on the right."
    ),
    "editor.used": "The new world will be built on your land.",
    "editor.undo": "Undo",
    "editor.redo": "Redo",
    "editor.zoom_in": "Zoom in",
    "editor.zoom_out": "Zoom out",
    "editor.zoom_fit": "Show the whole sheet",
    "editor.zoom_100": "Actual size",
    "editor.layer.drawing": "Show your drawing",
    "editor.layer.americas": "Show the game's Americas",
    "editor.layer.islands": "Show the Old World's island groups",
    "editor.layer.margin": "Show the coast margin: land drawn in the hatched band is dropped",
    "editor.tools": "Tools",
    "editor.tool.brush": "Brush",
    "editor.tool.eraser": "Eraser (paints sea)",
    "editor.tool.fill": "Fill",
    "editor.tool.line": "Line",
    "editor.tool.rectangle": "Rectangle",
    "editor.tool.ellipse": "Ellipse",
    "editor.tool.pan": "Move the view (or hold Space)",
    "editor.kinds": "What to paint",
    "editor.kind.sea": "Sea",
    "editor.kind.land": "Land",
    "editor.kind.mountains": "Mountains",
    "editor.kind.highlands": "Highlands",
    "editor.kind.lowlands": "Lowlands",
    "editor.kind.lake": "Lake",
    "editor.kind.sea.tip": "Open water; the eraser paints it too",
    "editor.kind.land.tip": "Plain land: the generator chooses its relief",
    "editor.kind.mountains.tip": "Mountains: a range or high peaks rise here",
    "editor.kind.highlands.tip": "Highlands: hills and plateaus",
    "editor.kind.lowlands.tip": "Lowlands: flat plains and valleys",
    "editor.kind.lake.tip": "A lake: water that land encloses",
    "editor.size": "Size",
    "editor.on_ground": "Terrain on land only",
    "editor.on_ground_tip": (
        "Mountains, highlands and lowlands are painted on land only, never on sea or lakes."
    ),
    "editor.filled": "Filled shapes",
    "editor.hint": "Paint land with the brush, or start from a ready land on the right.",
    "editor.start": "Start from",
    "editor.reroll": "Roll again",
    "editor.reroll_tip": "Another shape for each ready land",
    "editor.preset.supercontinent": "Supercontinent",
    "editor.preset.two_continents": "Two continents",
    "editor.preset.three_continents": "Three continents",
    "editor.preset.archipelago": "Archipelago",
    "editor.preset.island_chain": "Island chain",
    "editor.preset.ring": "Ring",
    "editor.preset.crescent": "Crescent",
    "editor.preset.scattered": "Scattered islands",
    "editor.americas": "The game's Americas",
    "editor.sketch": "Sketch {number}",
    "editor.decorate": "Add terrain",
    "editor.decorate_tip": (
        "Adds mountain chains, highlands, lowlands and lakes to plain land. What you painted stays."
    ),
    "editor.add.mountains": "Mountain chains",
    "editor.add.highlands": "Highlands",
    "editor.add.lowlands": "Lowlands",
    "editor.add.lakes": "Lakes",
    "editor.decorate_run": "Add to the land",
    "editor.nothing_added": "Nothing was added: there is no plain land to add to.",
    "editor.check": "What the generator will do",
    "editor.checking": "Checking…",
    "editor.check.land": "Land is {share} % of the sheet.",
    "editor.check.share": (
        "Land is {share} % of the sheet; a world needs between {low} % and {high} %."
    ),
    "editor.check.outside_all": (
        "Almost all of the land lies outside the area or on its coast margin ({kept} % is left). "
        "Draw inside the lighter area, away from the hatched band."
    ),
    "editor.check.lake_open": (
        "Lakes that open to the sea: {count} (ringed on the sheet). A lake is water that land "
        "encloses: leave a strip of land between it and the sea, or paint it as sea."
    ),
    "editor.check.dropped": (
        "{dropped} % of the land lies outside the area or on its coast margin and will be dropped."
    ),
    "editor.check.specks": (
        "Pieces of land smaller than the smallest island, which will be removed: {count}."
    ),
    "editor.check.islands": (
        "Island groups of the Old World that the land reaches: {count}. Each moves, as one "
        "piece, to the nearest open sea."
    ),
    "editor.picture": "Picture",
    "editor.import": "Import a picture…",
    "editor.export": "Save the drawing…",
    "editor.clear": "Clear the sheet",
    "editor.fit.stretched": "The picture was stretched to the sheet.",
    "editor.fit.centered": (
        "The picture has other proportions than the sheet; it was centered on it."
    ),
    "editor.keys": (
        "B brush · E eraser · G fill · 1–6 kinds · [ ] size · right button takes a kind · "
        "Space moves"
    ),
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
    "group.resources": "Resources",
    "group.resources.about": (
        "Relative placement weights: 1× uses vanilla frequencies; 0 removes a resource. "
        "Climate and terrain still guide placement. More of one resource leaves fewer "
        "locations for others; production per location is unchanged. Generation stops if "
        "no enabled resource suits a location."
    ),
    "control.new_world.land_permille": "Land",
    "control.new_world.expand_oceans": "Expand generation into the oceans",
    "control.new_world.expand_oceans.about": "Recommended",
    "control.new_world.expand_oceans.info": (
        "Gives the New World more room, so its continents need not follow the outline of "
        "the Americas. The Old World is kept; islands in the way stay or move to free water."
        "\n\n"
        "If the land crowds the Old World's shores, do not uncheck this: raise “Distance from "
        "the Old World” in Advanced (Land and sea) instead. It moves the land toward the "
        "middle of the ocean without changing how much land there is, and the continents stay "
        "free to take any shape. Unchecking confines the New World to the original band "
        "around the Americas."
    ),
    "part.resources.real": (
        "A world that keeps the real Americas has the game's own resources: there are none to "
        "make again."
    ),
    "control.new_world.keep_geography": "Keep the real Americas",
    "control.new_world.keep_geography.about": "Peoples only",
    "control.new_world.keep_geography.info": (
        "The Americas stay exactly as the game draws them: no land, coast, relief, river or "
        "place is generated or changed. Only their peoples are generated: states, cultures, "
        "religions, history, laws and the rest of the society of 1337. The land, ocean, map and "
        "resource settings do not apply, and the New World is not covered in the lobby."
    ),
    "control.new_world.reveal_at_start": "Reveal the New World at the start",
    "control.new_world.reveal_at_start.about": "For multiplayer",
    "control.new_world.reveal_at_start.info": (
        "At the start of a campaign the country of every player discovers every area of this "
        "New World, land and sea, so that every player sees it from the first day. Countries "
        "run by the computer are not given it: they find the New World by exploring, as in the "
        "game. Off by default: the New World then waits to be discovered by everyone. The "
        "game's own event that announces the discovery of the New World does not fire, because "
        "the discovery is already made."
    ),
    "control.new_world.land_permille.about": "How much of the New World is land.",
    "control.new_world.centre_permille": "Distance from the Old World",
    "control.new_world.centre_permille.about": (
        "Higher: continents lie nearer the middle of the ocean, farther from the Old World's "
        "shores. The amount of land does not change. The Wall ignores it."
    ),
    "control.new_world.feature_px": "Size of landmasses",
    "control.new_world.feature_px.about": ("Large: a few great landmasses. Small: many islands."),
    "control.new_world.min_island_px": "Smallest island",
    "control.new_world.min_island_px.about": "Islands smaller than this sink.",
    "control.new_world.persistence_permille": "Rough coasts",
    "control.new_world.persistence_permille.about": ("Higher: more jagged coasts and more islets."),
    "control.new_world.octaves": "Coast detail",
    "control.new_world.octaves.about": "Layers of detail in the coastline.",
    "control.new_world.max_lake_px": "Largest lake",
    "control.new_world.max_lake_px.about": (
        "Lakes up to about this size are drawn. Large enclosed basins can form inland seas."
    ),
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
    "control.natives.peasant_peak_permille": "Peasant share",
    "control.natives.peasant_peak_permille.about": (
        "Upper limit for the peasant share of each inhabited location, reached only at full "
        "social complexity. Applies to all inhabited land, including land outside states. "
        "Less complex or poor-farming locations remain more tribal. Total population and the "
        "vanilla farming threshold for landed states do not change."
    ),
    "control.natives.state_share_permille": "Land in states",
    "control.natives.state_share_permille.about": (
        "Target share of inhabited land for native states (vanilla: 11 %). "
        "Actual coverage may be lower where farming and population do not support states."
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
        "Chance of an extraordinary trajectory around each cultural hearth. History determines "
        "whether a great empire, sea league, highland confederation, divided realm or sacred "
        "centre takes shape and survives until 1337."
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
    "legend.not_recorded": "Not recorded in this world",
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
    "card.rule": "Counts as {region} in the game's rules",
    "card.rule_tip": (
        "The base game's events, advances and AI goals for {region} apply here. The world gives "
        "the region a name of its own."
    ),
    "fact.country": "Country",
    "fact.culture": "Culture",
    "fact.religion": "Religion",
    "fact.material": "Resource",
    "fact.population": "Population",
    "fact.development": "Development",
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
    "other_build_checking": (
        "Made for game build {made}; you have {current}. Comparing the files it was made from "
        "with the game's…"
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
    "playset_replaced": (
        "“{mod}” comes after this world in your playset and has files at the same paths as "
        "the world's, such as {files}. EU5 then reads that mod's files instead of the "
        "world's, and the New World can come out with Clay everywhere and empty map modes. "
        "Put “{mod}” before this world in the load order, or untick it."
    ),
    "playset_worlds": (
        "More than one RNW world is ticked in your playset (also {names}). Their files "
        "overwrite one another, so the New World can come out wrong, for example with Clay "
        "everywhere and empty map modes."
    ),
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
    "settings.classic_window": "Use the classic window",
    "settings.classic_window.about": (
        "From the next start. The classic window also opens by itself when this new one cannot."
    ),
    "panes.library": "Show or hide the library",
    "panes.inspector": "Show or hide the side panel",
    # -- the Tauri window: a new world --
    "forge.drawn": "Drawn this time: {type}. A new seed draws again.",
    "dock.budget": "Locations",
    "dock.forging": "Making the world…",
    "dock.open_world": "Open the world",
    "candidates.use": "Use this continent",
    "candidates.chosen": "Chosen",
    "candidates.queued": "In the queue",
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
    "map.tribes": "Tribes",
    "map.show_tribes": "Show tribes",
    "map.show_tribes_tip": (
        "Tribes are countries too, but the game's political map leaves them uncoloured; so does "
        "this map unless this is ticked."
    ),
}
RESOURCE_NAMES: Final[dict[str, str]] = {
    "alum": "Alum",
    "amber": "Amber",
    "beeswax": "Beeswax",
    "chili": "Chili",
    "clay": "Clay",
    "coal": "Coal",
    "cocoa": "Cocoa",
    "copper": "Copper",
    "cotton": "Cotton",
    "dyes": "Dyes",
    "fiber_crops": "Fiber crops",
    "fish": "Fish",
    "fruit": "Fruit",
    "fur": "Fur",
    "incense": "Incense",
    "iron": "Iron",
    "ivory": "Ivory",
    "lead": "Lead",
    "legumes": "Legumes",
    "livestock": "Livestock",
    "lumber": "Lumber",
    "maize": "Maize",
    "marble": "Marble",
    "medicaments": "Medicaments",
    "mercury": "Mercury",
    "potato": "Potatoes",
    "salt": "Salt",
    "saltpeter": "Saltpeter",
    "sand": "Sand",
    "stone": "Stone",
    "tin": "Tin",
    "tobacco": "Tobacco",
    "wild_game": "Wild game",
    "wool": "Wool",
}
for _resource, _label in RESOURCE_NAMES.items():
    STRINGS[f"control.resources.{_resource}"] = _label
    STRINGS[f"control.resources.{_resource}.about"] = (
        "Relative placement weight against vanilla. 0 removes this resource."
    )


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
        **history_presenter.SOURCES,
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
