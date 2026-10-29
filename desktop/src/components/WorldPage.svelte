<script lang="ts">
  import { app, grouped, t, when, type WorldTab } from "../lib/app.svelte";
  import { copyImage, copyText, openPath, pickFolder, saveFile } from "../lib/native";
  import Icon from "./Icon.svelte";
  import MapViewer from "./MapViewer.svelte";
  import Toggle from "./ui/Toggle.svelte";

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

  const TABS: { key: WorldTab; icon: string; label: string }[] = [
    { key: "overview", icon: "globe", label: "tab.world" },
    { key: "map", icon: "map", label: "tab.maps" },
    { key: "versions", icon: "branch", label: "world_versions" },
    { key: "share", icon: "share", label: "world_share" },
    { key: "notes", icon: "notes", label: "tab.notes" },
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
  <div class="page" class:focus={app.mapFocus && app.worldTab === "map"} class:compact={app.worldTab === "map"}>
    <header class="hero">
      <div class="banner" style:background-image={banner ? `url(${banner})` : undefined}></div>
      <div class="shade"></div>
      <div class="hero-body">
        <div class="titles">
          <span class="eyebrow">{w.type}{w.part ? ` · ${w.part}` : ""} · <span class="mono">{w.tag}</span></span>
          <div class="name-row">
            <input
              class="name"
              value={name ?? w.name}
              maxlength={app.info?.name_limit}
              placeholder={t("name_hint", { limit: app.info?.name_limit ?? 40 })}
              aria-label={t("name_hint", { limit: app.info?.name_limit ?? 40 })}
              oninput={(event) => (name = (event.currentTarget as HTMLInputElement).value)}
              onblur={rename}
              onkeydown={(event) => {
                if (event.key === "Enter") (event.currentTarget as HTMLInputElement).blur();
                if (event.key === "Escape") { name = null; (event.currentTarget as HTMLInputElement).blur(); }
              }}
            />
            <button class="star" class:on={notes?.starred} aria-pressed={!!notes?.starred} title={t("starred")} onclick={() => saveNotes(!notes?.starred)}>
              <Icon name="star" size={20} fill={!!notes?.starred} />
            </button>
          </div>
          <div class="badges">
            {#if w.placement === "in_game"}
              <span class="badge ok"><span class="dot"></span>{t("list.in_game")}</span>
            {:else if w.placement === "kept"}
              <span class="badge">{t("list.kept")}</span>
            {:else}
              <span class="badge">{t("list.code_only")}</span>
            {/if}
            <span class="badge">{#if w.shown}<Icon name="eye" size={13} />{t("preview_shown")}{:else}<Icon name="eyeOff" size={13} />{t("preview_hidden")}{/if}</span>
            {#if w.user_tag}<span class="badge accent"><Icon name="tag" size={12} />{w.user_tag}</span>{/if}
          </div>
        </div>
        <div class="actions">
          {#if w.placement === "in_game"}
            <button class="btn" disabled={!!w.remove_problem} title={w.remove_problem ?? t("remove_tip")} onclick={remove}><Icon name="eyeOff" size={16} />{t("remove")}</button>
          {:else}
            <button class="btn primary" disabled={!!w.add_problem} title={w.add_problem ?? ""} onclick={() => app.act("add")}><Icon name="play" size={15} />{t("add")}</button>
          {/if}
          <button class="btn icon" title={t("open_folder")} aria-label={t("open_folder")} onclick={openFolder}><Icon name="folder" /></button>
        </div>
      </div>
      {#if w.task && (w.task.running || w.task.line)}
        <div class="task" class:failed={w.task.failed}>
          {#if w.task.running}<span class="spinner"></span>{:else}<Icon name="alert" size={16} />{/if}
          <span class="selectable">{w.task.line}</span>
          {#if w.task.bar}<span class="task-bar"><span style:width={`${Math.round(w.task.fraction * 100)}%`}></span></span>{/if}
        </div>
      {/if}
    </header>

    <div class="tabs" role="tablist">
      {#each TABS as tab (tab.key)}
        <button role="tab" aria-selected={app.worldTab === tab.key} class:on={app.worldTab === tab.key} onclick={() => (app.worldTab = tab.key)}>
          <Icon name={tab.icon} size={16} />{t(tab.label)}
        </button>
      {/each}
    </div>

    <div class="body" class:map={app.worldTab === "map"}>
      {#if app.worldTab === "overview"}
        <div class="overview scroll">
          {#if w.totals}
            <div class="stats">
              <div class="stat"><Icon name="crown" /><strong class="num">{grouped(w.totals.countries)}</strong><span>{t("stat.countries")}</span><small class="faint">{t("stat.split", { states: grouped(w.totals.states), tribes: grouped(w.totals.tribes) })}</small></div>
              <div class="stat"><Icon name="people" /><strong class="num">{grouped(w.totals.cultures)}</strong><span>{t("stat.cultures")}</span></div>
              <div class="stat"><Icon name="flame" /><strong class="num">{grouped(w.totals.religions)}</strong><span>{t("stat.religions")}</span></div>
              <div class="stat"><Icon name="location" /><strong class="num">{grouped(w.totals.land)}</strong><span>{t("stat.land")}</span><small class="faint">{t("stat.locations", { count: grouped(w.totals.locations) })}</small></div>
            </div>
          {:else if !w.revealed}
            <div class="callout accent reveal">
              <Icon name="eyeOff" />
              <div><p>{t("covered_maps")}</p><button class="btn small" onclick={() => app.call("reveal", { id: w.id })}><Icon name="eye" size={14} />{t("reveal_world")}</button></div>
            </div>
          {/if}

          {#if w.advice}
            <div class="callout accent"><Icon name="game" /><p>{w.advice}</p></div>
          {/if}
          {#if w.note}
            <div class="callout warn"><Icon name="warning" /><p>{w.note}</p></div>
          {/if}

          <div class="columns">
            <section class="card padded">
              <h3>{t("world_details")}</h3>
              <dl class="details">
                <dt>{t("detail.code")}</dt>
                <dd class="code-row"><code class="selectable">{w.code}</code><button class="btn icon small ghost" title={t("copy_code")} aria-label={t("copy_code")} onclick={() => copy(w.code)}><Icon name="copy" size={14} /></button></dd>
                {#each details as [key, value] (key)}
                  <dt>{t(key)}</dt><dd class="selectable">{value}</dd>
                {/each}
                <dt>{t("detail.reproduce")}</dt>
                <dd>
                  <span class="selectable">{w.reproduce}</span>
                  <button class="btn small check" disabled={busy || !w.can_change} title={t("check_tip")} onclick={() => app.act("check")}><Icon name="refresh" size={14} />{t("check")}</button>
                </dd>
              </dl>
            </section>
            <section class="card padded side-card">
              <h3>{t("visibility")}</h3>
              <Toggle checked={w.shown} disabled={busy} label={t("show_new_world")} hint={t("world_visibility_hint")} onchange={(value) => app.act("set_visibility", { id: w.id, value })} />
              {#if w.summary}<p class="faint small">{w.summary}</p>{/if}
              <div class="danger-zone">
                <span class="eyebrow">{t("world.danger")}</span>
                <button class="btn danger small" disabled={busy} onclick={del}><Icon name="trash" size={14} />{t("delete")}</button>
              </div>
            </section>
          </div>
        </div>
      {:else if app.worldTab === "map"}
        {#if !w.atlas}
          <div class="empty"><Icon name="map" size={32} /><p>{t("no_atlas")}</p></div>
        {:else if !w.revealed}
          <div class="empty">
            <div class="covered-art" aria-hidden="true"><Icon name="eyeOff" size={34} /></div>
            <h2>{t("world.terra_incognita")}</h2>
            <p class="dim">{t("covered_maps")}</p>
            <button class="btn primary" title={t("reveal_world_tip")} onclick={() => app.call("reveal", { id: w.id })}><Icon name="eye" size={16} />{t("reveal_world")}</button>
          </div>
        {:else}
          <MapViewer world={w.id} bind:layer onCompare={compare} />
        {/if}
      {:else if app.worldTab === "versions"}
        <div class="grid-page scroll">
          <p class="dim intro">{t("world.versions_intro")}</p>
          <div class="action-grid">
            <button class="action" disabled={!w.can_change} onclick={() => reroll("peoples", keepBoth)}>
              <Icon name="people" /><strong>{t("part.peoples.button")}</strong><span>{t("part.peoples.tip")}</span>
            </button>
            <button class="action" disabled={!w.can_change} onclick={() => reroll("resources", keepBoth)}>
              <Icon name="sparkles" /><strong>{t("part.resources.button")}</strong><span>{t("part.resources.tip")}</span>
            </button>
            <button class="action" disabled={busy} onclick={() => app.call("edit")}>
              <Icon name="sliders" /><strong>{t("edit_same_land")}</strong><span>{t("edit_same_land_tip")}</span>
            </button>
            <button class="action" disabled={busy} onclick={() => app.call("like", { id: w.id })}>
              <Icon name="dice" /><strong>{t("like_this")}</strong><span>{t("world.like_tip")}</span>
            </button>
            {#if w.parent}
              <button class="action" onclick={() => app.call("select", { id: w.parent })}>
                <Icon name="branch" /><strong>{t("previous_version")}</strong><span>{w.parent_name}</span>
              </button>
              <button class="action" disabled={busy} onclick={() => app.act("undo")}>
                <Icon name="undo" /><strong>{t("undo_roll")}</strong><span>{t("world.undo_tip")}</span>
              </button>
            {/if}
          </div>
          {#if w.placement === "in_game"}
            <div class="card padded keep">
              <Toggle checked={keepBoth} label={t("keep_both")} hint={t("keep_both_tip")} onchange={(value) => (keepBoth = value)} />
            </div>
          {/if}
        </div>
      {:else if app.worldTab === "share"}
        <div class="grid-page scroll">
          <div class="action-grid">
            <button class="action" onclick={exportFile}><Icon name="file" /><strong>{t("export_file")}</strong><span>{t("export_file_tip")}</span></button>
            <button class="action" disabled={busy} onclick={sendBuilt}><Icon name="upload" /><strong>{t("send_built")}</strong><span>{t("send_built_tip")}</span></button>
            <button class="action" disabled={busy} onclick={copyMod}><Icon name="folder" /><strong>{t("copy_mod")}</strong><span>{t("copy_mod_tip")}</span></button>
            <button class="action" onclick={savePreview}><Icon name="image" /><strong>{t("save_picture")}</strong><span>{t("save_picture_tip")}</span></button>
            <button class="action" onclick={() => copy(w.code)}><Icon name="copy" /><strong>{t("copy_code")}</strong><span class="mono">{w.code}</span></button>
            <button class="action" onclick={() => copy(w.tag)}><Icon name="tag" /><strong>{t("copy_tag")}</strong><span class="mono">{w.tag}</span></button>
            <button class="action" disabled={!banner} onclick={copyPicture}><Icon name="camera" /><strong>{t("copy_picture")}</strong><span>{w.shown ? t("preview_shown") : t("preview_hidden")}</span></button>
          </div>
        </div>
      {:else if app.worldTab === "notes" && notes}
        <div class="notes scroll">
          <label class="field">
            <span class="field-label">{t("user_tag")}</span>
            <input class="input" maxlength="64" bind:value={notes.tag} placeholder={t("user_tag")} />
          </label>
          <label class="field grow">
            <span class="field-label">{t("tab.notes")}</span>
            <textarea class="input" maxlength="16384" bind:value={notes.notes} placeholder={t("notes_hint")}
              onkeydown={(event) => { if ((event.ctrlKey || event.metaKey) && event.key === "s") { event.preventDefault(); void saveNotes(); } }}></textarea>
          </label>
          <div class="notes-actions">
            <Toggle checked={notes.starred} label={t("starred")} onchange={(value) => notes && (notes.starred = value)} />
            <button class="btn primary" onclick={() => saveNotes()}><Icon name="check" size={16} />{t("save_notes")}</button>
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
  .hero {
    position: relative;
    flex: none;
    min-height: 190px;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    overflow: hidden;
    border-bottom: 1px solid var(--line);
    transition: min-height 240ms var(--ease);
  }
  .focus .hero {
    min-height: 0;
  }
  .compact .hero {
    min-height: 112px;
  }
  .compact .hero-body {
    padding-top: 14px;
    padding-bottom: 12px;
  }
  .compact .name {
    font-size: 26px;
  }
  .focus .hero .banner,
  .focus .hero .shade {
    opacity: 0;
  }
  .focus .titles .badges,
  .focus .eyebrow {
    display: none;
  }
  .banner {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center 40%;
    transform: scale(1.04);
    filter: saturate(1.05);
    transition: opacity 300ms var(--ease);
  }
  .shade {
    position: absolute;
    inset: 0;
    background:
      linear-gradient(180deg, transparent 0%, color-mix(in srgb, var(--bg) 55%, transparent) 45%, var(--bg) 100%),
      linear-gradient(90deg, color-mix(in srgb, var(--bg) 70%, transparent), transparent 70%);
  }
  .hero-body {
    position: relative;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 20px;
    padding: 22px 32px 16px;
    flex-wrap: wrap;
  }
  .focus .hero-body {
    padding: 12px 24px;
  }
  .titles {
    display: grid;
    gap: 6px;
    min-width: 0;
    flex: 1;
  }
  .name-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .name {
    flex: 1;
    min-width: 0;
    max-width: 640px;
    padding: 2px 8px;
    margin-left: -8px;
    border: 1px solid transparent;
    border-radius: 10px;
    background: transparent;
    color: var(--text);
    font: 560 34px/1.15 var(--display);
    letter-spacing: -0.01em;
    text-shadow: 0 2px 12px rgba(0, 0, 0, 0.35);
    user-select: text;
  }
  .focus .name {
    font-size: 22px;
  }
  .name:hover {
    border-color: var(--line-2);
  }
  .name:focus {
    outline: none;
    border-color: var(--accent-line);
    background: color-mix(in srgb, var(--bg) 60%, transparent);
  }
  .star {
    display: grid;
    place-items: center;
    width: 38px;
    height: 38px;
    border-radius: 10px;
    border: 0;
    background: transparent;
    color: var(--text-3);
    cursor: pointer;
  }
  .star:hover {
    color: var(--text);
    background: var(--hover);
  }
  .star.on {
    color: var(--accent);
  }
  .badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .actions {
    display: flex;
    gap: 8px;
  }
  .task {
    position: relative;
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 32px 14px;
    padding: 9px 12px;
    border-radius: 10px;
    background: var(--panel);
    border: 1px solid var(--accent-line);
    font-size: 13px;
  }
  .task.failed {
    border-color: color-mix(in srgb, var(--danger) 40%, transparent);
    color: var(--danger);
  }
  .task span.selectable {
    flex: 1;
    overflow-wrap: anywhere;
  }
  .task-bar {
    flex: none;
    width: 160px;
    height: 6px;
    border-radius: 999px;
    background: var(--panel-3);
    overflow: hidden;
  }
  .task-bar span {
    display: block;
    height: 100%;
    background: var(--accent);
    transition: width 300ms var(--ease);
  }
  .spinner {
    flex: none;
    width: 15px;
    height: 15px;
    border-radius: 50%;
    border: 2px solid var(--line-2);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
  }
  .tabs {
    flex: none;
    display: flex;
    gap: 4px;
    padding: 0 26px;
    border-bottom: 1px solid var(--line);
    background: var(--bg);
    overflow-x: auto;
  }
  .tabs button {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    height: 42px;
    padding: 0 12px;
    border: 0;
    border-bottom: 2px solid transparent;
    background: transparent;
    color: var(--text-3);
    font: 600 13px var(--font);
    cursor: pointer;
    white-space: nowrap;
  }
  .tabs button:hover {
    color: var(--text);
  }
  .tabs button.on {
    color: var(--text);
    border-bottom-color: var(--accent);
  }
  .body {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .overview,
  .grid-page,
  .notes {
    flex: 1;
    min-height: 0;
    padding: 24px 32px 40px;
    display: grid;
    gap: 16px;
    align-content: start;
  }
  .stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }
  .stat {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto auto;
    column-gap: 12px;
    padding: 16px 18px;
    border-radius: var(--radius-lg);
    background: var(--panel);
    border: 1px solid var(--line);
  }
  .stat :global(svg) {
    grid-row: 1 / 4;
    color: var(--accent);
    width: 22px;
    height: 22px;
    margin-top: 4px;
  }
  .stat strong {
    font-family: var(--display);
    font-size: 28px;
    font-weight: 560;
    line-height: 1.1;
  }
  .stat span {
    color: var(--text-2);
    font-size: 12.5px;
    font-weight: 550;
  }
  .stat small {
    font-size: 11.5px;
  }
  .reveal div {
    display: grid;
    gap: 10px;
  }
  .reveal .btn {
    justify-self: start;
  }
  .columns {
    display: grid;
    grid-template-columns: minmax(0, 1.6fr) minmax(260px, 1fr);
    gap: 16px;
    align-items: start;
  }
  .padded {
    padding: 18px 20px;
  }
  .side-card {
    display: grid;
    gap: 14px;
  }
  .small {
    font-size: 12.5px;
    line-height: 1.5;
  }
  .details {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 9px 18px;
    margin: 14px 0 0;
    font-size: 13px;
  }
  .details dt {
    color: var(--text-3);
  }
  .details dd {
    margin: 0;
    min-width: 0;
    overflow-wrap: anywhere;
  }
  .code-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .code-row code {
    font-size: 11.5px;
    color: var(--text-2);
    overflow-wrap: anywhere;
  }
  .check {
    display: flex;
    margin-top: 8px;
  }
  .danger-zone {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    padding-top: 14px;
    border-top: 1px solid var(--line);
  }
  .empty {
    flex: 1;
    display: grid;
    place-content: center;
    justify-items: center;
    gap: 14px;
    padding: 40px;
    text-align: center;
    max-width: 560px;
    margin: 0 auto;
  }
  .covered-art {
    display: grid;
    place-items: center;
    width: 84px;
    height: 84px;
    border-radius: 50%;
    background: radial-gradient(circle, var(--accent-soft), transparent 70%);
    color: var(--accent);
    border: 1px solid var(--accent-line);
  }
  .intro {
    max-width: 720px;
  }
  .action-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
  }
  .action {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto 1fr;
    column-gap: 14px;
    row-gap: 4px;
    padding: 16px 18px;
    border-radius: var(--radius-lg);
    border: 1px solid var(--line);
    background: var(--panel);
    color: var(--text);
    text-align: left;
    font: inherit;
    cursor: pointer;
    transition: all var(--speed) var(--ease);
  }
  .action:hover:not(:disabled) {
    border-color: var(--accent-line);
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
  }
  .action:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }
  .action :global(svg) {
    grid-row: 1 / 3;
    color: var(--accent);
    margin-top: 2px;
  }
  .action strong {
    font-weight: 620;
  }
  .action span {
    color: var(--text-3);
    font-size: 12.5px;
    line-height: 1.45;
    overflow-wrap: anywhere;
  }
  .keep {
    max-width: 720px;
  }
  .notes {
    grid-template-rows: auto 1fr auto;
    align-content: stretch;
  }
  .field {
    display: grid;
    gap: 6px;
  }
  .field.grow {
    grid-template-rows: auto 1fr;
    min-height: 220px;
  }
  .field.grow textarea {
    height: 100%;
    min-height: 200px;
  }
  .field-label {
    font-size: 12.5px;
    font-weight: 600;
    color: var(--text-2);
  }
  .notes-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
  }
  @media (max-width: 1100px) {
    .stats {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .columns {
      grid-template-columns: 1fr;
    }
  }
</style>
