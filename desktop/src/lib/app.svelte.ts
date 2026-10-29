// The window's state: what the bridge last sent, what the window itself chose (the tab of a
// world, the worlds ticked in the library, the open dialog) and the messages it shows.

import { connect, type Transport } from "./transport";
import type { State, Static } from "./types";

export type ToastKind = "info" | "success" | "warning" | "error";
export interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
}

export type Modal =
  | { kind: "settings" }
  | { kind: "about" }
  | { kind: "candidates" }
  | { kind: "compare"; layer: string }
  | { kind: "shortcuts" }
  | {
      kind: "confirm";
      title: string;
      body: string;
      confirm: string;
      danger?: boolean;
      resolve: (answer: boolean) => void;
    }
  | {
      kind: "path";
      title: string;
      value: string;
      resolve: (answer: string | null) => void;
    };

export type WorldTab = "overview" | "map" | "versions" | "share" | "notes";

const LOCALES: Record<string, string> = {
  braz_por: "pt-BR",
  english: "en",
  french: "fr",
  german: "de",
  japanese: "ja",
  korean: "ko",
  polish: "pl",
  russian: "ru",
  simp_chinese: "zh-CN",
  spanish: "es",
  turkish: "tr",
};

class App {
  transport: Transport | null = null;
  info = $state<Static | null>(null);
  now = $state<State | null>(null);
  toasts = $state<Toast[]>([]);
  modal = $state<Modal | null>(null);
  worldTab = $state<WorldTab>("overview");
  ticked = $state<string[]>([]);
  failed = $state("");
  mapFocus = $state(false);
  private toastNumber = 0;

  async start(): Promise<void> {
    try {
      this.transport = connect();
      this.transport.onState((state) => {
        this.now = state;
      });
      this.transport.onEnd((reason) => {
        this.failed = reason;
      });
      const hello = await this.transport.call<{ static: Static; state: State }>("hello");
      this.info = hello.static;
      this.now = hello.state;
      document.documentElement.lang = LOCALES[hello.static.language] ?? "en";
    } catch (error) {
      this.failed = String(error);
    }
  }

  get native(): boolean {
    return this.transport?.native ?? false;
  }

  /** Call the bridge; an exception becomes an error message. */
  async call<T = unknown>(method: string, params: Record<string, unknown> = {}): Promise<T | null> {
    if (!this.transport) return null;
    try {
      return await this.transport.call<T>(method, params);
    } catch (error) {
      this.toast("error", error instanceof Error ? error.message : String(error));
      return null;
    }
  }

  /** Call an action that returns the reason it could not run, or nothing; show the reason. */
  async act(method: string, params: Record<string, unknown> = {}): Promise<boolean> {
    const problem = await this.call<string | null>(method, params);
    if (typeof problem === "string" && problem) {
      this.toast("warning", problem);
      return false;
    }
    return true;
  }

  /** Call an action that returns a message to show either way (saved, or why not). */
  async report(method: string, params: Record<string, unknown>, success: string): Promise<void> {
    const message = await this.call<string | null>(method, params);
    if (typeof message === "string" && message) {
      this.toast(message === success ? "success" : "warning", message);
    }
  }

  toast(kind: ToastKind, text: string, seconds = kind === "error" ? 12 : 6): void {
    const id = ++this.toastNumber;
    this.toasts = [...this.toasts.filter((item) => item.text !== text), { id, kind, text }];
    setTimeout(() => this.dismiss(id), seconds * 1000);
  }

  dismiss(id: number): void {
    this.toasts = this.toasts.filter((item) => item.id !== id);
  }

  confirm(title: string, body: string, confirm: string, danger = false): Promise<boolean> {
    return new Promise((resolve) => {
      this.modal = { kind: "confirm", title, body, confirm, danger, resolve };
    });
  }

  askPath(title: string, value = ""): Promise<string | null> {
    return new Promise((resolve) => {
      this.modal = { kind: "path", title, value, resolve };
    });
  }

  async setLanguage(language: string): Promise<void> {
    const hello = await this.call<{ static: Static; state: State }>("set_language", { language });
    if (hello) {
      this.info = hello.static;
      this.now = hello.state;
      document.documentElement.lang = LOCALES[hello.static.language] ?? "en";
    }
  }

  get locale(): string {
    return LOCALES[this.info?.language ?? "english"] ?? "en";
  }
}

export const app = new App();

/** The window's string for ``key``, with ``{name}`` fields filled in as Python's format does. */
export function t(key: string, values: Record<string, unknown> = {}): string {
  const source = app.info?.strings[key];
  if (source === undefined) return key;
  return source.replace(/\{(\w+)(?::([^}]*))?\}/g, (_whole, name: string, spec?: string) => {
    const value = values[name];
    if (value === undefined) return `{${name}}`;
    if (spec === "g" && typeof value === "number") return String(Number(value.toPrecision(6)));
    return String(value);
  });
}

/** A whole number with its digits grouped as the window's language groups them. */
export function grouped(value: number): string {
  const separator = app.info?.grouping ?? ",";
  return Math.round(value)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, separator);
}

export function when(seconds: number): string {
  return new Intl.DateTimeFormat(app.locale, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(seconds * 1000),
  );
}

export function clock(seconds: number): string {
  const total = Math.max(0, Math.ceil(seconds));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}:${rest.toString().padStart(2, "0")}`;
}
