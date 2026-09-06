import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // Proxy API requests to YOUR Community Edition install. VITE_API_BASE_URL
    // is the address install.sh printed; the default is a stock local install.
    // This used to point at a hosted service, which quietly sent a
    // self-hoster's requests to someone else's platform.
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'https://localhost',
        changeOrigin: true,
        // A stock install serves its own private-PKI certificate.
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
