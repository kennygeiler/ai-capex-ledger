"""Layout measured in Chrome (Playwright) against the real app on the working database, at 1600 and 1280 wide. Skipped
without Chrome or the database.

F-BF9: the hand check's exact-dollar line ("In thousands · $9,320,000") overflowed its 9.5rem value column and was cut by the
crop beside it ("$9,320,00"). F-BF8: Docs code blocks drew their text in the same colour as their background."""
import os
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

    def page(self, width, hash_):
        pg = self.browser.new_page(viewport={"width": width, "height": 1000})
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


if __name__ == "__main__":
    unittest.main()
