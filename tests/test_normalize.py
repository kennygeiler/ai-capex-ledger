"""Unit tests for the normalization rules. Run: python3 -m unittest discover -s tests"""
import unittest

from ledger.reference.normalize import REJECTED, best_vintages, calendar_quarter, discrete_quarters, fiscal_label


def fact(start, end, val, accn="a1", form="10-Q", filed="2025-01-01", concept="X"):
    return {"start": start, "end": end, "val": val, "accn": accn, "form": form, "filed": filed, "concept": concept}


class Calendar(unittest.TestCase):
    def test_majority_overlap(self):
        # Nvidia Q1 FY26: Jan 27 - Apr 27 2025 -> mostly Q1
        self.assertEqual(calendar_quarter("2025-01-27", "2025-04-27")[0], "2025Q1")
        # Micron Q1 FY26: Aug 29 - Nov 27 2025 -> mostly Q4
        self.assertEqual(calendar_quarter("2025-08-29", "2025-11-27")[0], "2025Q4")
        self.assertEqual(calendar_quarter("2025-04-01", "2025-06-30"), ("2025Q2", 0))

    def test_fiscal_label(self):
        self.assertEqual(fiscal_label("2025-04-27", "0126"), (2026, 1))  # Nvidia
        self.assertEqual(fiscal_label("2025-09-30", "0630"), (2026, 1))  # Microsoft
        self.assertEqual(fiscal_label("2025-06-30", "0630"), (2025, 4))
        self.assertEqual(fiscal_label("2025-12-31", "1231"), (2025, 4))


class CostcoCalendar(unittest.TestCase):
    def test_16_week_q4_and_collision_shift(self):
        from ledger.reference.normalize import build_company
        # Costco-like 12/12/12/16-week fiscal year ending ~Aug 31, revenue as filed each quarter.
        periods = [("2024-09-02", "2024-11-24", 62), ("2024-11-25", "2025-02-16", 63), ("2025-02-17", "2025-05-11", 63),
                   ("2025-05-12", "2025-08-31", 86), ("2025-09-01", "2025-11-23", 67)]
        units = [{"start": s, "end": e, "val": v * 10**9, "accn": f"a{i}", "form": "10-Q", "filed": "2026-01-01"} for i, (s, e, v) in enumerate(periods)]
        cf = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": units}}}}}
        m, notes, _ = build_company(cf, "0831")
        got = {q: r["period_end"] for q, r in m["revenue"].items()}
        self.assertEqual(got, {"2024Q4": "2024-11-24", "2025Q1": "2025-02-16", "2025Q2": "2025-05-11", "2025Q3": "2025-08-31", "2025Q4": "2025-11-23"})

    def test_no_cascade_for_13_week_calendar(self):
        from ledger.reference.normalize import build_company
        # Nvidia-like quarters ending late in the first month of each calendar quarter.
        periods = [("2024-10-28", "2025-01-26"), ("2025-01-27", "2025-04-27"), ("2025-04-28", "2025-07-27"), ("2025-07-28", "2025-10-26")]
        units = [{"start": s, "end": e, "val": 10**9 * (i + 1), "accn": f"a{i}", "form": "10-Q", "filed": "2026-01-01"} for i, (s, e) in enumerate(periods)]
        cf = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": units}}}}}
        m, _, _ = build_company(cf, "0125")
        self.assertEqual({q: r["period_end"] for q, r in m["revenue"].items()},
                         {"2024Q4": "2025-01-26", "2025Q1": "2025-04-27", "2025Q2": "2025-07-27", "2025Q3": "2025-10-26"})


class Quarters(unittest.TestCase):
    def test_ytd_and_q4(self):
        v = best_vintages([
            fact("2025-01-01", "2025-03-31", 10),
            fact("2025-01-01", "2025-06-30", 25),
            fact("2025-01-01", "2025-09-30", 45),
            fact("2025-01-01", "2025-12-31", 70, form="10-K"),
        ])
        q = discrete_quarters(v)
        self.assertEqual([(e, q[e]["value"], q[e]["method"]) for e in sorted(q)], [
            ("2025-03-31", 10, "reported"), ("2025-06-30", 15, "ytd_diff"),
            ("2025-09-30", 20, "ytd_diff"), ("2025-12-31", 25, "q4_derived")])

    def test_latest_vintage_wins(self):
        v = best_vintages([fact("2025-01-01", "2025-03-31", 10, accn="a1", filed="2025-04-30"),
                           fact("2025-01-01", "2025-03-31", 12, accn="a2", filed="2026-04-30")])
        f = v[("2025-01-01", "2025-03-31")]
        self.assertEqual((f["val"], f["original"], f["restated"], f["vintages"]), (12, 10, True, 2))

    def test_mistagged_full_year_quarter_dropped(self):
        REJECTED.clear()
        v = best_vintages([
            fact("2024-06-01", "2024-08-31", 10), fact("2024-06-01", "2024-11-30", 21), fact("2024-06-01", "2025-02-28", 33),
            fact("2024-06-01", "2025-05-31", 46, form="10-K"),
            fact("2025-03-01", "2025-05-31", 46, form="10-K"),  # filer error: "quarter" holds the year
        ])
        q = discrete_quarters(v)
        self.assertEqual((q["2025-05-31"]["value"], q["2025-05-31"]["method"]), (13, "q4_derived"))
        self.assertEqual(len(REJECTED), 1)


if __name__ == "__main__":
    unittest.main()
