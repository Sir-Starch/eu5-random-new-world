<script lang="ts">
  // The inspector of the new world: its type and basics, seed and code; the exact values; where
  // it goes and the queue. Under every tab: the location budget and Generate.
  import { app, grouped, t, type NewTab } from "../lib/app.svelte";
  import { copyText, pickFolder, readText, saveFile } from "../lib/native";
  import Icon from "./Icon.svelte";
  import Check from "./ui/Check.svelte";
  import Section from "./ui/Section.svelte";
  import Tabs from "./ui/Tabs.svelte";
  import ValueField from "./ui/ValueField.svelte";

  const s = $derived(app.now);
  const n = $derived(s?.new);
  const busy = $derived(!!s?.busy);
  let seedText = $state<string | null>(null);
  let codeText = $state<string | null>(null);

  const tabs = $derived<{ value: NewTab; label: string; count?: number }[]>([
    { value: "world", label: t("new_tab.world") },
    { value: "advanced", label: t("new_tab.advanced"), count: n?.changed || undefined },
    { value: "output", label: t("new_tab.output"), count: n?.queue.length || undefined },
  ]);

  const budget = $derived(app.info?.budget ?? 31200);
  const share = $derived(Math.min(1, (n?.estimate ?? 0) / 32000));
  const level = $derived(!n?.estimate ? "" : n.over_budget ? "over" : n.estimate > budget * 0.94 ? "near" : "ok");
  const running = $derived(busy && (s?.task === "generate" || s?.task === "queue"));
  const percent = $derived(Math.round((s?.fraction ?? 0) * 100));
  const groups = $derived(app.info?.groups ?? []);
  const controls = $derived(app.info?.controls.filter((c) => c.advanced) ?? []);

  async function seedDone(): Promise<void> {
    if (seedText === null) return;
    const value = seedText;
    seedText = null;
    if (value.trim() && value.trim() !== n?.seed) await app.act("set_seed", { value });
  }

  async function codeDone(): Promise<void> {
    if (codeText === null) return;
    const value = codeText;
    codeText = null;
    if (value.trim() && value.trim() !== n?.code) await app.act("use_code", { value });
  }

  async function paste(): Promise<void> {
    const text = (await readText()).trim();
    if (text) await app.act("set_seed", { value: text });
  }

  async function copyCode(): Promise<void> {
    if (!n) return;
    await copyText(n.code);
    app.toast("success", t("copied"));
  }

  async function destination(kind: string): Promise<void> {
    if (kind === n?.destination) return;
    await app.call("set_destination", { kind });
    if (kind !== "library") await chooseTarget(kind);
  }

  async function chooseTarget(kind = n?.destination ?? "library"): Promise<void> {
    const path =
      kind === "mod"
        ? await pickFolder(t("destination_choose"))
        : await saveFile(t("export_file"), "world.rnworld", [{ name: "World", extensions: ["rnworld"] }]);
    if (path) await app.call("set_destination", { kind, path });
  }

  function blurOnEnter(event: KeyboardEvent): void {
    if (event.key === "Enter") (event.currentTarget as HTMLInputElement).blur();
  }
</script>

<div class="pane-head">
  <Tabs label={t("new_world")} options={tabs} value={app.newTab} onchange={(tab) => (app.newTab = tab)} />
</div>

<div class="body scroll">
  {#if n?.notice}
    <div class="notice msg warn"><Icon name="warning" /><p>{n.notice}</p></div>
  {/if}

  {#if app.newTab === "world"}
    <Section id="new.basics" title={t("quick")}>
      <div class="props">
        <label class="key" for="world-type">{t("type")}</label>
        <select
          id="world-type"
          class="input val"
          value={n?.choice}
          disabled={busy}
          onchange={(event) => app.call("set_choice", { choice: event.currentTarget.value })}
        >
          {#each app.info?.choices ?? [] as choice (choice)}
            <option value={choice}>{t(`type.${choice}`)}</option>
          {/each}
        </select>
        <p class="wide hint">
          {t(`type.${n?.choice}.about`)}
          {#if n?.mode}{t("forge.drawn", { type: t(`type.${n.preset}`) })}{/if}
        </p>

        {#each app.info?.quick ?? [] as item (item.name)}
          <label class="key" for={`quick-${item.name}`} title={t(`quick.${item.name}.about`)}>{t(`quick.${item.name}`)}</label>
          <select
            id={`quick-${item.name}`}
            class="input val"
            class:custom={n?.quick[item.name] === null}
            title={t(`quick.${item.name}.about`)}
            value={n?.quick[item.name] ?? ""}
            disabled={busy}
            onchange={(event) => app.call("set_quick", { name: item.name, level: event.currentTarget.value })}
          >
            {#if n?.quick[item.name] === null}<option value="" disabled>{t("quick.custom")}</option>{/if}
            {#each item.levels as level (level)}
              <option value={level}>{t(`quick.${item.name}.${level}`)}</option>
            {/each}
          </select>
        {/each}

        <div class="wide oceans">
          <Check
            checked={(n?.values["new_world.expand_oceans"]?.shown ?? 0) > 0}
            disabled={busy}
            label={t("control.new_world.expand_oceans")}
            hint={t("control.new_world.expand_oceans.about")}
            onchange={(value) => app.call("set_value", { key: "new_world.expand_oceans", value: value ? 1 : 0 })}
          />
        </div>
      </div>
    </Section>

    <Section id="new.identity" title={t("world_identity")}>
      <label class="field">
        <span class="key">{t("seed")}</span>
        <span class="row">
          <input
            class="input mono"
            value={seedText ?? n?.seed ?? ""}
            disabled={busy}
            inputmode="numeric"
            oninput={(event) => (seedText = event.currentTarget.value)}
            onblur={seedDone}
            onkeydown={blurOnEnter}
          />
          <button class="btn" disabled={busy} onclick={() => app.call("randomize")}>{t("random")}</button>
        </span>
      </label>
      <label class="field">
        <span class="key">{t("code")}</span>
        <span class="row">
          <input
            class="input mono code"
            value={codeText ?? n?.code ?? ""}
            placeholder={t("code_hint")}
            title={t("code_hint")}
            disabled={busy}
            oninput={(event) => (codeText = event.currentTarget.value)}
            onblur={codeDone}
            onkeydown={blurOnEnter}
          />
          <button class="btn icon" onclick={copyCode} title={t("copy")} aria-label={t("copy")}><Icon name="copy" /></button>
          <button class="btn icon" disabled={busy} onclick={paste} title={t("paste")} aria-label={t("paste")}><Icon name="paste" /></button>
        </span>
      </label>
      <p class="hint">{t("code_hint")}</p>
    </Section>
  {:else if app.newTab === "advanced"}
    <div class="advanced-head">
      <p class="hint">{t("customize_hint")}</p>
      <button class="btn small" disabled={!n?.changed || busy} onclick={() => app.call("reset_values")}>{t("reset_all")}</button>
    </div>
    {#each groups as group (group)}
      {@const members = controls.filter((c) => c.group === group && n?.values[c.key])}
      {@const changed = members.filter((c) => n?.values[c.key]?.changed).length}
      {#if members.length}
      <Section id={`new.group.${group}`} title={t(`group.${group}`)}>
        {#snippet aside()}{#if changed}<span class="changed">{t("custom_some", { count: changed })}</span>{/if}{/snippet}
        {#if group === "resources"}<p class="hint">{t("group.resources.about")}</p>{/if}
        <div class="values">
          {#each members as control (control.key)}
            {#if n?.values[control.key]}
              {#if control.toggle}
                <Check checked={n.values[control.key].shown > 0} disabled={busy}
                  label={t(`control.${control.key}`)} hint={t(`control.${control.key}.about`)}
                  onchange={(value) => app.call("set_value", { key: control.key, value: value ? 1 : 0 })} />
              {:else}
                <ValueField {control} value={n.values[control.key]} disabled={busy} />
              {/if}
            {/if}
          {/each}
        </div>
      </Section>
      {/if}
    {/each}
  {:else}
    <Section id="new.output" title={t("output")}>
      <div class="choices" role="radiogroup" aria-label={t("output")}>
        {#each app.info?.destinations ?? [] as key (key)}
          <label class="check" class:disabled={busy}>
            <input type="radio" name="destination" checked={(n?.destination ?? "library") === key} disabled={busy} onchange={() => destination(key)} />
            <span>{t(`destination.${key}`)}</span>
          </label>
        {/each}
      </div>
      {#if n && n.destination !== "library"}
        <div class="row">
          <input class="input mono" readonly value={n.target} placeholder={t("destination_missing")} title={n.target} />
          <button class="btn" disabled={busy} onclick={() => chooseTarget()}>{t("destination_choose")}</button>
        </div>
      {:else}
        <Check
          checked={!!n?.install}
          disabled={busy}
          label={t("install")}
          hint={n?.install ? t("generation_install") : t("generation_keep")}
          onchange={(value) => app.call("set_install", { value })}
        />
      {/if}
      <Check
        checked={!!s?.preferences.show_new_world}
        disabled={busy}
        label={t("show_new_world")}
        hint={t("show_new_world_hint")}
        onchange={(value) => app.call("set_show_new_world", { value })}
      />
      <p class="hint">{t("output_hint")}</p>
    </Section>

    <Section id="new.queue" title={t("queue_title")}>
      {#snippet aside()}{#if n?.queue.length}<span class="num">{t("queue_count", { count: n.queue.length })}</span>{/if}{/snippet}
      <p class="hint">{t("queue_hint")}</p>
      {#if n?.queue.length}
        <ol class="queue">
          {#each n.queue as job, index (index)}
            <li><span class="num faint">{index + 1}</span><span class="ellipsis">{job.type}</span><code class="faint">{job.seed}</code></li>
          {/each}
        </ol>
        <div class="row">
          <button class="btn" disabled={busy} onclick={() => app.act("start_queue")}>{t("run_queue")}</button>
          <button class="btn ghost" disabled={busy} onclick={() => app.call("clear_queue")}>{t("clear_queue")}</button>
        </div>
      {/if}
    </Section>
  {/if}
</div>

<div class="generate">
  <div class="budget {level}" title={t("estimate_tip")}>
    <span class="key">{t("dock.budget")}</span>
    <span class="num value">{n?.estimate ? grouped(n.estimate) : "—"} / ~{grouped(32000)}</span>
    <span class="meter"><span style:width={`${share * 100}%`}></span><i style:left={`${(budget / 32000) * 100}%`}></i></span>
  </div>
  {#if running}
    <p class="note"><span class="spinner"></span><span>{s?.running || t("dock.forging")}</span><span class="num">{percent} %</span></p>
  {:else if n?.problem}
    <p class="note problem" title={n.problem}><Icon name="warning" /><span>{n.problem}</span></p>
  {:else}
    <p class="note" title={n?.hint}><span>{n?.hint}</span></p>
  {/if}
  <div class="actions">
    <button class="btn" disabled={!!n?.problem || busy} title={t("queue_hint")} onclick={() => app.act("enqueue")}>{t("enqueue")}</button>
    {#if running}
      <button class="btn grow" disabled={s?.phase !== "running"} onclick={() => app.call("cancel")}>{t("cancel")}</button>
    {:else}
      <button class="btn primary grow" disabled={!!n?.problem || busy} title={n?.problem ?? "Ctrl+Enter"} onclick={() => app.act("start")}>{t("generate")}</button>
    {/if}
  </div>
</div>

<style>
  .body {
    flex: 1;
    min-height: 0;
  }
  .notice {
    margin: 10px 12px 2px;
  }
  .props {
    padding-top: 2px;
  }
  .props .input {
    height: 24px;
    font-size: 12.5px;
  }
  .custom {
    color: var(--warn);
  }
  .oceans {
    padding-top: 4px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
  }
  .row > .input {
    flex: 1;
    min-width: 0;
  }
  .code {
    font-size: 11px;
  }
  .advanced-head {
    display: grid;
    justify-items: start;
    gap: 8px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--line);
  }
  .values {
    display: grid;
    gap: 4px;
  }
  .changed {
    color: var(--accent-text);
  }
  .choices {
    display: grid;
    gap: 4px;
  }
  .queue {
    display: grid;
    gap: 1px;
    margin: 0;
    padding: 4px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--field);
    list-style: none;
    font-size: 12px;
  }
  .queue li {
    display: grid;
    grid-template-columns: 18px minmax(0, 1fr) auto;
    gap: 6px;
    align-items: center;
    height: 20px;
    padding: 0 4px;
  }
  .queue code {
    font-size: 11px;
  }
  .ellipsis {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .generate {
    flex: none;
    display: grid;
    gap: 6px;
    padding: 10px 12px 12px;
    border-top: 1px solid var(--line);
    background: var(--panel);
  }
  .budget {
    display: grid;
    grid-template-columns: 1fr auto;
    align-items: baseline;
    gap: 3px 8px;
    font-size: 12px;
  }
  .budget .key {
    color: var(--text-2);
  }
  .meter {
    position: relative;
    grid-column: 1 / -1;
    height: 4px;
    background: var(--field);
    box-shadow: inset 0 0 0 1px var(--line-2);
  }
  .meter span {
    display: block;
    height: 100%;
    background: var(--ok);
  }
  .meter i {
    position: absolute;
    top: -2px;
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
    display: flex;
    align-items: flex-start;
    gap: 6px;
    min-height: 34px;
    color: var(--text-3);
    font-size: 12px;
    line-height: 1.4;
  }
  .note span:not(.spinner):not(.num) {
    flex: 1;
    min-width: 0;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .note .spinner {
    margin-top: 2px;
  }
  .note.problem {
    color: var(--warn);
  }
  .note :global(svg) {
    flex: none;
    margin-top: 1px;
  }
  .actions {
    display: flex;
    gap: 6px;
  }
  .grow {
    flex: 1;
  }
</style>
