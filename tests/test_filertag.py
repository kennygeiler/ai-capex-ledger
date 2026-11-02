"""The company's own tag as evidence for a category mapping (ledger/filertag.py) and the decision card (ledger/mapcard.py).

Pre-mortem tests: an ambiguous value match, a zero-valued category, members that differ by year, a company extension
member, an instance not on file, a partial tag, a forged or stale `mapping:filer_tag` refused by the walk, a person's
confirmation standing over the tag, and the card's facts matching taxonomy/us_gaap_members.yaml word for word. Proof ==
Reconcile parity on the fixtures is in tests/test_status.py (ProofAgreesWithReconcile, EveryCheckedRowNamesItsEvidence)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb
import yaml

from ledger import filertag, mapcard, mapper, status, store, taxonomy

CIK = 723125
G = "PropertyPlantAndEquipmentGross"
# (dimension, period, period_end, value, accession); the instance below decides what each one is
FACTS = [
    ("Land", "FY2024", "2024-12-31", 100e6, "acc0"), ("Land", "FY2025", "2025-12-31", 120e6, "acc1"),           # one us-gaap member, every year
    ("Shared", "FY2025", "2025-12-31", 50e6, "acc1"),                                                         # two members share the value
    ("Zeroed", "FY2024", "2024-12-31", 0, "acc0"), ("Zeroed", "FY2025", "2025-12-31", 70e6, "acc1"),          # a zero year
    ("Drift", "FY2024", "2024-12-31", 30e6, "acc0"), ("Drift", "FY2025", "2025-12-31", 40e6, "acc1"),         # members differ by year
    ("Servers", "FY2025", "2025-12-31", 80e6, "acc1"),                                                        # a company member
    ("Other", "FY2025", "2025-12-31", 90e6, "acc1"),                                                          # another us-gaap member
    ("Gone", "FY2025", "2025-12-31", 60e6, "acc2"),                                                           # no instance on disk
    ("Half", "FY2024", "2024-12-31", 15e6, "acc0"), ("Half", "FY2025", "2025-12-31", 16e6, "acc1"),           # tagged one year only
    ("Plain", "FY2025", "2025-12-31", 17e6, "acc1"),                                                          # not tagged
]
INSTANCES = {
    "acc0": {(G, "us-gaap:LandMember", "2024-12-31"): 100_000_000, (G, "us-gaap:MachineryAndEquipmentMember", "2024-12-31"): 30_000_000,
             (G, "us-gaap:EquipmentMember", "2024-12-31"): 0, (G, "", "2024-12-31"): 145_000_000},
    "acc1": {(G, "us-gaap:LandMember", "2025-12-31"): 120_000_000, (G, "us-gaap:BuildingMember", "2025-12-31"): 50_000_000,
             (G, "us-gaap:LeaseholdImprovementsMember", "2025-12-31"): 50_000_000, (G, "us-gaap:EquipmentMember", "2025-12-31"): 70_000_000,
             (G, "us-gaap:EquipmentMember", "2024-12-31"): 40_000_000,  # a value on another date never counts
             (G, "mu:ServersMember", "2025-12-31"): 80_000_000, (G, "us-gaap:OtherCapitalizedPropertyPlantAndEquipmentMember", "2025-12-31"): 90_000_000,
             (G, "us-gaap:LandImprovementsMember", "2025-12-31"): 16_000_000, (G, "", "2025-12-31"): 120_000_000},
}
INSTANCES["acc1"][(G, "us-gaap:EquipmentMember", "2025-12-31")] = 40_000_000  # Drift FY2025 reads EquipmentMember...
INSTANCES["acc1"][(G, "us-gaap:ComputerEquipmentMember", "2025-12-31")] = 70_000_000  # ...and Zeroed FY2025 another member
ENTRIES = {"MU": {
    "Land": {"standard_type": "LandMember", "evidence": "the note's own category name", "by": "Claude Fable 5.1", "at": "2026-11-01"},
    "Shared": {"standard_type": "BuildingMember", "evidence": "shared", "by": "Claude Fable 5.1"},
    "Zeroed": {"standard_type": "ComputerEquipmentMember", "evidence": "zeroed", "by": "Claude Fable 5.1"},
    "Drift": {"standard_type": "EquipmentMember", "evidence": "drift", "by": "Claude Fable 5.1"},
    "Servers": {"standard_type": "TechnologyEquipmentMember", "evidence": "servers", "by": "Claude Fable 5.1"},
    "Other": {"standard_type": "OtherMachineryAndEquipmentMember", "evidence": "other equipment", "by": "Claude Fable 5.1"},
    "Gone": {"standard_type": "LandMember", "evidence": "gone", "by": "Claude Fable 5.1"},
    "Half": {"standard_type": "LandImprovementsMember", "evidence": "half", "by": "Claude Fable 5.1"},
    "Plain": {"standard_type": "LandMember", "evidence": "plain", "by": "Claude Fable 5.1"},
}}


def _con():
    con = duckdb.connect()
    con.execute("create table facts (ticker text, field text, dimension text, period text, period_end text, value double, label text, reference text, accession text, extraction_ids text)")
    for d, p, pe, v, a in FACTS:
        con.execute("insert into facts values ('MU','ppe_category',?,?,?,?,'no_reference',null,?,?)", [d, p, pe, v, a, f"{a}|t1|{d}"])
    con.execute("create table documents (accession text, ticker text, cik integer, filed text, url text, tables_path text)")
    for a, f in (("acc0", "2025-02-01"), ("acc1", "2026-02-01"), ("acc2", "2026-02-01")):
        con.execute("insert into documents values (?, 'MU', ?, ?, ?, null)", [a, CIK, f, f"https://www.sec.gov/{a}.htm"])
    con.execute("create table note_extractions (extraction_id text, ticker text, accession text, table_id text, row_label text, cell_text text, field text, dimension text)")
    for d, p, pe, v, a in FACTS:
        con.execute("insert into note_extractions values (?, 'MU', ?, 't1', ?, ?, 'ppe_category', ?)", [f"{a}|t1|{d}", a, d, f"{int(v / 1e6):,}", d])
    return con


class Base(unittest.TestCase):
    def setUp(self):
        from ledger.ingest import edgar
        self.tmp = tempfile.TemporaryDirectory()
        raw = Path(self.tmp.name)
        (raw / f"{CIK:010d}" / "filings").mkdir(parents=True)
        for acc, inst in INSTANCES.items():  # acc2 has no instance on disk
            (raw / f"{CIK:010d}" / "filings" / f"{acc}.facts.json").write_text(json.dumps({"\t".join(k): v for k, v in inst.items()}))
        self.raw = raw
        p = mock.patch.object(edgar, "RAW", raw)
        p.start()
        self.addCleanup(p.stop)
        q = mock.patch("ledger.reference.dimensions.instance_facts", side_effect=AssertionError("no fetch on a page read"))
        q.start()
        self.addCleanup(q.stop)
        self.addCleanup(self.tmp.cleanup)
        self.con = _con()
        self.v = filertag.verdicts(self.con, ["MU"])


class Verdict(Base):
    def test_one_member_every_year_is_verified(self):
        v = self.v[("MU", "Land")]
        self.assertEqual((v["status"], v["member"]), ("tagged", "us-gaap:LandMember"))
        self.assertEqual([(r["accession"], r["period_end"], r["value"]) for r in v["readings"]], [("acc0", "2024-12-31", 100_000_000), ("acc1", "2025-12-31", 120_000_000)])
        self.assertTrue(filertag.verified(ENTRIES["MU"]["Land"], v))
        st = status.of_mapping(ENTRIES["MU"]["Land"], v)
        self.assertEqual((st["state"], st["by"], st["key"]), ("checked", "mapping:filer_tag", "twin"))  # graded as a twin: the filer's own instance

    def test_ambiguous_value_match_needs_a_person(self):
        v = self.v[("MU", "Shared")]
        self.assertEqual((v["status"], v["member"]), ("ambiguous", ["us-gaap:BuildingMember", "us-gaap:LeaseholdImprovementsMember"]))
        self.assertFalse(filertag.verified(ENTRIES["MU"]["Shared"], v))  # BuildingMember is one of the two: still not unambiguous
        self.assertEqual(status.of_mapping(ENTRIES["MU"]["Shared"], v)["by"], "label:to_confirm")

    def test_a_zero_valued_category_needs_a_person(self):
        v = self.v[("MU", "Zeroed")]
        self.assertEqual(v["status"], "zero")  # FY2025 alone would tag ComputerEquipmentMember; the zero year stops it
        self.assertFalse(filertag.verified(ENTRIES["MU"]["Zeroed"], v))
        self.assertEqual(filertag.members_at({(G, "us-gaap:EquipmentMember", "2024-12-31"): 0}, "2024-12-31", 0), [])  # a zero matches nothing

    def test_inconsistent_years_need_a_person(self):
        v = self.v[("MU", "Drift")]
        self.assertEqual((v["status"], v["member"]), ("inconsistent", ["us-gaap:EquipmentMember", "us-gaap:MachineryAndEquipmentMember"]))
        self.assertFalse(filertag.verified(ENTRIES["MU"]["Drift"], v))  # EquipmentMember in FY2025 only

    def test_an_extension_member_needs_a_person(self):
        v = self.v[("MU", "Servers")]
        self.assertEqual((v["status"], v["member"]), ("extension", "mu:ServersMember"))
        self.assertFalse(filertag.verified(ENTRIES["MU"]["Servers"], v))
        self.assertEqual(filertag.compare("TechnologyEquipmentMember", v), "extension")

    def test_no_instance_and_partial_and_untagged_need_a_person(self):
        self.assertEqual(self.v[("MU", "Gone")]["status"], "not_checked")  # not on disk: never "not tagged"
        self.assertEqual((self.v[("MU", "Half")]["status"], self.v[("MU", "Half")]["member"]), ("partial", "us-gaap:LandImprovementsMember"))
        self.assertEqual(self.v[("MU", "Plain")]["status"], "not_tagged")
        for n in ("Gone", "Half", "Plain"):
            self.assertFalse(filertag.verified(ENTRIES["MU"][n], self.v[("MU", n)]), n)

    def test_a_different_member_is_a_conflict_not_a_check(self):
        v = self.v[("MU", "Other")]
        self.assertEqual(filertag.compare("OtherMachineryAndEquipmentMember", v), "differs")
        self.assertFalse(filertag.verified(ENTRIES["MU"]["Other"], v))
        self.assertEqual(mapper.mismatch("OtherMachineryAndEquipmentMember", mapper.filer_members(self.con, "MU", ["Other"])["Other"]), True)

    def test_vacuous_inputs_never_verify(self):
        self.assertEqual(filertag.judge([])["status"], "not_checked")
        self.assertFalse(filertag.verified({"standard_type": "LandMember"}, None))
        self.assertFalse(filertag.verified(None, self.v[("MU", "Land")]))
        self.assertEqual(filertag.verdicts(duckdb.connect(), ["MU"]), {})  # no tables: nothing checked, nothing verified

    def test_only_one_verified_and_the_waiting_list_reads_it(self):
        self.assertEqual(sorted(n for (t, n), v in self.v.items() if filertag.verified(ENTRIES["MU"].get(n), v)), ["Land"])
        with mock.patch.object(taxonomy, "asset_types", return_value=ENTRIES):
            waiting = [e["reported_name"] for e in taxonomy.to_confirm(self.con, ["MU"])]
            everyone = [e["reported_name"] for e in taxonomy.to_confirm(self.con, ["MU"], with_verified=True)]
        self.assertNotIn("Land", waiting)  # off the person's queue and G6
        self.assertEqual(len(waiting), len(ENTRIES["MU"]) - 1)
        self.assertIn("Land", everyone)  # the writer still lets a person confirm it


class Precedence(Base):
    def test_a_persons_confirmation_stands_over_the_tag(self):
        e = {**ENTRIES["MU"]["Other"], "confirmed_by": "Kenny Geiler"}  # the company tags another member; the person decided
        st = status.of_mapping(e, self.v[("MU", "Other")])
        self.assertEqual((st["state"], st["by"]), ("checked", "mapping:OtherMachineryAndEquipmentMember"))

    def test_an_entry_edited_to_another_member_falls_back_to_a_person(self):
        e = {**ENTRIES["MU"]["Land"], "standard_type": "LandAndBuildingMember"}
        self.assertEqual(status.of_mapping(e, self.v[("MU", "Land")])["by"], "label:to_confirm")


class Walk(Base):
    def item(self, name="Land"):
        v = self.v[("MU", name)]
        return {"state": "checked", "by": "mapping:filer_tag", "ref": {"ticker": "MU", "name": name, "filer_tag": filertag.record(v)}}

    def ev(self, types=None):
        return {"asset_types": types or ENTRIES, "filer_tags": filertag.verdicts(self.con, ["MU"])}

    def test_the_tag_on_file_passes(self):
        self.assertIsNone(status.evidence_gap(self.item(), self.ev()))

    def test_a_forged_filer_tag_is_rejected(self):
        it = self.item()
        no_record = {**it, "ref": {"ticker": "MU", "name": "Land"}}
        self.assertIn("no company tag recorded", status.evidence_gap(no_record, self.ev()))
        forged = {**it, "ref": {**it["ref"], "filer_tag": {**it["ref"]["filer_tag"], "readings": [{**it["ref"]["filer_tag"]["readings"][0], "value": 1}]}}}
        self.assertIn("not the ones on file", status.evidence_gap(forged, self.ev()))
        other = {"state": "checked", "by": "mapping:filer_tag", "ref": {"ticker": "MU", "name": "Other", "filer_tag": {"member": "us-gaap:OtherMachineryAndEquipmentMember", "readings": [{"accession": "acc1", "period_end": "2025-12-31", "value": 90_000_000, "members": ["us-gaap:OtherMachineryAndEquipmentMember"]}]}}}
        self.assertIn("not the ones on file", status.evidence_gap(other, self.ev()))  # the company tags OtherCapitalized..., not this
        shared = {"state": "checked", "by": "mapping:filer_tag", "ref": {"ticker": "MU", "name": "Shared", "filer_tag": {"member": "us-gaap:BuildingMember", "readings": [{"accession": "acc1", "period_end": "2025-12-31", "value": 50_000_000, "members": ["us-gaap:BuildingMember"]}]}}}
        self.assertIn("is ambiguous", status.evidence_gap(shared, self.ev()))
        moved = {"MU": {**ENTRIES["MU"], "Land": {**ENTRIES["MU"]["Land"], "standard_type": "LandAndBuildingMember"}}}
        self.assertIn("is not the entry's member", status.evidence_gap(it, self.ev(moved)))
        self.assertIn("no entry", status.evidence_gap(it, self.ev({"MU": {}})))
        self.assertIn("no company tags on file", status.evidence_gap(it, {"asset_types": ENTRIES}))
        self.assertIn("does not explain", status.evidence_gap({**it, "state": "explained"}, self.ev()))

    def test_a_tag_that_changed_on_disk_is_rejected(self):
        it = self.item()
        p = self.raw / f"{CIK:010d}" / "filings" / "acc1.facts.json"
        d = json.loads(p.read_text())
        p.write_text(json.dumps({k.replace("us-gaap:LandMember", "us-gaap:LandAndBuildingMember"): v for k, v in d.items()}))
        self.assertIn("on file the company's tag is inconsistent", status.evidence_gap(it, self.ev()))


class Card(Base):
    def cards(self):
        with mock.patch.object(taxonomy, "asset_types", return_value=ENTRIES), mock.patch.object(mapcard, "asset_types", return_value=ENTRIES):
            return mapcard.decisions(self.con, "MU")

    def test_the_card_facts_match_the_yaml_and_definitions(self):
        doc = yaml.safe_load((store.ROOT / "taxonomy" / "us_gaap_members.yaml").read_text())
        c = self.cards()
        land = c["Land"]
        self.assertEqual(land["proposed"], {"member": "LandMember", "label": doc["members"]["LandMember"]["label"], "definition": doc["members"]["LandMember"]["definition"]})
        self.assertEqual(land["source"], doc["source"]["short"])
        self.assertEqual(land["source"], "FASB US GAAP 2025")
        self.assertEqual(land["state"], {"state": "checked", "by": "mapping:filer_tag", "label": "Verified · matches company's own tag"})
        self.assertEqual((land["tag"]["status"], land["tag"]["text"], land["tag"]["accession"], land["tag"]["period_end"]), ("same", "Same as proposed", "acc1", "2025-12-31"))
        self.assertEqual(land["line"]["latest"], {"period": "FY2025", "value": 120e6})
        self.assertEqual([s["period"] for s in land["line"]["series"]], ["FY2024", "FY2025"])
        self.assertTrue(land["line"]["link"].startswith("https://www.sec.gov/acc1.htm#:~:text=Land"))
        self.assertEqual(land["basis"], "the note's own category name")
        self.assertEqual(land["affects"], {"rows": 2, "value": 120e6, "period": "FY2025", "text": "2 figures · $120M FY2025"})
        for a in [x for card in c.values() for x in card["alternatives"]]:  # every member shown carries the file's own words
            self.assertEqual((a["label"], a["definition"]), (doc["members"][a["member"]]["label"], doc["members"][a["member"]]["definition"]))
        other = c["Other"]
        self.assertEqual(other["tag"]["text"], "Differs: Other Capitalized Property Plant and Equipment (OtherCapitalizedPropertyPlantAndEquipmentMember)")
        self.assertEqual((other["alternatives"][0]["member"], other["alternatives"][0]["why"]), ("OtherCapitalizedPropertyPlantAndEquipmentMember", "Company's own tag"))
        self.assertEqual(other["state"]["label"], "To confirm")
        self.assertEqual(c["Servers"]["tag"]["text"], "Company-specific tag: mu:ServersMember")
        self.assertEqual(c["Shared"]["tag"]["text"], "Ambiguous: us-gaap:BuildingMember, us-gaap:LeaseholdImprovementsMember")
        self.assertEqual(c["Gone"]["tag"]["text"], "Not checked: instance not on file")
        self.assertEqual(c["Plain"]["tag"]["text"], "Not tagged")
        self.assertEqual(c["Zeroed"]["tag"]["text"], "Not compared: zero value")
        self.assertEqual(c["Drift"]["tag"]["text"], "Differs by year: us-gaap:EquipmentMember, us-gaap:MachineryAndEquipmentMember")
        self.assertEqual(c["Half"]["tag"]["text"], "Tagged: Land Improvements (LandImprovementsMember) · not every year")
        self.assertEqual(c["Servers"]["affects"]["text"], "1 figure · $80M FY2025")

    def test_every_allowed_member_has_its_fasb_words(self):
        doc = yaml.safe_load((store.ROOT / "taxonomy" / "us_gaap_members.yaml").read_text())
        allowed = mapper.members()
        self.assertEqual(len(allowed), 18)
        self.assertEqual(sorted(allowed), sorted(doc["members"]))  # every member a person may choose has the standard's label and definition
        card = self.cards()["Land"]
        self.assertEqual([m["member"] for m in card["members"]], allowed)
        self.assertEqual([m["label"] for m in card["members"]], [doc["members"][m]["label"] for m in allowed])

    def test_alternatives_are_the_company_tag_then_shared_words(self):
        doc = mapcard.fasb()
        alts = mapcard.alternatives("Servers and networking equipment", "TechnologyEquipmentMember", None, mapper.members(), doc)
        self.assertEqual([a["member"] for a in alts], ["EquipmentMember", "ComputerEquipmentMember", "MachineryAndEquipmentMember"])
        self.assertTrue(all(a["why"] == "Shares words: equipment" for a in alts))
        self.assertNotIn("TechnologyEquipmentMember", [a["member"] for a in alts])  # never the proposal itself
        self.assertEqual(mapcard.alternatives("Add: assets not yet in service", "ConstructionInProgressMember", None, mapper.members(), doc), [])  # nothing shares a word: none offered


if __name__ == "__main__":
    unittest.main()
