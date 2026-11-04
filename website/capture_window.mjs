// Real frames of the generator's window for the guide's first steps, in every official language.
//
//   git worktree add --detach /tmp/rnw-release v1.1.0      # the release the guide describes
//   (cd /tmp/rnw-release && uv sync --locked) && ln -s "$PWD/desktop/node_modules" /tmp/rnw-release/desktop/
//   node website/capture_window.mjs /tmp/rnw-release
//
// For each language the release's own window runs in a browser through its development bridge
// (`npm run dev`, docs/gui-design.md) with an empty data folder that holds only the language
// choice, so no library, path or setting of this machine appears. The marks on the controls the
// guide names are an outline drawn on those elements. Frames are written at twice the CSS size to
// docs/images/website/, where website/sitegen.py takes them.
import { spawn } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { chromium } from "playwright";

const LANGUAGES = [
  ["english", "en"], ["german", "de"], ["spanish", "es"], ["french", "fr"], ["polish", "pl"],
  ["braz_por", "pt-br"], ["turkish", "tr"], ["russian", "ru"], ["japanese", "ja"],
  ["korean", "ko"], ["simp_chinese", "zh"],
];
const PORT = 5179;
const MARK = "#e07a55"; // the guide's red ink, as on its other plates
const checkout = resolve(process.argv[2] ?? "");
const out = resolve(import.meta.dirname, "..", "docs", "images", "website");
mkdirSync(out, { recursive: true });

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

async function serve(data) {
  const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], {
    cwd: join(checkout, "desktop"),
    env: { ...process.env, RNW_DATA: data },
    stdio: "ignore",
    detached: true,
  });
  for (let i = 0; i < 60; i += 1) {
    try {
      if ((await fetch(`http://127.0.0.1:${PORT}/`)).ok) return vite;
    } catch {
      // not listening yet
    }
    await sleep(500);
  }
  process.kill(-vite.pid);
  throw new Error("the window's development server did not start");
}

// The rectangle around elements, widened by margins above and below, inside the inspector.
async function around(page, selectors, above = 10, below = 10) {
  return page.evaluate(
    ({ selectors, above, below }) => {
      const pane = document.querySelector("aside.inspector").getBoundingClientRect();
      const boxes = selectors.map((s) => {
        const el = document.querySelector(s);
        if (!el) throw new Error(`missing ${s}`);
        return el.getBoundingClientRect();
      });
      const top = Math.max(pane.top, Math.min(...boxes.map((b) => b.top)) - above);
      const bottom = Math.min(pane.bottom, Math.max(...boxes.map((b) => b.bottom)) + below);
      return { x: pane.left, y: top, width: pane.width, height: bottom - top };
    },
    { selectors, above, below },
  );
}

async function mark(page, selectors) {
  await page.evaluate(
    ({ selectors, color }) => {
      for (const el of document.querySelectorAll(".rnw-mark")) el.classList.remove("rnw-mark");
      for (const s of selectors) document.querySelector(s).classList.add("rnw-mark");
      if (!document.getElementById("rnw-mark-style")) {
        const style = document.createElement("style");
        style.id = "rnw-mark-style";
        style.textContent = `.rnw-mark{outline:2px solid ${color}!important;outline-offset:3px!important;border-radius:3px}`;
        document.head.append(style);
      }
    },
    { selectors, color: MARK },
  );
}

async function capture(browser, game, slug) {
  const data = mkdtempSync(join(tmpdir(), "rnw-capture-"));
  writeFileSync(join(data, "preferences.json"), JSON.stringify({ language: game }));
  const vite = await serve(data);
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 2,
      colorScheme: "dark",
    });
    await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: "networkidle" });
    await page.waitForSelector("#world-type");
    await page.evaluate(() => document.fonts.ready);
    await sleep(600);

    // Step 2: the World tab and its world type.
    const tabs = "aside.inspector [role=tab]";
    await mark(page, ["#world-type"]);
    const world = await around(page, [`${tabs}:nth-child(1)`, "#world-type + .hint"], 10, 5);
    await page.screenshot({ path: join(out, `window-${slug}-world.png`), clip: world });

    // Step 3: Save and play, the library destination, "add to the game", and Generate.
    await page.click(`${tabs}:nth-child(3)`);
    await page.waitForSelector("input[name=destination]");
    await sleep(400);
    const library = "label.check:has(input[name=destination])";
    const install = "label.check:has(input[type=checkbox])";
    await mark(page, [library, install, "aside.inspector .generate .btn.primary"]);
    const top = await around(page, [`${tabs}:nth-child(1)`, install], 10, 7);
    await page.screenshot({ path: join(out, `window-${slug}-save.png`), clip: top });
    const bottom = await around(page, ["aside.inspector .generate .actions"], 6, 10);
    await page.screenshot({ path: join(out, `window-${slug}-generate.png`), clip: bottom });
    await page.close();
  } finally {
    process.kill(-vite.pid);
    await sleep(800);
    rmSync(data, { recursive: true, force: true });
  }
  console.log(`captured ${slug}`);
}

const browser = await chromium.launch();
try {
  for (const [game, slug] of LANGUAGES) await capture(browser, game, slug);
} finally {
  await browser.close();
}
