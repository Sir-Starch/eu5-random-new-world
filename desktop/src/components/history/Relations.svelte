<script lang="ts">
  // Who a country is tied to: the partners it remembers, each with the reasons and what EU5
  // receives for them, then its other agreements.
  import { t } from "../../lib/app.svelte";
  import { mood, signed, standing } from "../../lib/history";
  import type { HistoryDossier, HistoryPartner } from "../../lib/types";
  import PlaceLink from "./PlaceLink.svelte";

  let {
    dossier,
    names,
    swatch,
    onplace,
  }: {
    dossier: HistoryDossier;
    names: string[];
    swatch: (tag: string) => string | undefined;
    onplace: (cell: number) => void;
  } = $props();

  const remembered = $derived(dossier.partners.filter((partner) => partner.reasons.length > 0));
  const agreements = $derived(dossier.partners.filter((partner) => partner.reasons.length === 0));
  const hasEffect = $derived(remembered.some((partner) => partner.reasons.some((reason) => reason.effect !== 0)));
</script>

{#snippet who(partner: HistoryPartner)}
  <button class="hx-who" title={partner.name} onclick={() => onplace(partner.place)}>
    <span class="hx-swatch" style:background={swatch(partner.tag) ?? "var(--line-3)"}></span>
    <span>{partner.name}</span>
  </button>
{/snippet}

{#snippet chips(partner: HistoryPartner)}
  {#if partner.standing.length}
    <span class="hx-chips">
      {#each partner.standing as kind (kind.kind)}
        <span class="hx-chip {standing(kind.kind)}" title={kind.kind === "trade" ? t("history.trade_note") : undefined}>{kind.label}</span>
      {/each}
    </span>
  {/if}
{/snippet}

<p class="hx-note">{t("history.relations_note")}</p>

{#if dossier.partners.length === 0}
  <p class="hx-note">{t("history.no_relations")}</p>
{/if}

{#if remembered.length}
  <h3 class="hx-h">{t("history.remembered")}{#if hasEffect}<small>{t("history.effect")}</small>{/if}</h3>
  <ul class="hx-list">
    {#each remembered as partner (partner.place)}
      <li class="hx-partner">
        <header>
          {@render who(partner)}
          {@render chips(partner)}
        </header>
        <ul class="hx-reasons">
          {#each partner.reasons as reason, index (index)}
            <li class="hx-reason">
              <span class="hx-chip {mood(reason.factor)}">{reason.label}</span>
              <span class="what">
                {reason.cause} · {reason.year}
                {#if reason.place >= 0}<PlaceLink name={names[reason.place]} onclick={() => onplace(reason.place)} />{/if}
              </span>
              {#if reason.effect}
                <span class="effect num {reason.effect < 0 ? 'bad' : 'good'}" title={t("history.effect")}>{signed(reason.effect)}</span>
              {/if}
            </li>
          {/each}
        </ul>
      </li>
    {/each}
  </ul>
{/if}

{#if agreements.length}
  <h3 class="hx-h">{t("history.agreements")}</h3>
  <ul class="hx-list">
    {#each agreements as partner (partner.place)}
      <li class="hx-agree">
        {@render who(partner)}
        {@render chips(partner)}
      </li>
    {/each}
  </ul>
  {#if dossier.more > 0}<p class="hx-more num">+{dossier.more}</p>{/if}
{/if}
