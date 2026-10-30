<script lang="ts">
  // The middle of the window for a world: its map, or its mod picture while the map is covered or
  // missing.
  import { app, t } from "../lib/app.svelte";
  import { map } from "../lib/mapSession.svelte";
  import { picture } from "../lib/pictures";
  import MapViewer from "./MapViewer.svelte";

  const w = $derived(app.now?.world);
  const shows = $derived(!!w && w.atlas && w.revealed);
  let banner = $state("");

  $effect(() => {
    const world = w;
    if (!world || shows) return;
    const key = `${world.id}|${world.picture}`;
    banner = "";
    void picture(world.id, world.picture).then((url) => {
      if (app.now?.world && `${app.now.world.id}|${app.now.world.picture}` === key) banner = url;
    });
  });

  function compare(): void {
    if (w?.compare) app.modal = { kind: "compare", layer: map.layer };
    else app.toast("info", t("compare_need_two"));
  }
</script>

{#snippet title()}
  {#if w}
    <span class="pane-title">{w.name}</span>
    <span class="pane-sub">{w.type}{w.part ? ` · ${w.part}` : ""}</span>
  {/if}
{/snippet}

{#if w}
  {#if shows}
    <MapViewer world={w.id} session={map} head={title} lensPicker={!app.layout.inspector || app.focus} onCompare={compare} />
  {:else}
    <div class="view">
      <div class="pane-head">{@render title()}</div>
      <div class="cover">
        <div class="picture">
          {#if banner}<img src={banner} alt="" draggable="false" />{/if}
        </div>
        {#if w.atlas}
          <h2>{t("world.terra_incognita")}</h2>
          <p class="dim">{t("covered_maps")}</p>
          <button class="btn primary" title={t("reveal_world_tip")} onclick={() => app.call("reveal", { id: w.id })}>{t("reveal_world")}</button>
        {:else}
          <p class="dim">{t("no_atlas")}</p>
        {/if}
      </div>
    </div>
  {/if}
{/if}

<style>
  .view {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }
  .cover {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    padding: 24px;
    overflow: auto;
    background: var(--canvas);
    text-align: center;
  }
  .picture {
    width: min(100%, 520px);
    aspect-ratio: 2 / 1;
    margin-bottom: 6px;
    border-radius: 2px;
    overflow: hidden;
    background: var(--field);
    box-shadow:
      inset 0 0 0 1px var(--line),
      0 2px 12px rgba(0, 0, 0, 0.25);
  }
  .picture img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  p {
    max-width: 480px;
    font-size: 12.5px;
    line-height: 1.5;
  }
</style>
