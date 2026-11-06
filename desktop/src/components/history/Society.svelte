<script lang="ts">
  // A country in 1337 as the game shows it: its government, rank and societal values, how it
  // began, and the event that last shaped each value.
  import { t } from "../../lib/app.svelte";
  import { leaning, spread } from "../../lib/history";
  import type { HistoryDossier } from "../../lib/types";
  import PlaceLink from "./PlaceLink.svelte";

  let {
    dossier,
    country,
    names,
    onplace,
  }: {
    dossier: HistoryDossier;
    country: { name: string; tag: string; color: string };
    names: string[];
    onplace: (cell: number) => void;
  } = $props();
</script>

<div class="hx-identity">
  <div class="name">
    <span class="hx-swatch" style:background={country.color}></span>
    <span>{country.name}</span>
    <span class="faint mono">{country.tag}</span>
  </div>
  <div class="hx-chips">
    <span class="hx-chip rank">{dossier.government}</span>
    {#if dossier.rank}<span class="hx-chip">{dossier.rank}</span>{/if}
  </div>
</div>

<p class="hx-note">{t("history.society_note")}</p>

<h3 class="hx-h">{t("history.origin")}</h3>
<div class="hx-origin">
  <span class="hx-year num">{dossier.origin.year}</span>
  <span>{dossier.origin.text}</span>
  {#if dossier.origin.place >= 0}
    <span class="place"><PlaceLink name={names[dossier.origin.place]} onclick={() => onplace(dossier.origin.place)} /></span>
  {/if}
</div>

{#if dossier.values.length}
  <h3 class="hx-h">{t("history.values")}</h3>
  <ul class="hx-values">
    {#each dossier.values as value (value.key)}
      {@const lean = leaning(value)}
      {@const bar = spread(value.position)}
      <li class="hx-value">
        <div class="head">
          <span class="title">{value.label}</span>
          <span class="lean"><span>{lean.name}</span> <b class="num">{lean.strength}</b></span>
        </div>
        <div
          class="hx-bipolar"
          role="meter"
          aria-label={value.label}
          aria-valuemin="-100"
          aria-valuemax="100"
          aria-valuenow={value.position}
          aria-valuetext={lean.name ? `${lean.name} ${lean.strength}` : "0"}
        >
          <i style:left="{bar.left}%" style:width="{bar.width}%"></i>
          <span class="mid"></span>
        </div>
        <div class="poles">
          <span class="pole">{value.left}</span>
          {#if value.kind === "foundation"}
            <span></span>
          {:else if value.place >= 0}
            <button class="hx-since" title={names[value.place]} onclick={() => onplace(value.place)}>{value.cause} · {value.year}</button>
          {:else}
            <span class="hx-since">{value.cause} · {value.year}</span>
          {/if}
          <span class="pole right">{value.right}</span>
        </div>
      </li>
    {/each}
  </ul>
{/if}

{#if dossier.values.length === 0}
  <h3 class="hx-h">{t("history.values")}</h3>
  <p class="hx-note">{t("history.no_values")}</p>
{/if}
