import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  server: { host: true, port: 43180 },
  preview: { host: true, port: 43180 },
  build: { sourcemap: true, target: "es2022" },
});
