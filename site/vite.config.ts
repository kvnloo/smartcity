import { defineConfig } from "vite";

export default defineConfig({
  // Relative URLs so lookdev works at https://kvnloo.github.io/smartcity/ and locally.
  base: "./",
  server: { host: true, port: 43180 },
  preview: { host: true, port: 43180 },
  build: { sourcemap: true, target: "es2022" },
});
