<script lang="ts">
  import { untrack } from "svelte";
  import { app, t } from "../lib/app.svelte";
  import type { Camera } from "../lib/camera";
  import Icon from "./Icon.svelte";
  import MapViewer from "./MapViewer.svelte";
  import Modal from "./ui/Modal.svelte";

  let { layer: initial }: { layer: string } = $props();

  let worlds = $state<{ id: string; name: string }[]>([]);
  let left = $state("");
  let right = $state("");
  let layer = $state(untrack(() => initial));
  let camera = $state<Camera | null>(null);
  let linked = $state(true);
  let leftCamera = $state<Camera | null>(null);
  let rightCamera = $state<Camera | null>(null);

  $effect(() => {
    void app.call<{ id: string; name: string }[]>("compare_list").then((found) => {
      worlds = found ?? [];
      const current = app.now?.world?.id ?? "";
      left = worlds.find((w) => w.id === current)?.id ?? worlds[0]?.id ?? "";
      right = worlds.find((w) => w.id !== left)?.id ?? "";
    });
  });

  $effect(() => {
    if (linked) {
      const a = leftCamera;
      if (a) untrackSet(a);
    }
  });
  $effect(() => {
    if (linked) {
      const b = rightCamera;
      if (b) untrackSet(b);
    }
  });
  function untrackSet(next: Camera): void {
    if (!camera || camera.x !== next.x || camera.y !== next.y || camera.scale !== next.scale) {
      camera = next;
      leftCamera = next;
      rightCamera = next;
    }
  }
</script>

<Modal title={t("compare_title")} wide onclose={() => (app.modal = null)}>
  <div class="bar">
    <div class="lenses">
      {#each app.info?.layers ?? [] as name (name)}
        <button class:on={layer === name} onclick={() => (layer = name)}>{t(`layer.${name}`)}</button>
      {/each}
    </div>
    <button class="btn small" class:on={linked} aria-pressed={linked} onclick={() => (linked = !linked)}>
      <Icon name="compare" size={14} />{t("compare.linked")}
    </button>
  </div>
  <div class="panes">
    {#each [0, 1] as side (side)}
      <div class="pane">
        <select class="input" value={side === 0 ? left : right}
          onchange={(event) => {
            const value = (event.currentTarget as HTMLSelectElement).value;
            if (side === 0) left = value; else right = value;
          }}>
          {#each worlds as world (world.id)}<option value={world.id}>{world.name}</option>{/each}
        </select>
        <div class="map">
          {#if side === 0 && left}
            <MapViewer world={left} {layer} compact bind:camera={leftCamera} />
          {:else if side === 1 && right}
            <MapViewer world={right} {layer} compact bind:camera={rightCamera} />
          {/if}
        </div>
      </div>
    {/each}
  </div>
</Modal>

<style>
  .bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 0 20px 12px;
  }
  .lenses {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .lenses button {
    height: 30px;
    padding: 0 12px;
    border-radius: 999px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-2);
    font: 550 12.5px var(--font);
    cursor: pointer;
  }
  .lenses button.on,
  .btn.on {
    background: var(--accent-soft);
    border-color: var(--accent-line);
    color: var(--accent);
  }
  .panes {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1px;
    background: var(--line);
    border-top: 1px solid var(--line);
  }
  .pane {
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: var(--panel);
  }
  .pane select {
    margin: 10px;
    width: auto;
  }
  .map {
    flex: 1;
    min-height: 0;
  }
</style>
