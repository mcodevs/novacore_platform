import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Mini App backend bilan bir domenda beriladi: https://<host>/app
// Talab: bundle < 300 KB (gzip) — garajdagi zaif internet.
export default defineConfig({
  plugins: [react()],
  base: '/app/',
  build: {
    outDir: 'dist',
    target: 'es2020',
    sourcemap: false,
    reportCompressedSize: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
});
