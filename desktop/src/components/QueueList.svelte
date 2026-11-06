<script lang="ts">
  // The worlds waiting to be made: the one being made first, then those added; they can be taken
  // out one by one or all together, and the queue run when nothing else is at work. Shown in the
  // middle of the window so that Add to queue visibly does something, from every page of the
  // inspector and while a world is being made.
  import { app, t } from "../lib/app.svelte";
  import Icon from "./Icon.svelte";

  const s = $derived(app.now);
  const n = $derived(s?.new);
  const busy = $derived(!!s?.busy);
  const jobs = $derived(n?.queue ?? []);
  const failed = $derived(n?.queue_failed ?? 0);
</script>

{#if jobs.length}
  <section class="queue" aria-label={t("queue_title")}>
    <header>
      <h3>{t("queue_title")}</h3>
      <span class="num faint">{t("queue_count", { count: jobs.length - failed })}</span>
      {#if failed}<span class="num bad">{t("queue_failed_count", { count: failed })}</span>{/if}
      <span class="spacer"></span>
      <button class="btn small" disabled={busy} onclick={() => app.act("start_queue")}>{t("run_queue")}</button>
      <button class="btn small ghost" onclick={() => app.call("clear_queue")}>{t("clear_queue")}</button>
    </header>
    {#if busy && n?.queue_follows}<p class="hint">{t("queue_follows")}</p>{/if}
    {#if failed}<p class="hint">{t("queue_failed_hint")}</p>{/if}
    <ol>
      {#each jobs as job (job.code)}
        <li class:running={job.running} class:failed={!!job.error}>
          {#if job.running}<span class="spinner" title={t("queue_making")}></span>{:else if job.error}<span class="mark bad" title={job.error}><Icon name="warning" /></span>{:else}<span class="blank"></span>{/if}
          <span class="ellipsis">{job.type}</span>
          <code class="faint selectable">{job.seed}</code>
          <button
            class="btn icon small ghost"
            disabled={job.running}
            title={t("queue_remove")}
            aria-label={t("queue_remove")}
            onclick={() => app.call("dequeue", { code: job.code })}
          ><Icon name="x" /></button>
          {#if job.error}<p class="error selectable" title={job.error}>{job.error}</p>{/if}
        </li>
      {/each}
    </ol>
  </section>
{/if}

<style>
  .queue {
    display: grid;
    gap: 6px;
    width: min(100%, 620px);
    margin: 0 auto;
    padding: 10px 12px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel);
    flex: none;
  }
  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 6px;
    min-width: 0;
  }
  header .num {
    white-space: nowrap;
  }
  h3 {
    margin: 0;
    font-size: 12px;
  }
  ol {
    display: grid;
    gap: 1px;
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: 12px;
  }
  li {
    display: grid;
    grid-template-columns: 16px minmax(0, 1fr) auto 24px;
    gap: 8px;
    align-items: center;
    min-height: 24px;
    padding: 0 2px 0 4px;
    color: var(--text-2);
  }
  li.running {
    color: var(--text);
    font-weight: 500;
  }
  .mark {
    display: block;
    width: 16px;
  }
  .bad {
    color: var(--danger);
  }
  .error {
    grid-column: 2 / -1;
    margin: 0 0 4px;
    font-size: 11px;
    line-height: 1.4;
    color: var(--danger);
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow-wrap: anywhere;
  }
  li code {
    font-size: 11px;
  }
  .blank {
    display: block;
    width: 16px;
  }
  .ellipsis {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
