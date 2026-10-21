"""Every string the window shows, in one place so a translation is one more table."""

from __future__ import annotations

from typing import Final

TITLE: Final[str] = "Random New World"
GAME: Final[str] = "Europa Universalis V"
STRINGS: Final[dict[str, str]] = {
    "game": "Game",
    "profile": "Profile",
    "browse": "Browse…",
    "build": "Steam build {build}",
    "game_missing": "EU5 was not found. Choose its folder (the one that holds game/in_game).",
    "profile_missing": (
        "No EU5 profile was found. Start the game once so it creates one, or choose its "
        "folder (the one that holds mod/)."
    ),
    "not_a_game": "That folder is not an EU5 installation (game/in_game/map_data is missing).",
    "not_a_profile": "That folder does not exist.",
    "world": "World",
    "preset": "Preset",
    "preset.continents": "Continents",
    "preset.archipelago": "Archipelago",
    "seed": "Seed",
    "random": "Random",
    "code": "World code",
    "copy": "Copy",
    "paste": "Paste",
    "code_hint": "Paste a world code to get the same world. Same version, same world.",
    "other_version": (
        "This code was made by generator {made}; this is {current}. The world can differ."
    ),
    "bad_seed": "A seed is a whole number from 0 to 18446744073709551615.",
    "install": "Install into my profile when it is done",
    "generate": "Generate",
    "cancel": "Cancel",
    "cancelling": "Cancelling…",
    "progress": "Progress",
    "idle": "Ready.",
    "running": "Working: {stages}",
    "finished": "Done in {seconds} s.",
    "failed": "It did not work: {message}",
    "cancelled": "Cancelled. Nothing was changed in your game.",
    "history": "Worlds you made",
    "use_code": "Use this code",
    "outcome.installed": "installed",
    "outcome.generated": "generated",
    "outcome.failed": "failed",
    "outcome.cancelled": "cancelled",
    "result_installed": "Installed to {path}.",
    "result_generated": "Made in {path}. Nothing was installed.",
    "next_fresh": (
        "In EU5, switch to another playset and back to yours, which reloads the mods, then "
        "start a new 1337 game."
    ),
    "next_fresh_tick": (
        "In EU5, tick the generated world (RNW New World …) in your playset, which reloads "
        "the mods, then start a new 1337 game."
    ),
    "next_played": (
        "You have played in EU5 since you started it, and a different world started after "
        "that crashes the game: close EU5, start it again and begin a new 1337 game."
    ),
    "next_start": "Start EU5 and begin a new 1337 game.",
    "next_unknown": (
        "If EU5 is running and no game was started since you launched it, switch to another "
        "playset and back, then start a new 1337 game; otherwise restart EU5 first."
    ),
    "next_tick": "Tick the generated world (RNW New World …) in your playset.",
    "next_check_tick": "Make sure the generated world (RNW New World …) is ticked in your playset.",
    "open_folder": "Open folder",
    "preview": "Preview",
    "ready_no_game": "Choose the game folder first.",
    "ready_no_profile": "Choose a profile to install into, or turn installing off.",
    "ready_busy": "A world is being made.",
    "resources": "{threads} threads, {free} GiB free memory",
    "resources_unknown": "{threads} threads",
}


def text(key: str, **values: object) -> str:
    """The string for ``key``, with ``{name}`` fields filled in."""
    return STRINGS[key].format(**values)
