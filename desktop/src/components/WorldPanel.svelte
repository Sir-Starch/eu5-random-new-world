<script lang="ts">
  // The inspector of a world: its name, place in the game, details, versions and files; the
  // lenses and legend of its map; the player's notes.
  import { app, grouped, t, when, type WorldTab } from "../lib/app.svelte";
  import { copyImage, copyText, openPath, pickFolder, saveFile } from "../lib/native";
  import { picture } from "../lib/pictures";
  import Icon from "./Icon.svelte";
  import MapLegend from "./MapLegend.svelte";
  import Check from "./ui/Check.svelte";
  import Section from "./ui/Section.svelte";
  import Tabs from "./ui/Tabs.svelte";

  const s = $derived(app.now);
  const w = $derived(s?.world);
  const busy = $derived(!!s?.busy);
  let name = $state<string | null>(null);
  let notes = $state<{ id: string; notes: string; tag: string; starred: boolean } | null>(null);
  let keepBoth = $state(false);

  $effect(() => {
    const world = w;
    if (world && notes?.id !== world.id) {
      notes = { id: world.id, notes: world.notes, tag: world.user_tag, starred: world.starred };
      name = null;
    }
  });

  const tabs = $derived<{ value: WorldTab; label: string }[]>([
    { value: "world", label: t("tab.world") },
    { value: "maps", label: t("tab.maps") },
    { value: "notes", label: t("tab.notes") },
  ]);

  const place = $derived(
    w?.placement === "in_game" ? t("list.in_game") : w?.placement === "kept" ? t("list.kept") : t("list.code_only"),
  );

  const details = $derived(
    w
      ? [
          ["detail.type", w.type],
          ["detail.seed", w.seed],
          ["detail.custom", w.custom],
          ["detail.made", when(w.created)],
          ["detail.build", w.build],
          ["detail.generator", w.generator],
        ]
      : [],
  );

  async function rename(): Promise<void> {
    if (!w || name === null) return;
    const value = name;
    name = null;
    if (value !== w.name) await app.act("rename", { id: w.id, name: value });
  }

  async function saveNotes(starred?: boolean): Promise<void> {
    if (!w || !notes) return;
    if (starred !== undefined) notes.starred = starred;
    const message = await app.call<string>("annotate", {
      id: w.id,
      notes: notes.notes,
      user_tag: notes.tag,
      starred: notes.starred,
    });
    if (message && starred === undefined) app.toast("success", message);
  }

  async function del(): Promise<void> {
    if (!w) return;
    const sure = await app.confirm(t("delete_title"), t("delete_question", { name: w.name }), t("delete"), true);
    if (sure) await app.act("delete_entries", { ids: [w.id] });
  }

  const fileName = (extension: string): string => `${(w?.name ?? "world").replace(/\s+/g, "-")}.${extension}`;

  async function exportFile(): Promise<void> {
    if (!w) return;
    const path = await saveFile(t("export_file"), fileName("rnworld"), [{ name: "World file", extensions: ["rnworld"] }]);
    if (path) await app.report("export_file", { id: w.id, path }, t("file_saved", { path }));
  }

  async function sendBuilt(): Promise<void> {
    if (!w) return;
    const sure = await app.confirm(t("send_built"), t("send_built_warning"), t("send_built"));
    if (!sure) return;
    const path = await saveFile(t("send_built"), fileName("rnworld-mod"), [{ name: "Built world", extensions: ["rnworld-mod"] }]);
    if (path) await app.act("send_built", { id: w.id, path });
  }

  async function copyMod(): Promise<void> {
    if (!w) return;
    const path = await pickFolder(t("copy_mod"));
    if (path) await app.act("copy_mod", { id: w.id, path });
  }

  async function savePreview(): Promise<void> {
    if (!w) return;
    const path = await saveFile(t("save_picture"), fileName("png"), [{ name: "PNG", extensions: ["png"] }]);
    if (path) await app.report("save_preview", { id: w.id, path }, t("picture_saved", { path }));
  }

  async function copy(text: string): Promise<void> {
    await copyText(text);
    app.toast("success", t("copied"));
  }

  async function copyPicture(): Promise<void> {
    if (!w) return;
    const url = await picture(w.id, w.picture);
    if (!url) return;
    await copyImage(url);
    app.toast("success", t("copied"));
  }

  async function openFolder(): Promise<void> {
    if (!w) return;
    const path = await app.call<string>("folder", { id: w.id });
    if (path) await openPath(path);
  }

  function saveKey(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
      event.preventDefault();
      void saveNotes();
    }
  }
</script>

{#if w}
  <div class="pane-head">
    <Tabs label={w.name} options={tabs} value={app.worldTab} onchange={(tab) => (app.worldTab = tab)} />
  </div>

  {#if app.worldTab === "world"}
    {#key w.id}
    <div class="body scroll">
      <div class="identity">
        <div class="name-row">
          <input
            class="name"
            value={name ?? w.name}
            maxlength={app.info?.name_limit}
            title={t("name_hint", { limit: app.info?.name_limit ?? 40 })}
            aria-label={t("name_hint", { limit: app.info?.name_limit ?? 40 })}
            oninput={(event) => (name = event.currentTarget.value)}
            onblur={rename}
            onkeydown={(event) => {
              if (event.key === "Enter") event.currentTarget.blur();
              if (event.key === "Escape") {
                name = null;
                event.currentTarget.blur();
              }
            }}
          />
          <button class="btn icon small ghost star" class:on={notes?.starred} aria-pressed={!!notes?.starred} title={t("starred")} aria-label={t("starred")} onclick={() => saveNotes(!notes?.starred)}>
            <Icon name="star" fill={!!notes?.starred} />
          </button>
        </div>
        <div class="facts">
          <span>{w.type}{w.part ? ` · ${w.part}` : ""}</span>
          <code class="selectable">{w.tag}</code>
          {#if w.user_tag}<span>{w.user_tag}</span>{/if}
        </div>
        <div class="placement">
          <span class="state"><span class="dot" class:ok={w.placement === "in_game"}></span><span class="cap">{place}</span></span>
          <span class="spacer"></span>
          {#if w.placement === "in_game"}
            <button class="btn small" disabled={!!w.remove_problem} title={w.remove_problem ?? t("remove_tip")} onclick={() => app.act("remove_entries", { ids: [w.id] })}>{t("remove")}</button>
          {:else}
            <button class="btn small primary" disabled={!!w.add_problem} title={w.add_problem ?? ""} onclick={() => app.act("add")}>{t("add")}</button>
          {/if}
          <button class="btn icon small" title={t("open_folder")} aria-label={t("open_folder")} onclick={openFolder}><Icon name="folder" /></button>
        </div>
        {#if w.task && (w.task.running || w.task.line)}
          <div class="task" class:failed={w.task.failed}>
            {#if w.task.running}<span class="spinner"></span>{:else}<Icon name="alert" />{/if}
            <span class="selectable">{w.task.line}</span>
            {#if w.task.bar}<span class="progress"><span style:width={`${Math.round(w.task.fraction * 100)}%`}></span></span>{/if}
          </div>
        {/if}
        {#if w.advice}<div class="msg info"><Icon name="info" /><p>{w.advice}</p></div>{/if}
        {#if w.note}<div class="msg warn"><Icon name="warning" /><p>{w.note}</p></div>{/if}
      </div>

      <Section id="world.details" title={t("world_details")}>
        {#if w.totals}
          <dl class="props">
            <dt class="key cap">{t("stat.countries")}</dt>
            <dd class="val"><span class="num">{grouped(w.totals.countries)}</span> <span class="faint small">{t("stat.split", { states: grouped(w.totals.states), tribes: grouped(w.totals.tribes) })}</span></dd>
            <dt class="key cap">{t("stat.cultures")}</dt>
            <dd class="val num">{grouped(w.totals.cultures)}</dd>
            <dt class="key cap">{t("stat.religions")}</dt>
            <dd class="val num">{grouped(w.totals.religions)}</dd>
            <dt class="key cap">{t("stat.land")}</dt>
            <dd class="val"><span class="num">{grouped(w.totals.land)}</span> <span class="faint small">{t("stat.locations", { count: grouped(w.totals.locations) })}</span></dd>
          </dl>
          <hr />
        {:else if w.summary}
          <p class="hint">{w.summary}</p>
        {/if}
        <dl class="props">
          <dt class="key wide">{t("detail.code")}</dt>
          <dd class="val wide code-row">
            <code class="selectable">{w.code}</code>
            <button class="btn icon small ghost" title={t("copy_code")} aria-label={t("copy_code")} onclick={() => copy(w.code)}><Icon name="copy" /></button>
          </dd>
          {#each details as [key, value] (key)}
            <dt class="key">{t(key)}</dt>
            <dd class="val selectable">{value}</dd>
          {/each}
          <dt class="key wide">{t("detail.place")}</dt>
          <dd class="val wide selectable small">{w.place}</dd>
          <dt class="key wide">{t("detail.reproduce")}</dt>
          <dd class="val wide reproduce">
            <span class="selectable small">{w.reproduce}</span>
            <button class="btn small" disabled={busy || !w.can_change} title={t("check_tip")} onclick={() => app.act("check")}>{t("check")}</button>
          </dd>
        </dl>
      </Section>

      <Section id="world.visibility" title={t("visibility")}>
        <Check checked={w.shown} disabled={busy} label={t("show_new_world")} hint={t("world_visibility_hint")} onchange={(value) => app.act("set_visibility", { id: w.id, value })} />
      </Section>

      <Section id="world.versions" title={t("world_versions")} closed>
        <p class="hint">{t("world.versions_intro")}</p>
        <div class="commands two">
          <button class="btn" disabled={!w.can_change} title={t("part.peoples.tip")} onclick={() => app.act("reroll", { part: "peoples", keep_both: keepBoth })}>{t("part.peoples.button")}</button>
          <button class="btn" disabled={!w.can_change} title={t("part.resources.tip")} onclick={() => app.act("reroll", { part: "resources", keep_both: keepBoth })}>{t("part.resources.button")}</button>
        </div>
        {#if w.placement === "in_game"}
          <Check checked={keepBoth} label={t("keep_both")} hint={t("keep_both_tip")} onchange={(value) => (keepBoth = value)} />
        {/if}
        <div class="commands">
          <button class="btn" disabled={busy} title={t("edit_same_land_tip")} onclick={() => app.call("edit")}>{t("edit_same_land")}</button>
          <button class="btn" disabled={busy} title={t("world.like_tip")} onclick={() => app.call("like", { id: w.id })}>{t("like_this")}</button>
          {#if w.parent}
            <button class="btn" title={w.parent_name} onclick={() => app.call("select", { id: w.parent })}>{t("previous_version")}<span class="faint ellipsis">· {w.parent_name}</span></button>
            <button class="btn" disabled={busy} title={t("world.undo_tip")} onclick={() => app.act("undo")}>{t("undo_roll")}</button>
          {/if}
        </div>
      </Section>

      <Section id="world.share" title={t("world_share")} closed>
        <div class="commands">
          <button class="btn" title={t("export_file_tip")} onclick={exportFile}>{t("export_file")}</button>
          <button class="btn" disabled={busy} title={t("send_built_tip")} onclick={sendBuilt}>{t("send_built")}</button>
          <button class="btn" disabled={busy} title={t("copy_mod_tip")} onclick={copyMod}>{t("copy_mod")}</button>
          <button class="btn" title={t("save_picture_tip")} onclick={savePreview}>{t("save_picture")}</button>
          <button class="btn" title={w.shown ? t("preview_shown") : t("preview_hidden")} onclick={copyPicture}>{t("copy_picture")}</button>
        </div>
        <div class="commands two">
          <button class="btn" title={w.code} onclick={() => copy(w.code)}>{t("copy_code")}</button>
          <button class="btn" title={w.tag} onclick={() => copy(w.tag)}>{t("copy_tag")}</button>
        </div>
      </Section>

      <div class="end">
        <button class="btn danger" disabled={busy} title={t("delete_tip")} onclick={del}><Icon name="trash" />{t("delete")}…</button>
      </div>
    </div>
    {/key}
  {:else if app.worldTab === "maps"}
    {#if w.atlas && w.revealed}
      <MapLegend />
    {:else}
      <div class="body padded">
        <p class="hint">{w.atlas ? t("covered_maps") : t("no_atlas")}</p>
        {#if w.atlas}
          <div><button class="btn" title={t("reveal_world_tip")} onclick={() => app.call("reveal", { id: w.id })}>{t("reveal_world")}</button></div>
        {/if}
      </div>
    {/if}
  {:else if notes}
    <div class="body notes">
      <label class="field">
        <span class="key">{t("user_tag")}</span>
        <input class="input" maxlength="64" bind:value={notes.tag} onkeydown={saveKey} />
      </label>
      <textarea class="input grow" maxlength="16384" bind:value={notes.notes} placeholder={t("notes_hint")} aria-label={t("tab.notes")} onkeydown={saveKey}></textarea>
      <div class="notes-foot">
        <Check checked={notes.starred} label={t("starred")} onchange={(value) => notes && (notes.starred = value)} />
        <span class="spacer"></span>
        <button class="btn primary" title="Ctrl+S" onclick={() => saveNotes()}>{t("save_notes")}</button>
      </div>
    </div>
  {/if}
{/if}

<style>
  .body {
    flex: 1;
    min-height: 0;
  }
  .padded {
    display: grid;
    align-content: start;
    gap: 10px;
    padding: 12px;
  }
  .identity {
    display: grid;
    gap: 6px;
    padding: 10px 12px 12px;
    border-bottom: 1px solid var(--line);
  }
  .name-row {
    display: flex;
    align-items: center;
    gap: 2px;
    min-width: 0;
    margin-left: -5px;
  }
  .name {
    flex: 1;
    min-width: 0;
    height: 26px;
    padding: 0 4px;
    border: 1px solid transparent;
    border-radius: var(--radius);
    background: transparent;
    color: var(--text);
    font: 600 14px var(--font);
    text-overflow: ellipsis;
    user-select: text;
  }
  .name:hover {
    border-color: var(--line-2);
  }
  .name:focus {
    outline: none;
    border-color: var(--accent);
    background: var(--field);
  }
  .star {
    color: var(--text-3);
  }
  .star.on {
    color: var(--warn);
  }
  .facts {
    display: flex;
    flex-wrap: wrap;
    gap: 2px 10px;
    margin-top: -4px;
    color: var(--text-2);
    font-size: 12px;
  }
  .facts code {
    font-size: 11.5px;
  }
  .placement {
    display: flex;
    align-items: center;
    gap: 4px;
    min-height: 24px;
    margin-top: 2px;
    font-size: 12.5px;
  }
  .state {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    white-space: nowrap;
  }
  .task {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: center;
    gap: 4px 8px;
    font-size: 12px;
  }
  .task.failed {
    color: var(--danger);
  }
  .task .selectable {
    overflow-wrap: anywhere;
  }
  .task .progress {
    grid-column: 1 / -1;
  }
  .cap {
    display: inline-block;
  }
  .cap::first-letter {
    text-transform: uppercase;
  }
  .props > .key.wide {
    margin-top: 4px;
    margin-bottom: -3px;
  }
  .reproduce {
    display: grid;
    justify-items: start;
    gap: 6px;
  }
  .small {
    font-size: 12px;
  }
  hr {
    margin: 2px 0;
    border: 0;
    border-top: 1px solid var(--line);
  }
  .code-row {
    display: flex;
    align-items: center;
    gap: 2px;
  }
  .code-row {
    padding: 2px 2px 2px 7px;
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--field);
  }
  .code-row code {
    flex: 1;
    min-width: 0;
    font-size: 11px;
    color: var(--text-2);
    overflow-wrap: anywhere;
  }
  .ellipsis {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .end {
    padding: 12px;
  }
  .notes {
    display: grid;
    grid-template-rows: auto minmax(120px, 1fr) auto;
    gap: 10px;
    padding: 12px;
  }
  .grow {
    height: 100%;
    resize: none;
  }
  .notes-foot {
    display: flex;
    align-items: center;
    gap: 8px;
  }
</style>
