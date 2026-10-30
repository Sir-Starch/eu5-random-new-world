<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import { openUrl } from "../lib/native";
  import Modal from "./ui/Modal.svelte";

  const HOME = "https://github.com/Sir-Starch/eu5-random-new-world";
  const LINKS = [
    ["about_homepage", HOME],
    ["about_workshop", "https://steamcommunity.com/sharedfiles/filedetails/?id=3829217331"],
    ["about_documentation", `${HOME}/tree/main/docs`],
    ["about_issues", `${HOME}/issues`],
    ["about_changelog", `${HOME}/blob/main/CHANGELOG.md`],
  ];
</script>

<Modal title={t("about_title")} width={520} onclose={() => (app.modal = null)}>
  <div class="about">
    <div>
      <h2>{app.info?.title} <span class="faint num">{app.info?.version}</span></h2>
      <p class="dim">{t("about_subtitle")}</p>
    </div>
    <p>{t("about_description")}</p>
    <dl class="form">
      <dt class="label">{t("about_author")}</dt><dd class="selectable">Sir Starch &lt;starch@sirstarch.com&gt;</dd>
      <dt class="label">{t("about_license")}</dt><dd>Mozilla Public License 2.0 (MPL-2.0)</dd>
      {#each LINKS as [key, url] (key)}
        <dt class="label">{t(key)}</dt>
        <dd><button class="link" title={url} onclick={() => openUrl(url)}>{url.replace("https://", "")}</button></dd>
      {/each}
    </dl>
    <p class="hint">{t("about_disclaimer")}</p>
  </div>
</Modal>

<style>
  .about {
    display: grid;
    gap: 12px;
  }
  dl {
    margin: 0;
    gap: 4px 12px;
  }
  dd {
    margin: 0;
    min-width: 0;
  }
  .link {
    max-width: 100%;
    padding: 0;
    border: 0;
    background: none;
    color: var(--accent-text);
    font: 400 12.5px var(--font);
    text-align: left;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .link:hover {
    text-decoration: underline;
  }
</style>
