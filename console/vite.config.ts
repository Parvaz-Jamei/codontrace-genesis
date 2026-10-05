import os from "node:os";
import path from "node:path";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));

function readTempC(): number | null {
  if (os.platform() !== "linux") return null;
  try {
    const raw = readFileSync("/sys/class/thermal/thermal_zone0/temp", "utf8").trim();
    const value = Number(raw);
    if (!Number.isFinite(value)) return null;
    return value > 200 ? Math.round(value / 100) / 10 : value;
  } catch {
    return null;
  }
}

function hostDev(): Plugin {
  return {
    name: "codontrace-host-dev",
    configureServer(server) {
      server.middlewares.use("/api/host", (_req, res) => {
        const cores = Math.max(1, os.cpus().length || 1);
        const load = os.platform() === "win32" ? 0 : (os.loadavg()[0] ?? 0);
        const body = {
          platform: os.platform(),
          arch: os.arch(),
          cores,
          memoryMb: Math.round(os.totalmem() / (1024 * 1024)),
          freeMb: Math.round(os.freemem() / (1024 * 1024)),
          load1: Math.round(load * 100) / 100,
          tempC: readTempC(),
          recommendedWorkers: Math.max(1, Math.min(4, cores)),
          hostname: os.hostname(),
          source: "host",
          packageVersion: "0.3.0b19",
        };
        res.setHeader("content-type", "application/json; charset=utf-8");
        res.end(JSON.stringify(body));
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), hostDev()],
  resolve: { alias: { "@": path.resolve(root, "src") } },
  build: {
    outDir: path.resolve(root, "../src/codontrace/console/static"),
    emptyOutDir: true,
    sourcemap: false,
  },
});
