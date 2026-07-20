import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Keep in sync with public/_headers (Workers static assets production).
const godotHeaders = {
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Embedder-Policy": "require-corp",
  "Cross-Origin-Resource-Policy": "same-origin",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  "X-Frame-Options": "SAMEORIGIN",
};

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    headers: godotHeaders,
  },
  preview: {
    headers: godotHeaders,
  },
});
