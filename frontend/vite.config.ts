// Local, offline build: relative asset paths, no external requests, no inline scripts.
import { defineConfig } from 'vite'

export default defineConfig({
  base: './',
  build: { outDir: 'dist', modulePreload: false, assetsInlineLimit: 0 },
  server: { host: '127.0.0.1' },
  preview: { host: '127.0.0.1' },
})
