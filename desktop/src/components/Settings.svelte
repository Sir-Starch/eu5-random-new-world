<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import { pickFolder, saveFile } from "../lib/native";
  import { theme, setTheme, type ThemeChoice } from "../lib/theme.svelte";
  import Icon from "./Icon.svelte";
  import Modal from "./ui/Modal.svelte";
  import Segmented from "./ui/Segmented.svelte";
  import Toggle from "./ui/Toggle.svelte";

  const s = $derived(app.now);

  async function browse(kind: "game" | "profile"): Promise<void> {
    const path = await pickFolder(t(kind));
    if (path) await app.act(kind === "game" ? "choose_game" : "choose_profile", { path });
  }

  async function diagnostics(): Promise<void> {
    const name = (await app.call<string>("diagnostics_name")) ?? "rnw-diagnostics.zip";
    const path = await saveFile(t("diagnostics_title"), name, [{ name: "Zip", extensions: ["zip"] }]);
    if (!path) return;
    const problem = await app.call<string | null>("save_diagnostics", { path });
    if (problem) app.toast("warning", problem);
    else app.toast("success", t("diagnostics_saved", { path }));
  }

  const gameLanguage = $derived(
    app.info?.languages.find((item) => item.key === app.info?.language)?.name ?? "",
  );
</script>

<Modal title={t("settings_title")} width={640} onclose={() => (app.modal = null)}>
  <div class="settings">
    <section>
      <h3>{t("game")}</h3>
      <div class="pick">
        <select class="input" value={String(Math.max(0, s?.games.indexOf(s.game.directory) ?? 0))}
          onchange={(event) => app.call("pick_game", { index: Number((event.currentTarget as HTMLSelectElement).value) })}>
          {#each s?.games ?? [] as path, index (path)}<option value={String(index)}>{path}</option>{/each}
          {#if !s?.games.length}<option value="0">—</option>{/if}
        </select>
        <button class="btn" onclick={() => browse("game")}><Icon name="folder" size={16} />{t("browse")}</button>
      </div>
      {#if s?.game.build}<p class="faint small">{s.game.status}</p>{/if}
    </section>
    <section>
      <h3>{t("profile")}</h3>
      <div class="pick">
        <select class="input" value={String(Math.max(0, s?.profiles.indexOf(s.game.profile) ?? 0))}
          onchange={(event) => app.call("pick_profile", { index: Number((event.currentTarget as HTMLSelectElement).value) })}>
          {#each s?.profiles ?? [] as path, index (path)}<option value={String(index)}>{path}</option>{/each}
          {#if !s?.profiles.length}<option value="0">—</option>{/if}
        </select>
        <button class="btn" onclick={() => browse("profile")}><Icon name="folder" size={16} />{t("browse")}</button>
      </div>
      {#if s?.game.problem}<div class="callout warn"><Icon name="warning" /><p>{s.game.problem}</p></div>{/if}
    </section>
    <div class="two">
      <section>
        <h3>{t("language")}</h3>
        <select class="input" value={s?.preferences.language ?? ""}
          onchange={(event) => app.setLanguage((event.currentTarget as HTMLSelectElement).value)}>
          <option value="">{t("language.game", { language: gameLanguage })}</option>
          {#each app.info?.languages ?? [] as item (item.key)}<option value={item.key}>{item.name}</option>{/each}
        </select>
      </section>
      <section>
        <h3>{t("settings.theme")}</h3>
        <Segmented
          label={t("settings.theme")}
          value={theme.choice}
          options={[
            { value: "system", label: t("settings.theme.system") },
            { value: "dark", label: t("settings.theme.dark") },
            { value: "light", label: t("settings.theme.light") },
          ]}
          onchange={(value) => setTheme(value as ThemeChoice)}
        />
      </section>
    </div>
    <section>
      <Toggle checked={!!s?.preferences.show_new_world} label={t("show_new_world")} hint={t("show_new_world_hint")}
        onchange={(value) => app.call("set_show_new_world", { value })} />
    </section>
    <p class="faint small">{t("about_generator")}</p>
  </div>
  {#snippet footer()}
    <button class="btn ghost" title={t("diagnostics_tip")} onclick={diagnostics}><Icon name="download" size={16} />{t("diagnostics")}</button>
    <button class="btn ghost" onclick={() => (app.modal = { kind: "about" })}><Icon name="info" size={16} />{t("about")}</button>
    <span class="spacer"></span>
    <button class="btn primary" onclick={() => (app.modal = null)}>{t("close")}</button>
  {/snippet}
</Modal>

<style>
  .settings {
    display: grid;
    gap: 22px;
  }
  section {
    display: grid;
    gap: 8px;
  }
  .pick {
    display: flex;
    gap: 8px;
  }
  .pick select {
    flex: 1;
    min-width: 0;
    text-overflow: ellipsis;
  }
  .two {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 18px;
  }
  .small {
    font-size: 12.5px;
    line-height: 1.5;
  }
  .spacer {
    flex: 1;
  }
</style>
