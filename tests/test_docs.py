"""The Docs section (ledger/web/docs.py, pages/docs.js, pages/_markdown.js): every sidebar page loads over HTTP, the doc
route serves top-level docs/*.md only, every link in the overview and the operating guide resolves, the glossary names
every state word, and the shown docs carry no chat voice."""
import json
import re
import shutil
import subprocess
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
        for bad in ("../README.md", "archive/x.md", "MAP.txt", "/etc/passwd", "..", "", None, "MAP.md/..", ".md", "a b.md",
                    "MAP.md\n", "TICKETS.md", "DISCIPLINES.md"):
            self.assertIsNone(docs.read(bad), bad)
        self.assertTrue(set(docs.SERVED) >= {f for _, _, f in docs.SIDEBAR if f})
        for f in docs.SERVED:
            self.assertIsNotNone(docs.read(f), f)

    def test_a_symlink_never_leads_out_of_docs(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root, outside = Path(tmp) / "docs", Path(tmp) / "outside"
            root.mkdir()
            outside.mkdir()
            (outside / "secret.md").write_text("# secret\n")
            (root / "notes.txt").write_text("not markdown\n")
            (root / "OK.md").write_text("# ok\n")
            (root / "L.md").symlink_to(outside / "secret.md")
            (root / "M.md").symlink_to(root / "notes.txt")
            allow = {"OK.md", "L.md", "M.md"}
            self.assertEqual(docs.read("OK.md", root, allow), "# ok\n")
            self.assertIsNone(docs.read("L.md", root, allow))
            self.assertIsNone(docs.read("M.md", root, allow))
            self.assertIsNone(docs.read("OK.md", root, {"L.md"}))  # not on the allowlist

    def test_sidebar_files_exist_outside_archive(self):
        for slug, title, f in docs.SIDEBAR:
            if f:
                self.assertTrue((ROOT / "docs" / f).is_file(), f)
                self.assertNotIn("/", f)

    def test_renderer_writes_no_html(self):
        for f in ("docs.js", "_markdown.js"):
            text = (ROOT / "ledger" / "web" / "pages" / f).read_text()
            self.assertNotRegex(text, r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", f)

    @unittest.skipUnless(shutil.which("node"), "no node")
    def test_every_doc_renders_and_terminates(self):
        """_markdown.js over every top-level doc in node, with a stub h(): it returns, and gives blocks (a shared regex
        state once made a bold link loop forever and hang the page)."""
        js = (ROOT / "ledger" / "web" / "pages" / "_markdown.js").read_text()
        safe = next(l for l in (ROOT / "ledger" / "web" / "pages" / "_shared.js").read_text().splitlines() if l.startswith("const safeHref"))
        prog = ("const h=(tag,attrs={},...kids)=>({tag,attrs,kids:kids.flat(Infinity)});\n" + safe + "\n" + js +
                "\nconst fs=require('fs'); const out={}; for (const f of fs.readdirSync(process.argv[1]).filter((f)=>f.endsWith('.md')))"
                " out[f]=mdRender(fs.readFileSync(process.argv[1]+'/'+f,'utf8'),{files:{'MAP.md':'map'}}).length;"
                " out['bold-link']=mdRender('**[a `b`](MAP.md)** and [c](../ledger/web/) http://x.example/y.',{files:{'MAP.md':'map'}}).length;"
                " const links=(md)=>{const acc=[];const walk=(n)=>{if(n&&n.tag==='a')acc.push(n.attrs.href);if(n&&n.kids)n.kids.forEach(walk);};"
                " mdRender(md,{files:{'MAP.md':'map'},served:['PROOF.md']}).forEach(walk);return acc;};"
                " out.hrefs={javascript:links('[x](javascript:alert(1)) [y](JavaScript:alert(1))'),data:links('[x](data:text/html,<b>x</b>)'),"
                " mixed:links('[a](vbscript:x) [b](//evil.example/x) [c](../../etc/passwd) [d](mailto:a@b)'),"
                " served:links('[p](PROOF.md) [m](MAP.md) [t](TICKETS.md)')};"
                " process.stdout.write(JSON.stringify(out));")
        r = subprocess.run(["node", "-e", prog, str(ROOT / "docs")], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out.pop("bold-link"), 1)
        hrefs = out.pop("hrefs")
        self.assertEqual(hrefs["javascript"], [])
        self.assertEqual(hrefs["data"], [])
        self.assertEqual(hrefs["mixed"], [])
        self.assertEqual(hrefs["served"], ["/docs/PROOF.md", "#docs/map", "https://github.com/kennygeiler/ai-capex-ledger/blob/main/docs/TICKETS.md"])
        for f, n in out.items():
            self.assertGreater(n, 0, f)


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


# Every top-level doc: no first or second person, no owner named as the one who wants or decides, no session talk.
# Code spans, fenced code and quoted text (a filing's words, a recorded author) are not read. Allowed: "Kenny's Data
# Emporium" (the app's name), "Kenny Geiler" (an attribution: who signed, who owns a rule), and the roman numeral I as a
# section letter or in "Annex I".
VOICE = (
    re.compile(r"\b(?:you|your|yours|yourself|You|Your)\b"),
    re.compile(r"\b(?:we|our|ours|us|We|Our|Us)\b(?!-)"),
    re.compile(r"\bI\b"),
    re.compile(r"\bKenny\b(?!'s Data Emporium| Geiler)"),
    re.compile(r"\b(?:this branch|this session|tonight|the robot)\b", re.I),
)
VOICE_ALLOW = (re.compile(r"^#+ I\. "), re.compile(r"\bAnnex I\b"), re.compile(r"\b[A-H] and I\b"))


def _prose(text: str) -> list[str]:
    """The doc's lines with fenced code, code spans and quoted text blanked, line numbers kept."""
    text = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    out = []
    for line in text.split("\n"):
        line = re.sub(r"`[^`]*`", "", line)
        line = re.sub(r'"[^"]*"', "", line)
        out.append(re.sub(r"\u201c[^\u201d]*\u201d", "", line))
    return out


def voice_hits(text: str) -> list[str]:
    hits = []
    for n, line in enumerate(_prose(text), 1):
        for rx in VOICE_ALLOW:
            line = rx.sub("", line)
        for rx in (*VOICE, *BANNED):
            m = rx.search(line)
            if m:
                hits.append(f"{n}: {line[max(0, m.start() - 50):m.end() + 40].strip()}")
                break
    return hits


class Voice(unittest.TestCase):
    def test_shown_docs_carry_no_chat_voice(self):
        for slug, _, _ in docs.SIDEBAR:
            text = docs.page(slug)["markdown"]
            for rx in BANNED:
                m = rx.search(text)
                self.assertIsNone(m, f"{slug}: {m and text[max(0, m.start() - 60):m.end() + 40]!r}")

    def test_every_doc_and_the_readme_in_product_voice(self):
        files = sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]
        found = {f.name: voice_hits(f.read_text()) for f in files}
        self.assertEqual({k: v for k, v in found.items() if v}, {})
        for slug in ("glossary", "rules"):
            self.assertEqual(voice_hits(docs.page(slug)["markdown"]), [], slug)

    def test_scan_catches_chat_voice(self):
        for s in ("Kenny wants the table", "as you asked", "We decided today", "Claude wrote the 47 mappings", "If you are an AI agent",
                  "what each stage taught us", "I want a score", "Kenny confirms each", "on this branch"):
            self.assertTrue(voice_hits(s), s)
        for s in ("Signed by Kenny Geiler", '12 by "Claude Code, for Kenny Geiler to confirm"', "a Claude subscription", "a us-gaap member",
                  "## I. Agents", "the Annex I additions", "then H and I", "Kenny's Data Emporium", "`we` in code", 'quoted "we said"'):
            self.assertFalse(voice_hits(s), s)
