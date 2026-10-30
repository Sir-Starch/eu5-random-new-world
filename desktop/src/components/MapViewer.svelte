<script lang="ts">
  // A world's map: the canvas, its toolbar (overlays, pictures, zoom), the hover card, the card of
  // a location clicked, what is isolated and the minimap. The lens and the legend are chosen in
  // the inspector through the shared session.
  import { onDestroy, onMount, untrack, type Snippet } from "svelte";
  import { app, grouped, t } from "../lib/app.svelte";
  import type { Facts } from "../lib/atlas";
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
  import { createRenderer, type Renderer, type Theme } from "../lib/mapgl";
  import type { MapSession } from "../lib/mapSession.svelte";
  import { copyImage, saveFile } from "../lib/native";
  import Icon from "./Icon.svelte";

  let {
    world,
    session,
    camera = $bindable<Camera | null>(null),
    compact = false,
    lensPicker = false,
    head,
    onCompare,
  }: {
    world: string;
    session: MapSession;
    camera?: Camera | null;
    compact?: boolean;
    /** A lens list in the toolbar, for when the inspector is hidden. */
    lensPicker?: boolean;
    head?: Snippet;
    onCompare?: () => void;
  } = $props();

  let failed = $state(false);
  let loading = $state(true);
  let host: HTMLDivElement;
  let canvas: HTMLCanvasElement;
  let labelCanvas: HTMLCanvasElement;
  let minimap = $state<HTMLCanvasElement>();
  let renderer: Renderer | null = null;
  let rendererKind = $state("");
  let view = $state({ width: 1, height: 1 });
  let cam = $state<Camera>({ x: 0, y: 0, scale: 1 });
  let hover = $state(-1);
  let pointer = $state({ x: 0, y: 0 });
  let frame = 0;
  let animation = 0;
  let drag = $state<{ x: number; y: number; cam: Camera; moved: boolean } | null>(null);
  let observer: ResizeObserver | null = null;
  let theme: Theme = { ink: [10, 12, 16], accent: [220, 174, 90] };

  const atlas = $derived(session.atlas);
  const facts = $derived<Facts | null>(atlas ? atlas.facts(session.pinned >= 0 ? session.pinned : hover) : null);
  const hoverFacts = $derived<Facts | null>(atlas && hover >= 0 ? atlas.facts(hover) : null);
  const zoomPercent = $derived(Math.round(cam.scale * 100));

  // -- loading -----------------------------------------------------------------------------------

  $effect(() => {
    const id = world;
    untrack(() => {
      loading = true;
      failed = false;
      session.pinned = -1;
      session.match = null;
      session.atlas = null;
      hover = -1;
    });
    void loadAtlas(id).then((found) => {
      if (id !== world) return;
      loading = false;
      if (!found) {
        failed = true;
        return;
      }
      session.atlas = found;
      setup(found);
    });
  });

  function setup(found: NonNullable<typeof atlas>): void {
    renderer?.dispose();
    renderer = createRenderer(canvas, found);
    rendererKind = renderer.kind;
    canvas = renderer.canvas;
    renderer.setAtlas(found);
    renderer.setLens(session.layer);
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
      accent: parse("--map-accent", [255, 213, 74]),
    };
  }

  // -- drawing -----------------------------------------------------------------------------------

  function request(): void {
    if (!frame) frame = requestAnimationFrame(draw);
  }

  function draw(): void {
    frame = 0;
    if (!renderer || !atlas) return;
    renderer.draw(cam, session.overlays, theme);
    drawLabels();
    drawMinimapView();
  }

  function resize(): void {
    if (!host) return;
    const rect = host.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const before = view;
    view = { width: Math.max(1, rect.width), height: Math.max(1, rect.height) };
    for (const target of [canvas, labelCanvas]) {
      if (!target) continue;
      target.width = Math.round(view.width * dpr);
      target.height = Math.round(view.height * dpr);
    }
    // A pane shown or hidden keeps what was in the middle of the view in the middle.
    if (atlas && before.width > 1 && (before.width !== view.width || before.height !== view.height)) {
      const [ax, ay] = toAtlas(cam, before.width / 2, before.height / 2);
      setCamera({ scale: cam.scale, x: ax - view.width / 2 / cam.scale, y: ay - view.height / 2 / cam.scale });
    }
    request();
  }

  function drawLabels(): void {
    const context = labelCanvas?.getContext("2d");
    if (!context || !atlas) return;
    const dpr = window.devicePixelRatio || 1;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, view.width, view.height);
    if (!session.overlays.labels) return;
    const placed: [number, number, number, number][] = [];
    const light = theme.ink[0] > 30;
    const fill = light ? "rgba(36, 26, 12, 0.92)" : "rgba(246, 240, 226, 0.95)";
    const halo = light ? "rgba(250, 244, 230, 0.85)" : "rgba(6, 8, 12, 0.78)";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.lineJoin = "round";
    const layer = session.layer;
    const labels = atlas.labelsFor(layer);
    for (const label of labels) {
      const size = Math.min(26, Math.sqrt(label.weight) * cam.scale * 0.21);
      if (size < 10) continue;
      const [sx, sy] = toScreen(cam, label.x, label.y);
      if (sx < -200 || sy < -40 || sx > view.width + 200 || sy > view.height + 40) continue;
      const upper = layer === "countries";
      const text = upper ? label.text.toLocaleUpperCase() : label.text;
      context.font = `${upper ? 600 : 500} ${size.toFixed(1)}px "Noto Sans Variable", "Noto Sans", sans-serif`;
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
    const current = found.lens(session.layer);
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

  function fitAll(): void {
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
      session.pinned = cell === session.pinned ? -1 : cell;
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
    const shown = session.preview ?? session.match?.cells ?? null;
    const h = hover;
    const p = session.pinned;
    if (renderer && atlas) {
      renderer.setFlags(h, p, shown);
      request();
    }
  });

  $effect(() => {
    const current = session.layer;
    if (renderer && atlas) {
      untrack(() => {
        renderer?.setLens(current);
        paintMinimap();
        request();
      });
    }
  });

  $effect(() => {
    $state.snapshot(session.overlays);
    untrack(() => session.remember());
    request();
  });

  const isolate = (label: string, cells: number[], colour?: string, zoom = false): void =>
    session.isolate(label, cells, colour, zoom);

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
    const layer = session.layer;
    const name = `${(atlas?.data.name ?? "world").replace(/\s+/g, "-")}-${layer}.png`;
    const path = await saveFile(t("save_picture"), name, [{ name: "PNG", extensions: ["png"] }]);
    if (path) await app.report("save_map", { id: world, layer, path }, t("picture_saved", { path }));
  }

  async function copyView(): Promise<void> {
    if (!renderer) return;
    renderer.draw(cam, session.overlays, theme);
    const out = document.createElement("canvas");
    out.width = renderer.canvas.width;
    out.height = renderer.canvas.height;
    const context = out.getContext("2d");
    if (!context) return;
    context.fillStyle = getComputedStyle(host).getPropertyValue("--map-bg") || "#14171b";
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
      if (layers[index]) session.layer = layers[index];
    } else if (event.key === "+" || event.key === "=") zoomBy(1.6);
    else if (event.key === "-") zoomBy(1 / 1.6);
    else if (event.key.toLowerCase() === "f" && !event.ctrlKey) fitAll();
    else if (event.key.toLowerCase() === "l" && !event.ctrlKey) session.overlays.labels = !session.overlays.labels;
    else if (event.key.toLowerCase() === "b" && !event.ctrlKey && !event.metaKey) session.overlays.political = !session.overlays.political;
    else if (event.key === "Escape" && (session.pinned >= 0 || session.match)) {
      if (session.pinned >= 0) session.pinned = -1;
      else session.match = null;
    } else return;
    event.preventDefault();
  }

  onMount(() => {
    if (!compact) session.zoomTo = zoomToCells;
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
    if (!compact) session.zoomTo = () => {};
    session.atlas = null;
    session.preview = null;
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

</script>

<div class="viewer" class:compact data-renderer={rendererKind}>
  {#if !compact}
    <div class="pane-head toolbar">
      {@render head?.()}
      <span class="spacer"></span>
      {#if lensPicker}
        <select class="input lens" bind:value={session.layer} aria-label={t("shortcut.lenses")} title={t("shortcut.lenses")}>
          {#each app.info?.layers ?? [] as name, index (name)}
            <option value={name}>{index === 9 ? 0 : index + 1} · {t(`layer.${name}`)}</option>
          {/each}
        </select>
        <span class="tsep"></span>
      {/if}
      <div class="group">
        <button class="btn icon small ghost" class:active={session.overlays.political} title={`${t("map.political")} (B)`} aria-pressed={session.overlays.political} onclick={() => (session.overlays.political = !session.overlays.political)}>
          <Icon name="borders" />
        </button>
        <button class="btn icon small ghost" class:active={session.overlays.labels} title={`${t("map.labels")} (L)`} aria-pressed={session.overlays.labels} onclick={() => (session.overlays.labels = !session.overlays.labels)}>
          <Icon name="labels" />
        </button>
        <button class="btn icon small ghost" class:active={session.overlays.locations} title={t("map.locations")} aria-pressed={session.overlays.locations} onclick={() => (session.overlays.locations = !session.overlays.locations)}>
          <Icon name="grid" />
        </button>
      </div>
      <span class="tsep"></span>
      <div class="group export">
        <button class="btn icon small ghost" title={t("map.copy_view")} aria-label={t("map.copy_view")} onclick={copyView}><Icon name="image" /></button>
        <button class="btn icon small ghost" title={t("save_picture_tip")} aria-label={t("save_picture")} onclick={savePicture}><Icon name="download" /></button>
        {#if onCompare}
          <button class="btn icon small ghost" title={t("compare_title")} aria-label={t("compare_title")} onclick={onCompare}><Icon name="compare" /></button>
        {/if}
      </div>
      <span class="tsep export"></span>
      <div class="group zoom">
        <button class="btn icon small ghost" title={`${t("map.zoom_out")} (−)`} aria-label={t("map.zoom_out")} onclick={() => zoomBy(1 / 1.6)}><Icon name="zoomOut" /></button>
        <span class="num zoom-value" title={t("zoom_hint")}>{zoomPercent}%</span>
        <button class="btn icon small ghost" title={`${t("map.zoom_in")} (+)`} aria-label={t("map.zoom_in")} onclick={() => zoomBy(1.6)}><Icon name="zoomIn" /></button>
        <button class="btn icon small ghost" title={`${t("map.fit")} (F)`} aria-label={t("map.fit")} onclick={fitAll}><Icon name="fit" /></button>
      </div>
      <span class="tsep"></span>
      <button class="btn icon small ghost" class:active={app.focus} title={t("map.focus")} aria-label={t("map.focus")} aria-pressed={app.focus} onclick={() => (app.focus = !app.focus)}>
        <Icon name={app.focus ? "shrink" : "expand"} />
      </button>
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
      <div class="veil"><span>{t("no_atlas")}</span></div>
    {/if}

    {#if !compact && atlas}
      {#if session.match}
        <div class="chip" style:--swatch={session.match.colour ?? "var(--accent)"}>
          <span class="swatch"></span>
          <span>{t("map.showing", { name: session.match.label })}</span>
          <span class="faint num">{grouped(session.match.cells.size)}</span>
          <button class="btn icon small ghost" aria-label={t("map.clear")} title={`${t("map.clear")} (Esc)`} onclick={() => (session.match = null)}>
            <Icon name="x" />
          </button>
        </div>
      {/if}

      {#if session.pinned >= 0 && facts}
        <section class="card" aria-live="polite">
          <header>
            <div>
              <span class="eyebrow">{t(`kind.${facts.kind}`)}</span>
              <h2>{facts.name}</h2>
              {#if facts.area}<p class="faint">{facts.area}{facts.region ? ` · ${facts.region}` : ""}</p>{/if}
            </div>
            <button class="btn icon small ghost" aria-label={t("close")} title={`${t("close")} (Esc)`} onclick={() => (session.pinned = -1)}><Icon name="x" /></button>
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

      {#if hoverFacts && hover !== session.pinned && !drag?.moved}
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

      <div class="minimap">
        <canvas bind:this={minimap} onpointerdown={miniPointer} onpointermove={miniPointer} aria-label={t("map.minimap")} title={t("map.minimap")}></canvas>
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
    gap: 2px;
    overflow: hidden;
    container-type: inline-size;
  }
  .group {
    flex: none;
    display: flex;
    align-items: center;
    gap: 1px;
  }
  .toolbar .active {
    background: var(--accent-soft);
    color: var(--text);
  }
  .lens {
    flex: 0 1 auto;
    width: auto;
    min-width: 0;
    height: 22px;
    font-size: 12px;
  }
  .zoom-value {
    min-width: 38px;
    text-align: center;
    color: var(--text-2);
    font-size: 11.5px;
  }
  .stage {
    position: relative;
    flex: 1;
    min-height: 0;
    overflow: hidden;
    background: var(--map-bg);
    container-type: size;
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
    gap: 8px;
    color: var(--text-2);
    text-align: center;
    padding: 24px;
  }
  .chip,
  .card,
  .tooltip,
  .minimap {
    background: var(--panel);
    border: 1px solid var(--line-2);
    border-radius: var(--radius);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
  }
  .chip {
    position: absolute;
    top: 8px;
    left: 8px;
    z-index: 2;
    display: flex;
    align-items: center;
    gap: 6px;
    height: 26px;
    max-width: calc(100% - 16px - 296px);
    min-width: 0;
    padding: 0 2px 0 8px;
    font-size: 12.5px;
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
    width: 10px;
    height: 10px;
    border-radius: 1px;
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.3);
  }
  .card {
    position: absolute;
    top: 8px;
    right: 8px;
    width: min(280px, calc(100% - 16px));
    padding: 8px 10px 10px;
    z-index: 3;
  }
  .card header {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 6px;
  }
  .card h2 {
    font-size: 13px;
  }
  .card header p {
    font-size: 12px;
  }
  .eyebrow {
    font-size: 11px;
    color: var(--text-3);
  }
  dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 3px 10px;
    margin: 0;
    font-size: 12px;
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
    gap: 6px;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--accent-text);
    font: inherit;
    text-align: left;
  }
  .link:hover {
    text-decoration: underline;
  }
  .tooltip {
    position: absolute;
    z-index: 4;
    pointer-events: none;
    display: grid;
    gap: 2px;
    max-width: 260px;
    padding: 6px 8px;
    box-shadow: var(--shadow);
    font-size: 12px;
  }
  .tooltip strong {
    font-size: 12.5px;
    font-weight: 600;
  }
  .tip-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .minimap {
    position: absolute;
    left: 8px;
    bottom: 8px;
    padding: 2px;
    z-index: 2;
    line-height: 0;
  }
  .minimap canvas {
    width: 144px;
  }
  @container (max-width: 560px) {
    .toolbar :global(.pane-title),
    .toolbar :global(.pane-sub) {
      display: none;
    }
  }
  @container (max-width: 400px) {
    .export,
    .zoom-value {
      display: none;
    }
  }
  @container (max-width: 560px) {
    .minimap {
      display: none;
    }
    .chip {
      max-width: calc(100% - 16px);
    }
  }
</style>
