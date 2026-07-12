import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/chat': 'http://localhost:8088', '/stop': 'http://localhost:8088', '/history': 'http://localhost:8088', '/conversations': 'http://localhost:8088', '/clear-history': 'http://localhost:8088', '/delete-conversation': 'http://localhost:8088' } }
})
