"""T68: taxonomy/limitations.yaml is complete, its computed counts match the data, and every packet carries LIMITATIONS.md."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from ledger.release import limitations
from ledger.release.release import build

SEEDED = ("systematic_without_xbrl", "omission_escapes", "same_filer_answer_key", "one_person", "outside_proven_set", "survivor_bias",
          "failure_types_without_check", "interpretive_fields", "older_vintages_unchecked", "asset_type_mappings_unconfirmed", "no_monitoring_thresholds", "tie_offsetting_errors")
VAL = {"ticker": "NVDA", "field": "capex", "period": "FY2026", "period_end": "2026-01-25", "value": 5, "source": "agent", "label": "agree", "basis": "as_reported",
       "first_reported": 5, "extraction_ids": ""}


def _count(entry_id, files=None):
    return next(e for e in limitations.resolved(files) if e["id"] == entry_id)["count"]


class TheFile(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="limitations-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _write(self, data) -> Path:
        p = self.tmp / "limitations.yaml"
        p.write_text(yaml.safe_dump(data))
        return p

    def test_every_seeded_entry_is_there_with_every_field(self):
        es = limitations.load()
        self.assertEqual([e["id"] for e in es], list(SEEDED))
        for e in es:
            for k in limitations.REQUIRED:
                self.assertTrue(e.get(k), (e["id"], k))

    def test_an_entry_without_a_field_is_refused(self):
        good = {"weakness": "w", "rows": "all", "mitigation": "none", "closes": "none"}
        self.assertEqual(len(limitations.load(self._write({"a": good}))), 1)
        for k in limitations.REQUIRED:
            with self.assertRaises(ValueError, msg=k):
                limitations.load(self._write({"a": {f: v for f, v in good.items() if f != k}}))
            with self.assertRaises(ValueError, msg=k):
                limitations.load(self._write({"a": {**good, k: ""}}))
        for bad in ({"rows": "many"}, {"rows": {"computed": "made_up"}}, {"rows": True}, {"closes": "soon"}):
            with self.assertRaises(ValueError, msg=bad):
                limitations.load(self._write({"a": {**good, **bad}}))


class ComputedCounts(unittest.TestCase):
    """Each computed count equals the data it is read from, recounted here another way."""

    def test_tied_rows_count_the_taxonomy_rows_a_tie_checks(self):
        files = {"taxonomy.csv": "check,check_method\ncorroborated,rule:ppe_categories_tie\ncorroborated,reading:a\nagree,xbrl\ncorroborated,rule:segment_revenue_tie\n"}
        self.assertEqual(_count("tie_offsetting_errors", files), 2)

    def test_the_fault_test_escapes_are_the_reports(self):
        d = json.loads(limitations.FAULTS_XBRL_OFF.read_text())
        self.assertEqual(_count("systematic_without_xbrl"), d["by_kind"]["systematic"]["escaped"])
        self.assertEqual(_count("omission_escapes"), d["by_kind"]["omission"]["escaped"])
        self.assertEqual(d["by_kind"]["systematic"]["escaped"], 135)  # T67's figure on 1 Nov 2026; a rerun of the fault test moves it
        self.assertFalse(d["xbrl"])

    def test_failure_types_asset_types_and_companies_are_recounted_from_their_files(self):
        from ledger.core.config import SCOPE, tracked
        from ledger.checks.failures import load as failures
        from ledger.release.taxonomy import asset_types
        self.assertEqual(_count("failure_types_without_check"), sum(t["check"] == "none" for t in failures()))
        from ledger.checks.filertag import tally
        entries = [e for b in asset_types().values() if isinstance(b, dict) for e in b.values()]
        c = tally()  # the one count (claims check, packet): neither confirmed_by nor the company's own tag
        self.assertEqual(_count("asset_type_mappings_unconfirmed"), c["waiting"])
        self.assertEqual(c["waiting"] + c["verified"], sum(not str((e or {}).get("confirmed_by") or "").strip() for e in entries))
        self.assertEqual(_count("outside_proven_set"), len({c["ticker"] for c in tracked()} - set(SCOPE)))

    def test_packet_counts_come_from_the_packets_csvs(self):
        files = {"values.csv": "ticker,check_label,basis\nA,agree,restated\nB,agree,as_reported\nC,unresolved,as_reported\n",
                 "statements.csv": "statement_id\n1\n2\n", "projects.csv": "project_id\n1\n", "ai_spend.csv": "ticker\nA\n"}
        self.assertEqual(_count("same_filer_answer_key", files), 2)
        self.assertEqual(_count("older_vintages_unchecked", files), 1)
        self.assertEqual(_count("interpretive_fields", files), 4)
        self.assertIsNone(_count("one_person", files))  # `all` is not a number

    def test_a_missing_report_reads_unknown_not_zero(self):
        orig = limitations.FAULTS_XBRL_OFF
        limitations.FAULTS_XBRL_OFF = Path(tempfile.gettempdir()) / "no-such-report.json"
        try:
            self.assertIsNone(_count("systematic_without_xbrl"))
            self.assertIn("| unknown not measured", limitations.markdown("v0.0.1"))
        finally:
            limitations.FAULTS_XBRL_OFF = orig


class InThePacket(unittest.TestCase):
    def test_build_writes_limitations_md_with_every_entry_and_the_readme_lists_it(self):
        files = build("v0.1.0", [VAL], [], [], None)
        md = files["LIMITATIONS.md"]
        for i in SEEDED:
            self.assertIn(f"| `{i}` |", md)
        for section in ("## Intended use", "## Known weaknesses", "## Cadence", "## Corrections", "## Support"):
            self.assertIn(section, md)
        self.assertIn("Not for automated trading decisions", md)
        self.assertIn("SIGNOFF.json", md)
        self.assertNotIn("@", md)  # no email
        self.assertIn("1 of 1 values in values.csv agree", md)  # counted over the packet's own values.csv
        self.assertIn("`LIMITATIONS.md`", files["README.md"])
        n = len(limitations.unmitigated(limitations.resolved(files)))
        self.assertIn(f"{len(SEEDED)} entries from `taxonomy/limitations.yaml`; {n} have no mitigation in place.", md)
        self.assertEqual(n, 2)  # survivor_bias and no_monitoring_thresholds


if __name__ == "__main__":
    unittest.main()
