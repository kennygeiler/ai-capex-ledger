// Inlines a page's style.css, app.js and its data into <dir>/standalone.html,
// so it opens straight from disk (file://) or publishes as one page.
// Run: node scripts/build-standalone.mjs [dir=explorer] [data=data/clean/viz.json]
import { readFileSync, writeFileSync } from "node:fs";

const root = new URL("../", import.meta.url);
const read = (p) => readFileSync(new URL(p, root), "utf8");
const dir = process.argv[2] ?? "explorer";
const dataPath = process.argv[3] ?? "data/clean/viz.json";

let html = read(`${dir}/index.html`);
const css = read(`${dir}/style.css`);
const js = read(`${dir}/app.js`);
const data = JSON.stringify(JSON.parse(read(dataPath)));

html = html
  .replace('<link rel="stylesheet" href="style.css">', () => `<style>\n${css}\n</style>`)
  .replace('<script type="module" src="app.js"></script>', () =>
    `<script>window.__DATA__ = ${data.replace(/</g, "\\u003c")};</script>\n<script type="module">\n${js}\n</script>`);

writeFileSync(new URL(`${dir}/standalone.html`, root), html);
console.log(`wrote ${dir}/standalone.html (${(html.length / 1024).toFixed(0)} KB) from ${dataPath}`);
