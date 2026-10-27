// Inlines style.css, data/sample.json and app.js into prototype/standalone.html,
// so the prototype opens straight from disk (file://) or publishes as one page.
// Run: node scripts/build-standalone.mjs [path/to/data.json]
import { readFileSync, writeFileSync } from "node:fs";

const root = new URL("../", import.meta.url);
const read = (p) => readFileSync(new URL(p, root), "utf8");
const dataPath = process.argv[2] ?? "data/sample.json";

let html = read("prototype/index.html");
const css = read("prototype/style.css");
const js = read("prototype/app.js");
const data = JSON.stringify(JSON.parse(read(dataPath)));

html = html
  .replace('<link rel="stylesheet" href="style.css">', () => `<style>\n${css}\n</style>`)
  .replace('<script type="module" src="app.js"></script>', () =>
    `<script>window.__DATA__ = ${data.replace(/</g, "\\u003c")};</script>\n<script type="module">\n${js}\n</script>`);

writeFileSync(new URL("prototype/standalone.html", root), html);
console.log(`wrote prototype/standalone.html (${(html.length / 1024).toFixed(0)} KB) from ${dataPath}`);
