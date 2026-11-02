"""RNW Workshop page art: section banners and link buttons in the Terra Incognita look.

Flat vector: the lobby cover's fog brown, the caption parchment and rhumb lines fanning from a
compass node. Writes one PNG per picture into ``w/`` at the repository root, rendered through
``rsvg-convert``. The Workshop text pays for every byte of an image URL, so the path is as short
as it can be: ``https://raw.githubusercontent.com/Sir-Starch/eu5-random-new-world/main/w/en1.png``,
a flat folder, two-letter language code plus a one-character picture id. Steam shows pictures
at their own size and only shrinks those wider than its 630 px column, so section banners and the
plaque are drawn at 2x and the buttons at the size they are shown, ``BUTTON_PX``. Steam also caches every picture by its URL, so a redrawn picture needs a new id or it
keeps showing the old one (the button ids were a-f, g-j, now m-p; take the next unused character).

    ids  0 divider | 1 new world | 2 peoples | 3 make it yours | 4 getting started
         5 before you play | 6 compatibility | 7 guides and downloads
         m guide | n get | o bugs | p GitHub | k Ko-fi plaque
    code en ru pt fr de es pl tr ja ko zh

    python docs/images/workshop/make_banners.py            # PNG into w/
    python docs/images/workshop/make_banners.py --svg DIR  # also keep the SVG sources

Lettering is Cinzel (SIL OFL) for Latin text, Noto Serif Bold for Cyrillic and Noto Serif CJK Bold
for Japanese, Korean and Chinese; all must be installed (``fc-match`` finds them). Add a language by
adding its copy to ``TEXT``, a font to ``FONTS`` and a code to ``CODES``.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

FOG = "#4d443d"  # Terra Incognita fog (sampled from the lobby cover)
FOG_DEEP = "#3b332d"
FOG_LIGHT = "#5a5047"
PAPER = "#dac7a0"  # caption parchment
PAPER_DEEP = "#cbb68f"
INK = "#3a2f26"
GOLD = "#e9d9b4"  # lettering on fog


# Per-script lettering: Cinzel has no Cyrillic, so Russian uses Noto Serif Bold (the project's family).
def _font_file(pattern: str) -> str:
    found = subprocess.run(
        ["fc-match", "-f", "%{file}", pattern], capture_output=True, text=True, check=True
    ).stdout
    if not found:
        msg = f"font not installed: {pattern}"
        raise SystemExit(msg)
    return found


def _spec(css: str, pattern: str, track: int, **extra) -> dict:
    return {
        "css": css,
        "file": _font_file(pattern),
        "axes": None,
        "index": 0,
        "track": track,
        **extra,
    }


NOTE_ITALIC = {
    **_spec("'Noto Serif', serif", "Noto Serif:italic", 0),
    "style": "italic",
    "weight": 400,
}
LATIN = {
    **_spec("Cinzel, 'Noto Serif', serif", "Cinzel:bold", 7),
    "axes": [700],
    "note": NOTE_ITALIC,
}
CYRILLIC = {**_spec("'Noto Serif', serif", "Noto Serif:bold", 5), "note": NOTE_ITALIC}


def _cjk(family: str) -> dict:
    note = {**_spec(f"'{family}', serif", f"{family}:medium", 0), "style": "normal", "weight": 500}
    return {**_spec(f"'{family}', serif", f"{family}:bold", 4), "note": note}


FONTS = {
    "english": LATIN,
    "braz_por": LATIN,
    "french": LATIN,
    "german": LATIN,
    "polish": LATIN,
    "spanish": LATIN,
    "turkish": LATIN,
    "russian": CYRILLIC,
    "japanese": _cjk("Noto Serif CJK JP"),
    "korean": _cjk("Noto Serif CJK KR"),
    "simp_chinese": _cjk("Noto Serif CJK SC"),
}


def text_width(text: str, size: float, tracking: float, font_spec: dict) -> float:
    from PIL import ImageFont

    font = ImageFont.truetype(font_spec["file"], int(size), index=font_spec["index"])
    if font_spec["axes"]:
        font.set_variation_by_axes(font_spec["axes"])
    plain = text.replace("&amp;", "&")
    return font.getlength(plain) * size / int(size) + tracking * (len(plain) - 1)


def fit(text: str, size: float, tracking: float, room: float, font_spec: dict, floor: float = 20):
    while text_width(text, size, tracking, font_spec) > room and size > floor:
        size -= 1
        tracking = max(2.0, tracking - 0.15)
    return size, tracking


def rhumb(cx: float, cy: float, n: int = 32, opacity: float = 0.13) -> str:
    """Rhumb lines fanning out of a compass node, clipped to the banner."""
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x2 = cx + math.cos(a) * 3000
        y2 = cy + math.sin(a) * 3000
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    return (
        f'<g stroke="{GOLD}" stroke-width="1.4" opacity="{opacity}" fill="none">'
        + "".join(out)
        + "</g>"
    )


def star(cx, cy, r, color, long=1.0, short=0.55, width=0.16):
    """Eight-point compass rose as one filled path."""
    pts = []
    for i in range(8):
        a = -math.pi / 2 + i * math.pi / 4
        rr = r * (long if i % 2 == 0 else short)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        b = a + math.pi / 8
        pts.append((cx + math.cos(b) * r * width, cy + math.sin(b) * r * width))
    d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"
    return f'<path d="{d}" fill="{color}"/>'


# ---- pictograms, drawn in a 40x40 box centred on (0,0), stroke style set by caller -------------


def icon_globe(c):
    return (
        f'<circle r="15" fill="none" stroke="{c}" stroke-width="2"/>'
        f'<ellipse rx="6.5" ry="15" fill="none" stroke="{c}" stroke-width="2"/>'
        f'<path d="M -15 0 H 15 M -13 -7.5 H 13 M -13 7.5 H 13" stroke="{c}" stroke-width="2" fill="none"/>'
    )


def icon_compass(c):
    return (
        star(0, 0, 23, c, long=1.0, short=0.55, width=0.24)
        + f'<circle r="3" fill="none" stroke="{c}" stroke-width="1.6"/>'
    )


def icon_anchor(c):
    return (
        f'<g fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cy="-12.5" r="3.2"/><path d="M 0 -9 V 15 M -7 -4 H 7"/>'
        '<path d="M -14 4 Q -12 14 0 15 Q 12 14 14 4"/><path d="M -14 4 l -3 -3.5 M 14 4 l 3 -3.5"/></g>'
    )


def icon_chart(c):
    # folded sea chart: three panels
    return (
        f'<g fill="none" stroke="{c}" stroke-width="2.2" stroke-linejoin="round">'
        '<path d="M -17 -11 L -6 -15 L 6 -11 L 17 -15 V 11 L 6 15 L -6 11 L -17 15 Z"/>'
        '<path d="M -6 -15 V 11 M 6 -11 V 15"/></g>'
    )


def icon_warn(c):
    return (
        f'<g fill="none" stroke="{c}" stroke-width="2.2" stroke-linejoin="round">'
        '<path d="M 0 -17 L 16 0 L 0 17 L -16 0 Z"/></g>'
        f'<path d="M 0 -8 V 3" stroke="{c}" stroke-width="2.8" stroke-linecap="round"/>'
        f'<circle cy="8" r="1.9" fill="{c}"/>'
    )


def icon_download(c):
    return (
        f'<g fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M 0 -15 V 6 M -8 -2 L 0 6 L 8 -2"/><path d="M -14 13 H 14"/></g>'
    )


def icon_flag(c):
    return (
        f'<g fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M -9 16 V -15"/></g>'
        f'<path d="M -9 -15 L 14 -9 L -9 -2 Z" fill="{c}"/>'
    )


def icon_code(c):
    return (
        f'<g fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M -8 -10 L -17 0 L -8 10 M 8 -10 L 17 0 L 8 10 M 3 -14 L -3 14"/></g>'
    )


def icon_heart(c):
    return f'<path d="M 0 15 C -20 1 -13 -14 0 -6 C 13 -14 20 1 0 15 Z" fill="none" stroke="{c}" stroke-width="2.4" stroke-linejoin="round"/>'


# Brand marks: Simple Icons 16.31.0 (CC0-1.0), https://github.com/simple-icons/simple-icons. The marks
# themselves belong to GitHub and Ko-fi; they only label links to those services.
GITHUB_PATH = "M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
KOFI_PATH = "M11.351 2.715c-2.7 0-4.986.025-6.83.26C2.078 3.285 0 5.154 0 8.61c0 3.506.182 6.13 1.585 8.493 1.584 2.701 4.233 4.182 7.662 4.182h.83c4.209 0 6.494-2.234 7.637-4a9.5 9.5 0 0 0 1.091-2.338C21.792 14.688 24 12.22 24 9.208v-.415c0-3.247-2.13-5.507-5.792-5.87-1.558-.156-2.65-.208-6.857-.208m0 1.947c4.208 0 5.09.052 6.571.182 2.624.311 4.13 1.584 4.13 4v.39c0 2.156-1.792 3.844-3.87 3.844h-.935l-.156.649c-.208 1.013-.597 1.818-1.039 2.546-.909 1.428-2.545 3.064-5.922 3.064h-.805c-2.571 0-4.831-.883-6.078-3.195-1.09-2-1.298-4.155-1.298-7.506 0-2.181.857-3.402 3.012-3.714 1.533-.233 3.559-.26 6.39-.26m6.547 2.287c-.416 0-.65.234-.65.546v2.935c0 .311.234.545.65.545 1.324 0 2.051-.754 2.051-2s-.727-2.026-2.052-2.026m-10.39.182c-1.818 0-3.013 1.48-3.013 3.142 0 1.533.858 2.857 1.949 3.897.727.701 1.87 1.429 2.649 1.896a1.47 1.47 0 0 0 1.507 0c.78-.467 1.922-1.195 2.623-1.896 1.117-1.039 1.974-2.364 1.974-3.897 0-1.662-1.247-3.142-3.039-3.142-1.065 0-1.792.545-2.338 1.298-.493-.753-1.246-1.298-2.312-1.298"


def brand(path: str, c: str, size: float = 34):
    s = size / 24
    return f'<path transform="scale({s:.3f}) translate(-12 -12)" d="{path}" fill="{c}"/>'


def icon_github(c):
    return brand(GITHUB_PATH, c, 36)


def icon_kofi(c):
    return brand(KOFI_PATH, c, 38)


def icon_sun(c):
    rays = "".join(
        f'<line x1="{math.cos(a) * 11:.1f}" y1="{math.sin(a) * 11:.1f}" x2="{math.cos(a) * 17:.1f}" y2="{math.sin(a) * 17:.1f}"/>'
        for a in (i * math.pi / 6 for i in range(12))
    )
    return f'<g fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round"><circle r="6.5"/>{rays}</g>'


def icon_sliders(c):
    return (
        f'<g fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round">'
        '<path d="M -16 -9 H 16 M -16 0 H 16 M -16 9 H 16"/></g>'
        f'<g fill="{c}" stroke="none"><circle cx="-7" cy="-9" r="4"/><circle cx="8" cy="0" r="4"/><circle cx="-3" cy="9" r="4"/></g>'
    )


def icon_link(c):
    return (
        f'<g fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round">'
        '<rect x="-17" y="-7" width="19" height="14" rx="7" transform="rotate(-30)"/>'
        '<rect x="-2" y="-7" width="19" height="14" rx="7" transform="rotate(-30)"/></g>'
    )


ICONS = {
    "globe": icon_globe,
    "compass": icon_compass,
    "anchor": icon_anchor,
    "chart": icon_chart,
    "warn": icon_warn,
    "download": icon_download,
    "flag": icon_flag,
    "code": icon_code,
    "heart": icon_heart,
    "github": icon_github,
    "kofi": icon_kofi,
    "sun": icon_sun,
    "sliders": icon_sliders,
    "link": icon_link,
}


def banner(
    title: str, icon: str, font_spec: dict, w: int = 1260, h: int = 100, size: int = 44
) -> str:
    cx, cy = 74, h / 2
    size, tracking = fit(title, size, font_spec["track"], w - 148 - 96, font_spec)
    chamfer = 12
    outer = (
        f"M {chamfer},0 H {w - chamfer} L {w},{chamfer} V {h - chamfer} L {w - chamfer},{h} "
        f"H {chamfer} L 0,{h - chamfer} V {chamfer} Z"
    )
    m = 7
    inner = (
        f"M {chamfer + m},{m} H {w - chamfer - m} L {w - m},{chamfer + m} V {h - chamfer - m} "
        f"L {w - chamfer - m},{h - m} H {chamfer + m} L {m},{h - chamfer - m} V {chamfer + m} Z"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<title>{title}</title>
<defs>
 <linearGradient id="bg" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="{FOG_LIGHT}"/><stop offset="0.55" stop-color="{FOG}"/><stop offset="1" stop-color="{FOG_DEEP}"/></linearGradient>
 <clipPath id="cut"><path d="{outer}"/></clipPath>
</defs>
<path d="{outer}" fill="url(#bg)"/>
<g clip-path="url(#cut)">
 {rhumb(cx, cy)}
 {rhumb(w - 70, cy, n=32, opacity=0.08)}
</g>
<path d="{inner}" fill="none" stroke="{GOLD}" stroke-width="1.6" opacity="0.5"/>
<path d="{outer}" fill="none" stroke="{GOLD}" stroke-width="1.6" opacity="0.28"/>
<g transform="translate({cx} {cy})">
 <circle r="34" fill="{FOG_DEEP}" opacity="0.9"/>
 <circle r="34" fill="none" stroke="{GOLD}" stroke-width="1.6" opacity="0.7"/>
 <circle r="29" fill="none" stroke="{GOLD}" stroke-width="1" opacity="0.35"/>
 <g transform="scale(1.12)">{ICONS[icon](GOLD)}</g>
</g>
<path d="M {w - 70},{cy - 9} l 9,9 l -9,9 l -9,-9 Z" fill="{GOLD}" opacity="0.55"/>
<g font-family="{font_spec["css"]}" font-weight="700" font-size="{size}" letter-spacing="{tracking:.1f}" fill="{GOLD}">
 <text x="148" y="{cy + size * 0.36:.1f}" fill="#000" opacity="0.35" dx="2" dy="2">{title}</text>
 <text x="148" y="{cy + size * 0.36:.1f}">{title}</text>
</g>
</svg>
"""


BTN_W, BTN_H = 296, 88  # drawn at 2x, shown at BUTTON_PX x BUTTON_PX * BTN_H / BTN_W
BTN_SIZE = 34  # largest lettering, shrunk until the longest label of a language fits
BTN_LEFT, BTN_RIGHT = 100, BTN_W - 24  # text area: right of the divider, inside the frame


def button_size(label: str, font_spec: dict) -> int:
    return fit(label, BTN_SIZE, font_spec["track"] - 4, BTN_RIGHT - BTN_LEFT, font_spec, floor=14)[
        0
    ]


def button(label: str, icon: str, font_spec: dict, size: int) -> str:
    """Small link button. ``size`` is shared by all buttons of a language, so they look alike."""
    w, h = BTN_W, BTN_H
    tracking = max(2.0, font_spec["track"] - 4 - 0.15 * (BTN_SIZE - size))
    ch, m = 10, 6
    outer = f"M {ch},0 H {w - ch} L {w},{ch} V {h - ch} L {w - ch},{h} H {ch} L 0,{h - ch} V {ch} Z"
    inner = (
        f"M {ch + m},{m} H {w - ch - m} L {w - m},{ch + m} V {h - ch - m} "
        f"L {w - ch - m},{h - m} H {ch + m} L {m},{h - ch - m} V {ch + m} Z"
    )
    cy = h / 2
    tx = BTN_LEFT + (BTN_RIGHT - BTN_LEFT - text_width(label, size, tracking, font_spec)) / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<title>{label}</title>
<defs>
 <linearGradient id="p" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#e3d2ad"/><stop offset="1" stop-color="{PAPER_DEEP}"/></linearGradient>
</defs>
<path d="{outer}" fill="url(#p)"/>
<path d="{outer}" fill="none" stroke="{FOG_DEEP}" stroke-width="3"/>
<path d="{inner}" fill="none" stroke="{INK}" stroke-width="1.6" opacity="0.55"/>
<g transform="translate(50 {cy}) scale(1.25)">{ICONS[icon](INK)}</g>
<path d="M 86,{cy - 26} V {cy + 26}" stroke="{INK}" stroke-width="1.6" opacity="0.45"/>
<g font-family="{font_spec["css"]}" font-weight="700" font-size="{size}" letter-spacing="{tracking:.1f}" fill="{INK}">
 <text x="{tx:.1f}" y="{cy + size * 0.36:.1f}">{label}</text>
</g>
</svg>
"""


def plaque(eyebrow: str, big: str, note: str, font_spec: dict, w: int = 1260, h: int = 250) -> str:
    """Large Ko-fi call to action: parchment like the buttons, rhumb lines fanning from the mark.

    Three tiers in one voice: a question, the ask, a thank-you in italic. An arrow points at the mark.
    """
    ch, m = 14, 9
    outer = f"M {ch},0 H {w - ch} L {w},{ch} V {h - ch} L {w - ch},{h} H {ch} L 0,{h - ch} V {ch} Z"
    inner = (
        f"M {ch + m},{m} H {w - ch - m} L {w - m},{ch + m} V {h - ch - m} "
        f"L {w - ch - m},{h - m} H {ch + m} L {m},{h - ch - m} V {ch + m} Z"
    )
    mx, my = w - 150, h / 2
    room = mx - 292  # left margin, medallion, arrow and a clear gap before it
    s0, t0 = fit(eyebrow, 26, font_spec["track"] - 1, room, font_spec, floor=18)
    s1, t1 = fit(big, 56, font_spec["track"] - 1, room, font_spec)
    nf = font_spec["note"]
    s2, _ = fit(note, 32, 0, room, nf, floor=18)
    lines = [note]
    if s2 < MIN_NOTE_SIZE and " " in note:  # too long for one readable line: balance it over two
        words = note.split(" ")
        _, cut = min(
            (
                max(
                    text_width(" ".join(words[:i]), 30, 0, nf),
                    text_width(" ".join(words[i:]), 30, 0, nf),
                ),
                i,
            )
            for i in range(1, len(words))
        )
        lines = [" ".join(words[:cut]), " ".join(words[cut:])]
        s2 = fit(max(lines, key=lambda t: text_width(t, 30, 0, nf)), 30, 0, room, nf, floor=18)[0]
    lift = (len(lines) - 1) * 19  # two lines push the whole block up to stay centred
    note_svg = "".join(
        f'<text x="86" y="{my + 68 - lift + k * 38:.0f}" font-family="{nf["css"]}" font-style="{nf["style"]}" '
        f'font-weight="{nf["weight"]}" font-size="{s2}" fill="{INK}" opacity="0.88">{t}</text>'
        for k, t in enumerate(lines)
    )
    rays = "".join(
        f'<line x1="{mx}" y1="{my}" x2="{mx + math.cos(a) * 3000:.1f}" y2="{my + math.sin(a) * 3000:.1f}"/>'
        for a in (2 * math.pi * i / 32 for i in range(32))
    )
    ax = mx - 76 - 78
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<title>{big}</title>
<defs>
 <linearGradient id="p" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#e3d2ad"/><stop offset="1" stop-color="{PAPER_DEEP}"/></linearGradient>
 <clipPath id="cut"><path d="{outer}"/></clipPath>
</defs>
<path d="{outer}" fill="url(#p)"/>
<g clip-path="url(#cut)"><g stroke="{INK}" stroke-width="1.4" opacity="0.1">{rays}</g></g>
<path d="{outer}" fill="none" stroke="{FOG_DEEP}" stroke-width="4"/>
<path d="{inner}" fill="none" stroke="{INK}" stroke-width="1.8" opacity="0.55"/>
<circle cx="{mx}" cy="{my}" r="76" fill="{FOG_DEEP}"/>
<circle cx="{mx}" cy="{my}" r="76" fill="none" stroke="{GOLD}" stroke-width="2" opacity="0.7"/>
<circle cx="{mx}" cy="{my}" r="66" fill="none" stroke="{GOLD}" stroke-width="1.2" opacity="0.35"/>
<g transform="translate({mx} {my})">{brand(KOFI_PATH, KOFI_RED, 92)}</g>
<g font-family="{font_spec["css"]}" font-weight="700" fill="{INK}">
 <text x="84" y="{my - 58 - lift:.0f}" font-size="{s0}" letter-spacing="{t0:.1f}" opacity="0.7">{eyebrow}</text>
 <text x="84" y="{my + 8 - lift:.0f}" font-size="{s1}" letter-spacing="{t1:.1f}">{big}</text>
</g>
{note_svg}
<g fill="none" stroke="{KOFI_RED}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">
 <path d="M {ax - 26:.0f},{my:.0f} H {ax + 26:.0f} M {ax + 12:.0f},{my - 14:.0f} L {ax + 26:.0f},{my:.0f} L {ax + 12:.0f},{my + 14:.0f}"/>
</g>
</svg>
"""


def divider(w: int = 1260, h: int = 36) -> str:
    cx, cy = w / 2, h / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<title>Divider</title>
<g stroke="{GOLD}" stroke-linecap="round">
 <path d="M 14,{cy} H {cx - 40} M {cx + 40},{cy} H {w - 14}" stroke-width="1.6" opacity="0.5"/>
 <path d="M {cx - 56},{cy} H {cx - 46} M {cx + 46},{cy} H {cx + 56}" stroke-width="1.6" opacity="0.5"/>
 <circle cx="{cx}" cy="{cy}" r="12" fill="none" stroke-width="1.4" opacity="0.6"/>
</g>
<g transform="translate({cx} {cy})">{star(0, 0, 11, GOLD, long=1.0, short=0.5, width=0.24)}</g>
<path d="M 3,{cy} l 5,-5 l 5,5 l -5,5 Z M {w - 3},{cy} l -5,-5 l -5,5 l 5,5 Z" fill="{GOLD}" opacity="0.5"/>
</svg>
"""


SECTION_ICONS = ["globe", "sun", "sliders", "compass", "anchor", "link", "chart"]
SECTION_NAMES = ["world", "peoples", "custom", "start", "before", "compat", "links"]
BUTTON_ICONS = ["chart", "download", "flag", "github"]
BUTTON_NAMES = ["guide", "issues", "downloads", "bugs", "github"]
# Per language: seven section titles, five button labels, Ko-fi (question, ask, thank-you).
# Section 1, 4, 5 and 7 follow the headings of docs/workshop/<language>.bbcode. Latin and Cyrillic
# titles are set in capitals by ``caps``; CJK has no case.
TEXT = {
    "english": {
        "sections": [
            "A new world to explore",
            "Peoples of the new world",
            "Make it yours",
            "Getting started",
            "Before you play",
            "Compatibility",
            "Guides & downloads",
        ],
        "buttons": ["Guide", "Get", "Bugs", "GITHUB"],
        "kofi": (
            "Enjoying RNW?",
            "Buy the author a coffee",
            "RNW stays free. Your support helps it keep growing. Thank you!",
        ),
    },
    "russian": {
        "sections": [
            "Новый мир для исследования",
            "Народы Нового Света",
            "Настройте под себя",
            "Как начать",
            "Перед игрой",
            "Совместимость",
            "Руководства и загрузки",
        ],
        "buttons": ["Гайд", "Скачать", "Ошибки", "GITHUB"],
        "kofi": (
            "Нравится RNW?",
            "Угостите автора кофе",
            "RNW бесплатен. Ваша поддержка помогает ему расти. Спасибо!",
        ),
    },
    "braz_por": {
        "sections": [
            "Um novo mundo para explorar",
            "Povos do Novo Mundo",
            "Do seu jeito",
            "Como começar",
            "Antes de jogar",
            "Compatibilidade",
            "Guias e downloads",
        ],
        "buttons": ["Guia", "Baixar", "Erros", "GITHUB"],
        "kofi": (
            "Gostando do RNW?",
            "Um café para o autor",
            "O RNW segue gratuito. Seu apoio ajuda a crescer. Agradeço!",
        ),
    },
    "french": {
        "sections": [
            "Un nouveau monde à explorer",
            "Peuples du Nouveau Monde",
            "Un monde à votre goût",
            "Bien démarrer",
            "Avant de jouer",
            "Compatibilité",
            "Guides et téléchargements",
        ],
        "buttons": ["Guide", "Obtenir", "Bugs", "GITHUB"],
        "kofi": (
            "Vous aimez RNW ?",
            "Un café pour l’auteur",
            "RNW reste gratuit. Votre soutien l’aide à grandir. Merci !",
        ),
    },
    "german": {
        "sections": [
            "Eine neue Welt entdecken",
            "Völker der Neuen Welt",
            "Eure Welt",
            "So startet ihr",
            "Vor dem Spielen",
            "Kompatibilität",
            "Anleitungen und Downloads",
        ],
        "buttons": ["Guide", "Laden", "Fehler", "GITHUB"],
        "kofi": (
            "Gefällt euch RNW?",
            "Ein Kaffee für den Autor",
            "RNW bleibt kostenlos. Eure Hilfe lässt es wachsen. Danke!",
        ),
    },
    "spanish": {
        "sections": [
            "Un nuevo mundo por descubrir",
            "Pueblos del Nuevo Mundo",
            "A tu gusto",
            "Cómo empezar",
            "Antes de jugar",
            "Compatibilidad",
            "Guías y descargas",
        ],
        "buttons": ["Guía", "Obtener", "Errores", "GITHUB"],
        "kofi": (
            "¿Te gusta RNW?",
            "Un café para el autor",
            "RNW sigue siendo gratis. Tu apoyo ayuda a que siga creciendo. ¡Gracias!",
        ),
    },
    "polish": {
        "sections": [
            "Nowy świat do odkrycia",
            "Ludy Nowego Świata",
            "Świat po twojemu",
            "Jak zacząć",
            "Przed grą",
            "Zgodność",
            "Poradniki i pliki",
        ],
        "buttons": ["Pomoc", "Pobierz", "Błędy", "GITHUB"],
        "kofi": (
            "Podoba ci się RNW?",
            "Postaw autorowi kawę",
            "RNW pozostaje darmowy. Twoje wsparcie pomaga mu się rozwijać. Dziękuję!",
        ),
    },
    "turkish": {
        "sections": [
            "Keşfedilecek yeni bir dünya",
            "Yeni Dünya’nın halkları",
            "Size özel dünya",
            "Nasıl başlanır",
            "Oynamadan önce",
            "Uyumluluk",
            "Rehberler ve indirmeler",
        ],
        "buttons": ["Rehber", "İndir", "Hatalar", "GITHUB"],
        "kofi": (
            "RNW’yi beğendiniz mi?",
            "Yazara bir kahve ısmarlayın",
            "RNW ücretsiz kalacak. Desteğiniz büyümesine yardım eder. Teşekkürler!",
        ),
    },
    "japanese": {
        "sections": [
            "新たな世界を探検",
            "新世界の人々",
            "自分好みの世界",
            "始め方",
            "プレイ前に",
            "互換性",
            "ガイドとダウンロード",
        ],
        "buttons": ["ガイド", "ダウンロード", "不具合", "GITHUB"],
        "kofi": (
            "RNWを楽しんでいますか？",
            "作者にコーヒーを一杯",
            "RNWは無料です。応援が成長の力になります。ありがとう！",
        ),
    },
    "korean": {
        "sections": [
            "탐험할 새로운 세계",
            "신세계의 민족",
            "나만의 세계",
            "시작 방법",
            "플레이 전 안내",
            "호환성",
            "가이드 및 다운로드",
        ],
        "buttons": ["가이드", "다운로드", "버그", "GITHUB"],
        "kofi": (
            "RNW가 마음에 드시나요?",
            "제작자에게 커피 한 잔을",
            "RNW는 계속 무료입니다. 응원이 큰 힘이 됩니다. 감사합니다!",
        ),
    },
    "simp_chinese": {
        "sections": [
            "探索全新世界",
            "新世界的族群",
            "定制你的世界",
            "如何开始",
            "游玩前须知",
            "兼容性",
            "指南与下载",
        ],
        "buttons": ["指南", "下载", "问题反馈", "GITHUB"],
        "kofi": ("喜欢 RNW 吗？", "请作者喝杯咖啡", "RNW 将继续免费。你的支持让它不断成长，谢谢！"),
    },
}
CJK = {"japanese", "korean", "simp_chinese"}


def caps(lang: str, text: str) -> str:
    """Capitals for Latin and Cyrillic; Turkish keeps its dotted and dotless i."""
    if lang in CJK:
        return text
    if lang == "turkish":
        text = text.replace("i", "İ").replace("ı", "I")
    return text.upper()


MIN_NOTE_SIZE = 26  # below this the thank-you wraps onto two lines
KOFI_RED = "#ff5e5b"


CODES = {
    "english": "en", "russian": "ru", "braz_por": "pt", "french": "fr", "german": "de",
    "spanish": "es", "polish": "pl", "turkish": "tr", "japanese": "ja", "korean": "ko",
    "simp_chinese": "zh",
}  # fmt: skip
SECTION_IDS = "1234567"
BUTTON_IDS = "mnop"
BUTTON_PX = 148  # shown at their own size: four in a row fit Steam's column


def main(out: Path, svg_dir: Path | None) -> None:
    from xml.sax.saxutils import escape

    out.mkdir(parents=True, exist_ok=True)
    for stale in out.glob("??[0-9a-z].png"):
        stale.unlink()
    if svg_dir:
        svg_dir.mkdir(parents=True, exist_ok=True)

    def save(code: str, pid: str, svg: str, width: int | None = None) -> None:
        subprocess.run(
            [
                "rsvg-convert",
                *(["-w", str(width)] if width else []),
                "-o",
                str(out / f"{code}{pid}.png"),
            ],
            input=svg.encode(),
            check=True,
        )
        if svg_dir:
            (svg_dir / f"{code}{pid}.svg").write_text(svg, encoding="utf-8")

    for lang, deck in TEXT.items():
        code, spec = CODES[lang], FONTS[lang]
        for pid, text, icon in zip(SECTION_IDS, deck["sections"], SECTION_ICONS, strict=True):
            save(code, pid, banner(escape(caps(lang, text)), icon, spec))
        labels = [escape(caps(lang, t)) for t in deck["buttons"]]
        faces = [
            FONTS["english"] if t.isascii() else spec for t in deck["buttons"]
        ]  # GITHUB stays Latin
        size = min(button_size(t, face) for t, face in zip(labels, faces, strict=True))
        for pid, label, face, icon in zip(BUTTON_IDS, labels, faces, BUTTON_ICONS, strict=True):
            save(code, pid, button(label, icon, face, size), BUTTON_PX)
        eyebrow, big, note = deck["kofi"]
        save(
            code,
            "k",
            plaque(escape(caps(lang, eyebrow)), escape(caps(lang, big)), escape(note), spec),
        )
        save(code, "0", divider())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", nargs="?", type=Path, default=Path(__file__).parents[3] / "w")
    parser.add_argument("--svg", type=Path, help="also write the SVG sources here")
    args = parser.parse_args()
    main(args.out, args.svg)
