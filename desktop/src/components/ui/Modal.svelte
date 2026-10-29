<script lang="ts">
  import type { Snippet } from "svelte";
  import { t } from "../../lib/app.svelte";
  import Icon from "../Icon.svelte";

  let {
    title,
    onclose,
    width = 560,
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
    class="dialog card"
    class:wide
    style:width={wide ? undefined : `min(${width}px, calc(100vw - 48px))`}
    role="dialog"
    aria-modal="true"
    aria-label={title}
    tabindex="-1"
    bind:this={dialog}
  >
    <header>
      <h2>{title}</h2>
      <button class="btn icon ghost close" aria-label={t("close")} onclick={onclose}>
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
    background: rgba(4, 6, 10, 0.55);
    backdrop-filter: blur(4px);
    animation: fade 140ms var(--ease);
  }
  .dialog {
    max-height: calc(100vh - 48px);
    display: flex;
    flex-direction: column;
    box-shadow: var(--shadow);
    animation: rise 180ms var(--ease);
    outline: none;
  }
  .dialog.wide {
    width: calc(100vw - 48px);
    height: calc(100vh - 48px);
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 18px 20px 12px 24px;
  }
  .body {
    padding: 4px 24px 22px;
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
    gap: 10px;
    padding: 14px 24px 18px;
    border-top: 1px solid var(--line);
  }
</style>
