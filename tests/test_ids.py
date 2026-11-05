"""F-BF1: extraction_ids are comma-joined and a dimension may hold a comma. Every reader goes through core.ids.split_ids;
a bare .split(",") cut "Land, buildings and leasehold improvements" in two, so the fact found no readings: no restatement,
no second reading, no ladder rung."""
import re
import unittest
from pathlib import Path

import duckdb

from ledger.checks import ties
from ledger.core.ids import split_ids

ROOT = Path(__file__).resolve().parents[1]
OLD, NEW = "0000000001-24-000001", "0000000001-25-000001"
DIM = "Land, buildings and leasehold improvements"
A, B = f"{OLD}|ppe_category|{DIM}|2024-06-30", f"{NEW}|ppe_category|{DIM}|2024-06-30"


class SplitIds(unittest.TestCase):
    def test_comma_inside_an_id_is_kept(self):
        self.assertEqual(split_ids(f"{A},{B}"), [A, B])

    def test_empty(self):
        self.assertEqual(split_ids(""), [])
        self.assertEqual(split_ids(None), [])

    def test_no_bare_split_on_extraction_ids_left(self):
        """Pattern 4: two readers of one column must not disagree. No module splits extraction_ids by hand."""
        bad = []
        for p in (ROOT / "ledger").rglob("*.py"):
            for n, line in enumerate(p.read_text().splitlines(), 1):
                if "extraction_ids" in line and re.search(r"\.split\(\s*[\"'],[\"']\s*\)", line):
                    bad.append(f"{p.relative_to(ROOT)}:{n}")
        self.assertEqual(bad, [])

    def test_no_sql_splits_a_comma_joined_list(self):
        """The SQL form of the same bug (app.company joined on split_part(extraction_ids, ',', -1)): no module splits a
        string in SQL; it reads the ids with split_ids in Python."""
        bad = []
        for p in (ROOT / "ledger").rglob("*.py"):
            for n, line in enumerate(p.read_text().splitlines(), 1):
                if re.search(r"split_part\(|string_split\(|regexp_split|str_split\(", line, re.I):
                    bad.append(f"{p.relative_to(ROOT)}:{n}")
        self.assertEqual(bad, [])


class OnTheRealDatabase(unittest.TestCase):
    """End to end on the working database: APLD's comma-dimension note fact carries its cited cell on the trail
    (/api/v1/proof/APLD) and in the company feed (/api/company?t=APLD)."""

    DIM = "Networking equipment, electrical equipment, and software"

    def setUp(self):
        import os
        from ledger.core import store
        if not store.DEFAULT_DB.exists() or os.environ.get("LEDGER_SKIP_DB"):
            self.skipTest("no database")
        import threading
        from http.server import ThreadingHTTPServer
        from ledger.web import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        self.base = f"http://127.0.0.1:{srv.server_address[1]}"

    def get(self, path):
        import json
        from urllib import request
        with request.urlopen(self.base + path) as r:
            return json.loads(r.read())

    def test_the_trail_cites_the_cell(self):
        items = [i for i in self.get("/api/v1/proof/APLD")["stages"]["facts"]["all"] if (i.get("ref") or {}).get("dimension") == self.DIM]
        self.assertTrue(items)
        for it in items:
            where = it["card"]["where"]
            self.assertTrue(where, it["what"])
            self.assertTrue(all(w["row"] == self.DIM and w["cell"] for w in where), it["what"])

    def test_the_company_feed_carries_the_cell(self):
        facts = [f for f in self.get("/api/company?t=APLD")["facts"] if f["dimension"] == self.DIM]
        self.assertTrue(facts)
        self.assertTrue(all(f["row_label"] == self.DIM and f["cell_text"] for f in facts))


class CommaDimension(unittest.TestCase):
    """A fact whose dimension holds a comma, read in two filings that disagree: the readings and the restatement are found."""

    def setUp(self):
        self.con = duckdb.connect(":memory:")
        self.con.execute("create table facts (ticker varchar, field varchar, dimension varchar, period varchar, value double, accession varchar, extraction_ids varchar)")
        self.con.execute("create table note_extractions (extraction_id varchar, accession varchar, value double, scale bigint, cell_text varchar)")
        self.con.execute("create table documents (accession varchar, filed varchar, form varchar, period varchar)")
        self.con.execute("insert into facts values ('ZZ', 'ppe_category', ?, '2024-06-30', 1200000000, ?, ?)", [DIM, NEW, f"{A},{B}"])
        self.con.execute("insert into note_extractions values (?, ?, 1000000000, 1000000, '1,000'), (?, ?, 1200000000, 1000000, '1,200')", [A, OLD, B, NEW])
        self.con.execute("insert into documents values (?, '2024-08-01', '10-K', '2024-06-30'), (?, '2025-08-01', '10-K', '2025-06-30')", [OLD, NEW])

    def tearDown(self):
        self.con.close()

    def test_readings_of_finds_both(self):
        by_id = {A: {"extraction_id": A, "accession": OLD, "value": 1e9}, B: {"extraction_id": B, "accession": NEW, "value": 1.2e9}}
        self.assertEqual([r["accession"] for r in ties.readings_of({"extraction_ids": f"{A},{B}"}, by_id)], [OLD, NEW])

    def test_restatement_found(self):
        out = ties.restatements(self.con, ["ZZ"])
        self.assertIn(("ZZ", "ppe_category", DIM, "2024-06-30"), out)

    def test_restatement_by_one_reading(self):
        self.assertIn(("ZZ", "ppe_category", DIM, "2024-06-30"), ties.restatements(self.con, ["ZZ"], A))


if __name__ == "__main__":
    unittest.main()
