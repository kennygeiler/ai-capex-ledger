"""One definition of open (T1): `status.state` is what Proof and Reconcile both read, so their open counts agree.

The semantics on hand-built rows, and the agreement on the fixtures: the frozen tables of the proven set are loaded
into a fresh database in a temporary repo layout (LEDGER_ROOT, the way the golden harness does it, without running the
code stages), then `proof.board()` and `workbench.items()` are read in a subprocess and compared per company."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ledger import golden, status, store
from ledger.config import PROVEN

SCRIPT = """
import json, duckdb
from ledger import app, proof, store, taxonomy, workbench
from ledger.config import PROVEN
con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
b = proof.board(con)
it = workbench.items(con, app.flow("all"))
print(json.dumps({"proof": {c["ticker"]: c["open"] for c in b["proven"]}, "proof_total": b["open"], "keys": b["keys"],
                  "company_keys": {c["ticker"]: c["keys"] for c in b["proven"]}, "stage_rows": {c["ticker"]: sum(s["items"] for s in c["stages"].values()) for c in b["proven"]},
                  "keyed_items": {c["ticker"]: sum(1 for s in c["stages"].values() for i in s["all"] if i["key"]) for c in b["proven"]},
                  "reconcile": {t: sum(1 for r in it["rows"] if r["open"] and r["ticker"] == t) for t in PROVEN},
                  "states": sorted({r["state"] for r in it["rows"]}),
                  "by": sorted({r["by"].split(":")[0] for r in it["rows"] if r["ticker"] in PROVEN}),
                  "mapping_open": {c["ticker"]: len(c["stages"]["mapping"]["open"]) for c in b["proven"]},
                  "mapping_to_confirm": {c["ticker"]: sum(i["by"] == "label:to_confirm" for i in c["stages"]["mapping"]["open"]) for c in b["proven"]},
                  "mapping_checked_unconfirmed": {c["ticker"]: sum(i["state"] == "checked" for i in c["stages"]["mapping"]["all"]) - sum(1 for e in (taxonomy.asset_types().get(c["ticker"]) or {}).values() if (e or {}).get("confirmed_by")) for c in b["proven"]},
                  "waiting": {t: len(taxonomy.to_confirm(con, [t])) + len(taxonomy.unmapped(con, [t])) for t in PROVEN},
                  "open_names": {c["ticker"]: sorted(i["name"] for i in c["stages"]["mapping"]["open"]) for c in b["proven"]},
                  "waiting_names": {t: sorted([u["reported_name"] for u in taxonomy.to_confirm(con, [t])] + [u["reported_name"] for u in taxonomy.unmapped(con, [t])]) for t in PROVEN},
                  "checked_names": {c["ticker"]: sorted(i["name"] for i in c["stages"]["mapping"]["all"] if i["state"] == "checked") for c in b["proven"]},
                  "confirmed_names": {c["ticker"]: sorted(i["name"] for i in c["stages"]["mapping"]["all"] if (e := (taxonomy.asset_types().get(c["ticker"]) or {}).get(i["name"])) and e.get("standard_type") and e.get("confirmed_by")) for c in b["proven"]},
                  "to_confirm_names": {t: sorted(u["reported_name"] for u in taxonomy.to_confirm(con, [t])) for t in PROVEN},
                  "tax_to_confirm": {t: sorted({r["reported_name"] for r in taxonomy.rows(con, [t]) if r["check"] == "to_confirm" and not r["mapped"]}) for t in PROVEN},
                  "tax_mapped_unconfirmed": sum(1 for t in PROVEN for r in taxonomy.rows(con, [t]) if r["measure"] == "derived" and r["mapped"] and not ((taxonomy.asset_types().get(t) or {}).get(r["reported_name"]) or {}).get("confirmed_by")),
                  "to_confirm": {t: len(taxonomy.to_confirm(con, [t])) for t in PROVEN}}))
"""


class Definition(unittest.TestCase):
    def test_checked_explained_open_blocked(self):
        self.assertEqual(status.state({"check": "xbrl"})["state"], "checked")
        self.assertEqual(status.state({"check": "quote"})["by"], "quote")
        self.assertEqual(status.state({"check": "mapping", "mapping_to": "us-gaap:EquipmentMember"})["by"], "mapping:us-gaap:EquipmentMember")
        self.assertEqual(status.state({"definition": "cost_lines"}), {"state": "explained", "reason": "a definition on file: cost_lines", "by": "definition:cost_lines", "keys": [], "key": None})
        self.assertEqual(status.state({"rule": "restated_between_filings"})["state"], "explained")  # a guard counts as info
        self.assertEqual(status.state({"rule": "definition_note", "severity": "info"})["by"], "rule:definition_note")
        self.assertEqual(status.state({"label": "not_reported"})["by"], "label:not_reported")
        self.assertEqual(status.state({"rule": "sign", "severity": "block"})["state"], "blocked")
        self.assertEqual(status.state({"rule": "jump", "severity": "warn"})["state"], "open")  # a warn rule alone explains nothing
        self.assertEqual(status.state({}), {"state": "open", "reason": "neither checked nor explained", "by": "", "keys": [], "key": None})

    def test_a_person_resolves_what_nothing_on_file_covers(self):
        acc = {"id": "r1", "state": "accept", "reason": "right as is"}
        self.assertEqual(status.state({"resolution": acc}), {"state": "explained", "reason": "right as is", "by": "resolution:r1", "keys": [], "key": None})
        self.assertEqual(status.state({"resolution": {**acc, "state": "fix"}})["state"], "open")
        self.assertEqual(status.state({"resolution": {**acc, "state": "blocks"}})["state"], "blocked")
        # precedence: blocks beats a check; a check beats a fix; a fix beats a definition
        self.assertEqual(status.state({"check": "xbrl", "resolution": {**acc, "state": "blocks"}})["state"], "blocked")
        self.assertEqual(status.state({"check": "xbrl", "resolution": {**acc, "state": "fix"}})["state"], "checked")
        self.assertEqual(status.state({"definition": "revenue", "resolution": {**acc, "state": "fix"}})["state"], "open")
        self.assertTrue(status.is_open(status.state({"resolution": {**acc, "state": "blocks"}})))

    def test_a_missing_cell_with_an_xbrl_value_is_open_by_its_label(self):
        """T65: not_extracted explains nothing; the label names the cause so Proof and Reconcile show it."""
        st = status.of_value({"field": "revenue", "period": "FY2025", "label": "not_extracted"})
        self.assertEqual({k: st[k] for k in ("state", "reason", "by")}, {"state": "open", "reason": "the filing tags a value the reader did not extract", "by": "label:not_extracted"})
        self.assertEqual((st["keys"], st["key"]), ([], None))  # no answer key vouches for a missing cell (T56)
        self.assertTrue(status.is_open(st))
        # T81: not_reported explains only when XBRL was looked up and holds nothing; over a value, or unasked, it is open
        nr = {"field": "revenue", "period": "FY2025", "label": "not_reported"}
        self.assertEqual(status.of_value(nr, None, {"reference": None, "looked_up": True})["state"], "explained")
        over = status.of_value(nr, None, {"reference": 123, "looked_up": True})
        self.assertEqual((over["state"], over["by"]), ("open", "label:not_reported"))
        self.assertIn("XBRL holds 123", over["reason"])
        self.assertEqual(status.of_value(nr)["state"], "open")  # no lookup marker: fail closed
        self.assertEqual(status.of_value(nr, None, {"reference": None, "looked_up": False})["state"], "open")
        self.assertEqual(status.of_value(nr, {"id": "r1", "state": "explain", "reason": "the tag is a different line"}, {"reference": 123, "looked_up": True})["by"], "resolution:r1")
        self.assertEqual(status.of_exception({"rule_id": "coverage", "severity": "warn"}, None, [over])["state"], "open")  # one verdict: the coverage finding on it is open too
        acc = {"id": "r9", "state": "accept", "reason": "the line is not there"}
        self.assertEqual(status.of_value({"field": "revenue", "period": "FY2025", "label": "not_extracted"}, acc)["by"], "resolution:r9")  # a person may still resolve it
        jump = {"rule_id": "coverage", "severity": "warn", "message": "no revenue value for FY2025"}
        self.assertEqual(status.of_exception(jump, None, [st])["state"], "open")  # a coverage finding on it is open with it

    def test_a_warn_finding_takes_the_state_of_its_rows(self):
        jump = {"rule_id": "jump", "severity": "warn", "message": "capex moves 4×"}
        agree = status.of_value({"field": "capex", "period": "FY2025", "label": "agree"})
        gap = status.of_value({"field": "opex", "period": "FY2026", "label": "definition_gap"})
        unres = status.of_value({"field": "capex", "period": "FY2024", "label": "unresolved"})
        self.assertEqual(status.of_exception(jump, None, [agree])["state"], "checked")
        self.assertEqual(status.of_exception(jump, None, [gap])["by"], "definition:cost_lines")
        self.assertEqual(status.of_exception(jump, None, [agree, unres])["state"], "open")
        self.assertEqual(status.of_exception(jump, None, [])["state"], "open")
        self.assertEqual(status.of_exception({**jump, "severity": "block"}, None, [agree])["state"], "blocked")
        self.assertEqual(status.of_exception({**jump, "severity": "info"}, None, [])["state"], "explained")
        self.assertEqual(status.of_exception(jump, {"id": "r2", "state": "accept", "reason": "a real move"}, [unres])["by"], "resolution:r2")

    def test_the_four_answer_keys_check_a_row_the_same_way(self):
        """T40: esef:<tag>, source:<doc>, rule:<id>_tie and actual:<period> are checks like xbrl, through the one function."""
        xbrl = status.state({"check": "xbrl"})
        esef = status.state({"check": "esef:ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"})
        self.assertEqual((esef["state"], esef["by"]), ("checked", "esef:ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"))
        self.assertEqual({k: v for k, v in esef.items() if k != "reason"}, {**{k: v for k, v in xbrl.items() if k != "reason"}, "by": esef["by"]})  # same inputs, same state: a twin is a twin
        src = status.state({"check": "source:0001652044-25-000014"})
        self.assertEqual((src["state"], src["by"]), ("checked", "source:0001652044-25-000014"))
        tie = status.state({"check": "rule:quarters_tie"})
        self.assertEqual((tie["state"], tie["by"], tie["reason"]), ("checked", "rule:quarters_tie", "the tie holds"))
        actual = status.state({"check": "actual:FY2025"})
        self.assertEqual((actual["state"], actual["by"]), ("checked", "actual:FY2025"))
        # a tie that fails is the rule's finding, not a check: open (warn) or blocked (block), never checked
        self.assertEqual(status.state({"rule": "quarters_tie", "severity": "warn"}), {"state": "open", "reason": "rule quarters_tie fired and nothing on file says why", "by": "rule:quarters_tie", "keys": [], "key": None})  # a failed tie carries no key
        self.assertEqual(status.state({"rule": "statement_tie", "severity": "block"})["state"], "blocked")
        self.assertEqual(status.state({"check": "rule:jump"})["state"], "open")  # a rule that is not a tie vouches for nothing
        self.assertEqual(status.state({"check": "definition:revenue"})["state"], "open")  # an explanation is not a check
        # precedence holds for the new kinds as for xbrl
        blocks = {"id": "r9", "state": "blocks", "reason": "no"}
        self.assertEqual(status.state({"check": "esef:x", "resolution": blocks})["state"], "blocked")
        self.assertEqual(status.state({"check": "esef:x", "resolution": {**blocks, "state": "fix"}})["state"], "checked")
        # a row through the same function in Proof's and Reconcile's shape agrees by construction: one call, one answer
        self.assertEqual(status.of_exception({"rule_id": "jump", "severity": "warn"}, None, [esef])["state"], "checked")

    def test_answer_key_for_every_method_kind(self):
        """`answer_key` names one of four kinds, or None, for every kind in METHOD_KINDS; every ANSWER_KEYS kind is a METHOD_KIND."""
        expect = {"xbrl": "twin", "esef": "twin", "source": "second_source", "actual": "later_truth", "reading": "second_reading", "rule": None,  # rule alone is not a tie
                  "quote": None, "gathered": None, "located": None, "gate": None, "none": None, "mapping": None, "definition": None, "resolution": None, "label": None}
        self.assertEqual(set(expect), set(status.METHOD_KINDS))
        for kind, key in expect.items():
            self.assertEqual(status.answer_key(kind), key, kind)
            self.assertEqual(status.answer_key(f"{kind}:some-id"), key, kind)
        self.assertEqual(status.answer_key("rule:quarters_tie"), "tie")
        self.assertEqual(status.answer_key("rule:statement_tie"), "tie")
        self.assertIsNone(status.answer_key("rule:restated_between_filings"))
        self.assertIsNone(status.answer_key(""))
        self.assertEqual(set(status.ANSWER_KEYS), {"twin", "second_source", "tie", "later_truth", "second_reading"})
        for kinds in status.ANSWER_KEYS.values():
            self.assertTrue(set(kinds) <= set(status.METHOD_KINDS), kinds)

    def test_key_grades(self):
        """T56: the four keys ranked by independence, strongest first; `strongest` picks over several keys per row."""
        self.assertEqual(status.KEY_GRADE, ("twin", "second_source", "tie", "later_truth", "second_reading"))  # T92: a second reading is the same filer's next 10-K, the weakest
        self.assertEqual(set(status.KEY_GRADE), set(status.ANSWER_KEYS))
        self.assertEqual(set(status.KEY_WHY), set(status.KEY_GRADE))
        self.assertEqual(set(status.KEY_LABEL), set(status.KEY_GRADE))
        self.assertTrue(status.grade("twin") < status.grade("second_source") < status.grade("tie") < status.grade("later_truth") < status.grade("second_reading") < status.grade(None))
        self.assertEqual(status.strongest(["second_reading", "tie"]), "tie")  # a tie outranks a second reading
        self.assertEqual(status.strongest(["later_truth", "tie", "second_source"]), "second_source")
        self.assertEqual(status.strongest(["tie", "twin", "tie"]), "twin")
        self.assertEqual(status.strongest(["later_truth"]), "later_truth")
        self.assertIsNone(status.strongest([]))
        self.assertIsNone(status.strongest([None, "quote"]))

    def test_state_carries_the_strongest_key(self):
        """T56: `state()` carries `keys` (every answer key that vouches for the row) and `key` (the strongest); a row today
        carries one `by`, so keys holds at most one; a quote, a mapping, an explanation and an open row carry none."""
        for by, key in (("xbrl", "twin"), ("esef:ifrs-full:Revenue", "twin"), ("source:0001652044-25-000014", "second_source"), ("rule:quarters_tie", "tie"), ("actual:FY2025", "later_truth"),
                        ("reading:0001144879-25-000021", "second_reading")):
            st = status.state({"check": by})
            self.assertEqual((st["state"], st["keys"], st["key"]), ("checked", [key], key), by)
        for row in ({"check": "quote"}, {"check": "located"}, {"check": "mapping", "mapping_to": "us-gaap:EquipmentMember"}, {"definition": "revenue"}, {"label": "no_reference"},
                    {"rule": "jump", "severity": "warn"}, {"rule": "statement_tie", "severity": "block"}, {"resolution": {"id": "r1", "state": "accept", "reason": "ok"}}, {}):
            st = status.state(row)
            self.assertEqual((st["keys"], st["key"]), ([], None), row)
        # the derived rows carry it too: a fact XBRL confirms, a warn finding on checked rows, a resolved finding
        self.assertEqual(status.of_fact({"label": "agree"})["key"], "twin")
        self.assertEqual(status.of_value({"field": "capex", "period": "FY2025", "label": "agree"})["key"], "twin")
        agree = status.of_value({"field": "capex", "period": "FY2025", "label": "agree"})
        self.assertEqual(status.of_exception({"rule_id": "jump", "severity": "warn"}, None, [agree])["key"], "twin")
        self.assertIsNone(status.of_exception({"rule_id": "jump", "severity": "warn"}, {"id": "r2", "state": "accept", "reason": "a real move"}, [agree])["key"])
        self.assertIn("keys", status.of_exception({"rule_id": "jump", "severity": "block"}, None, []))

    def test_fact_rows(self):
        self.assertEqual(status.of_fact({"label": "agree"})["by"], "xbrl")
        self.assertEqual(status.of_fact({"label": "no_reference"})["state"], "explained")
        self.assertEqual(status.of_fact({"label": "unresolved"})["state"], "open")
        r = status.of_fact({"label": "unresolved"}, None, "cell from a, tag from b")
        self.assertEqual((r["state"], r["by"], r["reason"]), ("explained", "rule:restated_between_filings", "cell from a, tag from b"))

    def test_the_ladder_of_an_untagged_fact(self):
        """T92: an untagged fact (no_reference) whose readings differ is open, whatever else holds, and only a person's
        resolution explains it; else a tie checks it, else a second reading, else the label explains it, citation only."""
        nr = {"label": "no_reference"}
        d = status.of_fact(nr, None, differ="readings differ across filings: $9.6M vs $1.8M", tie="ppe_categories_tie", reading="a")
        self.assertEqual((d["state"], d["by"], d["key"]), ("open", "rule:fact_readings_differ", None))
        self.assertIn("$9.6M vs $1.8M", d["reason"])
        self.assertEqual(status.of_fact(nr, {"id": "r1", "state": "explain", "reason": "reclassified"}, differ="x")["by"], "resolution:r1")
        self.assertEqual(status.of_fact(nr, {"id": "r1", "state": "fix", "reason": "re-read"}, differ="x")["state"], "open")
        t = status.of_fact(nr, None, tie="ppe_categories_tie", reading="a")
        self.assertEqual((t["state"], t["by"], t["key"]), ("checked", "rule:ppe_categories_tie", "tie"))
        r = status.of_fact(nr, None, reading="0001144879-25-000021")
        self.assertEqual((r["state"], r["by"], r["key"]), ("checked", "reading:0001144879-25-000021", "second_reading"))
        self.assertEqual(status.of_fact(nr)["by"], "label:no_reference")
        # a tagged fact keeps the twin: the ladder applies to no_reference only
        self.assertEqual(status.of_fact({"label": "agree"}, None, tie="ppe_categories_tie")["by"], "xbrl")
        self.assertEqual(status.of_fact({"label": "unresolved"}, None, None, differ="x", tie="ppe_categories_tie")["state"], "open")
        self.assertEqual(status.of_fact({"label": "unresolved"}, None, None, differ="x", tie="ppe_categories_tie")["by"], "")


def fixture_root() -> Path:
    """A repo layout in a temporary folder holding the proven set's frozen tables (fixtures/expected) in a fresh database,
    the way the golden harness lays it out, without running the code stages. The caller removes it."""
    seed = json.loads((golden.FIXTURES / "seed.json").read_text())
    root = Path(tempfile.mkdtemp(prefix="ledger-status-"))
    for name in golden.SHARED:  # taxonomy/ (the asset-type mappings the mapping stage reads) is in SHARED since T31
        if (store.ROOT / name).exists():
            os.symlink(store.ROOT / name, root / name)
    shutil.copytree(golden.FIXTURES / "data", root / "data")
    (root / "reports").mkdir()
    (root / "reports" / "stage3-faults.json").write_text("[]")
    con = store.init(root / "data" / "ledger.duckdb")
    store.write(con, "documents", seed["documents"])
    store.write(con, "texts", seed["texts"])
    if seed.get("reference_values"):
        store.write(con, "reference_values", seed["reference_values"])
    for name, skip in golden.TABLES.items():  # the frozen tables, with the per-run columns the freeze left out filled in
        f = golden.EXPECTED / f"{name}.csv"
        if f.exists() and f.read_text().strip():
            cols = {r[0]: (r[1], r[2] == "YES") for r in con.execute("select column_name, data_type, is_nullable from information_schema.columns where table_name = ?", [name]).fetchall()}
            head = con.execute("select * from read_csv(?, header = true, all_varchar = true) limit 0", [str(f)]).description
            sel = [(f"nullif({c}, '')" if nullable or typ != "VARCHAR" else f"coalesce({c}, '')") + f"::{typ} as {c}" for c in [h[0] for h in head] for typ, nullable in [cols[c]]]  # an empty cell is NULL where the schema allows it, '' where it does not
            sel += [f"'fixture' as {c}" if c == "run_id" else f"md5(concat_ws('|', rule_id, ticker, field, period, subject)) as {c}" for c in skip if c in cols]
            con.execute(f'insert into "{name}" by name select {", ".join(sel)} from read_csv(?, header = true, all_varchar = true)', [str(f)])
    con.close()
    return root


class ALabelNeverCountsAsACheck(unittest.TestCase):
    """T80: a checked or explained row points at the record that makes it so; `evidence_gap` names what is missing."""

    QUOTES = {"s1": "We expect capital expenditures of about $80 billion.", "s2": "capital expenditures of about $90 billion"}
    EV = {"definitions": {"APLD": {"cost_lines": {"by": "Kenny Geiler"}}}, "rules": {"definition_note": "info", "jump": "warn", "part_year": "info", "quarters_tie": "block"},
          "resolutions": {"r1": {"id": "r1", "by": "Kenny Geiler"}, "r2": {"id": "r2", "by": "Replication run (Claude), for Kenny to confirm"}, "r3": {"id": "r3", "by": "Gemini"}},
          "person_ids": {"r1"},
          "asset_types": {"MSFT": {"Servers": {"standard_type": "us-gaap:ComputerEquipmentMember", "by": "a model"},
                                   "Land": {"standard_type": "us-gaap:LandMember", "by": "a model", "confirmed_by": "Kenny Geiler"},
                                   "Racks": {"standard_type": "us-gaap:EquipmentMember", "by": "a model", "confirmed_by": "Claude"}}},
          "text": lambda tid: {"T1": status.norm("We expect capital expenditures of about $80 billion.")}.get(tid),
          "quote": lambda item: [ALabelNeverCountsAsACheck.QUOTES.get((item.get("ref") or {}).get("statement_id"))]}

    def gap(self, st, ref=None):
        return status.evidence_gap({**st, "ref": ref or {}}, self.EV)

    def test_backed_rows_pass(self):
        self.assertIsNone(self.gap(status.of_value({"label": "agree"}), {"reference": 5, "looked_up": True}))
        self.assertIsNone(self.gap(status.state({"check": "rule:quarters_tie"}), {"tie": [1, 2, 3]}))  # a tie that holds carries its own numbers
        self.assertIsNone(self.gap(status.state({"check": "esef:ifrs-full:Revenue"}), {"esef": 5}))
        self.assertIsNone(self.gap(status.state({"check": "quote"}), {"statement_id": "s1", "text_id": "T1"}))
        self.assertIsNone(self.gap(status.state({"check": "located"}), {"income_tables": "t1", "cash_flow_tables": "t2"}))
        self.assertIsNone(self.gap(status.state({"check": "gate"}), {"stage": "release", "blocks": 0}))
        self.assertIsNone(self.gap(status.of_mapping(self.EV["asset_types"]["MSFT"]["Land"]), {"ticker": "MSFT", "name": "Land"}))
        self.assertIsNone(self.gap(status.of_value({"field": "opex", "label": "definition_gap"}), {"ticker": "APLD"}))
        self.assertIsNone(self.gap(status.state({"rule": "part_year"})))
        self.assertIsNone(self.gap(status.state({"rule": "definition_note", "severity": "info"})))
        self.assertIsNone(self.gap(status.state({"resolution": {"id": "r1", "state": "accept", "reason": "right"}})))
        looked = {"reference": None, "looked_up": True}
        self.assertIsNone(self.gap(status.of_value({"label": "not_reported"}, None, looked), looked))  # looked up, and nothing there
        self.assertIsNone(self.gap(status.of_fact({"label": "no_reference"}), {"reference": None, "looked_up": True}))
        self.assertIsNone(self.gap(status.state({"rule": "jump", "severity": "warn"})))  # open claims nothing
        self.assertIsNone(self.gap(status.state({"rule": "sign", "severity": "block"})))

    def test_planted_bare_labels_fail(self):
        # (a) not_reported while XBRL holds a value; a blank whose XBRL lookup never ran (no marker, or marker false)
        # of_value opens these itself since T81; the walk still fails a hand-made explained state over them
        bare = status.state({"label": "not_reported"})
        self.assertIn("XBRL holds 123", self.gap(bare, {"reference": 123, "looked_up": True}))
        self.assertIn("not looked up", self.gap(bare, {"reference": None}))
        self.assertIn("not looked up", self.gap(bare, {"reference": None, "looked_up": False}))
        self.assertIn("not looked up", self.gap(status.of_fact({"label": "no_reference"}), {"reference": None}))  # a fact whose instance is absent
        self.assertIn("XBRL holds", self.gap(status.of_fact({"label": "no_reference"}), {"reference": 7, "looked_up": True}))
        self.assertIn("no XBRL value", self.gap(status.of_value({"label": "agree"}), {"reference": 5}))  # a reference with no lookup marker
        # (b) a mapping with no confirmed_by forced to checked, one confirmed by a model, one whose member is not the entry's
        forced = status.state({"check": "mapping", "mapping_to": "us-gaap:ComputerEquipmentMember"})
        self.assertIn("no confirmed_by", self.gap(forced, {"ticker": "MSFT", "name": "Servers"}))
        self.assertIn("not a person", self.gap({**forced, "by": "mapping:us-gaap:EquipmentMember"}, {"ticker": "MSFT", "name": "Racks"}))
        self.assertFalse(status.confirmed(self.EV["asset_types"]["MSFT"]["Racks"]))  # confirmed_by: Claude does not confirm
        self.assertFalse(status.confirmed({"standard_type": "x", "confirmed_by": "Somebody Else"}))  # nor a name off config.PEOPLE
        self.assertTrue(status.confirmed(self.EV["asset_types"]["MSFT"]["Land"]))
        self.assertIn("maps to us-gaap:LandMember", self.gap({**forced, "by": "mapping:us-gaap:BuildingsMember"}, {"ticker": "MSFT", "name": "Land"}))
        self.assertIn("no entry", self.gap(forced, {"ticker": "MSFT", "name": "Cranes"}))
        # (c) a resolution id that does not exist, one a run wrote, one by a name off config.PEOPLE
        self.assertIn("no such resolution", self.gap(status.state({"resolution": {"id": "nope", "state": "accept", "reason": "ok"}})))
        self.assertIn("not a person", self.gap(status.state({"resolution": {"id": "r2", "state": "explain", "reason": "ok"}})))
        self.assertIn("'Gemini', not a person", self.gap(status.state({"resolution": {"id": "r3", "state": "accept", "reason": "ok"}})))
        # answer keys: only checked, and each on its own value, never the XBRL one
        self.assertIn("does not explain", self.gap({"state": "explained", "by": "rule:quarters_tie"}, {"tie": [1], "reference": 5, "looked_up": True}))
        self.assertIn("no tie value", self.gap(status.state({"check": "rule:quarters_tie"}), {"reference": 5, "looked_up": True}))
        for by, field in (("esef:ifrs-full:Revenue", "esef"), ("source:0001652044-25-000014", "source"), ("actual:FY2025", "actual")):
            self.assertIn(f"no {field} value", self.gap(status.state({"check": by}), {"reference": 5, "looked_up": True}), by)
        # the gate belongs to the release stage only
        self.assertIn("only the release stage", self.gap(status.state({"check": "gate"}), {"stage": "values", "blocks": 0}))
        self.assertIn("only the release stage", self.gap(status.state({"check": "gate"}), {"blocks": 0}))
        self.assertIn("block items", self.gap(status.state({"check": "gate"}), {"stage": "release", "blocks": 2}))
        # and the rest: a definition the ticker lacks, a rule not on file, a warn rule forced to explain, a bare label,
        # a quote not in its text, a quote not on file, a text not on file, no tables, no `by` at all
        self.assertIn("no such definition", self.gap(status.of_value({"field": "opex", "label": "definition_gap"}), {"ticker": "MSFT"}))
        self.assertIn("no such rule", self.gap(status.state({"rule": "made_up", "severity": "info"})))
        self.assertIn("explains nothing", self.gap({"state": "explained", "by": "rule:jump"}))
        self.assertIn("bare label", self.gap({"state": "explained", "by": "label:to_confirm"}))
        self.assertIn("bare label", self.gap({"state": "explained", "by": "label:not_extracted"}))
        self.assertIn("not found", self.gap(status.state({"check": "quote"}), {"statement_id": "s2", "text_id": "T1"}))
        self.assertIn("no quote on file", self.gap(status.state({"check": "quote"}), {"statement_id": "s9", "text_id": "T1"}))
        self.assertIn("no text", self.gap(status.state({"check": "quote"}), {"statement_id": "s1", "text_id": "T9"}))
        self.assertIn("no income", self.gap(status.state({"check": "located"}), {"income_tables": "t1", "cash_flow_tables": ""}))
        self.assertEqual(self.gap({"state": "checked", "by": ""}), "names no evidence")

    def test_a_tie_and_a_second_reading_carry_their_numbers(self):
        """T92: rule:<id>_tie checks a part only when its group ties (on the row, and on file when the walk has the
        groups); reading:<accession> needs two or more filings that agree (and the same readings on file)."""
        tie = {"rule": "ppe_categories_tie", "key": "APLD|ppe_category|FY2024|a2", "total": 100, "sum": 100, "tolerance": 2, "dimensions": ["Land", "Other"]}
        part = {"ticker": "APLD", "field": "ppe_category", "dimension": "Land", "period": "FY2024", "tie": tie}
        checked = status.of_fact({"label": "no_reference"}, None, tie="ppe_categories_tie")
        self.assertIsNone(self.gap(checked, part))
        self.assertIn("does not hold", self.gap(checked, {**part, "tie": {**tie, "sum": 90}}))
        self.assertIn("not a part", self.gap(checked, {**part, "dimension": "Building"}))
        self.assertIn("the tie on the row is", self.gap(checked, {**part, "tie": {**tie, "rule": "segment_capex_tie"}}))
        on_file = {**self.EV, "ties": {tie["key"]: {**tie, "concept": "PropertyPlantAndEquipmentGross", "holds": True}}}
        self.assertIsNone(status.evidence_gap({**checked, "ref": part}, on_file))
        untied = {**self.EV, "ties": {tie["key"]: {**tie, "sum": 90, "concept": "PropertyPlantAndEquipmentGross", "holds": False}}}
        self.assertIn("does not tie", status.evidence_gap({**checked, "ref": part}, untied))
        self.assertIn("no group", status.evidence_gap({**checked, "ref": part}, {**self.EV, "ties": {}}))
        two = [{"accession": "a1", "filed": "2024-08-30", "value": 1_760_000, "scale": 1000}, {"accession": "a2", "filed": "2025-07-30", "value": 1_760_000, "scale": 1000}]
        second = status.of_fact({"label": "no_reference"}, None, reading="a1")
        row = {"ticker": "APLD", "field": "ppe_category", "dimension": "Other", "period": "FY2024", "readings": two}
        self.assertIsNone(self.gap(second, row))
        self.assertIn("fewer than two", self.gap(second, {**row, "readings": two[:1]}))
        self.assertIn("fewer than two", self.gap(second, {**row, "readings": [two[0], {**two[0]}]}))  # one filing read twice is one reading
        self.assertIn("readings differ", self.gap(second, {**row, "readings": [two[0], {**two[1], "value": 9_552_000}]}))
        self.assertIn("no readings value", self.gap(second, {k: v for k, v in row.items() if k != "readings"}))
        self.assertIn("not the ones on file", status.evidence_gap({**second, "ref": row}, {**self.EV, "readings": {}}))
        self.assertIsNone(status.evidence_gap({**second, "ref": row}, {**self.EV, "readings": {("APLD", "ppe_category", "Other", "FY2024"): two}}))
        self.assertIsNone(self.gap(second, {**row, "readings": [two[0], {**two[1], "value": 1_760_400}]}))  # within half a rounding unit (thousands)

    def test_a_person_is_on_the_list(self):
        """T80: fail closed. A resolution or a confirmed_by counts as a person's only by a name on config.PEOPLE."""
        from ledger import proof
        self.assertTrue(status.is_person("Kenny Geiler"))
        for who in ("Gemini", "Claude", "Somebody Else", "", None, "Kenny Geiler (agent)"):
            self.assertFalse(status.is_person(who), who)
        self.assertTrue(proof.person_wrote({"by": "Kenny Geiler", "reason": "right"}))
        self.assertFalse(proof.person_wrote({"by": "Gemini", "reason": "right"}))
        self.assertFalse(proof.person_wrote({"by": "Kenny Geiler", "reason": "to confirm"}))
        self.assertTrue(proof.person_wrote({"by": "anyone", "author_kind": "person"}))  # T69's field, once it lands
        self.assertFalse(proof.person_wrote({"by": "Kenny Geiler", "author_kind": "run"}))

    def test_rule_ids_are_unique_and_guards_fill_only_gaps(self):
        from ledger import proof
        with self.assertRaises(ValueError):
            proof.rule_severities([{"id": "jump", "severity": "warn"}, {"id": "jump", "severity": "info"}])
        sev = proof.rule_severities([{"id": "part_year", "severity": "block"}])
        self.assertEqual(sev["part_year"], "block")  # a guard never overrides a rule of the same id
        self.assertEqual(sev["program_words"], "info")


WALK = r'''
import json, sys, duckdb
from ledger import proof, resolutions, status, store
plant = sys.argv[1]
rw = lambda: duckdb.connect(str(store.DEFAULT_DB))
if plant == "not_reported":  # (a) blank a value XBRL holds and label it not_reported
    con = rw()
    t, f, p = con.execute("select v.ticker, v.field, v.period from \"values\" v join reference_values r using (ticker, field, period) where v.label = 'agree' and v.ticker = 'MSFT' order by 2, 3 limit 1").fetchone()
    con.execute("update \"values\" set label = 'not_reported', value = null where ticker = ? and field = ? and period = ?", [t, f, p])
    con.close()
if plant == "no_reference_fact":  # (a) on facts: a fact XBRL holds, relabelled no_reference
    con = rw()
    f, d, p = con.execute("select field, coalesce(dimension, ''), period from facts where ticker = 'MSFT' and label = 'agree' order by 1, 2, 3 limit 1").fetchone()
    con.execute("update facts set label = 'no_reference' where ticker = 'MSFT' and field = ? and coalesce(dimension, '') = ? and period = ?", [f, d, p])
    con.close()
if plant == "no_lookup_values":  # MSFT's reference_values gone: the lookup never ran, so no blank or agree is backed
    con = rw()
    con.execute("update \"values\" set label = 'not_reported' where ticker = 'MSFT' and field = (select min(field) from \"values\" where ticker = 'MSFT')")
    con.execute("delete from reference_values where ticker = 'MSFT'")
    con.close()
if plant == "no_instance":  # a fact's filing instance absent: its no_reference is no answer
    con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
    acc, cik = con.execute("select f.accession, d.cik from facts f join documents d using (accession) where f.ticker = 'MSFT' and f.label = 'no_reference' order by 1 limit 1").fetchone()
    con.close()
    from ledger.ingest.edgar import RAW
    for x in (RAW / f"{int(cik):010d}" / "filings").glob(acc + ".*"):
        x.unlink()
    print(json.dumps({"accession": acc}))
if plant == "mapping":  # (b) every entry forced to checked, confirmed_by or not
    status.of_mapping = lambda e: status.state({"check": "mapping", "mapping_to": e["standard_type"]}) if (e or {}).get("standard_type") else status.state({})
if plant == "claude":  # (b) a hand edit confirmed_by: Claude on every entry, and the stage forced to checked as well
    real_types = proof.asset_types
    types = {t: {n: {**e, "confirmed_by": "Claude"} for n, e in es.items()} for t, es in real_types().items()}
    proof.asset_types = lambda *a, **k: types
    print(json.dumps({"checked_by_claude": sum(status.of_mapping(e)["state"] == "checked" for es in types.values() for e in es.values())}))
    status.of_mapping = lambda e: status.state({"check": "mapping", "mapping_to": e["standard_type"]}) if (e or {}).get("standard_type") else status.state({})
if plant in ("resolution", "gemini"):  # (c) a resolution not on file; one on file by a name off config.PEOPLE, on a fact only its citation backs (T92: a tie or a second reading would check it first)
    con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
    r0 = next(i["ref"] for t in proof.PROVEN for i in proof.company(con, t)["stages"]["facts"]["all"] if i["by"] == "label:no_reference")
    con.close()
    tk, f, d, p = r0["ticker"], r0["field"], r0["dimension"], r0["period"]
    print(json.dumps({"planted_on": tk}))
    rid = "not-on-file" if plant == "resolution" else "planted-gemini"
    real, real_load = resolutions.by_row, resolutions.load
    resolutions.by_row = lambda *a, **k: {**real(*a, **k), ("facts", tk, f, d, p, ""): {"id": rid, "state": "accept", "status": "accepted", "by": "Gemini", "at": "", "reason": "planted"}}
    if plant == "gemini":
        resolutions.load = lambda *a, **k: real_load(*a, **k) + [{"id": rid, "key": "x", "hash": "x", "state": "accept", "reason": "planted", "by": "Gemini", "at": ""}]
if plant == "gate":  # a gate on the values stage
    status.of_value = lambda v, r=None, ref=None: status.state({"check": "gate"})
if plant in ("quote_variant", "quote_changed"):  # the same quote with curly quotes, a no-break space and upper case; or a changed one
    con = rw()
    sid, q = con.execute("select statement_id, quote from ai_statements where ticker = 'MSFT' and quote like '% %' order by 1 limit 1").fetchone()
    new = q.upper().replace(" ", "\u00a0", 1).replace("'", "\u2019") if plant == "quote_variant" else q + " and then some words the filing never said"
    con.execute("update ai_statements set quote = ? where statement_id = ?", [new, sid])
    con.close()
con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
cos = [proof.company(con, t) for t in proof.PROVEN]
if plant == "tie_on_untied":  # T92: a part checked by rule:ppe_categories_tie, forged to tie, whose filing's group does not tie on file
    g = next(g for g in proof.ladder(con, proof.PROVEN, proof.rules_on_file()[0])["groups"].values() if g["rule"] == "ppe_categories_tie" and not g["holds"])
    it = next(i for c in cos if c["ticker"] == g["ticker"] for i in c["stages"]["facts"]["all"]
              if i["ref"].get("field") == g["field"] and i["ref"].get("period") == g["period"] and i["ref"].get("dimension") in g["dimensions"] and not i["ref"].get("finding"))
    it.update(state="checked", by="rule:ppe_categories_tie", key="tie")
    it["ref"]["tie"] = {"rule": "ppe_categories_tie", "key": g["key"], "accession": g["accession"], "concept": g["concept"], "total": g["total"], "sum": g["total"], "tolerance": g["tolerance"], "dimensions": g["dimensions"]}
    print(json.dumps({"untied": [g["ticker"], g["key"]]}))
if plant == "reading_once":  # T92: a second reading resting on one filing
    it = next(i for c in cos for i in c["stages"]["facts"]["all"] if i["by"] == "label:no_reference")
    it.update(state="checked", by="reading:0000000000-00-000000", key="second_reading")
    it["ref"]["readings"] = [{"accession": "0000000000-00-000000", "filed": "2025-01-01", "value": 1, "scale": 1}]
types = proof.asset_types()
RUNGS = ("tie", "second_reading", "label:no_reference", "rule:fact_readings_differ")  # T92: the rungs an untagged fact can sit on
rung = lambda i: i["key"] if i["key"] in RUNGS else i["by"]
untagged = [(c["ticker"], i) for c in cos for i in c["stages"]["facts"]["all"] if not i["ref"].get("finding") and rung(i) in RUNGS]
print(json.dumps({"untagged": len(untagged), "ladder": {k: sum(1 for _, i in untagged if rung(i) == k) for k in RUNGS},
                  "differ": [[t, i["what"]] for t, i in untagged if i["by"] == "rule:fact_readings_differ"]}))
print(json.dumps({"gaps": proof.unevidenced(con, companies=cos),
                  "nr_open": [[c["ticker"], i["what"], i["state"]] for c in cos for i in c["stages"]["values"]["all"] if i["by"] == "label:not_reported" and i["state"] != "explained"],
                  "walked": sum(1 for c in cos for s in c["stages"].values() for i in s["all"] if i["state"] in ("checked", "explained")),
                  "unconfirmed": sum(1 for c in cos for i in c["stages"]["mapping"]["all"] if ((types.get(c["ticker"]) or {}).get(i["name"]) or {}).get("standard_type")
                                     and not status.confirmed((types.get(c["ticker"]) or {}).get(i["name"])))}, default=str))
'''


class EveryCheckedRowNamesItsEvidence(unittest.TestCase):
    """T80 on the six: every checked or explained row of the frozen fixtures, through proof.company and status.state,
    points at a record that exists; planting a bare label turns the walk red. The fixtures must exist: a walk over
    nothing would pass."""

    def walk(self, plant: str) -> dict:
        self.assertTrue((golden.FIXTURES / "seed.json").exists(), "the golden fixtures are missing: the walk would pass vacuously")
        root = fixture_root()
        try:
            out = subprocess.run([sys.executable, "-c", WALK, plant], cwd=store.ROOT, env={**os.environ, "LEDGER_ROOT": str(root)}, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            lines = [json.loads(l) for l in out.stdout.strip().splitlines() if l.startswith("{")]
            return {k: v for l in lines for k, v in l.items()}
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_six_as_they_are(self):
        r = self.walk("none")
        self.assertGreater(r["walked"], 800)  # the walk saw the rows, not an empty board
        self.assertEqual(r["gaps"], [], "checked or explained rows with no evidence on file")

    def test_planted_not_reported_with_an_xbrl_value(self):
        r = self.walk("not_reported")  # T81: of_value opens it (one verdict with the completeness line), so it claims nothing
        self.assertEqual(r["gaps"], [])
        self.assertEqual([(t, st) for t, _, st in r["nr_open"]], [("MSFT", "open")], r["nr_open"])
        self.assertIn("not_reported", r["nr_open"][0][1])

    def test_planted_no_reference_on_a_fact_xbrl_holds(self):
        gaps = self.walk("no_reference_fact")["gaps"]
        self.assertEqual([(g["ticker"], g["stage"], g["by"]) for g in gaps], [("MSFT", "facts", "label:no_reference")], gaps)
        self.assertIn("XBRL holds", gaps[0]["gap"])

    def test_planted_xbrl_lookup_never_ran(self):
        r = self.walk("no_lookup_values")
        gaps = r["gaps"]
        self.assertTrue(gaps and all(g["ticker"] == "MSFT" and g["stage"] == "values" and g["by"] == "xbrl" for g in gaps), gaps)
        self.assertTrue(r["nr_open"] and all(t == "MSFT" and st == "open" for t, _, st in r["nr_open"]), r["nr_open"])  # T81: unasked, not_reported is open

    def test_planted_fact_whose_instance_is_absent(self):
        r = self.walk("no_instance")
        self.assertTrue(r["gaps"] and all(g["ticker"] == "MSFT" and g["stage"] == "facts" for g in r["gaps"]), r["gaps"])
        self.assertTrue(any(g["by"] == "label:no_reference" and "not looked up" in g["gap"] for g in r["gaps"]), r["gaps"])

    def test_planted_mapping_without_confirmed_by_forced_to_checked(self):
        r = self.walk("mapping")
        self.assertGreater(r["unconfirmed"], 0)
        self.assertEqual(len(r["gaps"]), r["unconfirmed"], r["gaps"][:3])
        self.assertTrue(all(g["stage"] == "mapping" and g["gap"].endswith("has no confirmed_by") for g in r["gaps"]), r["gaps"][:3])

    def test_planted_confirmed_by_claude(self):
        r = self.walk("claude")
        self.assertEqual(r["checked_by_claude"], 0)  # status.confirmed refuses it: the stage stays open
        self.assertGreater(len(r["gaps"]), 0)
        self.assertTrue(all(g["stage"] == "mapping" and "'Claude' is not a person" in g["gap"] for g in r["gaps"]), r["gaps"][:3])

    def test_planted_resolution_that_does_not_exist(self):
        r = self.walk("resolution")
        gaps = r["gaps"]
        self.assertEqual([(g["ticker"], g["stage"], g["by"]) for g in gaps], [(r["planted_on"], "facts", "resolution:not-on-file")], gaps)
        self.assertIn("no such resolution", gaps[0]["gap"])

    def test_planted_resolution_by_a_name_off_the_list(self):
        r = self.walk("gemini")
        gaps = r["gaps"]
        self.assertEqual([(g["ticker"], g["stage"], g["by"]) for g in gaps], [(r["planted_on"], "facts", "resolution:planted-gemini")], gaps)
        self.assertIn("'Gemini', not a person", gaps[0]["gap"])

    def test_planted_tie_on_a_group_that_does_not_tie(self):
        """T92: the walk accepts rule:*_tie only when the item's group ties on file, not because the row says it does."""
        r = self.walk("tie_on_untied")
        gaps = r["gaps"]
        self.assertEqual([(g["ticker"], g["stage"], g["by"]) for g in gaps], [(r["untied"][0], "facts", "rule:ppe_categories_tie")], gaps)
        self.assertIn("does not tie", gaps[0]["gap"])

    def test_planted_second_reading_on_one_filing(self):
        gaps = self.walk("reading_once")["gaps"]
        self.assertEqual([(g["stage"], g["by"]) for g in gaps], [("facts", "reading:0000000000-00-000000")], gaps)
        self.assertIn("fewer than two filings", gaps[0]["gap"])

    def test_the_ladder_on_the_six(self):
        """T92 on the fixtures: every untagged fact sits on one rung (a tie, a second reading, citation only, or open
        because its readings differ), and Applied Digital's two disagreeing readings are open, not explained."""
        r = self.walk("none")
        self.assertEqual(r["gaps"], [])
        lad = r["ladder"]
        self.assertEqual(sum(lad.values()), r["untagged"], lad)
        self.assertGreater(lad["tie"], 0)
        self.assertGreater(lad["second_reading"], 0)
        self.assertEqual(sorted(r["differ"]), [["APLD", "ppe_category Other equipment and fixtures FY2024: readings differ"], ["APLD", "ppe_category Other equipment and fixtures FY2025: readings differ"]])

    def test_planted_gate_on_another_stage(self):
        gaps = self.walk("gate")["gaps"]
        self.assertTrue(gaps and all(g["stage"] == "values" and g["by"] == "gate" and "only the release stage" in g["gap"] for g in gaps), gaps[:3])

    def test_a_quote_differing_only_in_curly_quotes_space_or_case_holds(self):
        self.assertEqual(self.walk("quote_variant")["gaps"], [])
        gaps = self.walk("quote_changed")["gaps"]
        self.assertEqual([(g["ticker"], g["stage"], g["by"]) for g in gaps], [("MSFT", "statements", "quote")], gaps)


@unittest.skipIf(not (golden.FIXTURES / "seed.json").exists(), "no fixtures")
class ProofAgreesWithReconcile(unittest.TestCase):
    """On the frozen tables of the proven set, Proof's open count equals Reconcile's, company by company."""

    def test_open_counts_agree_on_the_fixtures(self):
        root = fixture_root()
        try:
            out = subprocess.run([sys.executable, "-c", SCRIPT], cwd=store.ROOT, env={**os.environ, "LEDGER_ROOT": str(root)}, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            r = json.loads(out.stdout.strip().splitlines()[-1])
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(sorted(r["proof"]), sorted(PROVEN))
        self.assertEqual(r["proof"], r["reconcile"], f"Proof and Reconcile disagree on what is open: {r}")
        self.assertEqual(r["proof_total"], sum(r["reconcile"].values()))
        # T63: the mapping stage counts a mapping as checked only when a person confirmed it; every entry without
        # confirmed_by is open as to confirm, and with the unmapped ones that is exactly what waits for a person
        self.assertEqual(r["mapping_open"], r["waiting"])
        self.assertEqual(r["mapping_to_confirm"], r["to_confirm"])
        self.assertEqual(r["open_names"], r["waiting_names"])  # the same names, not just the same counts
        self.assertEqual(r["checked_names"], r["confirmed_names"])
        self.assertEqual(r["tax_to_confirm"], r["to_confirm_names"])  # T63: the taxonomy rows say to_confirm, mapped false, for exactly those entries
        self.assertEqual(r["tax_mapped_unconfirmed"], 0)  # the exported rows never say mapped on an unconfirmed entry
        self.assertTrue(all(n <= 0 for n in r["mapping_checked_unconfirmed"].values()), r["mapping_checked_unconfirmed"])  # never more checked than confirmed entries
        self.assertTrue(set(r["states"]) <= set(status.STATES) | {"to confirm"}, r["states"])  # "to confirm": T3's group, the decisions a run left for a person (decisions/ is in the root since T31)
        # T56: on the board, rows by key grade sum to the denominator, per company and in total; a keyed item is on its trail
        grades = (*status.KEY_GRADE, "none")
        for t, k in r["company_keys"].items():
            self.assertEqual(sum(k[g] for g in grades), k["rows"], (t, k))
            self.assertEqual(k["rows"], r["stage_rows"][t], t)
            self.assertEqual(k["rows"] - k["none"], r["keyed_items"][t], t)
            self.assertGreater(k["twin"], 0, t)  # every proven company has rows XBRL confirms
        for g in (*grades, "rows"):
            self.assertEqual(r["keys"][g], sum(k[g] for k in r["company_keys"].values()), g)


if __name__ == "__main__":
    unittest.main()
