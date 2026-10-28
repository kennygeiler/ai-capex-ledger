"""The table parser and statement locator on real filing excerpts (tests/fixtures/filings/)."""
import json
import unittest
from pathlib import Path

from ledger.ingest.statements import assemble, locate
from ledger.ingest.tables import document_units, parse_number, parse_tables

FIX = Path(__file__).parent / "fixtures" / "filings"


def statement(name: str, kind: str) -> list[dict]:
    doc = (FIX / name).read_bytes()
    tables = parse_tables(doc)
    return assemble(tables, locate(tables)[kind], document_units(doc))


def cell(tables: list[dict], label: str, column: str) -> dict:
    for t in tables:
        for r in t["rows"]:
            if r["label"] == label:
                for c in r["cells"]:
                    if t["columns"][c["col"]] == column:
                        return c
    raise AssertionError(f"no cell {label!r} / {column!r}")


class Numbers(unittest.TestCase):
    def test_reader_conventions(self):
        self.assertEqual(parse_number("96,221"), 96221)
        self.assertEqual(parse_number("(4,434)"), -4434)
        self.assertEqual(parse_number("—"), 0)
        self.assertEqual(parse_number("1.5"), 1.5)
        self.assertIsNone(parse_number("Revenue"))
        self.assertIsNone(parse_number(""))


class Nvidia10Q(unittest.TestCase):
    """Quarter and year-to-date columns side by side; cash flow is year-to-date only."""

    def test_income_statement(self):
        t = statement("NVDA_10-Q_2026-07-26.html", "income")
        self.assertEqual((t[0]["scale"], t[0]["unit_source"]), (1_000_000, "table"))
        self.assertEqual(t[0]["columns"][0], "Three Months Ended | Jul 26, 2026")
        self.assertEqual(cell(t, "Revenue", "Three Months Ended | Jul 26, 2026")["text"], "96,221")
        self.assertEqual(cell(t, "Cost of revenue", "Three Months Ended | Jul 26, 2026")["value"], 24079)
        self.assertEqual(cell(t, "Operating income", "Six Months Ended | Jul 26, 2026")["value"], 117270)

    def test_cash_flow_capex_is_negative_and_year_to_date(self):
        t = statement("NVDA_10-Q_2026-07-26.html", "cash_flow")
        self.assertEqual(t[0]["columns"], ["Six Months Ended | Jul 26, 2026", "Six Months Ended | Jul 27, 2025"])
        c = cell(t, "Purchases related to property and equipment and intangible assets", "Six Months Ended | Jul 26, 2026")
        self.assertEqual((c["text"], c["value"]), ("(4,434)", -4434))


class Oracle10K(unittest.TestCase):
    """Annual columns only, no cost-of-revenue line, dashes for zero."""

    def test_income_statement(self):
        t = statement("ORCL_10-K_2026-05-31.html", "income")
        self.assertEqual(cell(t, "Total revenues", "Year Ended May 31, | 2026")["value"], 67357)
        self.assertEqual(cell(t, "Operating income", "Year Ended May 31, | 2025")["value"], 17678)
        self.assertFalse(any(r["label"].lower().startswith("cost of revenue") for x in t for r in x["rows"]))

    def test_cash_flow(self):
        t = statement("ORCL_10-K_2026-05-31.html", "cash_flow")
        self.assertEqual(cell(t, "Capital expenditures", "Year Ended May 31, | 2026")["value"], -55663)
        self.assertEqual(cell(t, "Increase in other deferred revenues", "Year Ended May 31, | 2024")["value"], 656)
        dash = [c for x in t for r in x["rows"] for c in r["cells"] if c["text"] == "—"]
        self.assertTrue(dash and all(c["value"] == 0 for c in dash))


class Iren10K(unittest.TestCase):
    """Header spans shifted against the numbers, a footnote-reference column, a cash-flow statement split at a page break."""

    def test_note_column_is_separate(self):
        t = statement("IREN_10-K_2026-06-30.html", "income")
        self.assertEqual(t[0]["columns"][0], "Years ended June 30, | Note")
        self.assertEqual(cell(t, "AI Cloud Services Revenue", "Years ended June 30, | 2026")["value"], 128795)
        self.assertEqual(cell(t, "Total revenue", "Years ended June 30, | 2025")["value"], 501023)

    def test_split_cash_flow_inherits_columns_and_unit(self):
        t = statement("IREN_10-K_2026-06-30.html", "cash_flow")
        self.assertEqual(len(t), 2)
        self.assertEqual(t[1]["columns"], t[0]["columns"])
        self.assertEqual((t[1]["scale"], t[1]["unit_source"]), (1000, "statement"))
        c = cell(t, "Payments for property, plant and equipment, net of computer hardware", "Years ended June 30, | 2026")
        self.assertEqual(c["value"], -2998006)


class Hygiene(unittest.TestCase):
    def test_no_xbrl_tag_names_reach_the_output(self):
        for f in FIX.glob("*.html"):
            out = json.dumps(parse_tables(f.read_bytes()))
            self.assertNotIn("us-gaap", out, f.name)
            self.assertNotIn("nonFraction", out, f.name)

    def test_parsing_is_deterministic(self):
        doc = (FIX / "NVDA_10-Q_2026-07-26.html").read_bytes()
        self.assertEqual(json.dumps(parse_tables(doc)), json.dumps(parse_tables(doc)))


if __name__ == "__main__":
    unittest.main()
