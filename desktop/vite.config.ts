import { svelte } from "@sveltejs/vite-plugin-svelte";
import { searchForWorkspaceRoot } from "vite";
import { defineConfig } from "vitest/config";
import { devBridge } from "./dev/bridge";

// Tauri serves the built files itself; `npm run dev` serves them with the dev bridge.
export default defineConfig({
  plugins: [svelte(), devBridge()],
  clearScreen: false,
  server: {
    port: 5178,
    strictPort: true,
    host: "127.0.0.1",
    // The lenses' look is the generator's own file (src/rnw/gui/lenses.json).
    fs: { allow: [searchForWorkspaceRoot(process.cwd()), "../src/rnw/gui"] },
  },
  build: { target: "es2022", outDir: "dist", emptyOutDir: true, sourcemap: false },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
