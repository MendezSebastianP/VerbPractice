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
        rollupOptions: {
            output: {
                entryFileNames: 'app.js',
                chunkFileNames: 'chunks/[name].js',
                assetFileNames: (assetInfo) => {
                    if (assetInfo.name?.endsWith('.css')) {
                        return 'app.css';
                    }
                    return 'assets/[name][extname]';
                }
            }
        }
    }
});
//# sourceMappingURL=vite.config.js.map