import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/travel_send_message': process.env.VITE_BACKEND_ORIGIN || 'http://localhost:5000',
      '/travel_submit_plan': process.env.VITE_BACKEND_ORIGIN || 'http://localhost:5000',
      '/complete': process.env.VITE_BACKEND_ORIGIN || 'http://localhost:5000',
      '/api/reset': process.env.VITE_BACKEND_ORIGIN || 'http://localhost:5000',
    },
  },
})
