// ── Docs: the repository's own docs/*.md and two pages written from code (ledger/web/docs.py), with a sidebar. ─────────
const SVG_NS = 'http://www.w3.org/2000/svg';
const svg = (tag, attrs = {}, ...kids) => {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) el.setAttribute(k, v);
  for (const c of kids.flat()) if (c != null) el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return el;
};

// A linear `flowchart` in mermaid's own syntax (nodes `id["Label<br/>sub"]`, edges `a --> b`, `click id "#route"`) drawn
// as boxes and arrows. Anything else (a branch, a back edge) returns null and the block shows as code.
function flowDiagram(src) {
  const lines = src.split('\n').map((l) => l.trim()).filter(Boolean);
  if (!/^flowchart\s+(LR|TD|TB)$/.test(lines[0] || '')) return null;
  const nodes = [], label = {}, link = {}, edges = [];
  const node = (tok) => {
    const m = tok.trim().match(/^([A-Za-z_][\w]*)(?:\["([^"]*)"\])?$/);
    if (!m) return null;
    if (!(m[1] in label)) { nodes.push(m[1]); label[m[1]] = m[1]; }
    if (m[2] != null) label[m[1]] = m[2];
    return m[1];
  };
  for (const l of lines.slice(1)) {
    const c = l.match(/^click\s+(\w+)\s+"([^"]+)"/);
    if (c) { link[c[1]] = c[2]; continue; }
    const parts = l.split('-->');
    const ids = parts.map(node);
    if (ids.some((x) => !x)) return null;
    for (let k = 1; k < ids.length; k++) edges.push([ids[k - 1], ids[k]]);
  }
  if (!nodes.length || edges.some(([a, b]) => nodes.indexOf(b) !== nodes.indexOf(a) + 1)) return null;
  const narrow = matchMedia('(max-width: 700px)').matches;
  const W = 132, H = 64, G = 34, n = nodes.length;
  const pos = (k) => (narrow ? [0, k * (H + G)] : [k * (W + G), 0]);
  const vw = narrow ? W : n * W + (n - 1) * G, vh = narrow ? n * H + (n - 1) * G : H;
  const root = svg('svg', {viewBox: `-2 -2 ${vw + 4} ${vh + 4}`, class: 'flow', role: 'img', 'aria-label': nodes.map((id) => label[id].split('<br/>')[0]).join(', then ')},
    svg('defs', {}, svg('marker', {id: 'flow-arrow', viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse'}, svg('path', {d: 'M0,0 L10,5 L0,10 z', class: 'flow-head'}))));
  for (const [a, b] of edges) {
    const [ax, ay] = pos(nodes.indexOf(a)), [bx, by] = pos(nodes.indexOf(b));
    root.append(narrow ? svg('line', {x1: ax + W / 2, y1: ay + H, x2: bx + W / 2, y2: by - 2, class: 'flow-edge', 'marker-end': 'url(#flow-arrow)'})
      : svg('line', {x1: ax + W, y1: ay + H / 2, x2: bx - 2, y2: by + H / 2, class: 'flow-edge', 'marker-end': 'url(#flow-arrow)'}));
  }
  nodes.forEach((id, k) => {
    const [x, y] = pos(k);
    const [main, ...sub] = label[id].split('<br/>');
    const g = svg('g', {}, svg('rect', {x, y, width: W, height: H, rx: 6, class: 'flow-box'}),
      svg('text', {x: x + W / 2, y: y + (sub.length ? H / 2 - 4 : H / 2 + 5), 'text-anchor': 'middle', class: 'flow-label'}, main),
      sub.length ? svg('text', {x: x + W / 2, y: y + H / 2 + 14, 'text-anchor': 'middle', class: 'flow-sub'}, sub.join(' ')) : null);
    const href = link[id] && safeHref(link[id]);
    root.append(href ? svg('a', {href}, g) : g);
  });
  return h('div', {class: 'flow-wrap'}, root);
}

async function docsPage(view, arg) {
  const idx = await api('/api/v1/docs');
  const slug = idx.pages.some((p) => p.slug === arg) ? arg : idx.pages[0].slug;
  const pg = await api(`/api/v1/docs/${encodeURIComponent(slug)}`);
  const side = h('nav', {class: 'viewlist', 'aria-label': 'Docs pages'}, idx.pages.map((p) =>
    h('a', {href: `#docs/${p.slug}`, class: 'viewrow' + (p.slug === slug ? ' on' : ''), 'aria-current': p.slug === slug ? 'page' : null}, p.title)));
  const source = h('p', {class: 'text-secondary small mt-4'}, pg.file ? ['Source: ', h('a', {href: `/docs/${pg.file.replace(/^docs\//, '')}`}, pg.file)] : 'Written from code on every request');
  view.append(h('div', {class: 'views docs'}, h('div', {}, side), h('article', {class: 'md'}, mdRender(pg.markdown, {files: idx.files, served: idx.served, diagram: flowDiagram}), source)));
}
