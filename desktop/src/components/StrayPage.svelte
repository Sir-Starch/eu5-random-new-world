<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import { openPath } from "../lib/native";
  import Icon from "./Icon.svelte";

  const stray = $derived(app.now?.stray);
</script>

{#if stray}
  <div class="page">
    <h1><Icon name="warning" />{t("stray_name")}</h1>
    <code class="selectable">{stray.folder}</code>
    <p class="dim">{stray.about}</p>
    <div class="actions">
      <button class="btn" disabled={!!stray.remove_problem} title={stray.remove_problem ?? ""}
        onclick={() => app.act("remove_entries", { ids: [app.now?.selection] })}>{t("remove")}</button>
      <button class="btn" onclick={() => openPath(stray.path)}>{t("open_folder")}</button>
    </div>
  </div>
{/if}

<style>
  .page {
    display: grid;
    gap: 10px;
    justify-items: start;
    max-width: 640px;
    padding: 16px;
  }
  h1 {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  h1 :global(svg) {
    color: var(--warn);
  }
  code {
    color: var(--text-2);
  }
  .actions {
    display: flex;
    gap: 6px;
  }
</style>
