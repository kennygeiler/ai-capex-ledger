"""A calculated figure says so (ledger/checks/calc.py) and the gold set puts the hard items first with an honest error rate
per group (ledger/review/gold.py group, ordered, rates). The review-fixes branch, from Kenny's screenshots of 2 Nov 2026.

Pre-mortem (docs/BUILD.md), one test per answer:
 1 a label standing in for a check: the arithmetic is recomputed from the inputs, never copied from the stored value;
   inputs that do not give the value say so (Calc.test_inputs_that_do_not_give_the_value_say_so).
 2 a vacuous pass: no printed total and no XBRL value is no cross-check at all, never "matches"
   (Calc.test_nothing_to_compare_is_no_check); an empty group has no rate (Groups.test_rates_per_group_add_up).
 3 one decision closing others: a group is read per item from its own claim (Groups.test_each_item_its_own_group).
 4 two consumers disagreeing: the trail's card and the gold set read calc.for_ticker; the API's group numbers are
   gold.rates (Consumers).
 5 degenerate cases: one cell is not a calculation; a cost line split in parts reads as one bracketed term; a negative
   operating income is bracketed (Calc.test_parts_and_a_loss).
 6 late writes: read-only, nothing written (no test needed: calc and rates write nothing).
 7 wording that claims more: a "Total costs and expenses" line holds cost of revenue and is never "the filing's own
   total" (Calc.test_a_wider_total_is_not_the_filings_own); "differs by" names a line only when one is that amount.
 8 stale input: the group comes from the claim on file, so the Proof page and the API agree with or without a database
   (Groups.test_the_group_is_the_claims_not_the_databases).
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from ledger.checks import calc
from ledger.core import states
from ledger.review import gold

M = 1_000_000
AMD_TABLE = {"id": "t0010", "columns": ["Year Ended | December 27,2025", "Year Ended | December 28,2024"], "rows": [
    {"label": "Net revenue", "cells": [{"col": 0, "text": "34,639", "value": 34639.0}]},
    {"label": "Total cost of sales", "cells": [{"col": 0, "text": "17,487", "value": 17487.0}]},
    {"label": "Total operating expenses", "cells": [{"col": 0, "text": "13,458", "value": 13458.0}, {"col": 1, "text": "10,825", "value": 10825.0}]},
    {"label": "Operating income", "cells": [{"col": 0, "text": "3,694", "value": 3694.0}]}]}


def _cell(eid, field, row, value, scale=M, col="Year Ended | December 27,2025", table="t0010"):
    return {"extraction_id": eid, "field": field, "row_label": row, "column_label": col, "value": value, "scale": scale, "table_id": table}


AMD = [_cell("r", "revenue", "Net revenue", 34_639 * M), _cell("c", "cost_of_revenue", "Total cost of sales", 17_487 * M),
       _cell("o", "operating_income", "Operating income", 3_694 * M)]
K = 1_000
APLD = [_cell("r", "revenue", "Total revenue", 611_311 * K, K, "Fiscal Year Ended | May 31, 2026", "t0021"),
        _cell("p1", "cost_of_revenue_part", "Services cost of revenue", 396_858 * K, K, "Fiscal Year Ended | May 31, 2026", "t0021"),
        _cell("p2", "cost_of_revenue_part", "Data center rental and other cost of revenue", 56_771 * K, K, "Fiscal Year Ended | May 31, 2026", "t0021"),
        _cell("o", "operating_income", "Operating loss", -236_462 * K, K, "Fiscal Year Ended | May 31, 2026", "t0021")]


class Calc(unittest.TestCase):
    def check(self, c, against):
        return next(x for x in c["checks"] if x["against"] == against)

    def test_amd_opex_says_how_it_was_calculated(self):
        c = calc.calculation("opex", 13_458 * M, AMD, 13_458 * M, AMD_TABLE)
        self.assertEqual(c["line"], "Calculated: revenue − cost of revenue − operating income = $13,458M")
        self.assertEqual(c["arithmetic"], "$34,639M − $17,487M − $3,694M = $13,458M")
        self.assertEqual([i["role"] for i in c["inputs"]], ["Revenue", "Cost of revenue", "Operating income"])
        self.assertTrue(c["holds"])
        self.assertEqual([x["text"] for x in c["checks"]], ["Filing’s own total: $13,458M · matches", "SEC XBRL: $13,458M · matches"])
        self.assertEqual(c["checks"][0]["row"], "Total operating expenses")

    def test_apld_definition_gap_names_the_line(self):
        c = calc.calculation("opex", 394_144 * K, APLD, 450_915 * K)
        self.assertEqual(c["arithmetic"], "$611.3M − ($56.8M + $396.9M) − (−$236.5M) = $394.1M")
        x = self.check(c, "xbrl")
        self.assertEqual((x["state"], x["diff"]), ("differs", -56_771 * K))  # XBRL is never "explained": only the filing's own total is
        self.assertEqual(x["by_line"]["row"], "Data center rental and other cost of revenue")
        self.assertEqual(x["text"], "SEC XBRL: $450.9M · differs by $56.8M · Data center rental and other cost of revenue line")

    def test_a_difference_no_line_explains_names_none(self):
        x = self.check(calc.calculation("opex", 394_144 * K, APLD, 400_000 * K), "xbrl")
        self.assertEqual((x["state"], x["by_line"]), ("differs", None))
        self.assertTrue(x["text"].endswith("differs by $5.9M"))

    def test_sign_matters(self):
        """The other total LOWER by a cost line is not that line (we subtract it; a total without it would be higher)."""
        x = self.check(calc.calculation("opex", 394_144 * K, APLD, (394_144 - 56_771) * K), "xbrl")
        self.assertEqual((x["state"], x["by_line"]), ("differs", None))

    def test_two_lines_of_the_amount_name_none(self):
        cells = APLD[:1] + [{**APLD[1], "value": 56_771 * K}] + APLD[2:]
        ours = calc.calculation("opex", None, cells)["result"]
        x = self.check(calc.calculation("opex", None, cells, ours + 56_771 * K), "xbrl")
        self.assertEqual(x["state"], "differs")
        self.assertIsNone(x["by_line"])
        self.assertNotIn(" line", x["text"])

    def test_the_xbrl_check_never_reads_the_table(self):
        t = json.loads(json.dumps(AMD_TABLE))
        t["rows"].append({"label": "Other", "cells": [{"col": 0, "text": "3", "value": 3.0}]})
        x = self.check(calc.calculation("opex", 13_458 * M, AMD, 13_461 * M, t), "xbrl")
        self.assertEqual((x["state"], x["by_line"]), ("differs", None))  # the table's "Other" $3M row is not an XBRL concept

    def test_inputs_that_do_not_give_the_value_say_so(self):
        c = calc.calculation("opex", 13_459 * M, AMD, None, AMD_TABLE)
        self.assertFalse(c["holds"])
        self.assertEqual(c["result"], 13_458 * M)  # the line shows what the inputs give, never the stored value

    def test_nothing_to_compare_is_no_total(self):
        c = calc.calculation("opex", 13_458 * M, AMD)
        self.assertEqual([(x["against"], x["state"], x["text"]) for x in c["checks"]],
                         [("filing", "none", "Filing’s own total: No total to compare"), ("xbrl", "none", "SEC XBRL: No total to compare")])
        self.assertNotEqual(states.CROSSCHECK.get("none").kind, states.GOOD)
        t = json.loads(json.dumps(AMD_TABLE))
        t["columns"] = ["Year Ended | December 28,2024"]  # the inputs' column is not in the table
        self.assertEqual(self.check(calc.calculation("opex", 13_458 * M, AMD, None, t), "filing")["state"], "none")

    def test_degenerate(self):
        self.assertIsNone(calc.calculation("opex", 5, AMD[:1]))
        self.assertIsNone(calc.calculation("capex", 5, AMD))

    def test_parts_and_a_loss(self):
        c = calc.calculation("opex", 394_144 * K, APLD)
        self.assertEqual([i["role"] for i in c["inputs"]], ["Revenue", "Cost of revenue", "Cost of revenue", "Operating income"])
        self.assertIn("(−$236.5M)", c["arithmetic"])

    def test_rounded_terms_that_do_not_add_up_print_exact_dollars(self):
        cells = [_cell("r", "revenue", "Revenue", 1_240_000, 1), _cell("c", "cost_of_revenue", "Cost", 1_160_000, 1), _cell("o", "operating_income", "OI", 40_000, 1)]
        c = calc.calculation("opex", 40_000, cells)
        self.assertEqual(c["arithmetic"], "$1,240,000 − $1,160,000 − $40,000 = $40,000")  # $1.2M − $1.2M − $40,000 ≠ $40,000
        self.assertTrue(c["exact"])
        self.assertFalse(calc.calculation("opex", 13_458 * M, AMD)["exact"])

    def test_a_wider_total_is_not_the_filings_own(self):
        t = json.loads(json.dumps(AMD_TABLE))
        t["rows"][2]["label"] = "Total costs and expenses"
        self.assertEqual(self.check(calc.calculation("opex", 13_458 * M, AMD, None, t), "filing")["state"], "none")

    def test_a_filing_total_off_by_exactly_one_input_is_explained(self):
        t = json.loads(json.dumps(AMD_TABLE))
        t["rows"][2]["cells"][0]["value"] = 30945.0  # Amazon-shaped: the printed total includes cost of sales
        x = self.check(calc.calculation("opex", 13_458 * M, AMD, None, t), "filing")
        self.assertEqual((x["state"], x["by_line"]["row"]), ("explained", "Total cost of sales"))
        self.assertEqual(x["text"], "Filing’s total includes total cost of sales · $17,487M")
        self.assertNotEqual(states.CROSSCHECK.get("explained").kind, states.OPEN)

    def test_explained_needs_an_exact_input_and_no_other_line(self):
        t = json.loads(json.dumps(AMD_TABLE))
        t["rows"][2]["cells"][0]["value"] = 30946.0  # off by a million more than the cost line: within no rule
        self.assertEqual(self.check(calc.calculation("opex", 13_458 * M, AMD, None, t), "filing")["state"], "differs")
        t = json.loads(json.dumps(AMD_TABLE))
        t["rows"][2]["cells"][0]["value"] = 30945.0
        t["rows"].append({"label": "Other charges", "cells": [{"col": 0, "text": "17,487", "value": 17487.0}]})  # a second line of the amount
        x = self.check(calc.calculation("opex", 13_458 * M, AMD, None, t), "filing")
        self.assertEqual((x["state"], x["by_line"]), ("differs", None))


def _db(tmp: Path):
    con = duckdb.connect(":memory:")
    con.execute('create table "values" (ticker varchar, field varchar, period varchar, value bigint, label varchar, extraction_ids varchar)')
    con.execute("create table extractions (extraction_id varchar, ticker varchar, accession varchar, field varchar, table_id varchar, row_label varchar, column_label varchar, cell_text varchar, value bigint, scale bigint)")
    con.execute("create table reference_values (ticker varchar, field varchar, period varchar, value bigint)")
    con.execute("create table documents (accession varchar, ticker varchar, cik integer)")
    con.execute("create table facts (ticker varchar, field varchar, dimension varchar, period varchar, value bigint, label varchar, reference bigint)")
    for c in AMD:
        con.execute("insert into extractions values (?, 'AMD', 'A1', ?, ?, ?, ?, '', ?, ?)", [c["extraction_id"], c["field"], c["table_id"], c["row_label"], c["column_label"], c["value"], c["scale"]])
    con.execute("""insert into "values" values ('AMD', 'opex', 'FY2025', 13458000000, 'agree', 'c,o,r'), ('AMD', 'revenue', 'FY2025', 34639000000, 'agree', 'r')""")
    con.execute("insert into reference_values values ('AMD', 'opex', 'FY2025', 13458000000)")
    con.execute("insert into documents values ('A1', 'AMD', 2488)")
    (tmp / "0000002488").mkdir(parents=True)
    (tmp / "0000002488" / "A1.tables.json").write_text(json.dumps({"tables": [AMD_TABLE]}))
    return con


class Consumers(unittest.TestCase):
    def test_one_reading_per_company(self):
        tmp = Path(tempfile.mkdtemp())
        con = _db(tmp)
        got = calc.for_ticker(con, "AMD", root=tmp)
        self.assertEqual(list(got), [("opex", "FY2025")])  # revenue, one cell, is no calculation
        self.assertEqual(got[("opex", "FY2025")]["checks"][0]["state"], "matches")

    def test_the_trail_and_the_gold_set_read_calc_for_ticker(self):
        import inspect
        from ledger.web import app, cards
        self.assertIn("calc.for_ticker(con, t)", inspect.getsource(cards.add))
        self.assertIn("gold.live_groups(con, docs)", inspect.getsource(app.gold_view))
        self.assertIn("calc_.for_ticker(con, t)", inspect.getsource(gold.live_groups))
        self.assertIn("gold.rates(every, groups)", inspect.getsource(app.gold_view))
        self.assertIn("gold.group_note(", inspect.getsource(app.gold_view))

    def test_a_label_with_a_comma_keeps_its_cell(self):
        tmp = Path(tempfile.mkdtemp())
        con = _db(tmp)
        lab = "Fuel, purchased power costs, and delivery fees"
        eid = f"0000000000-26-000001|cost_of_revenue_part|2025-01-01|2025-12-31|{lab}"
        con.execute("delete from extractions where extraction_id = 'c'")
        con.execute("insert into extractions values (?, 'AMD', 'A1', 'cost_of_revenue_part', 't0010', ?, 'Year Ended | December 27,2025', '', ?, ?)", [eid, lab, 17_487 * M, M])
        con.execute("""update "values" set extraction_ids = ? where field = 'opex'""", [f"o,r,{eid}"])
        c = calc.for_ticker(con, "AMD", root=tmp)[("opex", "FY2025")]
        self.assertEqual([i["row"] for i in c["inputs"]], ["Net revenue", lab, "Operating income"])
        self.assertTrue(c["holds"])


def _it(**kw):
    return {"id": kw.pop("id", "x"), "kind": "value", "ticker": "AMD", "field": "revenue", "period": "FY2025", "value": 1, "verdict": None,
            "label": "agree", "untagged": False, "xbrl": 1, "cites": [{"extraction_id": "a"}], **kw}


HOLDS = {"holds": True}


class Groups(unittest.TestCase):
    def test_every_label_has_its_group(self):
        """One group per reconcile label (states.CHECK's names, the labels values and facts carry), and for no label."""
        want = {"agree": "xbrl", "unresolved": "definition", "definition_gap": "definition", "no_reference": "no_counterpart",
                "not_reported": "no_counterpart", "not_extracted": "not_extracted", "unknown": "not_reconciled"}
        self.assertEqual(set(want), set(states.CHECK.names()))
        for lab, g in want.items():
            self.assertEqual(gold.group(_it(label=lab)), g, lab)
        for lab in (None, "", "bogus"):
            self.assertEqual(gold.group(_it(label=lab)), "not_reconciled", lab)
        self.assertEqual(set(gold.GROUP_OF_LABEL.values()) | {"xbrl", "calculated", "not_reconciled"}, set(states.GOLD_GROUP.names()))

    def test_each_item_its_own_group(self):
        self.assertEqual(gold.group(_it()), "xbrl")
        self.assertEqual(gold.group(_it(field="opex", cites=[{}, {}, {}]), HOLDS), "calculated")
        self.assertEqual(gold.group(_it(field="opex", cites=[{}, {}, {}])), "xbrl")  # no calculation on hand: its label's group
        self.assertEqual(gold.group(_it(field="opex", cites=[{}, {}, {}]), {"holds": False}), "xbrl")  # a calculation that does not hold is not Calculated
        self.assertEqual(gold.group(_it(field="opex", label="definition_gap", cites=[{}, {}, {}, {}]), HOLDS), "definition")
        self.assertEqual(gold.group(_it(kind="fact", field="ppe_category", label="no_reference", untagged=True, xbrl=None)), "no_counterpart")
        self.assertEqual(gold.group(_it(kind="fact", field="segment_revenue", cites=[{}, {}]), HOLDS), "xbrl")  # two readings of one figure: not a calculation
        self.assertEqual(gold.group(_it(xbrl=None)), "no_counterpart")

    def test_nothing_unreadable_lands_in_a_machine_checked_group(self):
        for it in ({}, None, _it(label=None), _it(label="bogus")):
            self.assertEqual(gold.group(it), "not_reconciled", it)
        self.assertNotEqual(states.GOLD_GROUP.get(states.GOLD_GROUP.absent).kind, states.GOOD)

    def test_hard_first_and_stable(self):
        items = [_it(id="a"), _it(id="b", label="no_reference", xbrl=None), _it(id="c", field="opex", cites=[{}, {}, {}]), _it(id="d", label="definition_gap"),
                 _it(id="e", label="no_reference", xbrl=None), _it(id="f", label="not_extracted"), _it(id="g", label=None)]
        live = {"c": {"claim": "calculated", "live": "calculated", "calc": HOLDS}}
        self.assertEqual([i["id"] for i in gold.ordered(items, live)], ["b", "e", "d", "f", "g", "c", "a"])

    def test_rates_per_group_add_up(self):
        items = [_it(id="a", verdict="right"), _it(id="b", label="no_reference", xbrl=None, verdict="wrong"), _it(id="c", label="no_reference", xbrl=None, verdict="right"),
                 _it(id="d", label="no_reference", xbrl=None, verdict="cant_say"), _it(id="e", label="no_reference", xbrl=None)]
        r = gold.rates(items)
        self.assertEqual(r["headline"], "no_counterpart")
        self.assertEqual([g["id"] for g in r["groups"]], list(states.GOLD_GROUP_ORDER))
        g = {x["id"]: x["rate"] for x in r["groups"]}
        self.assertEqual((g["no_counterpart"]["right"], g["no_counterpart"]["wrong"], g["no_counterpart"]["cant_say"], g["no_counterpart"]["unverified"]), (1, 1, 1, 1))
        self.assertEqual(g["no_counterpart"]["n"], 2)
        self.assertIsNotNone(g["no_counterpart"]["interval"])
        self.assertIsNone(g["definition"]["interval"])  # an empty group: no rate, no interval, never 0%
        self.assertIsNone(g["definition"]["rate"])
        for k in ("right", "wrong", "cant_say", "unverified", "items"):
            self.assertEqual(sum(x["rate"][k] for x in r["groups"]), r["all"][k], k)

    def test_an_item_counts_under_its_live_group_and_keeps_its_verdict(self):
        items = [_it(id="a", verdict="wrong", note="x")]
        live = {"a": {"claim": "xbrl", "live": "definition", "calc": None}}
        g = {x["id"]: x["rate"] for x in gold.rates(items, live)["groups"]}
        self.assertEqual((g["definition"]["wrong"], g["xbrl"]["items"]), (1, 0))
        self.assertEqual(items[0]["verdict"], "wrong")

    def test_live_groups_reads_the_live_label_and_flags_a_move(self):
        tmp = Path(tempfile.mkdtemp())
        con = _db(tmp)
        doc = {"items": [_it(id="v", field="revenue", period="FY2025"), _it(id="o", field="opex", period="FY2025", cites=[{}, {}, {}])]}
        with mock.patch("ledger.checks.calc.DOCS", tmp):
            got = gold.live_groups(con, {"AMD": doc})
        self.assertEqual((got["o"]["claim"], got["o"]["live"]), ("calculated", "calculated"))
        con.execute("""update "values" set label = 'unresolved' where field = 'revenue'""")
        with mock.patch("ledger.checks.calc.DOCS", tmp):
            got = gold.live_groups(con, {"AMD": doc})
        self.assertEqual((got["v"]["claim"], got["v"]["live"]), ("xbrl", "definition"))
        self.assertEqual(gold.group_note(got["v"]), "Group changed since draw: was Matches SEC XBRL, now Definition differs")
        self.assertIsNone(gold.group_note(got["o"]))
        con.execute("""delete from "values" where field = 'revenue'""")  # the row gone: never a checked group
        with mock.patch("ledger.checks.calc.DOCS", tmp):
            self.assertEqual(gold.live_groups(con, {"AMD": doc})["v"]["live"], "not_reconciled")

    def test_the_group_is_the_claims_when_the_database_is_busy(self):
        from ledger.web import app
        doc = {"items": [_it(id="a", verdict="right"), _it(id="b", xbrl=None, kind="fact", field="ppe_category", label="no_reference", untagged=True)]}
        with mock.patch.object(gold, "load_checked", return_value=({"AMD": doc}, [])), mock.patch.object(app, "_con", side_effect=app.Busy("busy")):
            v = app.gold_view("AMD")
            top = app.gold_view()
        self.assertEqual([(i["id"], i["group"]) for i in v["items"]], [("b", "no_counterpart"), ("a", "xbrl")])
        self.assertEqual(top["groups"], gold.rates(doc["items"])["groups"])
        self.assertEqual(top["companies"][0]["rates"]["groups"], top["groups"])
        self.assertEqual((top["headline"], top["groups_live"]), ("no_counterpart", False))
