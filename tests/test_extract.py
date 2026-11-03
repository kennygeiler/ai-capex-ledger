"""Task packing, output validation, citation resolution, period dating."""
import unittest
from pathlib import Path

from ledger.extract.extract import Invalid, make_task, period_start, resolve, validate_output
from ledger.ingest.statements import assemble, locate
from ledger.ingest.tables import document_units, parse_tables

FIX = Path(__file__).parent / "fixtures" / "filings" / "NVDA_10-Q_2026-07-26.html"
ACCN = "0001045810-26-000075"


def parsed():
    doc = FIX.read_bytes()
    t = parse_tables(doc)
    loc, units = locate(t), document_units(doc)
    return {"accession": ACCN, "ticker": "NVDA", "form": "10-Q", "period": "2026-07-26",
            "statements": {k: assemble(t, loc[k], units) for k in ("income", "cash_flow")}}


def value(**kw):
    v = {"field": "revenue", "table_id": "t0000", "row_label": "Revenue", "column_label": "Three Months Ended | Jul 26, 2026",
         "cell_text": "96,221", "period_end": "2026-07-26", "months": 3, "value": 96221000000, "confidence": 1.0}
    return {**v, **kw}


def output(*values):
    return {"accession": ACCN, "prompt_version": "statements@v1", "values": list(values), "not_found": []}


class Task(unittest.TestCase):
    def test_task_has_the_document_and_nothing_from_xbrl(self):
        task = make_task(parsed())
        self.assertIn("Revenue | [0] 96,221", task)
        self.assertNotIn("us-gaap", task)
        self.assertNotIn("96221000000", task)  # no unscaled reference-style values


class Validate(unittest.TestCase):
    def test_valid(self):
        validate_output(output(value()), ACCN)

    def test_rejects(self):
        cases = [
            ({**output(value()), "accession": "x"}, "accession"),
            ({k: v for k, v in output(value()).items() if k != "not_found"}, "missing 'not_found'"),
            (output(value(field="ebitda")), "field"),
            (output(value(months=4)), "months"),
            (output(value(value=96.2)), "integer"),
            (output(value(period_end="Jul 26, 2026")), "period_end"),
        ]
        for obj, needle in cases:
            with self.assertRaises(Invalid) as e:
                validate_output(obj, ACCN)
            self.assertIn(needle, e.exception.reason)


class Citation(unittest.TestCase):
    def test_resolves(self):
        self.assertEqual(resolve(value(), parsed())["scale"], 1_000_000)

    def test_a_table_with_no_unit_source_still_resolves(self):
        """A citation of a table that is no longer a located statement (re-located since, T65) carries no unit_source:
        it resolves with None there instead of crashing the citation rule."""
        doc = parsed()
        for k in ("income", "cash_flow"):
            for t in doc["statements"][k] or []:
                t.pop("unit_source", None)
        self.assertIsNone(resolve(value(), doc)["unit_source"])

    def test_capex_sign_convention(self):
        v = value(field="capex", table_id="t0001", row_label="Purchases related to property and equipment and intangible assets",
                  column_label="Six Months Ended | Jul 26, 2026", cell_text="(4,434)", months=6, value=4434000000)
        resolve(v, parsed())
        with self.assertRaises(Invalid):
            resolve({**v, "value": -4434000000}, parsed())

    def test_broken_citations(self):
        for bad, needle in [(value(table_id="t0099"), "not in the filing"), (value(row_label="Revenues"), "row"),
                            (value(column_label="Q2"), "column"), (value(cell_text="96,222"), "cell text"),
                            (value(value=96221000), "value")]:
            with self.assertRaises(Invalid) as e:
                resolve(bad, parsed())
            self.assertIn(needle, e.exception.reason)


class Dating(unittest.TestCase):
    CAL = ["2025-01-26", "2025-04-27", "2025-07-27", "2025-10-26", "2026-01-25", "2026-04-26", "2026-07-26"]

    def test_starts_from_the_company_calendar(self):
        self.assertEqual(period_start("2026-07-26", 3, self.CAL), "2026-04-27")
        self.assertEqual(period_start("2026-07-26", 6, self.CAL), "2026-01-26")
        self.assertEqual(period_start("2026-01-25", 12, self.CAL), "2025-01-27")

    def test_falls_back_when_the_calendar_is_short(self):
        self.assertEqual(period_start("2024-12-31", 3, []), "2024-10-01")
        self.assertEqual(period_start("2025-06-30", 6, []), "2025-01-01")  # CoreWeave: month-ends stay month-ends


if __name__ == "__main__":
    unittest.main()


class CapexSign(unittest.TestCase):
    def test_positive_cell_accepted_only_when_the_label_says_capex(self):
        from ledger.extract.extract import Invalid, resolve
        parsed = {"accession": "a", "tables": [{"id": "t1", "columns": ["2025"], "scale": 1_000_000, "unit_text": "(in millions)", "unit_source": "table",
                                                 "rows": [{"label": "Capital expenditures", "cells": [{"col": 0, "text": "4,494", "value": 4494.0}]},
                                                          {"label": "Proceeds from sale of assets", "cells": [{"col": 0, "text": "120", "value": 120.0}]}]}],
                  "statements": {"income": [], "cash_flow": []}}
        v = {"field": "capex", "table_id": "t1", "row_label": "Capital expenditures", "column_label": "2025", "cell_text": "4,494", "value": 4_494_000_000}
        resolve(v, parsed)
        with self.assertRaises(Invalid):
            resolve({**v, "row_label": "Proceeds from sale of assets", "cell_text": "120", "value": 120_000_000}, parsed)
