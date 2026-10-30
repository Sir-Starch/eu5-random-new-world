<script lang="ts">
  import { app, t } from "../lib/app.svelte";
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
  const day = $derived(new Intl.DateTimeFormat(app.locale, { dateStyle: "short" }));

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

  function pickNew(): void {
    app.ticked = [];
    void app.call("select", { id: "new" });
  }

  function key(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "a") {
      event.preventDefault();
      app.ticked = entries.map((e) => e.id);
      return;
    }
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
  <div class="head">
    <h2>{t("worlds")}</h2>
    <span class="faint num">{s?.library.filter((e) => e.kind === "world").length ?? 0}</span>
    <button class="btn icon small ghost open" title={t("open_world_file_tip")} aria-label={t("open_world_file")} onclick={onOpenFile}><Icon name="open" /></button>
  </div>
  <div class="find">
    <label class="search">
      <Icon name="search" />
      <input class="input" placeholder={t("library.filter")} bind:value={filter} aria-label={t("library.filter")} />
    </label>
    <select class="input view" bind:value={view} aria-label={t("worlds")}>
      <option value="all">{t("library.all")}</option>
      <option value="in_game">{t("library.in_game")}</option>
      <option value="starred">{t("starred")}</option>
    </select>
  </div>

  <div class="list scroll" role="listbox" aria-multiselectable="true" aria-label={t("worlds")} title={t("selection_hint")}>
    <div
      class="entry new"
      class:on={s?.selection === "new"}
      role="option"
      aria-selected={s?.selection === "new"}
      tabindex="0"
      data-entry="new"
      onclick={pickNew}
      onkeydown={(event) => (event.key === "Enter" || event.key === " " ? pickNew() : key(event))}
    >
      <span class="thumb plus"><Icon name="plus" /></span>
      <span class="title">{t("new_world")}</span>
    </div>
    {#each entries as entry (entry.id)}
      <div
        class="entry"
        class:on={ticked.has(entry.id) || s?.selection === entry.id}
        class:current={s?.selection === entry.id}
        class:version={(entry.depth ?? 0) > 0}
        role="option"
        aria-selected={ticked.has(entry.id) || s?.selection === entry.id}
        tabindex="0"
        data-entry={entry.id}
        onclick={(event) => pick(entry, event)}
        onkeydown={(event) => (event.key === "Enter" || event.key === " " ? pick(entry, event as unknown as MouseEvent) : key(event))}
      >
        <span class="thumb">
          {#if entry.kind === "world"}
            <Thumb id={entry.id} version={entry.picture ?? ""} />
          {:else}
            <span class="stray"><Icon name="warning" /></span>
          {/if}
        </span>
        <span class="text">
          <span class="title">
            <span class="name">{entry.title}</span>
            {#if entry.starred}<span class="star" title={t("starred")}><Icon name="star" size={12} fill /></span>{/if}
          </span>
          <span class="meta">
            {#if entry.placement === "in_game"}<span class="dot ok" title={t("list.in_game")}></span>{/if}
            {#if entry.kind === "stray"}
              {entry.folder}
            {:else}
              {entry.part || entry.type} · {day.format(new Date((entry.created ?? 0) * 1000))}{#if entry.tag} · {entry.tag}{/if}
            {/if}
          </span>
        </span>
      </div>
    {:else}
      <div class="empty faint">{s?.library.length ? t("library.no_match") : t("library.empty")}</div>
    {/each}
  </div>

  <div class="foot">
    {#if app.ticked.length > 1}
      <div class="line">
        <span class="num">{t("selection_count", { count: app.ticked.length, installed })}</span>
        <button class="btn small ghost" onclick={() => (app.ticked = [])}>{t("library.clear")}</button>
      </div>
      <div class="actions">
        <button class="btn small" disabled={!installed || s?.busy} title={t("remove_tip")} onclick={removeTicked}>{t("library_remove", { count: installed })}</button>
        <button class="btn small danger" disabled={!worlds.length || s?.busy} title={t("delete_tip")} onclick={deleteTicked}>{t("library_delete", { count: worlds.length })}</button>
      </div>
    {:else}
      <div class="line">
        <button class="btn small ghost" disabled={entries.length < 2} title={t("selection_hint")} onclick={() => (app.ticked = entries.map((e) => e.id))}>{t("select_all_worlds")}</button>
      </div>
    {/if}
    {#if s?.batch}<p class="batch selectable">{s.batch}</p>{/if}
  </div>
</aside>

<style>
  .sidebar {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    background: var(--panel);
  }
  .head {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 32px;
    padding: 0 4px 0 10px;
    flex: none;
  }
  .head h2 {
    font-size: 12px;
    color: var(--text-2);
  }
  .open {
    margin-left: auto;
  }
  .find {
    display: flex;
    gap: 4px;
    padding: 0 6px 6px;
    flex: none;
  }
  .search {
    position: relative;
    flex: 1;
    min-width: 0;
    color: var(--text-3);
  }
  .search :global(svg) {
    position: absolute;
    left: 6px;
    top: 5px;
  }
  .search .input {
    padding-left: 26px;
  }
  .view {
    flex: none;
    width: auto;
    max-width: 45%;
  }
  .list {
    flex: 1;
    min-height: 0;
    border-top: 1px solid var(--line);
    background: var(--field);
    outline: none;
  }
  .entry {
    position: relative;
    display: flex;
    align-items: center;
    gap: 8px;
    height: 42px;
    padding: 0 8px;
    outline-offset: -1px;
  }
  .entry:hover {
    background: var(--hover);
  }
  .entry.on {
    background: var(--accent-soft);
  }
  .entry.current {
    box-shadow: inset 2px 0 0 var(--accent);
  }
  .entry.version {
    padding-left: 22px;
  }
  .entry.version::before {
    content: "";
    position: absolute;
    left: 12px;
    top: 0;
    width: 6px;
    height: 21px;
    border-left: 1px solid var(--line-3);
    border-bottom: 1px solid var(--line-3);
  }
  .thumb {
    flex: none;
    width: 56px;
    height: 28px;
    overflow: hidden;
    border-radius: 2px;
    background: var(--panel);
    box-shadow: inset 0 0 0 1px var(--line);
  }
  .version .thumb {
    width: 44px;
    height: 22px;
  }
  .thumb.plus {
    display: grid;
    place-items: center;
    color: var(--text-2);
    border: 1px dashed var(--line-3);
    box-shadow: none;
    background: transparent;
  }
  .new .title {
    font-weight: 500;
  }
  .stray {
    display: grid;
    place-items: center;
    height: 100%;
    color: var(--warn);
  }
  .text {
    display: grid;
    min-width: 0;
    flex: 1;
    line-height: 1.3;
  }
  .title {
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
  }
  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .star {
    color: var(--warn);
    display: inline-flex;
  }
  .meta {
    display: flex;
    align-items: center;
    gap: 5px;
    min-width: 0;
    font-size: 11.5px;
    color: var(--text-3);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .meta .dot {
    width: 6px;
    height: 6px;
  }
  .empty {
    padding: 16px 10px;
    font-size: 12px;
  }
  .foot {
    flex: none;
    display: grid;
    gap: 4px;
    padding: 4px 6px;
    border-top: 1px solid var(--line);
  }
  .line {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
    min-height: 22px;
    font-size: 12px;
  }
  .actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
  }
  .actions .btn {
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .batch {
    font-size: 12px;
    color: var(--text-2);
    overflow-wrap: anywhere;
  }
</style>
