<script lang="ts">
  import type { Snippet } from "svelte";
  import { t } from "../../lib/app.svelte";
  import Icon from "../Icon.svelte";

  let {
    title,
    onclose,
    width = 520,
    children,
    footer,
    wide = false,
  }: {
    title: string;
    onclose: () => void;
    width?: number;
    children: Snippet;
    footer?: Snippet;
    wide?: boolean;
  } = $props();

  let dialog: HTMLDivElement;

  $effect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const first = dialog.querySelector<HTMLElement>(
      "input, select, textarea, button:not(.close)",
    );
    (first ?? dialog).focus();
    return () => previous?.focus?.();
  });

  function key(event: KeyboardEvent): void {
    if (event.key === "Escape") {
      event.stopPropagation();
      onclose();
    }
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="backdrop" onkeydown={key} onclick={(event) => event.target === event.currentTarget && onclose()}>
  <div
    class="dialog"
    class:wide
    style:width={wide ? undefined : `min(${width}px, calc(100vw - 32px))`}
    role="dialog"
    aria-modal="true"
    aria-label={title}
    tabindex="-1"
    bind:this={dialog}
  >
    <header>
      <h2>{title}</h2>
      <button class="btn icon small ghost close" aria-label={t("close")} title={t("close")} onclick={onclose}>
        <Icon name="x" />
      </button>
    </header>
    <div class="body scroll">{@render children()}</div>
    {#if footer}<footer>{@render footer()}</footer>{/if}
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: grid;
    place-items: center;
    background: rgba(0, 0, 0, 0.4);
  }
  .dialog {
    max-height: calc(100vh - 32px);
    display: flex;
    flex-direction: column;
    background: var(--bg);
    border: 1px solid var(--line-2);
    border-radius: 4px;
    box-shadow: var(--shadow);
    outline: none;
  }
  .dialog.wide {
    width: calc(100vw - 32px);
    height: calc(100vh - 32px);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    height: 34px;
    padding: 0 6px 0 14px;
    border-bottom: 1px solid var(--line);
    background: var(--panel);
    border-radius: 4px 4px 0 0;
  }
  h2 {
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .body {
    padding: 14px;
    min-height: 0;
    flex: 1;
  }
  .wide .body {
    padding: 0;
    display: flex;
    flex-direction: column;
  }
  footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border-top: 1px solid var(--line);
    background: var(--panel);
    border-radius: 0 0 4px 4px;
  }
</style>
