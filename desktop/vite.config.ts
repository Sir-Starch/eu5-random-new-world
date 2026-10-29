import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vitest/config";
import { devBridge } from "./dev/bridge";

// Tauri serves the built files itself; `npm run dev` serves them with the dev bridge.
export default defineConfig({
  plugins: [svelte(), devBridge()],
  clearScreen: false,
  server: { port: 5178, strictPort: true, host: "127.0.0.1" },
  build: { target: "es2022", outDir: "dist", emptyOutDir: true, sourcemap: false },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
