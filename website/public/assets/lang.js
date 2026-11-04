// The root page: open the guide in the visitor's language, keeping any #section.
(() => {
  const slugs = JSON.parse(document.currentScript.dataset.slugs);
  const known = new Set(Object.values(slugs));
  let chosen = null;
  try {
    chosen = localStorage.getItem("rnw.lang");
  } catch {
    // storage refused
  }
  if (!known.has(chosen)) {
    chosen = null;
    for (const tag of navigator.languages || [navigator.language || "en"]) {
      const base = String(tag).toLowerCase().split("-")[0];
      if (slugs[base]) {
        chosen = slugs[base];
        break;
      }
    }
  }
  location.replace(`/${chosen || "en"}/${location.hash}`);
})();
