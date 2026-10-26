"""Every static text of the world's mod, by key, in English, and its writing in each language.

The static texts are the stories (events, options, modifiers, privileges), the formable families
(descriptions with ``{name}`` for the formable's name, founding modifiers) and the exceptional
places: the sources of the ``game`` catalogs (``translations``). A world's localization is a set
of *entries*: a static text by its key (``Text``), a static text with a name filled in
(``Described``), or a name the world composed (``wording.Name``); ``localize`` writes them in one
language.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

from rnw import eu5_places, translations, wording
from rnw.formations import SPECS
from rnw.stories import STORIES
from rnw.storymodel import event_keys

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

FORMATION_DESCRIPTION = "rnw_formation_{family}_desc"


@dataclass(frozen=True, slots=True)
class Text:
    """A static text, by the key of its English source."""

    source: str


@dataclass(frozen=True, slots=True)
class Described:
    """A static text with ``{name}`` for a name the world composed."""

    source: str
    name: wording.Name


type Entry = Text | Described | wording.Name


def formation_description(family: str) -> str:
    """The key of a formable family's description, with ``{name}`` for the formable's name."""
    return FORMATION_DESCRIPTION.format(family=family)


@cache
def sources() -> dict[str, str]:
    """Every static text of the mod, by its key, in English."""
    found: dict[str, str] = {"rnw_treaty_meridian": "Treaty meridian"}
    for story in STORIES:
        found.update(event_keys(story))
    for spec in SPECS:
        found[formation_description(spec.family)] = spec.description
        found[f"STATIC_MODIFIER_NAME_{spec.modifier.name}"] = spec.modifier.title
        found[f"STATIC_MODIFIER_DESC_{spec.modifier.name}"] = spec.modifier.text
    found.update(eu5_places.texts(eu5_places.SPECS))
    return found


def untranslated(languages: Iterable[str]) -> list[str]:
    """The languages among ``languages`` that the generator has no catalog for (written in
    English, and refused by the release check)."""
    return [
        language
        for language in languages
        if not translations.has_catalog(translations.GAME, language)
    ]


def localize(entries: Mapping[str, Entry], language: str) -> dict[str, str]:
    """The entries written in ``language``, by their keys, in their order."""
    english = sources()
    needed = {
        entry.source: english[entry.source]
        for entry in entries.values()
        if isinstance(entry, Text | Described)
    }
    texts = (
        translations.translate(translations.GAME, language, needed)
        if translations.has_catalog(translations.GAME, language)
        else needed
    )
    written: dict[str, str] = {}
    for key, entry in entries.items():
        if isinstance(entry, Text):
            written[key] = texts[entry.source]
        elif isinstance(entry, Described):
            written[key] = texts[entry.source].replace(
                "{name}", wording.render(entry.name, language)
            )
        else:
            written[key] = wording.render(entry, language)
    return written
