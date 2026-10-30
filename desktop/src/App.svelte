<script lang="ts">
  import { onMount } from "svelte";
  import About from "./components/About.svelte";
  import Compare from "./components/Compare.svelte";
  import Dialogs from "./components/Dialogs.svelte";
  import Icon from "./components/Icon.svelte";
  import NewWorldPanel from "./components/NewWorldPanel.svelte";
  import NewWorldView from "./components/NewWorldView.svelte";
  import Settings from "./components/Settings.svelte";
  import Sidebar from "./components/Sidebar.svelte";
  import StrayView from "./components/StrayView.svelte";
  import Toasts from "./components/Toasts.svelte";
  import WorldPanel from "./components/WorldPanel.svelte";
  import WorldView from "./components/WorldView.svelte";
  import { app, LIMITS, t } from "./lib/app.svelte";
  import { map } from "./lib/mapSession.svelte";
  import { onDrop, openFile } from "./lib/native";

  const s = $derived(app.now);
  const page = $derived(!s ? "loading" : s.world ? "world" : s.stray ? "stray" : "new");
  const generating = $derived(!!s?.busy && (s.task === "generate" || s.task === "queue"));
  const percent = $derived(Math.round((s?.fraction ?? 0) * 100));
  // The map alone, while a world's map is shown.
  const focused = $derived(app.focus && page === "world" && !!s?.world?.atlas && !!s.world.revealed);
  const library = $derived(app.layout.library && !focused);
  const inspector = $derived(app.layout.inspector && !focused && page !== "stray");
  let lastResult = "";
  let lastSelection = "";

  // Work that has no page of its own reports its failure as a message.
  $effect(() => {
    const now = app.now;
    if (now && now.phase === "failed" && ["receive", "send", "copy", "template", "candidates"].includes(now.task ?? "")) {
      const key = `${now.runs}`;
      if (key !== lastResult) {
        lastResult = key;
        app.toast("error", now.message);
      }
    }
  });

  // The library's selection follows the world shown.
  $effect(() => {
    const selection = app.now?.selection ?? "";
    if (selection !== lastSelection) {
      lastSelection = selection;
      if (!app.ticked.includes(selection) && selection !== "new") app.ticked = [selection];
    }
  });

  async function openWorldFile(): Promise<void> {
    const path = await openFile(t("open_world_file"), [
      { name: t("world_files").replace(/\s*\(.*\)$/, ""), extensions: ["rnworld", "rnworld-mod"] },
    ]);
    if (path) await take(path);
  }

  async function take(path: string): Promise<void> {
    const problem = await app.call<string | null>("import_file", { path });
    if (problem) app.toast("warning", problem);
    else if (!path.toLowerCase().endsWith(".rnworld-mod")) app.toast("success", t("imported"));
  }

  function editing(target: EventTarget | null): boolean {
    const element = target as HTMLElement | null;
    return !!element && (element.tagName === "INPUT" || element.tagName === "TEXTAREA" || element.tagName === "SELECT" || element.isContentEditable);
  }

  function newWorld(): void {
    app.ticked = [];
    void app.call("select", { id: "new" });
  }

  function key(event: KeyboardEvent): void {
    const control = event.ctrlKey || event.metaKey;
    const letter = event.key.toLowerCase();
    if (app.modal && event.key !== "Escape") return;
    if (control && letter === "n") newWorld();
    else if (control && letter === "o") void openWorldFile();
    else if (control && event.key === ",") app.modal = { kind: "settings" };
    else if (control && letter === "b" && !event.shiftKey) app.toggle("library");
    else if (control && letter === "i" && !event.shiftKey) app.toggle("inspector");
    else if (control && event.key === "Enter" && page === "new") void app.act("start");
    else if ((event.key === "?" || event.key === "F1") && !editing(event.target)) app.modal = { kind: "shortcuts" };
    else if (event.key === "Escape" && app.focus && !app.modal && map.pinned < 0 && !map.match) {
      app.focus = false;
      return;
    } else return;
    event.preventDefault();
  }

  function pasted(event: ClipboardEvent): void {
    if (editing(event.target)) return;
    const text = event.clipboardData?.getData("text")?.trim() ?? "";
    if (/^RNW/i.test(text)) {
      event.preventDefault();
      void app.call("select", { id: "new" }).then(() => app.act("set_seed", { value: text }));
    }
  }

  /** ``#world=ID&tab=maps`` opens a world on an inspector tab at start (a link into the window). */
  async function deepLink(): Promise<void> {
    const wanted = new URLSearchParams(location.hash.slice(1));
    const world = wanted.get("world");
    if (!world) return;
    await app.call("select", { id: world });
    const tab = wanted.get("tab") ?? "";
    if (tab === "maps" || tab === "map") app.worldTab = "maps";
    else if (tab === "notes") app.worldTab = "notes";
    else if (tab) app.worldTab = "world";
  }

  /** Drag a pane's inner edge; the width is kept per machine. */
  function resize(event: PointerEvent, pane: "side" | "aside"): void {
    const handle = event.currentTarget as HTMLElement;
    handle.setPointerCapture(event.pointerId);
    const x = event.clientX;
    const width = app.layout[pane];
    const [low, high] = LIMITS[pane];
    const move = (next: PointerEvent): void => {
      const moved = pane === "side" ? next.clientX - x : x - next.clientX;
      app.layout[pane] = Math.max(low, Math.min(high, width + moved));
    };
    const up = (): void => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", up);
      app.saveLayout();
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", up);
  }

  onMount(() => {
    void app.start().then(deepLink);
    void onDrop((paths) => {
      for (const path of paths) {
        if (/\.rnworld(-mod)?$/i.test(path)) {
          void take(path);
          return;
        }
      }
      app.toast("warning", t("not_world_file"));
    });
  });
</script>

<svelte:window onkeydown={key} onpaste={pasted} />

{#if app.failed}
  <div class="fatal">
    <h1><Icon name="alert" />{app.info?.title ?? "Random New World"}</h1>
    <p class="selectable mono">{app.failed}</p>
  </div>
{:else if !s}
  <div class="splash"><span class="spinner"></span><span class="faint">Random New World</span></div>
{:else}
  <div
    class="shell"
    class:no-library={!library}
    class:no-inspector={!inspector}
    style:--side={`${app.layout.side}px`}
    style:--aside={`${app.layout.aside}px`}
  >
    <aside class="library" aria-label={t("worlds")}><Sidebar onOpenFile={openWorldFile} onNew={newWorld} /></aside>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="splitter left" onpointerdown={(event) => resize(event, "side")}></div>
    <main class="center">
      {#if s.game.problem}
        <div class="msg warn banner">
          <Icon name="warning" />
          <span>{s.game.problem}</span>
          <button class="btn small" onclick={() => (app.modal = { kind: "settings" })}>{t("settings")}</button>
        </div>
      {/if}
      <div class="view">
        {#if page === "world"}
          <WorldView />
        {:else if page === "stray"}
          <StrayView />
        {:else}
          <NewWorldView />
        {/if}
      </div>
    </main>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="splitter right" onpointerdown={(event) => resize(event, "aside")}></div>
    <aside class="inspector">
      {#if page === "world"}
        <WorldPanel />
      {:else if page === "new"}
        <NewWorldPanel />
      {/if}
    </aside>
    <footer class="status">
      <button class="btn icon small ghost" class:on={library} aria-pressed={library} title={`${t("panes.library")} (Ctrl+B)`} aria-label={t("panes.library")} onclick={() => app.toggle("library")}><Icon name="sidebarLeft" /></button>
      <button
        class="item game"
        title={s.game.problem || `${s.game.directory}\n${s.game.profile}`}
        onclick={() => (app.modal = { kind: "settings" })}
      >
        <span class="dot" class:ok={!s.game.problem} class:warn={!!s.game.problem}></span>
        <span class="text">{s.game.problem ? t(s.game.found ? "library.no_profile" : "library.no_game") : s.game.status}</span>
      </button>
      {#if s.busy && !(generating && page === "new")}
        <span class="item task">
          <span class="spinner"></span>
          <span class="text">{s.running || (generating ? t("dock.forging") : t(`task.${s.task}`))}</span>
          {#if generating}<span class="num">{percent} %</span>{/if}
        </span>
      {/if}
      <span class="item resources faint num">{s.resources}</span>
      <button class="btn icon small ghost" title={t("settings_title")} aria-label={t("settings_title")} onclick={() => (app.modal = { kind: "settings" })}><Icon name="settings" /></button>
      <button class="btn icon small ghost" title={t("about_title")} aria-label={t("about_title")} onclick={() => (app.modal = { kind: "about" })}><Icon name="info" /></button>
      <button class="btn icon small ghost" class:on={inspector} aria-pressed={inspector} disabled={page === "stray"} title={`${t("panes.inspector")} (Ctrl+I)`} aria-label={t("panes.inspector")} onclick={() => app.toggle("inspector")}><Icon name="sidebarRight" /></button>
    </footer>
    <Toasts />
  </div>
{/if}

{#if app.modal?.kind === "settings"}
  <Settings />
{:else if app.modal?.kind === "about"}
  <About />
{:else if app.modal?.kind === "compare"}
  <Compare layer={app.modal.layer} />
{:else}
  <Dialogs />
{/if}

<style>
  .shell {
    --toast-right: calc(var(--aside) + 13px);
    display: grid;
    grid-template-columns: var(--side) 1px minmax(0, 1fr) 1px var(--aside);
    grid-template-rows: minmax(0, 1fr) 24px;
    height: 100vh;
  }
  .shell.no-library {
    grid-template-columns: 0 0 minmax(0, 1fr) 1px var(--aside);
  }
  .shell.no-inspector {
    --toast-right: 12px;
    grid-template-columns: var(--side) 1px minmax(0, 1fr) 0 0;
  }
  .shell.no-library.no-inspector {
    grid-template-columns: 0 0 minmax(0, 1fr) 0 0;
  }
  .library,
  .inspector {
    grid-row: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
    overflow: hidden;
    background: var(--panel);
  }
  .library {
    grid-column: 1;
  }
  .inspector {
    grid-column: 5;
  }
  .no-library .library,
  .no-library .left,
  .no-inspector .inspector,
  .no-inspector .right {
    display: none;
  }
  .splitter {
    grid-row: 1;
    position: relative;
    background: var(--line);
    cursor: col-resize;
    z-index: 5;
  }
  .splitter::after {
    content: "";
    position: absolute;
    inset: 0 -3px;
  }
  .splitter:hover {
    background: var(--line-3);
  }
  .left {
    grid-column: 2;
  }
  .right {
    grid-column: 4;
  }
  .center {
    grid-row: 1;
    grid-column: 3;
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
  }
  .view {
    flex: 1;
    min-height: 0;
  }
  .banner {
    flex: none;
    align-items: center;
    border-radius: 0;
    border-width: 0 0 1px 3px;
  }
  .banner span {
    flex: 1;
  }
  .status {
    grid-row: 2;
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    gap: 2px;
    min-width: 0;
    padding: 0 2px;
    border-top: 1px solid var(--line);
    background: var(--panel);
    font-size: 12px;
    color: var(--text-2);
  }
  .status .btn.on {
    background: transparent;
    color: var(--accent-text);
  }
  .item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    height: 22px;
    padding: 0 8px;
    white-space: nowrap;
  }
  .item .text {
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .game {
    flex: 0 1 auto;
    border: 0;
    border-radius: var(--radius);
    background: transparent;
    color: inherit;
    font: inherit;
  }
  .game:hover {
    background: var(--hover);
  }
  .task {
    flex: 0 1 auto;
    border-left: 1px solid var(--line);
  }
  .resources {
    margin-left: auto;
    flex: none;
  }
  .splash,
  .fatal {
    height: 100vh;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: 10px;
    padding: 32px;
  }
  .splash {
    grid-auto-flow: column;
    align-items: center;
  }
  .fatal h1 {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .fatal :global(svg) {
    color: var(--danger);
  }
  .fatal p {
    max-width: 720px;
    overflow-wrap: anywhere;
  }
</style>
