<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import Icon from "./Icon.svelte";

  const ICONS = { info: "info", success: "check", warning: "warning", error: "alert" };
</script>

<div class="toasts" aria-live="polite">
  {#each app.toasts as toast (toast.id)}
    <div class="toast {toast.kind}" role={toast.kind === "error" ? "alert" : "status"}>
      <Icon name={ICONS[toast.kind]} />
      <p class="selectable">{toast.text}</p>
      <button class="btn icon small ghost" aria-label={t("close")} title={t("close")} onclick={() => app.dismiss(toast.id)}><Icon name="x" /></button>
    </div>
  {/each}
</div>

<style>
  .toasts {
    position: fixed;
    right: var(--toast-right, 12px);
    bottom: 34px;
    z-index: 60;
    display: grid;
    gap: 6px;
    width: min(380px, calc(100vw - 24px));
  }
  .toast {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 7px 4px 7px 10px;
    border: 1px solid var(--line-2);
    border-left: 3px solid var(--text-3);
    border-radius: var(--radius);
    background: var(--panel);
    box-shadow: var(--shadow);
    font-size: 12.5px;
    line-height: 1.45;
  }
  .toast > :global(svg:first-child) {
    margin-top: 1px;
  }
  .toast p {
    flex: 1;
    overflow-wrap: anywhere;
  }
  .success {
    border-left-color: var(--ok);
  }
  .success > :global(svg:first-child) {
    color: var(--ok);
  }
  .warning {
    border-left-color: var(--warn);
  }
  .warning > :global(svg:first-child) {
    color: var(--warn);
  }
  .error {
    border-left-color: var(--danger);
  }
  .error > :global(svg:first-child) {
    color: var(--danger);
  }
  .info {
    border-left-color: var(--accent);
  }
  .info > :global(svg:first-child) {
    color: var(--accent-text);
  }
</style>
