<script lang="ts">
  import { onDestroy, onMount, untrack } from "svelte";
  import { app, grouped, t } from "../lib/app.svelte";
  import { WorldAtlas, type Facts, type Match } from "../lib/atlas";
  import { loadAtlas } from "../lib/atlasCache";
  import {
    between,
    clamp,
    fit,
    toAtlas,
    toScreen,
    zoomAt,
    type Camera,
  } from "../lib/camera";
  import { createRenderer, type Overlays, type Renderer, type Theme } from "../lib/mapgl";
  import { copyImage, saveFile } from "../lib/native";
  import Icon from "./Icon.svelte";

  let {
    world,
    layer = $bindable("countries"),
    camera = $bindable<Camera | null>(null),
    compact = false,
    onCompare,
  }: {
    world: string;
    layer?: string;
    camera?: Camera | null;
    compact?: boolean;
    onCompare?: () => void;
  } = $props();

  const LENS_ICONS: Record<string, string> = {
    land: "mountain",
    countries: "crown",
    cultures: "people",
    religions: "flame",
    resources: "sparkles",
    development: "layers",
    population: "people",
    climate: "sun",
    terrain: "mountain",
    areas: "grid",
  };
  const STORE = "rnw.map";

  function remembered(): { overlays: Overlays & { labels: boolean } } {
    try {
      const value = JSON.parse(localStorage.getItem(STORE) ?? "{}") as Partial<{
        overlays: Overlays & { labels: boolean };
      }>;
      return {
        overlays: {
          lensBorders: true,
          political: true,
          locations: false,
          coast: true,
          labels: true,
          ...value.overlays,
        },
      };
    } catch {
      return {
        overlays: { lensBorders: true, political: true, locations: false, coast: true, labels: true },
      };
    }
  }

  let atlas = $state<WorldAtlas | null>(null);
  let failed = $state(false);
  let loading = $state(true);
  let overlays = $state(remembered().overlays);
  let host: HTMLDivElement;
  let canvas: HTMLCanvasElement;
  let labelCanvas: HTMLCanvasElement;
  let minimap = $state<HTMLCanvasElement>();
  let renderer: Renderer | null = null;
  let rendererKind = $state("");
  let view = $state({ width: 1, height: 1 });
  let cam = $state<Camera>({ x: 0, y: 0, scale: 1 });
  let hover = $state(-1);
  let pinned = $state(-1);
  let pointer = $state({ x: 0, y: 0 });
  let match = $state<{ label: string; cells: Set<number>; colour?: string } | null>(null);
  let preview = $state<Set<number> | null>(null);
  let query = $state("");
  let results = $state<Match[]>([]);
  let searching = $state(false);
  let resultIndex = $state(0);
  let legendFilter = $state("");
  let legendOpen = $state(true);
  let frame = 0;
  let animation = 0;
  let drag = $state<{ x: number; y: number; cam: Camera; moved: boolean } | null>(null);
  let observer: ResizeObserver | null = null;
  let theme: Theme = { ink: [10, 12, 16], accent: [220, 174, 90] };

  const lens = $derived(atlas?.lens(layer) ?? null);
  const facts = $derived<Facts | null>(atlas ? atlas.facts(pinned >= 0 ? pinned : hover) : null);
  const hoverFacts = $derived<Facts | null>(atlas && hover >= 0 ? atlas.facts(hover) : null);
  const landCells = $derived(atlas?.data.totals.land ?? 1);
  const legend = $derived.by(() => {
    if (!lens) return [];
    const needle = legendFilter.trim().toLocaleLowerCase();
    return lens.legend
      .map((entry, index) => ({ ...entry, index }))
      .filter((entry) => !needle || entry.label.toLocaleLowerCase().includes(needle));
  });
  const isRamp = $derived(app.info?.ramps.includes(layer) ?? false);
  const zoomPercent = $derived(Math.round(cam.scale * 100));

  // -- loading -----------------------------------------------------------------------------------

  $effect(() => {
    const id = world;
    untrack(() => {
      loading = true;
      failed = false;
      pinned = -1;
      hover = -1;
      match = null;
    });
    void loadAtlas(id).then((found) => {
      if (id !== world) return;
      loading = false;
      if (!found) {
        failed = true;
        return;
      }
      atlas = found;
      setup(found);
    });
  });

  function setup(found: WorldAtlas): void {
    renderer?.dispose();
    renderer = createRenderer(canvas, found);
    rendererKind = renderer.kind;
    canvas = renderer.canvas;
    renderer.setAtlas(found);
    renderer.setLens(layer);
    renderer.setFlags(-1, -1, null);
    readTheme();
    resize();
    cam = camera && camera.scale > 0 ? camera : fit(view, found.width, found.height);
    paintMinimap();
    request();
  }

  function readTheme(): void {
    const style = getComputedStyle(host);
    const parse = (name: string, fallback: [number, number, number]): [number, number, number] => {
      const probe = document.createElement("span");
      probe.style.color = style.getPropertyValue(name);
      host.appendChild(probe);
      const rgb = getComputedStyle(probe).color.match(/\d+/g)?.map(Number);
      probe.remove();
      return rgb && rgb.length >= 3 ? [rgb[0], rgb[1], rgb[2]] : fallback;
    };
    const light = document.documentElement.dataset.theme === "light" ||
      (!document.documentElement.dataset.theme &&
        matchMedia("(prefers-color-scheme: light)").matches);
    theme = {
      ink: light ? [44, 32, 18] : [8, 10, 14],
      accent: parse("--accent", [220, 174, 90]),
    };
  }

  // -- drawing -----------------------------------------------------------------------------------

  function request(): void {
    if (!frame) frame = requestAnimationFrame(draw);
  }

  function draw(): void {
    frame = 0;
    if (!renderer || !atlas) return;
    renderer.draw(cam, overlays, theme);
    drawLabels();
    drawMinimapView();
  }

  function resize(): void {
    if (!host) return;
    const rect = host.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    view = { width: Math.max(1, rect.width), height: Math.max(1, rect.height) };
    for (const target of [canvas, labelCanvas]) {
      if (!target) continue;
      target.width = Math.round(view.width * dpr);
      target.height = Math.round(view.height * dpr);
    }
    request();
  }

  function drawLabels(): void {
    const context = labelCanvas?.getContext("2d");
    if (!context || !atlas) return;
    const dpr = window.devicePixelRatio || 1;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, view.width, view.height);
    if (!overlays.labels) return;
    const placed: [number, number, number, number][] = [];
    const light = theme.ink[0] > 30;
    const fill = light ? "rgba(36, 26, 12, 0.92)" : "rgba(246, 240, 226, 0.95)";
    const halo = light ? "rgba(250, 244, 230, 0.85)" : "rgba(6, 8, 12, 0.78)";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.lineJoin = "round";
    const labels = atlas.labelsFor(layer);
    for (const label of labels) {
      const size = Math.min(26, Math.sqrt(label.weight) * cam.scale * 0.21);
      if (size < 10) continue;
      const [sx, sy] = toScreen(cam, label.x, label.y);
      if (sx < -200 || sy < -40 || sx > view.width + 200 || sy > view.height + 40) continue;
      const upper = layer === "countries";
      const text = upper ? label.text.toLocaleUpperCase() : label.text;
      context.font = `${upper ? 600 : 500} ${size.toFixed(1)}px "Fraunces Variable", Georgia, serif`;
      if ("letterSpacing" in context) {
        (context as unknown as { letterSpacing: string }).letterSpacing = upper
          ? `${(size * 0.12).toFixed(1)}px`
          : "0px";
      }
      const width = context.measureText(text).width;
      const box: [number, number, number, number] = [
        sx - width / 2 - 4,
        sy - size / 2 - 2,
        sx + width / 2 + 4,
        sy + size / 2 + 2,
      ];
      if (placed.some((p) => box[0] < p[2] && box[2] > p[0] && box[1] < p[3] && box[3] > p[1])) {
        continue;
      }
      placed.push(box);
      context.lineWidth = Math.max(2.5, size * 0.22);
      context.strokeStyle = halo;
      context.strokeText(text, sx, sy);
      context.fillStyle = fill;
      context.fillText(text, sx, sy);
      if (placed.length > 260) break;
    }
    if (layer === "countries" && cam.scale > 0.9) {
      for (const capital of atlas.capitals()) {
        const [sx, sy] = toScreen(cam, capital.x, capital.y);
        if (sx < -10 || sy < -10 || sx > view.width + 10 || sy > view.height + 10) continue;
        const r = Math.min(5, 2 + cam.scale * 0.6);
        context.beginPath();
        context.moveTo(sx, sy - r);
        context.lineTo(sx + r, sy);
        context.lineTo(sx, sy + r);
        context.lineTo(sx - r, sy);
        context.closePath();
        context.fillStyle = light ? "#2a1f10" : "#fbf4e2";
        context.strokeStyle = halo;
        context.lineWidth = 2;
        context.stroke();
        context.fill();
      }
    }
  }

  // -- the minimap -------------------------------------------------------------------------------

  const MINI = 196;
  let miniImage: HTMLCanvasElement | null = null;

  function paintMinimap(): void {
    if (!atlas) return;
    const found = atlas;
    const current = found.lens(layer);
    const ratio = found.height / found.width;
    const w = MINI;
    const h = Math.max(1, Math.round(MINI * ratio));
    miniImage = document.createElement("canvas");
    miniImage.width = w;
    miniImage.height = h;
    const context = miniImage.getContext("2d");
    if (!context) return;
    const pixels = context.createImageData(w, h);
    for (let y = 0; y < h; y++) {
      const ay = Math.min(found.height - 1, Math.floor(((y + 0.5) / h) * found.height));
      for (let x = 0; x < w; x++) {
        const ax = Math.min(found.width - 1, Math.floor(((x + 0.5) / w) * found.width));
        const c = found.labels[ay * found.width + ax];
        if (c < 0) continue;
        const o = (y * w + x) * 4;
        pixels.data[o] = current.colours[c * 3];
        pixels.data[o + 1] = current.colours[c * 3 + 1];
        pixels.data[o + 2] = current.colours[c * 3 + 2];
        pixels.data[o + 3] = 255;
      }
    }
    context.putImageData(pixels, 0, 0);
  }

  function drawMinimapView(): void {
    if (!minimap || !miniImage || !atlas) return;
    const dpr = window.devicePixelRatio || 1;
    const w = miniImage.width;
    const h = miniImage.height;
    if (minimap.width !== w * dpr) {
      minimap.width = w * dpr;
      minimap.height = h * dpr;
    }
    const context = minimap.getContext("2d");
    if (!context) return;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, w, h);
    context.drawImage(miniImage, 0, 0);
    const k = w / atlas.width;
    const x = cam.x * k;
    const y = cam.y * k;
    const vw = (view.width / cam.scale) * k;
    const vh = (view.height / cam.scale) * k;
    context.fillStyle = "rgba(0,0,0,0.35)";
    context.fillRect(0, 0, w, h);
    context.save();
    context.beginPath();
    context.rect(x, y, vw, vh);
    context.clip();
    context.drawImage(miniImage, 0, 0);
    context.restore();
    context.strokeStyle = `rgb(${theme.accent.join(",")})`;
    context.lineWidth = 1.5;
    context.strokeRect(x + 0.5, y + 0.5, vw - 1, vh - 1);
  }

  function miniPointer(event: PointerEvent): void {
    if (!atlas || !minimap || !miniImage) return;
    if (event.type === "pointermove" && event.buttons !== 1) return;
    const rect = minimap.getBoundingClientRect();
    const ax = ((event.clientX - rect.left) / rect.width) * atlas.width;
    const ay = ((event.clientY - rect.top) / rect.height) * atlas.height;
    setCamera({
      scale: cam.scale,
      x: ax - view.width / 2 / cam.scale,
      y: ay - view.height / 2 / cam.scale,
    });
  }

  // -- the camera --------------------------------------------------------------------------------

  function setCamera(next: Camera): void {
    if (!atlas) return;
    cam = clamp(next, view, atlas.width, atlas.height);
    camera = cam;
    request();
  }

  function animateTo(target: Camera, duration = 420): void {
    cancelAnimationFrame(animation);
    const start = cam;
    const began = performance.now();
    const step = (now: number): void => {
      const share = Math.min(1, (now - began) / duration);
      setCamera(between(start, target, share, view));
      if (share < 1) animation = requestAnimationFrame(step);
    };
    animation = requestAnimationFrame(step);
  }

  export function fitAll(): void {
    if (atlas) animateTo(fit(view, atlas.width, atlas.height));
  }

  function zoomBy(factor: number): void {
    const target = zoomAt(cam, factor, view.width / 2, view.height / 2);
    animateTo(target, 220);
  }

  function zoomToCells(cells: Iterable<number>): void {
    if (!atlas) return;
    const box = atlas.bounds(cells);
    if (box) animateTo(fit(view, atlas.width, atlas.height, box, 80, 8));
  }

  // Another viewer moved the shared camera (compare mode).
  $effect(() => {
    const shared = camera;
    if (shared && atlas && (shared.x !== cam.x || shared.y !== cam.y || shared.scale !== cam.scale)) {
      untrack(() => {
        cam = shared;
        request();
      });
    }
  });

  // -- pointer -----------------------------------------------------------------------------------

  function local(event: MouseEvent): [number, number] {
    const rect = host.getBoundingClientRect();
    return [event.clientX - rect.left, event.clientY - rect.top];
  }

  function wheel(event: WheelEvent): void {
    event.preventDefault();
    cancelAnimationFrame(animation);
    const [sx, sy] = local(event);
    const delta = event.deltaMode === 1 ? event.deltaY * 16 : event.deltaY;
    setCamera(zoomAt(cam, Math.exp(-delta * 0.0018), sx, sy));
  }

  function down(event: PointerEvent): void {
    if (event.button !== 0) return;
    host.setPointerCapture(event.pointerId);
    cancelAnimationFrame(animation);
    drag = { x: event.clientX, y: event.clientY, cam, moved: false };
  }

  function move(event: PointerEvent): void {
    const [sx, sy] = local(event);
    pointer = { x: sx, y: sy };
    if (drag) {
      const dx = event.clientX - drag.x;
      const dy = event.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
      if (drag.moved) {
        setCamera({ ...drag.cam, x: drag.cam.x - dx / cam.scale, y: drag.cam.y - dy / cam.scale });
        return;
      }
    }
    if (!atlas) return;
    const [ax, ay] = toAtlas(cam, sx, sy);
    const cell = atlas.cellAt(ax, ay);
    if (cell !== hover) hover = cell;
  }

  function up(event: PointerEvent): void {
    if (drag && !drag.moved && atlas) {
      const [sx, sy] = local(event);
      const [ax, ay] = toAtlas(cam, sx, sy);
      const cell = atlas.cellAt(ax, ay);
      pinned = cell === pinned ? -1 : cell;
    }
    drag = null;
  }

  function leave(): void {
    if (!drag) hover = -1;
  }

  function dblclick(event: MouseEvent): void {
    const [sx, sy] = local(event);
    animateTo(zoomAt(cam, 2.4, sx, sy), 300);
  }

  // -- what is lit -------------------------------------------------------------------------------

  $effect(() => {
    const shown = preview ?? match?.cells ?? null;
    const h = hover;
    const p = pinned;
    if (renderer && atlas) {
      renderer.setFlags(h, p, shown);
      request();
    }
  });

  $effect(() => {
    const current = layer;
    if (renderer && atlas) {
      untrack(() => {
        renderer?.setLens(current);
        paintMinimap();
        request();
      });
    }
  });

  $effect(() => {
    try {
      localStorage.setItem(STORE, JSON.stringify({ overlays: $state.snapshot(overlays) }));
    } catch {
      // Storage is a convenience.
    }
    request();
  });

  function isolate(label: string, cells: number[], colour?: string, zoom = false): void {
    if (match && match.label === label) {
      match = null;
      return;
    }
    match = { label, cells: new Set(cells), colour };
    if (zoom) zoomToCells(cells);
  }

  function legendCells(index: number): number[] {
    return atlas ? atlas.classCells(layer, index) : [];
  }

  function searched(): void {
    searching = true;
    results = atlas ? atlas.find(query, 60) : [];
    resultIndex = 0;
  }

  function choose(result: Match): void {
    match = { label: result.label, cells: new Set(result.cells), colour: result.colour };
    if (result.kind === "place" && result.cells.length === 1) pinned = result.cells[0];
    zoomToCells(result.cells);
    searching = false;
  }

  function searchKey(event: KeyboardEvent): void {
    if (event.key === "ArrowDown") {
      resultIndex = Math.min(results.length - 1, resultIndex + 1);
      event.preventDefault();
    } else if (event.key === "ArrowUp") {
      resultIndex = Math.max(0, resultIndex - 1);
      event.preventDefault();
    } else if (event.key === "Enter" && results[resultIndex]) {
      choose(results[resultIndex]);
    } else if (event.key === "Escape") {
      searching = false;
      (event.target as HTMLElement).blur();
    }
  }

  function highlightOf(kind: "country" | "culture" | "religion" | "material" | "area"): void {
    if (!atlas || !facts) return;
    const d = atlas.data;
    const c = facts.cell;
    if (kind === "country" && facts.country) {
      isolate(facts.country.name, atlas.cellsWhere("owner", d.owner[c]), facts.country.color, true);
    } else if (kind === "culture") {
      isolate(facts.culture, atlas.cellsWhere("culture", d.culture[c]), undefined, true);
    } else if (kind === "religion") {
      isolate(facts.religion, atlas.cellsWhere("religion", d.religion[c]), undefined, true);
    } else if (kind === "material") {
      isolate(facts.material, atlas.cellsWhere("material", d.material[c]));
    } else if (kind === "area") {
      const cells: number[] = [];
      for (let k = 0; k < atlas.cells; k++) if (d.area[k] === facts.area && d.kind[k] === 0) cells.push(k);
      isolate(facts.area, cells, undefined, true);
    }
  }

  // -- pictures ----------------------------------------------------------------------------------

  async function savePicture(): Promise<void> {
    const name = `${(atlas?.data.name ?? "world").replace(/\s+/g, "-")}-${layer}.png`;
    const path = await saveFile(t("save_picture"), name, [{ name: "PNG", extensions: ["png"] }]);
    if (path) await app.report("save_map", { id: world, layer, path }, t("picture_saved", { path }));
  }

  async function copyView(): Promise<void> {
    if (!renderer) return;
    renderer.draw(cam, overlays, theme);
    const out = document.createElement("canvas");
    out.width = renderer.canvas.width;
    out.height = renderer.canvas.height;
    const context = out.getContext("2d");
    if (!context) return;
    context.fillStyle = getComputedStyle(host).getPropertyValue("--map-bg") || "#0b1119";
    context.fillRect(0, 0, out.width, out.height);
    context.drawImage(renderer.canvas, 0, 0);
    context.drawImage(labelCanvas, 0, 0);
    try {
      await copyImage(out.toDataURL("image/png"));
      app.toast("success", t("map.copied"));
    } catch (error) {
      app.toast("warning", String(error));
    }
  }

  // -- keys --------------------------------------------------------------------------------------

  function key(event: KeyboardEvent): void {
    const target = event.target as HTMLElement | null;
    if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return;
    if (!host?.isConnected || compact) return;
    const layers = app.info?.layers ?? [];
    if (/^[0-9]$/.test(event.key) && !event.ctrlKey && !event.metaKey) {
      const index = event.key === "0" ? 9 : Number(event.key) - 1;
      if (layers[index]) layer = layers[index];
    } else if (event.key === "+" || event.key === "=") zoomBy(1.6);
    else if (event.key === "-") zoomBy(1 / 1.6);
    else if (event.key.toLowerCase() === "f" && !event.ctrlKey) fitAll();
    else if (event.key.toLowerCase() === "l" && !event.ctrlKey) overlays.labels = !overlays.labels;
    else if (event.key.toLowerCase() === "b" && !event.ctrlKey) overlays.political = !overlays.political;
    else if (event.key === "Escape") {
      if (pinned >= 0) pinned = -1;
      else match = null;
    } else return;
    event.preventDefault();
  }

  onMount(() => {
    observer = new ResizeObserver(() => resize());
    observer.observe(host);
    window.addEventListener("keydown", key);
    const scheme = matchMedia("(prefers-color-scheme: light)");
    const retheme = (): void => {
      readTheme();
      request();
    };
    scheme.addEventListener("change", retheme);
    const themeWatch = new MutationObserver(retheme);
    themeWatch.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      scheme.removeEventListener("change", retheme);
      themeWatch.disconnect();
    };
  });

  onDestroy(() => {
    observer?.disconnect();
    window.removeEventListener("keydown", key);
    cancelAnimationFrame(frame);
    cancelAnimationFrame(animation);
    renderer?.dispose();
  });

  const tooltipStyle = $derived.by(() => {
    const flipX = pointer.x > view.width - 300;
    const flipY = pointer.y > view.height - 220;
    const x = flipX ? pointer.x - 16 : pointer.x + 18;
    const y = flipY ? pointer.y - 16 : pointer.y + 18;
    return `left:${x}px;top:${y}px;transform:translate(${flipX ? "-100%" : "0"},${flipY ? "-100%" : "0"})`;
  });

  function share(count: number): string {
    const value = (count * 100) / Math.max(1, landCells);
    return value >= 10 ? value.toFixed(0) : value.toFixed(1);
  }
</script>

<div class="viewer" class:compact data-renderer={rendererKind}>
  {#if !compact}
    <div class="toolbar">
      <div class="lenses" role="tablist" aria-label={t("legend")}>
        {#each app.info?.layers ?? [] as name, index (name)}
          <button
            class="lens"
            class:on={layer === name}
            role="tab"
            aria-selected={layer === name}
            title={`${t(`layer.${name}.tip`)} (${index === 9 ? 0 : index + 1})`}
            onclick={() => (layer = name)}
          >
            <Icon name={LENS_ICONS[name] ?? "layers"} size={15} />
            <span>{t(`layer.${name}`)}</span>
          </button>
        {/each}
      </div>
      <div class="tools">
        <button class="btn icon small ghost" class:active={overlays.political} title={t("map.political")} aria-pressed={overlays.political} onclick={() => (overlays.political = !overlays.political)}>
          <Icon name="borders" size={16} />
        </button>
        <button class="btn icon small ghost" class:active={overlays.labels} title={t("map.labels")} aria-pressed={overlays.labels} onclick={() => (overlays.labels = !overlays.labels)}>
          <Icon name="labels" size={16} />
        </button>
        <button class="btn icon small ghost" class:active={overlays.locations} title={t("map.locations")} aria-pressed={overlays.locations} onclick={() => (overlays.locations = !overlays.locations)}>
          <Icon name="grid" size={16} />
        </button>
        <span class="sep"></span>
        <button class="btn icon small ghost" title={t("map.copy_view")} onclick={copyView}><Icon name="camera" size={16} /></button>
        <button class="btn icon small ghost" title={t("save_picture_tip")} onclick={savePicture}><Icon name="download" size={16} /></button>
        {#if onCompare}
          <button class="btn icon small ghost" title={t("compare_title")} onclick={onCompare}><Icon name="compare" size={16} /></button>
        {/if}
        <button class="btn icon small ghost" class:active={app.mapFocus} title={t("map.focus")} aria-pressed={app.mapFocus} onclick={() => (app.mapFocus = !app.mapFocus)}>
          <Icon name={app.mapFocus ? "shrink" : "expand"} size={16} />
        </button>
      </div>
    </div>
  {/if}

  <div class="stage">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="canvas-host"
      class:dragging={drag?.moved}
      bind:this={host}
      onwheel={wheel}
      onpointerdown={down}
      onpointermove={move}
      onpointerup={up}
      onpointerleave={leave}
      ondblclick={dblclick}
    >
      <canvas bind:this={canvas} class="layer"></canvas>
      <canvas bind:this={labelCanvas} class="layer labels"></canvas>
    </div>

    {#if loading}
      <div class="veil"><div class="spinner"></div><span>{t("map.loading")}</span></div>
    {:else if failed}
      <div class="veil"><Icon name="map" size={28} /><span>{t("no_atlas")}</span></div>
    {/if}

    {#if !compact && atlas}
      <div class="search">
        <div class="search-box">
          <Icon name="search" size={15} />
          <input
            class="search-input"
            placeholder={t("search_hint")}
            bind:value={query}
            oninput={searched}
            onkeydown={searchKey}
            onfocus={() => (searching = !!query.trim())}
            aria-label={t("search_hint")}
          />
          {#if query}
            <button class="btn icon small ghost" aria-label={t("map.clear")} onclick={() => { query = ""; results = []; }}>
              <Icon name="x" size={14} />
            </button>
          {/if}
        </div>
        {#if query.trim() && searching}
          <div class="results scroll" role="listbox">
            {#each results as result, index (index)}
              <button
                class="result"
                class:on={index === resultIndex}
                role="option"
                aria-selected={index === resultIndex}
                onmouseenter={() => { resultIndex = index; preview = new Set(result.cells); }}
                onmouseleave={() => (preview = null)}
                onclick={() => { preview = null; choose(result); }}
              >
                <span class="kind">{t(`found.${result.kind}`)}</span>
                <span class="label">{result.label}</span>
                <span class="count num">{grouped(result.cells.length)}</span>
              </button>
            {:else}
              <div class="empty">{t("map.no_results")}</div>
            {/each}
          </div>
        {/if}
      </div>

      {#if match}
        <div class="chip" style:--swatch={match.colour ?? "var(--accent)"}>
          <span class="swatch"></span>
          <span>{t("map.showing", { name: match.label })}</span>
          <span class="faint num">{grouped(match.cells.size)}</span>
          <button class="btn icon small ghost" aria-label={t("map.clear")} onclick={() => (match = null)}>
            <Icon name="x" size={14} />
          </button>
        </div>
      {/if}

      <aside class="legend card" class:closed={!legendOpen}>
        <button class="legend-head" onclick={() => (legendOpen = !legendOpen)} aria-expanded={legendOpen}>
          <span class="eyebrow">{t("legend")}</span>
          <strong>{t(`layer.${layer}`)}</strong>
          <Icon name={legendOpen ? "chevronDown" : "chevronRight"} size={15} />
        </button>
        {#if legendOpen}
          {#if isRamp && lens}
            <div class="ramp">
              <div class="ramp-bar" style:background={`linear-gradient(90deg, ${lens.ramp.join(",")})`}></div>
              <div class="ramp-labels faint">
                <span>{t("legend.lowest")}</span><span>{t("legend.highest")}</span>
              </div>
            </div>
          {/if}
          {#if (lens?.legend.length ?? 0) > 12}
            <input class="input legend-filter" placeholder={t("map.legend_filter")} bind:value={legendFilter} />
          {/if}
          <div class="entries scroll">
            {#each legend as entry (entry.index)}
              {#if entry.count > 0}
                <button
                  class="entry"
                  class:on={match?.label === entry.label}
                  onmouseenter={() => (preview = new Set(legendCells(entry.index)))}
                  onmouseleave={() => (preview = null)}
                  onclick={() => { preview = null; isolate(entry.label, legendCells(entry.index), entry.colour); }}
                  ondblclick={() => zoomToCells(legendCells(entry.index))}
                  title={entry.label}
                >
                  <span class="swatch" style:background={entry.colour}></span>
                  <span class="label">{entry.label}</span>
                  <span class="count num">{grouped(entry.count)}</span>
                  <span class="bar" style:width={`${Math.min(100, (entry.count * 100) / Math.max(1, lens?.legend[0]?.count ?? 1))}%`} style:background={entry.colour}></span>
                </button>
              {/if}
            {/each}
          </div>
          <p class="legend-hint faint">{t("map.legend_hint")}</p>
        {/if}
      </aside>

      {#if pinned >= 0 && facts}
        <section class="inspector card" aria-live="polite">
          <header>
            <div>
              <span class="eyebrow">{t(`kind.${facts.kind}`)}</span>
              <h2>{facts.name}</h2>
              {#if facts.area}<p class="faint">{facts.area}{facts.region ? ` · ${facts.region}` : ""}</p>{/if}
            </div>
            <button class="btn icon small ghost" aria-label={t("close")} onclick={() => (pinned = -1)}><Icon name="x" size={15} /></button>
          </header>
          {#if facts.kind === "land"}
            <dl>
              <dt>{t("fact.country")}</dt>
              <dd>
                {#if facts.country}
                  <button class="link" onclick={() => highlightOf("country")}>
                    <span class="swatch" style:background={facts.country.color}></span>{facts.country.name}
                    <span class="faint mono">{facts.country.tag}</span>
                  </button>
                {:else}<span class="faint">{t("no_country")}</span>{/if}
              </dd>
              {#if facts.culture}
                <dt>{t("fact.culture")}</dt><dd><button class="link" onclick={() => highlightOf("culture")}>{facts.culture}</button></dd>
                <dt>{t("fact.religion")}</dt><dd><button class="link" onclick={() => highlightOf("religion")}>{facts.religion}</button></dd>
              {/if}
              <dt>{t("fact.material")}</dt>
              <dd><button class="link" onclick={() => highlightOf("material")}>{facts.material}{facts.precious ? " ✦" : ""}</button></dd>
              <dt>{t("fact.terrain")}</dt>
              <dd>{[facts.topography, facts.vegetation, facts.climate].filter(Boolean).join(" · ")}</dd>
              {#if facts.population}
                <dt>{t("fact.population")}</dt><dd class="num">{grouped(facts.population)}</dd>
                <dt>{t("fact.complexity")}</dt><dd class="num">{facts.complexity}</dd>
              {/if}
              {#if facts.area}
                <dt>{t("fact.area")}</dt><dd><button class="link" onclick={() => highlightOf("area")}>{facts.area}</button></dd>
              {/if}
            </dl>
          {/if}
        </section>
      {/if}

      {#if hoverFacts && hover !== pinned && !drag?.moved}
        <div class="tooltip" style={tooltipStyle}>
          <strong>{hoverFacts.name}</strong>
          <span class="faint">{t(`kind.${hoverFacts.kind}`)}</span>
          {#if hoverFacts.kind === "land"}
            <div class="tip-row">
              <span class="faint">{t("fact.country")}:</span>
              {#if hoverFacts.country}<span class="swatch" style:background={hoverFacts.country.color}></span>{hoverFacts.country.name}{:else}<span class="faint">{t("no_country")}</span>{/if}
            </div>
            {#if hoverFacts.culture}<div class="tip-row dim">{hoverFacts.culture} · {hoverFacts.religion}</div>{/if}
            <div class="tip-row dim">{hoverFacts.material}{hoverFacts.precious ? " ✦" : ""} · {hoverFacts.topography}</div>
            {#if hoverFacts.population}<div class="tip-row dim num">{t("fact.population")}: {grouped(hoverFacts.population)}</div>{/if}
          {/if}
        </div>
      {/if}

      <div class="minimap card">
        <canvas bind:this={minimap} onpointerdown={miniPointer} onpointermove={miniPointer} aria-label={t("map.minimap")}></canvas>
      </div>

      <div class="zoom card">
        <button class="btn icon small ghost" title={t("map.zoom_in")} onclick={() => zoomBy(1.6)}><Icon name="zoomIn" size={16} /></button>
        <span class="num faint zoom-value">{zoomPercent}%</span>
        <button class="btn icon small ghost" title={t("map.zoom_out")} onclick={() => zoomBy(1 / 1.6)}><Icon name="zoomOut" size={16} /></button>
        <button class="btn icon small ghost" title={t("map.fit")} onclick={fitAll}><Icon name="fit" size={16} /></button>
      </div>
    {/if}
  </div>
</div>

<style>
  .viewer {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }
  .toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--line);
    background: var(--panel);
  }
  .lenses {
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    flex: 1;
    min-width: 0;
  }
  .lens {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    height: 30px;
    padding: 0 10px;
    border-radius: 999px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-2);
    font: 550 13px var(--font);
    cursor: pointer;
    white-space: nowrap;
    transition: all var(--speed) var(--ease);
  }
  .lens:hover {
    background: var(--hover);
    color: var(--text);
  }
  .lens.on {
    background: var(--accent-soft);
    border-color: var(--accent-line);
    color: var(--accent);
  }
  .tools {
    display: flex;
    align-items: center;
    gap: 2px;
  }
  .tools .active {
    color: var(--accent);
    background: var(--accent-soft);
  }
  .sep {
    width: 1px;
    height: 20px;
    background: var(--line-2);
    margin: 0 6px;
  }
  .stage {
    position: relative;
    flex: 1;
    min-height: 0;
    overflow: hidden;
    background:
      radial-gradient(ellipse at 50% 40%, color-mix(in srgb, var(--sea) 10%, transparent), transparent 70%),
      var(--map-bg);
  }
  .canvas-host {
    position: absolute;
    inset: 0;
    cursor: crosshair;
    touch-action: none;
  }
  .canvas-host.dragging {
    cursor: grabbing;
  }
  .layer {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }
  .labels {
    pointer-events: none;
  }
  .veil {
    position: absolute;
    inset: 0;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: 12px;
    color: var(--text-2);
    text-align: center;
    padding: 24px;
  }
  .spinner {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: 2.5px solid var(--line-2);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
  }
  .search {
    position: absolute;
    top: 14px;
    left: 14px;
    width: min(380px, calc(100% - 28px));
    z-index: 3;
  }
  .search-box {
    display: flex;
    align-items: center;
    gap: 8px;
    height: 40px;
    padding: 0 6px 0 13px;
    border-radius: 12px;
    background: color-mix(in srgb, var(--panel) 88%, transparent);
    backdrop-filter: blur(14px);
    border: 1px solid var(--line-2);
    box-shadow: var(--shadow-sm);
    color: var(--text-3);
  }
  .search-box:focus-within {
    border-color: var(--accent-line);
    box-shadow: 0 0 0 3px var(--accent-soft), var(--shadow-sm);
  }
  .search-input {
    flex: 1;
    min-width: 0;
    border: 0;
    background: transparent;
    color: var(--text);
    font: 450 13.5px var(--font);
    outline: none;
    user-select: text;
  }
  .results {
    margin-top: 6px;
    max-height: 340px;
    padding: 4px;
    border-radius: 12px;
    background: color-mix(in srgb, var(--panel) 95%, transparent);
    backdrop-filter: blur(14px);
    border: 1px solid var(--line-2);
    box-shadow: var(--shadow);
    animation: rise 140ms var(--ease);
  }
  .result {
    display: grid;
    grid-template-columns: 76px 1fr auto;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 8px 10px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: var(--text);
    font: 500 13px var(--font);
    text-align: left;
    cursor: pointer;
  }
  .result.on {
    background: var(--accent-soft);
  }
  .result .kind {
    font-size: 11px;
    font-weight: 650;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-3);
  }
  .result .label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .result .count,
  .entry .count {
    color: var(--text-3);
    font-size: 12px;
  }
  .empty {
    padding: 10px;
    color: var(--text-3);
  }
  .chip {
    position: absolute;
    top: 14px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 2;
    display: flex;
    align-items: center;
    gap: 9px;
    height: 36px;
    padding: 0 6px 0 12px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--panel) 92%, transparent);
    backdrop-filter: blur(14px);
    border: 1px solid var(--accent-line);
    box-shadow: var(--glow);
    font-weight: 550;
    animation: rise 160ms var(--ease);
    max-width: 40%;
  }
  .chip > span:nth-child(2) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .chip .swatch {
    background: var(--swatch);
  }
  .swatch {
    flex: none;
    width: 12px;
    height: 12px;
    border-radius: 4px;
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.25);
  }
  .legend {
    position: absolute;
    top: 14px;
    right: 14px;
    width: 272px;
    max-height: calc(100% - 28px - 150px);
    display: flex;
    flex-direction: column;
    background: color-mix(in srgb, var(--panel) 90%, transparent);
    backdrop-filter: blur(14px);
    box-shadow: var(--shadow-sm);
    z-index: 2;
    overflow: hidden;
  }
  .legend.closed {
    max-height: none;
  }
  .legend-head {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: baseline;
    gap: 10px;
    padding: 12px 14px;
    border: 0;
    background: transparent;
    color: var(--text);
    cursor: pointer;
    text-align: left;
    font: 600 14px var(--font);
  }
  .legend-filter {
    margin: 0 12px 8px;
    width: auto;
    min-height: 30px;
    font-size: 12.5px;
  }
  .entries {
    padding: 0 6px 6px;
    min-height: 0;
  }
  .entry {
    position: relative;
    display: grid;
    grid-template-columns: 12px 1fr auto;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 6px 8px;
    border: 0;
    border-radius: 7px;
    background: transparent;
    color: var(--text);
    font: 500 12.5px var(--font);
    text-align: left;
    cursor: pointer;
    overflow: hidden;
  }
  .entry:hover {
    background: var(--hover);
  }
  .entry.on {
    background: var(--accent-soft);
    box-shadow: inset 0 0 0 1px var(--accent-line);
  }
  .entry .label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .entry .bar {
    position: absolute;
    left: 8px;
    bottom: 2px;
    height: 2px;
    border-radius: 2px;
    opacity: 0.55;
    max-width: calc(100% - 16px);
  }
  .legend-hint {
    padding: 8px 14px 12px;
    font-size: 11.5px;
    border-top: 1px solid var(--line);
  }
  .ramp {
    padding: 0 14px 10px;
  }
  .ramp-bar {
    height: 10px;
    border-radius: 6px;
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.2);
  }
  .ramp-labels {
    display: flex;
    justify-content: space-between;
    font-size: 11.5px;
    margin-top: 4px;
  }
  .inspector {
    position: absolute;
    right: 14px;
    bottom: 14px;
    width: 300px;
    padding: 14px 16px 16px;
    background: color-mix(in srgb, var(--panel) 94%, transparent);
    backdrop-filter: blur(14px);
    box-shadow: var(--shadow);
    border-color: var(--accent-line);
    z-index: 3;
    animation: rise 180ms var(--ease);
  }
  .inspector header {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 10px;
  }
  .inspector h2 {
    font-size: 21px;
    margin-top: 2px;
  }
  dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 6px 14px;
    margin: 0;
    font-size: 13px;
  }
  dt {
    color: var(--text-3);
  }
  dd {
    margin: 0;
    min-width: 0;
  }
  .link {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--text);
    font: inherit;
    cursor: pointer;
    text-align: left;
    text-decoration: underline;
    text-decoration-color: var(--line-3);
    text-underline-offset: 3px;
  }
  .link:hover {
    color: var(--accent);
    text-decoration-color: var(--accent-line);
  }
  .tooltip {
    position: absolute;
    z-index: 4;
    pointer-events: none;
    display: grid;
    gap: 3px;
    max-width: 280px;
    padding: 10px 12px;
    border-radius: 10px;
    background: color-mix(in srgb, var(--panel) 96%, transparent);
    border: 1px solid var(--line-2);
    box-shadow: var(--shadow);
    font-size: 12.5px;
  }
  .tooltip strong {
    font-family: var(--display);
    font-size: 15px;
    font-weight: 600;
  }
  .tip-row {
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .minimap {
    position: absolute;
    left: 14px;
    bottom: 14px;
    padding: 6px;
    background: color-mix(in srgb, var(--panel) 88%, transparent);
    backdrop-filter: blur(14px);
    box-shadow: var(--shadow-sm);
    z-index: 2;
    line-height: 0;
  }
  .minimap canvas {
    width: 196px;
    border-radius: 8px;
    cursor: pointer;
  }
  .zoom {
    position: absolute;
    left: 230px;
    bottom: 14px;
    display: flex;
    align-items: center;
    gap: 2px;
    padding: 4px;
    background: color-mix(in srgb, var(--panel) 88%, transparent);
    backdrop-filter: blur(14px);
    box-shadow: var(--shadow-sm);
    z-index: 2;
  }
  .zoom-value {
    min-width: 46px;
    text-align: center;
    font-size: 12px;
  }
  .compact .stage {
    border-radius: 0;
  }
  @media (max-width: 1100px) {
    .legend {
      width: 230px;
    }
    .zoom {
      left: auto;
      right: 14px;
      bottom: 14px;
    }
    .inspector {
      bottom: 64px;
    }
  }
</style>
