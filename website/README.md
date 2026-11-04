# Player's guide website

The page behind the Workshop's **Guide** button: `https://rnw.sirstarch.com`, one static page per
official EU5 language (`/en/`, `/ru/`, `/pt-br/`, …). The root page opens the visitor's language
(browser language, or the one they picked before) and keeps a `#section` anchor, so
`rnw.sirstarch.com/#help-memory` opens the memory answer in any language.

The guide is for players: four steps to a first campaign, the rules that keep a save safe, world
types, the main settings, hidden maps, the library, compatibility and common problems. Commands,
reproduction and implementation stay in the [technical guide](../docs/generator-guide.md), which the
footer links.

## Files

| Path | What it is |
|---|---|
| `content/english.toml` | The English text, the source of every translation |
| `content/<language>.toml` | One translation per official language; `source` is the fingerprint of the English it was made from |
| `src/` | Hand-written CSS and JS, the favicon and the hosting headers |
| `sitegen.py` | The generator: pages, pictures, chart art and font subsets |
| `fontsubset.py` | The fontTools call that subsets one face |
| `public/` | The built site, committed; this folder is what gets hosted |

## Look

Terra Incognita fog (`#4d443d`), caption parchment and rhumb lines from compass nodes, as on the
Workshop banners (`docs/images/workshop/make_banners.py`). Titles are set in Cinzel; Russian uses
Noto Serif in capitals and Japanese, Korean and Chinese use Noto Serif CJK, as the banners do.
The text is Noto Sans, the generator's own face. The world-type vignettes, the fog over the hero
map and the rhumb backgrounds are drawn by `sitegen.py`. The pictures are crops of the
owner-approved screenshots in `docs/images/showcase`.

The four plates in the first section show where to click. They are drawn in HTML, so each
language's plate carries the words that player will see on screen.

## Words on the page

- **Controls of the generator** are written `{ui:KEY}` and resolved from the window's catalogues
  **at the release tag** in `RELEASE` (`rnw/gui/text.py` and `rnw/locale/<language>/window.toml`).
  A missing or stale window translation stops the build, as it would stop the window.
- **Parts of EU5's interface** are written `{game:KEY}` and come from `GAME_TERMS`, read from the
  installed game's `main_menu/localization` (single interface words only).
- **Release facts** are `{v:version}`, `{v:game}`, `{v:verified}`.
- `**bold**`, `` `code` `` and `[text](url)` mark the rest. A translation keeps the same terms,
  code spans and link targets; `tests/test_website.py` compares them key by key.

To change the text: edit the English, rewrite every affected key in each translation, then set
each translation's `source` to the new fingerprint (printed by the failing test or by
`sitegen.content_problems()`). Write each language as the [localization rules](../docs/localization.md)
ask: the game's register, its interface words, no calques and no brochure tone.

## Build

```sh
uv sync --locked --group dev
uv run python website/sitegen.py          # pages, pictures and font subsets
uv run python website/sitegen.py --html   # pages only, with the fonts already recorded
uv run python website/sitegen.py --only english,russian   # a draft of some languages
```

The full build needs Cinzel, Noto Sans, Noto Serif and Noto Serif CJK installed (fontconfig finds
them). Each page loads only the glyphs it shows: about 30 KB of fonts for a Latin page, up to
80 KB for Japanese. Two builds of the same sources are byte-identical. Commit `public/` together
with the change; `make check` fails while a committed page is out of date.

For a release, set `RELEASE` in `sitegen.py` to the new tag, game branch and verified build,
rebuild and review the changed terms.

## Hosting

`public/` is a plain static folder with no build step on the host. Its `_headers` file sets
security headers and caching on Cloudflare Pages; other hosts ignore it. `sirstarch.com` is on
Cloudflare DNS, so Cloudflare Pages serving `website/public` with the custom domain
`rnw.sirstarch.com` is the shortest route; GitHub Pages from the same folder works as well.
Connecting the domain, the first deployment and pointing the Workshop's Guide button at the new
address are owner-authorized account actions.

## Licences

Guide text and drawings are original work under CC BY 4.0. The fonts are subsets of SIL OFL 1.1
fonts; `public/fonts/OFL.txt` lists their copyright notices and each subset keeps its name records.
The page makes no request to another site and sets no cookies; the only stored value is the chosen
language, in the visitor's own browser.
