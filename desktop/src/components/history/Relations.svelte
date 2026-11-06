<script lang="ts">
  // A country's opinion of others on the first day, as the game lists it: for each country the
  // sum and the lines, each under its name in the game, with its value and what fades a year.
  import { t } from "../../lib/app.svelte";
  import { signed } from "../../lib/history";
  import type { HistoryDossier } from "../../lib/types";

  let {
    dossier,
    swatch,
    onplace,
  }: {
    dossier: HistoryDossier;
    swatch: (tag: string) => string | undefined;
    onplace: (cell: number) => void;
  } = $props();

  const tone = (value: number): string => (value < 0 ? "bad" : value > 0 ? "good" : "");
</script>

<p class="hx-note">{t("history.relations_note")}</p>

{#if dossier.partners.length === 0}
  <p class="hx-note">{t("history.no_relations")}</p>
{:else}
  <ul class="hx-list">
    {#each dossier.partners as partner (partner.tag || partner.place)}
      <li class="hx-partner">
        <header>
          <button class="hx-who" title={partner.name} onclick={() => onplace(partner.place)}>
            <span class="hx-swatch" style:background={swatch(partner.tag) ?? "var(--line-3)"}></span>
            <span>{partner.name}</span>
          </button>
          <span class="effect num {tone(partner.total)}" title={t("history.total")}>{signed(partner.total)}</span>
        </header>
        <ul class="hx-reasons">
          {#each partner.opinions as line, index (index)}
            <li class="hx-reason">
              {#if line.place >= 0}
                <button class="what hx-line" onclick={() => onplace(line.place)}>{line.label}</button>
              {:else}
                <span class="what">{line.label}</span>
              {/if}
              {#if line.decay}<span class="hx-since num">{t("history.yearly", { value: signed(-line.decay) })}</span>{/if}
              <span class="effect num {tone(line.value)}">{signed(line.value)}</span>
            </li>
          {/each}
        </ul>
      </li>
    {/each}
  </ul>
  {#if dossier.more > 0}<p class="hx-more num">+{dossier.more}</p>{/if}
{/if}
