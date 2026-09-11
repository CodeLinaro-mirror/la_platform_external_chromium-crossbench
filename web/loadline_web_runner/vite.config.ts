// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

import {resolve} from 'path';
import {defineConfig, type Plugin, searchForWorkspaceRoot} from 'vite';

const POPUP_ALLOWED_PREFIXES = [
  '/auth',
  '/privacy',
  '/google03706b24b8377fa4.html',
];

function coopCoepPlugin(): Plugin {
  const handler = (req: any, res: any, next: any) => {
    const url = req.url || '';
    if (POPUP_ALLOWED_PREFIXES.some((prefix) => url.startsWith(prefix))) {
      res.setHeader('Cross-Origin-Opener-Policy', 'same-origin-allow-popups');
      next();
      return;
    }
    res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
    res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
    next();
  };

  return {
    name: 'coop-coep-plugin',
    configureServer(server) {
      server.middlewares.use(handler);
    },
    configurePreviewServer(server) {
      server.middlewares.use(handler);
    },
  };
}

export default defineConfig({
  plugins: [coopCoepPlugin()],
  worker: {
    format: 'es',
  },
  optimizeDeps: {
    exclude: ['pyodide'],
  },
  server: {
    fs: {
      allow: [searchForWorkspaceRoot(process.cwd())],
      deny: ['.env', '.env.*', '**/.git/**'],
    },
    proxy: {
      '/gcs-proxy': {
        target: 'https://storage.googleapis.com',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/gcs-proxy/, ''),
      },
    },
  },
  build: {
    target: 'es2022',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        auth: resolve(__dirname, 'auth.html'),
        privacy: resolve(__dirname, 'privacy.html'),
      },
    },
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    include: ['tests/**/*.test.ts'],
    pool: 'forks',
  },
});
