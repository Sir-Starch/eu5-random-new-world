// What the system does for the window: file dialogs, the clipboard, opening a folder or a link.
// In Tauri these are the platform's own; in a browser (development) a path is typed instead.

import { app } from "./app.svelte";
import { inTauri } from "./transport";

export interface Filter {
  name: string;
  extensions: string[];
}

export async function openFile(title: string, filters: Filter[]): Promise<string | null> {
  if (!inTauri()) return app.askPath(title);
  const { open } = await import("@tauri-apps/plugin-dialog");
  const chosen = await open({ title, filters, multiple: false, directory: false });
  return typeof chosen === "string" ? chosen : null;
}

export async function saveFile(
  title: string,
  name: string,
  filters: Filter[],
): Promise<string | null> {
  if (!inTauri()) return app.askPath(title, name);
  const { save } = await import("@tauri-apps/plugin-dialog");
  const { homeDir, join } = await import("@tauri-apps/api/path");
  const defaultPath = await join(await homeDir(), name);
  return (await save({ title, defaultPath, filters })) ?? null;
}

export async function pickFolder(title: string): Promise<string | null> {
  if (!inTauri()) return app.askPath(title);
  const { open } = await import("@tauri-apps/plugin-dialog");
  const chosen = await open({ title, directory: true, multiple: false });
  return typeof chosen === "string" ? chosen : null;
}

export async function copyText(text: string): Promise<void> {
  if (inTauri()) {
    const { writeText } = await import("@tauri-apps/plugin-clipboard-manager");
    await writeText(text);
  } else {
    await navigator.clipboard.writeText(text);
  }
}

export async function readText(): Promise<string> {
  if (inTauri()) {
    const { readText: read } = await import("@tauri-apps/plugin-clipboard-manager");
    return (await read()) ?? "";
  }
  return navigator.clipboard.readText();
}

export async function copyImage(dataUrl: string): Promise<void> {
  const bytes = Uint8Array.from(atob(dataUrl.split(",")[1] ?? ""), (c) => c.charCodeAt(0));
  if (inTauri()) {
    const { writeImage } = await import("@tauri-apps/plugin-clipboard-manager");
    await writeImage(bytes);
  } else {
    await navigator.clipboard.write([
      new ClipboardItem({ "image/png": new Blob([bytes], { type: "image/png" }) }),
    ]);
  }
}

export async function openPath(path: string): Promise<void> {
  if (inTauri()) {
    const { openPath: open } = await import("@tauri-apps/plugin-opener");
    await open(path);
  } else {
    app.toast("info", path);
  }
}

export async function openUrl(url: string): Promise<void> {
  if (inTauri()) {
    const { openUrl: open } = await import("@tauri-apps/plugin-opener");
    await open(url);
  } else {
    window.open(url, "_blank", "noopener");
  }
}

/** Paths dropped on the window (Tauri gives them; a browser does not). */
export async function onDrop(handler: (paths: string[]) => void): Promise<void> {
  if (!inTauri()) return;
  const { getCurrentWebview } = await import("@tauri-apps/api/webview");
  await getCurrentWebview().onDragDropEvent((event) => {
    if (event.payload.type === "drop") handler(event.payload.paths);
  });
}
