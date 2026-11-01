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

    def test_cost_lines_are_added_when_there_is_no_total_line(self):
        xs = [x(f, "2025-05-31", v, "a", "2025-07-01") for f, v in (("revenue", 100_000_000), ("operating_income", 20_000_000))]
        xs += [{**x("cost_of_revenue_part", "2025-05-31", v, "a", "2025-07-01"), "extraction_id": f"a|part|{n}", "row_label": n}
               for n, v in (("Cloud", 30_000_000), ("Hardware", 10_000_000))]
        v = {r["field"]: r for r in values_for("ORCL", xs, {}, "0531", DOCS)}
        self.assertEqual(v["opex"]["value"], 40_000_000)
        self.assertEqual(len(v["opex"]["extraction_ids"].split(",")), 4)

    def test_xbrl_drawing_cost_of_revenue_differently_is_explained_by_code(self):
        xs = [x(f, "2025-05-31", v, "a", "2025-07-01") for f, v in (("revenue", 100_000_000), ("operating_income", 20_000_000))]
        xs += [{**x("cost_of_revenue_part", "2025-05-31", 30_000_000, "a", "2025-07-01"), "extraction_id": "a|part|Cloud", "row_label": "Cloud"}]
        ref = {("revenue", "FY2025"): 100_000_000, ("operating_income", "FY2025"): 20_000_000, ("opex", "FY2025"): 80_000_000}
        self.assertEqual({r["field"]: r for r in values_for("ORCL", xs, ref, "0531", DOCS)}["opex"]["label"], "definition_gap")
        ref[("revenue", "FY2025")] = 90_000_000  # revenue disagrees too: the cause is unknown, so a person decides
        self.assertEqual({r["field"]: r for r in values_for("ORCL", xs, ref, "0531", DOCS)}["opex"]["label"], "unresolved")

    def test_no_cost_of_revenue_line_means_opex_not_reported(self):
        xs = [x(f, "2025-05-31", v, "a", "2025-07-01") for f, v in (("revenue", 100_000_000), ("operating_income", 20_000_000))]
        v = {r["field"]: r for r in values_for("ORCL", xs, {}, "0531", DOCS)}
        self.assertEqual((v["opex"]["value"], v["opex"]["label"], v["opex"]["source"]), (None, "not_reported", "missing"))

    def test_a_missing_cell_with_an_xbrl_value_is_not_extracted(self):  # T65: AMZN's income statement located as its cash-flow table
        xs = [x("capex", "2025-05-31", 131_819_000_000, "a", "2025-07-01")]
        ref = {("revenue", "FY2025"): 716_924_000_000, ("opex", "FY2025"): 280_535_000_000, ("capex", "FY2025"): 131_819_000_000}
        v = {r["field"]: r for r in values_for("AMZN", xs, ref, "0531", DOCS)}
        self.assertEqual((v["revenue"]["value"], v["revenue"]["label"], v["revenue"]["source"]), (None, "not_extracted", "missing"))
        self.assertEqual(v["opex"]["label"], "not_extracted")  # opex needs three cells; none read, XBRL has the derived value
        self.assertEqual(v["capex"]["label"], "agree")
        v = {r["field"]: r for r in values_for("AMZN", xs, {}, "0531", DOCS)}
        self.assertEqual(v["revenue"]["label"], "not_reported")  # XBRL tags nothing either: the company reports no such line

    def test_a_same_day_partial_amendment_is_not_a_restatement(self):  # AMD: a 10-K/A filed with the 10-K
        xs = [x(f, "2025-05-31", v, "a", "2026-02-04") for f, v in (("revenue", 100_000_000), ("cost_of_revenue", 40_000_000), ("operating_income", 20_000_000), ("capex", 5_000_000))]
        xs += [x(f, "2025-05-31", v, "b", "2026-02-04") for f, v in (("revenue", 100_000_000), ("cost_of_revenue", 45_000_000), ("operating_income", 20_000_000))]
        v = {r["field"]: r for r in values_for("AMD", xs, {}, "0531", DOCS)}
        self.assertEqual((v["opex"]["value"], v["opex"]["basis"], v["capex"]["value"]), (40_000_000, "as_reported", 5_000_000))

    def test_any_change_beyond_rounding_is_a_restatement(self):  # Meta capex moved 0.8%
        xs = [x("capex", "2025-05-31", 31_431_000_000, "a", "2025-07-01"), x("capex", "2025-05-31", 31_186_000_000, "b", "2026-07-01")]
        v = {r["field"]: r for r in values_for("META", xs, {}, "0531", DOCS)}
        self.assertEqual(v["capex"]["basis"], "restated")
        self.assertEqual((v["revenue"]["value"], v["revenue"]["label"]), (None, "not_reported"))  # no such line in this 10-K: blank, with the reason


if __name__ == "__main__":
    unittest.main()
