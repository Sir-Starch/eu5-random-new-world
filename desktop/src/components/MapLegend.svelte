<script lang="ts">
  // The inspector's maps tab: the lenses with their keys, one field that finds countries,
  // cultures, religions, resources, areas and places, and the legend of the lens. An entry or a
  // result lights its locations while the pointer rests on it, isolates them on a click and
  // brings them into view on a double-click.
  import { app, grouped, t } from "../lib/app.svelte";
  import type { Match } from "../lib/atlas";
  import { map } from "../lib/mapSession.svelte";
  import Icon from "./Icon.svelte";

  let query = $state("");
  let cursor = $state(0);

  const atlas = $derived(map.atlas);
  const lens = $derived(atlas?.lens(map.layer) ?? null);
  const ramp = $derived(app.info?.ramps.includes(map.layer) ?? false);
  const entries = $derived(
    (lens?.legend ?? []).map((entry, index) => ({ ...entry, index })).filter((entry) => entry.count > 0),
  );
  const most = $derived(Math.max(1, ...entries.map((entry) => entry.count)));
  const results = $derived<Match[]>(atlas && query.trim() ? atlas.find(query, 80) : []);

  function choose(result: Match): void {
    map.preview = null;
    map.match = { label: result.label, cells: new Set(result.cells), colour: result.colour };
    if (result.kind === "place" && result.cells.length === 1) map.pinned = result.cells[0];
    map.zoomTo(result.cells);
  }

  function key(event: KeyboardEvent): void {
    if (event.key === "ArrowDown") cursor = Math.min(results.length - 1, cursor + 1);
    else if (event.key === "ArrowUp") cursor = Math.max(0, cursor - 1);
    else if (event.key === "Enter" && results[cursor]) choose(results[cursor]);
    else if (event.key === "Escape" && query) query = "";
    else return;
    event.preventDefault();
    event.stopPropagation();
  }
</script>

<div class="maps">
  <div class="lenses" role="radiogroup" aria-label={t("shortcut.lenses")}>
    {#each app.info?.layers ?? [] as name, index (name)}
      <button
        class="lens"
        class:on={map.layer === name}
        role="radio"
        aria-checked={map.layer === name}
        title={t(`layer.${name}.tip`)}
        onclick={() => (map.layer = name)}
      >
        <span class="name">{t(`layer.${name}`)}</span>
        <span class="key">{index === 9 ? 0 : index + 1}</span>
      </button>
    {/each}
  </div>

  <div class="find">
    <label class="search">
      <Icon name="search" />
      <input
        class="input"
        placeholder={t("search_hint")}
        title={t("search_hint")}
        aria-label={t("search_hint")}
        bind:value={query}
        oninput={() => (cursor = 0)}
        onkeydown={key}
      />
      {#if query}
        <button class="btn icon small ghost clear" aria-label={t("map.clear")} title={t("map.clear")} onclick={() => (query = "")}><Icon name="x" /></button>
      {/if}
    </label>
  </div>

  {#if query.trim()}
    <div class="list scroll" role="listbox" aria-label={t("search_hint")}>
      {#each results as result, index (index)}
        <button
          class="row result"
          class:on={index === cursor}
          role="option"
          aria-selected={index === cursor}
          onmouseenter={() => {
            cursor = index;
            map.preview = new Set(result.cells);
          }}
          onmouseleave={() => (map.preview = null)}
          onclick={() => choose(result)}
        >
          <span class="label">{result.label}</span>
          <span class="kind">{t(`found.${result.kind}`)}</span>
          <span class="count num">{grouped(result.cells.length)}</span>
        </button>
      {:else}
        <p class="none">{t("map.no_results")}</p>
      {/each}
    </div>
  {:else}
    <div class="legend-head">
      <span class="title">{t("legend")}</span>
      <span class="faint">{t(`layer.${map.layer}`)}</span>
    </div>
    {#if ramp && lens}
      <div class="ramp">
        <div class="ramp-bar" style:background={`linear-gradient(90deg, ${lens.ramp.join(",")})`}></div>
        <div class="ramp-labels faint"><span>{t("legend.lowest")}</span><span>{t("legend.highest")}</span></div>
      </div>
    {/if}
    <div class="list scroll" role="list">
      {#each entries as entry (entry.index)}
        <button
          class="row entry"
          class:on={map.match?.label === entry.label}
          title={entry.label}
          onmouseenter={() => (map.preview = new Set(map.classCells(entry.index)))}
          onmouseleave={() => (map.preview = null)}
          onclick={() => {
            map.preview = null;
            map.isolate(entry.label, map.classCells(entry.index), entry.colour);
          }}
          ondblclick={() => map.zoomTo(map.classCells(entry.index))}
        >
          <span class="swatch" style:background={entry.colour}></span>
          <span class="label">{entry.label}</span>
          <span class="count num">{grouped(entry.count)}</span>
          <span class="bar" style:width={`${(entry.count * 100) / most}%`} style:background={entry.colour}></span>
        </button>
      {/each}
    </div>
  {/if}
  <p class="hint foot">{t("map.legend_hint")}</p>
</div>

<style>
  .maps {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .lenses {
    flex: none;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2px;
    padding: 8px 8px 6px;
  }
  .lens {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    height: 24px;
    padding: 0 6px 0 8px;
    border: 1px solid transparent;
    border-radius: var(--radius);
    background: transparent;
    color: var(--text-2);
    font: 400 12.5px var(--font);
    text-align: left;
  }
  .lens:hover {
    background: var(--hover);
    color: var(--text);
  }
  .lens.on {
    background: var(--accent-soft);
    border-color: var(--accent);
    color: var(--text);
  }
  .lens .name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .lens .key {
    flex: none;
    color: var(--text-3);
    font: 400 11px var(--mono);
  }
  .find {
    flex: none;
    padding: 2px 8px 8px;
    border-bottom: 1px solid var(--line);
  }
  .search {
    position: relative;
    display: block;
    color: var(--text-3);
  }
  .search > :global(svg) {
    position: absolute;
    left: 6px;
    top: 5px;
  }
  .search .input {
    padding-left: 26px;
    padding-right: 26px;
  }
  .clear {
    position: absolute;
    right: 2px;
    top: 2px;
  }
  .legend-head {
    flex: none;
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 8px 12px 4px;
    font-size: 12px;
  }
  .legend-head .title {
    font-weight: 600;
  }
  .ramp {
    flex: none;
    padding: 2px 12px 6px;
  }
  .ramp-bar {
    height: 8px;
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.2);
  }
  .ramp-labels {
    display: flex;
    justify-content: space-between;
    margin-top: 2px;
    font-size: 11px;
  }
  .list {
    flex: 1;
    min-height: 0;
    padding: 2px 4px 4px;
  }
  .row {
    position: relative;
    display: grid;
    align-items: center;
    gap: 6px;
    width: 100%;
    height: 22px;
    padding: 0 8px;
    border: 0;
    border-radius: 2px;
    background: transparent;
    color: var(--text);
    font: 400 12px var(--font);
    text-align: left;
    overflow: hidden;
  }
  .row:hover {
    background: var(--hover);
  }
  .row.on {
    background: var(--accent-soft);
  }
  .entry {
    grid-template-columns: 10px minmax(0, 1fr) auto;
  }
  .result {
    grid-template-columns: minmax(0, 1fr) auto 44px;
  }
  .label {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .kind {
    color: var(--text-3);
    font-size: 11px;
    white-space: nowrap;
  }
  .count {
    color: var(--text-3);
    font-size: 11px;
    text-align: right;
  }
  .swatch {
    width: 10px;
    height: 10px;
    border-radius: 1px;
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.3);
  }
  .bar {
    position: absolute;
    left: 8px;
    bottom: 1px;
    height: 1px;
    max-width: calc(100% - 16px);
    opacity: 0.6;
  }
  .none {
    padding: 6px 8px;
    color: var(--text-3);
    font-size: 12px;
  }
  .foot {
    flex: none;
    padding: 6px 12px 8px;
    border-top: 1px solid var(--line);
    font-size: 11.5px;
  }
</style>
