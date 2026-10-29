// How the window speaks to the generator: Tauri's IPC in the application, a WebSocket to the
// dev bridge (dev/bridge.ts) in a browser. Both carry the bridge's JSON lines unchanged.

import type { State } from "./types";

type Pending = { resolve: (value: unknown) => void; reject: (reason: Error) => void };
type Listener = (state: State) => void;

export interface Transport {
  call<T = unknown>(method: string, params?: Record<string, unknown>): Promise<T>;
  onState(listener: Listener): void;
  onEnd(listener: (reason: string) => void): void;
  readonly native: boolean;
}

export function inTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

class TauriTransport implements Transport {
  readonly native = true;
  private listeners: Listener[] = [];

  private ends: ((reason: string) => void)[] = [];

  constructor() {
    void import("@tauri-apps/api/event").then(({ listen }) => {
      void listen<State>("rnw://state", (event) => {
        for (const listener of this.listeners) listener(event.payload);
      });
      void listen<string>("rnw://ended", (event) => {
        for (const listener of this.ends) listener(event.payload);
      });
    });
  }

  onEnd(listener: (reason: string) => void): void {
    this.ends.push(listener);
  }

  async call<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    const { invoke } = await import("@tauri-apps/api/core");
    try {
      return await invoke<T>("rpc", { method, params });
    } catch (error) {
      throw new Error(String(error));
    }
  }

  onState(listener: Listener): void {
    this.listeners.push(listener);
  }
}

class SocketTransport implements Transport {
  readonly native = false;
  private socket: WebSocket;
  private open: Promise<void>;
  private next = 1;
  private pending = new Map<number, Pending>();
  private listeners: Listener[] = [];

  constructor(url: string) {
    this.socket = new WebSocket(url);
    this.open = new Promise((resolve, reject) => {
      this.socket.addEventListener("open", () => resolve(), { once: true });
      this.socket.addEventListener("error", () => reject(new Error("No bridge")), { once: true });
    });
    this.socket.addEventListener("message", (event) => this.receive(String(event.data)));
  }

  onEnd(listener: (reason: string) => void): void {
    this.socket.addEventListener("close", () => listener("The bridge closed"));
  }

  private receive(line: string): void {
    const message = JSON.parse(line) as {
      id?: number;
      result?: unknown;
      error?: string;
      event?: string;
      data?: State;
    };
    if (message.event === "state" && message.data) {
      for (const listener of this.listeners) listener(message.data);
      return;
    }
    if (typeof message.id !== "number") return;
    const waiting = this.pending.get(message.id);
    if (!waiting) return;
    this.pending.delete(message.id);
    if (message.error !== undefined) waiting.reject(new Error(message.error));
    else waiting.resolve(message.result);
  }

  async call<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
    await this.open;
    const id = this.next++;
    return new Promise<T>((resolve, reject) => {
      this.pending.set(id, { resolve: resolve as (value: unknown) => void, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  onState(listener: Listener): void {
    this.listeners.push(listener);
  }
}

export function connect(): Transport {
  if (inTauri()) return new TauriTransport();
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  return new SocketTransport(`${scheme}://${location.host}/__rnw`);
}
