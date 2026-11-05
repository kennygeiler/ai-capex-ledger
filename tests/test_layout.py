"""Layout measured in Chrome (Playwright) against the real app on the working database, at 1600 and 1280 wide. Skipped
without Chrome or the database.

F-BF9: the hand check's exact-dollar line ("In thousands · $9,320,000") overflowed its 9.5rem value column and was cut by the
crop beside it ("$9,320,00"). F-BF8: Docs code blocks drew their text in the same colour as their background.
V3-V8 (docs/ux-visual/problems.md, measured in docs/ux-visual/verification/V3-V8.md): the page head band, the Proof board's
first screen, Reconcile's rows and jumps, Dataset paging.
V9-V23 (measured in docs/ux-visual/verification/V9-V23.md): content in its column, empty columns, the navbar at 1280, Rules
length, filter marks, colour by state."""
import os
import re
import shutil
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from ledger.core import store

CHROME = Path("/Applications/Google Chrome.app").exists() or shutil.which("google-chrome")
WIDTHS = (1600, 1280)


@unittest.skipUnless(CHROME and store.DEFAULT_DB.exists() and not os.environ.get("LEDGER_SKIP_DB"), "no Chrome or no database")
class Layout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ledger.web import app
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}/"
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(channel="chrome")

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def page(self, width, hash_, height=1000):
        pg = self.browser.new_page(viewport={"width": width, "height": height})
        self.addCleanup(pg.close)
        pg.goto(self.base + "#" + hash_)
        return pg

    def test_hand_check_value_cell_never_clips_the_exact_dollars(self):
        from ledger.review import gold
        docs, _ = gold.load_checked()
        for t in sorted(docs):
            for w in WIDTHS:
                with self.subTest(company=t, width=w):
                    pg = self.page(w, f"proof?gold={t}")
                    pg.wait_for_selector("table.gold tr[data-item]", timeout=60000)
                    exact = pg.eval_on_selector_all("table.gold td.num .gold-exact", "es => es.length")
                    spill = pg.eval_on_selector_all("table.gold td.num", """cells => cells.flatMap((td) => {
                        const box = td.getBoundingClientRect(), pad = parseFloat(getComputedStyle(td).paddingRight) || 0;
                        return [...td.querySelectorAll('div')].filter((d) => d.scrollWidth > d.clientWidth + 1 || d.getBoundingClientRect().right > box.right - pad + 1)
                          .map((d) => d.textContent + ' over by ' + Math.round(Math.max(d.scrollWidth - d.clientWidth, d.getBoundingClientRect().right - (box.right - pad))) + 'px');
                    })""")
                    self.assertEqual(spill, [])
                    if t == "APLD":
                        self.assertGreater(exact, 0)  # APLD's figures are in thousands: the exact line is drawn and measured

    def test_docs_code_blocks_are_readable(self):
        for w in WIDTHS:
            with self.subTest(width=w):
                pg = self.page(w, "docs/handoff")
                pg.wait_for_selector(".md pre.raw code", timeout=60000)
                ratio = pg.eval_on_selector(".md pre.raw", """pre => {
                    const lum = (c) => { const [r, g, b] = c.match(/[\\d.]+/g).slice(0, 3).map(Number).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
                    const fg = lum(getComputedStyle(pre.querySelector('code')).color), bg = lum(getComputedStyle(pre).backgroundColor);
                    return (Math.max(fg, bg) + 0.05) / (Math.min(fg, bg) + 0.05);
                }""")
                self.assertGreaterEqual(ratio, 4.5)
                self.assertIn("uv sync", pg.text_content(".md pre.raw"))
                self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth - window.innerWidth"), 0)

    def test_page_head_band(self):
        """V5: navbar → scope line at least 12 px, scope line → H1 at most 24 px, H1 top at most 110 px, one left edge."""
        for hash_ in ("proof", "proof/APLD", "reconcile", "gaps"):
            with self.subTest(page=hash_):
                pg = self.page(1600, hash_)
                pg.wait_for_selector("main h1.page-title", timeout=60000)
                pg.wait_for_selector("#scopeline a", timeout=60000)
                m = pg.evaluate("""() => { const n = document.querySelector('header.navbar').getBoundingClientRect(), s = document.querySelector('#scopeline a').getBoundingClientRect(),
                    t = document.querySelector('main h1.page-title').getBoundingClientRect(); return {gap1: s.top - n.bottom, gap2: t.top - s.bottom, top: t.top, dx: Math.abs(t.left - s.left)}; }""")
                self.assertGreaterEqual(m["gap1"], 12)
                self.assertLessEqual(m["gap2"], 24)
                self.assertLessEqual(m["top"], 110)
                self.assertLessEqual(m["dx"], 1)

    def test_proof_board_first_screen(self):
        """V5/V6: at 1280×800 all six company rows and the parts sub-header are above the fold; the headline is at least 20 px."""
        pg = self.page(1280, "proof", height=800)
        pg.wait_for_selector("table.proof-board tbody tr", timeout=60000)
        m = pg.evaluate("""() => { const rows = [...document.querySelectorAll('table.proof-board tbody tr')];
            return {n: rows.length, last: rows[rows.length - 1].getBoundingClientRect().bottom, legend: document.querySelector('tr.proof-legend').getBoundingClientRect().bottom,
              fs: parseFloat(getComputedStyle(document.querySelector('.proof-headline')).fontSize),
              parts: [...document.querySelectorAll('td.stage')].map((td) => td.querySelectorAll('span.part').length)}; }""")
        self.assertLessEqual(m["last"], 800)
        self.assertLessEqual(m["legend"], 800)
        self.assertGreaterEqual(m["fs"], 20)
        self.assertEqual(set(m["parts"]), {4})  # every stage cell: the same four parts

    def test_reconcile_rows_and_jumps(self):
        """V4/V8: collapsed rows at most 44 px; ticking a box moves no row; opening a row moves no header more than 1 px."""
        for w in WIDTHS:
            with self.subTest(width=w):
                pg = self.page(w, "reconcile")
                pg.wait_for_selector("table.rec tr.item", timeout=60000)
                m = pg.evaluate("""async () => { const hs = [...document.querySelectorAll('tr.item')].map((r) => r.getBoundingClientRect().height);
                    const cb = document.querySelector('tr.item input[type=checkbox]'); let moved = 0;
                    if (cb) { const tr = cb.closest('tr'), y0 = tr.getBoundingClientRect().top; cb.click(); await new Promise((r) => setTimeout(r, 300)); moved = Math.abs(tr.getBoundingClientRect().top - y0); cb.click(); }
                    let worst = 0;
                    for (const tbl of document.querySelectorAll('table.rec')) { const tr = tbl.querySelector('tr.item'); if (!tr) continue;
                      const xs = () => [...tbl.querySelectorAll(':scope > thead th')].map((t) => t.getBoundingClientRect().left); const a = xs(); tr.click();
                      await new Promise((r) => setTimeout(r, 200)); worst = Math.max(worst, ...xs().map((x, i) => Math.abs(x - a[i]))); tr.click(); }
                    return {maxH: Math.max(...hs), moved, worst}; }""")
                self.assertLessEqual(m["maxH"], 44.5)
                self.assertLessEqual(m["moved"], 0.5)
                self.assertLessEqual(m["worst"], 1)

    def test_dataset_rows_are_paged(self):
        """V4: Dataset Rows draws at most 100 rows with a pager, and its header row stays on screen."""
        pg = self.page(1600, "data?list=taxonomy")
        pg.wait_for_selector("main table tbody tr", timeout=60000)
        self.assertLessEqual(pg.eval_on_selector_all("main table tbody tr", "rs => rs.length"), 100)
        self.assertTrue(pg.query_selector(".pager"))
        self.assertLessEqual(pg.evaluate("document.documentElement.scrollHeight / innerHeight"), 3)

    def test_a_slow_page_never_draws_into_the_next(self):
        """F-VS4: Release still loading when the reader moves to Known gaps: the checklist never lands on the Known gaps page."""
        pg = self.browser.new_page(viewport={"width": 1600, "height": 1000})
        self.addCleanup(pg.close)
        # the checklist answers 2.5 s late (in the page, so the test thread is free to move on meanwhile)
        pg.add_init_script("""const f0 = window.fetch; window.fetch = (u, o) => String(u).includes('/api/v1/release/checklist')
            ? new Promise((r) => setTimeout(r, 2500)).then(() => f0(u, o)).finally(() => setTimeout(() => { window.__released = 1; }, 50)) : f0(u, o);""")
        pg.goto(self.base + "#release")
        pg.wait_for_timeout(300)
        pg.evaluate("location.hash = 'gaps'")
        pg.wait_for_selector("main h1.page-title", timeout=60000)
        pg.wait_for_function("window.__released", timeout=60000)  # the release request has answered and its page has run on
        pg.wait_for_timeout(1000)
        titles = pg.eval_on_selector_all("main h1.page-title", "hs => hs.map((x) => x.textContent)")
        self.assertEqual(titles, ["Known gaps"])
        self.assertNotIn("required checks pass", pg.text_content("main"))
    def test_hand_check_tables_are_measured_after_their_await(self):
        """Review risk 1: the hand check and failure-type tables are drawn after the router's skin(); their wrappers still get
        .fit or .wide, and the hand check's header stays on screen when the page scrolls past its top."""
        pg = self.page(1600, "proof?gold=APLD")
        pg.wait_for_selector("table.gold tr[data-item]", timeout=60000)
        pg.wait_for_timeout(500)
        self.assertEqual(pg.evaluate("[...document.querySelectorAll('#gold .table-responsive, main .table-responsive')].filter((w) => !w.classList.contains('fit') && !w.classList.contains('wide')).length"), 0)
        top = pg.evaluate("""async () => { const t = document.querySelector('table.gold'); window.scrollTo(0, t.getBoundingClientRect().top + scrollY + 600);
            await new Promise((r) => setTimeout(r, 200)); return t.querySelector('thead th').getBoundingClientRect().top; }""")
        self.assertLessEqual(abs(top), 1)

    def test_pager_keeps_keyboard_focus(self):
        """Review risk 2: Next and Previous are updated in place, so focus stays on the pager."""
        pg = self.page(1600, "data?list=taxonomy")
        pg.wait_for_selector(".pager button", timeout=60000)
        nxt = pg.locator(".pager button", has_text="Next")
        nxt.focus()
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(200)
        self.assertEqual(pg.evaluate("document.activeElement.textContent"), "Next")
        self.assertIn("Rows 101–200", pg.text_content(".pager"))

    # content wider than its box with overflow visible, the way the layout audit counts it, less two things that are not
    # spills: a Bootstrap .row's negative gutter (it sits in its parent's padding by design) and SVG internals (Plotly)
    SPILLS = """() => [...document.querySelectorAll('main *')].filter((e) => {
        if (e.closest('svg') || !e.getBoundingClientRect().width || e.clientWidth < 24) return false;
        if (!getComputedStyle(e).overflowX.includes('visible')) return false;
        const spill = e.scrollWidth - e.clientWidth; if (spill <= 4) return false;
        const gutter = Math.max(0, ...[...e.querySelectorAll('.row, .list-group-transparent')].map((r) => -parseFloat(getComputedStyle(r).marginRight) || 0));
        return spill > gutter + 1;
    }).map((e) => e.tagName + '.' + e.className + ' ' + (e.scrollWidth - e.clientWidth))"""

    def test_content_stays_in_its_column(self):
        """V10: no spill on Evidence compare, Rules, Dataset Rows with a row open, the hand check; the compare's two filings
        start on the H1's left edge; a table wider than its card is .wide (the edge shade says so); Rules fits in 6,000 px."""
        ev = "0001144879-24-000216%7Cppe_category%7COther%20equipment%20and%20fixtures%7C2024-05-31"
        ev2 = "0001144879-25-000021%7Cppe_category%7COther%20equipment%20and%20fixtures%7C2024-05-31"
        for w in WIDTHS:
            with self.subTest(page="compare", width=w):
                pg = self.page(w, f"evidence/compare?a={ev}&b={ev2}")
                pg.wait_for_selector(".ev-grid section", timeout=60000)
                self.assertEqual(pg.evaluate(self.SPILLS), [])
                dx = pg.evaluate("Math.abs(document.querySelector('.ev-grid').getBoundingClientRect().left - document.querySelector('main h1.page-title').getBoundingClientRect().left)")
                self.assertLessEqual(dx, 1)
            with self.subTest(page="rules", width=w):
                pg = self.page(w, "rules")
                pg.wait_for_selector("#agent-reader", timeout=60000)
                self.assertEqual(pg.evaluate(self.SPILLS), [])
                self.assertEqual(pg.evaluate("[...document.querySelectorAll('main .card .card')].length"), 0)  # V15: no card in a card
                self.assertLessEqual(pg.evaluate("document.documentElement.scrollHeight"), 6000)
            with self.subTest(page="rows", width=w):
                pg = self.page(w, "data?list=taxonomy")
                pg.wait_for_selector("main tbody tr.click", timeout=60000)
                pg.click("main tbody tr.click")
                self.assertEqual(pg.evaluate(self.SPILLS), [])
                m = pg.evaluate("""() => { const d = document.querySelector('tr.detail .row-detail').getBoundingClientRect(), b = d && document.querySelector('tr.detail').closest('.table-responsive');
                    return {wide: b.classList.contains('wide'), right: d.right - b.getBoundingClientRect().right}; }""")
                self.assertTrue(m["wide"])
                self.assertLessEqual(m["right"], 1)  # the opened row's fields end inside the visible box

    # a column whose every body cell is a dash (or empty, with no element in it: a gap bar is not empty)
    EMPTY_COLS = """() => [...document.querySelectorAll('main table')].flatMap((t) => {
        const head = t.tHead && t.tHead.rows[t.tHead.rows.length - 1]; if (!head) return [];
        const rows = [...t.tBodies].flatMap((b) => [...b.rows]).filter((r) => r.cells.length === head.cells.length && r.getBoundingClientRect().height);
        if (rows.length < 2) return [];
        return [...head.cells].map((th, i) => [th, i]).filter(([th, i]) => th.textContent.trim() && rows.every((r) => /^[—–·\\s-]*$/.test(r.cells[i].textContent) && !r.cells[i].querySelector('input, .gg, svg, img, canvas')))
          .map(([th]) => th.textContent.trim() + ' ' + Math.round(th.getBoundingClientRect().width));
    })"""

    def test_empty_columns_and_the_empty_state(self):
        """V9: no column of dashes on the trail (Filings had Value "—" ×5), Reconcile by company, Dataset Rows; an empty Grid
        says which filters left it empty and Export CSV is off; Reconcile by-company rows stay at 44 px at 1280."""
        for hash_ in ("proof/APLD", "proof/MSFT", "reconcile?group=company", "data?list=statements"):
            with self.subTest(page=hash_):
                pg = self.page(1280, hash_)
                pg.wait_for_selector("main table tbody tr", timeout=60000)
                pg.wait_for_timeout(300)
                self.assertEqual([c for c in pg.evaluate(self.EMPTY_COLS) if int(c.rsplit(' ', 1)[1]) > 48], [])
                if hash_.startswith("reconcile"):
                    self.assertLessEqual(pg.evaluate("Math.max(...[...document.querySelectorAll('tr.item')].map((r) => r.getBoundingClientRect().height))"), 44.5)
        pg = self.page(1600, "data?view=grid&k=planned")
        pg.wait_for_selector("main .card-body", timeout=60000)
        self.assertIn("No rows for Field = Capex", pg.text_content("main .card-body"))
        self.assertIn("Kind = Planned", pg.text_content("main .card-body"))
        self.assertTrue(pg.locator("main button", has_text="Export CSV").is_disabled())

    def test_redrawn_tables_keep_the_kit(self):
        """V17: after Find (Dataset) and Show rows (Explore) every header button carries the kit's classes, none is outset."""
        pg = self.page(1600, "data?list=taxonomy")
        pg.wait_for_selector("main thead button", timeout=60000)
        pg.fill("main input[aria-label='Find in rows']", "NVDA")
        pg.wait_for_timeout(500)
        pg2 = self.page(1600, "explore")
        pg2.wait_for_selector("main .plot .main-svg", timeout=60000)
        pg2.click("text=Show rows")
        pg2.wait_for_selector("main thead button", timeout=60000)
        for p in (pg, pg2):
            got = p.eval_on_selector_all("main thead button", "bs => bs.map((b) => [b.classList.contains('btn-link') && b.classList.contains('btn'), getComputedStyle(b).borderTopStyle])")
            self.assertTrue(got)
            self.assertTrue(all(k and st != "outset" for k, st in got), got[:3])

    def test_counts_follow_what_is_shown(self):
        """V18: with a filter on, Reconcile's header reads "N of total" for a bucket the filter narrows (the total unchanged);
        Dataset's one count sits under the list name and follows Find."""
        pg = self.page(1600, "reconcile")
        pg.wait_for_selector("table.rec tr.item", timeout=60000)
        whole = pg.text_content("main .page-header .small")
        n = int(re.search(r"Needs review (\d+)", whole).group(1))
        pg2 = self.page(1600, "reconcile?field=segment_capex")
        pg2.wait_for_selector("main .page-header .small", timeout=60000)
        shown = pg2.eval_on_selector_all("table.rec tr.item", "rs => rs.length")
        self.assertIn(f"Needs review {shown if shown < n else n}" + (f" of {n}" if shown < n else ""), pg2.text_content("main .page-header .small").replace("\u00a0", " "))
        pg3 = self.page(1600, "data?list=taxonomy")
        pg3.wait_for_selector("main tbody tr", timeout=60000)
        pg3.fill("main input[aria-label='Find in rows']", "NVDA")
        pg3.wait_for_timeout(500)
        head = pg3.text_content("main .page-header")
        self.assertRegex(head, r"[\d,]+ rows of [\d,]+ · USD")
        self.assertEqual(len(re.findall(r"[\d,]+ rows\b", pg3.text_content("main"))), 1)  # one count, not one per place

if __name__ == "__main__":
    unittest.main()
