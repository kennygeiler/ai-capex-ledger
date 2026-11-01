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


class ToConfirm(unittest.TestCase):
    """T3: the decisions a run made for a person to confirm stay flagged until that person resolves the same key."""

    def test_unconfirmed_is_the_latest_per_key_that_says_to_confirm(self):
        from ledger.resolutions import unconfirmed
        rs = [{"id": "a", "key": "k1", "hash": "h", "state": "fix", "reason": "x", "by": "Replication run (Claude), for Kenny to confirm", "at": "2026-10-30T00:00:00"},
              {"id": "b", "key": "k1", "hash": "h", "state": "accept", "reason": "y", "by": "Claude, for Kenny Geiler to confirm", "at": "2026-10-31T00:00:00"},
              {"id": "c", "key": "k2", "hash": "h", "state": "explain", "reason": "fine, to confirm later", "by": "Claude", "at": "2026-10-29T00:00:00"},
              {"id": "d", "key": "k3", "hash": "h", "state": "accept", "reason": "confirmed", "by": "Kenny Geiler", "at": "2026-10-28T00:00:00"},
              {"id": "e", "key": "k4", "hash": "h", "state": "accept", "reason": "z", "by": "Claude, for Kenny to confirm", "at": "2026-10-27T00:00:00"},
              {"id": "f", "key": "k4", "hash": "h", "state": "accept", "reason": "yes", "by": "Kenny Geiler", "at": "2026-10-31T01:00:00"}]
        self.assertEqual([r["id"] for r in unconfirmed(rs)], ["c", "b"])  # k3 was a person's own; k4 was confirmed by a later resolution

    def test_the_log_on_file_has_seven_for_kenny(self):
        from ledger.resolutions import unconfirmed
        rs = unconfirmed()
        self.assertEqual(len(rs), 7, [r["key"] for r in rs])
        self.assertTrue(all("to confirm" in (r["by"] + r["reason"]).lower() for r in rs))

    def test_the_release_gate_fails_while_any_remain(self):
        from ledger.release import gates
        self.assertEqual(gates([], [], {"values": []}, frozenset(), [{"key": "reference_disagrees|GOOGL|AI capex FY2024"}])["G6"], ["reference_disagrees|GOOGL|AI capex FY2024"])
        self.assertEqual(gates([], [], {"values": []})["G6"], [])
