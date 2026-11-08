<script lang="ts">
  // A society's story as the game's Our History tells it, then the most significant recorded
  // events, oldest first, on a rail of dots.
  import { t } from "../../lib/app.svelte";
  import { eventStyle } from "../../lib/history";
  import type { HistoryEntry } from "../../lib/types";
  import Icon from "../Icon.svelte";
  import PlaceLink from "./PlaceLink.svelte";

  let {
    entries,
    story = [],
    title = "",
    names,
    onplace,
  }: {
    entries: HistoryEntry[];
    story?: string[];
    title?: string;
    names: string[];
    onplace: (cell: number) => void;
  } = $props();
</script>

{#if story.length}
  <h3 class="hx-h">{title}</h3>
  <div class="hx-story">
    {#each story as paragraph, index (index)}
      <p>{paragraph}</p>
    {/each}
  </div>
{/if}

<p class="hx-note">{t("history.chronicle_note")}</p>
{#if entries.length === 0}
  <p class="hx-note">{t("history.none")}</p>
{:else}
  <ol class="hx-timeline">
    {#each entries as entry, index (index)}
      {@const style = eventStyle(entry.kind)}
      <li class="hx-event" data-tone={style.tone}>
        <time class="hx-year num" datetime={String(entry.year)}>{entry.year}</time>
        <span class="hx-rail"><span class="hx-dot"><Icon name={style.glyph} size={12} /></span></span>
        <div class="hx-what">
          <span class="hx-kind">{entry.label}</span>
          <span class="hx-text">{entry.text}</span>
          {#if entry.place >= 0}
            <PlaceLink name={names[entry.place]} onclick={() => onplace(entry.place)} />
          {/if}
        </div>
      </li>
    {/each}
  </ol>
{/if}
