import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        timeout: 300000,        // 5 min — local LLM calls can be slow
        proxyTimeout: 300000,
      },
      '/ws': { target: 'ws://localhost:8080', ws: true }
    }
  }
})
