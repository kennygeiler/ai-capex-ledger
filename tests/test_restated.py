"""A fact whose readings disagree across filings (ledger/checks/ties.py restatement) and a segment series that mixes bases
across a re-segmentation (segment_basis, rules/segment_basis_mixed.yaml). The pre-mortem, docs/BUILD.md:

 1 label standing in for a check: the restatement is display only; a fact checked by its XBRL twin stays checked
   (DisplayOnly), an untagged one stays open by fact_readings_differ.
 2 vacuous pass: readings that agree, one reading, or none give no line (Restatement.test_agreeing_or_single_readings_say_nothing).
 3 one decision closing other items: segment_basis_mixed fires once per field and year, keyed by its cutover filing; it
   explains nothing and is explained by nothing but a person (SegmentBasis.test_fires_only_on_open_years_never_on_explained_rows).
 4 two consumers disagreeing: the trail, the gold item, the evidence page and Reconcile all read ties.restatement
   (OneFunction).
 5 degenerate cases: a rounding difference (thousands vs millions) is no restatement; a return to an earlier figure is
   three steps; a segment dropped with no figure printed two ways is not seen (documented, reports/segment-basis.md).
 6 late or concurrent writes: nothing is written; pure functions over the tables.
 7 wording that claims more than the check proves: "has no FY2022 reading", not "prints no FY2022"; "dataset uses", not "correct".
 8 stale input: read from the database on each request, like the ladder.
"""
from __future__ import annotations

import os
import unittest

from ledger.checks import ties
from ledger.checks.rules import CHECKS, Context
from ledger.core import states, status, store

HAS_DB = store.DEFAULT_DB.exists() and not os.environ.get("LEDGER_SKIP_DB")
MSFT_IC = ("MSFT", "segment_revenue", "Intelligent Cloud", "FY2024")
OLD, MID, NEW = "0000950170-24-087843", "0000950170-25-100235", "0001193125-26-323660"


def r(acc, filed, value, cell, scale=1_000_000):
    return {"accession": acc, "filed": filed, "form": "10-K", "period": filed[:4], "value": value, "scale": scale,
            "extraction_id": f"{acc}|segment_revenue|X|2024-06-30", "cell_text": cell}


class Restatement(unittest.TestCase):
    def test_the_line_says_every_figure_as_filed_and_which_one_the_dataset_uses(self):
        rs = [r(OLD, "2024-07-30", 105_362_000_000, "105,362"), r(MID, "2025-07-30", 87_464_000_000, "87,464"), r(NEW, "2026-07-29", 87_464_000_000, "87,464")]
        rec = ties.restatement(rs, NEW)
        self.assertEqual(rec["line"], "Restated: 105,362 (10-K 2024-07-30) → 87,464 (10-K 2025-07-30, 10-K 2026-07-29) · dataset uses 87,464 (10-K 2026-07-29)")
        self.assertEqual(rec["superseded"], [rs[0]["extraction_id"]])
        self.assertEqual(rec["compare"], {"a": rs[0]["extraction_id"], "b": rs[2]["extraction_id"]})
        self.assertEqual(rec["used"]["accession"], NEW)
        self.assertTrue(rec["line"].startswith(states.RESTATED))

    def test_agreeing_or_single_readings_say_nothing(self):
        self.assertIsNone(ties.restatement([], None))
        self.assertIsNone(ties.restatement([r(OLD, "2024-07-30", 5, "5")], OLD))
        self.assertIsNone(ties.restatement([r(OLD, "2024-07-30", 87_464_000_000, "87,464"), r(NEW, "2026-07-29", 87_464_000_000, "87,464")], NEW))
        # one filing in millions, the next in thousands: 87,464 vs 87,463,800 is rounding, not a restatement
        self.assertIsNone(ties.restatement([r(OLD, "2024-07-30", 87_464_000_000, "87,464"), r(NEW, "2026-07-29", 87_463_800_000, "87,463,800", 1000)], NEW))

    def test_a_return_to_an_earlier_figure_is_three_steps_and_only_the_others_are_superseded(self):
        rs = [r(OLD, "2024-07-30", 10_000_000, "10"), r(MID, "2025-07-30", 12_000_000, "12"), r(NEW, "2026-07-29", 10_000_000, "10")]
        rec = ties.restatement(rs, NEW)
        self.assertEqual([s["cell_text"] for s in rec["steps"]], ["10", "12", "10"])
        self.assertEqual(rec["superseded"], [rs[1]["extraction_id"]])

    def test_mark_puts_the_word_only_under_superseded_readings(self):
        rs = [r(OLD, "2024-07-30", 1_000_000, "1"), r(NEW, "2026-07-29", 2_000_000, "2")]
        rec = ties.restatement(rs, NEW)
        got = ties.mark([{"extraction_id": x["extraction_id"]} for x in rs], rec)
        self.assertEqual([g.get("mark") for g in got], [states.SUPERSEDED, None])
        self.assertEqual(ties.mark([{"extraction_id": "a"}], None), [{"extraction_id": "a"}])

    @unittest.skipUnless(HAS_DB, "no data/ledger.duckdb")
    def test_the_real_msft_intelligent_cloud_fy2024(self):
        import duckdb
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        try:
            rec = ties.restatements(con, ["MSFT"])[MSFT_IC]
            seen = ties.of_reading(con, "MSFT", f"{OLD}|segment_revenue|Intelligent Cloud|2024-06-30")
            used = ties.of_reading(con, "MSFT", f"{NEW}|segment_revenue|Intelligent Cloud|2024-06-30")
        finally:
            con.close()
        self.assertEqual(rec["line"], "Restated: 105,362 (10-K 2024-07-30) → 87,464 (10-K 2025-07-30, 10-K 2026-07-29) · dataset uses 87,464 (10-K 2026-07-29)")
        self.assertEqual(rec["superseded"], [f"{OLD}|segment_revenue|Intelligent Cloud|2024-06-30"])
        self.assertEqual((seen["mark"], used["mark"]), (states.SUPERSEDED, None))
        self.assertEqual(seen["restatement"]["line"], rec["line"])


class DisplayOnly(unittest.TestCase):
    """The restatement never decides a state: status.of_fact does, as before."""

    def lad(self, rs):
        return {("T", "segment_revenue", "X", "FY2024"): {"readings": rs, "tie": None, "restated": None, "filer_tag": None}}

    def test_a_tagged_fact_stays_verified_and_carries_the_line(self):
        rs = [r(OLD, "2024-07-30", 105_362_000_000, "105,362"), r(NEW, "2026-07-29", 87_464_000_000, "87,464")]
        f = {"ticker": "T", "field": "segment_revenue", "dimension": "X", "period": "FY2024", "label": "agree", "accession": NEW}
        st, ref = ties.fact_state(f, {}, self.lad(rs))
        self.assertEqual((st["state"], st["by"], states.row(st["state"], st["by"])), ("checked", "xbrl", "ok"))
        self.assertIn("Restated: 105,362", ref["restatement"]["line"])

    def test_an_untagged_fact_stays_open_by_its_rule(self):
        rs = [r(OLD, "2024-07-30", 9_552_000, "9,552", 1000), r(NEW, "2026-07-29", 1_760_000, "1,760", 1000)]
        f = {"ticker": "T", "field": "segment_revenue", "dimension": "X", "period": "FY2024", "label": "no_reference", "accession": NEW}
        st, ref = ties.fact_state(f, {}, self.lad(rs))
        self.assertEqual((st["state"], st["by"]), ("open", "rule:" + status.DIFFER))
        self.assertIn("restatement", ref)

    def test_agreeing_readings_add_nothing_to_the_record(self):
        rs = [r(OLD, "2024-07-30", 5_000_000, "5"), r(NEW, "2026-07-29", 5_000_000, "5")]
        f = {"ticker": "T", "field": "segment_revenue", "dimension": "X", "period": "FY2024", "label": "agree", "accession": NEW}
        self.assertNotIn("restatement", ties.fact_state(f, {}, self.lad(rs))[1])


@unittest.skipUnless(HAS_DB, "no data/ledger.duckdb")
class OneFunction(unittest.TestCase):
    """The trail, the gold item, the evidence page and Reconcile say the same line for the same fact."""

    def test_every_view_says_the_same_line(self):
        from ledger.checks import proof
        from ledger.web import app, cards
        con = app._con()
        try:
            want = ties.restatements(con, ["MSFT", "APLD"])
            trail = cards.add(con, proof.company(con, "MSFT"))
            ev = ties.of_reading(con, "MSFT", f"{OLD}|segment_revenue|Intelligent Cloud|2024-06-30")
        finally:
            con.close()
        item = next(i for i in trail["stages"]["facts"]["all"] if (i["ref"].get("field"), i["ref"].get("dimension"), i["ref"].get("period")) == MSFT_IC[1:])
        self.assertEqual(item["card"]["restatement"]["line"], want[MSFT_IC]["line"])
        self.assertEqual(item["card"]["compare"], want[MSFT_IC]["compare"])
        self.assertEqual([w.get("mark") for w in item["card"]["where"]], [states.SUPERSEDED, None, None])
        self.assertEqual(states.row(item["state"], item["by"]), "ok")  # still Verified: the line is display only
        self.assertEqual(ev["restatement"]["line"], want[MSFT_IC]["line"])
        g = next((i for i in app.gold_view("MSFT")["items"] if i["id"] == "fact|MSFT|segment_revenue|Intelligent Cloud|FY2024"), None)
        if g is not None:  # the item is in the drawn sample on this checkout
            self.assertEqual(g["restatement"]["line"], want[MSFT_IC]["line"])
            self.assertEqual([c.get("mark") for c in g["cites"]], [states.SUPERSEDED, None, None])

    def test_reconcile_drawer_reads_the_same_record(self):
        from ledger.review import workbench
        from ledger.web import app
        flow = app._flow("APLD")
        con = app._con()
        try:
            rows = workbench.items(con, flow)["rows"]
            want = ties.restatements(con, ["APLD"])
        finally:
            con.close()
        differ = [x for x in rows if x["cause"] == "finding_unconfirmed" and (x["evidence"].get("restatement") or {}).get("line")]
        self.assertTrue(differ, "an APLD readings-differ row carries its restatement")
        for x in differ:
            self.assertIn(x["evidence"]["restatement"]["line"], {v["line"] for v in want.values()})


def nx(acc, filed, dim, end, value, cell):
    return {"extraction_id": f"{acc}|segment_revenue|{dim}|{end}", "accession": acc, "ticker": "T", "field": "segment_revenue", "dimension": dim,
            "period_end": end, "value": value, "scale": 1_000_000, "cell_text": cell, "filed": filed, "form": "10-K", "period": filed}


def fx(dim, period, value, ids, acc, label="agree"):
    return {"ticker": "T", "field": "segment_revenue", "dimension": dim, "period": period, "value": value, "label": label, "accession": acc, "extraction_ids": ",".join(ids)}


class SegmentBasis(unittest.TestCase):
    def series(self, resegment=True):
        M = 1_000_000
        a22, a23 = nx("A", "2023-07-01", "Cloud", "2022-06-30", 70 * M, "70"), nx("A", "2023-07-01", "Cloud", "2023-06-30", 80 * M, "80")
        b23, b24 = nx("B", "2024-07-01", "Cloud", "2023-06-30", (60 if resegment else 80) * M, "60" if resegment else "80"), nx("B", "2024-07-01", "Cloud", "2024-06-30", 90 * M, "90")
        ext = [a22, a23, b23, b24]
        facts = [fx("Cloud", "FY2022", 70 * M, [a22["extraction_id"]], "A"), fx("Cloud", "FY2023", b23["value"], [a23["extraction_id"], b23["extraction_id"]], "B"),
                 fx("Cloud", "FY2024", 90 * M, [b24["extraction_id"]], "B")]
        return facts, ext

    def run_rule(self, facts, ext, years=("FY2022", "FY2023", "FY2024")):
        return CHECKS["segment_basis_mixed"](Context(values=[], extractions=[], facts=facts, note_extractions=ext, years=list(years)), {})

    def test_a_year_from_before_the_cutover_fires_once_keyed_by_the_cutover(self):
        facts, ext = self.series()
        s = ties.segment_basis(facts, ext)[0]
        self.assertEqual((s["cutover"]["accession"], s["mixed"]), ("B", ["FY2022"]))
        got = self.run_rule(facts, ext)
        self.assertEqual([(f.ticker, f.field, f.period, f.subject) for f in got], [("T", "segment_revenue", "FY2022", "B")])
        self.assertIn("has no FY2022 reading", got[0].message)
        self.assertIn("Cloud FY2023 80 → 60", got[0].message)

    def test_no_restated_figure_no_cutover_no_finding(self):
        facts, ext = self.series(resegment=False)
        self.assertIsNone(ties.segment_basis(facts, ext)[0]["cutover"])
        self.assertEqual(self.run_rule(facts, ext), [])

    def test_a_year_outside_the_release_years_does_not_fire(self):
        facts, ext = self.series()
        self.assertEqual(self.run_rule(facts, ext, years=("FY2023", "FY2024")), [])

    def test_nothing_is_changed(self):
        facts, ext = self.series()
        before = [dict(f) for f in facts]
        self.run_rule(facts, ext)
        self.assertEqual(facts, before)

    @unittest.skipUnless(HAS_DB, "no data/ledger.duckdb")
    def test_real_proven_six_only_msft_fy2022_and_on_no_explained_row(self):
        """On the proven six the rule fires once: MSFT segment revenue FY2022, cutover the FY2025 10-K. The facts it names
        are checked by XBRL and no resolution explains them, so the new finding lands on no already-explained row."""
        import duckdb
        from ledger.cli.rules import context
        from ledger.checks.rules import load
        from ledger.core.config import PROVEN
        from ledger.review import resolutions
        rules = load()
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        try:
            ctx = context(con, list(PROVEN), rules)
        finally:
            con.close()
        got = CHECKS["segment_basis_mixed"](ctx, next(r for r in rules if r["id"] == "segment_basis_mixed")["params"])
        self.assertEqual([(f.ticker, f.field, f.period, f.subject) for f in got], [("MSFT", "segment_revenue", "FY2022", MID)])
        idx = resolutions.by_row()
        for f in ctx.facts:
            if f["ticker"] == "MSFT" and f["field"] == "segment_revenue" and f["period"] == "FY2022":
                self.assertIsNone(resolutions.resolution_of(idx, "facts", "MSFT", f["field"], f["dimension"] or "", f["period"]))
        self.assertIsNone(resolutions.resolution_of(idx, "findings", "MSFT", "segment_revenue", MID, "FY2022", "segment_basis_mixed"))


if __name__ == "__main__":
    unittest.main()
