"""F17: a note figure whose filing's XBRL instance was never loaded read "Unverified · citation only", the same as one
whose instance tags nothing. It now reads "XBRL instance not loaded", open, on Proof, the trail card and the taxonomy
check column; and a tie reads an instance stored as XML whose facts were never distilled."""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from ledger.core import states, status, store
from ledger.checks import ties

UNTAGGED = {"ticker": "ZZZ", "field": "ppe_category", "dimension": "Land", "period": "FY2024", "label": "no_reference", "value": 5.0}

XML = b"""<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://fasb.org/us-gaap/2024">
  <xbrli:context id="c1"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">1</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period></xbrli:context>
  <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
  <us-gaap:PropertyPlantAndEquipmentGross contextRef="c1" unitRef="usd">1234</us-gaap:PropertyPlantAndEquipmentGross>
</xbrl>"""


class NotLookedUp(unittest.TestCase):
    def test_an_untagged_fact_with_no_instance_is_open_and_says_so(self):
        loaded = status.of_fact(UNTAGGED)
        self.assertEqual((loaded["state"], loaded["by"]), ("explained", "label:no_reference"))
        st = status.of_fact(UNTAGGED, looked_up=False)
        self.assertEqual((st["state"], st["by"]), ("open", "label:not_looked_up"))
        self.assertEqual(states.ladder(st), "not_looked_up")
        self.assertEqual(states.word("ladder", "not_looked_up"), "XBRL instance not loaded")
        self.assertEqual(ties.check_columns(st), ("not_checked", "label:not_looked_up"))
        self.assertNotEqual(states.word("ladder", "not_looked_up"), states.word("check", "no_reference"))
        from ledger.web.cards import _how
        self.assertEqual(_how({**st, "ref": {}}, "ZZZ", {})["text"], "XBRL instance not loaded")
        # a tie or a second reading still checks it: they do not rest on the missing instance's empty tag
        self.assertEqual(status.of_fact(UNTAGGED, reading="0000000000-24-000001", looked_up=False)["state"], "checked")

    def test_the_ladder_is_the_machines_absent_state(self):
        self.assertEqual(states.LADDER.absent, "not_looked_up")
        self.assertEqual(states.LADDER.get("not_looked_up").kind, states.UNKNOWN)  # never good

    def test_a_tie_reads_a_stored_instance_xml_with_no_distilled_facts(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / "0000000001" / "filings").mkdir(parents=True)
        (d / "0000000001" / "filings" / "0000000001-25-000001.xml").write_bytes(XML)
        with mock.patch("ledger.ingest.edgar.RAW", d):
            got = ties.instance_totals(1, "0000000001-25-000001", {"PropertyPlantAndEquipmentGross"})
        self.assertEqual(got, {("0000000001-25-000001", "PropertyPlantAndEquipmentGross", "2024-12-31"): 1234})
        self.assertFalse((d / "0000000001" / "filings" / "0000000001-25-000001.facts.json").exists())  # read only, nothing written


class InstanceReading(unittest.TestCase):
    """Review of F17: one reading of an instance (ties.instance) for the ladder, the ties and the company's tag."""

    def _raw(self, name, body):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / "0000000001" / "filings").mkdir(parents=True)
        (d / "0000000001" / "filings" / name).write_bytes(body)
        return d

    def test_a_malformed_instance_is_unreadable_never_tags_nothing(self):
        for name, body in (("0000000001-25-000001.xml", b"<xbrl><not closed"), ("0000000001-25-000001.facts.json", b"{not json")):
            with mock.patch("ledger.ingest.edgar.RAW", self._raw(name, body)):
                self.assertEqual(ties.instance(1, "0000000001-25-000001"), ("unreadable", {}), name)
                self.assertEqual(ties.instance_totals(1, "0000000001-25-000001", {"PropertyPlantAndEquipmentGross"}), {})
                from ledger.checks import filertag, proof
                self.assertIsNone(filertag.instance(1, "0000000001-25-000001"))
                self.assertFalse(proof.instance_on_file(1, "0000000001-25-000001"))
        st = status.of_fact(UNTAGGED, looked_up="unreadable")
        self.assertEqual((st["state"], st["by"]), ("open", "label:not_looked_up"))
        self.assertIn("does not parse", st["reason"])

    def test_the_xml_is_parsed_once_per_file_version(self):
        d = self._raw("0000000001-25-000001.xml", XML)
        ties._INSTANCES.clear()
        with mock.patch("ledger.ingest.edgar.RAW", d), mock.patch("ledger.ingest.reference.dimensions.parse_instance", wraps=__import__("ledger.ingest.reference.dimensions", fromlist=["x"]).parse_instance) as p:
            for _ in range(3):
                self.assertEqual(ties.instance(1, "0000000001-25-000001")[0], "loaded")
        self.assertEqual(p.call_count, 1)

    def test_a_fact_the_ladder_did_not_see_is_not_looked_up(self):
        st, _ = ties.fact_state({**UNTAGGED, "accession": "x"}, {}, {})
        self.assertEqual(st["by"], "label:not_looked_up")  # no instance marker: never loaded by default


@unittest.skipUnless(store.DEFAULT_DB.exists(), "needs the working database")
class OnProof(unittest.TestCase):
    def test_proof_and_taxonomy_say_the_instance_was_not_loaded(self):
        from ledger.checks import proof
        from ledger.release import taxonomy
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        self.addCleanup(con.close)
        before = [i for i in proof.company(con, "MSFT")["stages"]["facts"]["all"] if i["by"] == "label:no_reference"]
        self.assertTrue(before)
        real = ties.instance
        gone_state = lambda state: (lambda cik, acc: (state, real(cik, acc)[1]))  # the totals stay; only the marker says the lookup did not answer
        with mock.patch("ledger.checks.ties.instance", side_effect=gone_state("absent")):
            items = proof.company(con, "MSFT")["stages"]["facts"]["all"]
            rows = [r for r in taxonomy.rows(con, ["MSFT"]) if r["check_method"] == "label:not_looked_up"]
        with mock.patch("ledger.checks.ties.instance", side_effect=gone_state("unreadable")):
            bad = [i for i in proof.company(con, "MSFT")["stages"]["facts"]["all"] if i["by"] == "label:not_looked_up"]
        self.assertEqual(len(bad), len(before))
        self.assertTrue(all(i["what"].endswith("XBRL instance unreadable") for i in bad))
        gone = [i for i in items if i["by"] == "label:not_looked_up"]
        self.assertEqual(len(gone), len(before))  # every citation-only fact, and nothing else
        self.assertTrue(all(i["state"] == "open" and i["what"].endswith("XBRL instance not loaded") and i["needs"] == "XBRL instance" for i in gone))
        self.assertFalse([i for i in items if i["by"] == "label:no_reference"])
        self.assertTrue(rows and all(r["check"] == "not_checked" for r in rows))


if __name__ == "__main__":
    unittest.main()
