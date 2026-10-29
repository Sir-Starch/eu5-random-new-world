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
    <Icon name="alert" size={32} />
    <h1>{app.info?.title ?? "Random New World"}</h1>
    <p class="selectable mono">{app.failed}</p>
  </div>
{:else if !s}
  <div class="splash">
    <div class="mark" aria-hidden="true">
      <svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="13" /><path d="M6 13c5 1 7-3 11-2s5 5 9 4M5.5 20c4-1 6 2 10 1s6-4 11-2" /></svg>
    </div>
  </div>
{:else}
  <div class="shell" class:focus={app.mapFocus && page === "world" && app.worldTab === "map"}>
    <div class="side"><Sidebar onOpenFile={openWorldFile} /></div>
    <main>
      {#if s.game.problem}
        <div class="banner">
          <Icon name="warning" size={16} />
          <span>{s.game.problem}</span>
          <button class="btn small" onclick={() => (app.modal = { kind: "settings" })}>{t("settings_title")}</button>
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
    grid-template-columns: 296px minmax(0, 1fr);
    height: 100vh;
    transition: grid-template-columns 240ms var(--ease);
    background:
      radial-gradient(1200px 600px at 85% -10%, color-mix(in srgb, var(--accent) 7%, transparent), transparent 60%),
      radial-gradient(900px 500px at 10% 110%, color-mix(in srgb, var(--sea) 7%, transparent), transparent 60%),
      var(--bg);
  }
  .shell.focus {
    grid-template-columns: 0 minmax(0, 1fr);
  }
  .side {
    min-width: 0;
    overflow: hidden;
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
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 20px;
    background: var(--warn-soft);
    border-bottom: 1px solid color-mix(in srgb, var(--warn) 30%, transparent);
    color: var(--text);
    font-size: 13px;
  }
  .banner :global(svg) {
    color: var(--warn);
    flex: none;
  }
  .banner span {
    flex: 1;
  }
  .splash,
  .fatal {
    height: 100vh;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: 14px;
    padding: 40px;
    text-align: center;
  }
  .fatal :global(svg) {
    color: var(--danger);
  }
  .splash svg {
    width: 64px;
    height: 64px;
    fill: none;
    stroke: var(--accent);
    stroke-width: 1.4;
    stroke-linecap: round;
    animation: fade 1.2s ease-in-out infinite alternate;
  }
  .splash circle {
    fill: var(--accent-soft);
  }
  @media (max-width: 1000px) {
    .shell {
      grid-template-columns: 250px minmax(0, 1fr);
    }
  }
</style>
