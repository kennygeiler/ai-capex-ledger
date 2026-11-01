"""The mapping assistant (T33): the yaml writer keeps the header and format and refuses a duplicate or a member off the list;
the proposals log parses to the latest standing proposal per category with rejections honoured; the output contract;
the Reconcile group through workbench.items; POST /api/mapping through the real Handler (403 read-only, 400 bad member)."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from urllib import error, request
from http.server import ThreadingHTTPServer

import duckdb
import yaml

from ledger import mapper


_PEOPLE = None


def setUpModule():  # T80: config.PEOPLE fails closed; these tests confirm as placeholder people, never a real confirmer
    global _PEOPLE
    from ledger import config
    _PEOPLE = list(config.PEOPLE)
    config.PEOPLE[:] = _PEOPLE + ["A Tester", "No", "Bruno Runyon", "Kenny", "a test"]


def tearDownModule():
    from ledger import config
    config.PEOPLE[:] = _PEOPLE

HEADER = """# The company's own PP&E category, mapped to the nearest us-gaap PropertyPlantAndEquipmentByTypeAxis member.
#
# us-gaap members used: TechnologyEquipmentMember, LandMember,
# ConstructionInProgressMember, MachineryAndEquipmentMember.

MSFT:
  "Land": {standard_type: LandMember, evidence: "the note's own category name", by: Claude Fable 5.1, at: 2026-11-01, confirmed_by: A Tester, confirmed_at: 2026-11-02}
AMD:
  "Equipment": {standard_type: MachineryAndEquipmentMember, evidence: "equipment", by: Claude Fable 5.1, at: 2026-11-01}
"""


class Writer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "asset_types.yaml"
        self.path.write_text(HEADER)
        self.log = Path(self.tmp.name) / "proposals.jsonl"
        # the company's unmapped categories, as taxonomy.unmapped would report them from the database
        self.um = mock.patch.object(mapper, "_unmapped", side_effect=lambda con, t: {"MU": [{"ticker": "MU", "reported_name": "Construction in progress"}, {"ticker": "MU", "reported_name": "Software"}],
                                                                                   "MSFT": [{"ticker": "MSFT", "reported_name": "Servers"}]}.get(t, []))
        self.um.start()
        # T63: the company's reported categories whose entry no person confirmed, as taxonomy.to_confirm would report them
        self.tc = mock.patch.object(mapper, "_to_confirm", side_effect=lambda con, t: {"AMD": [{"ticker": "AMD", "reported_name": "Equipment", "standard_type": "MachineryAndEquipmentMember"}]}.get(t, []))
        self.tc.start()

    def tearDown(self):
        self.um.stop()
        self.tc.stop()
        self.tmp.cleanup()

    def test_approve_refuses_a_name_the_company_does_not_report_unmapped(self):
        before = self.path.read_text()
        for ticker, name in (("ZZZZ", "Not a category"), ("MU", "Land")):  # an unknown company; a name the notes never reported for it
            with self.assertRaises(ValueError) as c:
                mapper.approve(ticker, name, "LandMember", "land", "Kenny", path=self.path, log=self.log)
            self.assertIn("not one of the company's reported PP&E categories with no mapping", str(c.exception))
        self.assertEqual(self.path.read_text(), before)
        self.assertFalse(self.log.exists())

    def test_members_come_from_the_header(self):
        self.assertEqual(mapper.members(self.path), ["TechnologyEquipmentMember", "LandMember", "ConstructionInProgressMember", "MachineryAndEquipmentMember"])
        self.assertIn("TechnologyEquipmentMember", mapper.members())  # the real file
        self.assertGreaterEqual(len(mapper.members()), 14)

    def test_approve_appends_under_the_ticker_and_keeps_the_header(self):
        e = mapper.approve("MU", "Construction in progress", "ConstructionInProgressMember", "Construction in progress(2)", "Kenny Geiler", path=self.path, log=self.log, at="2026-11-02")
        e2 = mapper.approve("msft", "Servers", "TechnologyEquipmentMember", 'servers, "network" gear', "Kenny Geiler", path=self.path, log=self.log, at="2026-11-02")
        text = self.path.read_text()
        self.assertTrue(text.startswith(HEADER.split("\n\nMSFT:")[0]))  # the comment header, byte for byte
        lines = text.splitlines()
        self.assertEqual(lines[lines.index("MSFT:") + 2], '  "Servers": {standard_type: TechnologyEquipmentMember, evidence: "servers, \\"network\\" gear", by: Kenny Geiler, at: 2026-11-02, confirmed_by: Kenny Geiler, confirmed_at: 2026-11-02}')
        self.assertEqual(lines[-2:], ["MU:", '  "Construction in progress": {standard_type: ConstructionInProgressMember, evidence: "Construction in progress(2)", by: Kenny Geiler, at: 2026-11-02, confirmed_by: Kenny Geiler, confirmed_at: 2026-11-02}'])
        d = yaml.safe_load(text)
        got = d["MU"]["Construction in progress"]
        self.assertEqual({**got, "at": str(got["at"]), "confirmed_at": str(got["confirmed_at"])}, {"standard_type": "ConstructionInProgressMember", "evidence": "Construction in progress(2)", "by": "Kenny Geiler", "at": "2026-11-02",
                                                                                            "confirmed_by": "Kenny Geiler", "confirmed_at": "2026-11-02"})  # yaml reads `at` as a date, as it does the existing entries; a person's approval is their confirmation (T63)
        self.assertEqual(d["MSFT"]["Servers"]["evidence"], 'servers, "network" gear')
        self.assertEqual(d["AMD"]["Equipment"]["standard_type"], "MachineryAndEquipmentMember")  # untouched
        self.assertEqual((e["ticker"], e2["ticker"]), ("MU", "MSFT"))
        self.assertEqual([l["kind"] for l in mapper.load_proposals(self.log)], ["approved", "approved"])

    def test_approve_refuses_a_duplicate_and_a_member_off_the_list(self):
        before = self.path.read_text()
        with self.assertRaises(ValueError) as c:
            mapper.approve("MSFT", "Land", "LandMember", "land", "Kenny", path=self.path, log=self.log)
        self.assertIn("already mapped", str(c.exception))
        self.assertIn("confirmed by A Tester", str(c.exception))
        with self.assertRaises(ValueError) as c:
            mapper.approve("MU", "Software", "SoftwareAndSoftwareDevelopmentCostsMember", "software", "Kenny", path=self.path, log=self.log)
        self.assertIn("not a member on the list", str(c.exception))
        with self.assertRaises(ValueError):
            mapper.approve("MU", "Software", "LandMember", "software", "", path=self.path, log=self.log)  # no name, no write
        self.assertEqual(self.path.read_text(), before)
        self.assertFalse(self.log.exists())


class Confirm(unittest.TestCase):
    """T63: an entry without confirmed_by is a proposal. Approve adds confirmed_by and confirmed_at to its line, Edit
    replaces it with the person's member (confirmed), Reject removes it and logs the member; a confirmed entry stays."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "asset_types.yaml"
        self.path.write_text(HEADER)
        self.log = Path(self.tmp.name) / "proposals.jsonl"
        self.tc = mock.patch.object(mapper, "_to_confirm", side_effect=lambda con, t: {"AMD": [{"ticker": "AMD", "reported_name": "Equipment", "standard_type": "MachineryAndEquipmentMember"}]}.get(t, []))
        self.tc.start()
        self.patch = mock.patch.object(mapper, "ASSET_TYPES", self.path)
        self.patch.start()

    def tearDown(self):
        self.tc.stop()
        self.patch.stop()
        self.tmp.cleanup()

    def test_approve_confirms_the_line_in_place(self):
        before = self.path.read_text().splitlines()
        e = mapper.approve("AMD", "Equipment", "MachineryAndEquipmentMember", "equipment", "A Tester", path=self.path, log=self.log, at="2026-11-03")
        after = self.path.read_text().splitlines()
        self.assertEqual(after[-1], '  "Equipment": {standard_type: MachineryAndEquipmentMember, evidence: "equipment", by: Claude Fable 5.1, at: 2026-11-01, confirmed_by: A Tester, confirmed_at: 2026-11-03}')
        self.assertEqual(after[:-1], before[:-1])  # nothing else moved
        self.assertEqual((e["by"], e["confirmed_by"], e["confirmed_at"]), ("Claude Fable 5.1", "A Tester", "2026-11-03"))  # the proposer stays named
        self.assertEqual([l["kind"] for l in mapper.load_proposals(self.log)], ["confirmed"])
        from ledger import status
        self.assertTrue(status.confirmed(yaml.safe_load(self.path.read_text())["AMD"]["Equipment"]))
        with self.assertRaises(ValueError) as c:  # once confirmed, it is a person's: not confirmed twice, not replaced
            mapper.approve("AMD", "Equipment", "LandMember", "equipment", "A Tester", path=self.path, log=self.log)
        self.assertIn("already mapped", str(c.exception))

    def test_edit_replaces_the_proposal_with_the_persons_member(self):
        e = mapper.approve("AMD", "Equipment", "TechnologyEquipmentMember", "test equipment and computers", "A Tester", path=self.path, log=self.log, at="2026-11-03")
        self.assertEqual(self.path.read_text().splitlines()[-1], '  "Equipment": {standard_type: TechnologyEquipmentMember, evidence: "test equipment and computers", by: A Tester, at: 2026-11-03, confirmed_by: A Tester, confirmed_at: 2026-11-03}')
        self.assertEqual(e["replaced"]["standard_type"], "MachineryAndEquipmentMember")
        self.assertEqual(mapper.load_proposals(self.log)[0]["kind"], "approved")

    def test_approve_refuses_an_entry_the_company_does_not_report(self):
        before = self.path.read_text()
        with mock.patch.object(mapper, "_to_confirm", return_value=[]):
            with self.assertRaises(ValueError) as c:
                mapper.approve("AMD", "Equipment", "MachineryAndEquipmentMember", "equipment", "A Tester", path=self.path, log=self.log)
        self.assertIn("unconfirmed mapping", str(c.exception))
        self.assertEqual(self.path.read_text(), before)

    def test_reject_removes_an_unconfirmed_entry_and_logs_the_member(self):
        r = mapper.reject("AMD", "Equipment", "MachineryAndEquipmentMember", "A Tester", "the note says test equipment", path=self.log)
        d = yaml.safe_load(self.path.read_text())
        self.assertNotIn("Equipment", d.get("AMD") or {})
        self.assertEqual(d["MSFT"]["Land"]["standard_type"], "LandMember")
        self.assertEqual((r["kind"], r["removed_entry"]["by"]), ("rejected", "Claude Fable 5.1"))
        self.assertEqual(mapper.by_name("AMD", mapper.load_proposals(self.log))["Equipment"]["rejected"], ["MachineryAndEquipmentMember"])  # the next run proposes another
        self.assertTrue(self.path.read_text().startswith(HEADER.split("\n\nMSFT:")[0]))

    def test_reject_never_removes_a_confirmed_entry(self):
        before = self.path.read_text()
        with self.assertRaises(ValueError) as c:
            mapper.reject("MSFT", "Land", "LandMember", "A Tester", path=self.log)
        self.assertIn("confirmed by A Tester", str(c.exception))
        self.assertEqual(self.path.read_text(), before)
        r = mapper.reject("MSFT", "Land", "LandAndBuildingMember", "A Tester", path=self.log)  # a different member: logged, the entry untouched
        self.assertNotIn("removed_entry", r)
        self.assertEqual(self.path.read_text(), before)


class Confirmed(unittest.TestCase):
    def test_confirmed_is_a_field_check(self):
        from ledger import status
        self.assertFalse(status.confirmed(None))
        self.assertFalse(status.confirmed({"standard_type": "LandMember", "by": "Claude Fable 5.1"}))
        self.assertFalse(status.confirmed({"standard_type": "LandMember", "by": "Kenny, confirmed", "evidence": "confirmed by a person"}))  # never a phrase
        self.assertFalse(status.confirmed({"standard_type": "LandMember", "confirmed_by": "  "}))
        self.assertTrue(status.confirmed({"standard_type": "LandMember", "confirmed_by": "A Tester"}))

    def test_of_mapping(self):
        from ledger import status
        self.assertEqual({k: v for k, v in status.of_mapping({"standard_type": "LandMember", "confirmed_by": "A Tester"}).items() if k != "reason"}, {"state": "checked", "by": "mapping:LandMember", "keys": [], "key": None})
        st = status.of_mapping({"standard_type": "LandMember", "by": "Claude Fable 5.1"})
        self.assertEqual((st["state"], st["by"]), ("open", "label:to_confirm"))
        self.assertIn("Claude Fable 5.1", st["reason"])
        self.assertEqual(status.of_mapping(None)["state"], "open")

    def test_an_unconfirmed_mapping_fails_g6_under_its_company(self):
        from ledger.release import gates
        g = gates([], [], {"values": []}, tickers=["NVDA"], mappings=[{"ticker": "NVDA", "reported_name": "Land"}, {"ticker": "TSLA", "reported_name": "Land"}])
        self.assertEqual(g["G6"], {"NVDA": ["asset_types|NVDA|Land"], "TSLA": ["asset_types|TSLA|Land"]})

    def test_the_taxonomy_lists_what_waits_for_a_person(self):
        from ledger import taxonomy
        types = {"MU": {"Land": {"standard_type": "LandMember", "by": "Claude Fable 5.1", "at": "2026-11-01"}, "Equipment": {"standard_type": "MachineryAndEquipmentMember", "by": "A Tester", "confirmed_by": "A Tester"}}}
        with mock.patch.object(taxonomy, "asset_types", return_value=types):
            got = taxonomy.to_confirm(_con(), ["MU"])
        self.assertEqual([(g["ticker"], g["reported_name"], g["standard_type"]) for g in got], [("MU", "Land", "LandMember")])

    def test_filer_member_and_mismatch(self):
        """Read from the distilled instance on disk only; a zero never matches; two members on one value are ambiguous;
        no instance on disk is None (not checked), never 'tags nothing'."""
        from ledger.ingest import edgar
        con = _con()
        con.execute("alter table facts add column accession text")
        con.execute("update facts set accession = 'acc1'")
        con.execute("insert into facts values ('MU','ppe_category','Other equipment','FY2026',5e6,'agree','5000000','2026-09-03','acc1'), ('MU','ppe_category','Leasehold','FY2026',7e6,'agree','7000000','2026-09-03','acc1'),"
                    " ('MU','ppe_category','Empty','FY2026',0,'agree','0','2026-09-03','acc1'), ('MU','ppe_category','Elsewhere','FY2026',1e6,'agree','1000000','2026-09-03','acc2')")
        con.execute("insert into documents values ('acc2','MU',723125,'2025-10-09','x','u')")
        inst = {"PropertyPlantAndEquipmentGross\tus-gaap:EquipmentMember\t2026-09-03": 5000000, "PropertyPlantAndEquipmentGross\tus-gaap:LandMember\t2026-09-03": 420000000,
                "PropertyPlantAndEquipmentGross\t\t2026-09-03": 5000000, "PropertyPlantAndEquipmentGross\tus-gaap:LeaseholdImprovementsMember\t2026-09-03": 7000000,
                "PropertyPlantAndEquipmentGross\tus-gaap:BuildingMember\t2026-09-03": 7000000, "PropertyPlantAndEquipmentGross\tus-gaap:FurnitureAndFixturesMember\t2026-09-03": 0}
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "0000723125" / "filings").mkdir(parents=True)
            (raw / "0000723125" / "filings" / "acc1.facts.json").write_text(json.dumps(inst))  # acc2 has no instance on disk
            with mock.patch.object(edgar, "RAW", raw), mock.patch("ledger.reference.dimensions.instance_facts", side_effect=AssertionError("no fetch on a page read")):
                got = mapper.filer_members(con, "MU", ["Other equipment", "Land", "Equipment", "Leasehold", "Empty", "Elsewhere"])
        self.assertEqual(got["Other equipment"], {"members": ["us-gaap:EquipmentMember"], "ambiguous": False})  # the total (no member) never counts
        self.assertEqual(got["Land"], {"members": ["us-gaap:LandMember"], "ambiguous": False})
        self.assertEqual(got["Equipment"], {"members": [], "ambiguous": False})  # checked: nothing tagged with that value
        self.assertEqual(got["Leasehold"], {"members": ["us-gaap:BuildingMember", "us-gaap:LeaseholdImprovementsMember"], "ambiguous": True})
        self.assertEqual(got["Empty"], {"members": [], "ambiguous": False})  # a zero matches nothing
        self.assertIsNone(got["Elsewhere"])  # no instance on disk: not checked
        self.assertTrue(mapper.mismatch("OtherMachineryAndEquipmentMember", got["Other equipment"]))
        self.assertFalse(mapper.mismatch("EquipmentMember", got["Other equipment"]))
        self.assertFalse(mapper.mismatch("LandAndBuildingMember", got["Leasehold"]))  # ambiguous: never a mismatch
        self.assertFalse(mapper.mismatch("TechnologyEquipmentMember", {"members": ["amzn:ServersAndNetworkingEquipmentMember"], "ambiguous": False}))  # extension: nothing to compare
        self.assertFalse(mapper.mismatch("LandMember", None))

    def test_filer_members_failure_is_not_checked(self):
        con = duckdb.connect()  # no facts table: the query fails
        self.assertEqual(mapper.filer_members(con, "MU", ["Land"]), {"Land": None})

    def test_an_entry_with_no_member_is_unmapped(self):
        from ledger import proof, status, taxonomy
        types = {"MU": {"Land": {"evidence": "land", "by": "a test"}}}
        with mock.patch.object(taxonomy, "asset_types", return_value=types):
            self.assertEqual(taxonomy.unmapped(_con(), ["MU"]), [{"ticker": "MU", "reported_name": "Equipment"}, {"ticker": "MU", "reported_name": "Land"}])
            self.assertEqual(taxonomy.to_confirm(_con(), ["MU"]), [])
        self.assertEqual(status.of_mapping(types["MU"]["Land"])["reason"], status.UNMAPPED)

    def test_the_taxonomy_rows_of_an_unconfirmed_entry_are_not_mapped(self):
        """T63 review: the exported rows of an entry no person confirmed read mapped false, check to_confirm."""
        from ledger import taxonomy
        con = _con()
        for t, cols in (("extractions", "extraction_id text, accession text, table_id text, row_label text, cell_text text, ticker text"),):
            con.execute(f"create table {t} ({cols})")
        con.execute("alter table facts add column accession text")
        con.execute("alter table facts add column extraction_ids text")
        con.execute("alter table \"values\" add column period_end text")
        con.execute("alter table \"values\" add column extraction_ids text")
        types = {"MU": {"Land": {"standard_type": "LandMember", "evidence": "land", "by": "Claude Fable 5.1"},
                        "Equipment": {"standard_type": "MachineryAndEquipmentMember", "evidence": "equipment", "by": "a test", "confirmed_by": "a test", "confirmed_at": "2026-11-02"}}}
        with mock.patch.object(taxonomy, "asset_types", return_value=types), mock.patch.object(taxonomy, "_restated", return_value=None):
            rows = {r["reported_name"]: r for r in taxonomy.rows(con, ["MU"]) if r["measure"] == "derived"}
        self.assertEqual((rows["Land"]["mapped"], rows["Land"]["check"], rows["Land"]["check_method"], rows["Land"]["standard_type"]), (False, "to_confirm", "label:to_confirm", "LandMember"))
        self.assertEqual((rows["Equipment"]["mapped"], rows["Equipment"]["check"], rows["Equipment"]["check_method"]), (True, "agree", "xbrl"))


class Hardening(unittest.TestCase):
    """T63 review: one locked, atomic, whole-file-checked write; odd headers refused; names YAML would misread quoted;
    a model's name never confirms."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "asset_types.yaml"
        self.log = Path(self.tmp.name) / "proposals.jsonl"
        self.name = 'Land, buildings and "leasehold" improvements'
        self.path.write_text(HEADER + f'MU:\n  {json.dumps(self.name)}: {{standard_type: ConstructionInProgressMember, evidence: "land", by: Claude Fable 5.1, at: 2026-11-01}}\n')
        self.tc = mock.patch.object(mapper, "_to_confirm", return_value=[{"ticker": "MU", "reported_name": self.name}])
        self.um = mock.patch.object(mapper, "_unmapped", return_value=[{"ticker": "MU", "reported_name": "No"}])
        self.tc.start(); self.um.start()
        self.patch = mock.patch.object(mapper, "ASSET_TYPES", self.path)
        self.patch.start()

    def tearDown(self):
        self.tc.stop(); self.um.stop(); self.patch.stop()
        self.tmp.cleanup()

    def test_a_name_with_a_comma_and_quotes_through_approve_edit_and_reject(self):
        mapper.approve("MU", self.name, "ConstructionInProgressMember", "land", "No", path=self.path, log=self.log, at="2026-11-03")  # a confirmer called No stays a string
        e = yaml.safe_load(self.path.read_text())["MU"][self.name]
        self.assertEqual((e["confirmed_by"], str(e["confirmed_at"]), e["by"]), ("No", "2026-11-03", "Claude Fable 5.1"))
        self.path.write_text(self.path.read_text().replace(", confirmed_by: \"No\", confirmed_at: 2026-11-03", ""))  # back to a proposal
        mapper.approve("MU", self.name, "LandMember", "land only", "A Tester", path=self.path, log=self.log, at="2026-11-03")
        self.assertEqual(yaml.safe_load(self.path.read_text())["MU"][self.name]["standard_type"], "LandMember")
        self.path.write_text(HEADER + f'MU:\n  {json.dumps(self.name)}: {{standard_type: ConstructionInProgressMember, evidence: "land", by: Claude Fable 5.1, at: 2026-11-01}}\n')
        mapper.reject("MU", self.name, "ConstructionInProgressMember", "A Tester", path=self.log)
        self.assertNotIn(self.name, yaml.safe_load(self.path.read_text())["MU"] or {})
        mapper.approve("MU", "No", "LandMember", "no", "A Tester", path=self.path, log=self.log, at="2026-11-03")  # a name YAML would read as false
        self.assertIn("No", yaml.safe_load(self.path.read_text())["MU"])

    def test_a_duplicate_or_odd_ticker_header_is_refused(self):
        for extra in ('"MU":\n  "Other": {standard_type: LandMember, evidence: "x", by: a, at: 2026-11-01, confirmed_by: a, confirmed_at: 2026-11-01}\n',
                      'MU: # a second block\n'):
            text = self.path.read_text().split("MU:\n")[0] + extra + "MU:\n" + self.path.read_text().split("MU:\n")[1]
            self.path.write_text(text)
            for call in (lambda: mapper.approve("MU", self.name, "ConstructionInProgressMember", "land", "A Tester", path=self.path, log=self.log),
                         lambda: mapper.reject("MU", self.name, "ConstructionInProgressMember", "A Tester", path=self.log)):
                with self.assertRaises(ValueError) as c:
                    call()
                self.assertIn("blocks for MU", str(c.exception))
            self.assertEqual(self.path.read_text(), text)

    def test_the_write_refuses_any_change_beyond_the_entry(self):
        before = self.path.read_text()
        with self.assertRaises(ValueError) as c:
            mapper._edit(self.path, "MU", self.name, lambda lines, data: ([l for l in lines if "MSFT" not in l and '"Land": {' not in l], data["MU"][self.name]))
        self.assertIn("more than the one entry", str(c.exception))
        self.assertEqual(self.path.read_text(), before)
        self.assertEqual(sorted(p.name for p in Path(self.tmp.name).iterdir() if p.suffix == ".tmp"), [])  # no temporary file left

    def test_reject_sees_a_confirmation_written_after_its_caller_looked(self):
        """The check and the removal are one snapshot under the lock: a line confirmed meanwhile is never removed."""
        self.path.write_text(HEADER + f'MU:\n  {json.dumps(self.name)}: {{standard_type: ConstructionInProgressMember, evidence: "land", by: Claude Fable 5.1, at: 2026-11-01, confirmed_by: A Tester, confirmed_at: 2026-11-02}}\n')
        before = self.path.read_text()
        with self.assertRaises(ValueError) as c:
            mapper.reject("MU", self.name, "ConstructionInProgressMember", "A Tester", path=self.log)
        self.assertIn("confirmed by A Tester", str(c.exception))
        self.assertEqual(self.path.read_text(), before)
        self.assertFalse(self.log.exists())

    def test_a_model_never_confirms(self):
        before = self.path.read_text()
        for who in ("Claude Fable 5.1", "claude", "Opus", "the mapper agent", "Replication run", "Sonnet 4", "HAIKU"):
            with self.assertRaises(ValueError) as c:
                mapper.approve("MU", self.name, "ConstructionInProgressMember", "land", who, path=self.path, log=self.log)
            self.assertIn("not a person's name", str(c.exception))
        self.assertEqual(self.path.read_text(), before)
        self.assertEqual(mapper.person("Bruno Runyon"), "Bruno Runyon")  # whole words only (on config.PEOPLE for this test)
        with self.assertRaises(ValueError) as c:
            mapper.person("Gemini")
        with self.assertRaises(ValueError) as c:
            mapper.person("Somebody Else")  # T80: not on config.PEOPLE
        self.assertIn("config.PEOPLE", str(c.exception))


class Proposals(unittest.TestCase):
    def test_latest_proposal_stands_unless_rejected(self):
        lines = [{"kind": "proposed", "ticker": "MU", "reported_name": "Equipment", "standard_type": "TechnologyEquipmentMember", "at": "1"},
                 {"kind": "rejected", "ticker": "MU", "reported_name": "Equipment", "standard_type": "TechnologyEquipmentMember", "by": "K", "at": "2"},
                 {"kind": "proposed", "ticker": "MU", "reported_name": "Land", "standard_type": "LandMember", "at": "3"},
                 {"kind": "proposed", "ticker": "AMD", "reported_name": "Land", "standard_type": "LandMember", "at": "3"}]
        idx = mapper.by_name("MU", lines)
        self.assertIsNone(idx["Equipment"]["proposal"])
        self.assertEqual(idx["Equipment"]["rejected"], ["TechnologyEquipmentMember"])
        self.assertEqual(idx["Land"]["proposal"]["standard_type"], "LandMember")
        self.assertNotIn("AMD", idx)
        lines.append({"kind": "proposed", "ticker": "MU", "reported_name": "Equipment", "standard_type": "MachineryAndEquipmentMember", "at": "4"})
        self.assertEqual(mapper.by_name("MU", lines)["Equipment"]["proposal"]["standard_type"], "MachineryAndEquipmentMember")

    def test_the_task_names_rejected_members(self):
        task = mapper.make_task("MU", ["Equipment", "Land"], [], {"Equipment": ["TechnologyEquipmentMember"]}, ["LandMember", "MachineryAndEquipmentMember"])
        self.assertIn('- "Equipment"  (a person rejected: TechnologyEquipmentMember', task)
        self.assertIn("- LandMember\n- MachineryAndEquipmentMember", task)
        self.assertIn("Prompt version: mapper@v1", task)

    def test_validate_output(self):
        task = mapper.make_task("MU", ["Equipment", "Land"], [{"before": "Note 7", "table": "Rows: Land | 420\n Equipment(1) | 93,954", "accession": "a", "table_id": "t1", "filed": "2026"}], None, ["LandMember", "MachineryAndEquipmentMember"])
        ok = {"ticker": "MU", "prompt_version": "mapper@v1", "proposals": [
            {"reported_name": "Equipment", "standard_type": "MachineryAndEquipmentMember", "evidence": "Equipment(1)", "confidence": "medium", "reason": "r"},
            {"reported_name": "Land", "standard_type": "none", "evidence": "Land", "confidence": "low", "reason": "r"}]}
        mapper.validate_output(ok, "MU", ["Equipment", "Land"], task, ["LandMember", "MachineryAndEquipmentMember"])
        bad = [({**ok, "proposals": ok["proposals"][:1]}, "no proposal for"),
               ({**ok, "proposals": [{**ok["proposals"][0], "standard_type": "ServersMember"}, ok["proposals"][1]]}, "not on the allowed list"),
               ({**ok, "proposals": [{**ok["proposals"][0], "evidence": "servers and GPUs"}, ok["proposals"][1]]}, "not whole words of the note"),
               ({**ok, "proposals": [{**ok["proposals"][0], "evidence": "Allowed members"}, ok["proposals"][1]]}, "not whole words of the note"),  # a heading of the task, not the note
               ({**ok, "proposals": [{**ok["proposals"][0], "evidence": "Categories to map"}, ok["proposals"][1]]}, "not whole words of the note"),
               ({**ok, "proposals": [{**ok["proposals"][0], "evidence": "MachineryAndEquipmentMember"}, ok["proposals"][1]]}, "not whole words of the note"),  # a member name from the list
               ({**ok, "proposals": [{**ok["proposals"][0], "evidence": "quipment(1"}, ok["proposals"][1]]}, "not whole words of the note"),  # part of a word
               ({**ok, "proposals": [{**ok["proposals"][0], "confidence": 0.9}, ok["proposals"][1]]}, "confidence"),
               ({**ok, "proposals": [{**ok["proposals"][0], "reported_name": "Buildings"}, ok["proposals"][1]]}, "not one of the categories"),
               ({**ok, "ticker": "AMD"}, "ticker")]
        for obj, why in bad:
            with self.assertRaises(mapper.Invalid) as c:
                mapper.validate_output(obj, "MU", ["Equipment", "Land"], task, ["LandMember", "MachineryAndEquipmentMember"])
            self.assertIn(why, c.exception.reason)


def _con():
    con = duckdb.connect()
    con.execute("create table facts (ticker text, field text, dimension text, period text, value double, label text, reference text, period_end text)")
    con.execute("insert into facts values ('MU','ppe_category','Equipment','FY2026',93954e6,'agree','93954000000','2026-09-03'), ('MU','ppe_category','Land','FY2026',420e6,'agree','420000000','2026-09-03'), ('MSFT','ppe_category','Land','FY2026',1e6,'agree','1000000','2026-06-30')")
    con.execute("create table documents (accession text, ticker text, cik integer, filed text, tables_path text, url text)")
    con.execute("create table note_extractions (extraction_id text, ticker text, accession text, table_id text, row_label text, cell_text text, field text, dimension text)")
    con.execute("insert into note_extractions values ('e1','MU','acc1','t0025','Equipment(1)','93,954','ppe_category','Equipment')")
    con.execute("insert into documents values ('acc1','MU',723125,'2026-10-09','data/docs/none/missing.json','u')")  # not on disk: the group still renders, without the note's words
    con.execute('create table "values" (ticker text, field text, period text, value double, label text)')
    return con


class Group(unittest.TestCase):
    def test_reconcile_group_shape(self):
        from ledger import workbench
        lines = [{"kind": "proposed", "ticker": "MU", "reported_name": "Equipment", "standard_type": "MachineryAndEquipmentMember", "evidence": "Equipment(1)", "confidence": "medium", "reason": "r", "prompt_version": "mapper@v1", "model": "m", "at": "2026-11-01T00:00:00+00:00"}]
        flow = {"scope": "MU", "tickers": ["MU"], "names": {"MU": "Micron"}, "release": {"last": None}, "changed": {"last_run": None}, "queue": []}
        with mock.patch.object(mapper, "load_proposals", return_value=lines), mock.patch("ledger.resolutions.unconfirmed", return_value=[]):
            out = workbench.items(_con(), flow)
        rows = [r for r in out["rows"] if r["cause"] == "asset_types"]
        self.assertEqual([r["where"] for r in rows], ["Equipment", "Land"])  # MU has no entries in the real file; both are open
        eq = rows[0]
        self.assertEqual((eq["key"], eq["state"], eq["open"], eq["action"], eq["ticker"], eq["name"]), ("asset_types|MU|Equipment", "open", True, "mapping", "MU", "Micron"))
        self.assertEqual(eq["evidence"]["proposal"]["standard_type"], "MachineryAndEquipmentMember")
        self.assertEqual((eq["evidence"]["reported_name"], eq["evidence"]["rejected"], eq["evidence"]["note"]), ("Equipment", [], None))
        self.assertIsNone(rows[1]["evidence"]["proposal"])
        self.assertEqual(out["open"], 2)
        self.assertIn("TechnologyEquipmentMember", out["members"])
        cause = next(c for c in out["causes"] if c["cause"] == "asset_types")
        self.assertEqual((cause["rows"], cause["open"]), (2, 2))
        self.assertEqual(eq["evidence"]["mapping"], "unmapped")

    def test_an_unconfirmed_entry_is_an_open_row_to_confirm(self):
        """T63: MSFT's Land has an entry with no confirmed_by: an open row, by label:to_confirm, the entry as its proposal."""
        from ledger import workbench
        flow = {"scope": "MSFT", "tickers": ["MSFT"], "names": {"MSFT": "Microsoft"}, "release": {"last": None}, "changed": {"last_run": None}, "queue": []}
        types = {"MSFT": {"Land": {"standard_type": "LandMember", "evidence": "the note's own category name", "by": "Claude Fable 5.1", "at": "2026-11-01"}}}
        with mock.patch("ledger.taxonomy.asset_types", return_value=types), mock.patch.object(mapper, "load_proposals", return_value=[]), mock.patch("ledger.resolutions.unconfirmed", return_value=[]):
            out = workbench.items(_con(), flow)
            types["MSFT"]["Land"]["confirmed_by"] = "A Tester"
            after = workbench.items(_con(), flow)
        row = next(r for r in out["rows"] if r["cause"] == "asset_types")
        self.assertEqual((row["where"], row["state"], row["open"], row["by"]), ("Land", "open", True, "label:to_confirm"))
        self.assertEqual((row["evidence"]["mapping"], row["evidence"]["proposal"]["standard_type"], row["evidence"]["proposal"]["by"]), ("to_confirm", "LandMember", "Claude Fable 5.1"))
        self.assertEqual([r for r in after["rows"] if r["cause"] == "asset_types"], [])  # confirmed: off the group


class Route(unittest.TestCase):
    def _serve(self):
        from ledger import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        return f"http://127.0.0.1:{srv.server_address[1]}"

    def _post(self, url, body):
        req = request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_mapping_route(self):
        from ledger import app
        base = self._serve()
        with tempfile.TemporaryDirectory() as tmp:
            path, log = Path(tmp) / "asset_types.yaml", Path(tmp) / "p.jsonl"
            path.write_text(HEADER)
            body = {"ticker": "MU", "reported_name": "Land", "standard_type": "LandMember", "evidence": "Land", "by": "Kenny Geiler"}
            with mock.patch.object(app, "READONLY", True):
                code, d = self._post(base + "/api/mapping", body)
            self.assertEqual(code, 403)
            self.assertIn("read-only", d["error"])
            um = [{"ticker": "MU", "reported_name": "Land"}, {"ticker": "MU", "reported_name": "Equipment"}]
            with mock.patch.object(mapper, "ASSET_TYPES", path), mock.patch.object(mapper, "PROPOSALS", log), mock.patch.object(mapper, "unmapped", return_value=um), mock.patch("ledger.app._con", return_value=mock.MagicMock()):
                code, d = self._post(base + "/api/mapping", {**body, "standard_type": "SoftwareAndSoftwareDevelopmentCostsMember"})
                self.assertEqual(code, 400)
                self.assertIn("not a member on the list", d["error"])
                code, d = self._post(base + "/api/mapping", {**body, "ticker": "ZZZZ", "reported_name": "Not a category"})  # not an unmapped category of any company
                self.assertEqual(code, 400)
                self.assertIn("not one of the company's reported PP&E categories", d["error"])
                self.assertEqual(path.read_text(), HEADER)
                code, d = self._post(base + "/api/mapping", {**body, "by": "Claude Fable 5.1"})  # T63: a model never confirms
                self.assertEqual(code, 400)
                self.assertIn("not a person's name", d["error"])
                code, d = self._post(base + "/api/mapping", body)
                self.assertEqual(code, 200)
                self.assertEqual((d["ticker"], d["standard_type"], d["by"]), ("MU", "LandMember", "Kenny Geiler"))
                self.assertEqual(yaml.safe_load(path.read_text())["MU"]["Land"]["standard_type"], "LandMember")
                code, d = self._post(base + "/api/mapping", body)  # the same again: refused
                self.assertEqual(code, 400)
                self.assertIn("already mapped", d["error"])
                code, d = self._post(base + "/api/mapping/reject", {"ticker": "MU", "reported_name": "Equipment", "standard_type": "TechnologyEquipmentMember", "by": "Kenny Geiler"})
                self.assertEqual((code, d["kind"]), (200, "rejected"))
                code, d = self._post(base + "/api/mapping/reject", {"ticker": "MU", "reported_name": "Equipment", "standard_type": "", "by": "Kenny Geiler"})
                self.assertEqual(code, 400)
                self.assertEqual([l["kind"] for l in mapper.load_proposals(log)], ["approved", "rejected"])


if __name__ == "__main__":
    unittest.main()
