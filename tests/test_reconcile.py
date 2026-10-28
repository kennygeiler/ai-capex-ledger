"""Fiscal-year values: one cell each; opex from one 10-K column; newest 10-K wins, first kept; no line, no value."""
import unittest

from ledger.reconcile import values_for


def x(field, end, value, accn, filed):
    start = f"{int(end[:4]) - 1}{end[4:7]}-{int(end[8:]) + 1:02d}" if end.endswith("-31") is False else f"{int(end[:4]) - 1}-{int(end[5:7]) + 1:02d}-01"
    return {"extraction_id": f"{accn}|{field}|{start}|{end}", "accession": accn, "field": field, "period_start": start, "period_end": end,
            "value": value, "scale": 1_000_000, "filed": filed}


DOCS = {"a": ("h1", "p"), "b": ("h2", "p")}


class Annual(unittest.TestCase):
    def test_a_year_never_mixes_filings(self):
        xs = [x(f, "2025-05-31", v, "a", "2025-07-01") for f, v in (("revenue", 100_000_000), ("cost_of_revenue", 40_000_000), ("operating_income", 20_000_000))]
        xs += [x(f, "2025-05-31", v, "b", "2026-07-01") for f, v in (("revenue", 80_000_000), ("operating_income", 20_000_000))]  # newer 10-K drops the line
        v = {r["field"]: r for r in values_for("APLD", xs, {}, "0531", DOCS)}
        self.assertEqual((v["revenue"]["value"], v["opex"]["value"], v["opex"]["label"]), (80_000_000, None, "not_reported"))

    def test_opex_from_one_column_and_restatement_keeps_first(self):
        xs = [x(f, "2025-05-31", v, "a", "2025-07-01") for f, v in (("revenue", 100_000_000), ("cost_of_revenue", 40_000_000), ("operating_income", 20_000_000))]
        xs += [x(f, "2025-05-31", v, "b", "2026-07-01") for f, v in (("revenue", 80_000_000), ("cost_of_revenue", 30_000_000), ("operating_income", 20_000_000))]
        v = {r["field"]: r for r in values_for("APLD", xs, {}, "0531", DOCS)}
        self.assertEqual((v["revenue"]["value"], v["revenue"]["first_reported"], v["revenue"]["basis"]), (80_000_000, 100_000_000, "restated"))
        self.assertEqual((v["opex"]["value"], v["opex"]["first_reported"], v["opex"]["method"]), (30_000_000, 40_000_000, "computed"))
        self.assertEqual(v["opex"]["period"], "FY2025")

    def test_no_cost_of_revenue_line_means_opex_not_reported(self):
        xs = [x(f, "2025-05-31", v, "a", "2025-07-01") for f, v in (("revenue", 100_000_000), ("operating_income", 20_000_000))]
        v = {r["field"]: r for r in values_for("ORCL", xs, {}, "0531", DOCS)}
        self.assertEqual((v["opex"]["value"], v["opex"]["label"], v["opex"]["source"]), (None, "not_reported", "missing"))


if __name__ == "__main__":
    unittest.main()
