// Random New World · player's guide: small conveniences; the page works without them.
(() => {
  for (const link of document.querySelectorAll("[data-lang]")) {
    link.addEventListener("click", () => {
      try {
        localStorage.setItem("rnw.lang", link.dataset.lang);
      } catch {
        // storage refused: the root page falls back to the browser's language
      }
    });
  }

  const menu = document.querySelector("details.lang");
  if (menu) {
    document.addEventListener("click", (event) => {
      if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && menu.open) {
        menu.open = false;
        menu.querySelector("summary").focus();
      }
    });
  }

  // An answer named in the address opens by itself (rnw.sirstarch.com/en/#help-memory).
  const openNamed = () => {
    const target = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target instanceof HTMLDetailsElement) target.open = true;
  };
  openNamed();
  window.addEventListener("hashchange", openNamed);

  // The contents follow the reader.
  const links = new Map([...document.querySelectorAll(".toc a")].map((a) => [a.hash.slice(1), a]));
  if (!("IntersectionObserver" in window) || links.size === 0) return;
  const visible = new Set();
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) visible.add(entry.target.id);
        else visible.delete(entry.target.id);
      }
      const first = [...links.keys()].find((id) => visible.has(id));
      if (!first) return;
      for (const [id, a] of links) {
        if (id === first) a.setAttribute("aria-current", "true");
        else a.removeAttribute("aria-current");
      }
    },
    { rootMargin: "-30% 0px -60% 0px" },
  );
  for (const id of links.keys()) {
    const section = document.getElementById(id);
    if (section) observer.observe(section);
  }
})();
