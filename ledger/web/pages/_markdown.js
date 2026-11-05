// ── A small markdown renderer for the Docs section (ledger/web/docs.py serves the text). It builds DOM nodes
// with h() and text nodes only, never an HTML string, so text from a doc is never parsed as HTML. Supports
// headings, paragraphs, lists (nested by indent), tables, fenced code, block quotes, inline code, bold and links.
// A ```mermaid block goes to opts.diagram, which returns a node or null (then it shows as code). Horizontal rules
// are dropped. Lines here are wrapped at 120 characters except a few regular expressions and h() calls. ──────
const REPO_URL = 'https://github.com/kennygeiler/ai-capex-ledger/blob/main/';

// a doc's link target as the app opens it: an app route, a doc page, a served doc's raw text, the repository on
// GitHub, or a web address. Any other scheme (javascript:, data:, mailto:) is no link.
// a heading's anchor: its words, lower case, joined by hyphens ("The hosted copy" -> the-hosted-copy)
const mdSlug = (t) => String(t).toLowerCase().replace(/[`*]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
// a doc's reference written as code, `docs/MAP.md` (report #12): rendered as the link a [label](MAP.md) link would be
const MD_DOC_REF = /^(?:\.\.\/)?docs\/[A-Za-z0-9_/-]+\.md$/;
function mdHref(href, ctx) {
  if (/^https?:\/\//i.test(href)) return {href, ext: true};
  if (ctx.anchors && ctx.page && /^#[a-z0-9-]+$/.test(href) && ctx.anchors.has(href.slice(1))) return {href: `#docs/${ctx.page}?at=${href.slice(1)}`};  // a heading on this page: stays on it
  if (/^#[a-z]/.test(href)) return {href};
  if (href.startsWith('#') || /^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith('//')) return null;
  const p = href.split('#')[0];
  if (!p) return null;
  // a doc's relative link is relative to docs/
  const repo = p.startsWith('../') ? p.slice(3) : p.startsWith('/') ? p.slice(1) : 'docs/' + p;
  if (repo.split('/').includes('..')) return null;
  const doc = repo.match(/^docs\/([A-Za-z0-9_-]+\.md)$/);
  if (doc && ctx.files[doc[1]]) return {href: '#docs/' + ctx.files[doc[1]]};
  if (doc && ctx.served.includes(doc[1])) return {href: '/docs/' + doc[1]};
  return {href: REPO_URL + repo.replace(/\/$/, ''), ext: true};
}

const MD_INLINE = /`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)\s]+)\)|(https?:\/\/[^\s)<>|]+[^\s)<>|.,;:])/g;

function mdInline(text, ctx) {
  const out = [];
  const rx = new RegExp(MD_INLINE.source, 'g');  // one per call: labels recurse, and a shared lastIndex would restart the outer scan
  let last = 0, m;
  while ((m = rx.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1] != null) {
      const t = MD_DOC_REF.test(m[1]) ? mdHref('/' + m[1].replace(/^\.\.\//, ''), ctx) : null;
      const ref = t && (/^\/docs\/[A-Za-z0-9_-]+\.md$/.test(t.href) ? t.href : safeHref(t.href));
      out.push(ref ? h('a', {href: ref, target: t.ext ? '_blank' : null, rel: t.ext ? 'noopener' : null}, h('code', {}, m[1])) : h('code', {}, m[1]));
    }
    else if (m[2] != null) out.push(h('b', {}, mdInline(m[2], ctx)));
    else {
      const label = m[3] != null ? m[3] : m[5];
      const t = mdHref(m[3] != null ? m[4] : m[5], ctx);
      const kids = m[3] != null ? mdInline(label, ctx) : [label];
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

function mdList(lines, ctx) {
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
  const build = (nodes) => h(nodes[0].ordered ? 'ol' : 'ul', {}, nodes.map((n) => h('li', {}, mdInline(n.text, ctx), n.kids.length ? build(n.kids) : '')));
  return build(root.kids);
}

function mdRender(text, opts = {}) {
  const anchors = new Set(text.split('\n').map((l) => l.match(/^#{1,4}\s+(.*)$/)).filter(Boolean).map((m) => mdSlug(m[1])));
  const ctx = {files: opts.files || {}, served: opts.served || [], page: opts.page || null, anchors};
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
      out.push(h('h' + n, {class: n === 1 ? 'page-title mb-3' : null, id: n > 1 ? mdSlug(hd[2]) : null, 'data-land': n > 1 && opts.at === mdSlug(hd[2]) ? '' : null}, mdInline(hd[2], ctx)));  // ?at=<anchor> lands here (_router.js)
      i++;
      continue;
    }
    if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {
      const head = mdCells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(mdCells(lines[i++]));
      out.push(h('div', {class: 'scroll'}, h('table', {class: 'table table-sm'},
        h('thead', {}, h('tr', {}, head.map((c) => h('th', {}, mdInline(c, ctx))))),
        h('tbody', {}, rows.map((r) => h('tr', {}, head.map((_, j) => h('td', {}, mdInline(r[j] || '', ctx)))))))));
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
      out.push(mdList(items, ctx));
      continue;
    }
    if (/^>\s?/.test(line)) {
      const q = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) q.push(lines[i++].replace(/^>\s?/, ''));
      out.push(h('blockquote', {class: 'text-secondary'}, mdInline(q.join(' '), ctx)));
      continue;
    }
    if (/^\s*(---+|\*\*\*+)\s*$/.test(line) || !line.trim()) { i++; continue; }
    const para = [lines[i++].trim()];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|>|\s*\|)/.test(lines[i]) && !MD_ITEM.test(lines[i])) para.push(lines[i++].trim());
    out.push(h('p', {}, mdInline(para.join(' '), ctx)));
  }
  return out;
}
