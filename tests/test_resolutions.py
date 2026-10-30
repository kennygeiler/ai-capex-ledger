import unittest

from ledger import resolutions


class Keys(unittest.TestCase):
    def test_parse_each_kind(self):
        self.assertEqual(resolutions._parse("reference_disagrees|AMD|AI revenue FY2024"), ("attribution", "AMD", "revenue", "", "FY2024", "actual"))
        self.assertEqual(resolutions._parse("attribution_moved|LITE|revenue FY2025 actual"), ("attribution", "LITE", "revenue", "", "FY2025", "actual"))
        self.assertEqual(resolutions._parse("fact_differs|IRM|segment_capex GLOBAL DATA CENTER BUSINESS FY2023"), ("facts", "IRM", "segment_capex", "GLOBAL DATA CENTER BUSINESS", "FY2023", ""))
        self.assertEqual(resolutions._parse("finding_unconfirmed|LITE|operating_income"), ("values", "LITE", "operating_income", "", "", ""))
        self.assertEqual(resolutions._parse("finding_unconfirmed|T|opex FY2022"), ("values", "T", "opex", "", "FY2022", ""))
        self.assertIsNone(resolutions._parse("new_filing|X|10-K for the year ended 2025-12-31"))

    def test_by_row_takes_the_latest_and_status_of_falls_back_to_the_field(self):
        rs = [{"key": "reference_disagrees|TSLA|AI capex FY2024", "hash": "a", "state": "accept", "reason": "r", "by": "k", "at": "1"},
              {"key": "reference_disagrees|TSLA|AI capex FY2024", "hash": "a", "state": "fix", "reason": "r", "by": "k", "at": "2"},
              {"key": "finding_unconfirmed|LITE|operating_income", "hash": "b", "state": "explain", "reason": "r", "by": "k", "at": "3"}]
        idx = resolutions.by_row(rs)
        self.assertEqual(idx[("attribution", "TSLA", "capex", "", "FY2024", "actual")]["status"], "fix_pending")
        self.assertEqual(resolutions.status_of(idx, "attribution", "TSLA", "capex", "", "FY2024", "actual"), "fix_pending")
        self.assertEqual(resolutions.status_of(idx, "attribution", "TSLA", "capex", "", "FY2025", "actual"), "")
        self.assertEqual(resolutions.status_of(idx, "values", "LITE", "operating_income", "", "FY2023"), "explained")  # no period in the key: every year

    def test_log_is_at_the_repo_root_and_tracked(self):
        self.assertEqual(resolutions.LOG, resolutions.ROOT / "decisions" / "resolutions.jsonl")
        self.assertNotIn("resolutions.jsonl", (resolutions.ROOT / ".gitignore").read_text())


if __name__ == "__main__":
    unittest.main()
