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
</script>

{#if jobs.length}
  <section class="queue" aria-label={t("queue_title")}>
    <header>
      <h3>{t("queue_title")}</h3>
      <span class="num faint">{t("queue_count", { count: jobs.length })}</span>
      <span class="spacer"></span>
      <button class="btn small" disabled={busy} onclick={() => app.act("start_queue")}>{t("run_queue")}</button>
      <button class="btn small ghost" onclick={() => app.call("clear_queue")}>{t("clear_queue")}</button>
    </header>
    {#if busy && n?.queue_follows}<p class="hint">{t("queue_follows")}</p>{/if}
    <ol>
      {#each jobs as job (job.code)}
        <li class:running={job.running}>
          {#if job.running}<span class="spinner" title={t("queue_making")}></span>{:else}<span class="blank"></span>{/if}
          <span class="ellipsis">{job.type}</span>
          <code class="faint selectable">{job.seed}</code>
          <button
            class="btn icon small ghost"
            disabled={job.running}
            title={t("queue_remove")}
            aria-label={t("queue_remove")}
            onclick={() => app.call("dequeue", { code: job.code })}
          ><Icon name="x" /></button>
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
    align-items: center;
    gap: 6px;
    min-width: 0;
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
