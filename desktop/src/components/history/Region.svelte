<script lang="ts">
  // What happened across the region of the pinned location: the aims it was seeded with, the
  // inheritances its societies share, and the years its land changed historical owners.
  import { t } from "../../lib/app.svelte";
  import type { HistoryRegion } from "../../lib/types";
  import Icon from "../Icon.svelte";
  import PlaceLink from "./PlaceLink.svelte";

  let {
    region,
    names,
    onplace,
  }: {
    region: HistoryRegion;
    names: string[];
    onplace: (cell: number) => void;
  } = $props();

  const busiest = $derived(Math.max(1, ...region.changes.map((change) => change.count)));
</script>

{#if region.ambitions.length}
  <h3 class="hx-h">{t("history.ambitions")}</h3>
  <ul class="hx-list">
    {#each region.ambitions as aim, index (index)}
      <li class="hx-aim" class:done={aim.realized}>
        <span class="state"><Icon name={aim.realized ? "check" : "circle"} size={14} /></span>
        <span>{aim.label} — <PlaceLink name={aim.name} onclick={() => onplace(aim.place)} /></span>
        <span class="status">{t(aim.realized ? "history.fulfilled" : "history.unfulfilled")}</span>
      </li>
    {/each}
  </ul>
{/if}

{#if region.heritage.length}
  <h3 class="hx-h">{t("history.inheritance")}</h3>
  <ul class="hx-list">
    {#each region.heritage as heritage, index (index)}
      <li class="hx-heritage">
        {#each heritage.labels as label (label)}<span class="label">{label}</span>{/each}
        <span class="members">
          {#each heritage.members as member (member.place)}
            <PlaceLink name={member.name} onclick={() => onplace(member.place)} />
          {/each}
        </span>
      </li>
    {/each}
  </ul>
{/if}

{#if region.changes.length}
  <h3 class="hx-h">{t("history.owner_changes")}</h3>
  <ul class="hx-list">
    {#each region.changes as change, index (index)}
      <li>
        <button class="hx-change" title={names[change.place]} onclick={() => onplace(change.place)}>
          <span class="num">{change.year}</span>
          <span class="hx-meter"><i style:width="{(change.count / busiest) * 100}%"></i></span>
          <span class="num">{change.count}</span>
        </button>
      </li>
    {/each}
  </ul>
{/if}
