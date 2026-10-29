<script lang="ts">
  import { app, t, when } from "../lib/app.svelte";
  import type { LibraryEntry } from "../lib/types";
  import Icon from "./Icon.svelte";
  import Thumb from "./Thumb.svelte";

  let { onOpenFile }: { onOpenFile: () => void } = $props();

  let filter = $state("");
  let view = $state<"all" | "in_game" | "starred">("all");
  let anchor = $state("");

  const s = $derived(app.now);
  const entries = $derived.by(() => {
    const needle = filter.trim().toLocaleLowerCase();
    return (s?.library ?? []).filter((entry) => {
      if (view === "in_game" && entry.placement !== "in_game") return false;
      if (view === "starred" && !entry.starred) return false;
      if (!needle) return true;
      return [entry.title, entry.tag, entry.type, entry.folder, entry.id]
        .filter(Boolean)
        .some((text) => String(text).toLocaleLowerCase().includes(needle));
    });
  });
  const ticked = $derived(new Set(app.ticked));
  const installed = $derived(
    (s?.library ?? []).filter((e) => ticked.has(e.id) && e.placement === "in_game").length,
  );
  const worlds = $derived((s?.library ?? []).filter((e) => ticked.has(e.id) && e.kind === "world"));
  const generating = $derived(s?.busy && (s.task === "generate" || s.task === "queue"));
  const percent = $derived(Math.round((s?.fraction ?? 0) * 100));

  function pick(entry: LibraryEntry, event: MouseEvent): void {
    const ids = entries.map((e) => e.id);
    if (event.shiftKey && anchor && ids.includes(anchor)) {
      const [a, b] = [ids.indexOf(anchor), ids.indexOf(entry.id)].sort((x, y) => x - y);
      app.ticked = ids.slice(a, b + 1);
    } else if (event.ctrlKey || event.metaKey) {
      app.ticked = ticked.has(entry.id)
        ? app.ticked.filter((id) => id !== entry.id)
        : [...app.ticked, entry.id];
      anchor = entry.id;
      return;
    } else {
      app.ticked = [entry.id];
      anchor = entry.id;
    }
    void app.call("select", { id: entry.id });
  }

  function toggle(entry: LibraryEntry, event: Event): void {
    event.stopPropagation();
    app.ticked = ticked.has(entry.id)
      ? app.ticked.filter((id) => id !== entry.id)
      : [...app.ticked, entry.id];
    anchor = entry.id;
  }

  function key(event: KeyboardEvent): void {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const ids = ["new", ...entries.map((e) => e.id)];
    const at = ids.indexOf(s?.selection ?? "new");
    const next = ids[Math.max(0, Math.min(ids.length - 1, at + (event.key === "ArrowDown" ? 1 : -1)))];
    app.ticked = next === "new" ? [] : [next];
    void app.call("select", { id: next });
    requestAnimationFrame(() =>
      document.querySelector<HTMLElement>(`[data-entry="${next}"]`)?.focus(),
    );
  }

  async function removeTicked(): Promise<void> {
    await app.act("remove_entries", { ids: app.ticked });
  }

  async function deleteTicked(): Promise<void> {
    const names = worlds.map((w) => `• ${w.title}`).join("\n");
    const sure = await app.confirm(
      t("delete_many_title", { count: worlds.length }),
      t("delete_many_question", { count: worlds.length, names }),
      t("delete"),
      true,
    );
    if (sure && (await app.act("delete_entries", { ids: worlds.map((w) => w.id) }))) {
      app.ticked = [];
    }
  }

</script>

<aside class="sidebar">
  <div class="brand">
    <div class="mark" aria-hidden="true">
      <svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="13" /><path d="M6 13c5 1 7-3 11-2s5 5 9 4M5.5 20c4-1 6 2 10 1s6-4 11-2" /></svg>
    </div>
    <div class="brand-text">
      <strong>{app.info?.title}</strong>
      <span class="faint num">v{app.info?.version}</span>
    </div>
  </div>

  <button
    class="new"
    class:on={s?.selection === "new"}
    data-entry="new"
    onclick={() => { app.ticked = []; void app.call("select", { id: "new" }); }}
    onkeydown={key}
  >
    <span class="plus"><Icon name={generating ? "sparkles" : "plus"} size={17} /></span>
    <span class="new-text">
      <strong>{t("new_world")}</strong>
      {#if generating}<span class="faint num">{percent} %</span>{/if}
    </span>
    {#if generating}<span class="new-bar" style:width={`${percent}%`}></span>{/if}
  </button>

  <div class="find">
    <Icon name="search" size={15} />
    <input class="find-input" placeholder={t("library.filter")} bind:value={filter} aria-label={t("library.filter")} />
  </div>
  <div class="views" role="tablist">
    {#each [["all", t("library.all")], ["in_game", t("library.in_game")], ["starred", t("starred")]] as [key, label] (key)}
      <button role="tab" aria-selected={view === key} class:on={view === key} onclick={() => (view = key as typeof view)}>{label}</button>
    {/each}
  </div>

  <div class="list scroll" role="listbox" aria-multiselectable="true" aria-label={t("worlds")}>
    {#each entries as entry (entry.id)}
      <div
        class="entry"
        class:on={s?.selection === entry.id}
        class:ticked={ticked.has(entry.id) && app.ticked.length > 1}
        class:version={(entry.depth ?? 0) > 0}
        role="option"
        aria-selected={ticked.has(entry.id) || s?.selection === entry.id}
        tabindex="0"
        data-entry={entry.id}
        onclick={(event) => pick(entry, event)}
        onkeydown={(event) => (event.key === "Enter" || event.key === " " ? pick(entry, event as unknown as MouseEvent) : key(event))}
      >
        <button class="tick" class:shown={ticked.has(entry.id) && app.ticked.length > 1} aria-label={t("library.tick")} onclick={(event) => toggle(entry, event)}>
          {#if ticked.has(entry.id) && app.ticked.length > 1}<Icon name="check" size={12} stroke={3} />{/if}
        </button>
        <div class="thumb">
          {#if entry.kind === "world"}
            <Thumb id={entry.id} version={entry.picture ?? ""} />
          {:else}
            <span class="stray"><Icon name="alert" size={18} /></span>
          {/if}
          {#if entry.placement === "in_game"}<span class="live" title={t("list.in_game")}></span>{/if}
        </div>
        <div class="text">
          <span class="title">
            {#if entry.starred}<Icon name="star" size={12} fill />{/if}
            {entry.title}
          </span>
          <span class="meta faint">
            {#if entry.kind === "stray"}
              {entry.folder}
            {:else}
              {entry.part || entry.type} · {when(entry.created ?? 0)}
            {/if}
          </span>
          {#if entry.tag}<span class="tag">{entry.tag}</span>{/if}
        </div>
      </div>
    {:else}
      <div class="empty faint">{s?.library.length ? t("library.no_match") : t("library.empty")}</div>
    {/each}
  </div>

  {#if app.ticked.length > 1 || s?.batch}
    <div class="batch">
      <div class="batch-line">
        <span class="num">{t("selection_count", { count: app.ticked.length, installed })}</span>
        <button class="btn small ghost" onclick={() => (app.ticked = [])}>{t("library.clear")}</button>
      </div>
      {#if app.ticked.length > 1}
        <div class="batch-actions">
          <button class="btn small" disabled={!installed || s?.busy} title={t("remove_tip")} onclick={removeTicked}>
            <Icon name="eyeOff" size={14} />{t("library_remove", { count: installed })}
          </button>
          <button class="btn small danger" disabled={!worlds.length || s?.busy} title={t("delete_tip")} onclick={deleteTicked}>
            <Icon name="trash" size={14} />{t("library_delete", { count: worlds.length })}
          </button>
        </div>
      {/if}
      {#if s?.batch}<p class="batch-status selectable">{s.batch}</p>{/if}
    </div>
  {:else if entries.length > 1}
    <button class="btn small ghost select-all" onclick={() => (app.ticked = entries.map((e) => e.id))}>{t("select_all_worlds")}</button>
  {/if}

  {#if s?.busy && s.task !== "generate" && s.task !== "queue"}
    <div class="task">
      <span class="spinner"></span>
      <span class="task-text">{s.running || t(`task.${s.task}`)}</span>
    </div>
  {/if}

  <footer>
    <button class="game" class:problem={!!s?.game.problem} title={s?.game.problem || `${s?.game.directory}\n${s?.game.profile}`} onclick={() => (app.modal = { kind: "settings" })}>
      <span class="dot"></span>
      <span class="game-text">{s?.game.problem ? t(s.game.found ? "library.no_profile" : "library.no_game") : s?.game.status}</span>
    </button>
    <div class="footer-actions">
      <button class="btn icon ghost" title={t("open_world_file_tip")} aria-label={t("open_world_file")} onclick={onOpenFile}><Icon name="open" /></button>
      <button class="btn icon ghost" title={t("settings_title")} aria-label={t("settings_title")} onclick={() => (app.modal = { kind: "settings" })}><Icon name="settings" /></button>
      <button class="btn icon ghost" title={t("about_title")} aria-label={t("about_title")} onclick={() => (app.modal = { kind: "about" })}><Icon name="info" /></button>
    </div>
    <span class="resources faint num">{s?.resources}</span>
  </footer>
</aside>

<style>
  .sidebar {
    display: flex;
    flex-direction: column;
    min-height: 0;
    height: 100%;
    background: var(--bg-2);
    border-right: 1px solid var(--line);
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 11px;
    padding: 18px 18px 14px;
  }
  .mark svg {
    width: 30px;
    height: 30px;
    fill: none;
    stroke: var(--accent);
    stroke-width: 1.6;
    stroke-linecap: round;
  }
  .mark circle {
    fill: var(--accent-soft);
  }
  .brand-text {
    display: grid;
    line-height: 1.2;
  }
  .brand-text strong {
    font-family: var(--display);
    font-size: 16px;
    font-weight: 600;
  }
  .brand-text span {
    font-size: 11.5px;
  }
  .new {
    position: relative;
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 4px 12px 12px;
    padding: 10px 12px;
    border-radius: 12px;
    border: 1px solid var(--line-2);
    background: var(--panel);
    color: var(--text);
    cursor: pointer;
    text-align: left;
    overflow: hidden;
    transition: all var(--speed) var(--ease);
  }
  .new:hover {
    border-color: var(--accent-line);
  }
  .new.on {
    border-color: var(--accent-line);
    box-shadow: var(--glow);
  }
  .plus {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 9px;
    background: linear-gradient(180deg, var(--accent-2), var(--accent));
    color: var(--on-accent);
  }
  .new-text {
    display: flex;
    flex: 1;
    justify-content: space-between;
    align-items: baseline;
  }
  .new-bar {
    position: absolute;
    left: 0;
    bottom: 0;
    height: 2px;
    background: var(--accent);
    transition: width 300ms var(--ease);
  }
  .find {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 12px;
    padding: 0 10px;
    height: 34px;
    border-radius: 9px;
    background: var(--panel);
    border: 1px solid var(--line);
    color: var(--text-3);
  }
  .find:focus-within {
    border-color: var(--accent-line);
  }
  .find-input {
    flex: 1;
    min-width: 0;
    border: 0;
    background: transparent;
    color: var(--text);
    font: 450 13px var(--font);
    outline: none;
    user-select: text;
  }
  .views {
    display: flex;
    gap: 2px;
    padding: 8px 12px 6px;
  }
  .views button {
    flex: 1;
    height: 26px;
    border: 0;
    border-radius: 7px;
    background: transparent;
    color: var(--text-3);
    font: 600 12px var(--font);
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .views button.on {
    background: var(--panel-2);
    color: var(--text);
  }
  .list {
    flex: 1;
    min-height: 0;
    padding: 4px 8px 8px;
  }
  .entry {
    position: relative;
    display: grid;
    grid-template-columns: 76px 1fr;
    gap: 11px;
    align-items: center;
    padding: 7px 8px;
    border-radius: 11px;
    cursor: pointer;
    transition: background var(--speed) var(--ease);
    outline-offset: -2px;
  }
  .entry:hover {
    background: var(--hover);
  }
  .entry.on {
    background: var(--panel-2);
    box-shadow: inset 0 0 0 1px var(--line-2);
  }
  .entry.ticked {
    background: var(--accent-soft);
    box-shadow: inset 0 0 0 1px var(--accent-line);
  }
  .entry.version {
    margin-left: 18px;
    grid-template-columns: 60px 1fr;
  }
  .entry.version::before {
    content: "";
    position: absolute;
    left: -10px;
    top: -6px;
    width: 9px;
    height: 26px;
    border-left: 1.5px solid var(--line-3);
    border-bottom: 1.5px solid var(--line-3);
    border-bottom-left-radius: 6px;
  }
  .tick {
    position: absolute;
    left: 2px;
    top: 2px;
    z-index: 1;
    width: 18px;
    height: 18px;
    display: grid;
    place-items: center;
    padding: 0;
    border-radius: 6px;
    border: 1.5px solid var(--line-3);
    background: var(--panel);
    color: var(--on-accent);
    cursor: pointer;
    opacity: 0;
    transition: opacity var(--speed) var(--ease);
  }
  .entry:hover .tick,
  .tick.shown,
  .tick:focus-visible {
    opacity: 1;
  }
  .tick.shown {
    background: var(--accent);
    border-color: var(--accent);
  }
  .thumb {
    position: relative;
    aspect-ratio: 2 / 1;
    border-radius: 7px;
    overflow: hidden;
    background: var(--panel-3);
    box-shadow: inset 0 0 0 1px var(--line);
  }
  .stray {
    display: grid;
    place-items: center;
    height: 100%;
    color: var(--warn);
  }
  .live {
    position: absolute;
    right: 4px;
    bottom: 4px;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--ok);
    box-shadow: 0 0 0 2px var(--bg-2), 0 0 10px var(--ok);
  }
  .text {
    display: grid;
    min-width: 0;
    line-height: 1.3;
  }
  .title {
    display: flex;
    align-items: center;
    gap: 5px;
    font-weight: 600;
    font-size: 13.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .title :global(svg) {
    color: var(--accent);
    flex: none;
  }
  .meta {
    font-size: 11.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tag {
    justify-self: start;
    margin-top: 3px;
    padding: 0 7px;
    border-radius: 999px;
    background: var(--sea-soft);
    color: var(--sea);
    font-size: 10.5px;
    font-weight: 600;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .empty {
    padding: 24px 12px;
    text-align: center;
    font-size: 13px;
  }
  .batch {
    margin: 0 10px 8px;
    padding: 10px;
    border-radius: 12px;
    background: var(--panel);
    border: 1px solid var(--accent-line);
    display: grid;
    gap: 8px;
    animation: rise 160ms var(--ease);
  }
  .batch-line {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12.5px;
    font-weight: 600;
  }
  .batch-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }
  .batch-actions .btn {
    padding: 0 8px;
    overflow: hidden;
  }
  .batch-status {
    font-size: 12px;
    color: var(--text-2);
    overflow-wrap: anywhere;
  }
  .select-all {
    margin: 0 12px 6px;
    align-self: flex-start;
  }
  .task {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 12px 8px;
    padding: 8px 10px;
    border-radius: 10px;
    background: var(--panel);
    font-size: 12.5px;
    color: var(--text-2);
  }
  .task-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .spinner {
    flex: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid var(--line-2);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
  }
  footer {
    display: grid;
    gap: 6px;
    padding: 10px 12px 12px;
    border-top: 1px solid var(--line);
  }
  .game {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 7px 10px;
    border-radius: 9px;
    border: 1px solid var(--line);
    background: var(--panel);
    color: var(--text-2);
    font: 550 12px var(--font);
    cursor: pointer;
    text-align: left;
  }
  .game .dot {
    flex: none;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--ok);
    box-shadow: 0 0 8px var(--ok);
  }
  .game.problem .dot {
    background: var(--warn);
    box-shadow: 0 0 8px var(--warn);
  }
  .game.problem {
    color: var(--warn);
    border-color: color-mix(in srgb, var(--warn) 35%, transparent);
  }
  .game-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .footer-actions {
    display: flex;
    gap: 2px;
  }
  .resources {
    font-size: 11px;
  }
</style>
