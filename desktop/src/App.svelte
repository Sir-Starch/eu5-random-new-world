<script lang="ts">
  import { onMount } from "svelte";
  import About from "./components/About.svelte";
  import Candidates from "./components/Candidates.svelte";
  import Compare from "./components/Compare.svelte";
  import Dialogs from "./components/Dialogs.svelte";
  import Icon from "./components/Icon.svelte";
  import NewWorld from "./components/NewWorld.svelte";
  import Settings from "./components/Settings.svelte";
  import Sidebar from "./components/Sidebar.svelte";
  import StrayPage from "./components/StrayPage.svelte";
  import Toasts from "./components/Toasts.svelte";
  import WorldPage from "./components/WorldPage.svelte";
  import { app, t } from "./lib/app.svelte";
  import { onDrop, openFile } from "./lib/native";

  const s = $derived(app.now);
  const page = $derived(
    !s ? "loading" : s.world ? "world" : s.stray ? "stray" : "new",
  );
  const generating = $derived(!!s?.busy && (s.task === "generate" || s.task === "queue"));
  const percent = $derived(Math.round((s?.fraction ?? 0) * 100));
  let sketched = 0;
  let lastSelection = "";
  let lastResult = "";

  // Sketches are shown once, when they are done.
  $effect(() => {
    const now = app.now;
    if (now && now.task === "candidates" && now.phase === "finished" && now.runs !== sketched && now.candidates.length) {
      sketched = now.runs;
      app.modal = { kind: "candidates" };
    }
    if (now && now.phase === "failed" && ["receive", "send", "copy", "template", "candidates"].includes(now.task ?? "")) {
      const key = `${now.runs}`;
      if (key !== lastResult) {
        lastResult = key;
        app.toast("error", now.message);
      }
    }
  });

  // A new world page opens on its overview; a world keeps its tab while it stays selected.
  $effect(() => {
    const selection = app.now?.selection ?? "";
    if (selection !== lastSelection) {
      if (lastSelection && app.worldTab !== "map") app.worldTab = "overview";
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

  function key(event: KeyboardEvent): void {
    const control = event.ctrlKey || event.metaKey;
    if (app.modal && event.key !== "Escape") return;
    if (control && event.key.toLowerCase() === "n") {
      app.ticked = [];
      void app.call("select", { id: "new" });
    } else if (control && event.key.toLowerCase() === "o") {
      void openWorldFile();
    } else if (control && event.key === ",") {
      app.modal = { kind: "settings" };
    } else if (control && event.key === "Enter" && page === "new") {
      void app.act("start");
    } else if ((event.key === "?" || event.key === "F1") && !editing(event.target)) {
      app.modal = { kind: "shortcuts" };
    } else if (event.key === "Escape" && app.mapFocus && !app.modal) {
      app.mapFocus = false;
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

  /** ``#world=ID&tab=map`` opens a world's tab at start (a link into the window). */
  async function deepLink(): Promise<void> {
    const wanted = new URLSearchParams(location.hash.slice(1));
    const world = wanted.get("world");
    if (!world) return;
    await app.call("select", { id: world });
    const tab = wanted.get("tab");
    if (tab === "overview" || tab === "map" || tab === "versions" || tab === "share" || tab === "notes") {
      app.worldTab = tab;
    }
  }

  // The library's width, dragged at its edge and kept per machine like the theme.
  const WIDTH = "rnw.library";
  let side = $state(storedWidth());
  function storedWidth(): number {
    try {
      const value = Number(localStorage.getItem(WIDTH));
      return value >= 180 && value <= 440 ? value : 240;
    } catch {
      return 240;
    }
  }
  function resizing(event: PointerEvent): void {
    const handle = event.currentTarget as HTMLElement;
    handle.setPointerCapture(event.pointerId);
    const start = event.clientX - side;
    const move = (next: PointerEvent): void => {
      side = Math.max(180, Math.min(440, next.clientX - start));
    };
    const up = (): void => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", up);
      try {
        localStorage.setItem(WIDTH, String(side));
      } catch {
        // Storage is a convenience.
      }
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
  <div class="shell" class:focus={app.mapFocus && page === "world" && app.worldTab === "map"} style:--side={`${side}px`}>
    <div class="side"><Sidebar onOpenFile={openWorldFile} /></div>
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="splitter" onpointerdown={resizing}></div>
    <main>
      {#if s.game.problem}
        <div class="msg warn banner">
          <Icon name="warning" />
          <span>{s.game.problem}</span>
          <button class="btn small" onclick={() => (app.modal = { kind: "settings" })}>{t("settings")}</button>
        </div>
      {/if}
      <div class="page">
        {#if page === "world"}
          <WorldPage />
        {:else if page === "stray"}
          <StrayPage />
        {:else}
          <NewWorld />
        {/if}
      </div>
    </main>
    <footer class="status">
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
    </footer>
  </div>
{/if}

{#if app.modal?.kind === "settings"}
  <Settings />
{:else if app.modal?.kind === "about"}
  <About />
{:else if app.modal?.kind === "candidates"}
  <Candidates />
{:else if app.modal?.kind === "compare"}
  <Compare layer={app.modal.layer} />
{:else}
  <Dialogs />
{/if}
<Toasts />

<style>
  .shell {
    display: grid;
    grid-template-columns: var(--side) 1px minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) 24px;
    height: 100vh;
  }
  .shell.focus {
    grid-template-columns: 0 0 minmax(0, 1fr);
  }
  .side {
    min-width: 0;
    overflow: hidden;
  }
  .splitter {
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
  .focus .splitter {
    display: none;
  }
  main {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 0;
  }
  .page {
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
    grid-column: 1 / -1;
    display: flex;
    align-items: center;
    gap: 2px;
    min-width: 0;
    padding: 0 4px 0 2px;
    border-top: 1px solid var(--line);
    background: var(--panel);
    font-size: 12px;
    color: var(--text-2);
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
