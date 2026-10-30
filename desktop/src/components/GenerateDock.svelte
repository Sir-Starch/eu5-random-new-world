<script lang="ts">
  // The bar under the new-world settings: the location budget, Generate and its progress, the
  // outcome of the last run and the queue.
  import { app, clock, grouped, t } from "../lib/app.svelte";
  import { copyText } from "../lib/native";
  import Icon from "./Icon.svelte";

  const s = $derived(app.now);
  const n = $derived(s?.new);
  const budget = $derived(app.info?.budget ?? 31200);
  const share = $derived(Math.min(1, (n?.estimate ?? 0) / 32000));
  const level = $derived(
    !n?.estimate ? "" : n.over_budget ? "over" : n.estimate > budget * 0.94 ? "near" : "ok",
  );
  const running = $derived(!!s?.busy && !!s?.generating && s.task !== "candidates");
  const percent = $derived(Math.round((s?.fraction ?? 0) * 100));
  const ours = $derived(s?.task === "generate" || s?.task === "queue");
  let details = $state(false);
</script>

<div class="dock">
  {#if running && details}
    <ol class="stages scroll">
      {#each s?.stages ?? [] as stage, index (index)}
        <li class={stage.state}>
          {#if stage.state === "done"}<Icon name="check" />{:else if stage.state === "running"}<span class="spinner"></span>{:else}<span class="blank"></span>{/if}
          {stage.label}
        </li>
      {/each}
    </ol>
  {/if}

  {#if !running && ours && s?.phase === "finished" && s.result}
    <div class="msg ok outcome">
      <Icon name="check" />
      <p>{s.status}</p>
      <button class="btn small" onclick={() => app.call("select", { id: s.result?.world })}>{t("dock.open_world")}</button>
    </div>
  {:else if !running && ours && s?.phase === "failed"}
    <div class="msg error outcome">
      <Icon name="alert" />
      <p class="selectable failure">{s.status}</p>
      <div class="buttons">
        {#if n?.retry}
          <button class="btn small" disabled={!n.retry_enabled} onclick={() => app.act("retry_new_seed")}>{t("retry_new_seed")}</button>
        {/if}
        <button class="btn small" onclick={() => copyText(s.status)}>{t("copy")}</button>
      </div>
    </div>
  {:else if !running && ours && s?.phase === "cancelled"}
    <div class="msg info outcome"><Icon name="info" /><p>{s.status}</p></div>
  {/if}

  {#if n?.queue.length}
    <div class="queue">
      <span class="queue-title">{t("queue_title")}</span>
      <ol class="jobs">
        {#each n.queue as job, index (index)}
          <li title={job.seed}>{index + 1}. {job.type} <span class="mono faint">{job.seed}</span></li>
        {/each}
      </ol>
      <button class="btn small" disabled={s?.busy} onclick={() => app.act("start_queue")}>{t("run_queue")}</button>
      <button class="btn small ghost" disabled={s?.busy} onclick={() => app.call("clear_queue")}>{t("clear_queue")}</button>
    </div>
  {/if}

  <div class="bar">
    {#if running}
      <div class="run" aria-live="polite">
        <div class="run-line">
          <span class="num percent">{percent} %</span>
          <span class="stage">{s?.phase === "cancelling" ? t("cancelling") : s?.running || t("dock.forging")}</span>
          {#if s?.eta}<span class="faint num">{t("eta", { time: clock(s.eta) })}</span>{/if}
          {#if s?.task === "queue" && n?.queue.length}<span class="faint">· {t("queue_count", { count: n.queue.length })}</span>{/if}
        </div>
        <div class="progress"><span style:width={`${percent}%`}></span></div>
      </div>
      <button class="btn" class:on={details} aria-pressed={details} onclick={() => (details = !details)}>{t("progress_details")}</button>
      <button class="btn" disabled={s?.phase !== "running"} onclick={() => app.call("cancel")}>{t("cancel")}</button>
    {:else}
      <div class="budget {level}" title={t("estimate_tip")}>
        <span class="faint">{t("dock.budget")}</span>
        <span class="num value">{n?.estimate ? grouped(n.estimate) : "—"} / ~{grouped(32000)}</span>
        <span class="meter"><span style:width={`${share * 100}%`}></span><i style:left={`${(budget / 32000) * 100}%`}></i></span>
      </div>
      <p class="note" class:problem={!!n?.problem} title={n?.problem ?? n?.hint}>
        {#if n?.problem}<Icon name="warning" />{/if}
        <span>{n?.problem ?? n?.hint}</span>
      </p>
      <button class="btn" disabled={!!n?.problem || s?.busy} title={t("queue_hint")} onclick={() => app.act("enqueue")}>{t("enqueue")}</button>
      <button class="btn primary generate" disabled={!!n?.problem || s?.busy} onclick={() => app.act("start")} title={n?.problem ?? "Ctrl+Enter"}>{t("generate")}</button>
    {/if}
  </div>
</div>

<style>
  .dock {
    flex: none;
    border-top: 1px solid var(--line);
    background: var(--panel);
  }
  .bar {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 44px;
    padding: 8px 12px;
  }
  .budget {
    display: grid;
    grid-template-columns: auto auto;
    align-items: center;
    gap: 2px 8px;
    flex: none;
    font-size: 12px;
  }
  .value {
    text-align: right;
  }
  .meter {
    position: relative;
    grid-column: 1 / -1;
    height: 4px;
    background: var(--field);
    border: 1px solid var(--line-2);
  }
  .meter span {
    display: block;
    height: 100%;
    background: var(--ok);
  }
  .meter i {
    position: absolute;
    top: -3px;
    width: 1px;
    height: 8px;
    background: var(--text-2);
  }
  .near .meter span {
    background: var(--warn);
  }
  .over .meter span {
    background: var(--danger);
  }
  .over .value {
    color: var(--danger);
  }
  .note {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 6px;
    padding-left: 8px;
    border-left: 1px solid var(--line);
    color: var(--text-3);
    font-size: 12px;
    line-height: 1.35;
  }
  .note span {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .note.problem {
    color: var(--warn);
  }
  .generate {
    min-width: 96px;
  }
  .run {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 4px;
  }
  .run-line {
    display: flex;
    align-items: baseline;
    gap: 8px;
    min-width: 0;
    font-size: 12px;
    white-space: nowrap;
  }
  .percent {
    font-weight: 600;
    min-width: 36px;
  }
  .stage {
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }
  .outcome {
    align-items: center;
    margin: 8px 12px 0;
  }
  .outcome p {
    flex: 1;
    min-width: 0;
  }
  .failure {
    max-height: 96px;
    overflow: auto;
    overflow-wrap: anywhere;
  }
  .buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .queue {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 8px 12px 0;
    padding: 4px 4px 4px 10px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--bg);
    font-size: 12px;
  }
  .queue-title {
    flex: none;
    font-weight: 600;
  }
  .jobs {
    flex: 1;
    min-width: 0;
    display: flex;
    gap: 12px;
    margin: 0;
    padding: 0;
    list-style: none;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .jobs .mono {
    font-size: 11px;
  }
  .stages {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 2px 12px;
    max-height: 160px;
    margin: 0;
    padding: 8px 12px;
    list-style: none;
    border-bottom: 1px solid var(--line);
    font-size: 12px;
  }
  .stages li {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text-3);
    min-width: 0;
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
  .blank {
    width: 16px;
    flex: none;
  }
  .stages .spinner {
    margin: 0 2px;
  }
</style>
