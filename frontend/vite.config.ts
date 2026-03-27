import { resolve } from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const repoEnv = loadEnv(mode, resolve(process.cwd(), ".."), "");
  const backendPort = env.BACKEND_PORT || repoEnv.BACKEND_PORT || "18000";
  const proxyTarget = env.VITE_DEV_API_PROXY || repoEnv.VITE_DEV_API_PROXY || `http://localhost:${backendPort}`;

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
