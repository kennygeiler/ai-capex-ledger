"""The flow simplifications (docs/ux-flow/report.md #2, #4, #5, STORY-027): one open count per company on every page,
the Release page that leads with what blocks signing, the category mapping queue, and Reconcile's rule findings."""
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger.core import store
from tests.test_pages_js import block, line, node

_PEOPLE = None


def setUpModule():  # T80: config.PEOPLE fails closed; these tests approve as a placeholder person, never a real confirmer
    global _PEOPLE
    from ledger.core import config
    _PEOPLE = list(config.PEOPLE)
    config.PEOPLE[:] = _PEOPLE + ["A Tester"]


def tearDownModule():
    from ledger.core import config
    config.PEOPLE[:] = _PEOPLE

REAL_DB = store.DEFAULT_DB.exists() and not os.environ.get("LEDGER_SKIP_DB")


def _ext(acc, filed, value, eid):
    return {"extraction_id": eid, "accession": acc, "filed": filed, "form": "10-K", "period": filed, "value": value, "scale": 1000, "cell_text": str(value // 1000)}


class StaleRulesTable(unittest.TestCase):
    """F-FL1: Proof's ladder read the readings live while Reconcile's queue read the `exceptions` table `ledger rules`
    last wrote. After a change to how readings are read (the comma fix), APLD had 4 facts whose readings differ on Proof
    and 2 rows on Reconcile: Release said Needs review 18, Reconcile 16. Both now read ties.differ_findings."""

    def test_one_finding_per_untagged_fact_whose_readings_differ(self):
        from ledger.checks import ties
        ext = [_ext("0000000001-24-000001", "2024-08-30", 9_552_000, "0000000001-24-000001|ppe_category|Networking, electrical, and software|2024-05-31"),
               _ext("0000000001-25-000002", "2025-07-30", 1_760_000, "0000000001-25-000002|ppe_category|Networking, electrical, and software|2024-05-31"),
               _ext("0000000001-25-000003", "2025-07-30", 500_000, "0000000001-25-000003|ppe_category|Land|2024-05-31")]
        facts = [{"ticker": "X", "field": "ppe_category", "dimension": "Networking, electrical, and software", "period": "FY2024", "label": "no_reference",
                  "extraction_ids": "0000000001-24-000001|ppe_category|Networking, electrical, and software|2024-05-31,0000000001-25-000002|ppe_category|Networking, electrical, and software|2024-05-31"},
                 {"ticker": "X", "field": "ppe_category", "dimension": "Land", "period": "FY2024", "label": "no_reference", "extraction_ids": "0000000001-25-000003|ppe_category|Land|2024-05-31"},
                 {"ticker": "X", "field": "ppe_category", "dimension": "Tagged", "period": "FY2024", "label": "agree", "extraction_ids": ""}]
        out = ties.differ_findings(facts, ext)
        self.assertEqual([(x["subject"], x["period"]) for x in out], [("Networking, electrical, and software", "FY2024")])  # a dimension with commas still reads both cells
        self.assertTrue(out[0]["message"].startswith("ppe_category Networking, electrical, and software FY2024: readings differ"))
        self.assertEqual(ties.differ_findings([], []), [])

    def test_the_rule_writes_what_the_function_finds(self):
        from ledger.checks import rules, ties
        ext = [_ext("0000000001-24-000001", "2024-08-30", 9_552_000, "0000000001-24-000001|f|D|e"), _ext("0000000001-25-000002", "2025-07-30", 1_760_000, "0000000001-25-000002|f|D|e")]
        facts = [{"ticker": "X", "field": "ppe_category", "dimension": "D", "period": "FY2024", "label": "no_reference", "extraction_ids": "0000000001-24-000001|f|D|e,0000000001-25-000002|f|D|e"}]
        ctx = rules.Context(values=[], extractions=[], facts=facts, note_extractions=ext)
        got = rules.CHECKS["readings_differ"](ctx, {})
        self.assertEqual([(f.ticker, f.message, f.field, f.period, f.subject) for f in got],
                         [(x["ticker"], x["message"], x["field"], x["period"], x["subject"]) for x in ties.differ_findings(facts, ext)])

    @unittest.skipUnless(REAL_DB, "no data/ledger.duckdb")
    def test_reconcile_lists_every_live_reading_that_differs_even_with_no_exception_row(self):
        from ledger.web import app, hq
        real = hq.snapshot

        def stale(*a, **k):  # the exceptions table as an old rules run left it: no readings_differ rows at all
            s = real(*a, **k)
            return {**s, "findings": [x for x in s["findings"] if x.get("rule") != "fact_readings_differ"]}
        with mock.patch.object(app, "snapshot", stale):
            flow = app._flow("all")
        con = app._con()
        try:
            from ledger.checks import ties
            live = ties.differ_findings(**(lambda d: {"facts": d["facts"], "extractions": d["extractions"]})(ties.load(con, flow["tickers"], [])))
        finally:
            con.close()
        got = sorted(q["key"] for q in flow["queue"] if (q.get("detail") or {}).get("rule") == "fact_readings_differ")
        from ledger.review import resolutions
        want = sorted(resolutions.key_for("finding_unconfirmed", x["ticker"], x["field"], x["period"], rule_id="fact_readings_differ", subject=x["subject"]) for x in live)
        self.assertEqual(got, want)



class OneNumber(unittest.TestCase):
    """F-FL2 (docs/ux-flow/report.md #4): GOOGL read 7 on Reconcile's header, 11 on the Proof board, 7 in the Release
    detail and 4 in the Release by-company table. One function counts the open buckets per company (states.buckets, fed
    by workbench.company_counts); every page says the buckets by their row word."""

    def test_buckets_count_each_company_with_its_zeros(self):
        from ledger.core.states import buckets
        got = buckets([("A", "bad"), ("A", "wait"), ("A", "wait"), ("A", "ok"), ("B", "info"), ("B", "blocked")])
        self.assertEqual(got, {"A": {"bad": 1, "wait": 2, "blocked": 0}, "B": {"bad": 0, "wait": 0, "blocked": 1}})
        self.assertEqual(buckets([]), {})
        self.assertEqual(buckets([("A", "unknown")]), {"A": {"bad": 1, "wait": 0, "blocked": 0}})  # Not checked is open work, never counted nowhere
        with self.assertRaises(ValueError):
            buckets([("A", "no such word")])

    def test_a_decision_key_that_does_not_parse_raises(self):
        from ledger.review.workbench import company_counts
        with self.assertRaises(ValueError):
            company_counts({"proven": []}, [{"key": "not a key"}])

    @unittest.skipUnless(REAL_DB, "no data/ledger.duckdb")
    def test_counts_read_their_inputs_once_per_stamp(self):
        from ledger.checks import proof
        from ledger.web import app
        app._COUNTS_IN.clear()
        con = app._con()
        try:
            b = proof.board(con)
            with mock.patch("ledger.release.taxonomy.unmapped", return_value=[]) as um:
                app.with_counts(con, b)
                app.with_counts(con, b)
            self.assertEqual(um.call_count, 1)
        finally:
            con.close()
            app._COUNTS_IN.clear()

    @unittest.skipUnless(REAL_DB, "no data/ledger.duckdb")
    def test_needs_review_names_each_unmapped_category_and_proposed_lists_each_item(self):
        from ledger.release import checklist
        from ledger.web import app
        con = app._con()
        try:
            with mock.patch.object(checklist.taxonomy, "unmapped", return_value=[{"ticker": "GOOGL", "reported_name": "A made-up category"}]):
                cl = checklist.checklist(con)
        finally:
            con.close()
        lines = {l["id"]: l for l in cl["lines"]}
        self.assertIn({"company": "GOOGL", "unmapped_category": "A made-up category", "link": "reconcile?cause=asset_types&scope=GOOGL"}, lines["open"]["detail"])
        g6 = lines["gate_G6"]["detail"]
        self.assertEqual(len(g6), lines["gate_G6"]["count"])
        self.assertTrue(all({"company", "key", "state", "reason", "link"} <= set(d) for d in g6))

    def test_company_counts_add_a_runs_decisions_and_categories_no_page_lists(self):
        from ledger.review.workbench import company_counts
        it = lambda state, by, name=None: {"state": state, "by": by, **({"name": name} if name else {})}
        board = {"proven": [{"ticker": "X", "stages": {"facts": {"all": [it("open", "rule:jump")]}, "mapping": {"all": [it("open", "label:to_confirm", "Land")]}}},
                            {"ticker": "Y", "stages": {"values": {"all": [it("checked", "xbrl")]}}}]}
        unc = [{"key": "finding_unconfirmed|Y|capex|FY2024||jump|"}]
        um = [{"ticker": "X", "reported_name": "Land"}, {"ticker": "X", "reported_name": "Servers"}]  # Land is on the board already
        self.assertEqual(company_counts(board, unc, um), {"X": {"bad": 2, "wait": 1, "blocked": 0}, "Y": {"bad": 0, "wait": 1, "blocked": 0}})

    @unittest.skipUnless(REAL_DB, "no data/ledger.duckdb")
    def test_proof_board_trail_reconcile_and_release_say_the_same_numbers_for_every_company(self):
        from ledger.checks import proof
        from ledger.core.config import SCOPE
        from ledger.release import checklist
        from ledger.review import workbench
        from ledger.web import app, cards
        con = app._con()
        try:
            board = {c["ticker"]: c["counts"] for c in app.with_counts(con, proof.board(con))["proven"]}
            trail = {t: app.with_counts(con, cards.add(con, proof.company(con, t)))["counts"] for t in SCOPE}
            rec_all = workbench.items(con, app._flow("all"))["by_company"]
            rec_head = {t: {b: workbench.items(con, app._flow(t))["by_state"].get(b, 0) for b in ("bad", "wait", "blocked")} for t in SCOPE}
            cl = checklist.checklist(con)
        finally:
            con.close()
        lines = {l["id"]: l for l in cl["lines"]}
        det = lambda lid, k: {d["company"]: d[k] for d in lines[lid]["detail"] if k in d}
        g6 = lambda t: sum(d["company"] == t for d in lines["gate_G6"]["detail"])  # one row per proposed item, each naming its company
        release = {t: {"bad": det("open", "needs_review").get(t, 0), "wait": g6(t), "blocked": det("blocked", "blocks_release").get(t, 0)} for t in SCOPE}
        self.assertEqual(sorted(board), sorted(SCOPE))
        for t in SCOPE:
            self.assertEqual(board[t], trail[t], t)
            self.assertEqual(board[t], rec_head[t], t)
            self.assertEqual(board[t], rec_all.get(t, {"bad": 0, "wait": 0, "blocked": 0}), t)
            self.assertEqual(board[t], release[t], t)
        self.assertEqual(sum(x["bad"] for x in board.values()), lines["open"]["count"])
        self.assertEqual(sum(x["wait"] for x in board.values()), lines["gate_G6"]["count"])

    def test_pages_say_buckets_not_a_to_review_total(self):
        pages = Path(store.ROOT) / "ledger" / "web" / "pages"
        self.assertIn("bucketLine(c.counts)", (pages / "proof.js").read_text())
        trail = (pages / "trail.js").read_text()
        self.assertIn("bucketLine(c.counts)", trail)
        self.assertIn("bucketLine(st.counts)", trail)
        for f in ("proof.js", "trail.js"):
            self.assertNotIn("to review`", (pages / f).read_text(), f)
        self.assertIn("...OPEN_BUCKETS.map((s, i) =>", (pages / "reconcile.js").read_text())

    @unittest.skipUnless(shutil.which("node"), "no node")
    def test_bucket_parts_leave_zeros_out_in_one_order(self):
        js = line("_shared.js", "const OPEN_BUCKETS") + "\n" + line("_shared.js", "const bucketParts") + \
            "\nprocess.stdout.write(JSON.stringify(bucketParts(JSON.parse(process.argv[process.argv.length - 1]))));"
        self.assertEqual(json.loads(node(js, json.dumps({"blocked": 1, "wait": 4, "bad": 7}))), [["bad", 7], ["wait", 4], ["blocked", 1]])
        self.assertEqual(json.loads(node(js, json.dumps({"bad": 0, "wait": 4, "blocked": 0}))), [["wait", 4]])


PATHS = re.compile(r"[\w.<>*-]+/[\w.<>*/-]+|\.(?:json|jsonl|yaml|md|csv|html)\b|`")


class ReleasePage(unittest.TestCase):
    """docs/ux-flow/report.md #2: the failing required lines lead; passing and informational lines fold under one row;
    every Details is one short product line with no file path; the gate card is gone; the packet files and the row diff
    appear once (in their lines' details)."""

    @unittest.skipUnless(REAL_DB, "no data/ledger.duckdb")
    def test_no_detail_names_a_file_or_a_command_in_backticks(self):
        from ledger.release import checklist
        from ledger.web import app
        con = app._con()
        try:
            cl = checklist.checklist(con)
        finally:
            con.close()
        for l in cl["lines"]:
            if l["id"] == "claims" and l["state"] == "fail":
                continue  # the register's own error text, when it cannot be read
            self.assertIsNone(PATHS.search(l["note"]), (l["id"], l["note"]))
            self.assertLess(len(l["note"]), 160, l["id"])

    def test_the_notes_without_a_database_are_product_copy(self):
        from ledger.release import checklist
        for note in [*checklist.GATE_NOTE.values(), checklist.tests_line(None)["note"], checklist.regression_line(None)["note"]]:
            self.assertIsNone(PATHS.search(note), note)

    @unittest.skipUnless(shutil.which("node"), "no node")
    def test_failing_lines_first_and_the_rest_folded_under_one_row(self):
        js = line("release.js", "const LINE_ORDER") + "\n" + line("release.js", "const splitLines") + "\n" + line("release.js", "const passSummary") + """
const L = JSON.parse(process.argv[process.argv.length - 1]);
const {act, rest} = splitLines(L);
process.stdout.write(JSON.stringify({act: act.map((l) => l.id), rest: rest.map((l) => l.id), sum: passSummary(rest)}));"""
        lines = [{"id": "g1", "state": "pass"}, {"id": "open", "state": "fail"}, {"id": "diff", "state": "info"}, {"id": "tests", "state": "stale"},
                 {"id": "hand", "state": "fail"}, {"id": "packet", "state": "pass"}, {"id": "reg", "state": "not_run"}]
        got = json.loads(node(js, json.dumps(lines)))
        self.assertEqual(got["act"], ["open", "hand", "tests", "reg"])
        self.assertEqual(got["rest"], ["g1", "packet", "diff"])
        self.assertEqual(got["sum"], "2 checks pass · 1 informational")

    @unittest.skipUnless(shutil.which("node"), "no node")
    def test_each_company_keeps_its_gate_counts_and_result(self):
        js = line("release.js", "const gateRows") + """
process.stdout.write(JSON.stringify(gateRows(JSON.parse(process.argv[process.argv.length - 1]))));"""
        cl = {"gates": {"table": {"G1": {"A": [], "B": ["x"]}, "G6": {"A": [], "B": ["k1", "k2"]}}}}
        self.assertEqual(json.loads(node(js, json.dumps(cl))), [{"company": "A", "G1": 0, "G6": 0, "result": "pass"}, {"company": "B", "G1": 1, "G6": 2, "result": "fail"}])
        page = (Path(store.ROOT) / "ledger" / "web" / "pages" / "release.js").read_text()
        self.assertIn("lines.querySelector('tbody').append(byCo);", page)  # inside the folded passing area

    def test_no_command_on_the_page(self):
        from ledger.release import checklist
        notes = [checklist.tests_line(None)["note"], checklist.regression_line(None)["note"],
                 checklist.tests_line({"ok": True, "count": 1, "git": "0ld0000", "at": "x", "dirty": False, "code": "c1"}, live={"head": "abc1234", "dirty": False, "code": "c2"})["note"],
                 checklist.doc_line(text="a", doc=Path("/nonexistent/CLAIMS.md"))["note"]]
        for n in notes:
            self.assertNotIn("ledger ", n, n)

    def test_no_gate_card_and_each_list_once(self):
        js = (Path(store.ROOT) / "ledger" / "web" / "pages" / "release.js").read_text()
        for gone in ("Release checks by company", "gatesTable(", "diffTable", "dtable(`Packet"):
            self.assertNotIn(gone, js)
        self.assertIn("{detail: (l) => (l.summary ? '' : l.id === 'regression' ? regressionDetail(golden) : lineDetail(l))}", js)  # the packet files and the diff live in their lines' details only; the regression line's detail is its steps and differences (flow-2 review 4)
        self.assertIn("button, status", js)  # Sign stays in the header


HEADER = """# us-gaap members used: TechnologyEquipmentMember, LandMember, ConstructionInProgressMember, MachineryAndEquipmentMember.

AMD:
  "Equipment": {standard_type: MachineryAndEquipmentMember, evidence: "equipment", by: Claude Fable 5.1, at: 2026-11-01}
  "Land": {standard_type: LandMember, evidence: "land", by: Claude Fable 5.1, at: 2026-11-01}
  "Building": {standard_type: TechnologyEquipmentMember, evidence: "building", by: Claude Fable 5.1, at: 2026-11-01}
"""


class MappingQueue(unittest.TestCase):
    """docs/ux-flow/report.md #5: "Approve all N" on Matches company tag writes each approval through mapper.approve with
    its `expected`, stops at the first refusal, and never changes a member; Choose another starts empty or on the
    company's own tag."""

    def setUp(self):
        from ledger.review import mapper
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "asset_types.yaml"
        self.path.write_text(HEADER)
        self.log = Path(self.tmp.name) / "proposals.jsonl"
        self.tc = mock.patch.object(mapper, "_to_confirm", side_effect=lambda con, t: [{"ticker": "AMD", "reported_name": n} for n in ("Equipment", "Land", "Building")] if t == "AMD" else [])
        self.tc.start()

    def tearDown(self):
        self.tc.stop()
        self.tmp.cleanup()

    def items(self, **stale):
        rows = [("Equipment", "MachineryAndEquipmentMember"), ("Land", "LandMember"), ("Building", "TechnologyEquipmentMember")]
        return [{"ticker": "AMD", "reported_name": n, "standard_type": m, "evidence": n.lower(), "expected": {"standard_type": m, "at": stale.get(n, "2026-11-01")}} for n, m in rows]

    def matched(self, *names):
        from ledger.review import mapper
        return mock.patch.object(mapper, "matched", return_value={("AMD", n) for n in names})

    def test_every_entry_confirmed_in_one_write_with_the_single_approve_checks(self):
        from ledger.review import mapper
        import yaml
        with self.matched("Equipment", "Land", "Building"), mock.patch.object(mapper, "_check_expected", wraps=mapper._check_expected) as ce:
            out = mapper.approve_many(self.items(), "A Tester", path=self.path, log=self.log, at="2026-11-05")
        self.assertEqual((out["approved"], [i["reported_name"] for i in out["items"]]), (3, ["Equipment", "Land", "Building"]))
        self.assertEqual([c.args[1] for c in ce.call_args_list], [i["expected"] for i in self.items()])  # each checked against what the page showed
        d = yaml.safe_load(self.path.read_text())["AMD"]
        self.assertEqual({n: (e["standard_type"], e.get("confirmed_by"), e["by"]) for n, e in d.items()},
                         {"Equipment": ("MachineryAndEquipmentMember", "A Tester", "Claude Fable 5.1"), "Land": ("LandMember", "A Tester", "Claude Fable 5.1"),
                          "Building": ("TechnologyEquipmentMember", "A Tester", "Claude Fable 5.1")})
        self.assertEqual([l["kind"] for l in mapper.load_proposals(self.log)], ["confirmed"] * 3)

    def test_a_stale_entry_refuses_the_batch_and_writes_nothing(self):
        from ledger.review import mapper
        with self.matched("Equipment", "Land", "Building"), self.assertRaises(mapper.Stale) as c:  # Land changed since the page loaded: 409 on the route
            mapper.approve_many(self.items(Land="2026-10-30"), "A Tester", path=self.path, log=self.log, at="2026-11-05")
        self.assertIn("Approved 0 of 3; nothing written", str(c.exception))
        self.assertEqual(self.path.read_text(), HEADER)

    def test_a_category_the_server_does_not_find_matching_refuses_the_batch(self):
        from ledger.review import mapper
        with self.matched("Equipment", "Building"), self.assertRaises(ValueError) as c:  # Land is Proposed on the server, whatever the page sent
            mapper.approve_many(self.items(), "A Tester", path=self.path, log=self.log)
        self.assertIn("not a category the company's own tag matches: AMD 'Land'", str(c.exception))
        self.assertEqual(self.path.read_text(), HEADER)

    def test_a_name_off_the_people_list_writes_nothing(self):
        from ledger.review import mapper
        with self.matched("Equipment", "Land", "Building"), self.assertRaises(ValueError):
            mapper.approve_many(self.items(), "Somebody Else", path=self.path, log=self.log)
        self.assertEqual(self.path.read_text(), HEADER)

    def test_a_bulk_never_changes_a_member_repeats_nothing_and_has_a_cap(self):
        from ledger.review import mapper
        items = self.items()
        items[1]["standard_type"] = "ConstructionInProgressMember"  # a different member than the page showed
        with self.matched("Equipment", "Land", "Building"):
            for bad in (items, [], self.items() + self.items()[:1], self.items() * 40):
                with self.assertRaises(ValueError):
                    mapper.approve_many(bad, "A Tester", path=self.path, log=self.log)
        self.assertEqual(self.path.read_text(), HEADER)

    def test_the_route_refuses_a_proposed_item_with_400_and_writes_nothing(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib import error, request
        from ledger.review import mapper
        from ledger.web import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        url = f"http://127.0.0.1:{srv.server_address[1]}/api/mapping/bulk"

        def post(body):
            req = request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
            try:
                with request.urlopen(req) as r:
                    return r.status, json.loads(r.read())
            except error.HTTPError as e:
                return e.code, json.loads(e.read())
        # the server's verdict: Equipment and Building match the company's tag; Land is still to confirm (Proposed)
        tc = lambda con, tickers, with_verified=False: [{"ticker": "AMD", "reported_name": n} for n in (("Equipment", "Land", "Building") if with_verified else ("Land",))]
        with mock.patch.object(mapper, "ASSET_TYPES", self.path), mock.patch.object(mapper, "PROPOSALS", self.log), mock.patch.object(mapper, "to_confirm", side_effect=tc), \
                mock.patch("ledger.web.app._con", return_value=mock.MagicMock()):
            code, d = post({"items": self.items(), "by": "A Tester"})
            self.assertEqual(code, 400)
            self.assertIn("AMD 'Land'", d["error"])
            self.assertEqual(self.path.read_text(), HEADER)  # zero bytes written
            self.assertFalse(self.log.exists())
            code, d = post({"items": [i for i in self.items() if i["reported_name"] != "Land"], "by": "A Tester"})
            self.assertEqual((code, d["approved"]), (200, 2))
            code, d = post({"items": [i for i in self.items() if i["reported_name"] == "Equipment"], "by": "A Tester"})  # the same again: already confirmed
            self.assertEqual(code, 400)  # already confirmed by a person: refused, as a single Approve refuses it
            self.assertIn("already mapped", d["error"])
    @unittest.skipUnless(shutil.which("node"), "no node")
    def test_choose_another_starts_empty_or_on_the_companys_tag(self):
        js = line("reconcile.js", "const bare") + "\n" + line("reconcile.js", "const chooseDefault") + """
const [tag, members] = JSON.parse(process.argv[process.argv.length - 1]);
process.stdout.write(JSON.stringify(chooseDefault(tag, members)));"""
        members = ["TechnologyEquipmentMember", "LandMember", "OtherCapitalizedPropertyPlantAndEquipmentMember"]
        pick = lambda tag: json.loads(node(js, json.dumps([tag, members])))
        self.assertEqual(pick(None), "")  # never the first option
        self.assertEqual(pick({"status": "same", "member": "us-gaap:LandMember"}), "")
        self.assertEqual(pick({"status": "differs", "member": "us-gaap:OtherCapitalizedPropertyPlantAndEquipmentMember"}), "OtherCapitalizedPropertyPlantAndEquipmentMember")
        self.assertEqual(pick({"status": "differs", "member": "us-gaap:NotOnTheListMember"}), "")
        page = (Path(store.ROOT) / "ledger" / "web" / "pages" / "reconcile.js").read_text()
        self.assertIn("h('option', {value: '', selected: !pre || null}, 'Choose a category')", page)
        self.assertIn("if (!select.value) { select.focus();", page)

    @unittest.skipUnless(shutil.which("node"), "no node")
    def test_approve_all_lists_only_matching_categories_with_what_the_page_showed(self):
        js = "\n".join(line("reconcile.js", p) for p in ("const isMatch", "const expectedOf", "const bulkApproveItems")) + """
process.stdout.write(JSON.stringify(bulkApproveItems(JSON.parse(process.argv[process.argv.length - 1]))));"""
        P = lambda m: {"standard_type": m, "evidence": "e", "at": "2026-11-01"}
        rows = [{"ticker": "AMD", "cause": "asset_types", "verification": "company", "evidence": {"reported_name": "Land", "mapping": "verified", "proposal": P("LandMember")}},
                {"ticker": "AMD", "cause": "asset_types", "verification": "wait", "evidence": {"reported_name": "CIP", "mapping": "to_confirm", "proposal": P("ConstructionInProgressMember")}},
                {"ticker": "AMD", "cause": "finding_unconfirmed", "verification": "bad", "evidence": {}}]
        self.assertEqual(json.loads(node(js, json.dumps(rows))), [{"ticker": "AMD", "reported_name": "Land", "standard_type": "LandMember", "evidence": "e", "expected": {"standard_type": "LandMember", "at": "2026-11-01"}}])

    def test_mapping_cards_draw_no_number_columns_and_one_action_set(self):
        page = (Path(store.ROOT) / "ledger" / "web" / "pages" / "reconcile.js").read_text()
        self.assertIn("assetCard ? h('th', {}, 'Proposed') : [h('th', {class: 'num'}, 'Dataset')", page)
        self.assertIn("'Category mapping · Proposed'", page)
        self.assertIn("'Category mapping · Matches company tag'", page)
        self.assertIn("acts(t, false)", page)  # the row's buttons hide while its card, with the same actions, is open


class RuleFindings(unittest.TestCase):
    """STORY-027: rule findings show their numbers in the columns; after a save the next row has focus; one Decision
    panel at a time."""

    def test_a_failing_tie_and_two_readings_carry_their_numbers(self):
        from ledger.review.workbench import _finding_numbers
        lad = {"groups": {"X|segment_revenue|FY2025|0000000001-26-000001": {"sum": 402_963, "total": 402_836}}}
        got = _finding_numbers({"rule": "segment_revenue_tie", "field": "segment_revenue", "period": "FY2025", "subject": "0000000001-26-000001"}, "X", lad, {})
        self.assertEqual((got["ours"], got["reference"], got["ours_label"], got["ref_label"]), (402_963, 402_836, "Sum of parts", "Reported total"))
        rec = {("X", "ppe_category", "Other", "FY2024"): {"used": {"extraction_id": "b", "value": 1_760, "form": "10-K", "filed": "2025-07-30"},
                                                         "steps": [{"filings": [{"extraction_id": "a", "value": 9_552, "form": "10-K", "filed": "2024-08-30"}]}, {"filings": [{"extraction_id": "b", "value": 1_760}]}]}}
        got = _finding_numbers({"rule": "fact_readings_differ", "field": "ppe_category", "period": "FY2024", "subject": "Other"}, "X", {}, rec)
        self.assertEqual((got["ours"], got["reference"], got["ours_label"], got["ref_label"]), (1_760, 9_552, "Used · 10-K 2025-07-30", "Other · 10-K 2024-08-30"))
        self.assertEqual(_finding_numbers({"rule": "segment_basis_mixed"}, "X", lad, rec), {})  # no numbers: nothing invented
        self.assertEqual(_finding_numbers({"rule": "segment_revenue_tie", "field": "f", "period": "p", "subject": "missing"}, "X", lad, {}), {})

    @unittest.skipUnless(REAL_DB, "no data/ledger.duckdb")
    def test_googl_segment_revenue_shows_the_127m_gap_in_its_row(self):
        from ledger.review import workbench
        from ledger.web import app
        con = app._con()
        try:
            rows = workbench.items(con, app._flow("GOOGL"))["rows"]
        finally:
            con.close()
        r = next(r for r in rows if r["cause"] == "finding_unconfirmed" and r["field"] == "segment_revenue" and r["period"] == "FY2025")
        self.assertEqual((r["ours"], r["reference"], r["delta"]), (402_963_000_000, 402_836_000_000, 127_000_000))
        self.assertTrue(all(r["delta"] is not None for r in rows if r["cause"] == "finding_unconfirmed" and r["cause_label"] in ("Does not tie to reported total", "Readings differ across filings")))

    @unittest.skipUnless(shutil.which("node"), "no node")
    def test_after_a_save_the_next_row_has_focus(self):
        js = line("reconcile.js", "const nextKey") + """
const [order, saved] = JSON.parse(process.argv[process.argv.length - 1]);
process.stdout.write(JSON.stringify(nextKey(order, saved)));"""
        nk = lambda o, s: json.loads(node(js, json.dumps([o, s])))
        self.assertEqual(nk(["a", "b", "c", "d"], ["b"]), "c")
        self.assertEqual(nk(["a", "b", "c", "d"], ["b", "c"]), "d")  # a bulk save: the row after the last saved
        self.assertEqual(nk(["a", "b", "c", "d"], ["d"]), "c")  # the last row: the one before it
        self.assertIsNone(nk(["a"], ["a"]))
        page = (Path(store.ROOT) / "ledger" / "web" / "pages" / "reconcile.js").read_text()
        self.assertIn("FOCUS_KEY = nextKey(trs.map((t) => t.r.key), items.map((x) => x.key))", page)

    def test_one_decision_panel_at_a_time(self):
        page = (Path(store.ROOT) / "ledger" / "web" / "pages" / "reconcile.js").read_text()
        self.assertIn("for (const o of trs) if (o !== t && o.detail) { o.detail.remove();", page)  # opening a row closes the others
        self.assertIn("wrap.querySelectorAll('.decision-panel').forEach((x) => { x.hidden = selected.size > 0; })", page)  # a selection's panel replaces the row's

    def test_filters_live_in_the_address_so_a_save_keeps_them(self):
        page = (Path(store.ROOT) / "ledger" / "web" / "pages" / "reconcile.js").read_text()
        self.assertIn("const setQ = (patch) => { const p = {scope, group, cause: fCause, layer: fLayer, field: fField", page)
        self.assertIn("setTimeout(route, 250)", page)  # a save re-renders from the same address: scope and field stay


if __name__ == "__main__":
    unittest.main()
