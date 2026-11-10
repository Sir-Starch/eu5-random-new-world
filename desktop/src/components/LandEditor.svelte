<script lang="ts">
  // The land editor: draw the land of a new world on the area the generator can fill, from a
  // ready land or from nothing, with ground kinds (mountains, highlands, lowlands, lakes), and
  // see what the generator will make of it before it begins. The drawing is a sheet of kinds
  // (`lib/landEditor`); the generator makes the ready lands, adds terrain, checks and takes the
  // picture (`rnw.gui.studio`).
  import { onDestroy, onMount, tick } from "svelte";
  import { app, t } from "../lib/app.svelte";
  import {
    BACK,
    DEFAULT_RULE,
    HIGHLANDS,
    LAKE,
    LAND,
    LOWLANDS,
    MAX_SIZE,
    MIN_SIZE,
    MOUNTAINS,
    SEA,
    SHOWN,
    Sheet,
    backdropRgba,
    fitCamera,
    refused,
    sayReport,
    toSheet,
    zoomAt,
    type Camera,
    type Report,
    type Tool,
  } from "../lib/landEditor";
  import { greysOfUrl, kindsOfUrl, thumbnail, urlOfKinds } from "../lib/landPictures";
  import { openFile, saveFile } from "../lib/native";
  import type { EditorInfo } from "../lib/types";
  import Icon from "./Icon.svelte";
  import Check from "./ui/Check.svelte";

  const IMAGES = [{ name: "PNG, JPEG, BMP, TIFF", extensions: ["png", "jpg", "jpeg", "bmp", "tif", "tiff"] }];
  const DRAFT = "rnw.landeditor.draft";
  const KIND_NAMES = ["sea", "land", "mountains", "highlands", "lowlands", "lake"] as const;
  const TOOL_ICONS: Record<Tool, string> = {
    brush: "brush",
    eraser: "eraser",
    fill: "bucket",
    line: "line",
    rectangle: "rectangle",
    ellipse: "ellipse",
    pan: "hand",
  };
  const TOOL_KEYS: Record<string, Tool> = { b: "brush", e: "eraser", g: "fill", l: "line", r: "rectangle", o: "ellipse", h: "pan" };
  const TOOL_HOTKEY: Record<Tool, string> = { brush: "B", eraser: "E", fill: "G", line: "L", rectangle: "R", ellipse: "O", pan: "H" };
  const TOOL_LIST: Tool[] = ["brush", "eraser", "fill", "line", "rectangle", "ellipse", "pan"];
  const THUMB_EVERY = 4;

  type Stage = "preparing" | "loading" | "ready" | "failed";
  interface Start {
    id: string;
    label: string;
    kinds: Uint8Array | null;
    thumb: string;
  }

  const s = $derived(app.now);
  let stage = $state<Stage>("preparing");
  let failure = $state("");
  let armed = $state(false);
  let startedRuns = 0;
  let info = $state<EditorInfo | null>(null);
  let sheet = $state.raw<Sheet | null>(null);
  let version = $state(0);
  let greys: Uint8Array | null = null;
  let margin: Uint8Array | null = null;
  let inside: Uint8Array | null = null;

  // What is drawn with, and how.
  let tool = $state<Tool>("brush");
  let kind = $state<number>(LAND);
  let size = $state(7);
  let terrainOnGround = $state(true);
  let filled = $state(true);
  const painting = $derived(tool === "eraser" ? SEA : kind);
  const rule = $derived({ ...DEFAULT_RULE, terrainOnGround, filled });

  // What is shown.
  let showDrawing = $state(true);
  let showAmericas = $state(true);
  let showIslands = $state(true);
  let showMargin = $state(true);
  let camera = $state<Camera>({ x: 0, y: 0, scale: 1 });
  let hover = $state<[number, number] | null>(null);
  let spaceDown = $state(false);

  // The elements the sheet is drawn on.
  let stageElement = $state<HTMLDivElement | null>(null);
  let backCanvas = $state<HTMLCanvasElement | null>(null);
  let drawCanvas = $state<HTMLCanvasElement | null>(null);
  let markCanvas = $state<HTMLCanvasElement | null>(null);
  let backContext: CanvasRenderingContext2D | null = null;
  let drawContext: CanvasRenderingContext2D | null = null;
  let drawImage: ImageData | null = null;
  let frame = 0;

  // The strokes in the making.
  let anchor: [number, number] | null = null;
  let last: [number, number] | null = null;
  let pan = $state<{ x: number; y: number; camera: Camera } | null>(null);

  // The ready lands, the terrain to add and what the generator says.
  let starts = $state.raw<Start[]>([]);
  let seed = $state(freshSeed());
  let startRun = 0;
  let knownRun = 0;
  let knownStarts = $state.raw<Start[]>([]);
  let sketchStarts = $state.raw<Start[]>([]);
  let sketchRun = 0;
  let sketched = "";
  let adding = $state({ mountains: true, highlands: true, lowlands: false, lakes: true });
  let decorations = 0;
  let report = $state<Report | null>(null);
  let checking = $state(false);
  let checkRun = 0;
  let checkTimer: ReturnType<typeof setTimeout> | undefined;
  let draftTimer: ReturnType<typeof setTimeout> | undefined;
  let working = $state(false);

  const canUndo = $derived.by(() => {
    void version;
    return sheet?.canUndo ?? false;
  });
  const canRedo = $derived.by(() => {
    void version;
    return sheet?.canRedo ?? false;
  });
  const empty = $derived.by(() => {
    void version;
    return !!sheet && !sheet.kinds.some((value) => value !== SEA);
  });
  const lines = $derived(report ? sayReport(report) : []);
  const usable = $derived(!working && !checking && !refused(report));
  const under = $derived.by(() => {
    void version;
    return hover && sheet ? sheet.get(hover[0], hover[1]) : null;
  });

  function freshSeed(): number {
    return Math.floor(Math.random() * 0x7fffffff);
  }

  // -- opening ---------------------------------------------------------------------------------

  onMount(() => {
    startedRuns = app.now?.runs ?? 0;
    void app.act("prepare_land_area").then((ok) => {
      if (ok) armed = true;
      else close();
    });
  });

  onDestroy(() => {
    cancelAnimationFrame(frame);
    clearTimeout(checkTimer);
    clearTimeout(draftTimer);
    startRun++;
    sketchRun++;
    checkRun++;
  });

  // The area is cut (a few seconds the first time, then from the land cache): open the sheet.
  $effect(() => {
    if (!armed || stage !== "preparing" || !s) return;
    if (s.new.editor_ready && !s.busy) void open();
    else if (!s.busy && s.phase === "failed" && s.task === "template" && s.runs > startedRuns) {
      failure = s.message;
      stage = "failed";
    }
  });

  async function open(): Promise<void> {
    stage = "loading";
    const found = await app.call<EditorInfo>("land_editor");
    if (!found) {
      close();
      return;
    }
    try {
      const [backdrop, coast] = await Promise.all([greysOfUrl(found.backdrop), greysOfUrl(found.margin)]);
      greys = backdrop;
      margin = coast;
      inside = backdrop.map((grey) => (grey === found.classes.outside ? 0 : 1));
      let start: Uint8Array | null = null;
      if (found.image) start = await kindsOfUrl(found.image, found.palette);
      else start = await savedDraft(found);
      sheet = new Sheet(found.width, found.height, start ?? undefined);
      info = found;
    } catch (error) {
      failure = String(error);
      stage = "failed";
      return;
    }
    stage = "ready";
    await tick();
    setup();
    scheduleCheck();
    void loadStarts();
    void loadKnown();
  }

  async function savedDraft(found: EditorInfo): Promise<Uint8Array | null> {
    try {
      const kept = JSON.parse(localStorage.getItem(DRAFT) ?? "null") as { width: number; height: number; image: string } | null;
      if (kept && kept.width === found.width && kept.height === found.height && kept.image) {
        return await kindsOfUrl(kept.image, found.palette);
      }
    } catch {
      // A draft is a convenience.
    }
    return null;
  }

  function saveDraft(): void {
    clearTimeout(draftTimer);
    draftTimer = setTimeout(() => {
      if (!sheet || !info) return;
      try {
        const image = urlOfKinds(sheet.kinds, sheet.width, sheet.height, info.palette);
        localStorage.setItem(DRAFT, JSON.stringify({ width: sheet.width, height: sheet.height, image }));
      } catch {
        // A draft is a convenience.
      }
    }, 1200);
  }

  /** The canvases are there: give them the area, the drawing and a camera that shows it all. */
  function setup(): void {
    if (!sheet || !info || !backCanvas || !drawCanvas || !markCanvas) return;
    for (const canvas of [backCanvas, drawCanvas, markCanvas]) {
      canvas.width = sheet.width;
      canvas.height = sheet.height;
    }
    backContext = backCanvas.getContext("2d");
    drawContext = drawCanvas.getContext("2d");
    drawImage = new ImageData(sheet.width, sheet.height);
    paintBack();
    paintAll();
    fit();
  }

  // -- drawing the sheet -------------------------------------------------------------------------

  function paintBack(): void {
    if (!greys || !margin || !info || !sheet || !backContext) return;
    const rgba = backdropRgba(greys, margin, info.classes, { showAmericas, showIslands, showMargin }, sheet.width);
    backContext.putImageData(new ImageData(rgba, sheet.width, sheet.height), 0, 0);
  }

  function paintBox(x0: number, y0: number, x1: number, y1: number): void {
    if (!sheet || !drawContext || !drawImage) return;
    const data = drawImage.data;
    const width = sheet.width;
    for (let y = y0; y <= y1; y++) {
      for (let x = x0; x <= x1; x++) {
        const shown = SHOWN[sheet.kinds[y * width + x]!]!;
        const at = (y * width + x) * 4;
        data[at] = shown[0];
        data[at + 1] = shown[1];
        data[at + 2] = shown[2];
        data[at + 3] = shown[3];
      }
    }
    drawContext.putImageData(drawImage, 0, 0, x0, y0, x1 - x0 + 1, y1 - y0 + 1);
  }

  function paintAll(): void {
    if (!sheet) return;
    sheet.takeDirty();
    paintBox(0, 0, sheet.width - 1, sheet.height - 1);
  }

  function schedule(): void {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      const box = sheet?.takeDirty();
      if (box) paintBox(box.x0, box.y0, box.x1, box.y1);
    });
  }

  $effect(() => {
    void [showAmericas, showIslands, showMargin];
    if (stage === "ready") paintBack();
  });

  // The generator's marks on the sheet: where a lake opens to the sea.
  $effect(() => {
    const places = report?.open_lakes ?? [];
    if (!markCanvas || !sheet) return;
    const context = markCanvas.getContext("2d");
    if (!context) return;
    context.clearRect(0, 0, markCanvas.width, markCanvas.height);
    context.strokeStyle = `rgb(${BACK.hatch.join(",")})`;
    context.lineWidth = 3;
    for (const [x, y] of places) {
      context.beginPath();
      context.arc(x + 0.5, y + 0.5, 12, 0, Math.PI * 2);
      context.stroke();
    }
  });

  // -- the camera ----------------------------------------------------------------------------------

  function box(): { width: number; height: number } {
    return { width: stageElement?.clientWidth ?? 0, height: stageElement?.clientHeight ?? 0 };
  }

  function fit(): void {
    if (sheet) camera = fitCamera(box(), sheet.width, sheet.height);
  }

  function zoom(factor: number): void {
    const { width, height } = box();
    camera = zoomAt(camera, factor, width / 2, height / 2);
  }

  function actual(): void {
    zoom(1 / camera.scale);
  }

  function wheel(event: WheelEvent): void {
    event.preventDefault();
    const rect = stageElement!.getBoundingClientRect();
    const delta = event.deltaMode === 1 ? event.deltaY * 16 : event.deltaY;
    camera = zoomAt(camera, Math.exp(-delta * 0.0018), event.clientX - rect.left, event.clientY - rect.top);
  }

  function at(event: PointerEvent): [number, number] {
    const rect = stageElement!.getBoundingClientRect();
    const [x, y] = toSheet(camera, event.clientX - rect.left, event.clientY - rect.top);
    return [Math.floor(x), Math.floor(y)];
  }

  // -- the pointer -----------------------------------------------------------------------------------

  function changed(): void {
    version++;
    schedule();
    scheduleCheck();
    saveDraft();
  }

  function shape(from: [number, number], to: [number, number]): void {
    if (!sheet) return;
    if (tool === "line") sheet.stroke(from[0], from[1], to[0], to[1], size, painting, rule);
    else if (tool === "rectangle") sheet.rectangle(from[0], from[1], to[0], to[1], size, painting, rule);
    else if (tool === "ellipse") sheet.ellipse(from[0], from[1], to[0], to[1], size, painting, rule);
  }

  function down(event: PointerEvent): void {
    if (!sheet || !stageElement) return;
    stageElement.setPointerCapture(event.pointerId);
    const point = at(event);
    if (event.button === 1 || (event.button === 0 && (tool === "pan" || spaceDown))) {
      pan = { x: event.clientX, y: event.clientY, camera };
      return;
    }
    if (event.button === 2) {
      // The right button takes the kind under the pointer, as a pipette.
      const picked = sheet.get(point[0], point[1]);
      kind = picked;
      if (tool === "eraser" || tool === "pan") tool = "brush";
      return;
    }
    if (event.button !== 0) return;
    sheet.begin();
    if (tool === "brush" || tool === "eraser") {
      sheet.stamp(point[0], point[1], size, painting, rule);
      last = point;
    } else if (tool === "fill") {
      sheet.fill(point[0], point[1], painting, rule);
      finish();
    } else {
      anchor = point;
      shape(point, point);
    }
    schedule();
  }

  function move(event: PointerEvent): void {
    if (!sheet) return;
    const point = at(event);
    hover = point;
    if (pan) {
      camera = { ...pan.camera, x: pan.camera.x + event.clientX - pan.x, y: pan.camera.y + event.clientY - pan.y };
      return;
    }
    if (!sheet.drawing) return;
    if (last && (tool === "brush" || tool === "eraser")) {
      sheet.stroke(last[0], last[1], point[0], point[1], size, painting, rule);
      last = point;
    } else if (anchor) {
      sheet.restore();
      shape(anchor, point);
    }
    schedule();
  }

  function up(): void {
    pan = null;
    if (sheet?.drawing) finish();
  }

  function finish(): void {
    if (!sheet) return;
    anchor = null;
    last = null;
    if (sheet.commit()) changed();
    else schedule();
  }

  function leave(): void {
    hover = null;
  }

  // -- the keys --------------------------------------------------------------------------------------

  function editing(target: EventTarget | null): boolean {
    const element = target as HTMLElement | null;
    return !!element && (element.tagName === "INPUT" || element.tagName === "TEXTAREA" || element.tagName === "SELECT");
  }

  function undo(): void {
    if (sheet?.undo()) changed();
  }

  function redo(): void {
    if (sheet?.redo()) changed();
  }

  function key(event: KeyboardEvent): void {
    if (app.modal || stage !== "ready") {
      if (event.key === "Escape" && !app.modal) close();
      return;
    }
    if (editing(event.target) && event.key !== "Escape") return;
    const control = event.ctrlKey || event.metaKey;
    const letter = event.key.toLowerCase();
    if (control && letter === "z") {
      if (event.shiftKey) redo();
      else undo();
    } else if (control && letter === "y") redo();
    else if (control || event.altKey) return;
    else if (Object.hasOwn(TOOL_KEYS, letter)) tool = TOOL_KEYS[letter]!;
    else if (/^[1-6]$/.test(event.key)) {
      kind = Number(event.key) - 1;
      if (tool === "eraser" || tool === "pan") tool = "brush";
    } else if (event.key === "[") size = Math.max(MIN_SIZE, size > 8 ? Math.round(size * 0.8) : size - 1);
    else if (event.key === "]") size = Math.min(MAX_SIZE, size >= 8 ? Math.round(size * 1.25) : size + 1);
    else if (event.key === "+" || event.key === "=") zoom(1.25);
    else if (event.key === "-") zoom(0.8);
    else if (event.key === "0") fit();
    else if (event.key === " ") spaceDown = true;
    else if (event.key === "Escape") close();
    else return;
    event.preventDefault();
  }

  function released(event: KeyboardEvent): void {
    if (event.key === " ") spaceDown = false;
  }

  // -- what the generator does -------------------------------------------------------------------

  function urlOf(): string {
    return urlOfKinds(sheet!.kinds, sheet!.width, sheet!.height, info!.palette);
  }

  function scheduleCheck(): void {
    clearTimeout(checkTimer);
    checking = true;
    checkTimer = setTimeout(() => void runCheck(), 350);
  }

  async function runCheck(): Promise<void> {
    if (!sheet || !info) return;
    const run = ++checkRun;
    const found = await app.call<Report>("land_check", { image: urlOf() });
    if (run !== checkRun) return;
    report = found;
    checking = false;
  }

  /** Put a drawing on the sheet as one step of the undo. */
  function take(kinds: Uint8Array): boolean {
    if (!sheet) return false;
    const different = sheet.replace(kinds);
    paintAll();
    if (different) changed();
    return different;
  }

  async function loadStarts(): Promise<void> {
    if (!info || !inside) return;
    const run = ++startRun;
    const found = info;
    const area = inside;
    const wanted: { id: string; label: string; call: () => Promise<string | null> }[] = [
      ...found.presets.map((preset) => ({
        id: `preset:${preset}`,
        label: t(`editor.preset.${preset}`),
        call: () => app.call<string>("land_preset", { preset, seed }),
      })),
      { id: "americas", label: t("editor.americas"), call: () => app.call<string>("land_americas") },
    ];
    starts = wanted.map((item) => ({ id: item.id, label: item.label, kinds: null, thumb: "" }));
    for (const [index, item] of wanted.entries()) {
      const url = await item.call();
      if (run !== startRun) return;
      if (!url) continue;
      const kinds = await kindsOfUrl(url, found.palette);
      if (run !== startRun) return;
      const next = starts.slice();
      next[index] = { id: item.id, label: item.label, kinds, thumb: thumbnail(kinds, found.width, found.height, THUMB_EVERY, area) };
      starts = next;
    }
  }

  /** The famous lands: fixed outlines, laid on the sheet by the generator. */
  async function loadKnown(): Promise<void> {
    if (!info || !inside) return;
    const run = ++knownRun;
    const found = info;
    const area = inside;
    knownStarts = found.lands.map((land) => ({ id: `land:${land}`, label: t(`editor.land.${land}`), kinds: null, thumb: "" }));
    for (const [index, land] of found.lands.entries()) {
      const url = await app.call<string>("land_known", { land });
      if (run !== knownRun) return;
      if (!url) continue;
      const kinds = await kindsOfUrl(url, found.palette);
      if (run !== knownRun) return;
      const next = knownStarts.slice();
      next[index] = { ...next[index]!, kinds, thumb: thumbnail(kinds, found.width, found.height, THUMB_EVERY, area) };
      knownStarts = next;
    }
  }

  /** The continents sketched in the window (one task, six pictures) join the ready lands. */
  async function loadSketches(): Promise<void> {
    if (!info || !inside) return;
    const run = ++sketchRun;
    const found = info;
    const area = inside;
    const count = app.now?.candidates.length ?? 0;
    sketchStarts = Array.from({ length: count }, (_, index) => ({
      id: `sketch:${index}`,
      label: t("editor.sketch", { number: index + 1 }),
      kinds: null,
      thumb: "",
    }));
    for (let index = 0; index < count; index++) {
      const url = await app.call<string>("land_sketch", { index });
      if (run !== sketchRun) return;
      if (!url) continue;
      const kinds = await kindsOfUrl(url, found.palette);
      if (run !== sketchRun) return;
      const next = sketchStarts.slice();
      next[index] = { ...next[index]!, kinds, thumb: thumbnail(kinds, found.width, found.height, THUMB_EVERY, area) };
      sketchStarts = next;
    }
  }

  // New sketches (another set of seeds) replace the old ones in the gallery.
  $effect(() => {
    const key = (s?.candidates ?? []).map((candidate) => candidate.seed).join(",");
    if (stage !== "ready" || key === sketched) return;
    sketched = key;
    void loadSketches();
  });

  const sketching = $derived(!!s?.busy && s.task === "candidates");

  function again(): void {
    seed = freshSeed();
    void loadStarts();
  }

  async function decorate(): Promise<void> {
    if (!sheet || !info || working) return;
    const parts = Object.entries(adding)
      .filter(([, on]) => on)
      .map(([name]) => name);
    if (!parts.length) return;
    working = true;
    try {
      const done = await app.call<string>("land_decorate", { image: urlOf(), seed: seed + ++decorations, parts });
      if (!done) return;
      const kinds = await kindsOfUrl(done, info.palette);
      if (!take(kinds)) app.toast("info", t("editor.nothing_added"), 4);
    } finally {
      working = false;
    }
  }

  async function importPicture(): Promise<void> {
    const path = await openFile(t("land_image_title"), IMAGES);
    if (path) await bring(path);
  }

  /** A picture dropped on the window, or chosen, goes onto the sheet. */
  async function bring(path: string): Promise<void> {
    if (!info || working) return;
    working = true;
    try {
      const got = await app.call<{ image: string; fit: string }>("land_import", { path });
      if (!got) return;
      take(await kindsOfUrl(got.image, info.palette));
      if (got.fit === "stretched" || got.fit === "centered") app.toast("info", t(`editor.fit.${got.fit}`), 8);
    } finally {
      working = false;
    }
  }

  // Pictures dropped on the window while it is open (or that opened it).
  $effect(() => {
    const path = app.importPath;
    if (!path || stage !== "ready" || working) return;
    app.importPath = "";
    void bring(path);
  });

  /** The picture as it is, at its own size and without the editor (finer than the sheet). */
  async function useAsIs(): Promise<void> {
    const path = await openFile(t("land_image_title"), IMAGES);
    if (!path) return;
    if (await app.act("choose_land_image", { path })) {
      app.toast("success", t("editor.used"), 5);
      close();
    }
  }

  /** The grey picture of the area to paint on elsewhere, saved where the player says. */
  async function saveTemplate(): Promise<void> {
    const path = await saveFile(t("land_template"), "new-world-template.png", [{ name: "PNG", extensions: ["png"] }]);
    if (!path || !(await app.act("save_land_template", { path }))) return;
    for (let waited = 0; waited < 600 && app.now?.busy; waited++) await new Promise((done) => setTimeout(done, 100));
    if (app.now?.phase === "finished") app.toast("success", t("picture_saved", { path }), 5);
  }

  async function exportPicture(): Promise<void> {
    if (!sheet || !info) return;
    const path = await saveFile(t("editor.export"), "new-world-land.png", [{ name: "PNG", extensions: ["png"] }]);
    if (!path) return;
    const message = await app.call<string>("save_png", { path, data: urlOf() });
    if (message) app.toast("success", message);
  }

  async function use(): Promise<void> {
    if (!sheet || !info || !usable) return;
    working = true;
    try {
      if (await app.act("use_land_picture", { image: urlOf() })) {
        app.toast("success", t("editor.used"), 5);
        close();
      }
    } finally {
      working = false;
    }
  }

  function clearSheet(): void {
    if (sheet?.clear()) {
      paintAll();
      changed();
    }
  }

  function close(): void {
    clearTimeout(draftTimer);
    if (sheet && info && version > 0) {
      try {
        const image = urlOfKinds(sheet.kinds, sheet.width, sheet.height, info.palette);
        localStorage.setItem(DRAFT, JSON.stringify({ width: sheet.width, height: sheet.height, image }));
      } catch {
        // A draft is a convenience.
      }
    }
    app.editor = false;
  }

  const cursor = $derived(spaceDown || tool === "pan" ? (pan ? "grabbing" : "grab") : tool === "fill" ? "cell" : "crosshair");
  const ring = $derived(tool === "brush" || tool === "eraser" || tool === "line" ? size : 0);
</script>

<svelte:window onkeydown={key} onkeyup={released} />

<div class="editor" role="dialog" aria-modal="true" aria-label={t("editor.title")}>
  <header class="top">
    <span class="pane-title">{t("editor.title")}</span>
    {#if info}<span class="pane-sub num">{info.width} × {info.height}</span>{/if}
    <span class="sep"></span>
    <button class="btn icon small ghost" disabled={!canUndo} title={`${t("editor.undo")} (Ctrl+Z)`} aria-label={t("editor.undo")} onclick={undo}><Icon name="undo" /></button>
    <button class="btn icon small ghost" disabled={!canRedo} title={`${t("editor.redo")} (Ctrl+Shift+Z)`} aria-label={t("editor.redo")} onclick={redo}><Icon name="redo" /></button>
    <span class="sep"></span>
    <button class="btn icon small ghost" title={`${t("editor.zoom_out")} (-)`} aria-label={t("editor.zoom_out")} onclick={() => zoom(0.8)}><Icon name="zoomOut" /></button>
    <button class="btn small ghost num zoom" title={t("editor.zoom_100")} onclick={actual}>{Math.round(camera.scale * 100)} %</button>
    <button class="btn icon small ghost" title={`${t("editor.zoom_in")} (+)`} aria-label={t("editor.zoom_in")} onclick={() => zoom(1.25)}><Icon name="zoomIn" /></button>
    <button class="btn icon small ghost" title={`${t("editor.zoom_fit")} (0)`} aria-label={t("editor.zoom_fit")} onclick={fit}><Icon name="fit" /></button>
    <span class="sep"></span>
    <button class="btn icon small ghost" class:on={showDrawing} aria-pressed={showDrawing} title={t("editor.layer.drawing")} aria-label={t("editor.layer.drawing")} onclick={() => { showDrawing = !showDrawing; }}><Icon name="eye" /></button>
    <button class="btn icon small ghost" class:on={showAmericas} aria-pressed={showAmericas} title={t("editor.layer.americas")} aria-label={t("editor.layer.americas")} onclick={() => { showAmericas = !showAmericas; }}><Icon name="mountain" /></button>
    <button class="btn icon small ghost" class:on={showIslands} aria-pressed={showIslands} title={t("editor.layer.islands")} aria-label={t("editor.layer.islands")} onclick={() => { showIslands = !showIslands; }}><Icon name="islands" /></button>
    <button class="btn icon small ghost" class:on={showMargin} aria-pressed={showMargin} title={t("editor.layer.margin")} aria-label={t("editor.layer.margin")} onclick={() => { showMargin = !showMargin; }}><Icon name="borders" /></button>
    <span class="spacer"></span>
    <button class="btn" onclick={close}>{t("editor.cancel")}</button>
    <button class="btn primary" disabled={!usable || stage !== "ready"} title={refused(report) ? t("editor.use_blocked") : t("editor.use_tip")} onclick={use}>
      <Icon name="check" />{t("editor.use")}
    </button>
  </header>

  {#if stage === "preparing" || stage === "loading"}
    <div class="wait">
      <span class="spinner"></span>
      <p>{stage === "preparing" ? t("editor.preparing") : t("editor.loading")}</p>
      <p class="faint">{t("editor.preparing_hint")}</p>
      <button class="btn" onclick={close}>{t("editor.cancel")}</button>
    </div>
  {:else if stage === "failed"}
    <div class="wait">
      <div class="msg error"><Icon name="alert" /><span class="selectable">{failure || t("editor.failed")}</span></div>
      <button class="btn" onclick={close}>{t("editor.close")}</button>
    </div>
  {:else}
    <div class="options">
      <div class="kinds" role="radiogroup" aria-label={t("editor.kinds")}>
        {#each KIND_NAMES as name, index (name)}
          <button
            class="kind"
            class:on={kind === index && tool !== "eraser"}
            role="radio"
            aria-checked={kind === index && tool !== "eraser"}
            title={`${t(`editor.kind.${name}.tip`)} (${index + 1})`}
            onclick={() => {
              kind = index;
              if (tool === "eraser" || tool === "pan") tool = "brush";
            }}
          >
            <span class="swatch" class:sea={index === SEA} style:background={index === SEA ? undefined : `rgb(${SHOWN[index]!.slice(0, 3).join(",")})`}></span>
            <span>{t(`editor.kind.${name}`)}</span>
            <kbd>{index + 1}</kbd>
          </button>
        {/each}
      </div>
      <label class="size">
        <span>{t("editor.size")}</span>
        <input type="range" min={MIN_SIZE} max={MAX_SIZE} bind:value={size} aria-label={t("editor.size")} />
        <span class="num value">{size}</span>
      </label>
      <Check checked={terrainOnGround} label={t("editor.on_ground")} info={t("editor.on_ground_tip")} onchange={(value) => (terrainOnGround = value)} />
      <Check checked={filled} label={t("editor.filled")} onchange={(value) => (filled = value)} />
    </div>

    <div class="body">
      <nav class="tools" aria-label={t("editor.tools")}>
        {#each TOOL_LIST as name (name)}
          <button
            class="btn icon ghost"
            class:on={tool === name}
            aria-pressed={tool === name}
            title={`${t(`editor.tool.${name}`)} (${TOOL_HOTKEY[name]})`}
            aria-label={t(`editor.tool.${name}`)}
            onclick={() => (tool = name)}
          >
            <Icon name={TOOL_ICONS[name]} size={18} />
          </button>
        {/each}
      </nav>

      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="stage"
        bind:this={stageElement}
        style:cursor
        onwheel={wheel}
        onpointerdown={down}
        onpointermove={move}
        onpointerup={up}
        onpointercancel={up}
        onpointerleave={leave}
        oncontextmenu={(event) => event.preventDefault()}
      >
        <div class="world" style:width={`${info?.width ?? 0}px`} style:height={`${info?.height ?? 0}px`} style:transform={`translate(${camera.x}px, ${camera.y}px) scale(${camera.scale})`} style:--scale={camera.scale}>
          <canvas class="layer back" bind:this={backCanvas}></canvas>
          <canvas class="layer" class:hidden={!showDrawing} bind:this={drawCanvas}></canvas>
          <canvas class="layer" bind:this={markCanvas}></canvas>
          {#if hover && ring && !pan && !spaceDown}
            <span class="ring" style:left={`${hover[0] - (ring - 1) / 2}px`} style:top={`${hover[1] - (ring - 1) / 2}px`} style:width={`${ring}px`} style:height={`${ring}px`}></span>
          {/if}
        </div>
        {#if empty}
          <div class="hint" aria-hidden="true">{t("editor.hint")}</div>
        {/if}
      </div>

      <aside class="side scroll">
        <section>
          <div class="head">
            <h3>{t("editor.start")}</h3>
            <button class="btn small" title={t("editor.reroll_tip")} onclick={again}><Icon name="dice" />{t("editor.reroll")}</button>
          </div>
          {#snippet tile(item: Start)}
            <button class="start" disabled={!item.kinds} title={item.label} onclick={() => item.kinds && take(item.kinds)}>
              <span class="picture">{#if item.thumb}<img src={item.thumb} alt="" />{:else}<span class="spinner"></span>{/if}</span>
              <span class="name">{item.label}</span>
            </button>
          {/snippet}
          <div class="gallery">
            <p class="group">{t("editor.group_ready")}</p>
            {#each starts as item (item.id)}{@render tile(item)}{/each}
            {#if knownStarts.length}
              <p class="group">{t("editor.group_known")}</p>
              {#each knownStarts as item (item.id)}{@render tile(item)}{/each}
            {/if}
            {#if sketchStarts.length}
              <p class="group">{t("editor.group_sketches")}</p>
              {#each sketchStarts as item (item.id)}{@render tile(item)}{/each}
            {/if}
          </div>
          <button class="btn" disabled={sketching || !s?.new.candidates_enabled} title={t("editor.sketch_tip")} onclick={() => app.act("sketch_candidates")}>
            {#if sketching}<span class="spinner"></span>{s?.running || t("stage.candidates")}{:else}<Icon name="dice" />{t("editor.sketch_run")}{/if}
          </button>
        </section>

        <section>
          <div class="head"><h3>{t("editor.decorate")}</h3></div>
          <p class="faint note">{t("editor.decorate_tip")}</p>
          <div class="adds">
            <Check checked={adding.mountains} label={t("editor.add.mountains")} onchange={(value) => (adding.mountains = value)} />
            <Check checked={adding.highlands} label={t("editor.add.highlands")} onchange={(value) => (adding.highlands = value)} />
            <Check checked={adding.lowlands} label={t("editor.add.lowlands")} onchange={(value) => (adding.lowlands = value)} />
            <Check checked={adding.lakes} label={t("editor.add.lakes")} onchange={(value) => (adding.lakes = value)} />
          </div>
          <button class="btn" disabled={working || empty || !Object.values(adding).some(Boolean)} onclick={decorate}><Icon name="sparkle" />{t("editor.decorate_run")}</button>
        </section>

        <section>
          <div class="head">
            <h3>{t("editor.check")}</h3>
            {#if checking}<span class="spinner"></span>{/if}
          </div>
          {#if report && !checking}
            <ul class="report">
              {#each lines as line (line.key)}
                <li class={line.level}>
                  <Icon name={line.level === "ok" ? "check" : line.level === "warn" ? "warning" : "alert"} />
                  <span>{t(line.key, line.values)}</span>
                </li>
              {/each}
            </ul>
          {:else if !report}
            <p class="faint note">{t("editor.checking")}</p>
          {/if}
        </section>

        <section>
          <div class="head"><h3>{t("editor.picture")}</h3></div>
          <div class="commands">
            <button class="btn" disabled={working} onclick={importPicture}><Icon name="open" />{t("editor.import")}</button>
            <button class="btn" disabled={working} title={t("editor.as_is_tip")} onclick={useAsIs}><Icon name="image" />{t("editor.as_is")}</button>
            <button class="btn" disabled={empty} onclick={exportPicture}><Icon name="download" />{t("editor.export")}</button>
            <button class="btn" disabled={!s?.new.template_enabled} title={t("land_template_tip")} onclick={saveTemplate}><Icon name="file" />{t("land_template")}</button>
            <button class="btn danger" disabled={empty} onclick={clearSheet}><Icon name="trash" />{t("editor.clear")}</button>
          </div>
        </section>
      </aside>
    </div>

    <footer class="status num faint">
      <span>{hover ? `${hover[0]}, ${hover[1]}` : ""}</span>
      <span>{under !== null && hover ? t(`editor.kind.${KIND_NAMES[under]}`) : ""}</span>
      {#if lines.length && !checking}
        <span class="verdict {lines[0]!.level}" title={t(lines[0]!.key, lines[0]!.values)}>
          <Icon name={lines[0]!.level === "ok" ? "check" : lines[0]!.level === "warn" ? "warning" : "alert"} size={13} />
          <span class="said">{t(lines[0]!.key, lines[0]!.values)}</span>
        </span>
      {/if}
      <span class="spacer"></span>
      <span class="keys">{t("editor.keys")}</span>
    </footer>
  {/if}
</div>

<style>
  .editor {
    position: fixed;
    inset: 0;
    z-index: 40;
    display: flex;
    flex-direction: column;
    background: var(--bg);
    color: var(--text);
  }
  .top {
    flex: none;
    display: flex;
    align-items: center;
    gap: 4px;
    height: 40px;
    padding: 0 10px;
    border-bottom: 1px solid var(--line);
    background: var(--panel);
    overflow: hidden;
  }
  .sep {
    width: 1px;
    height: 18px;
    margin: 0 6px;
    background: var(--line-2);
  }
  .spacer {
    flex: 1;
  }
  .zoom {
    min-width: 54px;
  }
  .top .pane-sub {
    color: var(--text-3);
    font-size: 12px;
  }
  .wait {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    text-align: center;
    padding: 24px;
  }
  .wait .msg {
    max-width: 560px;
  }
  .options {
    flex: none;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 16px;
    padding: 6px 10px;
    border-bottom: 1px solid var(--line);
    background: var(--panel);
  }
  .kinds {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }
  .kind {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 26px;
    padding: 0 8px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius);
    background: var(--raised);
    color: var(--text);
    font: 400 12.5px/1 var(--font);
    cursor: default;
  }
  .kind:hover {
    background: var(--raised-hover);
  }
  .kind.on {
    border-color: var(--accent);
    background: var(--accent-soft);
  }
  .kind kbd {
    color: var(--text-3);
    font: 400 10.5px/1 var(--mono);
  }
  .swatch {
    width: 14px;
    height: 14px;
    border-radius: 2px;
    border: 1px solid rgba(255, 255, 255, 0.25);
  }
  .swatch.sea {
    background: rgb(34, 62, 100);
  }
  .size {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 12.5px;
    color: var(--text-2);
  }
  .size input {
    width: 140px;
  }
  .size .value {
    min-width: 2ch;
    text-align: right;
    color: var(--text);
  }
  .body {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: 44px minmax(0, 1fr) 300px;
  }
  .tools {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 8px 0;
    border-right: 1px solid var(--line);
    background: var(--panel);
  }
  .stage {
    position: relative;
    overflow: hidden;
    background: var(--canvas);
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
  }
  .world {
    position: absolute;
    left: 0;
    top: 0;
    transform-origin: 0 0;
    box-shadow: 0 0 0 1px var(--line-3);
  }
  .layer {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    image-rendering: pixelated;
  }
  .layer.hidden {
    visibility: hidden;
  }
  .ring {
    position: absolute;
    pointer-events: none;
    border-radius: 50%;
    border: calc(1.5px / var(--scale)) solid rgba(255, 255, 255, 0.9);
    box-shadow: 0 0 0 calc(1px / var(--scale)) rgba(0, 0, 0, 0.6);
  }
  .hint {
    position: absolute;
    left: 50%;
    bottom: 16px;
    transform: translateX(-50%);
    max-width: 80%;
    padding: 6px 12px;
    border-radius: var(--radius);
    background: rgba(0, 0, 0, 0.6);
    color: #fff;
    font-size: 12.5px;
    text-align: center;
    pointer-events: none;
  }
  .side {
    display: flex;
    flex-direction: column;
    gap: 0;
    border-left: 1px solid var(--line);
    background: var(--panel);
    overflow-y: auto;
    scrollbar-gutter: stable;
  }
  .side section {
    display: grid;
    gap: 8px;
    padding: 10px 12px 12px;
    border-bottom: 1px solid var(--line);
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    min-height: 22px;
  }
  .head h3 {
    margin: 0;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-2);
  }
  .note {
    margin: 0;
    font-size: 12px;
    line-height: 1.45;
  }
  .gallery {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 6px;
  }
  .group {
    grid-column: 1 / -1;
    margin: 4px 0 0;
    font-size: 11px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-2);
  }
  .group:first-child {
    margin-top: 0;
  }
  .start {
    display: grid;
    gap: 3px;
    padding: 3px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius);
    background: var(--raised);
    color: var(--text);
    cursor: default;
    min-width: 0;
  }
  .start:hover:not(:disabled) {
    border-color: var(--accent);
    background: var(--raised-hover);
  }
  .start:disabled {
    opacity: 0.6;
  }
  .start .picture {
    display: flex;
    align-items: center;
    justify-content: center;
    aspect-ratio: 5 / 4;
    background: rgb(20, 22, 27);
    overflow: hidden;
  }
  .start img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
  .start .name {
    font-size: 11px;
    line-height: 1.2;
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .adds {
    display: grid;
    gap: 4px;
  }
  .report {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 6px;
  }
  .report li {
    display: grid;
    grid-template-columns: 16px 1fr;
    gap: 6px;
    font-size: 12.5px;
    line-height: 1.4;
  }
  .report li.ok {
    color: var(--ok);
  }
  .report li.warn {
    color: var(--warn);
  }
  .report li.error {
    color: var(--danger);
  }
  .report li span {
    color: var(--text);
  }
  .commands {
    display: grid;
    gap: 6px;
  }
  .commands .btn {
    justify-content: flex-start;
  }
  .status {
    flex: none;
    display: flex;
    gap: 16px;
    align-items: center;
    height: 24px;
    padding: 0 10px;
    border-top: 1px solid var(--line);
    background: var(--panel);
    font-size: 11.5px;
  }
  .status > span {
    white-space: nowrap;
  }
  .status .verdict {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    min-width: 0;
    overflow: hidden;
  }
  .status .verdict .said {
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .status .verdict.ok {
    color: var(--ok);
  }
  .status .verdict.warn {
    color: var(--warn);
  }
  .status .verdict.error {
    color: var(--danger);
  }
  .status .keys {
    flex: 0 100000 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  @media (max-width: 900px) {
    .body {
      grid-template-columns: 44px minmax(0, 1fr) 240px;
    }
  }
</style>
