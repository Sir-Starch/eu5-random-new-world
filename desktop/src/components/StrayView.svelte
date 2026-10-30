<script lang="ts">
  // The middle of the window for a mod in the game that the library cannot account for.
  import { app, t } from "../lib/app.svelte";
  import { openPath } from "../lib/native";
  import Icon from "./Icon.svelte";

  const stray = $derived(app.now?.stray);
</script>

{#if stray}
  <div class="view">
    <div class="pane-head">
      <Icon name="warning" />
      <span class="pane-title">{t("stray_name")}</span>
      <code class="pane-sub">{stray.folder}</code>
    </div>
    <div class="body">
      <p class="dim">{stray.about}</p>
      <code class="selectable faint">{stray.path}</code>
      <div class="actions">
        <button class="btn" disabled={!!stray.remove_problem} title={stray.remove_problem ?? ""}
          onclick={() => app.act("remove_entries", { ids: [app.now?.selection] })}>{t("remove")}</button>
        <button class="btn" onclick={() => openPath(stray.path)}>{t("open_folder")}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .view {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  .pane-head :global(svg) {
    flex: none;
    color: var(--warn);
  }
  .body {
    flex: 1;
    display: grid;
    align-content: start;
    justify-items: start;
    gap: 10px;
    padding: 16px;
    background: var(--canvas);
  }
  .body p {
    max-width: 640px;
    line-height: 1.5;
  }
  code {
    overflow-wrap: anywhere;
  }
  .actions {
    display: flex;
    gap: 6px;
  }
</style>
