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
        self.assertTrue(pg.locator("main .page-header button", has_text="CSV").is_disabled())

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

    def test_explore_controls_and_cold_chart(self):
        """V20: a cold deep link draws its chart (Plotly is waited for); every control has a visible label; the three control
        lines never wrap at 1600."""
        pg = self.page(1600, "explore?measure=projects&x=ticker&type=bars")
        pg.wait_for_selector("main .plot .main-svg", timeout=60000)
        self.assertEqual(pg.eval_on_selector_all("main .plot p.msg", "ps => ps.length"), 0)
        pg = self.page(1600, "explore")
        pg.wait_for_selector("main .plot .main-svg", timeout=60000)
        self.assertEqual(pg.eval_on_selector_all("main .exbody select, main .exbody input", "es => es.filter((e) => !(e.closest('label') && e.closest('label').querySelector('.exl').textContent.trim())).length"), 0)
        lines = pg.eval_on_selector_all("main .exc", """cs => cs.map((c) => { const rs = [...c.querySelectorAll('select, input')].map((e) => e.getBoundingClientRect());
            return rs.length ? Math.max(...rs.map((r) => r.top)) - Math.min(...rs.map((r) => r.top)) : 0; })""")
        self.assertTrue(all(d < 4 for d in lines), lines)

    def test_one_line_at_1280_and_filters_that_show(self):
        """V12: the navbar is 56 px and one line at 1280 on every page; Reconcile's filter bar is one line at 1280.
        V19: a filter off its default reads as set and is counted beside Clear; Grid's Companies reads Custom only after Apply."""
        for hash_ in ("proof", "rules", "reconcile", "data", "explore", "release", "gaps", "docs"):
            with self.subTest(page=hash_):
                pg = self.page(1280, hash_, height=800)
                pg.wait_for_selector("main .route > *", timeout=60000)
                m = pg.evaluate("""() => ({h: document.querySelector('header.navbar').getBoundingClientRect().height,
                    wrapped: [...document.querySelectorAll('.navbar .nav-link')].filter((a) => { const r = document.createRange(); r.selectNodeContents(a); return r.getClientRects().length > 1; }).length})""")
                self.assertLessEqual(m["h"], 56.5)
                self.assertEqual(m["wrapped"], 0)
        for w in WIDTHS:
            with self.subTest(page="reconcile filtered", width=w):
                pg = self.page(w, "reconcile?field=segment_capex&cause=finding_unconfirmed")
                pg.wait_for_selector(".filterbar select", timeout=60000)
                m = pg.evaluate("""() => { const f = document.querySelector('.filterbar'), R = [...f.children].map((e) => e.getBoundingClientRect());
                    return {spread: Math.max(...R.map((r) => r.top)) - Math.min(...R.map((r) => r.top)), set: f.querySelectorAll('select.is-set').length, clear: (f.querySelector('button') || {}).textContent}; }""")
                self.assertLess(m["spread"], 8)  # one line: every control's top within a few px
                self.assertEqual(m["set"], 2)
                self.assertEqual(m["clear"], "Clear 2")
        pg = self.page(1600, "data?view=grid")
        pg.wait_for_selector("main select[aria-label=Companies]", timeout=60000)
        pg.select_option("main select[aria-label=Companies]", "custom")
        pg.wait_for_selector(".drawer", timeout=10000)
        pg.keyboard.press("Escape")
        self.assertEqual(pg.eval_on_selector("main select[aria-label=Companies]", "s => s.options[s.selectedIndex].text"), "All companies")

    def test_reconcile_row_affordance(self):
        """V14: a row under the pointer is filled; no row reads as current on load; one tab stop per row (the row: its
        checkbox, company link and mapping buttons are pointer-only, the opened row has the same actions); the keys are a
        disclosure reachable by Tab."""
        pg = self.page(1600, "reconcile")
        pg.wait_for_selector("table.rec tr.item", timeout=60000)
        m = pg.evaluate("""() => { const rows = [...document.querySelectorAll('tr.item')];
            return {cur: document.querySelectorAll('tr.item.cur').length,
              stops: Math.max(...rows.map((r) => [r, ...r.querySelectorAll('a, button, input, select, [tabindex]')].filter((e) => e.tabIndex >= 0 && !e.disabled).length)),
              keys: document.querySelector('details.keys > summary').tabIndex}; }""")
        self.assertEqual(m["cur"], 0)
        self.assertEqual(m["stops"], 1)
        self.assertEqual(m["keys"], 0)
        pg.hover("table.rec tr.item >> nth=2")
        bg = pg.eval_on_selector("table.rec tr.item >> nth=2", "tr => getComputedStyle(tr.cells[2]).backgroundColor")
        self.assertNotIn(bg, ("rgba(0, 0, 0, 0)", "transparent"))

    # a block at least 300 × 300 px and 8 % of the viewport whose content covers under 10 % of it (the layout audit's dead
    # space, less SVG internals and <col>: Plotly's layers and a column's box are not content holders; less a block of text
    # alone, which is its own content, and what sits in a closed <details>, which Chrome still gives a box)
    DEAD = """() => { const out = []; for (const e of document.querySelectorAll('main *')) { if (e.closest('svg') || e.matches('col, colgroup') || !e.children.length || e.closest('details:not([open]) > :not(summary)')) continue;
        const r = e.getBoundingClientRect(); if (r.width < 300 || r.height < 300 || r.width * r.height < innerWidth * innerHeight * .08) continue;
        const kids = [...e.querySelectorAll('*')].filter((k) => { const q = k.getBoundingClientRect(); return q.width && q.height; }); if (kids.length > 400) continue;
        let cov = 0; for (const k of kids) { if (k.children.length && !k.matches('button, a, input, select, img, svg, canvas, textarea')) continue; const q = k.getBoundingClientRect();
          cov += Math.max(0, Math.min(q.right, r.right) - Math.max(q.left, r.left)) * Math.max(0, Math.min(q.bottom, r.bottom) - Math.max(q.top, r.top)); }
        if (cov / (r.width * r.height) < .10) out.push(e.tagName + '.' + e.className + ' ' + Math.round(r.width) + 'x' + Math.round(r.height)); } return out; }"""

    def test_no_card_in_a_card_and_no_dead_blocks(self):
        """V15: an opened Reconcile mapping row shows no bordered box inside the table's card; no dead block on Reconcile (a
        mapping open), Rules or Proof at either width."""
        for w in WIDTHS:
            with self.subTest(page="reconcile mapping open", width=w):
                pg = self.page(w, "reconcile?cause=asset_types")
                pg.wait_for_selector("table.rec tr.item", timeout=60000)
                pg.click("table.rec tr.item")
                pg.wait_for_selector("tr.ev", timeout=10000)
                boxed = pg.eval_on_selector_all(".card .card", "cs => cs.filter((c) => { const s = getComputedStyle(c); return parseFloat(s.borderTopWidth) > 0 || s.boxShadow !== 'none'; }).length")
                self.assertEqual(boxed, 0)
                self.assertEqual(pg.evaluate(self.DEAD), [])
            for hash_ in ("rules", "proof"):
                with self.subTest(page=hash_, width=w):
                    pg = self.page(w, hash_)
                    pg.wait_for_selector("main .route > *", timeout=60000)
                    pg.wait_for_timeout(1500)
                    self.assertEqual(pg.evaluate(self.DEAD), [])

    def test_one_header_style_and_one_head(self):
        """V21: every table header in one case and size, a numeric column's header right-aligned, on every page; the Rows/Grid
        switch and the CSV in the same place on both views. F-VS2: on Dataset, Explore and Docs the H1 shares the scope
        line's left edge."""
        for hash_ in ("proof", "proof/APLD", "rules", "reconcile", "data", "data?view=grid", "release", "gaps", "docs"):
            with self.subTest(page=hash_):
                pg = self.page(1600, hash_)
                pg.wait_for_selector("main table thead th", timeout=60000)
                m = pg.evaluate("""() => { const ths = [...document.querySelectorAll('main thead th')].filter((th) => th.getBoundingClientRect().height && th.textContent.trim() && !th.closest('tr.proof-legend, tr.gold-group'));
                    const styles = new Set(ths.map((th) => { const b = th.querySelector('button') || th, c = getComputedStyle(b); return c.textTransform + ' ' + c.fontSize; }));
                    const off = ths.filter((th) => { const t = th.closest('table'), td = t.tBodies[0] && t.tBodies[0].rows[0] && t.tBodies[0].rows[0].cells[th.cellIndex];
                      return th.colSpan === 1 && td && td.colSpan === 1 && getComputedStyle(td).textAlign === 'right' && getComputedStyle(th).textAlign !== 'right'; }).map((th) => th.textContent.trim());
                    return {styles: [...styles], off}; }""")
                self.assertEqual(len(m["styles"]), 1, m["styles"])
                self.assertEqual(m["off"], [])
        at = {}
        for hash_ in ("data?list=taxonomy", "data?view=grid"):
            pg = self.page(1600, hash_)
            pg.wait_for_selector("main .page-header .seg", timeout=60000)
            at[hash_] = pg.evaluate("""() => { const r = (e) => Math.round(e.getBoundingClientRect().left); const csv = [...document.querySelectorAll('main .page-header .btn')].find((b) => b.textContent === 'CSV');
                return [r(document.querySelector('main .page-header .seg')), r(csv)]; }""")
        self.assertEqual(at["data?list=taxonomy"][:2], at["data?view=grid"][:2])
        for hash_ in ("data?list=taxonomy", "explore", "docs"):
            with self.subTest(page=hash_, check="F-VS2"):
                pg = self.page(1600, hash_)
                pg.wait_for_selector("main h1.page-title", timeout=60000)
                pg.wait_for_selector("#scopeline a", timeout=60000)
                self.assertLessEqual(pg.evaluate("Math.abs(document.querySelector('main h1.page-title').getBoundingClientRect().left - document.querySelector('#scopeline a').getBoundingClientRect().left)"), 1)

    # snake_case, a US GAAP …Member code or an accession number in text on screen (code blocks, Docs and the raw Rows table
    # are the code's own words and are left out)
    MACHINE = r"""() => { const out = new Set(); const walk = (n) => { for (const c of n.childNodes) {
        if (c.nodeType === 3) { const m = c.textContent.match(/\b[a-z]+_[a-z_]+\b|\b\w+Member\b|\b\d{10}-\d{2}-\d{6}\b/g);
          if (m && c.parentElement.getBoundingClientRect().height && !c.parentElement.closest('pre, code, .md, .mono, table.raw, .charter, details:not([open]) > :not(summary)')) m.forEach((x) => out.add(x)); }
        else if (c.nodeType === 1 && !['SCRIPT', 'STYLE', 'SELECT'].includes(c.tagName)) walk(c); } }; walk(document.querySelector('main')); return [...out]; }"""

    def test_no_machine_words_on_screen(self):
        """V22: Reconcile (a row open, a mapping open), Explore with its saved views and rows, the trail and Evidence show no
        snake_case, no …Member code and no accession number."""
        ev = "0001144879-24-000216%7Cppe_category%7COther%20equipment%20and%20fixtures%7C2024-05-31"
        for hash_, click in (("reconcile", "table.rec tr.item"), ("reconcile?cause=asset_types", "table.rec tr.item"), ("explore", "text=Show rows"), ("proof/APLD", None), ("evidence/" + ev, None)):
            with self.subTest(page=hash_):
                pg = self.page(1600, hash_)
                pg.wait_for_selector("main .route > *", timeout=60000)
                pg.wait_for_timeout(800)
                if click:
                    pg.click(click)
                    pg.wait_for_timeout(500)
                self.assertEqual(pg.evaluate(self.MACHINE), [])

    # paddings, margins and gaps off a 4 px scale (the layout audit's spacing.offScale), Plotly's own modebar left out
    OFF_SCALE = """() => { const out = new Set(); for (const e of [...document.querySelectorAll('body *')].slice(0, 3000)) {
        const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1 || e.closest('.modebar')) continue; const cs = getComputedStyle(e);
        for (const p of ['paddingTop', 'paddingLeft', 'marginTop', 'rowGap', 'columnGap']) { const v = Math.round(parseFloat(cs[p])); if (v > 2 && v < 200 && v % 4) out.add(v + ' ' + p + ' ' + e.tagName.toLowerCase() + '.' + String(e.className).split(' ').slice(0, 2).join('.')); } }
        return [...out]; }"""

    def test_spacing_on_the_scale(self):
        """V23: every padding, margin and gap on every page is on the 4 px scale (4 / 8 / 12 / 16 / 24 …)."""
        ev = "0001144879-24-000216%7Cppe_category%7COther%20equipment%20and%20fixtures%7C2024-05-31"
        for hash_ in ("proof", "proof?gold=APLD", "proof/APLD", "rules", "reconcile", "data", "data?view=grid", "explore", "release", "gaps", "docs", "evidence/" + ev):
            for w in WIDTHS:
                with self.subTest(page=hash_, width=w):
                    pg = self.page(w, hash_)
                    pg.wait_for_selector("main .route > *", timeout=60000)
                    pg.wait_for_timeout(600)
                    self.assertEqual(pg.evaluate(self.OFF_SCALE), [])

    def test_wide_box_stays_on_screen_at_the_page_end(self):
        """F-VS3: Dataset Rows scrolls inside its card; with the page scrolled to its end, the box and its header are on screen."""
        for w in WIDTHS:
            with self.subTest(width=w):
                pg = self.page(w, "data?list=taxonomy")
                pg.wait_for_selector(".table-responsive.wide thead th", timeout=60000)
                top = pg.evaluate("""async () => { window.scrollTo(0, document.documentElement.scrollHeight); await new Promise((r) => setTimeout(r, 200));
                    return document.querySelector('.table-responsive.wide thead th').getBoundingClientRect().top; }""")
                self.assertGreaterEqual(top, 0)

    def test_cut_lines_say_their_whole_text(self):
        """F-VS5: every Reconcile cell or line cut with an ellipsis carries its whole text on hover; the trail's visible crop
        thumbnails never overlap (thumbnails inside a closed <details> are not on screen, though Chrome boxes them)."""
        for w in WIDTHS:
            with self.subTest(width=w):
                pg = self.page(w, "reconcile")
                pg.wait_for_selector("table.rec tr.item", timeout=60000)
                pg.wait_for_timeout(300)
                self.assertEqual(pg.evaluate("""() => [...document.querySelectorAll('table.rec tr.item > td, table.rec tr.item > td > div')]
                    .filter((e) => e.scrollWidth > e.clientWidth + 1 && !(e.title || e.querySelector('[title]') || e.closest('[title]'))).map((e) => e.textContent.slice(0, 40))"""), [])
                pg = self.page(w, "proof/APLD")
                pg.wait_for_selector(".crop-thumb", state="attached", timeout=60000)
                pg.wait_for_timeout(800)
                self.assertEqual(pg.evaluate("""() => { const ts = [...document.querySelectorAll('.crop-thumb')].filter((t) => !t.closest('details:not([open])')).map((t) => t.getBoundingClientRect()).filter((r) => r.width && r.height);
                    let n = 0; for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) { const a = ts[i], b = ts[j];
                      if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 4 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 4) n++; } return n; }"""), 0)

if __name__ == "__main__":
    unittest.main()
