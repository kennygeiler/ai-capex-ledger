"""The Docs section (ledger/web/docs.py, pages/docs.js, pages/_markdown.js): every sidebar page loads over HTTP, the doc
route serves top-level docs/*.md only, every link in the overview and the operating guide resolves, the glossary names
every state word, and the shown docs carry no chat voice."""
import json
import re
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from ledger.core import states, store
from ledger.web import app, docs

ROOT = store.ROOT
LINK = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
CLICK = re.compile(r'^\s*click\s+\w+\s+"([^"]+)"', re.M)
# Chat voice: who wants what, session history, notes to an agent, a model as the actor. Attribution facts ("Signed by
# Kenny Geiler", a quoted decision author) are allowed.
BANNED = (
    re.compile(r"\bKenny (wants|wanted|asked|said|says|decided|thinks|prefers|likes)\b"),
    re.compile(r"\byou asked\b", re.I),
    re.compile(r"\bwe decided\b", re.I),
    re.compile(r"\bas discussed\b", re.I),
    re.compile(r"\bthe robot\b", re.I),
    re.compile(r"\b(tonight|this session|earlier today)\b", re.I),
    re.compile(r"\bnote to (the |an )?(agent|AI|Claude)\b", re.I),
    re.compile(r"\bIf you are an AI agent\b"),
    re.compile(r"(?<![\"'`])\bClaude(?: Code| Fable[\w .]*?| Opus[\w .]*?)? (wrote|did|added|decided|built|made|changed|ran|proposed|found|fixed|thinks)\b"),
)


def _server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = _server()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=30) as r:
                return r.status, r.headers.get("Content-Type"), r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type"), e.read().decode()

    def test_every_sidebar_page_loads(self):
        code, _, body = self.get("/api/v1/docs")
        self.assertEqual(code, 200)
        idx = json.loads(body)
        self.assertEqual([p["slug"] for p in idx["pages"]], [s for s, _, _ in docs.SIDEBAR])
        for p in idx["pages"]:
            code, _, body = self.get(f"/api/v1/docs/{p['slug']}")
            self.assertEqual(code, 200, p["slug"])
            pg = json.loads(body)
            self.assertTrue(pg["markdown"].startswith("# "), p["slug"])
            if p["file"]:
                self.assertEqual(pg["markdown"], (ROOT / "docs" / p["file"]).read_text(encoding="utf-8"))

    def test_the_pages_are_served(self):
        for f in ("docs.js", "_markdown.js"):
            code, kind, _ = self.get(f"/pages/{f}")
            self.assertEqual((code, kind.split(";")[0]), (200, "application/javascript"), f)
        _, _, html = self.get("/")
        self.assertIn('href="#docs" data-nav="docs">Docs</a>', html)
        self.assertLess(html.index('data-nav="gaps"'), html.index('data-nav="docs"'))

    def test_unknown_page_is_404(self):
        self.assertEqual(self.get("/api/v1/docs/nope")[0], 404)
        self.assertEqual(self.get("/api/v1/docs/..%2FREADME")[0], 404)
        self.assertEqual(self.get("/api/v1/docs/map/extra")[0], 404)

    def test_doc_route_serves_top_level_md_only(self):
        code, kind, body = self.get("/docs/MAP.md")
        self.assertEqual((code, kind.split(";")[0]), (200, "text/plain"))
        self.assertEqual(body, (ROOT / "docs" / "MAP.md").read_text(encoding="utf-8"))
        archived = next((ROOT / "docs" / "archive").glob("*.md"), None)
        refused = ["/docs/../README.md", "/docs/..%2FREADME.md", "/docs/%2e%2e/README.md", "/docs/..%2F..%2Fpyproject.toml",
                   "/docs/MAP.txt", "/docs/MAP", "/docs/", "/docs/.env", "/docs/NOPE.md", "/docs/%2Fetc%2Fpasswd"]
        if archived:
            refused += [f"/docs/archive/{archived.name}", f"/docs/archive%2F{archived.name}"]
        for path in refused:
            code, _, body = self.get(path)
            self.assertEqual(code, 404, path)
            self.assertNotIn("[project]", body)


class Read(unittest.TestCase):
    def test_read_whitelist(self):
        self.assertIsNotNone(docs.read("MAP.md"))
        for bad in ("../README.md", "archive/x.md", "MAP.txt", "/etc/passwd", "..", "", None, "MAP.md/..", ".md", "a b.md"):
            self.assertIsNone(docs.read(bad), bad)

    def test_sidebar_files_exist_outside_archive(self):
        for slug, title, f in docs.SIDEBAR:
            if f:
                self.assertTrue((ROOT / "docs" / f).is_file(), f)
                self.assertNotIn("/", f)

    def test_renderer_writes_no_html(self):
        for f in ("docs.js", "_markdown.js"):
            text = (ROOT / "ledger" / "web" / "pages" / f).read_text()
            self.assertNotRegex(text, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", f)


def _resolves(href: str) -> str | None:
    """None when the link resolves, else why not. Links are relative to docs/ (GitHub's rule, and _markdown.js mdHref)."""
    if href.startswith("#"):
        page, _, arg = href[1:].partition("?")[0].partition("/")
        if page not in docs.APP_PAGES:
            return f"no app page {page!r}"
        if page == "docs" and arg and arg not in docs.SLUGS:
            return f"no docs page {arg!r}"
        return None
    if re.match(r"https?://", href):
        return None if href.startswith("https://github.com/kennygeiler/ai-capex-ledger") else "external link"
    path = href.split("#")[0]
    target = (ROOT / path[3:]) if path.startswith("../") else (ROOT / "docs" / path)
    return None if target.exists() else f"no file {target.relative_to(ROOT)}"


class Links(unittest.TestCase):
    def test_overview_and_operations_links_resolve(self):
        for f in ("OVERVIEW.md", "OPERATIONS.md"):
            text = (ROOT / "docs" / f).read_text()
            links = LINK.findall(text) + CLICK.findall(text)
            self.assertTrue(links, f)
            for href in links:
                self.assertIsNone(_resolves(href), f"{f}: {href}")

    def test_overview_boxes_link_to_pages(self):
        text = (ROOT / "docs" / "OVERVIEW.md").read_text()
        clicks = CLICK.findall(text)
        self.assertEqual(len(clicks), 6)
        for pkg in ("ingest", "extract", "checks", "review", "release", "web"):
            self.assertIn(f"(../ledger/{pkg}/)", text)
            self.assertIn(f"`ledger/{pkg}/`", (ROOT / "docs" / "MAP.md").read_text())

    def test_readme_links_resolve(self):
        text = (ROOT / "README.md").read_text()
        for href in LINK.findall(text):
            self.assertTrue((ROOT / href.split("#")[0]).exists(), href)


class Glossary(unittest.TestCase):
    def test_every_state_word_is_defined(self):
        g = docs.glossary()
        for w in states.words():
            self.assertIn(f"| {w} |", g, w)

    def test_every_nav_page_is_defined(self):
        g = docs.glossary()
        for w in docs.APP_PAGES.values():
            self.assertIn(f"| {w} |", g, w)

    def test_rules_page_lists_every_rule(self):
        from ledger.checks.rules import load
        page = docs.rules_page()
        for r in load():
            self.assertIn(f"`{r['id']}`", page)


class Voice(unittest.TestCase):
    def test_shown_docs_carry_no_chat_voice(self):
        for slug, _, _ in docs.SIDEBAR:
            text = docs.page(slug)["markdown"]
            for rx in BANNED:
                m = rx.search(text)
                self.assertIsNone(m, f"{slug}: {m and text[max(0, m.start() - 60):m.end() + 40]!r}")
        readme = (ROOT / "README.md").read_text()
        for rx in BANNED:
            self.assertIsNone(rx.search(readme), rx.pattern)

    def test_scan_catches_chat_voice(self):
        for s in ("Kenny wants the table", "as you asked", "We decided today", "Claude wrote the 47 mappings", "If you are an AI agent"):
            self.assertTrue(any(rx.search(s) for rx in BANNED), s)
        for s in ("Signed by Kenny Geiler", '12 by "Claude Code, for Kenny Geiler to confirm"', "a Claude subscription"):
            self.assertFalse(any(rx.search(s) for rx in BANNED), s)
