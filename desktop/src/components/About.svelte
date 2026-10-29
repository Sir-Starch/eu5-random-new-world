<script lang="ts">
  import { app, t } from "../lib/app.svelte";
  import { openUrl } from "../lib/native";
  import Icon from "./Icon.svelte";
  import Modal from "./ui/Modal.svelte";

  const HOME = "https://github.com/Sir-Starch/eu5-random-new-world";
  const LINKS = [
    ["about_homepage", HOME],
    ["about_documentation", `${HOME}/tree/main/docs`],
    ["about_issues", `${HOME}/issues`],
    ["about_changelog", `${HOME}/blob/main/CHANGELOG.md`],
  ];
</script>

<Modal title={t("about_title")} width={580} onclose={() => (app.modal = null)}>
  <div class="about">
    <div class="head">
      <div class="mark" aria-hidden="true">
        <svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="13" /><path d="M6 13c5 1 7-3 11-2s5 5 9 4M5.5 20c4-1 6 2 10 1s6-4 11-2" /></svg>
      </div>
      <div>
        <h2>{app.info?.title} <span class="faint num">{app.info?.version}</span></h2>
        <p class="dim">{t("about_subtitle")}</p>
      </div>
    </div>
    <p>{t("about_description")}</p>
    <dl>
      <dt>{t("about_author")}</dt><dd class="selectable">Sir Starch &lt;starch@sirstarch.com&gt;</dd>
      <dt>{t("about_license")}</dt><dd>Mozilla Public License 2.0 (MPL-2.0)</dd>
    </dl>
    <div class="links">
      {#each LINKS as [key, url] (key)}
        <button class="link" onclick={() => openUrl(url)}><Icon name="external" size={15} /><span>{t(key)}</span><span class="faint mono url">{url.replace("https://", "")}</span></button>
      {/each}
    </div>
    <p class="faint small">{t("about_disclaimer")}</p>
  </div>
</Modal>

<style>
  .about {
    display: grid;
    gap: 16px;
  }
  .head {
    display: flex;
    gap: 14px;
    align-items: center;
  }
  .mark svg {
    width: 52px;
    height: 52px;
    fill: none;
    stroke: var(--accent);
    stroke-width: 1.4;
    stroke-linecap: round;
  }
  .mark circle {
    fill: var(--accent-soft);
  }
  dl {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 6px 16px;
    margin: 0;
  }
  dt {
    color: var(--text-3);
  }
  dd {
    margin: 0;
  }
  .links {
    display: grid;
    gap: 4px;
  }
  .link {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border: 0;
    border-radius: 8px;
    background: var(--bg-2);
    color: var(--text);
    font: 550 13px var(--font);
    cursor: pointer;
    text-align: left;
  }
  .link:hover {
    color: var(--accent);
  }
  .url {
    margin-left: auto;
    font-size: 11px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .small {
    font-size: 12px;
    line-height: 1.5;
  }
</style>
