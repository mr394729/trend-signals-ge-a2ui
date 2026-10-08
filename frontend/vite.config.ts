/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig, type Plugin } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// Gemini Enterprise's WebFrameSrcdoc renderer REJECTS any payload that doesn't
// self-declare exactly `connect-src 'none'`. We inject that meta only in the
// PRODUCTION build — in `vite dev` the same directive would block Vite's HMR
// websocket. index.html ships a `<!-- GE_SRCDOC_CSP -->` marker we swap at build.
function geSrcdocCsp(): Plugin {
  const META =
    '<meta http-equiv="Content-Security-Policy" content="connect-src \'none\'" />';
  return {
    name: "ge-srcdoc-csp",
    transformIndexHtml: {
      order: "pre",
      handler(html, ctx) {
        if (ctx.server) return html; // skip under `vite dev`
        return html.replace("<!-- GE_SRCDOC_CSP -->", META);
      },
    },
  };
}

// The workspace is delivered as the `htmlContent` of an IFrameSrcdoc: ONE self-contained
// HTML doc (no origin inside srcdoc → no external asset URLs). The server splices
// `window.__TREND_SIGNALS_STATE__` before `</head>` at emission time. `viteSingleFile` inlines all JS/CSS; `base: ""`
// keeps references relative so the doc works from `srcdoc=`.
export default defineConfig({
  base: "",
  plugins: [react(), tailwindcss(), geSrcdocCsp(), viteSingleFile()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: { port: 5173, host: true },
  build: {
    outDir: "dist",
    sourcemap: false,
    assetsInlineLimit: 100_000_000,
    chunkSizeWarningLimit: 4_000,
    cssCodeSplit: false,
    reportCompressedSize: false,
    rollupOptions: { output: { inlineDynamicImports: true } },
  },
});
