"""The hook probes of N2: what a mod can ask of the engine before the content stages rely on it.

The content plan (N3, N4) builds stories, formables and colonial names out of hooks the game
may or may not give a mod: a tag that no country file defines (the pattern of the vanilla
formable-only tag ``ADU``, C175), a scripted country name of the mod's own (C180), variables set
for a country and a location at the start of a game, the Russian forms of a tag without any
(C176) and the vanilla titles of such a tag. This module writes one small mod,
``rnw_exp_probe_hooks``, that asks for each of them on the vanilla map, so the owner can see what
the game does. It is a research tool: its texts are English and it is never part of a world.

Every vanilla anchor the probe leans on is checked against the installation first, and a
missing one stops the build (``anchor_problems``); nothing is guessed.

The probe makes the formable ``rnw_probe_f`` for the tag ``ZQP`` available to Bern (``BRN``),
a county of two locations, a scripted name for the subject made from Interlaken, two variables
set when a game starts, and decisions that found the subject and read the variables back. It
also runs the start of a story in miniature (H7): a hidden event with a dynamic historical window
that is certain to open in the first months, a variable that holds a location, and a delayed
event, so the owner sees in a few game months what a story needs decades to show.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Final

from rnw.geography import read_locations
from rnw.languages import official_languages
from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from pathlib import Path

NAME: Final[str] = "rnw_exp_probe_hooks"
TAG: Final[str] = "ZQP"
HOST: Final[str] = "BRN"
CAPITAL: Final[str] = "bern"
COLONY: Final[str] = "interlaken"
FORMABLE: Final[str] = "rnw_probe_f"
SCRIPTED_NAME: Final[str] = "rnw_probe_colony_scripted_country_name"
VARIABLE: Final[str] = "rnw_probe_start"
START_ACTION: Final[str] = "rnw_probe_game_start"
CENTRE: Final[str] = "rnw_probe_centre"
COUNTRY_VARIABLE: Final[tuple[str, str, int]] = ("FRA", VARIABLE, 7)
LOCATION_VARIABLE: Final[tuple[str, str, int]] = ("paris", VARIABLE, 3)
GAME: Final[str] = "game"
FORMABLE_README: Final[str] = f"{GAME}/in_game/common/formable_countries/readme.txt"
FORMABLE_KEYS: Final[tuple[str, ...]] = (
    "level",
    "required_locations_fraction",
    "rule",
    "potential",
    "allow",
    "form_effect",
    "name",
    "flag",
    "adjective",
    "tag",
    "color",
    "locations",
)


class ProbeError(ValueError):
    """The installation lacks something the probe leans on."""


def _read(game_dir: Path, relative: str) -> str:
    return (game_dir / GAME / relative).read_text(encoding="utf-8-sig")


def _anywhere(game_dir: Path, word: str) -> list[str]:
    """Script and localization files of the installation that contain ``word``."""
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(word)}(?![A-Za-z0-9_])")
    found: list[str] = []
    for root in ("in_game", "main_menu"):
        for path in (game_dir / GAME / root).rglob("*"):
            if path.suffix in {".txt", ".yml"} and path.is_file():
                try:
                    text = path.read_text(encoding="utf-8-sig")
                except UnicodeDecodeError:
                    continue
                if pattern.search(text):
                    found.append(path.relative_to(game_dir).as_posix())
    return found


def anchor_problems(game_dir: Path) -> list[str]:
    """Why the probe cannot be built on this installation; empty when every anchor holds."""
    problems: list[str] = []
    if clash := _anywhere(game_dir, TAG):
        problems.append(f"the tag {TAG} is already used by the game: {clash[0]}")
    if undocumented := [
        key
        for key in FORMABLE_KEYS
        if key not in (game_dir / FORMABLE_README).read_text("utf-8-sig")
    ]:
        problems.append(f"the formable readme no longer documents: {', '.join(undocumented)}")
    countries = parse(_read(game_dir, "main_menu/setup/1337/10_countries.txt")).block(
        "countries", "countries"
    )
    host = None if countries is None else countries.block(HOST)
    core = None if host is None else host.block("own_control_core")
    owned = (
        {word.value for word in core.words() if isinstance(word.value, str)}
        if core is not None
        else set[str]()
    )
    if not {CAPITAL, COLONY} <= owned:
        problems.append(f"{HOST} no longer starts with {CAPITAL} and {COLONY}")
    rank = None if host is None else host.first("country_rank")
    if rank is None or rank.value != "rank_county":
        problems.append(f"{HOST} is no longer a county, so a level 3 formable may not be formable")
    vanilla = {
        "main_menu/common/coat_of_arms/coat_of_arms/pre_scripted_countries.txt": (
            '"pattern_solid.dds"',
            '"ce_checky_15_points.dds"',
        ),
        "in_game/common/on_action/_hardcoded.txt": ("on_game_start = {",),
        "in_game/common/on_action/country_yearly.txt": (
            "yearly_country_pulse = {",
            "on_actions = {",
        ),
        "in_game/common/decisions/canal_construction.txt": (
            "decision_category = infrastructure_decisions",
            "ai_will_do",
        ),
        "in_game/common/subject_types/vassal.txt": ("vassal",),
    }
    for relative, needles in vanilla.items():
        text = _read(game_dir, relative) if (game_dir / GAME / relative).is_file() else ""
        problems.extend(
            f"{relative} no longer holds {needle}" for needle in needles if needle not in text
        )
    effects = "".join(
        path.read_text("utf-8-sig")
        for path in sorted((game_dir / GAME / "in_game/common/scripted_effects").glob("*.txt"))
    )
    problems.extend(
        f"no scripted effect uses {needle} any more"
        for needle in ("create_country_from_location", "make_subject_of", "set_capital")
        if needle not in effects
    )
    return problems


def _area_of(game_dir: Path, location: str) -> str:
    for item in read_locations(game_dir / GAME / "in_game/map_data/definitions.txt"):
        if item.key == location:
            return item.area
    message = f"{location} is not in the installation"
    raise ProbeError(message)


def _formable() -> str:
    return f"""{FORMABLE} = {{
	level = 3
	required_locations_fraction = 1
	rule = plausible

	potential = {{
		tag = {HOST}
	}}

	allow = {{
	}}

	name = {TAG}
	flag = {TAG}
	adjective = {TAG}_ADJ
	tag = {TAG}
	color = map_{TAG}

	locations = {{
		{CAPITAL}
		{COLONY}
	}}
	form_effect = {{
	}}
}}
"""


def _scripted_name(area: str) -> str:
    return f"""{SCRIPTED_NAME} = {{
	country_trigger = {{
		overlord ?= {{
			OR = {{
				tag = {HOST}
				tag = {TAG}
			}}
		}}
	}}

	capital_trigger = {{
		area = area:{area}
	}}

	location_trigger = {{
	}}
}}
"""


def _decisions() -> str:
    return f"""rnw_probe_found_colony = {{
	decision_category = infrastructure_decisions

	potential = {{
		OR = {{
			tag = {HOST}
			tag = {TAG}
		}}
	}}

	allow = {{
		owns = location:{COLONY}
	}}

	ai_will_do = {{
		value = -1
	}}

	option = {{
		name = rnw_probe_found_colony.a
		ai_chance = {{ value = 0 }}
		effect = {{
			location:{COLONY} = {{
				create_country_from_location = {{
					save_scope_as = rnw_probe_colony
					set_capital = location:{COLONY}
					make_subject_of = {{
						target = root
						type = subject_type:vassal
					}}
				}}
			}}
			trigger_event_non_silently = {{ id = rnw_probe.6 }}
		}}
	}}
}}

rnw_probe_read_state = {{
	decision_category = infrastructure_decisions

	potential = {{
		OR = {{
			tag = {HOST}
			tag = {TAG}
		}}
	}}

	allow = {{
		always = yes
	}}

	ai_will_do = {{
		value = -1
	}}

	option = {{
		name = rnw_probe_read_state.a
		ai_chance = {{ value = 0 }}
		effect = {{
			trigger_event_non_silently = {{ id = rnw_probe.1 }}
		}}
	}}
}}
"""


def _on_action() -> str:
    country, name, value = COUNTRY_VARIABLE
    location, _, location_value = LOCATION_VARIABLE
    # Two files that define ``on_game_start`` with an ``effect`` of their own do not both run:
    # the engine keeps the most recent (log: "There is more than one 'effect' defined"), so the
    # game's own start would not happen (experiment 036). A mod hooks the start the way the
    # game's ``ai_personalities_setup.txt`` does: a sub-on-action in ``on_actions``.
    return f"""on_game_start = {{
	on_actions = {{
		{START_ACTION}
	}}
}}

{START_ACTION} = {{
	effect = {{
		c:{country} = {{
			set_variable = {{ name = {name} value = {value} }}
		}}
		location:{location} = {{
			set_variable = {{ name = {name} value = {location_value} }}
		}}
		c:{HOST} = {{
			trigger_event_non_silently = {{ id = rnw_probe.1 }}
		}}
	}}
}}
"""


def _pulse() -> str:
    return f"""yearly_country_pulse = {{
	on_actions = {{
		rnw_probe_pulse
	}}
}}

rnw_probe_pulse = {{
	trigger = {{
		OR = {{
			tag = {HOST}
			tag = {TAG}
		}}
	}}
	events = {{
		rnw_probe.2
	}}
}}
"""


def _events() -> str:
    country, name, value = COUNTRY_VARIABLE
    location, _, location_value = LOCATION_VARIABLE
    return f"""namespace = rnw_probe

rnw_probe.1 = {{
	type = country_event
	title = rnw_probe.1.title
	desc = rnw_probe.1.desc
	outcome = neutral

	option = {{
		name = rnw_probe.1.country_variable
		trigger = {{
			c:{country} = {{ has_variable = {name} }}
		}}
	}}
	option = {{
		name = rnw_probe.1.country_value
		trigger = {{
			c:{country} = {{
				var:{name} >= {value}
				var:{name} <= {value}
			}}
		}}
	}}
	option = {{
		name = rnw_probe.1.location_variable
		trigger = {{
			location:{location} = {{ has_variable = {name} }}
		}}
	}}
	option = {{
		name = rnw_probe.1.location_value
		trigger = {{
			location:{location} = {{
				var:{name} >= {location_value}
				var:{name} <= {location_value}
			}}
		}}
	}}
	option = {{
		name = rnw_probe.1.nothing
		trigger = {{
			NOT = {{
				c:{country} = {{ has_variable = {name} }}
			}}
			NOT = {{
				location:{location} = {{ has_variable = {name} }}
			}}
		}}
	}}
	option = {{
		name = rnw_probe.1.close
	}}
}}

rnw_probe.2 = {{
	type = country_event
	title = rnw_probe.2.title
	desc = rnw_probe.2.desc
	outcome = neutral
	fire_only_once = yes

	option = {{
		name = rnw_probe.2.close
	}}
}}

rnw_probe.3 = {{
	type = country_event
	hidden = yes
	fire_only_once = yes

	dynamic_historical_event = {{
		tag = {HOST}
		from = 1337.1.1
		to = 1338.1.1
		monthly_chance = 100
	}}

	trigger = {{
		owns = location:{CAPITAL}
	}}

	immediate = {{
		set_variable = {{ name = {CENTRE} value = location:{CAPITAL} }}
		trigger_event_non_silently = {{ id = rnw_probe.4 }}
	}}
}}

rnw_probe.4 = {{
	type = country_event
	title = rnw_probe.4.title
	desc = rnw_probe.4.desc
	outcome = neutral

	option = {{
		name = rnw_probe.4.kept
		trigger = {{
			exists = var:{CENTRE}
			var:{CENTRE} ?= {{ owner ?= root }}
		}}
		trigger_event_non_silently = {{ id = rnw_probe.5 months = {{ 1 2 }} }}
	}}
	option = {{
		name = rnw_probe.4.lost
		trigger = {{
			NOT = {{ exists = var:{CENTRE} }}
		}}
	}}
}}

rnw_probe.5 = {{
	type = country_event
	title = rnw_probe.5.title
	desc = rnw_probe.5.desc
	outcome = neutral

	trigger = {{
		exists = var:{CENTRE}
		var:{CENTRE} ?= {{ owner ?= root }}
	}}

	option = {{
		name = rnw_probe.5.close
		remove_variable = {CENTRE}
	}}
}}

rnw_probe.6 = {{
	type = country_event
	title = rnw_probe.6.title
	desc = rnw_probe.6.desc
	outcome = neutral

	option = {{
		name = rnw_probe.6.close
	}}
}}
"""


def _flags() -> str:
    return f"""{TAG} = {{
	flag_definition = {{
		coa = {TAG}
		priority = 1
	}}
}}
"""


def _coat_of_arms() -> str:
    return f"""{TAG} = {{
	pattern = "pattern_solid.dds"
	color1 = "green"
	color2 = "white"

	colored_emblem = {{
		texture = "ce_checky_15_points.dds"
		color1 = color1
		color2 = color2
	}}
}}
"""


def _colors() -> str:
    return f"colors = {{\n\tmap_{TAG} = rgb {{ 200 40 160 }}\n}}\n"


def _texts(colony: str) -> dict[str, str]:
    return {
        TAG: "Probe Realm",
        f"{TAG}_ADJ": "Probe",
        SCRIPTED_NAME: "Probe Colony",
        f"{SCRIPTED_NAME}_ADJ": "Probe Colonial",
        # A decision is named by ``<id>.title`` and ``<id>.desc``; a formable by ``<id>`` and
        # ``<id>_desc`` (vanilla ``SWI_f: "$SWI$"``). Other keys show as the bare key (036).
        FORMABLE: f"${TAG}$",
        f"{FORMABLE}_desc": "A formable of a tag that no country file defines.",
        "rnw_probe_found_colony.title": "Probe: found a subject",
        "rnw_probe_found_colony.desc": (
            f"Makes {colony} a subject of the host. Reads the name its scripted country name gives."
        ),
        "rnw_probe_found_colony.a": "Found it",
        "rnw_probe_read_state.title": "Probe: read the start state",
        "rnw_probe_read_state.desc": "Shows which start variables the game kept.",
        "rnw_probe_read_state.a": "Show",
        "rnw_probe.1.title": "Probe: start state",
        "rnw_probe.1.desc": (
            f"Each line below is an option that shows only if it holds. Variable {VARIABLE} on "
            f"{COUNTRY_VARIABLE[0]} and on {LOCATION_VARIABLE[0]}, set when the game started."
        ),
        "rnw_probe.1.country_variable": f"The variable is set on {COUNTRY_VARIABLE[0]}",
        "rnw_probe.1.country_value": (
            f"Its value on {COUNTRY_VARIABLE[0]} is {COUNTRY_VARIABLE[2]}"
        ),
        "rnw_probe.1.location_variable": f"The variable is set on {LOCATION_VARIABLE[0]}",
        "rnw_probe.1.location_value": (
            f"Its value on {LOCATION_VARIABLE[0]} is {LOCATION_VARIABLE[2]}"
        ),
        "rnw_probe.1.nothing": "Neither variable is set: the mod's on_game_start did not run",
        "rnw_probe.1.close": "Close",
        "rnw_probe.2.title": "Probe: the yearly pulse",
        "rnw_probe.2.desc": (
            "The yearly pulse of the game reached an on_action of the mod that the mod hooked "
            "into it from its own file. If the game's other yearly events stopped happening, "
            "the mod's definition replaced the game's instead of adding to it."
        ),
        "rnw_probe.2.close": "Close",
        "rnw_probe.4.title": "Probe: the dynamic start",
        "rnw_probe.4.desc": (
            "A hidden event of the mod, opened by its dynamic historical window (certain every "
            f"month of the first year), stored {CAPITAL} in a variable and showed this. The "
            "stories of the mod begin the same way."
        ),
        "rnw_probe.4.kept": "The variable holds a location that the host owns: go on",
        "rnw_probe.4.lost": "The variable is missing",
        "rnw_probe.5.title": "Probe: the delayed event",
        "rnw_probe.5.desc": (
            "One or two months after the choice: the next event of the chain arrived and the "
            "variable still held its location. Closing removes the variable."
        ),
        "rnw_probe.5.close": "Close and remove the variable",
        "rnw_probe.6.title": "Probe: the new subject",
        "rnw_probe.6.desc": (
            "The decision made a subject of the host. Its name, as the game shows it: "
            "[rnw_probe_colony.GetName] (adjective: [rnw_probe_colony.GetAdjective]). It reads "
            "Probe Colony if the scripted country name of the mod applies."
        ),
        "rnw_probe.6.close": "Close",
    }


def _yaml(language: str, entries: dict[str, str]) -> bytes:
    lines = [f"l_{language}:"] + [f' {key}: "{value}"' for key, value in entries.items()]
    return ("\n".join(lines) + "\n").encode("utf-8-sig")


def metadata() -> bytes:
    """The mod's ``.metadata/metadata.json``."""
    payload: dict[str, object] = {
        "name": "RNW probe: content hooks",
        "id": NAME,
        "version": "0.2.0",
        "supported_game_version": "1.4.*",
        "short_description": (
            "Research probe of the Random New World project: a formable of a tag no country "
            "file defines, a scripted country name, start variables, a story start in miniature. "
            "Not a world; remove when the experiment is done."
        ),
        "tags": ["Utilities"],
        "relationships": [],
        "game_custom_data": {},
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8-sig")


def build(game_dir: Path) -> dict[str, bytes]:
    """The files of the probe mod by path; refuses an installation whose anchors differ."""
    problems = anchor_problems(game_dir)
    if problems:
        message = "The probe cannot be built:\n- " + "\n- ".join(problems)
        raise ProbeError(message)
    area = _area_of(game_dir, COLONY)
    files: dict[str, bytes] = {
        ".metadata/metadata.json": metadata(),
        "in_game/common/formable_countries/rnw_probe.txt": _formable().encode("utf-8-sig"),
        "in_game/common/scripted_country_names/rnw_probe.txt": _scripted_name(area).encode(
            "utf-8-sig"
        ),
        "in_game/common/decisions/rnw_probe.txt": _decisions().encode("utf-8-sig"),
        "in_game/common/on_action/rnw_probe.txt": _on_action().encode("utf-8-sig"),
        "in_game/common/on_action/rnw_probe_pulse.txt": _pulse().encode("utf-8-sig"),
        "in_game/events/rnw_probe.txt": _events().encode("utf-8-sig"),
        "main_menu/common/flag_definitions/rnw_probe.txt": _flags().encode("utf-8-sig"),
        "main_menu/common/coat_of_arms/coat_of_arms/rnw_probe.txt": _coat_of_arms().encode(
            "utf-8-sig"
        ),
        "main_menu/common/named_colors/rnw_probe.txt": _colors().encode("utf-8-sig"),
    }
    texts = _texts(COLONY)
    for language in official_languages(game_dir):
        files[f"main_menu/localization/{language}/rnw_probe_l_{language}.yml"] = _yaml(
            language, texts
        )
    return files


def check(files: dict[str, bytes]) -> None:
    """Every script file of the probe reads as Paradox script; raises ``ProbeError`` if not."""
    for path, data in files.items():
        if path.endswith(".txt"):
            root = parse(data.decode("utf-8-sig"))
            if not any(isinstance(entry.value, Block) for entry in root.entries):
                message = f"{path} holds no block"
                raise ProbeError(message)
