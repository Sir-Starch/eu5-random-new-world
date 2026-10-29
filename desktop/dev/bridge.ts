// The generator's bridge for the window in a browser: `npm run dev` without Tauri.
//
// Vite serves the window; this plugin starts `python -m rnw.gui.bridge` (through uv, from the
// repository) and relays its JSON lines over a WebSocket at /__rnw, as the Tauri shell relays them
// over its IPC. It is a development tool: the packaged window never opens a port.
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { createInterface } from "node:readline";
import { resolve } from "node:path";
import type { Plugin } from "vite";
import { WebSocketServer, type WebSocket } from "ws";

export function devBridge(): Plugin {
  return {
    name: "rnw-dev-bridge",
    apply: "serve",
    configureServer(server) {
      const root = resolve(import.meta.dirname, "..", "..");
      const sockets = new Set<WebSocket>();
      let bridge: ChildProcessWithoutNullStreams | null = null;

      const start = (): ChildProcessWithoutNullStreams => {
        const args = ["run", "--quiet", "python", "-m", "rnw.gui.bridge"];
        if (process.env.RNW_DATA) args.push("--data", process.env.RNW_DATA);
        const child = spawn("uv", args, { cwd: root, stdio: ["pipe", "pipe", "pipe"] });
        createInterface({ input: child.stdout }).on("line", (line) => {
          for (const socket of sockets) socket.send(line);
        });
        child.stderr.on("data", (chunk: Buffer) => process.stderr.write(`[bridge] ${chunk}`));
        child.on("exit", (code) => {
          server.config.logger.warn(`[rnw] bridge ended (${code ?? "signal"})`);
          bridge = null;
        });
        return child;
      };

      const sockets_server = new WebSocketServer({ noServer: true });
      server.httpServer?.on("upgrade", (request, socket, head) => {
        if (request.url !== "/__rnw") return;
        sockets_server.handleUpgrade(request, socket, head, (ws) => {
          sockets.add(ws);
          bridge ??= start();
          ws.on("message", (data) => bridge?.stdin.write(`${data.toString()}\n`));
          ws.on("close", () => sockets.delete(ws));
        });
      });
      server.httpServer?.on("close", () => bridge?.stdin.end());
    },
  };
}
