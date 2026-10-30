<script lang="ts" module>
  // Which sections are closed, kept per machine.
  const STORE = "rnw.sections";

  function stored(): Record<string, boolean> {
    try {
      return JSON.parse(localStorage.getItem(STORE) ?? "{}") as Record<string, boolean>;
    } catch {
      return {};
    }
  }

  const open = $state<Record<string, boolean>>(stored());
</script>

<script lang="ts">
  // A titled part of the inspector that folds away under its header.
  import type { Snippet } from "svelte";
  import Icon from "../Icon.svelte";

  let {
    id,
    title,
    closed = false,
    aside,
    children,
  }: {
    id: string;
    title: string;
    /** Closed until the player opens it. */
    closed?: boolean;
    aside?: Snippet;
    children: Snippet;
  } = $props();

  const shown = $derived(open[id] ?? !closed);

  function flip(): void {
    open[id] = !shown;
    try {
      localStorage.setItem(STORE, JSON.stringify(open));
    } catch {
      // Storage is a convenience.
    }
  }
</script>

<section class="section">
  <div class="head">
    <button class="title" aria-expanded={shown} onclick={flip}>
      <Icon name={shown ? "chevronDown" : "chevronRight"} />
      <span>{title}</span>
    </button>
    {#if aside}<div class="aside">{@render aside()}</div>{/if}
  </div>
  {#if shown}<div class="body">{@render children()}</div>{/if}
</section>

<style>
  .section {
    border-bottom: 1px solid var(--line);
  }
  .head {
    display: flex;
    align-items: center;
    gap: 6px;
    min-height: 30px;
    padding-right: 8px;
  }
  .title {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 4px;
    height: 30px;
    padding: 0 6px;
    border: 0;
    background: transparent;
    color: var(--text);
    font: 600 12px var(--font);
    text-align: left;
  }
  .title span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .title :global(svg) {
    color: var(--text-3);
  }
  .title:hover :global(svg) {
    color: var(--text);
  }
  .aside {
    flex: none;
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--text-3);
  }
  .body {
    display: grid;
    gap: 8px;
    padding: 0 12px 12px 12px;
  }
</style>
