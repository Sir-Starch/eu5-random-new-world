<script lang="ts">
  // The small dialogs: a question to confirm, a path typed (in a browser), the shortcuts.
  import { app, t } from "../lib/app.svelte";
  import Modal from "./ui/Modal.svelte";

  const modal = $derived(app.modal);
  let typed = $state("");

  $effect(() => {
    if (modal?.kind === "path") typed = modal.value;
  });

  function answer(value: boolean): void {
    if (modal?.kind === "confirm") modal.resolve(value);
    app.modal = null;
  }

  function path(value: string | null): void {
    if (modal?.kind === "path") modal.resolve(value);
    app.modal = null;
  }

  const KEYS: [string, string][] = [
    ["Ctrl+N", "shortcut.new"],
    ["Ctrl+O", "shortcut.open"],
    ["Ctrl+Enter", "shortcut.generate"],
    ["Ctrl+,", "shortcut.settings"],
    ["Ctrl+V", "shortcut.paste"],
    ["Ctrl+B", "panes.library"],
    ["Ctrl+I", "panes.inspector"],
    ["↑ ↓", "shortcut.library"],
    ["1 … 0", "shortcut.lenses"],
    ["+ − F", "shortcut.zoom"],
    ["L · B", "shortcut.overlays"],
    ["Esc", "shortcut.clear"],
  ];
</script>

{#if modal?.kind === "confirm"}
  <Modal title={modal.title} width={500} onclose={() => answer(false)}>
    <p class="body">{modal.body}</p>
    {#snippet footer()}
      <button class="btn" onclick={() => answer(false)}>{t("cancel")}</button>
      <button class="btn {modal.kind === 'confirm' && modal.danger ? 'danger solid' : 'primary'}" onclick={() => answer(true)}>
        {modal.kind === "confirm" ? modal.confirm : ""}
      </button>
    {/snippet}
  </Modal>
{:else if modal?.kind === "path"}
  <Modal title={modal.title} width={560} onclose={() => path(null)}>
    <input class="input mono" bind:value={typed} onkeydown={(event) => event.key === "Enter" && path(typed || null)} />
    {#snippet footer()}
      <button class="btn" onclick={() => path(null)}>{t("cancel")}</button>
      <button class="btn primary" onclick={() => path(typed || null)}>OK</button>
    {/snippet}
  </Modal>
{:else if modal?.kind === "shortcuts"}
  <Modal title={t("shortcuts")} width={520} onclose={() => (app.modal = null)}>
    <dl>
      {#each KEYS as [keys, label] (label)}
        <dt><kbd>{keys}</kbd></dt><dd>{t(label)}</dd>
      {/each}
    </dl>
  </Modal>
{/if}

<style>
  .body {
    white-space: pre-line;
    line-height: 1.5;
  }
  dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 6px 14px;
    margin: 0;
    align-items: center;
  }
  dd {
    margin: 0;
    color: var(--text-2);
  }
</style>
