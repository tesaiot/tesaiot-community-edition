import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // loadEnv, not process.env: Vite exposes .env to the CLIENT, and this config
  // runs in Node, where those variables are not set. Reading process.env here
  // silently fell through to the default target, so a dev server configured in
  // .env proxied somewhere else entirely — on a machine running two installs,
  // to the wrong one.
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    server: {
      port: 3000,
      // Proxy /api to YOUR Community Edition install — the address install.sh
      // printed. This used to target a hosted service, which quietly sent a
      // self-hoster's requests to someone else's platform.
      //
      // Its own variable on purpose: VITE_API_BASE_URL is what the CLIENT uses,
      // and in dev that must stay same-origin so requests come through here.
      // CE answers a preflight 200 without an access-control-allow-origin
      // header, so a direct cross-origin call from the dev server is blocked.
      proxy: {
        '/api': {
          target:
            env.VITE_DEV_PROXY_TARGET || env.VITE_API_BASE_URL || 'https://localhost',
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
  };
});
