// A themed drop-down for the native <select>. The list a web view opens for a <select> is the
// platform's own widget (white, system-blue selection in WebKitGTK) and no CSS reaches it, so
// in a theme that dresses the window (Terra Incognita) the click is taken over and the same
// options are listed in a menu of the window's own. The <select> stays the single source of
// truth: choosing an item sets it and fires `input` and `change`, so bindings and handlers
// written for the native control work unchanged. Keyboard use (arrows on a focused select)
// is left to the browser; Space, Enter and Alt+Down open the menu.

const THEMES = new Set(["incognita"]);

interface Item {
  option: HTMLOptionElement | null; // null: a group label
  label: string;
  node: HTMLElement;
}

let open: { select: HTMLSelectElement; menu: HTMLElement; items: Item[]; active: number; close: () => void } | null = null;

function themed(): boolean {
  return THEMES.has(document.documentElement.dataset.theme ?? "");
}

function closeMenu(): void {
  open?.close();
}

function build(select: HTMLSelectElement): Item[] {
  const items: Item[] = [];
  const add = (option: HTMLOptionElement, grouped: boolean): void => {
    const node = document.createElement("div");
    node.className = "sel-item";
    node.setAttribute("role", "option");
    if (grouped) node.classList.add("grouped");
    if (option.disabled) {
      node.classList.add("disabled");
      node.setAttribute("aria-disabled", "true");
    }
    node.textContent = option.textContent ?? "";
    items.push({ option, label: node.textContent, node });
  };
  for (const child of Array.from(select.children)) {
    if (child instanceof HTMLOptGroupElement) {
      const node = document.createElement("div");
      node.className = "sel-group";
      node.textContent = child.label;
      items.push({ option: null, label: child.label, node });
      for (const option of Array.from(child.querySelectorAll("option"))) add(option, true);
    } else if (child instanceof HTMLOptionElement) {
      add(child, false);
    }
  }
  return items;
}

function openMenu(select: HTMLSelectElement): void {
  closeMenu();
  const items = build(select);
  if (!items.length) return;
  const menu = document.createElement("div");
  menu.className = "sel-menu";
  menu.setAttribute("role", "listbox");
  for (const item of items) menu.appendChild(item.node);
  document.body.appendChild(menu);

  const rect = select.getBoundingClientRect();
  menu.style.minWidth = `${rect.width}px`;
  menu.style.left = `${Math.max(4, Math.min(rect.left, window.innerWidth - menu.offsetWidth - 4))}px`;
  const room = { below: window.innerHeight - rect.bottom - 8, above: rect.top - 8 };
  const wanted = Math.min(menu.scrollHeight + 2, 360); // + the border
  const down = room.below >= wanted || room.below >= room.above;
  const height = Math.min(wanted, down ? room.below : room.above);
  menu.style.maxHeight = `${Math.max(60, height)}px`;
  menu.style.top = down ? `${rect.bottom + 2}px` : `${rect.top - Math.max(60, height) - 2}px`;

  const usable = (index: number): boolean => !!items[index]?.option && !items[index].option!.disabled;
  const current = items.findIndex((item) => item.option?.selected);
  const state = { select, menu, items, active: usable(current) ? current : items.findIndex((_, i) => usable(i)), close: () => {} };

  const highlight = (index: number): void => {
    state.active = index;
    items.forEach((item, i) => item.node.classList.toggle("active", i === index));
    items[index]?.node.scrollIntoView({ block: "nearest" });
  };
  items.forEach((item, i) => item.option?.selected && item.node.classList.add("chosen"));
  highlight(state.active);

  const choose = (index: number): void => {
    const option = items[index]?.option;
    if (!option || option.disabled) return;
    const changed = select.selectedIndex !== option.index;
    select.selectedIndex = option.index;
    closeMenu();
    select.focus();
    if (changed) {
      select.dispatchEvent(new Event("input", { bubbles: true }));
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }
  };
  const step = (from: number, delta: number): number => {
    for (let i = from + delta; i >= 0 && i < items.length; i += delta) if (usable(i)) return i;
    return from;
  };

  const onDown = (event: MouseEvent): void => {
    if (!menu.contains(event.target as Node)) closeMenu();
  };
  const onKey = (event: KeyboardEvent): void => {
    const swallow = (): void => {
      event.preventDefault();
      event.stopPropagation();
    };
    if (event.key === "Escape") {
      swallow();
      closeMenu();
      select.focus();
    } else if (event.key === "ArrowDown") {
      swallow();
      highlight(step(state.active, 1));
    } else if (event.key === "ArrowUp") {
      swallow();
      highlight(step(state.active, -1));
    } else if (event.key === "Home") {
      swallow();
      highlight(step(-1, 1));
    } else if (event.key === "End") {
      swallow();
      highlight(step(items.length, -1));
    } else if (event.key === "Enter" || event.key === " ") {
      swallow();
      choose(state.active);
    } else if (event.key === "Tab") {
      closeMenu();
    } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) {
      swallow();
      const start = state.active;
      const order = [...items.keys()].slice(start + 1).concat([...items.keys()].slice(0, start + 1));
      const hit = order.find((i) => usable(i) && items[i].label.toLowerCase().startsWith(event.key.toLowerCase()));
      if (hit !== undefined) highlight(hit);
    }
  };
  const onWheel = (event: Event): void => {
    if (!menu.contains(event.target as Node)) closeMenu();
  };
  menu.addEventListener("mousemove", (event) => {
    const index = items.findIndex((item) => item.node === (event.target as HTMLElement).closest(".sel-item"));
    if (index >= 0 && index !== state.active && usable(index)) highlight(index);
  });
  menu.addEventListener("mousedown", (event) => event.preventDefault());
  menu.addEventListener("click", (event) => {
    const index = items.findIndex((item) => item.node === (event.target as HTMLElement).closest(".sel-item"));
    if (index >= 0) choose(index);
  });
  document.addEventListener("mousedown", onDown, true);
  document.addEventListener("keydown", onKey, true);
  document.addEventListener("wheel", onWheel, { capture: true, passive: true });
  window.addEventListener("resize", closeMenu);
  window.addEventListener("blur", closeMenu);
  state.close = () => {
    document.removeEventListener("mousedown", onDown, true);
    document.removeEventListener("keydown", onKey, true);
    document.removeEventListener("wheel", onWheel, true);
    window.removeEventListener("resize", closeMenu);
    window.removeEventListener("blur", closeMenu);
    menu.remove();
    select.classList.remove("menu-open");
    open = null;
  };
  select.classList.add("menu-open");
  open = state;
}

function target(event: Event): HTMLSelectElement | null {
  const select = (event.target as Element | null)?.closest?.("select");
  return select instanceof HTMLSelectElement && !select.disabled && !select.multiple && themed() ? select : null;
}

export function installSelectMenu(): void {
  document.addEventListener(
    "mousedown",
    (event) => {
      const select = target(event);
      if (!select || event.button !== 0) return;
      event.preventDefault(); // keeps the native list shut
      select.focus();
      if (open?.select === select) closeMenu();
      else openMenu(select);
    },
    true,
  );
  document.addEventListener("keydown", (event) => {
    const select = target(event);
    if (!select || open) return;
    if (event.key === " " || (event.altKey && event.key === "ArrowDown") || event.key === "F4") {
      event.preventDefault();
      openMenu(select);
    }
  });
}
