"""The second flow batch (docs/ux-flow/report.md #6, #8, #10-#14; docs/ux-flow/verification-2.md): rule findings in
groups with a deliberate Save, the packet on Release, Proof with one job, the condensed trail, Docs from Start here, one
Verification filter on the Dataset, and the read-only copy's scope line."""
import json
import shutil
import unittest
from pathlib import Path

from tests.test_pages_js import PAGES, block, line, node


def _run(js: str, arg):
    return json.loads(node(js + "\nconst A = JSON.parse(process.argv[process.argv.length - 1]);\n", json.dumps(arg)) or "null")


def _call(prelude: str, expr: str, arg):
    return json.loads(node(prelude + "\nconst A = JSON.parse(process.argv[process.argv.length - 1]);\nprocess.stdout.write(JSON.stringify(" + expr + "));", json.dumps(arg)))


@unittest.skipUnless(shutil.which("node"), "no node")
class RuleFindingGroups(unittest.TestCase):
    """#6: rule findings grouped by company + field + check; no decision preselected; a prefilled reason for readings that
    differ where the dataset uses the newest filing; Fix says the item stays open; an "N left · Release" link."""

    PRE = "\n".join(line("reconcile.js", p) for p in ("const ruleGroupKey", "const ruleOrder", "const ruleGroups"))

    def test_rows_group_by_company_field_and_check(self):
        R = lambda t, f, c, p: {"cause": "finding_unconfirmed", "ticker": t, "field": f, "cause_label": c, "period": p}
        rows = [R("GOOGL", "segment_revenue", "Does not tie", "FY2024"), R("APLD", "segment_capex", "Does not tie", "FY2023"),
                R("GOOGL", "segment_revenue", "Does not tie", "FY2025"), R("APLD", "ppe_category", "Readings differ", "FY2024"),
                R("APLD", "segment_capex", "Does not tie", "FY2026")]
        got = _call(self.PRE, "ruleGroups([...A].sort(ruleOrder)).map((g) => [g.key, g.rows.map((r) => r.period)])", rows)
        self.assertEqual(got, [["APLD|ppe_category|Readings differ", ["FY2024"]], ["APLD|segment_capex|Does not tie", ["FY2026", "FY2023"]],
                               ["GOOGL|segment_revenue|Does not tie", ["FY2025", "FY2024"]]])
        self.assertIsNone(_call(self.PRE, "ruleGroupKey(A)", {"cause": "fact_differs", "ticker": "X"}))  # only rule findings group

    def test_a_decision_starts_unchosen_and_save_waits_for_one(self):
        st = lambda r: _call(line("reconcile.js", "const startState"), "startState(A)", r)
        self.assertIsNone(st(None))
        self.assertIsNone(st({"key": "k"}))  # before: 'accept'
        self.assertEqual(st({"resolution": {"state": "explain"}}), "explain")  # a saved row reopens on its own decision
        page = (PAGES / "reconcile.js").read_text()
        self.assertIn("let state = startState(r);", page)
        self.assertIn("disabled: !state, title: state ? null : 'Choose a decision first'", page)
        self.assertIn("finally { save.disabled = !state; }", page)

    def test_fix_says_the_item_stays_open(self):
        eff = _call(line("reconcile.js", "const RES_EFFECT"), "A.map((s) => RES_EFFECT[s])", ["fix", "accept"])
        self.assertEqual(eff, ["Item stays open until the next run", "Closes the item"])
        self.assertIn("effect.textContent = RES_EFFECT[s]", (PAGES / "reconcile.js").read_text())

    def test_readings_differ_prefills_the_reason_when_the_newest_reading_is_used(self):
        pre = line("reconcile.js", "const laterReading") + "\n" + line("reconcile.js", "const prefillReason")
        f = lambda eid, filed: {"extraction_id": eid, "form": "10-K", "filed": filed}
        rs = lambda used: {"cause": "finding_unconfirmed", "evidence": {"restatement": {"used": used, "steps": [{"filings": [f("a", "2024-08-30")]}, {"filings": [f("b", "2025-07-30")]}]}}}
        self.assertEqual(_call(pre, "prefillReason(A)", [rs(f("b", "2025-07-30"))]), "Later filing’s reading used · 10-K 2025-07-30")
        self.assertEqual(_call(pre, "prefillReason(A)", [rs(f("b", "2025-07-30")), rs(f("b", "2025-07-30"))]), "Later filing’s reading used")
        self.assertEqual(_call(pre, "prefillReason(A)", [rs(f("a", "2024-08-30"))]), "")  # the dataset uses the older reading: nothing to prefill
        self.assertEqual(_call(pre, "prefillReason(A)", [rs(f("b", "2025-07-30")), {"cause": "finding_unconfirmed", "evidence": {}}]), "")  # a mixed batch
        self.assertEqual(_call(pre, "prefillReason(A)", [{"cause": "fact_differs", "evidence": rs(f("b", "x"))["evidence"]}]), "")

    def test_the_way_back_to_release(self):
        page = (PAGES / "reconcile.js").read_text()
        self.assertIn("`${int(openRows.length)} left · Release`", page)
        self.assertIn("status.replaceChildren(`Saved · ${int(left)} left · `, h('a', {href: '#release'}, 'Release'))", page)
        self.assertIn("tbody.append(ruleGroupRow(groupOf.get(r)))", page)
        self.assertIn("const cb = keys.length ? writes(h('input'", page)  # the group tick is a write control: hidden on the read-only copy


if __name__ == "__main__":
    unittest.main()
