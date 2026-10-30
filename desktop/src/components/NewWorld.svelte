<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import { copyText, openFile, pickFolder, readText, saveFile } from "../lib/native";
  import GenerateDock from "./GenerateDock.svelte";
  import Icon from "./Icon.svelte";
  import Check from "./ui/Check.svelte";
  import ControlRow from "./ui/ControlRow.svelte";
  import Segmented from "./ui/Segmented.svelte";

  const s = $derived(app.now);
  const n = $derived(s?.new);
  const busy = $derived(!!s?.busy);
  let seedText = $state<string | null>(null);
  let codeText = $state<string | null>(null);
  let advanced = $state(false);

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

  const groups = $derived(app.info?.groups ?? []);
  const controls = $derived(app.info?.controls.filter((c) => c.advanced) ?? []);
</script>

<div class="page">
  <div class="content scroll">
    <div class="sheet">
      {#if n?.notice}
        <div class="msg warn"><Icon name="warning" /><p>{n.notice}</p></div>
      {/if}

      <section>
        <h3 class="group-title">{t("new_tab.world")}</h3>
        <div class="form">
          <label class="label" for="world-type">{t("type")}</label>
          <select
            id="world-type"
            class="input"
            value={n?.choice}
            disabled={busy}
            onchange={(event) => app.call("set_choice", { choice: (event.currentTarget as HTMLSelectElement).value })}
          >
            {#each app.info?.choices ?? [] as choice (choice)}
              <option value={choice}>{t(`type.${choice}`)}</option>
            {/each}
          </select>
          <p class="span hint">
            {t(`type.${n?.choice}.about`)}
            {#if n?.mode}{t("forge.drawn", { type: t(`type.${n.preset}`) })}{/if}
          </p>

          {#each app.info?.quick ?? [] as item (item.name)}
            <span class="label" title={t(`quick.${item.name}.about`)}>
              {t(`quick.${item.name}`)}{#if n && n.quick[item.name] === null}<span class="custom"> · {t("quick.custom")}</span>{/if}
            </span>
            <Segmented
              label={t(`quick.${item.name}`)}
              disabled={busy}
              value={n?.quick[item.name] ?? null}
              options={item.levels.map((level) => ({ value: level, label: t(`quick.${item.name}.${level}`), title: t(`quick.${item.name}.about`) }))}
              onchange={(level) => app.call("set_quick", { name: item.name, level })}
            />
          {/each}

          <div class="span spaced">
            <Check
              checked={(n?.values["new_world.expand_oceans"]?.shown ?? 0) > 0}
              disabled={busy}
              label={t("control.new_world.expand_oceans")}
              hint={t("control.new_world.expand_oceans.about")}
              onchange={(value) => app.call("set_value", { key: "new_world.expand_oceans", value: value ? 1 : 0 })}
            />
          </div>
        </div>
      </section>

      <section>
        <h3 class="group-title">{t("world_identity")}</h3>
        <div class="form">
          <label class="label" for="seed">{t("seed")}</label>
          <div class="row">
            <input
              id="seed"
              class="input mono"
              value={seedText ?? n?.seed ?? ""}
              disabled={busy}
              inputmode="numeric"
              oninput={(event) => (seedText = (event.currentTarget as HTMLInputElement).value)}
              onblur={seedDone}
              onkeydown={(event) => event.key === "Enter" && (event.currentTarget as HTMLInputElement).blur()}
            />
            <button class="btn" disabled={busy} onclick={() => app.call("randomize")}>{t("random")}</button>
          </div>
          <label class="label" for="code">{t("code")}</label>
          <div class="row">
            <input
              id="code"
              class="input mono"
              value={codeText ?? n?.code ?? ""}
              placeholder={t("code_hint")}
              title={t("code_hint")}
              disabled={busy}
              oninput={(event) => (codeText = (event.currentTarget as HTMLInputElement).value)}
              onblur={codeDone}
              onkeydown={(event) => event.key === "Enter" && (event.currentTarget as HTMLInputElement).blur()}
            />
            <button class="btn icon" onclick={copyCode} title={t("copy")} aria-label={t("copy")}><Icon name="copy" /></button>
            <button class="btn icon" disabled={busy} onclick={paste} title={t("paste")} aria-label={t("paste")}><Icon name="paste" /></button>
          </div>
          <p class="span hint">{t("code_hint")}</p>
        </div>
      </section>

      <section>
        <h3 class="group-title">{t("land_tools")}</h3>
        <div class="form">
          <span class="label top">{t("quick.land")}</span>
          <div class="stack">
            <div class="row wrap">
              <button class="btn" disabled={!n?.candidates_enabled} title={t("candidates_hint")} onclick={() => app.act("sketch_candidates")}>{t("candidates")}</button>
              <button class="btn" disabled={busy} title={t("land_image_tip")} onclick={landImage}>{t("land_image")}</button>
              <button class="btn" disabled={!n?.template_enabled} title={t("land_template_tip")} onclick={template}>{t("land_template")}</button>
            </div>
            {#if n?.land_mask}
              <div class="row chosen">
                <Icon name="image" />
                <span class="selectable path" title={n.land_mask}>{n.land_mask_text}</span>
                <button class="btn small" disabled={busy} onclick={() => app.call("clear_land_image")}>{t("land_image_clear")}</button>
              </div>
            {/if}
            <p class="hint">{t("candidates_hint")}</p>
          </div>
        </div>
      </section>

      <section>
        <div class="group-title custom-head">
          <button class="disclose" onclick={() => (advanced = !advanced)} aria-expanded={advanced}>
            <Icon name={advanced ? "chevronDown" : "chevronRight"} />
            {t("customize")}
            <span class="faint">{n?.changed ? t("custom_some", { count: n.changed }) : ""}</span>
          </button>
        </div>
        {#if advanced}
          <p class="hint">{t("customize_hint")}</p>
          <div class="form controls">
            {#each groups as group (group)}
              <h4 class="full sub">{t(`group.${group}`)}</h4>
              {#each controls.filter((c) => c.group === group) as control (control.key)}
                {#if n?.values[control.key]}
                  <ControlRow {control} value={n.values[control.key]} disabled={busy} />
                {/if}
              {/each}
            {/each}
            <div class="span">
              <button class="btn small" disabled={!n?.changed || busy} onclick={() => app.call("reset_values")}>{t("reset_all")}</button>
            </div>
          </div>
        {/if}
      </section>

      <section>
        <h3 class="group-title">{t("output")}</h3>
        <div class="form">
          <div class="span stack" role="radiogroup" aria-label={t("output")}>
            {#each app.info?.destinations ?? [] as key (key)}
              <label class="check" class:disabled={busy}>
                <input type="radio" name="destination" checked={(n?.destination ?? "library") === key} disabled={busy} onchange={() => destination(key)} />
                <span>{t(`destination.${key}`)}</span>
              </label>
            {/each}
            <p class="hint">{t("output_hint")}</p>
          </div>
          {#if n && n.destination !== "library"}
            <div class="span row">
              <input class="input mono" readonly value={n.target} placeholder={t("destination_missing")} title={n.target} />
              <button class="btn" disabled={busy} onclick={() => chooseTarget()}>{t("destination_choose")}</button>
            </div>
          {:else}
            <div class="span">
              <Check
                checked={!!n?.install}
                disabled={busy}
                label={t("install")}
                hint={n?.install ? t("generation_install") : t("generation_keep")}
                onchange={(value) => app.call("set_install", { value })}
              />
            </div>
          {/if}
          <div class="span">
            <Check
              checked={!!s?.preferences.show_new_world}
              disabled={busy}
              label={t("show_new_world")}
              hint={t("show_new_world_hint")}
              onchange={(value) => app.call("set_show_new_world", { value })}
            />
          </div>
        </div>
      </section>
    </div>
  </div>

  <GenerateDock />
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }
  .content {
    flex: 1;
    min-height: 0;
  }
  .sheet {
    display: grid;
    gap: 16px;
    max-width: 820px;
    padding: 12px 16px 20px;
  }
  section {
    display: grid;
    gap: 8px;
  }
  .custom {
    color: var(--warn);
    font-size: 12px;
  }
  .spaced {
    padding-top: 4px;
  }
  .stack {
    display: grid;
    gap: 6px;
    min-width: 0;
  }
  .wrap {
    flex-wrap: wrap;
  }
  .chosen {
    padding: 4px 6px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel);
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
  .custom-head {
    gap: 0;
  }
  .disclose {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0 6px 0 0;
    border: 0;
    background: none;
    color: var(--text-2);
    font: 600 12px var(--font);
  }
  .disclose:hover {
    color: var(--text);
  }
  .disclose .faint {
    font-weight: 400;
    margin-left: 4px;
  }
  .controls {
    gap: 4px 12px;
  }
  .sub {
    margin: 6px 0 0;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-3);
  }
  .sub:first-child {
    margin-top: 0;
  }
</style>
