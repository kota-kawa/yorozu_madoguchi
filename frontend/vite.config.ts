/**
 * EN: Provide the vite.config module implementation.
 * JP: vite.config モジュールの実装を定義する。
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * EN: Declare the backendTarget value.
 * JP: backendTarget の値を宣言する。
 */
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
      '/job_send_message': backendTarget,
      '/study_send_message': backendTarget,
      '/api/user_type': backendTarget,
    },
  },
})
