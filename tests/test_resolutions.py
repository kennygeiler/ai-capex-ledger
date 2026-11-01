import json
import unittest

from ledger import resolutions


class Keys(unittest.TestCase):
    def test_parse_each_kind(self):
        self.assertEqual(resolutions._parse("fact_differs|IRM|segment_capex GLOBAL DATA CENTER BUSINESS FY2023"), ("facts", "IRM", "segment_capex", "GLOBAL DATA CENTER BUSINESS", "FY2023", ""))
        self.assertEqual(resolutions._parse("finding_unconfirmed|LITE|operating_income"), ("values", "LITE", "operating_income", "", "", ""))
        self.assertEqual(resolutions._parse("finding_unconfirmed|T|opex FY2022"), ("values", "T", "opex", "", "FY2022", ""))
        self.assertIsNone(resolutions._parse("new_filing|X|10-K for the year ended 2025-12-31"))
        # kinds the inferred layer produced (2ee2e6f removed it) name no row today
        self.assertIsNone(resolutions._parse("reference_disagrees|AMD|AI revenue FY2024"))
        self.assertIsNone(resolutions._parse("attribution_moved|LITE|revenue FY2025 actual"))

    def test_live_kinds_are_what_the_queue_produces(self):
        import re
        src = (resolutions.ROOT / "ledger" / "app.py").read_text()
        produced = set(re.findall(r'queue\.append\(\{"kind": "([a-z_]+)"', src))
        self.assertEqual(produced, set(resolutions.LIVE_KINDS))
        self.assertTrue(resolutions.is_live("fact_differs|IRM|segment_capex X FY2023"))
        self.assertFalse(resolutions.is_live("reference_disagrees|AMD|AI revenue FY2024"))

    def test_by_row_takes_the_latest_and_status_of_falls_back_to_the_field(self):
        rs = [{"key": "fact_differs|TSLA|segment_capex Energy FY2024", "hash": "a", "state": "accept", "reason": "r", "by": "k", "at": "1"},
              {"key": "fact_differs|TSLA|segment_capex Energy FY2024", "hash": "a", "state": "fix", "reason": "r", "by": "k", "at": "2"},
              {"key": "finding_unconfirmed|LITE|operating_income", "hash": "b", "state": "explain", "reason": "r", "by": "k", "at": "3"},
              {"key": "reference_disagrees|TSLA|AI capex FY2024", "hash": "c", "state": "fix", "reason": "stale", "by": "k", "at": "4"}]
        idx = resolutions.by_row(rs)
        self.assertEqual(idx[("facts", "TSLA", "segment_capex", "Energy", "FY2024", "")]["status"], "fix_pending")
        self.assertEqual(resolutions.status_of(idx, "facts", "TSLA", "segment_capex", "Energy", "FY2024"), "fix_pending")
        self.assertEqual(resolutions.status_of(idx, "facts", "TSLA", "segment_capex", "Energy", "FY2025"), "")
        self.assertFalse([k for k in idx if k[0] == "attribution"])  # a stale kind maps onto no row
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
        rs = [{"id": "a", "key": "fact_differs|A|x d FY2024", "hash": "h", "state": "fix", "reason": "x", "by": "Replication run (Claude), for Kenny to confirm", "at": "2026-10-30T00:00:00"},
              {"id": "b", "key": "fact_differs|A|x d FY2024", "hash": "h", "state": "accept", "reason": "y", "by": "Claude, for Kenny Geiler to confirm", "at": "2026-10-31T00:00:00"},
              {"id": "c", "key": "blocked|B|y FY2024", "hash": "h", "state": "explain", "reason": "fine, to confirm later", "by": "Claude", "at": "2026-10-29T00:00:00"},
              {"id": "d", "key": "new_filing|C|10-K", "hash": "h", "state": "accept", "reason": "confirmed", "by": "Kenny Geiler", "at": "2026-10-28T00:00:00"},
              {"id": "e", "key": "fact_changed|D|z FY2023", "hash": "h", "state": "accept", "reason": "z", "by": "Claude, for Kenny to confirm", "at": "2026-10-27T00:00:00"},
              {"id": "f", "key": "fact_changed|D|z FY2023", "hash": "h", "state": "accept", "reason": "yes", "by": "Kenny Geiler", "at": "2026-10-31T01:00:00"}]
        self.assertEqual([r["id"] for r in unconfirmed(rs)], ["c", "b"])  # k3 was a person's own; k4 was confirmed by a later resolution

    def test_the_log_on_file_has_one_for_kenny_and_the_stale_ones_are_archived(self):
        """After the 2 Nov sweep: the live log holds only live kinds (LITE operating_income, a finding_unconfirmed, is the
        one decision left to confirm); the 12 stale lines sit under decisions/archive/ behind a note line."""
        from ledger.resolutions import LOG, ROOT, is_live, load, unconfirmed
        rs = unconfirmed()
        self.assertEqual([r["key"] for r in rs], ["finding_unconfirmed|LITE|operating_income"])
        self.assertTrue(all("to confirm" in (r["by"] + r["reason"]).lower() for r in rs))
        self.assertTrue(all(is_live(r["key"]) for r in load()), "stale kinds belong in decisions/archive/")
        self.assertEqual(len(load()), 2)
        arch = [json.loads(l) for l in (ROOT / "decisions" / "archive" / "resolutions-stale-2026-11-02.jsonl").read_text().splitlines() if l.strip()]
        self.assertIn("2ee2e6f", arch[0]["note"])
        self.assertEqual(len(arch) - 1, 12)
        self.assertTrue(all(not is_live(r["key"]) for r in arch[1:]))
        self.assertEqual(LOG, ROOT / "decisions" / "resolutions.jsonl")

    def test_unconfirmed_ignores_stale_kinds_even_if_present(self):
        from ledger.resolutions import unconfirmed
        rs = [{"id": "a", "key": "reference_disagrees|GOOGL|AI capex FY2024", "hash": "h", "state": "explain", "reason": "x", "by": "Claude, for Kenny to confirm", "at": "2026-10-30T00:00:00"},
              {"id": "b", "key": "attribution_moved|LITE|revenue FY2025 actual", "hash": "h", "state": "fix", "reason": "y", "by": "Claude, for Kenny to confirm", "at": "2026-10-30T00:00:00"},
              {"id": "c", "key": "finding_unconfirmed|LITE|operating_income", "hash": "h", "state": "accept", "reason": "z", "by": "Claude, for Kenny to confirm", "at": "2026-10-30T00:00:00"}]
        self.assertEqual([r["id"] for r in unconfirmed(rs)], ["c"])

    def test_the_release_gate_fails_while_any_live_one_remains(self):
        from ledger.release import gates
        g = gates([], [], {"values": []}, frozenset(), [{"key": "finding_unconfirmed|GOOGL|opex FY2024"}], tickers=["GOOGL"])
        self.assertEqual(g["G6"], {"GOOGL": ["finding_unconfirmed|GOOGL|opex FY2024"]})
        self.assertEqual(gates([], [], {"values": []}, tickers=["GOOGL"])["G6"], {"GOOGL": []})
        stale = gates([], [], {"values": []}, frozenset(), [{"key": "reference_disagrees|GOOGL|AI capex FY2024"}], tickers=["GOOGL"])
        self.assertEqual(stale["G6"], {"GOOGL": []})  # a stale kind is never a G6 failure, and adds no company
