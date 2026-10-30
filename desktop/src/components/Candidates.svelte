<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import Modal from "./ui/Modal.svelte";

  let pictures = $state<string[]>([]);
  let chosen = $state(0);

  $effect(() => {
    void app.call<string[]>("candidate_pictures").then((found) => (pictures = found ?? []));
  });

  async function choose(index = chosen): Promise<void> {
    await app.call("choose_candidate", { index });
    app.modal = null;
  }
</script>

<Modal title={t("candidates")} width={900} onclose={() => (app.modal = null)}>
  <p class="hint intro">{t("candidates_hint")}</p>
  <div class="grid" role="listbox" aria-label={t("candidates")}>
    {#each app.now?.candidates ?? [] as candidate, index (candidate.seed)}
      <button class="candidate" class:on={chosen === index} role="option" aria-selected={chosen === index}
        onclick={() => (chosen = index)} ondblclick={() => choose(index)}>
        <span class="picture">
          {#if pictures[index]}<img src={pictures[index]} alt="" />{/if}
        </span>
        <span class="caption">
          <span class="num">{index + 1}</span>
          <span class="num">{candidate.land.toFixed(1)} %</span>
          <span class="mono faint seed">{candidate.seed}</span>
        </span>
      </button>
    {/each}
  </div>
  {#snippet footer()}
    <button class="btn" onclick={() => (app.modal = null)}>{t("cancel")}</button>
    <button class="btn primary" onclick={() => choose()}>{t("candidates.use")}</button>
  {/snippet}
</Modal>

<style>
  .intro {
    margin-bottom: 10px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 8px;
  }
  .candidate {
    display: grid;
    gap: 4px;
    padding: 4px;
    border-radius: var(--radius);
    border: 1px solid var(--line-2);
    background: var(--panel);
    color: var(--text);
    font: inherit;
  }
  .candidate:hover {
    border-color: var(--line-3);
  }
  .candidate.on {
    border-color: var(--accent);
    background: var(--accent-soft);
    box-shadow: inset 0 0 0 1px var(--accent);
  }
  .picture {
    display: block;
    aspect-ratio: 2 / 1;
    overflow: hidden;
    background: var(--field);
  }
  .picture img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    image-rendering: pixelated;
  }
  .caption {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 0 2px;
    font-size: 12px;
  }
  .seed {
    margin-left: auto;
    font-size: 11px;
  }
</style>
