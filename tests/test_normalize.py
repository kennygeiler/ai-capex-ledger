"""The XBRL answer key: fiscal-year labels, vintages, the revenue tag choice, opex."""
import unittest

from ledger.reference.normalize import annual_series, best_vintages, derive_costs, fiscal_label


def fact(start, end, val, accn="a1", form="10-K", filed="2025-01-01", concept="X"):
    return {"start": start, "end": end, "val": val, "accn": accn, "form": form, "filed": filed, "concept": concept}


def facts(**concepts):
    """companyfacts shape: {concept: [(start, end, value)]}, all from one 10-K."""
    return {"facts": {"us-gaap": {c: {"units": {"USD": [{"start": s, "end": e, "val": v, "accn": "k1", "form": "10-K", "filed": "2026-02-01"}
                                                     for s, e, v in rows]}} for c, rows in concepts.items()}}}


class AnswerKey(unittest.TestCase):
    def test_fiscal_label(self):
        self.assertEqual(fiscal_label("2025-04-27", "0126"), (2026, 1))  # Nvidia
        self.assertEqual(fiscal_label("2025-06-30", "0630"), (2025, 4))  # Microsoft
        self.assertEqual(fiscal_label("2025-12-31", "1231"), (2025, 4))

    def test_latest_vintage_wins_and_the_first_is_kept(self):
        v = best_vintages([fact("2025-01-01", "2025-12-31", 10, accn="a1", filed="2026-02-01"),
                           fact("2025-01-01", "2025-12-31", 12, accn="a2", filed="2027-02-01")])
        f = v[("2025-01-01", "2025-12-31")]
        self.assertEqual((f["val"], f["original"], f["restated"], f["vintages"]), (12, 10, True, 2))

    def test_a_total_revenue_tag_beats_a_component_tag(self):  # TeraWulf: contract revenue leaves out lease revenue
        cf = facts(RevenueFromContractWithCustomerIncludingAssessedTax=[("2025-01-01", "2025-12-31", 151)], Revenues=[("2025-01-01", "2025-12-31", 168)])
        self.assertEqual(annual_series(cf, "revenue", "1231")["FY2025"]["value"], 168)

    def test_opex_is_revenue_less_operating_income_less_cost_of_revenue(self):
        cf = facts(Revenues=[("2025-01-01", "2025-12-31", 100)], OperatingIncomeLoss=[("2025-01-01", "2025-12-31", 20)],
                   CostOfRevenue=[("2025-01-01", "2025-12-31", 50)])
        years = {m: annual_series(cf, m, "1231") for m in ("revenue", "operating_income", "cost_of_revenue", "opex_reported", "costs_and_expenses", "sga", "rnd", "noninterest_expense")}
        self.assertEqual(derive_costs(years)[1]["FY2025"]["value"], 30)

    def test_one_filing_per_year_the_newest_wins_over_a_better_ranked_tag(self):  # Applied Digital FY2025
        u = lambda accn, filed, v: {"start": "2024-06-01", "end": "2025-05-31", "val": v, "accn": accn, "form": "10-K", "filed": filed}
        cf = {"facts": {"us-gaap": {"RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [u("old", "2025-07-30", 144)]}},
                                    "Revenues": {"units": {"USD": [u("new", "2026-07-29", 228)]}}}}}
        r = annual_series(cf, "revenue", "0531")["FY2025"]
        self.assertEqual((r["value"], r["accession"]), (228, "new"))


if __name__ == "__main__":
    unittest.main()
