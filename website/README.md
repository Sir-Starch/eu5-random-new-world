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
| `capture_window.mjs` | Captures the release's generator window for the first steps, in every language |
| `public/` | The built site, committed; this folder is what gets hosted |

## Look

Terra Incognita fog (`#4d443d`), caption parchment and rhumb lines from compass nodes, as on the
Workshop banners (`docs/images/workshop/make_banners.py`). Titles are set in Cinzel; Russian uses
Noto Serif in capitals and Japanese, Korean and Chinese use Noto Serif CJK, as the banners do.
The text is Noto Sans, the generator's own face. The world-type vignettes, the fog over the hero
map and the rhumb backgrounds are drawn by `sitegen.py`. The pictures are crops of the
owner-approved screenshots in `docs/images/showcase`.

The four steps show the real screens with the controls marked. Steps 2 and 3 are the released
generator window in the page's own language, captured by `capture_window.mjs`: for each language
the release tag's window runs in a browser through its development bridge with an empty data
folder, so no library, path or setting of the capturing machine appears. Steps 1 and 4 are crops of
an owner-approved EU5 screenshot of **Mods & DLCs**, in English; the step text names each
language's own words. The sources are in `docs/images/website/`; `sitegen.py` draws the EU5 marks
and joins the two Save and play crops.

Recapture the window after a release that changes those screens:

```sh
git worktree add --detach /tmp/rnw-release vX.Y.Z
(cd /tmp/rnw-release && uv sync --locked)
ln -s "$PWD/desktop/node_modules" /tmp/rnw-release/desktop/node_modules
(cd website && npm ci && npx playwright install chromium)
node website/capture_window.mjs /tmp/rnw-release
uv run python website/sitegen.py
```

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

`public/` is served as Cloudflare Workers static assets with no Worker code (`wrangler.jsonc`,
Worker `rnw-guide`). The custom domain `rnw.sirstarch.com` owns its DNS record and certificate.
`public/_headers` sets the security headers and caching; unknown paths get `404.html`. Wrangler
is pinned in `package.json`.

```sh
cd website
npm ci
npx wrangler login       # once, in the owner's browser
npm run check            # dry run: reads public/, uploads nothing
npm run deploy           # publish public/ as it is committed
```

Deploy only a committed, checked `public/`. Publishing is an owner-authorized account action.

[V-EXEC] 2026-11-04: first deployment with Wrangler 4.151.3. Every language page, the root,
the stylesheet, fonts and pictures returned 200 over HTTPS; an unknown path returned the 404
page; `/en` redirected to `/en/`; the `_headers` security headers and the immutable font caching
were present. In a browser the root opened `/ru/`, `/ja/` and `/en/` for those locales, with all
fonts loaded and no console or request errors.

## Licences

Guide text and drawings are original work under CC BY 4.0. The fonts are subsets of SIL OFL 1.1
fonts; `public/fonts/OFL.txt` lists their copyright notices and each subset keeps its name records.
The page makes no request to another site and sets no cookies; the only stored value is the chosen
language, in the visitor's own browser.
