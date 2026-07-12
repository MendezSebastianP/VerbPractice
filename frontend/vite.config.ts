import { resolve } from 'node:path';
import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';

const spaOutDir = resolve(__dirname, 'static/spa');

export default defineConfig({
  base: '/static/spa/',
  plugins: [tailwindcss(), svelte()],
  build: {
    outDir: spaOutDir,
    emptyOutDir: true,
    // Content-hashed filenames + manifest: every deploy gets fresh URLs, so
    // browser/Cloudflare caches can never serve a stale bundle. The FastAPI
    // shell (app/routers/spa.py) reads the hashed names from the manifest.
    manifest: true,
    rollupOptions: {
      output: {
        entryFileNames: 'app-[hash].js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name?.endsWith('.css')) {
            return 'app-[hash].css';
          }
          return 'assets/[name]-[hash][extname]';
        }
      }
    }
  }
});
