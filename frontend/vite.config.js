import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = process.env.VITE_BACKEND_ORIGIN || 'http://localhost:5000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: ['chat.project-kk.com'],
    proxy: {
      '/travel_send_message': backendTarget,
      '/travel_submit_plan': backendTarget,
      '/complete': backendTarget,
      '/api/reset': backendTarget,
      '/reply_send_message': backendTarget,
      '/reply_submit_plan': backendTarget,
      '/fitness_send_message': backendTarget,
    },
  },
})
