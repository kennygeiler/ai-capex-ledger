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
