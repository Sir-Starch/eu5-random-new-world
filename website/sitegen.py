"""Build the player's guide at https://rnw.sirstarch.com into ``website/public/``.

The Workshop page's *Guide* button leads here. One static page per official EU5 language,
rendered from ``content/<language>.toml``; the root page sends a visitor to their language.
Nothing is fetched at run time: fonts are subset to the characters each page uses, pictures are
cut from the owner-approved screenshots in ``docs/images/showcase``, and the chart art (world-type
silhouettes, the Terra Incognita fog on the hero map, rhumb lines) is drawn here.

The guide describes a **released** generator, ``RELEASE``. Its controls are named in the
window's own words of that release: English from ``rnw/gui/text.py`` and the translations from
``rnw/locale/<language>/window.toml`` at the release tag, refused when missing or stale exactly
as the window refuses them. EU5's own interface words come from the game (``GAME_TERMS``).

    uv run --with "fonttools[woff]" python website/sitegen.py      # everything
    uv run python website/sitegen.py --html                        # pages only, fonts as recorded

The output is committed; ``tests/test_website.py`` fails when a page is out of date with its
sources, a translation is stale or loses markup, or a font subset lacks a character it shows.
Publishing the folder is a separate, owner-authorized step (website/README.md).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
import json
import math
import random
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, cast

ROOT: Final = Path(__file__).resolve().parent.parent
HERE: Final = ROOT / "website"
CONTENT: Final = HERE / "content"
SRC: Final = HERE / "src"
PUBLIC: Final = HERE / "public"
SHOWCASE: Final = ROOT / "docs" / "images" / "showcase"
SITE: Final = "https://rnw.sirstarch.com"
WORKSHOP: Final = "https://steamcommunity.com/sharedfiles/filedetails/?id=3829217331"
REPO: Final = "https://github.com/Sir-Starch/eu5-random-new-world"
KOFI: Final = "https://ko-fi.com/rnw"

# The release the guide describes. Bump with a release; the terms follow the tag.
RELEASE: Final[dict[str, str]] = {
    "tag": "v1.1.0",
    "version": "1.1.0",
    "game": "1.4.*",
    "verified": "1.4.7",
}


@dataclass(frozen=True)
class Language:
    game: str  # EU5's folder name, as in rnw/locale
    slug: str  # URL path
    tag: str  # BCP 47 for lang/hreflang
    name: str  # its own name
    script: str  # latin | cyrillic | ja | ko | zh


LANGUAGES: Final[tuple[Language, ...]] = (
    Language("english", "en", "en", "English", "latin"),
    Language("german", "de", "de", "Deutsch", "latin"),
    Language("spanish", "es", "es", "Español", "latin"),
    Language("french", "fr", "fr", "Français", "latin"),
    Language("polish", "pl", "pl", "Polski", "latin"),
    Language("braz_por", "pt-br", "pt-BR", "Português (Brasil)", "latin"),
    Language("turkish", "tr", "tr", "Türkçe", "latin"),
    Language("russian", "ru", "ru", "Русский", "cyrillic"),
    Language("japanese", "ja", "ja", "日本語", "ja"),
    Language("korean", "ko", "ko", "한국어", "ko"),
    Language("simp_chinese", "zh", "zh-Hans", "简体中文", "zh"),
)
SOURCE: Final = "english"

# EU5's words for the parts of its interface the guide names, read from the installed game's
# main_menu/localization (MAIN_MENU_MODS_AND_DLCS, MODS_GUI_TAB_MODS, MODS_GUI_OPEN_IN_FOLDER,
# MODS_GUI_APPLY_LABEL), EU5 1.4.7 / Steam build 26377361, 2026-11-04 [V-LOCAL].
GAME_TERMS: Final[dict[str, dict[str, str]]] = {
    "english": {
        "mods_dlcs": "Mods & DLCs",
        "open_folder": "Open folder",
        "apply": "Apply",
    },
    "german": {
        "mods_dlcs": "Mods & DLC",
        "open_folder": "Ordner öffnen",
        "apply": "Anwenden",
    },
    "spanish": {
        "mods_dlcs": "Mods y DLC",
        "open_folder": "Abrir carpeta",
        "apply": "Aplicar",
    },
    "french": {
        "mods_dlcs": "Mods et DLC",
        "open_folder": "Ouvrir le dossier",
        "apply": "Appliquer",
    },
    "polish": {
        "mods_dlcs": "Mody i DLC",
        "open_folder": "Otwórz folder",
        "apply": "Zastosuj",
    },
    "braz_por": {
        "mods_dlcs": "Mods e DLCs",
        "open_folder": "Abrir pasta",
        "apply": "Aplicar",
    },
    "turkish": {
        "mods_dlcs": "Modlar ve DLC'ler",
        "open_folder": "Klasörü aç",
        "apply": "Uygula",
    },
    "russian": {
        "mods_dlcs": "Модификации и дополнения",
        "open_folder": "Открыть папку",
        "apply": "Применить",
    },
    "japanese": {
        "mods_dlcs": "MODとDLC",
        "open_folder": "フォルダを開く",
        "apply": "適用",
    },
    "korean": {
        "mods_dlcs": "모드 및 DLC",
        "open_folder": "폴더 열기",
        "apply": "적용",
    },
    "simp_chinese": {
        "mods_dlcs": "模组和DLC",
        "open_folder": "打开文件夹",
        "apply": "应用",
    },
}


SECTIONS: Final[tuple[str, ...]] = (
    "start",
    "rules",
    "types",
    "settings",
    "hidden",
    "library",
    "compat",
    "help",
)
ROMAN: Final[tuple[str, ...]] = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII")
WORLD_TYPES: Final[tuple[str, ...]] = (
    "supercontinent",
    "continents",
    "small_continents",
    "archipelago",
    "islands",
    "wall",
)


class BuildError(RuntimeError):
    """The guide cannot be built as asked; nothing is quietly substituted."""


# ---------------------------------------------------------------------------------------------
# Sources: content, translations, the window's words


def flatten(table: dict[str, object], prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in table.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(cast("dict[str, object]", value), f"{name}."))
        elif isinstance(value, str):
            out[name] = value
        else:
            message = f"{name}: expected text"
            raise BuildError(message)
    return out


def fingerprint(texts: dict[str, str]) -> str:
    canonical = json.dumps(texts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def read_content(language: str) -> tuple[dict[str, str], str | None]:
    """A language's texts and the English fingerprint it records (None for English)."""
    path = CONTENT / f"{language}.toml"
    if not path.is_file():
        message = f"no content for {language}: {path}"
        raise BuildError(message)
    texts = flatten(tomllib.loads(path.read_text(encoding="utf-8")))
    source = texts.pop("source", None)
    return texts, source


MARKUP: Final = re.compile(
    r"\{(ui|game|v):([^}]+)\}|\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)\s]+)\)"
)


def markup_signature(text: str) -> list[str]:
    """What a translation must carry over unchanged: terms, facts, code and link targets."""
    found: list[str] = []
    for m in MARKUP.finditer(text):
        if m.group(1):
            found.append(f"{m.group(1)}:{m.group(2)}")
        elif m.group(4) is not None:
            found.append(f"code:{m.group(4)}")
        elif m.group(6):
            found.append(f"link:{m.group(6)}")
        else:
            found.append("strong")
    return sorted(found)


def content_problems(only: frozenset[str] | None = None) -> list[str]:
    """Every reason the translations cannot ship: missing, extra, stale or changed markup."""
    english, _ = read_content(SOURCE)
    expected = fingerprint(english)
    problems: list[str] = []
    for language in LANGUAGES:
        if language.game == SOURCE or (only is not None and language.game not in only):
            continue
        try:
            texts, source = read_content(language.game)
        except BuildError as error:
            problems.append(str(error))
            continue
        if source != expected:
            problems.append(f"{language.game}: translated from {source}, English is {expected}")
        problems.extend(
            f"{language.game}: {key} is missing" for key in english.keys() - texts.keys()
        )
        problems.extend(
            f"{language.game}: {key} is not in the English" for key in texts.keys() - english.keys()
        )
        for key in english.keys() & texts.keys():
            if markup_signature(english[key]) != markup_signature(texts[key]):
                problems.append(f"{language.game}: {key} changes its markup")
            if not texts[key].strip():
                problems.append(f"{language.game}: {key} is empty")
    return problems


def git_show(path: str) -> str:
    spec = f"{RELEASE['tag']}:{path}"
    done = subprocess.run(
        ["git", "-C", str(ROOT), "show", spec], capture_output=True, text=True, check=False
    )
    if done.returncode:
        message = f"cannot read {spec}: {done.stderr.strip()}"
        raise BuildError(message)
    return done.stdout


def window_english() -> dict[str, str]:
    module = ast.parse(git_show("src/rnw/gui/text.py"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id == "STRINGS":
            strings = cast("object", ast.literal_eval(value))
            if isinstance(strings, dict):
                return {str(k): str(v) for k, v in cast("dict[object, object]", strings).items()}
    message = "STRINGS not found in rnw/gui/text.py"
    raise BuildError(message)


def window_fingerprint(english: str) -> str:
    return hashlib.sha256(english.encode("utf-8")).hexdigest()[:16]  # rnw.translations.fingerprint


def window_terms(language: str, english: dict[str, str]) -> dict[str, str]:
    """The window's words in ``language`` at the release, refused when missing or stale."""
    if language == SOURCE:
        return english
    catalog: dict[str, object] = tomllib.loads(git_show(f"src/rnw/locale/{language}/window.toml"))

    class Terms(dict[str, str]):
        def __missing__(self, key: str) -> str:
            found = catalog.get(key)
            if key not in english or not isinstance(found, dict):
                message = f"{language}: the window has no translation of {key}"
                raise BuildError(message)
            entry = cast("dict[str, object]", found)
            if entry.get("source") != window_fingerprint(english[key]):
                message = f"{language}: the window's translation of {key} is stale"
                raise BuildError(message)
            return str(entry["text"])

    return Terms()


TERM_COUNT: Final = re.compile(r"\s*[(（]\s*\{count\}\s*[)）]")


def clean_term(text: str) -> str:
    """A control's label as prose names it: no count, no trailing ellipsis."""
    text = TERM_COUNT.sub("", text).strip()
    return re.sub(r"(…|\.\.\.)$", "", text).strip()


# ---------------------------------------------------------------------------------------------
# Rendering


def esc(text: str) -> str:
    return html.escape(text, quote=True)


@dataclass
class Page:
    language: Language
    texts: dict[str, str]
    terms: dict[str, str]
    display: set[str] = field(default_factory=set)  # characters set in the display face

    def raw(self, key: str) -> str:
        try:
            return self.texts[key]
        except KeyError:
            message = f"{self.language.game}: no text {key}"
            raise BuildError(message) from None

    def ui(self, key: str) -> str:
        return clean_term(self.terms[key])

    def game(self, key: str) -> str:
        return GAME_TERMS[self.language.game][key]

    def inline(self, text: str, *, display: bool = False) -> str:
        out: list[str] = []
        pos = 0
        for m in MARKUP.finditer(text):
            out.append(self._plain(text[pos : m.start()], display))
            kind, key = m.group(1), m.group(2)
            if kind == "ui":
                out.append(f'<span class="ui">{esc(self.ui(key))}</span>')
            elif kind == "game":
                out.append(f'<span class="gm">{esc(self.game(key))}</span>')
            elif kind == "v":
                out.append(self._plain(RELEASE[key], display))
            elif m.group(3) is not None:
                out.append(f"<strong>{self.inline(m.group(3), display=display)}</strong>")
            elif m.group(4) is not None:
                out.append(f"<code>{esc(m.group(4))}</code>")
            else:
                out.append(
                    f'<a href="{esc(m.group(6))}">{self.inline(m.group(5), display=display)}</a>'
                )
            pos = m.end()
        out.append(self._plain(text[pos:], display))
        return "".join(out)

    def _plain(self, text: str, display: bool) -> str:  # noqa: FBT001 - internal helper
        if display:
            self.display.update(text)
        return esc(text)

    def t(self, key: str) -> str:
        return self.inline(self.raw(key))

    def h(self, key: str) -> str:
        return self.inline(self.raw(key), display=True)

    def plain(self, key: str) -> str:
        """Text for an attribute: markup reduced to its words."""
        text = self.raw(key)
        text = MARKUP.sub(
            lambda m: (
                self.ui(m.group(2))
                if m.group(1) == "ui"
                else self.game(m.group(2))
                if m.group(1) == "game"
                else RELEASE[m.group(2)]
                if m.group(1) == "v"
                else (m.group(3) or m.group(4) or m.group(5) or "")
            ),
            text,
        )
        return esc(text)


# --- small drawings -------------------------------------------------------------------------

ICONS: Final[dict[str, str]] = {
    "flag": '<path d="M6 21V4"/><path d="M6 4.5h11l-2.6 4 2.6 4H6"/>',
    "tick": '<rect x="4" y="4" width="16" height="16" rx="1.5"/><path d="m8 12.4 2.8 2.8L16.4 9"/>',
    "restart": '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.6 3.8v3.6H16"/>',
    "anchor": (
        '<circle cx="12" cy="5" r="2"/><path d="M12 7v13"/><path d="M8.5 10.5h7"/>'
        '<path d="M4.5 13.5c.4 4 3.6 6.5 7.5 6.5s7.1-2.5 7.5-6.5"/><path d="m3 15 1.5-1.5L6 15"/><path d="m18 15 1.5-1.5L21 15"/>'
    ),
    "ok": '<circle cx="12" cy="12" r="9"/><path d="m8 12.3 2.7 2.7L16.2 9.3"/>',
    "if": '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5"/><path d="M12 16.2v.3"/>',
    "no": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6"/><path d="m15 9-6 6"/>',
    "globe": (
        '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/>'
        '<path d="M12 3c2.6 2.6 3.8 5.6 3.8 9s-1.2 6.4-3.8 9c-2.6-2.6-3.8-5.6-3.8-9S9.4 5.6 12 3z"/>'
    ),
    "dice": (
        '<rect x="4" y="4" width="16" height="16" rx="2.5"/><circle cx="9" cy="9" r=".6"/>'
        '<circle cx="15" cy="15" r=".6"/><circle cx="15" cy="9" r=".6"/><circle cx="9" cy="15" r=".6"/>'
        '<circle cx="12" cy="12" r=".6"/>'
    ),
    "storm": '<path d="M5 16c3-1 4-4 7-4s3 3 7 2"/><path d="M5 11c3-1 4-4 7-4s3 3 7 2"/><path d="m13 15-2 5 4-3"/>',
    "arrow": '<path d="M12 5v14"/><path d="m6 13 6 6 6-6"/>',
    "out": '<path d="M14 4h6v6"/><path d="m20 4-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
}


def icon(name: str, cls: str = "ic") -> str:
    return (
        f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" '
        f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'
    )


COMPASS: Final = (
    '<svg class="compass" viewBox="0 0 32 32" aria-hidden="true">'
    '<circle cx="16" cy="16" r="13" fill="none" stroke="currentColor" stroke-width="1"/>'
    '<circle cx="16" cy="16" r="9.5" fill="none" stroke="currentColor" stroke-width=".6" opacity=".6"/>'
    '<path d="M16 1.5 18.2 13.8 30.5 16 18.2 18.2 16 30.5 13.8 18.2 1.5 16 13.8 13.8Z" fill="currentColor"/>'
    '<path class="core" d="M16 7 17 15 25 16 17 17 16 25 15 17 7 16 15 15Z"/>'
    "</svg>"
)


# --- procedural chart art -------------------------------------------------------------------


class Noise:
    """Value noise on a seeded lattice, a few octaves: coastlines for the chart vignettes."""

    def __init__(self, seed: int, size: int = 64) -> None:
        rng = random.Random(seed)
        self.size: int = size
        self.grid: list[list[float]] = [
            [rng.random() * 2 - 1 for _ in range(size)] for _ in range(size)
        ]

    def _at(self, x: float, y: float) -> float:
        n = self.size
        x0, y0 = math.floor(x), math.floor(y)
        fx, fy = x - x0, y - y0
        sx, sy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        g = self.grid
        a = g[y0 % n][x0 % n]
        b = g[y0 % n][(x0 + 1) % n]
        c = g[(y0 + 1) % n][x0 % n]
        d = g[(y0 + 1) % n][(x0 + 1) % n]
        return (a + (b - a) * sx) + ((c + (d - c) * sx) - (a + (b - a) * sx)) * sy

    def __call__(self, x: float, y: float, octaves: int = 4) -> float:
        total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
        for _ in range(octaves):
            total += self._at(x * freq, y * freq) * amp
            norm += amp
            amp *= 0.5
            freq *= 2.0
        return total / norm


@dataclass(frozen=True)
class Blob:
    x: float
    y: float
    rx: float
    ry: float
    w: float = 1.0


def world_blobs(kind: str, rng: random.Random) -> list[Blob]:
    """Metaball recipes that read like each world type's typical result."""
    blobs: list[Blob] = []

    def isles(n: int, size: tuple[float, float], area: tuple[float, float, float, float]) -> None:
        for _ in range(n):
            r = rng.uniform(*size)
            blobs.append(
                Blob(
                    rng.uniform(area[0], area[1]),
                    rng.uniform(area[2], area[3]),
                    r,
                    r * rng.uniform(0.7, 1.3),
                )
            )

    if kind == "supercontinent":
        for x, y, rx, ry in (
            (0.5, 0.46, 0.25, 0.22),
            (0.32, 0.34, 0.13, 0.12),
            (0.69, 0.3, 0.14, 0.11),
            (0.4, 0.7, 0.15, 0.14),
            (0.67, 0.68, 0.12, 0.15),
            (0.2, 0.56, 0.07, 0.06),
        ):
            blobs.append(Blob(x, y, rx, ry))
        isles(3, (0.025, 0.04), (0.12, 0.88, 0.12, 0.88))
    elif kind == "continents":
        blobs += [
            Blob(0.4, 0.27, 0.2, 0.15),
            Blob(0.3, 0.32, 0.12, 0.1),
            Blob(0.6, 0.68, 0.17, 0.17),
        ]
        blobs += [Blob(0.48, 0.47, 0.035, 0.08, 0.9), Blob(0.54, 0.55, 0.04, 0.06, 0.9)]
        isles(5, (0.02, 0.035), (0.15, 0.88, 0.15, 0.9))
    elif kind == "small_continents":
        for x, y in ((0.28, 0.3), (0.68, 0.26), (0.36, 0.7), (0.72, 0.68)):
            blobs.append(
                Blob(x + rng.uniform(-0.03, 0.03), y + rng.uniform(-0.03, 0.03), 0.13, 0.12)
            )
        isles(3, (0.02, 0.03), (0.1, 0.9, 0.1, 0.9))
    elif kind == "archipelago":
        for x, y in (
            (0.22, 0.28),
            (0.5, 0.2),
            (0.78, 0.32),
            (0.3, 0.62),
            (0.58, 0.5),
            (0.8, 0.72),
            (0.48, 0.82),
        ):
            blobs.append(
                Blob(
                    x + rng.uniform(-0.03, 0.03),
                    y + rng.uniform(-0.03, 0.03),
                    rng.uniform(0.06, 0.085),
                    rng.uniform(0.05, 0.08),
                )
            )
        isles(16, (0.014, 0.026), (0.06, 0.94, 0.08, 0.92))
    elif kind == "islands":
        isles(34, (0.016, 0.034), (0.05, 0.95, 0.07, 0.93))
    elif kind == "wall":
        steps = 24
        for i in range(steps + 1):
            y = -0.1 + 1.2 * i / steps
            x = 0.5 + 0.05 * math.sin(y * 5.2) + 0.02 * math.sin(y * 13)
            blobs.append(Blob(x, y, 0.085, 0.07))
        isles(6, (0.018, 0.03), (0.08, 0.3, 0.1, 0.9))
        isles(6, (0.018, 0.03), (0.7, 0.92, 0.1, 0.9))
    else:
        raise BuildError(kind)
    return blobs


def marching_squares(
    values: list[list[float]], level: float = 0.0
) -> list[list[tuple[float, float]]]:
    """Closed contours of a field padded with sea; points in grid units."""
    h, w = len(values), len(values[0])
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []

    def lerp(p: tuple[int, int], q: tuple[int, int]) -> tuple[float, float]:
        a, b = values[p[1]][p[0]], values[q[1]][q[0]]
        t = 0.5 if a == b else (level - a) / (b - a)
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)

    for y in range(h - 1):
        for x in range(w - 1):
            c = [(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)]
            inside = [values[py][px] > level for px, py in c]
            idx = sum(1 << i for i, v in enumerate(inside) if v)
            if idx in (0, 15):
                continue
            edges = [(c[0], c[1]), (c[1], c[2]), (c[2], c[3]), (c[3], c[0])]
            crossings = [
                lerp(*e)
                for e, a, b in zip(edges, inside, inside[1:] + inside[:1], strict=True)
                if a != b
            ]
            if len(crossings) == 2:
                segments.append((crossings[0], crossings[1]))
            else:  # saddle: pair by the centre value
                centre = sum(values[py][px] for px, py in c) / 4 > level
                e = [lerp(*edge) for edge in edges]
                if (idx == 5) == centre:
                    segments += [(e[0], e[1]), (e[2], e[3])]
                else:
                    segments += [(e[0], e[3]), (e[1], e[2])]

    def key(p: tuple[float, float]) -> tuple[int, int]:
        return (round(p[0] * 1000), round(p[1] * 1000))

    links: dict[tuple[int, int], list[int]] = {}
    for i, (a, b) in enumerate(segments):
        links.setdefault(key(a), []).append(i)
        links.setdefault(key(b), []).append(i)
    used = [False] * len(segments)
    loops: list[list[tuple[float, float]]] = []
    for start in range(len(segments)):
        if used[start]:
            continue
        used[start] = True
        a, b = segments[start]
        loop = [a, b]
        current = b
        while True:
            nxt = next((i for i in links[key(current)] if not used[i]), None)
            if nxt is None:
                break
            used[nxt] = True
            p, q = segments[nxt]
            current = q if key(p) == key(current) else p
            loop.append(current)
        loops.append(loop)
    return loops


def chaikin(points: list[tuple[float, float]], rounds: int = 2) -> list[tuple[float, float]]:
    for _ in range(rounds):
        n = len(points)
        out: list[tuple[float, float]] = []
        for i in range(n):
            p, q = points[i], points[(i + 1) % n]
            out += [
                (0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]),
                (0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1]),
            ]
        points = out
    return points


def polygon_area(points: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        p[0] * q[1] - q[0] * p[1] for p, q in zip(points, points[1:] + points[:1], strict=True)
    )


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Ramer-Douglas-Peucker on a closed ring: fewer points, the same coast at chart scale."""

    def rdp(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if len(pts) < 3:
            return pts
        (x1, y1), (x2, y2) = pts[0], pts[-1]
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1e-9
        index, worst = 0, -1.0
        for i in range(1, len(pts) - 1):
            d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / norm
            if d > worst:
                index, worst = i, d
        if worst <= tolerance:
            return [pts[0], pts[-1]]
        return rdp(pts[: index + 1])[:-1] + rdp(pts[index:])

    half = len(points) // 2
    return rdp(points[: half + 1])[:-1] + rdp([*points[half:], points[0]])[:-1]


WATER_LINES: Final = (("#4a6273", 15), ("#34444f", 11.5), ("#5f7c8f", 7.5), ("#34444f", 4.5))


def world_svg(kind: str) -> str:
    """A chart vignette of a world type: water-lined coasts on the sea, mountains as hachures."""
    seed = int(hashlib.sha256(kind.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    noise = Noise(seed)
    vw, vh = 300.0, 200.0
    gw, gh = 150, 100
    blobs = world_blobs(kind, rng)
    field_: list[list[float]] = []
    for gy in range(gh + 1):
        row: list[float] = []
        for gx in range(gw + 1):
            if gx in (0, gw) or (kind != "wall" and gy in (0, gh)):
                row.append(-1.0)
                continue
            u, v = gx / gw, gy / gh
            wu = u + 0.09 * noise(u * 3 + 11, v * 3, 3)  # warped: peninsulas and gulfs
            wv = v + 0.09 * noise(u * 3, v * 3 + 7, 3)
            mass = sum(
                b.w * math.exp(-(((wu - b.x) / b.rx) ** 2 + ((wv - b.y) / b.ry) ** 2))
                for b in blobs
            )
            value = 1 - math.exp(-1.3 * mass)  # interiors saturate, so the noise shapes every coast
            value += (
                0.34 * noise(u * 6, v * 6)
                + 0.18 * noise(u * 16 + 3, v * 16 + 5, 3)
                + 0.08 * noise(u * 40, v * 40, 2)
            )
            row.append(value - 0.55)
        field_.append(row)
    if kind == "wall":  # the Wall runs off the chart at both poles
        field_.insert(0, [-1.0] * (gw + 1))
        field_.append([-1.0] * (gw + 1))
        offset = 1
    else:
        offset = 0
    sx, sy = vw / gw, vh / gh
    paths: list[str] = []
    for loop in marching_squares(field_):
        if len(loop) < 6:
            continue
        closed = abs(loop[0][0] - loop[-1][0]) + abs(loop[0][1] - loop[-1][1]) < 1e-6
        pts = [(x * sx, (y - offset) * sy) for x, y in chaikin(loop[:-1] if closed else loop, 1)]
        if abs(polygon_area(pts)) < 6:
            continue
        pts = simplify(pts, 0.35)
        paths.append(
            "M"
            + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts).replace(".0,", ",").replace(".0L", "L")
            + "Z"
        )
    coast = "".join(paths)
    marks: list[tuple[int, int]] = []
    cells = [(gx, gy) for gy in range(2, gh - 2, 3) for gx in range(2, gw - 2, 3)]
    rng.shuffle(cells)
    for gx, gy in cells:
        value = field_[gy + offset][gx]
        if value > (0.38 if kind == "wall" else 0.45) and all(
            abs(gx - mx) > 5 or abs(gy - my) > 4 for mx, my in marks
        ):
            marks.append((gx, gy))
        if len(marks) >= (14 if kind == "wall" else 7):
            break
    hachures = "".join(
        f"M{gx * sx - 4.5:.1f},{gy * sy + 2:.1f}l4.5-6 4.5 6" for gx, gy in sorted(marks)
    )
    rings = "".join(
        f'<use href="#c" stroke="{color}" stroke-width="{width}"/>' for color, width in WATER_LINES
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw:.0f} {vh:.0f}">'
        f'<defs><path id="c" d="{coast}" fill-rule="evenodd"/></defs>'
        '<rect width="300" height="200" fill="#34444f"/>'
        '<path d="M0 66.7H300M0 133.3H300M100 0V200M200 0V200" stroke="#e9d9b4" stroke-opacity=".1" '
        'stroke-width=".6" stroke-dasharray="2 4"/>'
        f'<g fill="none" stroke-linejoin="round">{rings}</g>'
        '<use href="#c" fill="#d8c59d" stroke="#2b241d" stroke-width="1.1" stroke-linejoin="round"/>'
        f'<path d="{hachures}" fill="none" stroke="#6e5838" stroke-width="1.2" stroke-linecap="round" '
        'stroke-linejoin="round"/></svg>\n'
    )


def hero_fog(seed: int = 1337) -> str:
    """The unknown west of the hero map: location-shaped steps, rhumb lines, a fog label."""
    rng = random.Random(seed)
    noise = Noise(seed)
    vw, vh = 1000, 600
    rows = 60
    points: list[tuple[float, float]] = [(0, 0)]
    for i in range(rows + 1):
        y = vh * i / rows
        x = 262 + 46 * noise(0.5, y / 140) + 12 * math.sin(y / 47) + rng.uniform(-6, 6)
        x = round(x / 7) * 7
        points += [(x, y), (x, min(vh, y + vh / rows))]
    points.append((0, vh))
    edge = "M" + "L".join(f"{x:.0f},{y:.0f}" for x, y in points) + "Z"
    rhumbs: list[str] = []
    for cx, cy in ((118, 300), (30, 70), (190, 570)):
        for k in range(16):
            a = 2 * math.pi * k / 16
            rhumbs.append(f"M{cx},{cy}L{cx + math.cos(a) * 900:.0f},{cy + math.sin(a) * 900:.0f}")
    return (
        f'<svg class="fog" viewBox="0 0 {vw} {vh}" preserveAspectRatio="none" aria-hidden="true">'
        f'<defs><clipPath id="fogclip"><path d="{edge}"/></clipPath></defs>'
        f'<path class="fog-fill" d="{edge}"/>'
        f'<g clip-path="url(#fogclip)"><path class="fog-rhumb" d="{"".join(rhumbs)}"/>'
        '<g class="fog-node"><circle cx="118" cy="300" r="22"/><circle cx="118" cy="300" r="15"/></g></g>'
        f'<path class="fog-edge" d="{edge}"/>'
        "</svg>"
    )


def rhumb_background() -> str:
    """Rhumb lines from compass nodes, as on the game's Terra Incognita, for page backgrounds."""
    lines: list[str] = []
    for cx, cy in ((160, 120), (1180, 60), (760, 520)):
        for k in range(32):
            a = 2 * math.pi * k / 32
            lines.append(f"M{cx} {cy}L{cx + math.cos(a) * 1600:.0f} {cy + math.sin(a) * 1600:.0f}")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 600" preserveAspectRatio="xMidYMid slice">'
        f'<path d="{"".join(lines)}" fill="none" stroke="#e9d9b4" stroke-width=".7" opacity=".09"/>'
        '<g fill="none" stroke="#e9d9b4" opacity=".14"><circle cx="160" cy="120" r="26"/><circle cx="160" cy="120" r="18"/>'
        '<circle cx="1180" cy="60" r="26"/><circle cx="760" cy="520" r="26"/></g></svg>'
    )


# --- the pictures ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Picture:
    name: str
    source: str
    box: tuple[int, int, int, int]  # crop in the source's pixels
    widths: tuple[int, ...]

    @property
    def ratio(self) -> float:
        return (self.box[2] - self.box[0]) / (self.box[3] - self.box[1])

    def height(self, width: int) -> int:
        return round(width / self.ratio)


PICTURES: Final[dict[str, Picture]] = {
    "hero": Picture(
        "hero", "01-procedural-continents.png", (440, 0, 2400, 1180), (720, 1100, 1560)
    ),
    "covered": Picture("covered", "02-lobby-terra-incognita.png", (0, 0, 2520, 1260), (640, 1100)),
    "shown": Picture("shown", "05-native-realms.png", (520, 60, 2560, 1080), (640, 1100)),
}
OG_IMAGE: Final = ("01-procedural-continents.png", (380, 0, 2560, 1145))  # 1.904 ≈ 1200×630


def picture_html(key: str, alt: str, sizes: str, cls: str = "") -> str:
    pic = PICTURES[key]
    srcset = ", ".join(f"/assets/{pic.name}-{w}.webp {w}w" for w in pic.widths)
    w = pic.widths[0]
    priority = 'fetchpriority="high"' if key == "hero" else 'loading="lazy"'
    return (
        f'<img class="{cls}" src="/assets/{pic.name}-{pic.widths[-1]}.webp" srcset="{srcset}" sizes="{sizes}" '
        f'width="{w}" height="{pic.height(w)}" alt="{alt}" decoding="async" {priority}>'
    )


def make_pictures() -> None:
    from PIL import Image

    out = PUBLIC / "assets"
    out.mkdir(parents=True, exist_ok=True)
    for pic in PICTURES.values():
        with Image.open(SHOWCASE / pic.source) as im:
            crop = im.convert("RGB").crop(pic.box)
            for w in pic.widths:
                crop.resize((w, pic.height(w)), Image.Resampling.LANCZOS).save(
                    out / f"{pic.name}-{w}.webp", "WEBP", quality=80, method=6
                )
    source, box = OG_IMAGE
    with Image.open(SHOWCASE / source) as im:
        im.convert("RGB").crop(box).resize((1200, 630), Image.Resampling.LANCZOS).save(
            out / "og.jpg", "JPEG", quality=82, optimize=True, progressive=True
        )


# --- page parts -----------------------------------------------------------------------------


def lang_menu(page: Page) -> str:
    current = ' aria-current="true"'
    items = "".join(
        (
            f'<li><a href="/{lang.slug}/" hreflang="{lang.tag}" lang="{lang.tag}" data-lang="{lang.slug}"'
            f"{current if lang == page.language else ''}>{esc(lang.name)}</a></li>"
        )
        for lang in LANGUAGES
    )
    return (
        '<details class="lang">'
        f'<summary aria-label="{page.plain("meta.language")}">{icon("globe")}<span>{esc(page.language.name)}</span></summary>'
        f"<ul>{items}</ul></details>"
    )


def topbar(page: Page) -> str:
    links = "".join(
        f'<a href="#{s}">{page.t(f"nav.{s}")}</a>' for s in ("start", "types", "compat", "help")
    )
    return (
        '<header class="bar"><div class="bar-in">'
        f'<a class="brand" href="/{page.language.slug}/">{COMPASS}<span>Random New World</span></a>'
        f'<nav class="bar-nav" aria-label="{page.plain("meta.contents")}">{links}</nav>'
        f"{lang_menu(page)}"
        f'<a class="btn-plaque" href="{WORKSHOP}">{page.t("nav.workshop")}</a>'
        "</div></header>"
    )


def hero(page: Page) -> str:
    facts = "".join(
        f"<li>{page.t(f'hero.{k}')}</li>" for k in ("fact_generator", "fact_game", "fact_languages")
    )
    picture = picture_html(
        "hero", page.plain("meta.image_hero"), "(min-width: 1080px) 640px, 100vw", "chart-img"
    )
    return (
        '<section class="hero"><div class="hero-in">'
        '<div class="hero-text">'
        f'<p class="kicker">{page.h("hero.kicker")}</p>'
        '<h1 class="brand-title">Random New World</h1>'
        f'<p class="lead">{page.t("hero.lead")}</p>'
        f'<ul class="facts">{facts}</ul>'
        '<p class="cta">'
        f'<a class="btn-paper" href="#start">{page.t("hero.cta")}{icon("arrow", "ic ic-s")}</a>'
        f'<a class="btn-line" href="#help">{page.t("hero.cta_help")}</a>'
        "</p></div>"
        '<figure class="chart"><div class="chart-frame">'
        f"{picture}{hero_fog()}"
        '<span class="chart-label" aria-hidden="true">Terra Incognita</span>'
        '<i class="corner tl"></i><i class="corner tr"></i><i class="corner bl"></i><i class="corner br"></i>'
        "</div></figure>"
        "</div></section>"
    )


def toc(page: Page) -> str:
    items = "".join(
        f'<li><a href="#{s}"><span class="num">{ROMAN[i]}</span>{page.t(f"nav.{s}")}</a></li>'
        for i, s in enumerate(SECTIONS)
    )
    return f'<nav class="toc" aria-label="{page.plain("meta.contents")}"><ol>{items}</ol></nav>'


def section_head(page: Page, sid: str, key: str, lead: str | None = None) -> str:
    n = ROMAN[SECTIONS.index(sid)]
    out = f'<header class="sec-head"><span class="sec-num" aria-hidden="true">{n}</span><h2>{page.h(key)}</h2></header>'
    if lead:
        out += f'<p class="sec-lead">{page.t(lead)}</p>'
    return out


# The four steps show the screens the player meets: the release's own generator window, captured
# in each language by website/capture_window.mjs, and EU5's Mods & DLCs menu from an
# owner-approved screenshot (English only; the step text gives each language's words).
SCREENS: Final = ROOT / "docs" / "images" / "website"
EU5_MARKS: Final[dict[str, tuple[tuple[int, int, int, int], ...]]] = {
    "eu5-open-folder.png": ((131, 39, 288, 75),),  # Open folder of Random New World (RNW)
    "eu5-apply.png": ((5, 169, 215, 213), (579, 414, 614, 449)),  # Apply, the world's tick
}
CUT: Final = 28  # the dashed cut between the two parts of the Save and play frame, in pixels
WINDOW_BG: Final = (28, 30, 35)


def png_size(path: Path) -> tuple[int, int]:
    """Width and height from a PNG's header, so the pages need no image library."""
    header = path.read_bytes()[16:24]
    return int.from_bytes(header[:4], "big"), int.from_bytes(header[4:], "big")


def step_screen(step: int, slug: str) -> tuple[str, tuple[int, int]]:
    """The asset path and pixel size of a step's screen."""
    if step == 1:
        return "/assets/step1.webp", png_size(SCREENS / "eu5-open-folder.png")
    if step == 4:
        return "/assets/step4.webp", png_size(SCREENS / "eu5-apply.png")
    if step == 2:
        return f"/assets/step2-{slug}.webp", png_size(SCREENS / f"window-{slug}-world.png")
    top = png_size(SCREENS / f"window-{slug}-save.png")
    bottom = png_size(SCREENS / f"window-{slug}-generate.png")
    return f"/assets/step3-{slug}.webp", (top[0], top[1] + CUT + bottom[1])


def make_screens() -> None:
    from PIL import Image, ImageDraw

    out = PUBLIC / "assets"
    mark = (224, 122, 85)
    for name, boxes in EU5_MARKS.items():
        with Image.open(SCREENS / name) as im:
            frame = im.convert("RGB")
        draw = ImageDraw.Draw(frame)
        for box in boxes:
            draw.rounded_rectangle(box, radius=6, outline=mark, width=4)
        step = 1 if name == "eu5-open-folder.png" else 4
        frame.save(out / f"step{step}.webp", "WEBP", quality=84, method=6)
    for language in LANGUAGES:
        slug = language.slug
        with Image.open(SCREENS / f"window-{slug}-world.png") as im:
            im.convert("RGB").save(out / f"step2-{slug}.webp", "WEBP", quality=88, method=6)
        with (
            Image.open(SCREENS / f"window-{slug}-save.png") as top,
            Image.open(SCREENS / f"window-{slug}-generate.png") as bottom,
        ):
            frame = Image.new("RGB", (top.width, top.height + CUT + bottom.height), WINDOW_BG)
            frame.paste(top.convert("RGB"), (0, 0))
            frame.paste(bottom.convert("RGB"), (0, top.height + CUT))
            y = top.height + CUT // 2
        draw = ImageDraw.Draw(frame)
        for x in range(0, frame.width, 16):
            draw.line((x, y, x + 8, y), fill=(110, 116, 128), width=2)
        frame.save(out / f"step3-{slug}.webp", "WEBP", quality=88, method=6)


def step_figure(page: Page, step: int) -> str:
    src, (width, height) = step_screen(step, page.language.slug)
    cls = "step-shot game" if step in {1, 4} else "step-shot window"
    return (
        f'<figure class="{cls}" aria-hidden="true">'
        f'<img src="{src}" width="{width // 2}" height="{height // 2}" alt="" loading="lazy" decoding="async">'
        "</figure>"
    )


def section_start(page: Page) -> str:
    legs: list[str] = []
    for i in range(1, 5):
        note_key = f"start.{i}_note"
        note = ""
        if note_key in page.texts:
            cls = "note warn" if i == 3 else "note"
            note = f'<p class="{cls}">{page.t(note_key)}</p>'
        leg = (
            '<li class="leg">'
            f'<span class="mark" aria-hidden="true"><span>{i}</span></span>'
            f'<div class="leg-body"><h3>{page.h(f"start.{i}_title")}</h3><p>{page.t(f"start.{i}_text")}</p>{note}</div>'
            f"{step_figure(page, i)}</li>"
        )
        legs.append(leg)
    ready = (
        '<aside class="ready">'
        f"<h3>{page.h('start.ready_title')}</h3><p>{page.t('start.ready_text')}</p></aside>"
    )
    return (
        '<section id="start" class="sec">'
        f"{section_head(page, 'start', 'start.title', 'start.lead')}"
        f'<ol class="course">{"".join(legs)}</ol>{ready}</section>'
    )


def section_rules(page: Page) -> str:
    icons = ("flag", "tick", "restart", "anchor")
    items = "".join(
        f"<li>{icon(icons[i - 1], 'ic ic-l')}<h3>{page.h(f'rules.{i}_title')}</h3><p>{page.t(f'rules.{i}_text')}</p></li>"
        for i in range(1, 5)
    )
    return (
        '<section id="rules" class="sec">'
        f'<div class="cartouche">{section_head(page, "rules", "rules.title", "rules.lead")}'
        f'<ul class="rules">{items}</ul></div></section>'
    )


def section_types(page: Page) -> str:
    cards = "".join(
        (
            '<li class="type">'
            f'<img class="vignette" src="/assets/world-{kind}.svg" width="300" height="200" alt="" loading="lazy">'
            f"<h3>{esc(page.ui(f'type.{kind}'))}</h3><p>{esc(page.ui(f'type.{kind}.about'))}</p></li>"
        )
        for kind in WORLD_TYPES
    )
    for kind in WORLD_TYPES:
        page.display.update(page.ui(f"type.{kind}"))
    extra = "".join(
        f"<li>{icon(ic, 'ic')}<div><b>{esc(page.ui(f'type.{kind}'))}</b> {esc(page.ui(f'type.{kind}.about'))}</div></li>"
        for kind, ic in (("random", "dice"), ("chaos", "storm"))
    )
    return (
        '<section id="types" class="sec">'
        f"{section_head(page, 'types', 'types.title', 'types.lead')}"
        f'<ul class="types">{cards}</ul>'
        f'<ul class="types-extra">{extra}</ul>'
        f'<p class="aside-note">{page.t("types.wall_note")}</p></section>'
    )


def legend(page: Page, prefix: str, keys: tuple[str, ...]) -> str:
    items = "".join(
        f'<div class="lg"><dt>{page.h(f"{prefix}.{k}_title")}</dt><dd>{page.t(f"{prefix}.{k}_text")}</dd></div>'
        for k in keys
    )
    return f'<dl class="legend">{items}</dl>'


def section_settings(page: Page) -> str:
    return (
        '<section id="settings" class="sec">'
        f"{section_head(page, 'settings', 'settings.title', 'settings.lead')}"
        f"{legend(page, 'settings', ('seed', 'sketch', 'draw', 'ocean', 'peoples', 'resources'))}"
        "</section>"
    )


def section_hidden(page: Page) -> str:
    covered = picture_html(
        "covered", page.plain("hidden.covered"), "(min-width: 900px) 460px, 100vw"
    )
    shown = picture_html("shown", page.plain("hidden.shown"), "(min-width: 900px) 460px, 100vw")
    return (
        '<section id="hidden" class="sec">'
        f"{section_head(page, 'hidden', 'hidden.title', 'hidden.lead')}"
        '<div class="pair">'
        f'<figure class="shot">{covered}<figcaption>{page.t("hidden.covered")}</figcaption></figure>'
        f'<figure class="shot">{shown}<figcaption>{page.t("hidden.shown")}</figcaption></figure>'
        "</div>"
        '<dl class="legend two">'
        f'<div class="lg"><dt><span class="ui">{esc(page.ui("reveal_world"))}</span></dt><dd>{page.t("hidden.reveal_text")}</dd></div>'
        f'<div class="lg"><dt><span class="ui">{esc(page.ui("show_new_world"))}</span></dt><dd>{page.t("hidden.show_text")}</dd></div>'
        "</dl>"
        f'<p class="aside-note">{page.t("hidden.atlas")}</p></section>'
    )


def section_library(page: Page) -> str:
    return (
        '<section id="library" class="sec">'
        f"{section_head(page, 'library', 'library.title', 'library.lead')}"
        f"{legend(page, 'library', ('versions', 'queue', 'share', 'move', 'clean'))}"
        "</section>"
    )


COMPAT: Final[tuple[tuple[str, str], ...]] = (
    ("game", "if"),
    ("saves", "if"),
    ("pillars", "ok"),
    ("refined", "ok"),
    ("multiplayer", "ok"),
    ("ironman", "ok"),
    ("maps", "no"),
    ("system", "if"),
)


def section_compat(page: Page) -> str:
    rows = "".join(
        (
            f'<div class="cp cp-{state}"><dt>{icon(state, "ic mark-" + state)}<span>{page.h(f"compat.{k}")}</span></dt>'
            f"<dd>{page.t(f'compat.{k}_text')}</dd></div>"
        )
        for k, state in COMPAT
    )
    return (
        '<section id="compat" class="sec">'
        f"{section_head(page, 'compat', 'compat.title')}"
        f'<dl class="compat">{rows}</dl></section>'
    )


HELP: Final[tuple[str, ...]] = (
    "found",
    "memory",
    "blank",
    "classic",
    "error",
    "blocked",
    "picture",
    "library",
    "bug",
)


def section_help(page: Page) -> str:
    items = "".join(
        f'<details class="qa" id="help-{k}"><summary>{page.t(f"help.{k}_q")}</summary><div class="qa-a"><p>{page.t(f"help.{k}_a")}</p></div></details>'
        for k in HELP
    )
    return (
        '<section id="help" class="sec">'
        f"{section_head(page, 'help', 'help.title')}"
        f'<div class="faq">{items}</div></section>'
    )


def footer(page: Page) -> str:
    links = (
        (WORKSHOP, "footer.workshop"),
        (f"{REPO}/releases", "footer.downloads"),
        (f"{REPO}/issues", "footer.bugs"),
        (f"{REPO}/blob/main/docs/generator-guide.md", "footer.technical"),
        (REPO, "footer.source"),
        (KOFI, "footer.kofi"),
    )
    items = "".join(f'<li><a href="{esc(url)}">{page.t(key)}</a></li>' for url, key in links)
    return (
        '<footer class="foot"><div class="foot-in">'
        f'<div class="foot-brand">{COMPASS}<span>Random New World</span></div>'
        f'<ul class="foot-links">{items}</ul>'
        f'<p class="small">{page.t("footer.version")} {page.t("footer.license")}</p>'
        "</div></footer>"
    )


# --- documents --------------------------------------------------------------------------------

FONT_SLOT: Final = "<!--fonts-->"


def head(page: Page, css: str, js: str) -> str:
    lang = page.language
    alternates = (
        "".join(
            f'<link rel="alternate" hreflang="{other.tag}" href="{SITE}/{other.slug}/">'
            for other in LANGUAGES
        )
        + f'<link rel="alternate" hreflang="x-default" href="{SITE}/">'
    )
    title = page.plain("meta.title")
    description = page.plain("meta.description")
    return (
        "<!doctype html>"
        f'<html lang="{lang.tag}" class="s-{lang.script}">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title}</title>"
        f'<meta name="description" content="{description}">'
        f'<link rel="canonical" href="{SITE}/{lang.slug}/">{alternates}'
        '<meta property="og:type" content="website">'
        f'<meta property="og:title" content="{title}">'
        f'<meta property="og:description" content="{description}">'
        f'<meta property="og:url" content="{SITE}/{lang.slug}/">'
        f'<meta property="og:image" content="{SITE}/assets/og.jpg">'
        f'<meta property="og:locale" content="{lang.tag.replace("-", "_")}">'
        '<meta name="twitter:card" content="summary_large_image">'
        '<meta name="theme-color" content="#2c2621">'
        '<meta name="color-scheme" content="dark">'
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
        f"{FONT_SLOT}"
        f'<link rel="stylesheet" href="/assets/site.css?v={css}">'
        f'<script src="/assets/site.js?v={js}" defer></script>'
        "</head>"
    )


def render_page(page: Page, css: str, js: str) -> str:
    body = "".join(
        (
            section_start(page),
            section_rules(page),
            section_types(page),
            section_settings(page),
            section_hidden(page),
            section_library(page),
            section_compat(page),
            section_help(page),
        )
    )
    return (
        head(page, css, js)
        + "<body>"
        + f'<a class="skip" href="#start">{page.t("meta.skip")}</a>'
        + topbar(page)
        + '<main id="main">'
        + hero(page)
        + f'<div class="layout">{toc(page)}<div class="sections">{body}</div></div>'
        + "</main>"
        + footer(page)
        + "</body></html>\n"
    )


def brand_css(manifest: dict[str, dict[str, str]]) -> str:
    """The title face alone, for the pages that choose a language."""
    chars = "".join(sorted(set(BRAND_TEXT)))
    name = font_name(BRAND, "", chars)
    if name not in manifest:
        message = f"font {name} is not built; run the full build"
        raise BuildError(message)
    return (
        f'<link rel="preload" href="/fonts/{name}" as="font" type="font/woff2" crossorigin>'
        f"<style>@font-face{{font-family:'{BRAND.family}';src:url(/fonts/{name}) format('woff2');"
        f"font-weight:{BRAND.weight};font-style:normal;font-display:swap}}</style>"
    )


def render_root(css: str, fonts: str) -> str:
    links = "".join(
        f'<li><a href="/{lang.slug}/" hreflang="{lang.tag}" lang="{lang.tag}">{esc(lang.name)}</a></li>'
        for lang in LANGUAGES
    )
    alternates = "".join(
        f'<link rel="alternate" hreflang="{lang.tag}" href="{SITE}/{lang.slug}/">'
        for lang in LANGUAGES
    )
    slugs = json.dumps({lang.tag.split("-")[0].lower(): lang.slug for lang in LANGUAGES})
    return (
        '<!doctype html><html lang="en" class="s-latin root"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Random New World · Guide</title>"
        '<meta name="description" content="The player\'s guide to Random New World for Europa Universalis V, in eleven languages.">'
        f'<link rel="canonical" href="{SITE}/">{alternates}'
        '<meta name="theme-color" content="#2c2621"><meta name="color-scheme" content="dark">'
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
        f"{fonts}"
        f'<link rel="stylesheet" href="/assets/site.css?v={css}">'
        f"<script src=\"/assets/lang.js?v={asset_hash(SRC / 'lang.js')}\" data-slugs='{slugs}'></script>"
        "</head><body>"
        f'<main class="pick"><div class="pick-in">{COMPASS}<h1 class="brand-title">Random New World</h1>'
        f'<ul class="pick-list">{links}</ul></div></main>'
        "</body></html>\n"
    )


def render_404(css: str, fonts: str) -> str:
    links = "".join(
        f'<li><a href="/{lang.slug}/" lang="{lang.tag}">{esc(lang.name)}</a></li>'
        for lang in LANGUAGES
    )
    return (
        '<!doctype html><html lang="en" class="s-latin root"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Terra Incognita · Random New World</title><meta name="robots" content="noindex">'
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">'
        f"{fonts}"
        f'<link rel="stylesheet" href="/assets/site.css?v={css}"></head><body>'
        f'<main class="pick"><div class="pick-in">{COMPASS}<h1 class="brand-title">Terra Incognita</h1>'
        '<p class="pick-note">404</p>'
        f'<ul class="pick-list">{links}</ul></div></main></body></html>\n'
    )


# ---------------------------------------------------------------------------------------------
# Fonts


@dataclass(frozen=True)
class Face:
    family: str  # CSS family
    pattern: str  # fc-match pattern of the source font
    weight: int
    role: str  # display | brand | sans
    instance: int | None = None  # wght of a variable source


BRAND: Final = Face("RNW Brand", "Cinzel", 700, "brand", instance=700)
SANS: Final = (
    Face("RNW Sans", "Noto Sans", 400, "sans"),
    Face("RNW Sans", "Noto Sans:semibold", 600, "sans"),
)
DISPLAY: Final[dict[str, Face]] = {
    "latin": Face("RNW Display", "Cinzel", 600, "display", instance=600),
    "cyrillic": Face("RNW Display", "Noto Serif:semibold", 600, "display"),
    "ja": Face("RNW Display", "Noto Serif CJK JP:bold", 700, "display"),
    "ko": Face("RNW Display", "Noto Serif CJK KR:bold", 700, "display"),
    "zh": Face("RNW Display", "Noto Serif CJK SC:bold", 700, "display"),
}
BRAND_TEXT: Final = "Random New World Terra Incognita RNW 0123456789 IVX"
CJK: Final = re.compile(r"[⺀-鿿가-힯豈-﫿＀-￯　-〿]")
BASIC: Final = "".join(chr(c) for c in range(0x20, 0x7F)) + "–—‘’“”…·×→←↓◆"


def faces(language: Language) -> tuple[Face, ...]:
    return (BRAND, *SANS, DISPLAY[language.script])


def visible_text(document: str) -> str:
    """The characters a page shows: element text and the alt/aria words."""
    body = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", document, flags=re.DOTALL)
    attrs = " ".join(re.findall(r'(?:alt|aria-label|title)="([^"]*)"', body))
    text = re.sub(r"<[^>]+>", " ", body)
    return html.unescape(text + " " + attrs)


def needed(face: Face, page: Page, document: str) -> str:
    if face.role == "brand":
        chars = set(BRAND_TEXT)
    elif face.role == "display":
        chars = set(page.display) | set(BASIC)
    else:
        chars = {c for c in visible_text(document) if not CJK.match(c)} | set(BASIC)
    chars.discard("\n")
    return "".join(sorted(chars))


def font_name(face: Face, slug: str, chars: str) -> str:
    digest = hashlib.sha256(f"{face}|{chars}".encode()).hexdigest()[:10]
    stem = re.sub(r"[^a-z0-9]+", "-", face.family.lower()).strip("-")
    scope = "all" if face.role == "brand" else slug
    return f"{stem}-{face.weight}.{scope}.{digest}.woff2"


def font_file(pattern: str) -> tuple[Path, int]:
    """The installed file and collection index of a font; refused when fontconfig substitutes."""
    found = subprocess.run(
        ["fc-match", "-f", "%{family}|%{file}|%{index}", pattern],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    families, file, index = found.split("|")
    family = pattern.split(":", maxsplit=1)[0]
    if family not in families.split(","):
        message = f"font not installed: {family} (fontconfig offers {families})"
        raise BuildError(message)
    return Path(file), int(index)


def subset(face: Face, chars: str, target: Path) -> dict[str, str]:
    from fontsubset import subset_font

    source, index = font_file(face.pattern)
    return {"source": source.name, **subset_font(source, index, face.instance, chars, target)}


def font_css(
    language: Language, manifest: dict[str, dict[str, str]], page: Page, document: str
) -> str:
    rules: list[str] = []
    preload: list[str] = []
    for face in faces(language):
        chars = needed(face, page, document)
        name = font_name(face, language.slug, chars)
        if name not in manifest:
            message = f"font {name} is not built; run the full build"
            raise BuildError(message)
        rule = (
            f"@font-face{{font-family:'{face.family}';src:url(/fonts/{name}) format('woff2');"
            f"font-weight:{face.weight};font-style:normal;font-display:swap}}"
        )
        rules.append(rule)
        if face.role != "sans" or face.weight == 400:
            preload.append(
                f'<link rel="preload" href="/fonts/{name}" as="font" type="font/woff2" crossorigin>'
            )
    return "".join(preload) + f"<style>{''.join(rules)}</style>"


# ---------------------------------------------------------------------------------------------
# The build


def asset_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


def pages(only: frozenset[str] | None = None) -> list[tuple[Page, str]]:
    """Every language's page (or those in ``only``), rendered with the font slot still open."""
    problems = content_problems(only)
    if problems:
        raise BuildError("translations are not ready:\n  " + "\n  ".join(problems))
    english_window = window_english()
    css, js = asset_hash(SRC / "site.css"), asset_hash(SRC / "site.js")
    out: list[tuple[Page, str]] = []
    for language in LANGUAGES:
        if only is not None and language.game not in only:
            continue
        texts, _ = read_content(language.game)
        page = Page(language, texts, window_terms(language.game, english_window))
        out.append((page, render_page(page, css, js)))
    return out


def render(
    manifest: dict[str, dict[str, str]], only: frozenset[str] | None = None
) -> dict[str, str]:
    """Every generated text file of the site, by its path under public/."""
    files: dict[str, str] = {}
    for page, document in pages(only):
        files[f"{page.language.slug}/index.html"] = document.replace(
            FONT_SLOT, font_css(page.language, manifest, page, document)
        )
    css = asset_hash(SRC / "site.css")
    fonts = brand_css(manifest)
    files["index.html"] = render_root(css, fonts)
    files["404.html"] = render_404(css, fonts)
    files["assets/rhumbs.svg"] = rhumb_background() + "\n"
    for kind in WORLD_TYPES:
        files[f"assets/world-{kind}.svg"] = world_svg(kind)
    urls = "".join(f"<url><loc>{SITE}/{lang.slug}/</loc></url>" for lang in LANGUAGES)
    files["sitemap.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n'
    )
    files["robots.txt"] = f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n"
    return files


MANIFEST: Final = PUBLIC / "fonts" / "manifest.json"


def read_manifest() -> dict[str, dict[str, str]]:
    if not MANIFEST.is_file():
        return {}
    return cast("dict[str, dict[str, str]]", json.loads(MANIFEST.read_text(encoding="utf-8")))


def build_fonts(only: frozenset[str] | None = None) -> dict[str, dict[str, str]]:
    manifest: dict[str, dict[str, str]] = {}
    fonts = PUBLIC / "fonts"
    for page, document in pages(only):
        for face in faces(page.language):
            chars = needed(face, page, document)
            name = font_name(face, page.language.slug, chars)
            if name in manifest:
                continue
            info = subset(face, chars, fonts / name)
            manifest[name] = {
                **info,
                "family": face.family,
                "weight": str(face.weight),
                "chars": chars,
            }
    for stale in fonts.glob("*.woff2"):
        if stale.name not in manifest:
            stale.unlink()
    _ = MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    licence = [
        "Fonts on this site are subsets of fonts under the SIL Open Font License 1.1",
        "(https://openfontlicense.org).",
        "",
    ]
    licence += sorted(
        {f"{v['source']} ({v['version']}): {v['copyright']}" for v in manifest.values()}
    )
    _ = (fonts / "OFL.txt").write_text("\n".join(licence) + "\n", encoding="utf-8")
    return manifest


def write(files: dict[str, str]) -> None:
    for path, text in files.items():
        target = PUBLIC / path
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text(text, encoding="utf-8")
    for name in ("site.css", "site.js", "lang.js", "favicon.svg", "_headers"):
        source = SRC / name
        target = PUBLIC / ("assets" if name.endswith((".css", ".js")) else "") / name
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = shutil.copyfile(source, target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    _ = parser.add_argument(
        "--html", action="store_true", help="pages only; fonts and pictures as recorded"
    )
    _ = parser.add_argument(
        "--only", help="comma-separated languages, for a draft; the release builds all"
    )
    args = parser.parse_args(argv)
    only_arg = cast("str | None", args.only)
    only = frozenset(only_arg.split(",")) if only_arg else None
    try:
        if cast("bool", args.html):
            manifest = read_manifest()
        else:
            make_pictures()
            make_screens()
            manifest = build_fonts(only)
        write(render(manifest, only))
    except BuildError as error:
        print(f"website: {error}", file=sys.stderr)
        return 1
    count = len(only) if only else len(LANGUAGES)
    print(f"website: built {count} languages into {PUBLIC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
