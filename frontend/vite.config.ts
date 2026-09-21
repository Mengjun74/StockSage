import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Bind mounts do not deliver inotify events on Docker Desktop for Windows, so the
    // container sets this to make HMR notice edits. Unset on a host, where they do.
    watch: process.env.CHOKIDAR_USEPOLLING ? { usePolling: true } : undefined,
  },
});
