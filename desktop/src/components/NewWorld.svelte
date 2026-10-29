<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import { copyText, openFile, pickFolder, readText, saveFile } from "../lib/native";
  import GenerateDock from "./GenerateDock.svelte";
  import Icon from "./Icon.svelte";
  import ControlRow from "./ui/ControlRow.svelte";
  import Segmented from "./ui/Segmented.svelte";
  import Toggle from "./ui/Toggle.svelte";
  import TypeGlyph from "./ui/TypeGlyph.svelte";

  const s = $derived(app.now);
  const n = $derived(s?.new);
  const busy = $derived(!!s?.busy);
  let seedText = $state<string | null>(null);
  let codeText = $state<string | null>(null);
  let advanced = $state(false);
  let openGroups = $state<Record<string, boolean>>({ land: true, map: true, peoples: true });

  const IMAGES = [{ name: "PNG, JPEG, BMP, TIFF", extensions: ["png", "jpg", "jpeg", "bmp", "tif", "tiff"] }];

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

  async function landImage(): Promise<void> {
    const path = await openFile(t("land_image_title"), IMAGES);
    if (path) await app.act("choose_land_image", { path });
  }

  async function template(): Promise<void> {
    const path = await saveFile(t("land_template"), "new-world-template.png", [{ name: "PNG", extensions: ["png"] }]);
    if (path) await app.act("save_land_template", { path });
  }

  async function destination(kind: string): Promise<void> {
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

  const groups = $derived(app.info?.groups ?? []);
  const controls = $derived(app.info?.controls.filter((c) => c.advanced) ?? []);
</script>

<div class="page">
  <div class="content scroll">
    <header class="hero">
      <div class="hero-text">
        <span class="eyebrow">{t("forge.eyebrow")}</span>
        <h1>{t("new_world")}</h1>
        <p class="dim">{t(`type.${n?.choice}.about`)}</p>
      </div>
      <div class="code-pill" title={t("code_hint")}>
        <span class="eyebrow">{t("code")}</span>
        <code class="selectable">{n?.code}</code>
        <button class="btn icon small ghost" title={t("copy")} aria-label={t("copy")} onclick={copyCode}><Icon name="copy" size={15} /></button>
        <button class="btn icon small ghost" title={t("paste")} aria-label={t("paste")} disabled={busy} onclick={paste}><Icon name="paste" size={15} /></button>
      </div>
    </header>

    {#if n?.notice}
      <div class="callout warn"><Icon name="warning" /><p>{n.notice}</p></div>
    {/if}

    <section class="section">
      <h3>{t("type")}</h3>
      <div class="types" role="radiogroup" aria-label={t("type")}>
        {#each app.info?.choices ?? [] as choice (choice)}
          <button
            class="type"
            class:on={n?.choice === choice}
            class:mode={app.info?.modes.includes(choice)}
            role="radio"
            aria-checked={n?.choice === choice}
            disabled={busy}
            title={t(`type.${choice}.about`)}
            onclick={() => app.call("set_choice", { choice })}
          >
            <span class="glyph"><TypeGlyph kind={choice} /></span>
            <span class="type-name">{t(`type.${choice}`)}</span>
          </button>
        {/each}
      </div>
      {#if n?.mode}
        <p class="faint small">{t("forge.drawn", { type: t(`type.${n.preset}`) })}</p>
      {/if}
    </section>

    <section class="section card padded">
      <div class="section-head">
        <h3>{t("quick")}</h3>
        <p class="faint small">{t("quick_hint")}</p>
      </div>
      <div class="quick">
        {#each app.info?.quick ?? [] as item (item.name)}
          <div class="quick-row">
            <div class="quick-name" title={t(`quick.${item.name}.about`)}>
              <span>{t(`quick.${item.name}`)}</span>
              {#if n && n.quick[item.name] === null}<span class="badge warn">{t("quick.custom")}</span>{/if}
              <span class="faint small about">{t(`quick.${item.name}.about`)}</span>
            </div>
            <Segmented
              label={t(`quick.${item.name}`)}
              disabled={busy}
              value={n?.quick[item.name] ?? null}
              options={item.levels.map((level) => ({ value: level, label: t(`quick.${item.name}.${level}`) }))}
              onchange={(level) => app.call("set_quick", { name: item.name, level })}
            />
          </div>
        {/each}
      </div>
      <div class="divider"></div>
      <Toggle
        checked={(n?.values["new_world.expand_oceans"]?.shown ?? 0) > 0}
        disabled={busy}
        label={t("control.new_world.expand_oceans")}
        hint={t("control.new_world.expand_oceans.about")}
        onchange={(value) => app.call("set_value", { key: "new_world.expand_oceans", value: value ? 1 : 0 })}
      />
    </section>

    <section class="section card padded">
      <div class="section-head"><h3>{t("world_identity")}</h3></div>
      <div class="identity">
        <label class="field">
          <span class="field-label">{t("seed")}</span>
          <div class="inline">
            <input
              class="input mono"
              value={seedText ?? n?.seed ?? ""}
              disabled={busy}
              inputmode="numeric"
              aria-label={t("seed")}
              oninput={(event) => (seedText = (event.currentTarget as HTMLInputElement).value)}
              onblur={seedDone}
              onkeydown={(event) => event.key === "Enter" && (event.currentTarget as HTMLInputElement).blur()}
            />
            <button class="btn" disabled={busy} onclick={() => app.call("randomize")} title={t("random")}>
              <Icon name="dice" size={16} />{t("random")}
            </button>
          </div>
        </label>
        <label class="field">
          <span class="field-label">{t("code")}</span>
          <div class="inline">
            <input
              class="input mono"
              value={codeText ?? n?.code ?? ""}
              placeholder={t("code_hint")}
              disabled={busy}
              aria-label={t("code")}
              oninput={(event) => (codeText = (event.currentTarget as HTMLInputElement).value)}
              onblur={codeDone}
              onkeydown={(event) => event.key === "Enter" && (event.currentTarget as HTMLInputElement).blur()}
            />
            <button class="btn icon" onclick={copyCode} title={t("copy")} aria-label={t("copy")}><Icon name="copy" size={16} /></button>
            <button class="btn icon" disabled={busy} onclick={paste} title={t("paste")} aria-label={t("paste")}><Icon name="paste" size={16} /></button>
          </div>
          <span class="faint small">{t("code_hint")}</span>
        </label>
      </div>
    </section>

    <section class="section card padded">
      <div class="section-head"><h3>{t("land_tools")}</h3></div>
      <div class="tools">
        <button class="tool" disabled={!n?.candidates_enabled} onclick={() => app.act("sketch_candidates")}>
          <span class="tool-icon"><Icon name="grid" /></span>
          <span class="tool-text"><strong>{t("candidates")}</strong><span class="faint small">{t("candidates_hint")}</span></span>
        </button>
        <div class="tool land" class:chosen={!!n?.land_mask}>
          <span class="tool-icon"><Icon name="image" /></span>
          <span class="tool-text">
            <strong>{n?.land_mask ? n.land_mask_text : t("land_image")}</strong>
            <span class="faint small">{t("land_image_tip")}</span>
            <span class="tool-actions">
              <button class="btn small" disabled={busy} onclick={landImage}><Icon name="upload" size={14} />{t("land_image")}</button>
              {#if n?.land_mask}
                <button class="btn small ghost" disabled={busy} onclick={() => app.call("clear_land_image")}>{t("land_image_clear")}</button>
              {/if}
              <button class="btn small ghost" disabled={!n?.template_enabled} title={t("land_template_tip")} onclick={template}><Icon name="download" size={14} />{t("land_template")}</button>
            </span>
          </span>
        </div>
      </div>
    </section>

    <section class="section card">
      <button class="collapse" onclick={() => (advanced = !advanced)} aria-expanded={advanced}>
        <Icon name="sliders" />
        <span class="collapse-text">
          <h3>{t("customize")}</h3>
          <span class="faint small">{n?.changed ? t("customized", { count: n.changed }) : t("customize_hint")}</span>
        </span>
        {#if n?.changed}<span class="badge accent">{n.changed}</span>{/if}
        <Icon name={advanced ? "chevronDown" : "chevronRight"} />
      </button>
      {#if advanced}
        <div class="advanced">
          <p class="faint small">{t("customize_hint")}</p>
          {#each groups as group (group)}
            <div class="group">
              <button class="group-head" onclick={() => (openGroups[group] = !openGroups[group])} aria-expanded={openGroups[group]}>
                <span class="eyebrow">{t(`group.${group}`)}</span>
                <Icon name={openGroups[group] ? "chevronDown" : "chevronRight"} size={14} />
              </button>
              {#if openGroups[group]}
                {#each controls.filter((c) => c.group === group) as control (control.key)}
                  {#if n?.values[control.key]}
                    <ControlRow {control} value={n.values[control.key]} disabled={busy} />
                  {/if}
                {/each}
              {/if}
            </div>
          {/each}
          <button class="btn small" disabled={!n?.changed || busy} onclick={() => app.call("reset_values")}>
            <Icon name="undo" size={14} />{t("reset_all")}
          </button>
        </div>
      {/if}
    </section>

    <section class="section card padded">
      <div class="section-head">
        <h3>{t("output")}</h3>
        <p class="faint small">{t("output_hint")}</p>
      </div>
      <Segmented
        label={t("output")}
        disabled={busy}
        value={n?.destination ?? "library"}
        options={(app.info?.destinations ?? []).map((key) => ({ value: key, label: t(`destination.${key}`) }))}
        onchange={destination}
      />
      {#if n && n.destination !== "library"}
        <div class="target">
          <Icon name={n.destination === "mod" ? "folder" : "file"} size={16} />
          <span class="mono selectable path" title={n.target}>{n.target || t("destination_missing")}</span>
          <button class="btn small" disabled={busy} onclick={() => chooseTarget()}>{t("destination_choose")}</button>
        </div>
      {:else}
        <div class="spaced">
          <Toggle
            checked={!!n?.install}
            disabled={busy}
            label={t("install")}
            hint={n?.install ? t("generation_install") : t("generation_keep")}
            onchange={(value) => app.call("set_install", { value })}
          />
        </div>
      {/if}
      <div class="divider"></div>
      <Toggle
        checked={!!s?.preferences.show_new_world}
        disabled={busy}
        label={t("show_new_world")}
        hint={t("show_new_world_hint")}
        onchange={(value) => app.call("set_show_new_world", { value })}
      />
    </section>
  </div>

  <aside class="side scroll">
    <GenerateDock />
  </aside>
</div>

<style>
  .page {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    height: 100%;
    min-height: 0;
  }
  .content {
    padding: 28px 32px 48px;
    display: grid;
    gap: 18px;
    align-content: start;
    min-height: 0;
  }
  .side {
    padding: 28px 24px 28px 0;
    min-height: 0;
  }
  .hero {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 20px;
    flex-wrap: wrap;
    padding-bottom: 4px;
  }
  .hero-text {
    display: grid;
    gap: 6px;
    max-width: 640px;
  }
  .hero h1 {
    font-size: 36px;
  }
  .code-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 6px 6px 14px;
    border-radius: 999px;
    border: 1px solid var(--line-2);
    background: var(--panel);
    max-width: 100%;
    min-width: 0;
  }
  .code-pill code {
    font-size: 12px;
    color: var(--text-2);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 280px;
  }
  .section {
    display: grid;
    gap: 12px;
  }
  .padded {
    padding: 18px 20px;
  }
  .section-head {
    display: grid;
    gap: 3px;
  }
  .small {
    font-size: 12.5px;
    line-height: 1.45;
  }
  .types {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
    gap: 10px;
  }
  .type {
    display: grid;
    gap: 8px;
    padding: 10px;
    border-radius: 14px;
    border: 1px solid var(--line);
    background: var(--panel);
    color: var(--text-2);
    cursor: pointer;
    text-align: center;
    font: 600 12.5px var(--font);
    transition: all var(--speed) var(--ease);
  }
  .type:hover:not(:disabled) {
    border-color: var(--line-3);
    color: var(--text);
    transform: translateY(-1px);
  }
  .type.on {
    border-color: var(--accent-line);
    background: linear-gradient(180deg, var(--accent-soft), transparent 80%), var(--panel);
    color: var(--text);
    box-shadow: var(--glow);
  }
  .type:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .glyph {
    display: block;
    aspect-ratio: 4 / 3;
    border-radius: 10px;
    background: var(--bg-2);
    padding: 6px;
  }
  .type.mode .glyph {
    background: linear-gradient(135deg, var(--sea-soft), var(--accent-soft));
  }
  .quick {
    display: grid;
    gap: 4px;
  }
  .quick-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 8px 0;
    flex-wrap: wrap;
  }
  .quick-name {
    display: grid;
    grid-template-columns: auto auto;
    justify-content: start;
    align-items: center;
    gap: 2px 10px;
    font-weight: 550;
    max-width: 420px;
  }
  .quick-name .about {
    grid-column: 1 / -1;
    font-weight: 400;
  }
  .divider {
    height: 1px;
    background: var(--line);
    margin: 4px 0;
  }
  .identity {
    display: grid;
    gap: 14px;
  }
  .field {
    display: grid;
    gap: 6px;
  }
  .field-label {
    font-size: 12.5px;
    font-weight: 600;
    color: var(--text-2);
  }
  .inline {
    display: flex;
    gap: 8px;
  }
  .inline .input {
    flex: 1;
  }
  .tools {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
  }
  .tool {
    display: flex;
    gap: 14px;
    padding: 14px;
    border-radius: 12px;
    border: 1px solid var(--line);
    background: var(--bg-2);
    color: var(--text);
    text-align: left;
    font: inherit;
  }
  button.tool {
    cursor: pointer;
    transition: border-color var(--speed) var(--ease);
  }
  button.tool:hover:not(:disabled) {
    border-color: var(--accent-line);
  }
  button.tool:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .tool.chosen {
    border-color: var(--accent-line);
  }
  .tool-icon {
    flex: none;
    display: grid;
    place-items: center;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    background: var(--accent-soft);
    color: var(--accent);
  }
  .tool-text {
    display: grid;
    gap: 4px;
    align-content: start;
  }
  .tool-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
  }
  .collapse {
    display: flex;
    align-items: center;
    gap: 14px;
    width: 100%;
    padding: 18px 20px;
    border: 0;
    background: transparent;
    color: var(--text);
    cursor: pointer;
    text-align: left;
    font: inherit;
  }
  .collapse > :global(svg:first-child) {
    color: var(--accent);
  }
  .collapse-text {
    flex: 1;
    display: grid;
    gap: 2px;
  }
  .advanced {
    padding: 0 20px 18px;
    display: grid;
    gap: 14px;
  }
  .advanced > .btn {
    justify-self: start;
  }
  .group {
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 4px 14px 6px;
    background: var(--bg-2);
  }
  .group-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 10px 0 6px;
    border: 0;
    background: none;
    color: var(--text-2);
    cursor: pointer;
  }
  .target {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--bg-2);
    border: 1px dashed var(--line-3);
    color: var(--text-2);
  }
  .path {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12px;
  }
  .spaced {
    padding-top: 4px;
  }
  @media (max-width: 1160px) {
    .page {
      grid-template-columns: 1fr;
      overflow: auto;
    }
    .content {
      overflow: visible;
    }
    .side {
      padding: 0 32px 32px;
      overflow: visible;
    }
  }
</style>
