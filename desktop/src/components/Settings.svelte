<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import { pickFolder, saveFile } from "../lib/native";
  import { theme, setTheme, type ThemeChoice } from "../lib/theme.svelte";
  import Modal from "./ui/Modal.svelte";
  import Check from "./ui/Check.svelte";

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

<Modal title={t("settings_title")} width={600} onclose={() => (app.modal = null)}>
  <div class="form">
    <label class="label" for="game">{t("game")}</label>
    <div class="row">
      <select id="game" class="input" value={String(Math.max(0, s?.games.indexOf(s.game.directory) ?? 0))}
        onchange={(event) => app.call("pick_game", { index: Number((event.currentTarget as HTMLSelectElement).value) })}>
        {#each s?.games ?? [] as path, index (path)}<option value={String(index)}>{path}</option>{/each}
        {#if !s?.games.length}<option value="0">—</option>{/if}
      </select>
      <button class="btn" onclick={() => browse("game")}>{t("browse")}</button>
    </div>
    {#if s?.game.build}<p class="span hint">{s.game.status}</p>{/if}

    <label class="label" for="profile">{t("profile")}</label>
    <div class="row">
      <select id="profile" class="input" value={String(Math.max(0, s?.profiles.indexOf(s.game.profile) ?? 0))}
        onchange={(event) => app.call("pick_profile", { index: Number((event.currentTarget as HTMLSelectElement).value) })}>
        {#each s?.profiles ?? [] as path, index (path)}<option value={String(index)}>{path}</option>{/each}
        {#if !s?.profiles.length}<option value="0">—</option>{/if}
      </select>
      <button class="btn" onclick={() => browse("profile")}>{t("browse")}</button>
    </div>
    {#if s?.game.problem}<div class="span msg warn"><p>{s.game.problem}</p></div>{/if}

    <label class="label" for="language">{t("language")}</label>
    <select id="language" class="input" value={s?.preferences.language ?? ""}
      onchange={(event) => app.setLanguage((event.currentTarget as HTMLSelectElement).value)}>
      <option value="">{t("language.game", { language: gameLanguage })}</option>
      {#each app.info?.languages ?? [] as item (item.key)}<option value={item.key}>{item.name}</option>{/each}
    </select>

    <label class="label" for="theme">{t("settings.theme")}</label>
    <select id="theme" class="input" value={theme.choice} onchange={(event) => setTheme((event.currentTarget as HTMLSelectElement).value as ThemeChoice)}>
      <option value="system">{t("settings.theme.system")}</option>
      <option value="dark">{t("settings.theme.dark")}</option>
      <option value="light">{t("settings.theme.light")}</option>
    </select>

    <div class="span spaced">
      <Check checked={!!s?.preferences.show_new_world} label={t("show_new_world")} hint={t("show_new_world_hint")}
        onchange={(value) => app.call("set_show_new_world", { value })} />
    </div>
    <div class="span">
      <Check checked={s?.preferences.window === "classic"} label={t("settings.classic_window")} hint={t("settings.classic_window.about")}
        onchange={(value) => app.call("set_window", { classic: value })} />
    </div>
    <p class="full hint about">{t("about_generator")}</p>
  </div>
  {#snippet footer()}
    <button class="btn" title={t("diagnostics_tip")} onclick={diagnostics}>{t("diagnostics")}</button>
    <button class="btn" onclick={() => (app.modal = { kind: "about" })}>{t("about")}</button>
    <span class="spacer"></span>
    <button class="btn primary" onclick={() => (app.modal = null)}>{t("close")}</button>
  {/snippet}
</Modal>

<style>
  .form {
    grid-template-columns: minmax(90px, 140px) minmax(0, 1fr);
  }
  .spaced {
    padding-top: 6px;
  }
  .about {
    padding-top: 8px;
    border-top: 1px solid var(--line);
  }
  .spacer {
    flex: 1;
  }
</style>
