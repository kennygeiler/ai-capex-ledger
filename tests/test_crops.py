"""Cell crops and the in-app filing viewer (ledger/crops.py, ledger/viewer.py, pages/evidence.js).

Pre-mortem (docs/BUILD.md), one class per answer:
 1 a label standing in for a check: "Cell located" is computed on every read from the record and the current facts,
   and only when the whole cell is the cited text under exactly that column header (Locator, Strict, State).
 2 a vacuous pass: no record, no picture, a missing filing: never "located" (State, Locator).
 3 one decision closing others: one crop file per extraction id; a header over two columns is ambiguous, never the
   last one (Names, Strict).
 4 two consumers disagreeing: the re-read's load_all skips crops.json; the viewer runs the crops' own locator and
   the same text rule (Parity); the page and the viewer hash the stored filing the same way (State); the app serves
   only the pictures the record calls located (Viewer.test_the_route).
 5 degenerate cases: a header that is a suffix of another, a row with no value, a run-together cell, the first row
   of a table (Locator, Strict).
 6 late writes: an older run's crop never replaces a newer one; one run at a time; every entry of a run carries its
   start; the picture is written whole or not at all (Merge, Run).
 7 wording: the banner and the reasons are labels of what was found ("Page shows X · cited Y"), never more (Viewer).
 8 stale input: a changed stored file, fingerprint, citation or crop code makes a crop stale; a changed picture is
   missing; the viewer refuses a stored copy that differs from its fingerprint; a filing renders with no network
   (State, Viewer, Offline).
"""
import fcntl
import hashlib
import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from ledger import crops, evidence, viewer

FIX = Path(__file__).parent / "fixtures" / "filings" / "ORCL_10-K_2026-05-31.html"
CHROME = Path("/Applications/Google Chrome.app").exists() or shutil.which("google-chrome")
ACCN = "0001341439-26-000001"
REV = {"extraction_id": "rev", "accession": ACCN, "table_id": "t0000", "row_label": "Total revenues",
       "column_label": "Year Ended May 31, | 2026", "cell_text": "67,357"}
SHA = hashlib.sha256(FIX.read_bytes()).hexdigest()
PNG = b"\x89PNG fake"
CITE = {"table_id": "t0022", "row_label": "Other equipment and fixtures", "column_label": "May 31,2024", "cell_text": "9,552"}


def _entry(**kw):
    return {"img": "a.png", "img_sha256": hashlib.sha256(PNG).hexdigest(), "accession": ACCN, "document_sha256": "d1", **CITE, "seen": "9,552",
            "match": True, "located": True, "reason": None, "hidden": 0, "at": "2026-11-02T10:00:00+00:00", "code": crops.CODE} | kw


def _root(tmp: Path) -> Path:
    """A clone-shaped folder: data/raw/<cik>/docs/<accession>.htm holding the ORCL fixture."""
    d = tmp / "data" / "raw" / "0001341439" / "docs"
    d.mkdir(parents=True)
    shutil.copy(FIX, d / f"{ACCN}.htm")
    return tmp


def _db(sha=SHA, url="https://www.sec.gov/x.htm"):
    con = duckdb.connect(":memory:")
    con.execute("create table documents (accession varchar, ticker varchar, cik integer, form varchar, period varchar, filed varchar, url varchar, sha256 varchar)")
    con.execute("insert into documents values (?, 'ORCL', 1341439, '10-K', '2026-05-31', '2026-06-20', ?, ?)", [ACCN, url, sha])
    con.execute("insert into documents values ('0001341439-25-000002', 'ORCL', 1341439, '10-K', '2025-05-31', '2025-06-20', 'https://www.sec.gov/y.htm', ?)", [sha])
    con.execute("""create table extractions (extraction_id varchar, accession varchar, ticker varchar, field varchar, period_start varchar, period_end varchar,
                   value bigint, scale bigint, table_id varchar, row_label varchar, column_label varchar, cell_text varchar)""")
    con.execute("""create table note_extractions (extraction_id varchar, accession varchar, ticker varchar, field varchar, dimension varchar, period_end varchar,
                   months integer, value bigint, scale bigint, table_id varchar, row_label varchar, column_label varchar, cell_text varchar)""")
    con.execute("insert into extractions values ('a', ?, 'ORCL', 'revenue', '2025-06-01', '2026-05-31', 67357000000, 1000000, 't0000', 'Total revenues', 'Year Ended May 31, | 2026', '67,357')", [ACCN])
    con.execute("insert into note_extractions values ('b', '0001341439-25-000002', 'ORCL', 'ppe_category', 'Land', '2026-05-31', 0, 9000000, 1000000, 't0003', 'Land', 'May 31, 2026', '9')")
    return con


def _page(html: str, d: Path) -> Path:
    f = d / "page.html"
    f.write_text(f"<html><body>{html}</body></html>")
    return f


def _cite(eid, row, col, cell):
    return {"extraction_id": eid, "accession": ACCN, "table_id": "t0000", "row_label": row, "column_label": col, "cell_text": cell}


class State(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        (self.dir / "a.png").write_bytes(PNG)
        self.doc = self.dir / "doc.htm"
        self.doc.write_bytes(b"<html>filing</html>")
        self.sha = hashlib.sha256(self.doc.read_bytes()).hexdigest()

    def st(self, e, cite=CITE, sha=None, doc="default"):
        return crops.state(e, cite, sha or self.sha, self.doc if doc == "default" else doc, self.dir)

    def test_located_only_while_the_filing_the_citation_and_the_code_are_unchanged(self):
        e = _entry(document_sha256=self.sha)
        self.assertEqual(self.st(e)["state"], "located")
        self.assertEqual(self.st(e, sha="d2")["state"], "stale")  # the fingerprint on record changed
        self.assertEqual(self.st(e, cite={**CITE, "cell_text": "9,553"})["state"], "stale")  # the citation names other text
        for f, v in (("row_label", "Land"), ("column_label", "May 31,2023"), ("table_id", "t0021")):
            self.assertEqual(self.st(e, cite={**CITE, f: v})["reason"], "Citation changed", f)
        self.assertEqual(self.st(_entry(document_sha256=self.sha, code="crops@0:old"))["reason"], "Crop code changed")

    def test_the_stored_file_is_hashed_as_the_viewer_does(self):
        e = _entry(document_sha256=self.sha)
        self.doc.write_bytes(b"<html>edited after the crop</html>")  # the record and the fingerprint agree; the file on disk does not
        self.assertEqual(self.st(e)["state"], "stale")
        self.assertIn("Stored filing changed", self.st(e)["reason"])
        self.assertEqual(self.st(e, doc=None)["reason"], "Stored filing missing")
        self.assertEqual(self.st(e, doc=self.dir / "gone.htm")["reason"], "Stored filing missing")

    def test_nothing_on_record_is_never_located(self):
        e = dict(document_sha256=self.sha)
        self.assertEqual(self.st(None)["state"], "none")
        self.assertEqual(self.st({})["state"], "none")
        self.assertEqual(self.st(_entry(img="gone.png", **e))["state"], "missing")
        self.assertEqual(self.st(_entry(img=None, **e))["state"], "missing")
        self.assertEqual(self.st(_entry(located=False, img=None, reason="Row or column not on page", **e))["state"], "not_located")

    def test_a_changed_picture_is_missing(self):
        (self.dir / "a.png").write_bytes(b"another picture")
        r = self.st(_entry(document_sha256=self.sha))
        self.assertEqual((r["state"], r["reason"]), ("missing", "Crop file changed"))
        self.assertEqual(crops.located_images({"x": _entry()}, self.dir), set())


class Merge(unittest.TestCase):
    def test_an_older_run_never_replaces_a_newer_one(self):
        with tempfile.TemporaryDirectory() as d:
            rec = Path(d) / "crops.json"
            crops.merge({"x": _entry(at="2026-11-02T12:00:00+00:00", seen="new")}, rec)
            crops.merge({"x": _entry(at="2026-11-02T11:00:00+00:00", seen="old"), "y": _entry()}, rec)
            out = crops.load(rec)
            self.assertEqual(out["x"]["seen"], "new")
            self.assertIn("y", out)
            self.assertEqual([p.name for p in Path(d).iterdir() if p.suffix == ".tmp"], [])


class Run(unittest.TestCase):
    def test_one_run_at_a_time(self):
        with tempfile.TemporaryDirectory() as d:
            rec = Path(d) / "crops.json"
            with open(rec.with_name(f".{rec.name}.run.lock"), "a") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                with self.assertRaises(crops.Busy):
                    crops.run(None, ["ORCL"], Path(d), rec)

    @unittest.skipUnless(CHROME, "needs Chrome")
    def test_every_entry_carries_the_runs_start_and_lands_per_filing(self):
        with tempfile.TemporaryDirectory() as d:
            root, rec, out = _root(Path(d)), Path(d) / "crops.json", Path(d) / "crops"
            with mock.patch.object(crops.store, "ROOT", root):
                res = crops.run(_db(), ["ORCL"], out, rec, log=lambda *_: None)
            on_disk = crops.load(rec)
            self.assertEqual(set(on_disk), {"a", "b"})
            self.assertEqual(len({v["at"] for v in on_disk.values()}), 1)
            self.assertTrue(on_disk["a"]["located"])
            self.assertEqual(on_disk["b"]["reason"], "Stored filing missing")
            self.assertEqual(hashlib.sha256((out / res["a"]["img"]).read_bytes()).hexdigest(), res["a"]["img_sha256"])


class Names(unittest.TestCase):
    def test_one_crop_file_per_extraction(self):
        ids = ["0001144879-24-000216|ppe_category|Other equipment and fixtures|2024-05-31", "0001144879-24-000216|ppe_category|Other equipment and fixtures|2023-05-31",
               "0001144879-25-000021|ppe_category|Other equipment and fixtures|2024-05-31"]
        self.assertEqual(len({crops.img_name(i) for i in ids}), 3)


class Consumers(unittest.TestCase):
    def test_the_rereads_loader_skips_the_crop_record(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "stage1.json").write_text(json.dumps({"x": {"cell": "1", "seen": "1", "match": True, "img": None}}))
            Path(d, evidence.CROPS_FILE).write_text(json.dumps({"x": _entry(), "z": _entry()}))
            with mock.patch.object(evidence, "DIR", Path(d)):
                out = evidence.load_all()
        self.assertEqual(out, {"x": {"cell": "1", "seen": "1", "match": True, "img": None}})

    def test_the_viewer_runs_the_crops_locator_and_text_rule(self):
        esc = lambda s: s.encode("ascii", "backslashreplace").decode()
        self.assertIn(esc(evidence._LOCATE), viewer.script())
        self.assertIn(esc(evidence._SAME), viewer.script())
        self.assertTrue(viewer.script().isascii())  # a filing without a charset must not garble it

    def test_the_crop_code_covers_both_copies_of_the_text_rule(self):
        import inspect
        ins = crops.code_inputs()
        self.assertIn(evidence._SAME, ins)
        self.assertIn(inspect.getsource(evidence.same), ins)
        self.assertIn(evidence._LOCATE, ins)


class Strict(unittest.TestCase):
    def test_a_run_together_cell_is_not_one_of_its_values(self):
        self.assertFalse(evidence.same("(2,292)(2,367)(2,828)", "(2,367)"))
        self.assertTrue(evidence.runs_together("(2,292)(2,367)(2,828)", "(2,367)"))
        self.assertTrue(evidence.same("$ 28,496", "28,496"))
        self.assertFalse(evidence.same("98,338", "(98,338)"))


class View(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        (self.dir / "a.png").write_bytes(PNG)
        self.root = _root(self.dir / "root")
        self.rec = {"a": _entry(document_sha256=SHA, table_id="t0000", row_label="Total revenues", column_label="Year Ended May 31, | 2026", cell_text="67,357")}

    def test_a_crop_url_only_when_located_and_current(self):
        con = _db()
        v = crops.view(con, "a", self.rec, self.dir, self.root)
        self.assertEqual((v["state"], v["crop"]["url"]), ("located", "/evidence/crops/a.png"))
        self.assertTrue(v["viewer"].startswith(f"/filing/{ACCN}?t=t0000&row=Total+revenues"))
        v = crops.view(con, "a", {"a": {**self.rec["a"], "document_sha256": "other"}}, self.dir, self.root)
        self.assertEqual((v["state"], v["crop"]["url"]), ("stale", None))
        self.assertEqual(crops.view(con, "b", {}, self.dir, self.root)["state"], "none")
        self.assertIsNone(crops.view(con, "nope", self.rec, self.dir, self.root))

    def test_only_an_sec_address_is_a_link(self):
        self.assertEqual(crops.view(_db(), "a", self.rec, self.dir, self.root)["sec_url"], "https://www.sec.gov/x.htm")
        for bad in ("javascript:alert(1)", "https://www.sec.gov.evil.example/x", "http://www.sec.gov/x", ""):
            self.assertIsNone(crops.view(_db(url=bad), "a", self.rec, self.dir, self.root)["sec_url"], bad)
        js = (Path(crops.__file__).parent / "pages" / "evidence.js").read_text()
        self.assertIn("SEC_LINK.test(e.sec_url || '') ? h('a'", js)

    def test_the_compare_view_has_two_sides_each_with_its_filing(self):
        """#evidence/compare?a=&b= reads each side from its own extraction: accession, filed date, value, state."""
        con = _db()
        a, b = crops.view(con, "a", {}, self.dir, self.root), crops.view(con, "b", {}, self.dir, self.root)
        self.assertEqual((a["accession"], a["filed"]), (ACCN, "2026-06-20"))
        self.assertEqual((b["accession"], b["filed"]), ("0001341439-25-000002", "2025-06-20"))
        self.assertNotEqual(a["value"], b["value"])
        js = (Path(crops.__file__).parent / "pages" / "evidence.js").read_text()
        self.assertIn("side(a, 'A'), side(b, 'B')", js)
        self.assertIn("Filing ${n} · ${e.form} filed ${day(e.filed)}", js)


class Viewer(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.root = _root(self.tmp)

    def test_refuses_an_unknown_accession_and_traversal(self):
        con = _db()
        for bad in ("0000000000-00-000000", "../../README.md", "..%2F..%2Fetc%2Fpasswd", f"{ACCN}/../x", "", ACCN + ".htm"):
            with self.assertRaises(viewer.Refused) as cm:
                viewer.filing(con, bad, self.root)
            self.assertEqual(cm.exception.code, 404, bad)

    def test_refuses_a_stored_copy_that_differs_from_its_fingerprint(self):
        with self.assertRaises(viewer.Refused) as cm:
            viewer.filing(_db(sha="0" * 64), ACCN, self.root)
        self.assertEqual(cm.exception.code, 409)
        with self.assertRaises(viewer.Refused) as cm:
            viewer.filing(_db(), "0001341439-25-000002", self.root)  # on record, the file is not there
        self.assertEqual(cm.exception.code, 410)

    def test_serves_the_filing_sandboxed_with_only_its_own_script(self):
        html, csp = viewer.filing(_db(), ACCN, self.root)
        nonce = csp.split("'nonce-")[1].split("'")[0]
        self.assertIn(f'<script nonce="{nonce}">'.encode(), html)
        self.assertTrue(csp.startswith("sandbox allow-scripts;"))
        self.assertIn("default-src 'none'", csp)
        self.assertIn("connect-src 'none'", csp)
        self.assertTrue(html.startswith(FIX.read_bytes()[:200]))

    def test_the_route(self):
        from http.server import ThreadingHTTPServer
        from urllib import error, request
        from ledger import app, store
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        cdir = self.tmp / "crops"
        cdir.mkdir()
        (cdir / "a.png").write_bytes(PNG)
        (cdir / "b.png").write_bytes(PNG)
        rec = self.tmp / "crops.json"
        rec.write_text(json.dumps({"a": _entry(), "b": _entry(img="b.png", located=False)}))
        with mock.patch.object(app, "_con", side_effect=lambda: _db()), mock.patch.object(store, "ROOT", self.root), \
                mock.patch.object(crops, "CROPS", cdir), mock.patch.object(crops, "RECORD", rec), mock.patch.object(app, "EVIDENCE", self.tmp):
            with request.urlopen(f"{base}/filing/{ACCN}?row=Total%20revenues") as r:
                self.assertTrue(r.headers["Content-Security-Policy"].startswith("sandbox allow-scripts;"))
                self.assertNotIn(b"Total%20revenues", r.read())  # the parameters are read by the page, never written into it
            for bad in ("/filing/0000000000-00-000000", "/filing/..%2F..%2FREADME.md", "/filing/../../README.md"):
                with self.assertRaises(error.HTTPError) as cm:
                    request.urlopen(base + bad)
                self.assertEqual(cm.exception.code, 404, bad)
                self.assertEqual(cm.exception.headers["Content-Security-Policy"], viewer.ERROR_CSP)
            with request.urlopen(f"{base}/evidence/crops/a.png") as r:
                self.assertEqual(r.read(), PNG)
            for name in ("b.png", "c.png"):  # not located; not on record
                with self.assertRaises(error.HTTPError) as cm:
                    request.urlopen(f"{base}/evidence/crops/{name}")
                self.assertEqual(cm.exception.code, 404, name)
            with mock.patch.object(crops, "RECORD", self.tmp / "none.json"):
                with request.urlopen(f"{base}/api/v1/evidence/a") as r:
                    self.assertEqual(json.loads(r.read())["state"], "none")
                with self.assertRaises(error.HTTPError) as cm:
                    request.urlopen(f"{base}/api/v1/evidence/nope")
                self.assertEqual(cm.exception.code, 404)


@unittest.skipUnless(CHROME, "needs Chrome")
class Locator(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)

    def crop(self, doc, cites):
        return crops.crop_doc(doc, hashlib.sha256(doc.read_bytes()).hexdigest(), cites, self.dir / "out", at="2026-11-02T00:00:00+00:00")

    def test_found_and_not_found(self):
        cites = [REV,
                 {**REV, "extraction_id": "first", "row_label": "Cloud", "cell_text": "33,989"},  # the first row under the header
                 {**REV, "extraction_id": "nohead", "column_label": "Year Ended May 31, | 2031"},  # no such column
                 {**REV, "extraction_id": "norow", "row_label": "Revenue from the moon"},  # no such row
                 {**REV, "extraction_id": "other", "row_label": "Operating income"}]  # the row shows other text there
        r = self.crop(FIX, cites)
        self.assertTrue(r["rev"]["located"])
        self.assertTrue((self.dir / "out" / r["rev"]["img"]).stat().st_size > 1000)
        self.assertTrue(r["first"]["located"])
        for k in ("nohead", "norow", "other"):
            self.assertFalse(r[k]["located"], k)
            self.assertIsNone(r[k]["img"], k)  # never a crop of the wrong place
        self.assertEqual(r["norow"]["reason"], "Row or column not on page")
        self.assertEqual(r["other"]["reason"], "Page shows 20,606 · cited 67,357")
        self.assertEqual({v["at"] for v in r.values()}, {"2026-11-02T00:00:00+00:00"})
        self.assertEqual(sorted(p.name for p in (self.dir / "out").iterdir()), sorted({r["rev"]["img"], r["first"]["img"]}))  # no temporary file left

    def test_a_header_is_its_whole_text_and_two_columns_are_ambiguous(self):
        doc = _page("""<table>
          <tr><td></td><td>Fiscal 2024</td><td>2023</td></tr>
          <tr><td>Revenue</td><td>100</td><td>90</td></tr></table>
          <table>
          <tr><td></td><td>2024</td><td>2024</td></tr>
          <tr><td>Cost</td><td>7</td><td>8</td></tr></table>
          <table>
          <tr><td></td><td>2024</td><td>2023</td></tr>
          <tr><td>Rent</td><td>5</td><td>4</td></tr>
          <tr><td></td><td>2024</td><td>2023</td></tr>
          <tr><td>Land</td><td>3</td><td>2</td></tr></table>
          <table><tr><td></td><td>2024</td></tr><tr><td>Total</td><td>(2,292)(2,367)</td></tr></table>""", self.dir)
        r = self.crop(doc, [_cite("suffix", "Revenue", "2024", "100"), _cite("amb", "Cost", "2024", "7"),
                            _cite("repeat", "Land", "2024", "3"), _cite("run", "Total", "2024", "(2,367)")])
        self.assertEqual(r["suffix"]["reason"], "Row or column not on page")  # "Fiscal 2024" ends with 2024; it is not the 2024 column
        self.assertEqual(r["amb"]["reason"], "Column ambiguous")
        self.assertTrue(r["repeat"]["located"])  # the same header repeated down the table names one column
        self.assertEqual(r["run"]["reason"], "Values run together · Page shows (2,292)(2,367) · cited (2,367)")

    def test_a_filing_that_differs_from_its_fingerprint_is_not_cropped(self):
        r = crops.crop_doc(FIX, "0" * 64, [REV], self.dir)
        self.assertEqual((r["rev"]["located"], r["rev"]["img"], r["rev"]["reason"]), (False, None, "Stored filing differs from fingerprint"))
        r = crops.crop_doc(self.dir / "gone.htm", SHA, [REV], self.dir)
        self.assertEqual(r["rev"]["reason"], "Stored filing missing")

    def test_the_viewer_banner_says_what_it_found(self):
        from urllib.parse import urlencode
        from playwright.sync_api import sync_playwright
        page_file = self.dir / "f.html"
        page_file.write_bytes(FIX.read_bytes() + f"<script>{viewer.script()}</script>".encode())
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            try:
                pg = b.new_page()
                pg.goto(page_file.as_uri() + "?" + urlencode({"t": "t0000", "row": "Total revenues", "col": "Year Ended May 31, | 2026", "cell": "67,357"}))
                self.assertEqual(pg.text_content("#ledger-banner"), "Cell located: Total revenues · Year Ended May 31, 2026 · 67,357")
                self.assertIn("solid 3px", pg.eval_on_selector("[data-ledger=cell]", "e => e.style.outline"))
                pg.goto(page_file.as_uri() + "?" + urlencode({"row": "Total revenues", "col": "Year Ended May 31, | 2026", "cell": "67,358"}))
                self.assertEqual(pg.text_content("#ledger-banner"), "Cell not located on this page · Page shows 67,357 · cited 67,358")
                pg.goto(page_file.as_uri() + "?" + urlencode({"row": "Nothing", "col": "Year Ended May 31, | 2026", "cell": "1"}))
                self.assertEqual(pg.text_content("#ledger-banner"), "Cell not located on this page")
                self.assertEqual(pg.eval_on_selector_all("*", "es => es.filter((e) => e.style.outline).length"), 0)  # nothing outlined
            finally:
                b.close()


@unittest.skipUnless(CHROME, "needs Chrome")
class Parity(unittest.TestCase):
    def test_the_pages_text_rule_is_pythons(self):
        from playwright.sync_api import sync_playwright
        cases = [("67,357", "67,357"), ("$ 28,496", "28,496"), ("(98,338)", "98,338"), ("(2,292)(2,367)(2,828)", "(2,367)"), ("—", "-"),
                 ("1​,234", "1,234"), ("", ""), ("12", "1,2"), ("3–5", "3-5"), ("(4,599 )", "(4,599)"), ("5.94", "5.94"), ("1,000", "1000.0")]
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            try:
                js = b.new_page().evaluate(f"(cases) => cases.map(([a, b]) => ({evidence._SAME})(a, b))", cases)
            finally:
                b.close()
        self.assertEqual(js, [evidence.same(a, b) for a, b in cases])


@unittest.skipUnless(CHROME, "needs Chrome")
class Offline(unittest.TestCase):
    def test_rendering_a_filing_fetches_nothing(self):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory() as d:
            doc = _page('<img src="https://www.sec.gov/logo.png"><link rel="stylesheet" href="http://127.0.0.1:9/x.css"><table><tr><td>a</td></tr></table>', Path(d))
            with sync_playwright() as p:
                b = p.chromium.launch(channel="chrome")
                try:
                    pg = b.new_page()
                    blocked = evidence.offline(pg)
                    pg.goto(doc.as_uri(), wait_until="load")
                    self.assertEqual(pg.evaluate("document.images[0].naturalWidth"), 0)
                finally:
                    b.close()
        self.assertEqual(sorted(blocked), ["http://127.0.0.1:9/x.css", "https://www.sec.gov/logo.png"])


class Claims(unittest.TestCase):
    def test_the_evidence_claims_have_rows_and_the_page_scan_reads_the_states(self):
        from ledger import claims
        ids = {e["id"] for e in claims.load()}
        self.assertLessEqual({"evidence_cell_located", "evidence_crop", "evidence_compare", "evidence_open_in_filing"}, ids)
        pages = Path(crops.__file__).parent / "pages"
        found = claims.strings_in("evidence.js", (pages / "evidence.js").read_text()) | claims.strings_in("_shared.js", (pages / "_shared.js").read_text())
        self.assertLessEqual({"Cell located", "Cell not located", "Crop out of date", "Crop file missing", "No crop", "Readings differ", "Readings agree"}, found)
        self.assertEqual([p for p in claims.unregistered() if "evidence" in p["where"]], [])


class RowEvidence(unittest.TestCase):
    """The trail rows, the gold set, Reconcile's cited cell and /api/v1/evidence read a cell's crop through one function
    (crops.cells / crops.brief over crops.state), so a row never shows a state another page contradicts (pattern 4). The
    fixture: ORCL's stored 10-K, a revenue cell cropped and current ('a'), a PP&E cell read in two filings whose crops
    are stale ('b', fingerprint changed) and absent ('c'), and a value whose extraction is not on file."""
    OLD = "0001341439-25-000002"

    def setUp(self):
        from ledger import store
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.root = _root(self.tmp / "root")
        (self.root / "data" / "raw" / "0001341439" / "docs" / f"{self.OLD}.htm").write_bytes(FIX.read_bytes())
        self.cdir = self.tmp / "crops"
        self.cdir.mkdir()
        (self.cdir / "a.png").write_bytes(PNG)
        (self.cdir / "b.png").write_bytes(PNG)
        self.rec = self.tmp / "crops.json"
        rev = dict(table_id="t0000", row_label="Total revenues", column_label="Year Ended May 31, | 2026", cell_text="67,357")
        self.rec.write_text(json.dumps({"a": _entry(document_sha256=SHA, **rev),
                                        "b": _entry(img="b.png", document_sha256="old fingerprint", table_id="t0003", row_label="Land", column_label="May 31, 2025", cell_text="9")}))
        self.db = self.tmp / "ledger.duckdb"
        con = store.init(self.db)
        for acc, filed in ((ACCN, "2026-06-20"), (self.OLD, "2025-06-20")):
            con.execute("insert into documents (accession, ticker, cik, form, period, filed, url, sha256, bytes, parser_version, table_count, tables_path, income_tables, cash_flow_tables) "
                        "values (?, 'ORCL', 1341439, '10-K', ?, ?, 'https://www.sec.gov/x.htm', ?, 1, 'p', 1, 'p', 't0', 't1')", [acc, filed[:4] + "-05-31", filed, SHA])
        run = "'(in millions)', 'table', 0.9, 'v', 'r'"
        con.execute("insert into extractions (extraction_id, accession, ticker, field, period_start, period_end, value, scale, table_id, row_label, column_label, cell_text, "
                    f"unit_stated, unit_source, confidence, prompt_version, run_id) values ('a', ?, 'ORCL', 'revenue', '2025-06-01', '2026-05-31', 67357000000, 1000000, 't0000', "
                    f"'Total revenues', 'Year Ended May 31, | 2026', '67,357', {run})", [ACCN])
        for eid, acc, v, cell in (("b", self.OLD, 9000000, "9"), ("c", ACCN, 12000000, "12")):
            con.execute("insert into note_extractions (extraction_id, accession, ticker, field, dimension, period_end, months, value, scale, table_id, row_label, column_label, cell_text, "
                        f"unit_stated, unit_source, confidence, prompt_version, run_id) values (?, ?, 'ORCL', 'ppe_category', 'Land', '2025-05-31', 12, ?, 1000000, 't0003', 'Land', 'May 31, 2025', ?, {run})",
                        [eid, acc, v, cell])
        con.execute('insert into "values" (ticker, field, period, period_end, value, source, method, label, basis, extraction_ids, input_hash) values '
                    "('ORCL', 'revenue', 'FY2026', '2026-05-31', 67357000000, 'agent', 'reported', 'agree', 'as_reported', 'a', 'h'), "
                    "('ORCL', 'capex', 'FY2026', '2026-05-31', 5000000, 'agent', 'reported', 'agree', 'as_reported', 'gone', 'h')")
        con.execute("insert into facts (ticker, field, dimension, period, period_end, value, first_reported, basis, label, accession, extraction_ids, input_hash) values "
                    "('ORCL', 'ppe_category', 'Land', 'FY2025', '2025-05-31', 12000000, 12000000, 'as_reported', 'no_reference', ?, 'b,c', 'h')", [ACCN])
        con.close()
        self.patches = [mock.patch.object(crops, "RECORD", self.rec), mock.patch.object(crops, "CROPS", self.cdir), mock.patch.object(crops.store, "ROOT", self.root)]
        for x in self.patches:
            x.start()
            self.addCleanup(x.stop)

    def con(self):
        return duckdb.connect(str(self.db))

    def trail(self):
        from ledger import cards
        items = {"values": [{"what": "revenue FY2026", "state": "checked", "by": "xbrl", "ref": {"field": "revenue", "period": "FY2026", "reference": 67357000000}},
                            {"what": "capex FY2026", "state": "checked", "by": "xbrl", "ref": {"field": "capex", "period": "FY2026", "reference": 5000000}}],
                 "facts": [{"what": "ppe Land FY2025", "state": "open", "by": "rule:fact_readings_differ",
                            "ref": {"field": "ppe_category", "dimension": "Land", "period": "FY2025", "readings": [{"value": 9000000, "filed": "2025-06-20"}, {"value": 12000000, "filed": "2026-06-20"}]}}]}
        con = self.con()
        try:
            return cards.add(con, {"ticker": "ORCL", "name": "Oracle", "stages": {k: {"all": v} for k, v in items.items()}})["stages"]
        finally:
            con.close()

    def trail_states(self):
        return {w["extraction_id"]: w["crop"]["state"] for st in self.trail().values() for it in st["all"] for w in it["card"]["where"] if "crop" in w}

    def gold_states(self):
        from ledger import app, gold
        doc = {"items": [{"id": "x", "kind": "fact", "ticker": "ORCL", "field": "ppe_category", "dimension": "Land", "period": "FY2025", "value": 12000000, "verdict": None,
                          "cites": [{"extraction_id": i, "accession": ACCN, "url": "https://www.sec.gov/x.htm"} for i in ("a", "b", "c", "nope")]}]}
        with mock.patch.object(gold, "load_checked", return_value=({"ORCL": doc}, [])), mock.patch.object(app, "_con", side_effect=self.con):
            return {c["extraction_id"]: c["evidence"] for c in app.gold_view("ORCL")["items"][0]["cites"]}

    def reconcile_crop(self, eid):
        from ledger import workbench
        q = {"kind": "fact_differs", "state": "disagrees", "ticker": "ORCL", "where": "ppe_category Land FY2025", "impact": "x", "dollars": 0, "new": False, "action": "definition", "key": "k", "hash": "h",
             "detail": {"field": "ppe_category", "dimension": "Land", "period": "FY2025", "value": 12000000, "reference": 11000000, "cite": {"extraction_id": eid, "table_id": "t0003", "row_label": "Land", "column_label": "May 31, 2025", "cell_text": "9", "accession": self.OLD}, "url": "https://www.sec.gov/x.htm"}}
        flow = {"scope": "ORCL", "tickers": ["ORCL"], "names": {"ORCL": "Oracle"}, "release": {"last": None}, "changed": {"last_run": "2026-11-02"}, "queue": [q]}
        con = self.con()
        try:
            with mock.patch.object(workbench, "asset_types", return_value=[]), mock.patch.object(workbench, "to_confirm", return_value=[]):
                return next(r for r in workbench.items(con, flow)["rows"] if r["cause"] == "fact_differs")["evidence"]["crop"]
        finally:
            con.close()

    def test_trail_gold_reconcile_and_the_api_read_one_state(self):
        api = {i: (crops.view(self.con(), i) or {}).get("state") for i in ("a", "b", "c")}
        self.assertEqual(api, {"a": "located", "b": "stale", "c": "none"})
        self.assertEqual(self.trail_states(), api)
        self.assertEqual({k: v["state"] for k, v in self.gold_states().items() if k != "nope"}, api)
        for i in ("a", "b", "c"):
            self.assertEqual(self.reconcile_crop(i)["state"], api[i], i)

    def test_a_stale_or_missing_crop_is_never_a_picture_on_any_row(self):
        urls = {w["extraction_id"]: w["crop"]["url"] for st in self.trail().values() for it in st["all"] for w in it["card"]["where"] if "crop" in w}
        self.assertEqual(urls, {"a": "/evidence/crops/a.png", "b": None, "c": None})
        g = self.gold_states()
        self.assertEqual((g["a"]["url"], g["b"]["url"], g["c"]["url"]), ("/evidence/crops/a.png", None, None))
        self.assertIsNone(self.reconcile_crop("b")["url"])
        (self.cdir / "a.png").write_bytes(b"changed")  # the picture is not the one written: missing everywhere, shown nowhere
        self.assertEqual(self.trail_states()["a"], "missing")
        self.assertEqual((self.gold_states()["a"]["state"], self.gold_states()["a"]["url"]), ("missing", None))

    def test_no_extraction_on_file_is_no_crop_never_blank(self):
        self.assertEqual(crops.brief(None), {"state": "none", "reason": "No crop", "url": None, "viewer": None, "sec_url": None, "filed": None, "form": None})
        self.assertEqual(self.gold_states()["nope"]["state"], "none")
        capex = next(i for i in self.trail()["values"]["all"] if i["ref"]["field"] == "capex")
        self.assertEqual(capex["card"]["where"], [])  # its cell is not on file: no source line, and the page shows —, never an empty crop

    def test_open_is_the_in_app_viewer_at_the_cell(self):
        w = self.trail()["values"]["all"][0]["card"]["where"][0]
        self.assertEqual(w["viewer"], crops.viewer_url({"accession": ACCN, "table_id": "t0000", "row_label": "Total revenues", "column_label": "Year Ended May 31, | 2026", "cell_text": "67,357"}))
        self.assertTrue(w["viewer"].startswith(f"/filing/{ACCN}?t=t0000&row=Total+revenues&col="))
        self.assertEqual(self.gold_states()["a"]["viewer"], w["viewer"])
        js = (Path(crops.__file__).parent / "pages" / "_shared.js").read_text()
        self.assertIn("h('a', {href: w.viewer, target: '_blank', rel: 'noopener', title: 'Open in filing, the cell outlined'}, 'Open')", js)
        self.assertIn("SEC_LINK.test(w.link || '')", js)  # sec.gov stays a second, guarded link

    def test_the_pages_read_one_label_map(self):
        """Every page says a crop's state with _shared.js CROP_STATE; no page keeps its own copy."""
        pages = Path(crops.__file__).parent / "pages"
        own = [f.name for f in pages.glob("*.js") if f.name != "_shared.js" and ("'Cell located'" in f.read_text() or "Crop out of date" in f.read_text())]
        self.assertEqual(own, [])
        self.assertIn("CROP_STATE[e.state]", (pages / "evidence.js").read_text())
        self.assertIn("citeCell(", (pages / "trail.js").read_text())
        self.assertIn("citeCell(", (pages / "proof.js").read_text())
        self.assertIn("citeCell(", (pages / "reconcile.js").read_text())

    def test_readings_that_differ_link_the_oldest_and_newest_reading(self):
        it = self.trail()["facts"]["all"][0]
        self.assertEqual(it["card"]["compare"], {"a": "b", "b": "c"})  # filed 2025 then 2026: old → new
        self.assertEqual(it["card"]["how"]["text"], "Readings differ: $9M → $12M")
        self.assertEqual([w["filed"] for w in it["card"]["where"]], ["2025-06-20", "2026-06-20"])
        self.assertIn("#evidence/compare?a=${encodeURIComponent(c.compare.a)}&b=${encodeURIComponent(c.compare.b)}", (Path(crops.__file__).parent / "pages" / "trail.js").read_text())


if __name__ == "__main__":
    unittest.main()
