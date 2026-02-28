import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";
import { copyFileSync, mkdirSync, existsSync } from "fs";

function copyManifestPlugin() {
  return {
    name: "copy-manifest",
    closeBundle() {
      const distDir = resolve(__dirname, "dist");
      const iconsDir = resolve(distDir, "icons");
      if (!existsSync(iconsDir)) mkdirSync(iconsDir, { recursive: true });

      copyFileSync(
        resolve(__dirname, "public/manifest.json"),
        resolve(distDir, "manifest.json")
      );
      for (const size of [16, 48, 128]) {
        const src = resolve(__dirname, `public/icons/icon${size}.png`);
        if (existsSync(src)) {
          copyFileSync(src, resolve(iconsDir, `icon${size}.png`));
        }
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), copyManifestPlugin()],
  base: "./",
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        sidepanel: resolve(__dirname, "src/sidepanel/index.html"),
        background: resolve(__dirname, "src/background/index.ts"),
        content: resolve(__dirname, "src/content/index.ts"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});
