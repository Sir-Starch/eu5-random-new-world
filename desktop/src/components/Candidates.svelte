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

<Modal title={t("candidates")} width={980} onclose={() => (app.modal = null)}>
  <p class="dim hint">{t("candidates_hint")}</p>
  <div class="grid" role="listbox" aria-label={t("candidates")}>
    {#each app.now?.candidates ?? [] as candidate, index (candidate.seed)}
      <button class="candidate" class:on={chosen === index} role="option" aria-selected={chosen === index}
        onclick={() => (chosen = index)} ondblclick={() => choose(index)}>
        <span class="picture">
          {#if pictures[index]}<img src={pictures[index]} alt="" />{:else}<span class="loading"></span>{/if}
        </span>
        <span class="caption">
          <strong>{index + 1}</strong>
          <span class="land">{candidate.land.toFixed(1)} %</span>
          <span class="mono faint seed">{candidate.seed}</span>
        </span>
      </button>
    {/each}
  </div>
  {#snippet footer()}
    <button class="btn ghost" onclick={() => (app.modal = null)}>{t("cancel")}</button>
    <button class="btn primary" onclick={() => choose()}>{t("candidates.use")}</button>
  {/snippet}
</Modal>

<style>
  .hint {
    margin-bottom: 16px;
    font-size: 13px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
  }
  .candidate {
    display: grid;
    gap: 8px;
    padding: 8px;
    border-radius: 14px;
    border: 1px solid var(--line);
    background: var(--bg-2);
    color: var(--text);
    cursor: pointer;
    font: inherit;
    transition: all var(--speed) var(--ease);
  }
  .candidate:hover {
    border-color: var(--line-3);
  }
  .candidate.on {
    border-color: var(--accent-line);
    box-shadow: var(--glow);
  }
  .picture {
    display: block;
    aspect-ratio: 2 / 1;
    border-radius: 9px;
    overflow: hidden;
    background: var(--panel-3);
  }
  .picture img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    image-rendering: pixelated;
  }
  .loading {
    display: block;
    height: 100%;
    background: linear-gradient(90deg, var(--panel-3), var(--panel-2), var(--panel-3));
    background-size: 200% 100%;
    animation: shimmer 1.4s linear infinite;
  }
  .caption {
    display: flex;
    align-items: baseline;
    gap: 10px;
    padding: 0 4px 2px;
    font-size: 13px;
  }
  .land {
    color: var(--ok);
    font-weight: 600;
  }
  .seed {
    margin-left: auto;
    font-size: 11px;
  }
</style>
