"""Every text the world's own scripts and texts ask the game for exists (no key on the screen).

The game shows a localization key it cannot find as the key itself, and logs it
(``localization_util.cpp``). Which keys a script asks for follows vanilla's conventions, read from
the installation [V-LOCAL, EU5 1.4.7 build 26377361]:

* a decision is named by ``<decision>.title`` and described by ``<decision>.desc``
  (``canal_decisions_l_english.yml``);
* an event shows its ``title``, ``desc`` and ``historical_info`` keys and each option's ``name``;
  an event with a ``dynamic_historical_event`` window is listed in the country's events by
  ``<event>.entry`` (every vanilla ``DHE`` event has one); a ``hidden`` event shows nothing;
* a formable is listed by its own key, its country by its tag and ``<tag>_ADJ``;
* a scripted geography is named by its own key wherever a tooltip shows it (vanilla names every
  one of its 45, ``scripted_geography_names_l_english.yml``); the game asked for every geography
  of the formables' file, used or not (``error.log`` of 2026-11-08), so a geography file that
  formables or missions use is named whole;
* ``$key$`` inside a text is the text of another key.

Only the mod's own script files (``rnw_*``) are read: vanilla files the export rewrites keep
vanilla's keys. A key resolves when the same language writes it or vanilla has its hash.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from rnw.loc_keys import key_hash
from rnw.pdx import Block, parse

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

# A localization entry: an indented key, an optional version number, then the quoted text.
ENTRY: Final[re.Pattern[str]] = re.compile(r'^\s+([^\s:#"]+):\d*\s+"(.*)"\s*$', re.MULTILINE)
# ``$key$`` or ``$key|format$`` inside a text.
REFERENCE: Final[re.Pattern[str]] = re.compile(r"\$([A-Za-z0-9_.\-']+)(?:\|[^$\s]*)?\$")
SCRIPTED_GEOGRAPHY: Final[re.Pattern[str]] = re.compile(r"scripted_geography:([A-Za-z0-9_]+)")
SHOWN: Final[tuple[str, ...]] = ("title", "desc", "historical_info")
REPORTED: Final[int] = 8


class TextReferenceError(ValueError):
    """A text that the world's scripts or texts ask for is written nowhere."""


def written_texts(outputs: Mapping[str, bytes]) -> dict[str, dict[str, str]]:
    """The localization the outputs write: by language, each key's text."""
    found: dict[str, dict[str, str]] = {}
    for path, data in outputs.items():
        if not path.endswith(".yml") or "/localization/" not in path:
            continue
        language = path.split("/localization/", 1)[1].split("/", 1)[0]
        texts = found.setdefault(language, {})
        texts.update(
            (match.group(1), match.group(2)) for match in ENTRY.finditer(data.decode("utf-8-sig"))
        )
    return found


def _strings(value: object, keys: tuple[str, ...]) -> Iterator[str]:
    """``value`` if it is a key, or every key under ``keys`` inside it (``first_valid``,
    ``triggered_desc``)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, Block):
        for entry in value.entries:
            if entry.key in keys or entry.key in {"first_valid", "random_valid", "triggered_desc"}:
                yield from _strings(entry.value, keys)


def _event_keys(event: str, body: Block) -> Iterator[str]:
    hidden = body.first("hidden")
    if hidden is not None and hidden.value == "yes":
        return
    for entry in body.entries:
        if entry.key in SHOWN:
            yield from _strings(entry.value, ("desc", "title"))
        elif entry.key == "option" and isinstance(entry.value, Block):
            for name in entry.value.find("name"):
                yield from _strings(name.value, ("desc", "title"))
    if body.block("dynamic_historical_event") is not None:
        yield f"{event}.entry"


def _formable_keys(key: str, body: Block) -> Iterator[str]:
    yield key
    for field in ("name", "adjective"):
        named = body.first(field)
        if named is not None:
            yield from _strings(named.value, ())


def _file_keys(path: str, text: str) -> set[str]:
    """The keys one of the mod's script files asks for."""
    keys: set[str] = set()
    blocks = [
        (entry.key, entry.value)
        for entry in parse(text).entries
        if entry.key is not None and isinstance(entry.value, Block)
    ]
    if "/common/decisions/" in path:
        keys.update(f"{key}.{part}" for key, _ in blocks for part in ("title", "desc"))
    elif "/events/" in path:
        for key, body in blocks:
            keys.update(_event_keys(key, body))
    elif "/common/formable_countries/" in path:
        for key, body in blocks:
            keys.update(_formable_keys(key, body))
    if "/common/formable_countries/" in path or "/common/missions/" in path:
        keys.update(SCRIPTED_GEOGRAPHY.findall(text))
    return keys


def _own(path: str, folder: str) -> bool:
    return folder in path and path.endswith(".txt") and path.rsplit("/", 1)[-1].startswith("rnw_")


def asked_keys(outputs: Mapping[str, bytes]) -> dict[str, set[str]]:
    """The keys each of the mod's own script files asks the game for, by path."""
    found: dict[str, set[str]] = {}
    for path, data in sorted(outputs.items()):
        if _own(path, "/"):
            keys = _file_keys(path, data.decode("utf-8-sig"))
            if keys:
                found[path] = keys
    # A geography file that formables or missions use is shown in their tooltips: all of it.
    used = {key for keys in found.values() for key in keys}
    for path, data in sorted(outputs.items()):
        if _own(path, "/common/scripted_geography/"):
            defined = {
                entry.key
                for entry in parse(data.decode("utf-8-sig")).entries
                if entry.key is not None
            }
            if defined & used:
                found[path] = defined
    return found


def verify(outputs: Mapping[str, bytes], vanilla_hashes: set[int]) -> dict[str, object]:
    """Raise unless every key the mod's scripts ask for and every ``$key$`` of its texts is
    written in every language of the world or is vanilla's."""
    texts = written_texts(outputs)
    asked = asked_keys(outputs)
    missing: list[str] = []
    references = 0
    for language, entries in sorted(texts.items()):

        def known(key: str, entries: Mapping[str, str] = entries) -> bool:
            return key in entries or key_hash(key) in vanilla_hashes

        for key, text in entries.items():
            for match in REFERENCE.finditer(text):
                reference = match.group(1)
                references += 1
                if not known(reference):
                    missing.append(f"{language}: ${reference}$ in {key}")
        for path, keys in asked.items():
            missing.extend(
                f"{language}: {key} for {path}" for key in sorted(keys) if not known(key)
            )
    if missing:
        shown = "; ".join(missing[:REPORTED])
        more = f" and {len(missing) - REPORTED} more" if len(missing) > REPORTED else ""
        message = f"The world asks for texts it does not write: {shown}{more}"
        raise TextReferenceError(message)
    return {
        "text_references": references,
        "script_text_keys": sum(len(keys) for keys in asked.values()),
    }
