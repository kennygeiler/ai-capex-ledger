"""The trust findings closed on branch `trust` (claims/findings.jsonl F11, F14, F16, F18, F20, F21): each class holds
the tests that fail on the code before its fix."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger.core import store

PERSON = "Kenny Geiler"
AGENT = "Claude Code, for Kenny Geiler to confirm"  # the 12 accepts on blocks in decisions/decisions.jsonl are by this name


def _exc(eid="xbrl_reconcile|ZZB|revenue|FY2024|None", sev="block", h="h1", ticker="ZZB", field="revenue", period="FY2024"):
    return {"exception_id": eid, "rule_id": eid.split("|")[0], "severity": sev, "ticker": ticker, "field": field, "period": period, "subject": None, "message": "m", "input_hash": h}


def _dec(eid, by, kind="accept", h="h1", value=None, at="2026-11-01T00:00:00+00:00", **kw):
    return {"decision_id": by[:3] + at, "exception_id": eid, "kind": kind, "value": value, "reason": kw.pop("reason", "a reason"), "reviewer": by,
            "decided_at": at, "input_hash": h, "supersedes": None, **kw}


class ProvenMeansTheProvenSet(unittest.TestCase):
    """F11: a company outside config.PROVEN with nothing open read Proven on its trail beside "Not in scope"."""

    def _con(self, ticker):
        con = store.init(":memory:")
        con.execute("insert into documents (accession, ticker, cik, form, period, filed, url, sha256, bytes, parser_version, table_count, tables_path, income_tables, cash_flow_tables) "
                    "values (?, ?, 1, '10-K', '2024-12-31', '2025-02-01', 'u', 's', 1, 'p', 40, 't', 't1', 't2')",
                    [f"{ticker}-1", ticker])
        return con

    def test_nothing_open_outside_the_proven_set_is_not_proven(self):
        from ledger.checks import proof
        fake = [{"ticker": "ZZOUT", "name": "Outside Co"}]
        con = self._con("ZZOUT")
        with mock.patch.object(proof, "tracked", return_value=fake), mock.patch.object(proof, "asset_types", return_value={}), mock.patch.object(proof, "decisions", return_value=[]):
            co = proof.company(con, "ZZOUT", idx={}, defs={}, rset=([], None))
            self.assertEqual(co["open"], 0)
            self.assertFalse(co["in_proven_set"])
            self.assertFalse(co["proven"])  # the old code said True: open == 0 alone
            with mock.patch.object(proof, "PROVEN", ["ZZOUT"]):
                self.assertTrue(proof.company(con, "ZZOUT", idx={}, defs={}, rset=([], None))["proven"])  # in the set, nothing open: Proven


class DecisionAuthors(unittest.TestCase):
    """F14: a decision by an agent or "to confirm" closed a block finding; now it is Proposed until a person decides."""

    def setUp(self):
        from ledger.review import review
        self.review = review
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        p = mock.patch.object(review, "LOG", self.tmp / "decisions.jsonl")
        p.start()
        self.addCleanup(p.stop)

    def test_a_run_decision_never_closes_a_block_and_is_proposed(self):
        e = _exc()
        ds = [_dec(e["exception_id"], AGENT)]
        self.assertEqual([x["exception_id"] for x in self.review.open_items([e], ds)], [e["exception_id"]])  # still open: G4 fails on it
        self.assertEqual([(x["exception_id"], x["decision"]["reviewer"]) for x in self.review.proposed([e], ds)], [(e["exception_id"], AGENT)])
        self.assertEqual(self.review.open_items([e], [_dec(e["exception_id"], PERSON)]), [])  # a person's decision closes it
        self.assertEqual(self.review.proposed([e], [_dec(e["exception_id"], PERSON)]), [])
        self.assertEqual(self.review.open_items([e], [_dec(e["exception_id"], PERSON, author_kind="run")]), [e])  # author_kind decides when present
        self.assertEqual(self.review.open_items([e], [_dec(e["exception_id"], PERSON, reason="accepted, to confirm")]), [e])  # the old rule's words

    def test_a_run_decision_on_a_warning_still_closes_it(self):
        w = _exc(sev="warn")
        self.assertEqual(self.review.open_items([w], [_dec(w["exception_id"], AGENT)]), [])
        self.assertEqual(self.review.proposed([w], [_dec(w["exception_id"], AGENT)]), [])

    def test_a_run_decision_never_supersedes_a_persons_on_the_same_input(self):
        e = _exc()
        ds = [_dec(e["exception_id"], PERSON, kind="reject"), _dec(e["exception_id"], AGENT, kind="accept", at="2026-11-02T00:00:00+00:00")]
        self.assertEqual(self.review.latest(ds)[e["exception_id"]]["reviewer"], PERSON)
        self.assertEqual(self.review.open_items([e], ds), [])

    def test_a_run_override_on_a_block_changes_no_released_value(self):
        e = _exc()
        v = {"ticker": "ZZB", "field": "revenue", "period": "FY2024", "value": 5}
        self.assertEqual(self.review.apply([v], [e], [_dec(e["exception_id"], AGENT, kind="override", value=9)])[0]["value"], 5)
        self.assertEqual(self.review.apply([v], [e], [_dec(e["exception_id"], PERSON, kind="override", value=9)])[0]["value"], 9)

    def test_every_new_decision_records_its_author_and_kind(self):
        e = _exc()
        with self.assertRaises(ValueError):
            self.review.decide(e, "accept", "why", "")  # no author
        with self.assertRaises(ValueError):
            self.review.decide(e, "accept", "why", "Somebody Else")  # a person's decision by a name off config.PEOPLE
        self.assertFalse(self.review.LOG.exists())
        d = self.review.decide(e, "accept", "why", PERSON)
        r = self.review.decide(e, "accept", "why", "mapper agent", author_kind="run")
        lines = [json.loads(l) for l in self.review.LOG.read_text().splitlines()]
        self.assertEqual([(l["reviewer"], l["author_kind"]) for l in lines], [(PERSON, "person"), ("mapper agent", "run")])
        self.assertEqual((d["author_kind"], r["author_kind"]), ("person", "run"))
        self.assertEqual(self.review.open_items([e], self.review.decisions()), [])  # the person's stands; the run's is not newer than it

    def test_the_cli_records_a_person_or_a_run(self):
        from ledger.cli import review as cli
        e = _exc()
        con = store.init(":memory:")
        store.write(con, "exceptions", [e])
        with mock.patch.object(cli.store, "init", return_value=con), mock.patch.object(cli, "decide", wraps=self.review.decide) as dec:
            self.assertEqual(cli.main(["decide", e["exception_id"], "accept", "--reason", "r", "--by", "Somebody Else", "--ticker", "ZZB"]), 1)
            self.assertEqual(cli.main(["decide", e["exception_id"], "accept", "--reason", "r", "--by", "an agent", "--run", "--ticker", "ZZB"]), 0)
        self.assertEqual(dec.call_args.kwargs["author_kind"], "run")
        self.assertEqual([json.loads(l)["author_kind"] for l in self.review.LOG.read_text().splitlines()], ["run"])

    def test_g4_and_g6_both_name_a_proposed_block(self):
        from ledger.release.release import gates
        e = _exc()
        ds = [_dec(e["exception_id"], AGENT)]
        g = gates([], self.review.open_items([e], ds), {"values": []}, tickers=["ZZB"], proposed=self.review.proposed([e], ds))
        self.assertEqual(g["G4"]["ZZB"], [e["exception_id"]])
        self.assertEqual(g["G6"]["ZZB"], [f"decisions|ZZB|{e['exception_id']}"])
        g = gates([], self.review.open_items([e], [_dec(e["exception_id"], PERSON)]), {"values": []}, tickers=["ZZB"], proposed=[])
        self.assertEqual((g["G4"]["ZZB"], g["G6"]["ZZB"]), ([], []))

    def test_proof_and_reconcile_read_it_proposed(self):
        from ledger.checks import proof
        from ledger.core.states import row
        from ledger.review import workbench
        from ledger.web import cards
        e = _exc()
        con = store.init(":memory:")
        store.write(con, "exceptions", [e])
        fake = [{"ticker": "ZZB", "name": "Block Co"}]
        with mock.patch.object(proof, "tracked", return_value=fake), mock.patch.object(proof, "asset_types", return_value={}), \
                mock.patch.object(proof, "decisions", return_value=[_dec(e["exception_id"], AGENT)]):
            co = proof.company(con, "ZZB", idx={}, defs={}, rset=([], None))
        it = co["stages"]["release"]["all"][0]
        self.assertEqual(row(it["state"], it["by"]), "wait")  # Proposed, not Blocks release, and never gone (the old code dropped it)
        self.assertEqual(cards._words(it, "", {})["text"], "Proposed decision. Review in Reconcile.")
        q = {"kind": "blocked", "ticker": "ZZB", "detail": {"rule": "xbrl_reconcile", "message": "m"}, "resolution": None, "proposed": {"kind": "accept", "reviewer": AGENT}}
        st = workbench._state(con, q, {})
        self.assertEqual(row(st["state"], st["by"]), "wait")
        st = workbench._state(con, {**q, "proposed": None}, {})
        self.assertEqual(row(st["state"], st["by"]), "blocked")


class EvidenceOnTheChecklist(unittest.TestCase):
    """F16: the walk that every verified or explained row names a record on file ran only in a test on frozen fixtures."""

    def test_a_dangling_record_is_a_red_required_line(self):
        from ledger.release import checklist
        gap = {"ticker": "MSFT", "stage": "values", "what": "capex FY2024", "state": "explained", "by": "resolution:gone", "gap": "no such resolution"}
        with mock.patch.object(checklist.proof, "unevidenced", return_value=[gap]) as u:
            l = checklist.evidence_line(None, {"proven": []})
        u.assert_called_once()
        self.assertEqual((l["id"], l["required"], l["state"], l["count"], l["link"]), ("evidenced", True, "fail", 1, "proof/MSFT"))
        self.assertEqual(l["detail"][0]["gap"], "no such resolution")
        with mock.patch.object(checklist.proof, "unevidenced", return_value=[]):
            self.assertEqual(checklist.evidence_line(None, {"proven": []})["state"], "pass")
        with mock.patch.object(checklist.proof, "unevidenced", side_effect=RuntimeError("boom")):
            self.assertEqual(checklist.evidence_line(None, {"proven": []})["state"], "fail")  # a walk that cannot run never passes

    @unittest.skipUnless(store.DEFAULT_DB.exists() and not __import__("os").environ.get("LEDGER_SKIP_DB"), "no data/ledger.duckdb")
    def test_the_live_checklist_carries_the_line_and_the_six_read_zero(self):
        from ledger.release import checklist
        from ledger.web import app
        con = app._con()
        try:
            lines = {l["id"]: l for l in checklist.checklist(con)["lines"]}
        finally:
            con.close()
        self.assertTrue(lines["evidenced"]["required"])
        self.assertEqual((lines["evidenced"]["state"], lines["evidenced"]["count"]), ("pass", 0), lines["evidenced"]["detail"][:3])


class EveryWriteNamesAPerson(unittest.TestCase):
    """F18: the signer box defaulted to Kenny Geiler; agent changes and the command-line signature took any name."""

    def test_the_page_has_no_default_signer(self):
        js = (store.ROOT / "ledger" / "web" / "pages" / "_shared.js").read_text()
        self.assertNotIn("'Kenny Geiler'", js)
        self.assertIn("let me = '';", js)
        self.assertNotIn('"Kenny Geiler")', (store.ROOT / "ledger" / "cli" / "report_template.html").read_text())

    def test_agent_changes_refuse_a_name_off_the_people_list(self):
        from ledger.extract import agents
        with mock.patch.object(agents, "_save") as save, mock.patch.object(agents, "PROMPTS", Path(tempfile.mkdtemp())):
            for name in ("", "Somebody Else", "Claude Code"):
                with self.assertRaises(ValueError):
                    agents.save_prompt("reader", "# x", name, "why")
                with self.assertRaises(ValueError):
                    agents.use_prompt("reader", "statements@v1", name)
                with self.assertRaises(ValueError):
                    agents.set_model("reader", "claude-opus-5-5", name)
            save.assert_not_called()

    def test_the_command_line_signature_checks_the_people_list(self):
        from ledger.cli import signoff
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        with mock.patch.object(signoff, "RELEASES", tmp):
            with self.assertRaisesRegex(ValueError, "config.PEOPLE"):
                signoff.sign("v9.9.0", "Somebody Else")
            self.assertEqual(signoff.main(["v9.9.0", "--by", "Claude Code"]), 1)

    def test_every_write_route_is_400_for_a_name_off_the_list_and_writes_nothing(self):
        from http.server import ThreadingHTTPServer
        import threading
        from urllib import error, request
        from ledger.web import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        base = f"http://127.0.0.1:{srv.server_address[1]}"

        def post(path, body):
            req = request.Request(base + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
            try:
                with request.urlopen(req) as r:
                    return r.status
            except error.HTTPError as e:
                return e.code
        routes = {"/api/release/sign": {"version": "v9.9.0"}, "/api/resolve": {"key": "blocked|MSFT|capex|FY2024|||", "hash": "h", "state": "accept", "reason": "r"},
                  "/api/resolve/bulk": {"items": [{"key": "blocked|MSFT|capex|FY2024|||", "hash": "h"}], "state": "accept", "reason": "r"},
                  "/api/judgement": {"key": "blocked|MSFT|capex|FY2024|||", "as": "definition", "why": "w"},
                  "/api/mapping": {"ticker": "MSFT", "reported_name": "Land", "standard_type": "us-gaap:LandMember", "evidence": "e", "expected": None},
                  "/api/mapping/bulk": {"items": [{"ticker": "MSFT", "reported_name": "Land", "standard_type": "us-gaap:LandMember", "evidence": "e", "expected": None}]},
                  "/api/mapping/reject": {"ticker": "MSFT", "reported_name": "Land", "standard_type": "us-gaap:LandMember", "reason": "r"},
                  "/api/v1/views": {"view": {"name": "v", "list": "values"}}, "/api/v1/views/x/delete": {},
                  "/api/gold/verdict": {"ticker": "MSFT", "id": "x", "verdict": "right"},
                  "/api/agents/reader/prompt": {"text": "# x", "note": "n"}, "/api/agents/reader/use": {"version": "statements@v1"}, "/api/agents/reader/model": {"model": "claude-opus-5-5"}}
        from ledger.extract import agents
        from ledger.release import checklist
        from ledger.review import gold, judgement, mapper
        from ledger.web import views
        sinks = [mock.patch.object(resolutions_mod(), "_write"), mock.patch.object(agents, "_save"), mock.patch.object(views, "_save"), mock.patch.object(gold, "_write"),
                 mock.patch.object(mapper, "_append"), mock.patch.object(mapper, "_edit"), mock.patch.object(judgement, "write_definition"), mock.patch.object(judgement, "write_rule"),
                 mock.patch.object(checklist, "write"), mock.patch("ledger.cli.signoff.sign"), mock.patch.object(agents, "PROMPTS", Path(tempfile.mkdtemp())),
                 mock.patch.object(app, "_con", return_value=mock.MagicMock())]
        ms = [p.start() for p in sinks]
        for p in sinks:
            self.addCleanup(p.stop)
        for path, body in routes.items():
            for name in ("", "Somebody Else"):
                self.assertEqual(post(path, {**body, "by": name}), 400, (path, name))
        for m in ms[:10]:
            m.assert_not_called()


def resolutions_mod():
    from ledger.review import resolutions
    return resolutions




if __name__ == "__main__":
    unittest.main()
