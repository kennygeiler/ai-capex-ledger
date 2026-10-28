"""Restatement generations: a quarter built across generations has no single basis."""
import unittest

from ledger.basis import first_reported, generation, restatement_dates


def x(field, start, end, value, filed):
    return {"field": field, "period_start": start, "period_end": end, "value": value, "filed": filed, "scale": 1000}


class Generations(unittest.TestCase):
    XS = [x("revenue", "2024-06-01", "2024-08-31", 60_704_000, "2024-10-01"),   # first reported
          x("revenue", "2024-06-01", "2024-08-31", 34_849_000, "2025-10-01"),   # recast after a sale: a restatement
          x("revenue", "2024-06-01", "2024-11-30", 124_572_000, "2025-01-01"),
          x("capex", "2024-06-01", "2024-08-31", 54_798_000, "2024-10-01"),
          x("capex", "2024-06-01", "2024-08-31", 54_800_000, "2025-10-01")]   # rounding, not a restatement

    def test_restatements_are_per_field_and_ignore_rounding(self):
        self.assertEqual(restatement_dates(self.XS), {"revenue": ["2025-10-01"]})

    def test_generation_counts_restatements_on_or_before_the_filing(self):
        d = restatement_dates(self.XS)
        self.assertEqual([generation(e, d) for e in self.XS[:3]], [0, 1, 0])  # mixing the last two would span generations

    def test_first_reported_keeps_the_earliest_filing(self):
        self.assertEqual(sorted(e["value"] for e in first_reported(self.XS) if e["field"] == "revenue"), [60_704_000, 124_572_000])


if __name__ == "__main__":
    unittest.main()
