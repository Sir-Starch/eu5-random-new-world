<script lang="ts">
  // The middle of the window for the new world: its land (continent sketches to choose from, an
  // image of the land, or nothing yet), the progress of a world being made and how it ended.
  import { app, clock, t } from "../lib/app.svelte";
  import { copyText } from "../lib/native";
  import Icon from "./Icon.svelte";
  import QueueList from "./QueueList.svelte";

  const s = $derived(app.now);
  const n = $derived(s?.new);
  const busy = $derived(!!s?.busy);
  const running = $derived(busy && (s?.task === "generate" || s?.task === "queue"));
  const sketching = $derived(busy && s?.task === "candidates");
  const percent = $derived(Math.round((s?.fraction ?? 0) * 100));
  const ours = $derived(s?.task === "generate" || s?.task === "queue");
  // While a world is made the next one can be prepared: the controls stay free for it.
  const locked = $derived(busy && !n?.preparable);
  const sketched = $derived(!!s?.candidates.length && !sketching && !n?.land_mask);
  const outcome = $derived(
    !busy && ours && (s?.phase === "finished" || s?.phase === "failed" || s?.phase === "cancelled") ? s.phase : null,
  );
  let dismissed = $state(-1);
  let pictures = $state<string[]>([]);
  let sketches = "";

  $effect(() => {
    const key = (s?.candidates ?? []).map((c) => c.seed).join(",");
    if (key === sketches) return;
    sketches = key;
    pictures = [];
    if (key) void app.call<string[]>("candidate_pictures").then((found) => sketches === key && (pictures = found ?? []));
  });
</script>

<div class="view">
  <div class="pane-head">
    <span class="pane-title">{t("new_world")}</span>
    <span class="pane-sub">{t(`type.${n?.choice}`)}</span>
    <span class="spacer"></span>
    <div class="land-tools">
      <button class="btn small" disabled={locked || !n?.template_enabled} title={t("editor.open_tip")} onclick={() => (app.editor = true)}>{t("editor.open")}</button>
    </div>
  </div>

  <div class="stage scroll">
    {#if running}
      <div class="run" aria-live="polite">
        <div class="run-top">
          <span class="spinner"></span>
          <h2>{s?.phase === "cancelling" ? t("cancelling") : t("dock.forging")}</h2>
          <span class="num percent">{percent} %</span>
        </div>
        <div class="progress"><span style:width={`${percent}%`}></span></div>
        <div class="run-meta">
          {#if s?.eta}<span class="num">{t("eta", { time: clock(s.eta) })}</span>{/if}
          {#if s?.task === "queue" && n?.queue.length}<span>{t("queue_count", { count: n.queue.length - n.queue_failed })}</span>{/if}
        </div>
        <ol class="stages">
          {#each s?.stages ?? [] as stage, index (index)}
            <li class={stage.state}>
              {#if stage.state === "done"}<Icon name="check" />{:else if stage.state === "running"}<span class="spinner"></span>{:else}<span class="blank"></span>{/if}
              <span>{stage.label}</span>
            </li>
          {/each}
        </ol>
        <div><button class="btn" disabled={s?.phase !== "running"} onclick={() => app.call("cancel")}>{t("cancel")}</button></div>
      </div>
    {:else if outcome && dismissed !== s?.runs}
      <div class="outcome msg {outcome === 'finished' ? 'ok' : outcome === 'failed' ? 'error' : 'info'}">
        <Icon name={outcome === "finished" ? "check" : outcome === "failed" ? "alert" : "info"} />
        <div class="said">
          <p class:failure={outcome === "failed"} class:selectable={outcome === "failed"}>{s?.status}</p>
          {#if outcome === "finished" && s?.result}
            <div class="buttons">
              <button class="btn small primary" onclick={() => app.call("select", { id: s.result?.world })}>{t("dock.open_world")}</button>
            </div>
          {:else if outcome === "failed"}
            <div class="buttons">
              {#if n?.retry}
                <button class="btn small" disabled={!n.retry_enabled} onclick={() => app.act("retry_new_seed")}>{t("retry_new_seed")}</button>
              {/if}
              <button class="btn small" onclick={() => copyText(s?.status ?? "")}>{t("copy")}</button>
            </div>
          {/if}
        </div>
        <button class="btn icon small ghost" aria-label={t("close")} title={t("close")} onclick={() => (dismissed = s?.runs ?? -1)}><Icon name="x" /></button>
      </div>
    {/if}

    <!-- Under the progress while a world is made; at rest below the sketches, which must not
         move down with every world added. -->
    {#if running}<QueueList />{/if}

    {#if sketched}
      <div class="sketches">
        <p class="hint">{t("candidates_hint")}</p>
        <div class="grid" role="listbox" aria-label={t("candidates")}>
          {#each s?.candidates ?? [] as candidate, index (candidate.seed)}
            {@const chosen = candidate.seed === n?.seed}
            <div class="card" class:on={chosen}>
              <button
                class="sketch"
                role="option"
                aria-selected={chosen}
                disabled={busy}
                title={t("candidates.use")}
                onclick={() => app.call("choose_candidate", { index })}
              >
                <span class="picture">{#if pictures[index]}<img src={pictures[index]} alt="" />{/if}</span>
                <span class="caption">
                  <span class="num">{index + 1}</span>
                  <span class="num faint">{candidate.land.toFixed(1)} %</span>
                  {#if chosen}<span class="chosen"><Icon name="check" />{t("candidates.chosen")}</span>{/if}
                  <code class="faint seed">{candidate.seed}</code>
                </span>
              </button>
              <button
                class="btn small add"
                class:queued={candidate.queued}
                disabled={candidate.queued || !n?.preparable}
                title={t("queue_hint")}
                onclick={() => app.enqueue(index)}
              >
                <Icon name={candidate.queued ? "check" : "plus"} />
                <span>{candidate.queued ? t("candidates.queued") : t("enqueue")}</span>
              </button>
            </div>
          {/each}
        </div>
      </div>
    {:else if !running}
      <!-- The New World before it has land: a blank sheet ruled like a map. -->
      <div class="land">
        <div class="sheet">
          {#if sketching}
            <span class="spinner"></span>
            <p class="dim">{s?.running || t("stage.candidates")}</p>
          {:else if n?.land_mask}
            <Icon name="image" />
            <p>{n.land_mask_text}</p>
            <code class="faint selectable">{n.land_mask}</code>
            <div class="row">
              <button class="btn small" disabled={locked || !n.template_enabled} onclick={() => (app.editor = true)}>{t("editor.edit")}</button>
              <button class="btn small" disabled={locked} onclick={() => app.call("clear_land_image")}>{t("land_image_clear")}</button>
            </div>
          {:else}
            <h2>{t("editor.title")}</h2>
            <p class="dim">{t("editor.open_tip")}</p>
            <button class="btn primary" disabled={locked || !n?.template_enabled} title={t("editor.open_tip")} onclick={() => (app.editor = true)}>{t("editor.open")}</button>
          {/if}
        </div>
      </div>
    {/if}

    {#if !running}<QueueList />{/if}
  </div>
</div>

<style>
  .view {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }
  .pane-head {
    overflow: hidden;
    container-type: inline-size;
  }
  .land-tools {
    flex: 0 1 auto;
    display: flex;
    gap: 4px;
    min-width: 0;
  }
  .land-tools .btn {
    display: block;
    flex: 0 1 auto;
    min-width: 0;
    line-height: 20px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .stage {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    background: var(--canvas);
  }
  .land {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }
  .sheet {
    --rule: rgba(255, 255, 255, 0.045);
    width: min(100%, 720px);
    aspect-ratio: 2 / 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 24px 12%;
    border: 1px solid var(--line-2);
    background:
      repeating-linear-gradient(90deg, var(--rule) 0 1px, transparent 1px 12.5%),
      repeating-linear-gradient(180deg, var(--rule) 0 1px, transparent 1px 25%),
      var(--map-bg);
    background-position: -1px -1px;
    color: var(--text-2);
    text-align: center;
  }
  :global(:root[data-theme="light"]) .sheet {
    --rule: rgba(0, 0, 0, 0.06);
  }
  @media (prefers-color-scheme: light) {
    :global(:root:not([data-theme="dark"])) .sheet {
      --rule: rgba(0, 0, 0, 0.06);
    }
  }
  .sheet p {
    max-width: 460px;
    font-size: 12.5px;
    line-height: 1.5;
  }
  .sheet h2 {
    color: var(--text);
  }
  .row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    justify-content: center;
  }
  .sheet code {
    max-width: 100%;
    overflow-wrap: anywhere;
  }
  .outcome {
    flex: none;
    align-items: flex-start;
    margin: 12px 12px 0;
  }
  .said {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 6px;
    padding-top: 1px;
  }
  .failure {
    max-height: 120px;
    overflow: auto;
    white-space: pre-line;
    overflow-wrap: anywhere;
  }
  .buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .run {
    display: grid;
    gap: 10px;
    width: min(100%, 620px);
    margin: 0 auto;
    padding: 32px 24px;
  }
  .stage > .run:only-child {
    margin: auto;
  }
  .run-top {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .run-top h2 {
    flex: 1;
  }
  .percent {
    font-size: 15px;
    font-weight: 600;
  }
  .run-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 14px;
    color: var(--text-2);
    font-size: 12px;
  }
  .stages {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 3px 16px;
    margin: 4px 0;
    padding: 10px 12px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel);
    list-style: none;
    font-size: 12px;
  }
  .stages li {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    color: var(--text-3);
  }
  .stages li span:last-child {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .stages li.done {
    color: var(--text-2);
  }
  .stages li.done :global(svg) {
    color: var(--ok);
  }
  .stages li.running {
    color: var(--text);
    font-weight: 500;
  }
  .stages .spinner {
    margin: 0 2px;
  }
  .blank {
    flex: none;
    width: 16px;
  }
  .sketches {
    display: grid;
    gap: 10px;
    padding: 12px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 8px;
  }
  .card {
    display: grid;
    gap: 4px;
    align-content: start;
    padding: 4px;
    border: 1px solid var(--line-2);
    border-radius: var(--radius);
    background: var(--panel);
  }
  .card:hover:not(:has(.sketch:disabled)) {
    border-color: var(--line-3);
  }
  .card.on {
    border-color: var(--accent);
    box-shadow: inset 0 0 0 1px var(--accent);
  }
  .sketch {
    display: grid;
    gap: 4px;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--text);
    font: inherit;
    text-align: left;
  }
  .add {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    min-width: 0;
  }
  .add span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .add.queued {
    color: var(--accent-text);
  }
  .picture {
    display: block;
    aspect-ratio: 2 / 1;
    overflow: hidden;
    background: var(--map-bg);
  }
  .picture img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: contain;
    image-rendering: pixelated;
  }
  .caption {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    height: 20px;
    padding: 0 2px;
    font-size: 12px;
  }
  .caption > span {
    flex: none;
    white-space: nowrap;
  }
  .chosen {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    color: var(--accent-text);
  }
  .seed {
    margin-left: auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 11px;
  }
  @container (max-width: 560px) {
    .pane-title,
    .pane-sub {
      display: none;
    }
  }
</style>
