import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

/**
 * Library build → Flask projesinin web/static/numune/ klasörüne
 * IIFE format: window.NumuneApp.mount(el, opts) ile inline çağrı.
 *
 * Output:
 *   ../web/static/numune/numune.js      (React + UI bundled)
 *   ../web/static/numune/numune.css     (Stiller)
 */
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: resolve(__dirname, "../web/static/numune"),
    emptyOutDir: true,
    cssCodeSplit: false,
    sourcemap: false,
    lib: {
      entry: resolve(__dirname, "src/main.tsx"),
      formats: ["iife"],
      name: "NumuneApp",
      fileName: () => "numune.js",
    },
    rollupOptions: {
      output: {
        assetFileNames: "numune.[ext]",
      },
    },
    target: "es2020",
    minify: "esbuild",
  },
});
