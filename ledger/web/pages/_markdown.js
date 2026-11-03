// ── A small markdown renderer for the Docs section (ledger/web/docs.py serves the text). It builds DOM nodes with h() and
// text nodes only, never an HTML string, so text from a doc is never parsed as HTML. Supports headings, paragraphs, lists (nested
// by indent), tables, fenced code, block quotes, inline code, bold and links. A ```mermaid block goes to opts.diagram,
// which returns a node or null (then it shows as code). Horizontal rules are dropped. ──────────────────────────────────
const REPO_URL = 'https://github.com/kennygeiler/ai-capex-ledger/blob/main/';

// a doc's link target as the app opens it: an app route, a doc page, a doc's raw text, the repository on GitHub, or a web address
function mdHref(href, files) {
  if (/^https?:\/\//i.test(href)) return {href, ext: true};
  if (/^#[a-z]/.test(href)) return {href};
  if (href.startsWith('#') || href.startsWith('mailto:')) return null;
  let p = href.split('#')[0];
  if (!p) return null;
  const repo = p.startsWith('../') ? p.slice(3) : p.startsWith('/') ? p.slice(1) : 'docs/' + p;  // a doc's relative link is relative to docs/
  const doc = repo.match(/^docs\/([A-Za-z0-9_-]+\.md)$/);
  if (doc) return files[doc[1]] ? {href: '#docs/' + files[doc[1]]} : {href: '/docs/' + doc[1]};
  return {href: REPO_URL + repo.replace(/\/$/, ''), ext: true};
}

const MD_INLINE = /`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)\s]+)\)|(https?:\/\/[^\s)<>|]+[^\s)<>|.,;:])/g;

function mdInline(text, files) {
  const out = [];
  const rx = new RegExp(MD_INLINE.source, 'g');  // one per call: labels recurse, and a shared lastIndex would restart the outer scan
  let last = 0, m;
  while ((m = rx.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1] != null) out.push(h('code', {}, m[1]));
    else if (m[2] != null) out.push(h('b', {}, mdInline(m[2], files)));
    else {
      const label = m[3] != null ? m[3] : m[5];
      const t = mdHref(m[3] != null ? m[4] : m[5], files);
      const kids = m[3] != null ? mdInline(label, files) : [label];
      const href = t && (/^\/docs\/[A-Za-z0-9_-]+\.md$/.test(t.href) ? t.href : safeHref(t.href));  // a doc's raw text, or what the shared guard allows
      out.push(href ? h('a', {href, target: t.ext ? '_blank' : null, rel: t.ext ? 'noopener' : null}, kids) : h('span', {}, kids));
    }
    last = rx.lastIndex;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

function mdCells(line) {
  const cells = [];
  let cur = '';
  const s = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  for (let i = 0; i < s.length; i++) {
    if (s[i] === '\\' && s[i + 1] === '|') { cur += '|'; i++; } else if (s[i] === '|') { cells.push(cur.trim()); cur = ''; } else cur += s[i];
  }
  cells.push(cur.trim());
  return cells;
}

const MD_ITEM = /^(\s*)([-*]|\d+\.)\s+(.*)$/;

function mdList(lines, files) {
  // lines: [{indent, ordered, text}] -> nested lists by indent
  const root = {kids: [], indent: -1};
  const stack = [root];
  for (const it of lines) {
    while (stack.length > 1 && it.indent <= stack[stack.length - 1].indent) stack.pop();
    const parent = stack[stack.length - 1];
    const node = {text: it.text, ordered: it.ordered, indent: it.indent, kids: []};
    parent.kids.push(node);
    stack.push(node);
  }
  const build = (nodes) => h(nodes[0].ordered ? 'ol' : 'ul', {}, nodes.map((n) => h('li', {}, mdInline(n.text, files), n.kids.length ? build(n.kids) : '')));
  return build(root.kids);
}

function mdRender(text, opts = {}) {
  const files = opts.files || {};
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const fence = line.match(/^```\s*([\w-]*)/);
    if (fence) {
      const body = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) body.push(lines[i++]);
      i++;
      const node = fence[1] === 'mermaid' && opts.diagram ? opts.diagram(body.join('\n')) : null;
      out.push(node || h('pre', {class: 'raw'}, h('code', {}, body.join('\n'))));
      continue;
    }
    const hd = line.match(/^(#{1,4})\s+(.*)$/);
    if (hd) {
      const n = hd[1].length;
      out.push(h('h' + n, {class: n === 1 ? 'page-title mb-3' : null}, mdInline(hd[2], files)));
      i++;
      continue;
    }
    if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {
      const head = mdCells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(mdCells(lines[i++]));
      out.push(h('div', {class: 'scroll'}, h('table', {class: 'table table-sm'},
        h('thead', {}, h('tr', {}, head.map((c) => h('th', {}, mdInline(c, files))))),
        h('tbody', {}, rows.map((r) => h('tr', {}, head.map((_, j) => h('td', {}, mdInline(r[j] || '', files)))))))));
      continue;
    }
    if (MD_ITEM.test(line)) {
      const items = [];
      while (i < lines.length) {
        const m = lines[i].match(MD_ITEM);
        if (m) { items.push({indent: m[1].length, ordered: /\d/.test(m[2]), text: m[3]}); i++; continue; }
        if (/^\s+\S/.test(lines[i]) && items.length) { items[items.length - 1].text += ' ' + lines[i].trim(); i++; continue; }
        break;
      }
      out.push(mdList(items, files));
      continue;
    }
    if (/^>\s?/.test(line)) {
      const q = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) q.push(lines[i++].replace(/^>\s?/, ''));
      out.push(h('blockquote', {class: 'text-secondary'}, mdInline(q.join(' '), files)));
      continue;
    }
    if (/^\s*(---+|\*\*\*+)\s*$/.test(line) || !line.trim()) { i++; continue; }
    const para = [lines[i++].trim()];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|>|\s*\|)/.test(lines[i]) && !MD_ITEM.test(lines[i])) para.push(lines[i++].trim());
    out.push(h('p', {}, mdInline(para.join(' '), files)));
  }
  return out;
}
