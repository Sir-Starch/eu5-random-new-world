<script lang="ts">
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
  const generating = $derived(!!s?.generating && s.task !== "candidates");
  const running = $derived(!!s?.busy && generating);
  const percent = $derived(Math.round((s?.fraction ?? 0) * 100));
  let details = $state(false);

  async function generate(): Promise<void> {
    await app.act("start");
  }
</script>

<div class="dock">
  <section class="card budget" title={t("estimate_tip")} class:over={level === "over"} class:near={level === "near"}>
    <div class="row">
      <span class="eyebrow">{t("dock.budget")}</span>
      <span class="num value">{n?.estimate ? grouped(n.estimate) : "—"}<span class="faint"> / ~{grouped(32000)}</span></span>
    </div>
    <div class="meter" title={t("estimate_tip")}>
      <span class="fill" style:width={`${share * 100}%`}></span>
      <span class="limit" style:left={`${(budget / 32000) * 100}%`}></span>
    </div>
    {#if n?.over_budget}<p class="small over-text">{n.problem}</p>{/if}
  </section>

  {#if !running}
    <section class="card go">
      <div class="summary">
        <div><span class="eyebrow">{t("type")}</span><strong>{t(`type.${n?.choice}`)}</strong></div>
        <div><span class="eyebrow">{t("seed")}</span><strong class="mono">{n?.seed}</strong></div>
        <div><span class="eyebrow">{t("customize")}</span><strong>{n?.changed ? t("custom_some", { count: n.changed }) : t("custom_none")}</strong></div>
      </div>
      <button class="btn primary big generate" disabled={!!n?.problem || s?.busy} onclick={generate} title={n?.problem ?? "Ctrl+Enter"}>
        <Icon name="sparkles" size={19} />
        {t("generate")}
      </button>
      <p class="hint" class:problem={!!n?.problem}>
        {#if n?.problem}<Icon name="warning" size={15} />{/if}
        <span>{n?.problem ?? n?.hint}</span>
      </p>

      {#if s?.task === "generate" || s?.task === "queue"}
        {#if s.phase === "finished" && s.result}
          <div class="callout accent done">
            <Icon name="check" />
            <div>
              <p>{s.status}</p>
              <button class="btn small" onclick={() => app.call("select", { id: s.result?.world })}>
                {t("dock.open_world")}<Icon name="chevronRight" size={14} />
              </button>
            </div>
          </div>
        {:else if s.phase === "failed"}
          <div class="callout error failure">
            <Icon name="alert" />
            <div class="failure-body">
              <p class="selectable">{s.status}</p>
              <div class="failure-actions">
                {#if n?.retry}
                  <button class="btn small" disabled={!n.retry_enabled} onclick={() => app.act("retry_new_seed")}>
                    <Icon name="dice" size={14} />{t("retry_new_seed")}
                  </button>
                {/if}
                <button class="btn small ghost" onclick={() => copyText(s.status)}><Icon name="copy" size={14} />{t("copy")}</button>
              </div>
            </div>
          </div>
        {:else if s.phase === "cancelled"}
          <div class="callout"><Icon name="info" /><p>{s.status}</p></div>
        {/if}
      {/if}
    </section>
  {:else}
    <section class="card progress" aria-live="polite">
      <div class="progress-head">
        <span class="big-number num">{percent}<small>%</small></span>
        <div class="progress-text">
          <strong>{s?.phase === "cancelling" ? t("cancelling") : t("dock.forging")}</strong>
          {#if s?.eta}<span class="faint num">{t("eta", { time: clock(s.eta) })}</span>{/if}
          {#if s?.task === "queue" && n?.queue.length}<span class="faint">{t("queue_count", { count: n.queue.length })}</span>{/if}
        </div>
      </div>
      <div class="bar"><span style:width={`${percent}%`}></span></div>
      <p class="stages-now dim">{s?.running || "…"}</p>
      <button class="details" onclick={() => (details = !details)} aria-expanded={details}>
        <Icon name={details ? "chevronDown" : "chevronRight"} size={14} />{t("progress_details")}
      </button>
      {#if details}
        <ol class="stages">
          {#each s?.stages ?? [] as stage, index (index)}
            <li class={stage.state}>
              <span class="mark">
                {#if stage.state === "done"}<Icon name="check" size={12} stroke={3} />{:else if stage.state === "running"}<span class="pulse"></span>{/if}
              </span>
              {stage.label}
            </li>
          {/each}
        </ol>
      {/if}
      <button class="btn danger" disabled={s?.phase !== "running"} onclick={() => app.call("cancel")}>
        <Icon name="stop" size={15} />{t("cancel")}
      </button>
    </section>
  {/if}

  <section class="card queue">
    <div class="row">
      <h3>{t("queue_title")}</h3>
      {#if n?.queue.length}<span class="badge accent num">{n.queue.length}</span>{/if}
    </div>
    <p class="faint small">{t("queue_hint")}</p>
    {#if n?.queue.length}
      <ol class="jobs">
        {#each n.queue as job, index (index)}
          <li><span class="num faint">{index + 1}</span><span>{job.type}</span><span class="mono faint">{job.seed}</span></li>
        {/each}
      </ol>
    {/if}
    <div class="queue-actions">
      <button class="btn small" disabled={!!n?.problem || s?.busy} onclick={() => app.act("enqueue")}><Icon name="plus" size={14} />{t("enqueue")}</button>
      <button class="btn small" disabled={s?.busy || !n?.queue.length} onclick={() => app.act("start_queue")}><Icon name="play" size={13} />{t("run_queue")}</button>
      <button class="btn small ghost" disabled={s?.busy || !n?.queue.length} onclick={() => app.call("clear_queue")}>{t("clear_queue")}</button>
    </div>
  </section>
</div>

<style>
  .dock {
    display: grid;
    gap: 14px;
    align-content: start;
  }
  .card {
    padding: 16px 18px;
  }
  .row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
  }
  .small {
    font-size: 12px;
    line-height: 1.45;
    margin-top: 6px;
  }
  .value {
    font-weight: 650;
  }
  .meter {
    position: relative;
    height: 8px;
    margin-top: 10px;
    border-radius: 999px;
    background: var(--panel-3);
    overflow: visible;
  }
  .fill {
    position: absolute;
    inset: 0 auto 0 0;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--ok), color-mix(in srgb, var(--ok) 60%, var(--accent)));
    transition: width 300ms var(--ease);
  }
  .near .fill {
    background: linear-gradient(90deg, var(--ok), var(--warn));
  }
  .over .fill {
    background: linear-gradient(90deg, var(--warn), var(--danger));
  }
  .over {
    border-color: color-mix(in srgb, var(--danger) 40%, transparent);
  }
  .over-text {
    color: var(--danger);
  }
  .limit {
    position: absolute;
    top: -4px;
    width: 2px;
    height: 16px;
    border-radius: 2px;
    background: var(--text-2);
  }
  .go {
    display: grid;
    gap: 14px;
  }
  .summary {
    display: grid;
    gap: 8px;
  }
  .summary div {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
    min-width: 0;
  }
  .summary strong {
    font-size: 13px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .generate {
    width: 100%;
  }
  .hint {
    display: flex;
    gap: 8px;
    font-size: 12.5px;
    color: var(--text-3);
    line-height: 1.45;
  }
  .hint.problem {
    color: var(--warn);
  }
  .hint :global(svg) {
    flex: none;
    margin-top: 2px;
  }
  .done div,
  .failure-body {
    display: grid;
    gap: 10px;
    min-width: 0;
  }
  .done .btn {
    justify-self: start;
  }
  .failure-body p {
    overflow-wrap: anywhere;
    max-height: 180px;
    overflow: auto;
  }
  .failure-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .progress {
    display: grid;
    gap: 12px;
    border-color: var(--accent-line);
    box-shadow: var(--glow);
  }
  .progress-head {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .big-number {
    font-family: var(--display);
    font-size: 44px;
    font-weight: 500;
    line-height: 1;
    color: var(--accent);
  }
  .big-number small {
    font-size: 20px;
    margin-left: 2px;
  }
  .progress-text {
    display: grid;
    gap: 2px;
  }
  .bar {
    height: 8px;
    border-radius: 999px;
    background: var(--panel-3);
    overflow: hidden;
  }
  .bar span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, var(--accent), var(--accent-2), var(--accent));
    background-size: 200% 100%;
    animation: shimmer 2.4s linear infinite;
    transition: width 400ms var(--ease);
  }
  .stages-now {
    font-size: 12.5px;
    min-height: 1.5em;
  }
  .details {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0;
    border: 0;
    background: none;
    color: var(--text-2);
    font: 550 12.5px var(--font);
    cursor: pointer;
    justify-self: start;
  }
  .stages {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 4px;
    max-height: 260px;
    overflow: auto;
    font-size: 12.5px;
  }
  .stages li {
    display: flex;
    align-items: center;
    gap: 9px;
    color: var(--text-3);
  }
  .stages li.running {
    color: var(--text);
    font-weight: 600;
  }
  .stages li.done {
    color: var(--text-2);
  }
  .mark {
    flex: none;
    display: grid;
    place-items: center;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 1.5px solid var(--line-2);
  }
  .done .mark {
    background: var(--ok-soft);
    border-color: transparent;
    color: var(--ok);
  }
  .running .mark {
    border-color: var(--accent);
  }
  .pulse {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--accent);
    animation: fade 0.9s ease-in-out infinite alternate;
  }
  .queue {
    display: grid;
    gap: 8px;
  }
  .jobs {
    list-style: none;
    margin: 4px 0 0;
    padding: 0;
    display: grid;
    gap: 4px;
    font-size: 12.5px;
  }
  .jobs li {
    display: grid;
    grid-template-columns: 18px 1fr auto;
    gap: 8px;
    padding: 6px 8px;
    border-radius: 8px;
    background: var(--panel-2);
  }
  .jobs .mono {
    font-size: 11px;
  }
  .queue-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
  }
</style>
