// Builds the explorer (web/, React + shadcn/ui) into one self-contained file: explorer/standalone.html.
// Vite + vite-plugin-singlefile inline the JS, CSS and font; this script then inlines the data as window.__DATA__,
// so the page opens straight from disk (file://) or publishes as one page.
// Run: node scripts/build-standalone.mjs [data=data/clean/viz.json]
import { execSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const root = new URL("../", import.meta.url);
const dataPath = process.argv[2] ?? "data/clean/viz.json";
execSync("pnpm exec vite build --logLevel warn", { cwd: new URL("web/", root), stdio: "inherit" });

const app = readFileSync(new URL("web/dist/index.html", root), "utf8");
const data = JSON.stringify(JSON.parse(readFileSync(new URL(dataPath, root), "utf8")));
if (!app.includes("<!--DATA-->")) throw new Error("web/dist/index.html has no <!--DATA--> placeholder");
const html = app.replace("<!--DATA-->", () => `<script>window.__DATA__ = ${data.replace(/</g, "\\u003c")};</script>`);

mkdirSync(new URL("explorer/", root), { recursive: true });
writeFileSync(new URL("explorer/standalone.html", root), html);
console.log(`wrote explorer/standalone.html (${(html.length / 1024 / 1024).toFixed(1)} MB) from ${dataPath}`);
