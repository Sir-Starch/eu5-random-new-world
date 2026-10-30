<script lang="ts">
  import { app, grouped, t, when, type WorldTab } from "../lib/app.svelte";
  import { copyImage, copyText, openPath, pickFolder, saveFile } from "../lib/native";
  import Icon from "./Icon.svelte";
  import MapViewer from "./MapViewer.svelte";
  import Check from "./ui/Check.svelte";

  const s = $derived(app.now);
  const w = $derived(s?.world);
  const busy = $derived(!!s?.busy);
  let name = $state<string | null>(null);
  let notes = $state<{ id: string; notes: string; tag: string; starred: boolean } | null>(null);
  let banner = $state("");
  let bannerKey = "";
  let layer = $state("countries");

  $effect(() => {
    const world = w;
    if (!world) return;
    const key = `${world.id}|${world.picture}`;
    if (key === bannerKey) return;
    bannerKey = key;
    banner = "";
    void app.call<string>("picture", { id: world.id }).then((url) => {
      if (bannerKey === key) banner = url ?? "";
    });
  });

  $effect(() => {
    const world = w;
    if (world && notes?.id !== world.id) {
      notes = { id: world.id, notes: world.notes, tag: world.user_tag, starred: world.starred };
      name = null;
    }
  });

  const TABS: { key: WorldTab; label: string }[] = [
    { key: "overview", label: "tab.world" },
    { key: "map", label: "tab.maps" },
    { key: "versions", label: "world_versions" },
    { key: "share", label: "world_share" },
    { key: "notes", label: "tab.notes" },
  ];

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

  async function remove(): Promise<void> {
    await app.act("remove_entries", { ids: [w?.id] });
  }

  async function del(): Promise<void> {
    if (!w) return;
    const sure = await app.confirm(t("delete_title"), t("delete_question", { name: w.name }), t("delete"), true);
    if (sure) await app.act("delete_entries", { ids: [w.id] });
  }

  async function exportFile(): Promise<void> {
    if (!w) return;
    const path = await saveFile(t("export_file"), `${w.name.replace(/\s+/g, "-")}.rnworld`, [{ name: "World file", extensions: ["rnworld"] }]);
    if (path) await app.report("export_file", { id: w.id, path }, t("file_saved", { path }));
  }

  async function sendBuilt(): Promise<void> {
    if (!w) return;
    const sure = await app.confirm(t("send_built"), t("send_built_warning"), t("send_built"));
    if (!sure) return;
    const path = await saveFile(t("send_built"), `${w.name.replace(/\s+/g, "-")}.rnworld-mod`, [{ name: "Built world", extensions: ["rnworld-mod"] }]);
    if (path) await app.act("send_built", { id: w.id, path });
  }

  async function copyMod(): Promise<void> {
    if (!w) return;
    const path = await pickFolder(t("copy_mod"));
    if (path) await app.act("copy_mod", { id: w.id, path });
  }

  async function savePreview(): Promise<void> {
    if (!w) return;
    const path = await saveFile(t("save_picture"), `${w.name.replace(/\s+/g, "-")}.png`, [{ name: "PNG", extensions: ["png"] }]);
    if (path) await app.report("save_preview", { id: w.id, path }, t("picture_saved", { path }));
  }

  async function copy(text: string): Promise<void> {
    await copyText(text);
    app.toast("success", t("copied"));
  }

  async function copyPicture(): Promise<void> {
    if (!banner) return;
    await copyImage(banner);
    app.toast("success", t("copied"));
  }

  async function openFolder(): Promise<void> {
    if (!w) return;
    const path = await app.call<string>("folder", { id: w.id });
    if (path) await openPath(path);
  }

  async function reroll(part: string, keepBoth: boolean): Promise<void> {
    await app.act("reroll", { part, keep_both: keepBoth });
  }
  let keepBoth = $state(false);

  function compare(): void {
    if (w?.compare) app.modal = { kind: "compare", layer };
    else app.toast("info", t("compare_need_two"));
  }

  const details = $derived(
    w
      ? [
          ["detail.type", w.type],
          ["detail.seed", w.seed],
          ["detail.custom", w.custom],
          ["detail.made", when(w.created)],
          ["detail.build", w.build],
          ["detail.generator", w.generator],
          ["detail.place", w.place],
        ]
      : [],
  );
</script>

{#if w}
  <div class="page" class:focus={app.mapFocus && app.worldTab === "map"}>
    <header class="head">
      <div class="picture" aria-hidden="true">
        {#if banner}<img src={banner} alt="" draggable="false" />{/if}
      </div>
      <div class="titles">
        <div class="name-row">
          <span class="name-fit" data-value={name ?? w.name}>
          <input
            class="name"
            value={name ?? w.name}
            maxlength={app.info?.name_limit}
            title={t("name_hint", { limit: app.info?.name_limit ?? 40 })}
            aria-label={t("name_hint", { limit: app.info?.name_limit ?? 40 })}
            oninput={(event) => (name = (event.currentTarget as HTMLInputElement).value)}
            onblur={rename}
            onkeydown={(event) => {
              if (event.key === "Enter") (event.currentTarget as HTMLInputElement).blur();
              if (event.key === "Escape") { name = null; (event.currentTarget as HTMLInputElement).blur(); }
            }}
          />
          </span>
          <button class="btn icon small ghost star" class:on={notes?.starred} aria-pressed={!!notes?.starred} title={t("starred")} aria-label={t("starred")} onclick={() => saveNotes(!notes?.starred)}>
            <Icon name="star" fill={!!notes?.starred} />
          </button>
        </div>
        <div class="facts">
          <span>{w.type}{w.part ? ` · ${w.part}` : ""}</span>
          <span class="mono">{w.tag}</span>
          <span class="state">
            <span class="dot" class:ok={w.placement === "in_game"}></span>
            {w.placement === "in_game" ? t("list.in_game") : w.placement === "kept" ? t("list.kept") : t("list.code_only")}
          </span>
          {#if w.user_tag}<span>{w.user_tag}</span>{/if}
        </div>
      </div>
      <div class="actions">
        {#if w.placement === "in_game"}
          <button class="btn" disabled={!!w.remove_problem} title={w.remove_problem ?? t("remove_tip")} onclick={remove}>{t("remove")}</button>
        {:else}
          <button class="btn primary" disabled={!!w.add_problem} title={w.add_problem ?? ""} onclick={() => app.act("add")}>{t("add")}</button>
        {/if}
        <button class="btn icon" title={t("open_folder")} aria-label={t("open_folder")} onclick={openFolder}><Icon name="folder" /></button>
      </div>
    </header>

    {#if w.task && (w.task.running || w.task.line)}
      <div class="task" class:failed={w.task.failed}>
        {#if w.task.running}<span class="spinner"></span>{:else}<Icon name="alert" />{/if}
        <span class="selectable">{w.task.line}</span>
        {#if w.task.bar}<span class="progress task-bar"><span style:width={`${Math.round(w.task.fraction * 100)}%`}></span></span>{/if}
      </div>
    {/if}

    <div class="tabs" role="tablist">
      {#each TABS as tab (tab.key)}
        <button role="tab" aria-selected={app.worldTab === tab.key} class:on={app.worldTab === tab.key} onclick={() => (app.worldTab = tab.key)}>
          {t(tab.label)}
        </button>
      {/each}
    </div>

    <div class="body" class:map={app.worldTab === "map"}>
      {#if app.worldTab === "overview"}
        <div class="scroll fill">
          <div class="sheet">
            {#if w.advice}
              <div class="msg info"><Icon name="info" /><p>{w.advice}</p></div>
            {/if}
            {#if w.note}
              <div class="msg warn"><Icon name="warning" /><p>{w.note}</p></div>
            {/if}

            {#if !w.totals && !w.revealed}
              <div class="msg info">
                <Icon name="info" />
                <p>{t("covered_maps")}</p>
                <button class="btn small" onclick={() => app.call("reveal", { id: w.id })}>{t("reveal_world")}</button>
              </div>
            {/if}

            <section>
              <h3 class="group-title">{t("world_details")}</h3>
              {#if w.totals}
                <dl class="form props totals">
                  <dt class="label cap">{t("stat.countries")}</dt>
                  <dd><span class="num">{grouped(w.totals.countries)}</span> <span class="faint">· {t("stat.split", { states: grouped(w.totals.states), tribes: grouped(w.totals.tribes) })}</span></dd>
                  <dt class="label cap">{t("stat.cultures")}</dt>
                  <dd class="num">{grouped(w.totals.cultures)}</dd>
                  <dt class="label cap">{t("stat.religions")}</dt>
                  <dd class="num">{grouped(w.totals.religions)}</dd>
                  <dt class="label cap">{t("stat.land")}</dt>
                  <dd><span class="num">{grouped(w.totals.land)}</span> <span class="faint">· {t("stat.locations", { count: grouped(w.totals.locations) })}</span></dd>
                </dl>
              {/if}
              <dl class="form props">
                <dt class="label">{t("detail.code")}</dt>
                <dd class="row">
                  <code class="selectable code">{w.code}</code>
                  <button class="btn icon small ghost" title={t("copy_code")} aria-label={t("copy_code")} onclick={() => copy(w.code)}><Icon name="copy" /></button>
                </dd>
                {#each details as [key, value] (key)}
                  <dt class="label">{t(key)}</dt><dd class="selectable">{value}</dd>
                {/each}
                <dt class="label top">{t("detail.reproduce")}</dt>
                <dd class="stack">
                  <span class="selectable">{w.reproduce}</span>
                  <span><button class="btn small" disabled={busy || !w.can_change} title={t("check_tip")} onclick={() => app.act("check")}>{t("check")}</button></span>
                </dd>
              </dl>
            </section>

            <section>
              <h3 class="group-title">{t("visibility")}</h3>
              <Check checked={w.shown} disabled={busy} label={t("show_new_world")} hint={t("world_visibility_hint")} onchange={(value) => app.act("set_visibility", { id: w.id, value })} />
              {#if w.summary && !w.totals}<p class="hint">{w.summary}</p>{/if}
            </section>

            <div class="delete">
              <button class="btn danger" disabled={busy} title={t("delete_tip")} onclick={del}><Icon name="trash" />{t("delete")}…</button>
            </div>
          </div>
        </div>
      {:else if app.worldTab === "map"}
        {#if !w.atlas}
          <div class="empty"><p class="dim">{t("no_atlas")}</p></div>
        {:else if !w.revealed}
          <div class="empty">
            <h2>{t("world.terra_incognita")}</h2>
            <p class="dim">{t("covered_maps")}</p>
            <button class="btn primary" title={t("reveal_world_tip")} onclick={() => app.call("reveal", { id: w.id })}>{t("reveal_world")}</button>
          </div>
        {:else}
          <MapViewer world={w.id} bind:layer onCompare={compare} />
        {/if}
      {:else if app.worldTab === "versions"}
        <div class="scroll fill">
          <div class="sheet">
            <p class="dim">{t("world.versions_intro")}</p>
            <div class="commands">
              <button class="btn" disabled={!w.can_change} onclick={() => reroll("peoples", keepBoth)}>{t("part.peoples.button")}</button>
              <p class="hint">{t("part.peoples.tip")}</p>
              <button class="btn" disabled={!w.can_change} onclick={() => reroll("resources", keepBoth)}>{t("part.resources.button")}</button>
              <p class="hint">{t("part.resources.tip")}</p>
              <button class="btn" disabled={busy} onclick={() => app.call("edit")}>{t("edit_same_land")}</button>
              <p class="hint">{t("edit_same_land_tip")}</p>
              <button class="btn" disabled={busy} onclick={() => app.call("like", { id: w.id })}>{t("like_this")}</button>
              <p class="hint">{t("world.like_tip")}</p>
              {#if w.parent}
                <button class="btn" onclick={() => app.call("select", { id: w.parent })}>{t("previous_version")}</button>
                <p class="hint">{w.parent_name}</p>
                <button class="btn" disabled={busy} onclick={() => app.act("undo")}>{t("undo_roll")}</button>
                <p class="hint">{t("world.undo_tip")}</p>
              {/if}
            </div>
            {#if w.placement === "in_game"}
              <Check checked={keepBoth} label={t("keep_both")} hint={t("keep_both_tip")} onchange={(value) => (keepBoth = value)} />
            {/if}
          </div>
        </div>
      {:else if app.worldTab === "share"}
        <div class="scroll fill">
          <div class="sheet">
            <div class="commands">
              <button class="btn" onclick={exportFile}>{t("export_file")}</button>
              <p class="hint">{t("export_file_tip")}</p>
              <button class="btn" disabled={busy} onclick={sendBuilt}>{t("send_built")}</button>
              <p class="hint">{t("send_built_tip")}</p>
              <button class="btn" disabled={busy} onclick={copyMod}>{t("copy_mod")}</button>
              <p class="hint">{t("copy_mod_tip")}</p>
              <button class="btn" onclick={savePreview}>{t("save_picture")}</button>
              <p class="hint">{t("save_picture_tip")}</p>
              <button class="btn" disabled={!banner} onclick={copyPicture}>{t("copy_picture")}</button>
              <p class="hint">{w.shown ? t("preview_shown") : t("preview_hidden")}</p>
              <button class="btn" onclick={() => copy(w.code)}>{t("copy_code")}</button>
              <p class="hint mono selectable">{w.code}</p>
              <button class="btn" onclick={() => copy(w.tag)}>{t("copy_tag")}</button>
              <p class="hint mono selectable">{w.tag}</p>
            </div>
          </div>
        </div>
      {:else if app.worldTab === "notes" && notes}
        <div class="notes">
          <div class="form">
            <label class="label" for="user-tag">{t("user_tag")}</label>
            <input id="user-tag" class="input" maxlength="64" bind:value={notes.tag} />
          </div>
          <textarea class="input grow" maxlength="16384" bind:value={notes.notes} placeholder={t("notes_hint")} aria-label={t("tab.notes")}
            onkeydown={(event) => { if ((event.ctrlKey || event.metaKey) && event.key === "s") { event.preventDefault(); void saveNotes(); } }}></textarea>
          <div class="notes-actions">
            <Check checked={notes.starred} label={t("starred")} onchange={(value) => notes && (notes.starred = value)} />
            <button class="btn primary" title="Ctrl+S" onclick={() => saveNotes()}>{t("save_notes")}</button>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .page {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
  }
  .head {
    flex: none;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: var(--panel);
  }
  .picture {
    flex: none;
    width: 88px;
    height: 44px;
    border-radius: 2px;
    overflow: hidden;
    background: var(--field);
    box-shadow: inset 0 0 0 1px var(--line);
  }
  .picture img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .focus .picture,
  .focus .facts {
    display: none;
  }
  .titles {
    flex: 1;
    min-width: 0;
    display: grid;
    gap: 2px;
  }
  .name-row {
    display: flex;
    align-items: center;
    gap: 2px;
    min-width: 0;
  }
  /* The name's field is as wide as the name: an invisible copy of it sizes the cell. */
  .name-fit {
    display: inline-grid;
    min-width: 0;
    max-width: 100%;
    margin-left: -5px;
  }
  .name-fit::after {
    content: attr(data-value) " ";
    grid-area: 1 / 1;
    visibility: hidden;
    white-space: pre;
    overflow: hidden;
    padding: 0 5px;
    font: 600 15px var(--font);
  }
  .name {
    grid-area: 1 / 1;
    width: 100%;
    min-width: 60px;
    height: 26px;
    padding: 0 4px;
    border: 1px solid transparent;
    border-radius: var(--radius);
    background: transparent;
    color: var(--text);
    font: 600 15px var(--font);
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
    align-items: center;
    gap: 2px 12px;
    font-size: 12px;
    color: var(--text-2);
    min-width: 0;
  }
  .facts .mono {
    font-size: 11.5px;
  }
  .state {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .actions {
    flex: none;
    display: flex;
    gap: 4px;
  }
  .task {
    flex: none;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 12px;
    border-top: 1px solid var(--line);
    background: var(--panel);
    font-size: 12px;
  }
  .task.failed {
    color: var(--danger);
  }
  .task span.selectable {
    flex: 1;
    overflow-wrap: anywhere;
  }
  .task-bar {
    flex: none;
    width: 140px;
  }
  .tabs {
    flex: none;
    display: flex;
    gap: 0;
    padding: 0 8px;
    background: var(--panel);
    border-bottom: 1px solid var(--line);
    overflow-x: auto;
    scrollbar-width: none;
  }
  .tabs button {
    height: 28px;
    padding: 0 10px;
    border: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: var(--text-2);
    font: 400 12.5px var(--font);
    white-space: nowrap;
  }
  .tabs button:hover {
    color: var(--text);
  }
  .tabs button.on {
    color: var(--text);
    border-bottom-color: var(--accent);
    font-weight: 500;
  }
  .body {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .fill {
    flex: 1;
    min-height: 0;
  }
  .sheet {
    display: grid;
    gap: 14px;
    max-width: 820px;
    padding: 12px 16px 20px;
  }
  section {
    display: grid;
    gap: 8px;
  }
  .props {
    margin: 0;
    gap: 4px 12px;
    align-items: baseline;
  }
  .props dd {
    margin: 0;
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .totals {
    padding-bottom: 8px;
    border-bottom: 1px solid var(--line);
  }
  .cap::first-letter {
    text-transform: uppercase;
  }
  .code {
    font-size: 11.5px;
    color: var(--text-2);
    overflow-wrap: anywhere;
  }
  .stack {
    display: grid;
    gap: 4px;
    justify-items: start;
  }
  .delete {
    padding-top: 10px;
    border-top: 1px solid var(--line);
  }
  .empty {
    flex: 1;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: 10px;
    padding: 32px;
    text-align: center;
    max-width: 520px;
    margin: 0 auto;
  }
  .commands {
    display: grid;
    grid-template-columns: minmax(0, max-content) minmax(0, 1fr);
    align-items: center;
    gap: 6px 12px;
  }
  .commands .btn {
    justify-content: flex-start;
    max-width: 260px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .commands .hint {
    overflow-wrap: anywhere;
  }
  .notes {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-rows: auto minmax(120px, 1fr) auto;
    gap: 8px;
    padding: 12px 16px;
    max-width: 780px;
    width: 100%;
  }
  .grow {
    height: 100%;
    resize: none;
  }
  .notes-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }
</style>
