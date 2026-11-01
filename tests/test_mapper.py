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

HEADER = """# The company's own PP&E category, mapped to the nearest us-gaap PropertyPlantAndEquipmentByTypeAxis member.
#
# us-gaap members used: TechnologyEquipmentMember, LandMember,
# ConstructionInProgressMember, MachineryAndEquipmentMember.

MSFT:
  "Land": {standard_type: LandMember, evidence: "the note's own category name", by: Claude Fable 5.1, at: 2026-11-01}
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

    def tearDown(self):
        self.um.stop()
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
        self.assertEqual(lines[lines.index("MSFT:") + 2], '  "Servers": {standard_type: TechnologyEquipmentMember, evidence: "servers, \\"network\\" gear", by: Kenny Geiler, at: 2026-11-02}')
        self.assertEqual(lines[-2:], ["MU:", '  "Construction in progress": {standard_type: ConstructionInProgressMember, evidence: "Construction in progress(2)", by: Kenny Geiler, at: 2026-11-02}'])
        d = yaml.safe_load(text)
        self.assertEqual({**d["MU"]["Construction in progress"], "at": str(d["MU"]["Construction in progress"]["at"])}, {"standard_type": "ConstructionInProgressMember", "evidence": "Construction in progress(2)", "by": "Kenny Geiler", "at": "2026-11-02"})  # yaml reads `at` as a date, as it does the existing entries
        self.assertEqual(d["MSFT"]["Servers"]["evidence"], 'servers, "network" gear')
        self.assertEqual(d["AMD"]["Equipment"]["standard_type"], "MachineryAndEquipmentMember")  # untouched
        self.assertEqual((e["ticker"], e2["ticker"]), ("MU", "MSFT"))
        self.assertEqual([l["kind"] for l in mapper.load_proposals(self.log)], ["approved", "approved"])

    def test_approve_refuses_a_duplicate_and_a_member_off_the_list(self):
        before = self.path.read_text()
        with self.assertRaises(ValueError) as c:
            mapper.approve("MSFT", "Land", "LandMember", "land", "Kenny", path=self.path, log=self.log)
        self.assertIn("already mapped", str(c.exception))
        with self.assertRaises(ValueError) as c:
            mapper.approve("MU", "Software", "SoftwareAndSoftwareDevelopmentCostsMember", "software", "Kenny", path=self.path, log=self.log)
        self.assertIn("not a member on the list", str(c.exception))
        with self.assertRaises(ValueError):
            mapper.approve("MU", "Software", "LandMember", "software", "", path=self.path, log=self.log)  # no name, no write
        self.assertEqual(self.path.read_text(), before)
        self.assertFalse(self.log.exists())


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
        self.assertEqual([r["where"] for r in rows], ["Equipment", "Land"])  # MSFT's Land is mapped in the real file; MU's two are open
        eq = rows[0]
        self.assertEqual((eq["key"], eq["state"], eq["open"], eq["action"], eq["ticker"], eq["name"]), ("asset_types|MU|Equipment", "open", True, "mapping", "MU", "Micron"))
        self.assertEqual(eq["evidence"]["proposal"]["standard_type"], "MachineryAndEquipmentMember")
        self.assertEqual((eq["evidence"]["reported_name"], eq["evidence"]["rejected"], eq["evidence"]["note"]), ("Equipment", [], None))
        self.assertIsNone(rows[1]["evidence"]["proposal"])
        self.assertEqual(out["open"], 2)
        self.assertIn("TechnologyEquipmentMember", out["members"])
        cause = next(c for c in out["causes"] if c["cause"] == "asset_types")
        self.assertEqual((cause["rows"], cause["open"]), (2, 2))


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
