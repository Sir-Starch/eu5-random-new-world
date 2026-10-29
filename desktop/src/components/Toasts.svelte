<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import Icon from "./Icon.svelte";

  const ICONS = { info: "info", success: "check", warning: "warning", error: "alert" };
</script>

<div class="toasts" aria-live="polite">
  {#each app.toasts as toast (toast.id)}
    <div class="toast {toast.kind}" role={toast.kind === "error" ? "alert" : "status"}>
      <Icon name={ICONS[toast.kind]} size={17} />
      <p class="selectable">{toast.text}</p>
      <button class="btn icon small ghost" aria-label={t("close")} onclick={() => app.dismiss(toast.id)}><Icon name="x" size={14} /></button>
    </div>
  {/each}
</div>

<style>
  .toasts {
    position: fixed;
    right: 20px;
    bottom: 20px;
    z-index: 60;
    display: grid;
    gap: 10px;
    width: min(420px, calc(100vw - 40px));
  }
  .toast {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 8px 12px 14px;
    border-radius: 12px;
    background: color-mix(in srgb, var(--panel-2) 96%, transparent);
    backdrop-filter: blur(14px);
    border: 1px solid var(--line-2);
    box-shadow: var(--shadow);
    font-size: 13px;
    line-height: 1.5;
    animation: rise 180ms var(--ease);
  }
  .toast :global(svg:first-child) {
    flex: none;
    margin-top: 2px;
  }
  .toast p {
    flex: 1;
    overflow-wrap: anywhere;
  }
  .success :global(svg:first-child) {
    color: var(--ok);
  }
  .warning {
    border-color: color-mix(in srgb, var(--warn) 40%, transparent);
  }
  .warning :global(svg:first-child) {
    color: var(--warn);
  }
  .error {
    border-color: color-mix(in srgb, var(--danger) 45%, transparent);
  }
  .error :global(svg:first-child) {
    color: var(--danger);
  }
  .info :global(svg:first-child) {
    color: var(--sea);
  }
</style>
