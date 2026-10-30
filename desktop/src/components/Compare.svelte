<script lang="ts">
  import { untrack } from "svelte";
  import { app, t } from "../lib/app.svelte";
  import type { Camera } from "../lib/camera";
  import { MapSession } from "../lib/mapSession.svelte";
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
  const sessions = [new MapSession(), new MapSession()];

  $effect(() => {
    for (const session of sessions) session.layer = layer;
  });

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
    <select class="input lens" bind:value={layer} aria-label={t("legend")}>
      {#each app.info?.layers ?? [] as name (name)}<option value={name}>{t(`layer.${name}`)}</option>{/each}
    </select>
    <label class="check"><input type="checkbox" bind:checked={linked} /><span>{t("compare.linked")}</span></label>
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
            <MapViewer world={left} session={sessions[0]} compact bind:camera={leftCamera} />
          {:else if side === 1 && right}
            <MapViewer world={right} session={sessions[1]} compact bind:camera={rightCamera} />
          {/if}
        </div>
      </div>
    {/each}
  </div>
</Modal>

<style>
  .bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 10px;
    border-bottom: 1px solid var(--line);
  }
  .lens {
    width: auto;
    min-width: 160px;
  }
  .panes {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1px;
    background: var(--line);
  }
  .pane {
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: var(--bg);
  }
  .pane select {
    margin: 6px;
    width: auto;
  }
  .map {
    flex: 1;
    min-height: 0;
  }
</style>
