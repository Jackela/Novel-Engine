import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";
import { readProductIdentity } from "../server/src/shared/infrastructure/workspace_manifest.js";

const apiProxyTimeoutMs = 5 * 60 * 1000;
const productIdentity = readProductIdentity(
  path.resolve(import.meta.dirname, "..", "server", "package.json"),
);
const PRODUCT_NAME_TOKEN = "__PRODUCT_NAME__";

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

export function injectProductIdentityHtml(html: string, productName: string): string {
  if (!html.includes(PRODUCT_NAME_TOKEN)) {
    throw new Error("frontend/index.html must contain the product-name token");
  }
  return html.replaceAll(PRODUCT_NAME_TOKEN, escapeHtml(productName));
}

const productIdentityHtmlPlugin: Plugin = {
  name: "product-identity-html",
  transformIndexHtml: (html) => injectProductIdentityHtml(html, productIdentity.name),
};

export default defineConfig({
  plugins: [productIdentityHtmlPlugin, react()],
  define: {
    __PRODUCT_IDENTITY__: JSON.stringify(productIdentity),
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: (process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000").replace(/\/+$/, ""),
        changeOrigin: true,
        timeout: apiProxyTimeoutMs,
        proxyTimeout: apiProxyTimeoutMs,
      },
    },
  },
  preview: {
    port: 4173,
  },
});
