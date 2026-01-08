import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/travel_send_message': 'http://localhost:5000',
      '/travel_submit_plan': 'http://localhost:5000',
      '/complete': 'http://localhost:5000',
      '/api/reset': 'http://localhost:5000',
    },
  },
})
