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
    "next_steps": (
        "Now close EU5 and start it again, with the generated world enabled in your playset, "
        "and start a new 1337 game. EU5 can crash if a different world is started without a "
        "restart."
    ),
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
