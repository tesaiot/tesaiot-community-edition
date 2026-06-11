/*
 * TESAIoT Community Edition
 * SPDX-License-Identifier: Apache-2.0
 * Copyright TESAIoT Platform contributors
 */

import { fileURLToPath, URL } from 'node:url';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, Plugin } from 'vite';
import { execSync } from 'child_process';
import crypto from 'crypto';
import fs from 'fs';
import path from 'path';

// Get version from VERSION.txt file
function getAppVersion() {
  try {
    return fs.readFileSync('./VERSION.txt', 'utf8').trim();
  } catch {
    return process.env.npm_package_version || 'v2025.06-beta-5';
  }
}

// Get git commit hash for build versioning
function getGitCommitHash() {
  try {
    // Suppress stderr to avoid noisy "fatal: not a git repository" during Docker builds
    return execSync('git rev-parse --short HEAD', { stdio: ['ignore', 'pipe', 'ignore'] })
      .toString()
      .trim();
  } catch {
    return 'unknown';
  }
}

// Custom plugin to inject build metadata into HTML and generate version.json
function htmlMetaInjector(): Plugin {
  const buildTime = new Date().toISOString();
  const buildTimestamp = Date.now();
  const buildId = crypto.randomBytes(8).toString('hex');
  const gitCommit = getGitCommitHash();
  const version = getAppVersion();
  
  return {
    name: 'html-meta-injector',
    transformIndexHtml(html) {
      let out = html
        .replace(/__BUILD_ID__/g, buildId)
        .replace(/__BUILD_TIME__/g, buildTime)
        .replace(/__BUILD_TIMESTAMP__/g, buildTimestamp.toString())
        .replace(/__BUILD_INTEGRITY__/g, gitCommit);
      // Robustly set build-version meta content from VERSION.txt regardless of placeholder
      out = out.replace(
        /(\<meta\s+name=\"build-version\"\s+content=\")[^"]*(\"\s*\/?\>)/,
        `$1${version}$2`
      );
      return out;
    },
    generateBundle() {
      // Generate version.json for runtime version checking
      const versionInfo = {
        version,
        buildTime,
        buildTimestamp,
        buildId,
        gitCommit,
        cacheBuster: buildTimestamp
      };
      
      this.emitFile({
        type: 'asset',
        fileName: 'version.json',
        source: JSON.stringify(versionInfo, null, 2)
      });
    }
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), htmlMetaInjector()],
  base: '/',
  // Use a single build timestamp across all output file names to avoid producing
  // multiple 'index.*.js' with different timestamps in one build.
  // This improves deploy determinism and avoids confusion when scanning assets.
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  define: {
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
    __GIT_COMMIT__: JSON.stringify(getGitCommitHash()),
    __APP_VERSION__: JSON.stringify(getAppVersion()), // Use the function that reads from VERSION.txt
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(getAppVersion()),
    'import.meta.env.VITE_APP_NAME': JSON.stringify('tesa'),
  },
  build: {
    chunkSizeWarningLimit: 3000,
    // Allow opt-in sourcemaps for one-off diagnostics
    sourcemap: process.env.BUILD_SOURCEMAP === '1',
    // Use Terser with conservative settings to avoid TDZ errors: esbuild's
    // aggressive code hoisting has broken circular dependencies in large
    // vendor bundles before ("Cannot access 'X' before initialization").
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: false,   // keep console logs for debugging
        drop_debugger: true,
        // CRITICAL: Disable ALL hoisting to prevent TDZ errors
        hoist_vars: false,
        hoist_funs: false,
        hoist_props: false,
        toplevel: false,
        passes: 1,
        // Disable optimizations that reorder code
        sequences: false,
        conditionals: true,
        evaluate: true,
        booleans: true,
        loops: true,
        unused: true,
        if_return: true,
        join_vars: false,  // Don't join var declarations
        collapse_vars: false,  // Don't collapse single-use vars
        reduce_vars: false,  // Don't reduce variables
      },
      mangle: {
        toplevel: false,
        // Keep function names for better stack traces
        keep_fnames: true,
      },
      format: {
        comments: false,
      },
    },
    // CRITICAL: Clear output directory to prevent stale files
    emptyOutDir: true,
    // Generate manifest for build tracking
    manifest: true,
    rollupOptions: {
      // Single build timestamp reused for all filenames
      // (prevents multiple index.*.js entries with different timestamps)
      // eslint-disable-next-line no-undef
      // @ts-ignore
      // Using a closure to capture once
      // Note: Rollup will reuse these functions within the same process
      // so the constant below remains stable for the whole build.
      // safer than calling Date.now() in each callback.
      // CRITICAL FIX: Exclude test dependencies from production build
      external: (id) => {
        // Exclude jest-axe and testing utilities from production builds
        const testDependencies = [
          'jest-axe',
          '@testing-library',
          'vitest',
          'jsdom',
          'msw'
        ];
        return testDependencies.some(dep => id.includes(dep));
      },
      output: {
        // Enhanced cache busting: content hash + a single build timestamp
        // captured once at config load
        entryFileNames: (() => {
          const ts = Date.now();
          return () => `assets/[name].[hash].${ts}.js`;
        })(),
        chunkFileNames: (() => {
          const ts = Date.now();
          return () => `assets/[name].[hash].${ts}.js`;
        })(),
        assetFileNames: (() => {
          const ts = Date.now();
          return () => `assets/[name].[hash].${ts}.[ext]`;
        })(),
        // Manual chunk splitting for the heaviest vendor groups
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-ui': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu', '@radix-ui/react-tabs', 'lucide-react', 'clsx', 'tailwind-merge'],
          'vendor-auth': ['@supabase/supabase-js'],
          'vendor-utils': ['axios', 'date-fns', 'zod', 'react-hook-form'],
        },
      },
    },
    // Preload directives for critical chunks
    modulePreload: {
      polyfill: true,
    },
  },
  // Optimize dependencies
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        '.ts': 'tsx',
        '.tsx': 'tsx',
      },
    },
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@radix-ui/react-dialog',
    ],
    // Let Vite auto-discover ag-grid dependencies
    // Use standard cache directory (will be cleaned by build process)
  },
  server: {
    // Add cache control headers in dev
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
    },
    // Proxy API requests to backend
    proxy: {
      '/api': {
        target: 'http://localhost:5566',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  // Enhanced preview mode with proper cache headers
  preview: {
    headers: {
      // HTML files should never be cached
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
      // Add security headers
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'X-XSS-Protection': '1; mode=block',
    },
  },
});
