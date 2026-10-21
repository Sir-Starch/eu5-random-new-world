"""Every string the window shows, in one place so a translation is one more table."""

from __future__ import annotations

from typing import Final

TITLE: Final[str] = "Random New World"
GAME: Final[str] = "Europa Universalis V"
STRINGS: Final[dict[str, str]] = {
    # -- the game, the profile and the settings dialog --
    "game": "Game",
    "profile": "Profile",
    "browse": "Browse…",
    "settings": "Settings…",
    "settings_title": "Settings",
    "close": "Close",
    "game_line": "EU5 build {build} · {game}",
    "game_line_unknown": "EU5 · {game}",
    "profile_line": "Profile · {profile}",
    "game_missing": "EU5 was not found. Open Settings and choose its folder.",
    "profile_missing": (
        "No EU5 profile was found. Start the game once so it creates one, or choose its "
        "folder in Settings."
    ),
    "not_a_game": "That folder is not an EU5 installation (game/in_game/map_data is missing).",
    "not_a_profile": "That folder does not exist.",
    "reveal_thumbnails": "Show the New World in the pictures of the game's mod list",
    "reveal_thumbnails_hint": (
        "Off: the pictures show the New World as terra incognita, so nothing of a world is "
        "given away before you play it."
    ),
    "about_generator": (
        "Random New World makes New World maps for EU5. Every world it makes is a complete "
        "mod of its own: tick it in your playset to play it, or share it. This generator "
        "does not need to be enabled."
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
    "default_name": "{type} #{seed}",
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
    "seed": "Seed",
    "random": "Random",
    "code": "World code",
    "copy": "Copy",
    "paste": "Paste",
    "code_hint": "Paste a world code to get the same world. Same version, same world.",
    "other_version": (
        "This code was made by generator {made}; this is {current}. The world can differ."
    ),
    "other_changes": "This code also changes settings the window does not show; they are kept.",
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
    "failed": "It did not work: {message}",
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
    "name_hint": "Name of this world",
    "preview_hidden": "The New World is hidden as terra incognita.",
    "preview_shown": "The New World is shown.",
    "preview_missing": "This world has no picture.",
    "zoom_hint": "Scroll to zoom, drag to move, double-click to fit.",
    "show_world": "Show the New World",
    "hide_world": "Hide the New World",
    "detail.code": "World code",
    "detail.type": "World type",
    "detail.seed": "Seed",
    "detail.custom": "Custom settings",
    "detail.made": "Made",
    "detail.build": "Game build",
    "detail.generator": "Generator",
    "detail.place": "Where",
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
    "standalone": (
        "This world is a complete mod: tick it in your playset to play it, on its own. You "
        "can share its folder, for example as your own map on the Steam Workshop."
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
    "task_failed": "It did not work: {message}",
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
