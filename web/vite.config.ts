import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { viteSingleFile } from "vite-plugin-singlefile"
import fs from "node:fs"
import type { Plugin } from "vite"

// Dev only: serve ../data/clean/* at /data/clean/* so the app can fetch viz.json.
const serveData = (): Plugin => ({
  name: "serve-data",
  configureServer(server) {
    server.middlewares.use("/data/clean", (req, res, next) => {
      const f = path.resolve(import.meta.dirname, "../data/clean", "." + (req.url ?? "").split("?")[0])
      if (!fs.existsSync(f)) return next()
      res.setHeader("Content-Type", "application/json")
      fs.createReadStream(f).pipe(res)
    })
    // Lets the built single file be checked in a browser that can't open large local files.
    server.middlewares.use("/__standalone", (_req, res) => {
      res.setHeader("Content-Type", "text/html")
      fs.createReadStream(path.resolve(import.meta.dirname, "../explorer/standalone.html")).pipe(res)
    })
  },
})

// Dev: the app fetches ../data/clean/viz.json through /data. Build: one self-contained HTML file
// (scripts/build-standalone.mjs injects the data as window.__DATA__).
export default defineConfig({
  plugins: [react(), tailwindcss(), viteSingleFile(), serveData()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  server: { port: 3600, fs: { allow: [".."] } },
  build: { outDir: "dist", chunkSizeWarningLimit: 4000 },
})
