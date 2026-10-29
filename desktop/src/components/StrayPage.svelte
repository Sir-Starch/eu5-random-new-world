<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import { openPath } from "../lib/native";
  import Icon from "./Icon.svelte";

  const stray = $derived(app.now?.stray);
</script>

{#if stray}
  <div class="page">
    <div class="card body">
      <span class="icon"><Icon name="alert" size={28} /></span>
      <h1>{t("stray_name")}</h1>
      <code class="selectable">{stray.folder}</code>
      <p class="dim">{stray.about}</p>
      <div class="actions">
        <button class="btn" disabled={!!stray.remove_problem} title={stray.remove_problem ?? ""}
          onclick={() => app.act("remove_entries", { ids: [app.now?.selection] })}>
          <Icon name="eyeOff" size={16} />{t("remove")}
        </button>
        <button class="btn ghost" onclick={() => openPath(stray.path)}><Icon name="folder" size={16} />{t("open_folder")}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .page {
    height: 100%;
    display: grid;
    place-items: center;
    padding: 32px;
  }
  .body {
    max-width: 560px;
    padding: 32px;
    display: grid;
    gap: 14px;
    justify-items: start;
  }
  .icon {
    display: grid;
    place-items: center;
    width: 52px;
    height: 52px;
    border-radius: 14px;
    background: var(--warn-soft);
    color: var(--warn);
  }
  code {
    color: var(--text-2);
    font-size: 12.5px;
  }
  .actions {
    display: flex;
    gap: 8px;
  }
</style>
