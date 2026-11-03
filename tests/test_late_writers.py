"""T100: a late writer never overwrites a newer state. (1) A loader refuses an agent output that answered an older task
(its `_run.task_sha` is not the current task's). (2) A mapper proposal of a member a person rejected is never current,
and one that arrives after a person confirmed the entry changes nothing. (3) A run line never supersedes a person's
resolution: tests/test_resolutions.py, Authors.test_a_run_line_never_supersedes_a_person_line."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger.extract import agent
from ledger.core import store
from ledger.extract.extract import make_task

from tests.test_extract import ACCN, parsed, value


class StaleOutput(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        (self.dir / "outputs").mkdir()
        self.db = self.dir / "ledger.duckdb"

    def _doc(self, p):
        tp = self.dir / "tables.json"
        tp.write_text(json.dumps(p))
        con = store.init(self.db)
        con.execute("DELETE FROM documents")
        store.write(con, "documents", [{"accession": ACCN, "ticker": "NVDA", "cik": 1045810, "form": "10-K", "period": "2026-07-26", "filed": "2026-08-27",
                                        "url": "https://www.sec.gov/x", "sha256": "0" * 64, "bytes": 1, "parser_version": "t", "table_count": 0, "tables_path": str(tp)}])
        con.close()

    def _load(self):
        from ledger.cli import extract as cli
        with mock.patch.object(cli, "OUTPUTS", self.dir / "outputs"), mock.patch.object(cli, "report_period_ends", lambda t: []):
            cli.main(["--ticker", "NVDA", "--load", "--db", str(self.db)])
        con = store.init(self.db)
        try:
            return (con.execute("select count(*) from extractions").fetchone()[0],
                    [r[0] for r in con.execute("select message from exceptions where rule_id = 'extraction_failed'").fetchall()])
        finally:
            con.close()

    def test_stale_names_the_mismatch_and_passes_an_unfingerprinted_output(self):
        self.assertIsNone(agent.stale({"_run": {"task_sha": agent.task_sha("task")}}, "task"))
        self.assertIn("stale output: answered an older task", agent.stale({"_run": {"task_sha": agent.task_sha("task")}}, "task, repacked"))
        self.assertIsNone(agent.stale({"values": []}, "task"))  # written by hand before headless runs: no fingerprint to compare
        self.assertIsNone(agent.stale({"_run": {"task_sha": "x"}}, None))  # the current task cannot be built: nothing to compare

    def test_repack_a_task_then_load_the_old_output_refused(self):
        """T100 done-when (1): the output answered the task as packed; the task is repacked (a statement re-located, as
        T65 did to AMZN's income table); the old output is refused and logged, never loaded."""
        p = parsed()
        p["tables"] = []
        self._doc(p)
        out = {"accession": ACCN, "prompt_version": "statements@v1", "values": [value()], "not_found": [], "_run": {"model": "m", "task_sha": agent.task_sha(make_task(p))}}
        (self.dir / "outputs" / f"{ACCN}.json").write_text(json.dumps(out))
        n, failed = self._load()
        self.assertEqual((n, failed), (1, []))  # the output answers the current task: loaded
        repacked = {**p, "statements": {**p["statements"], "cash_flow": []}}  # the cash-flow statement re-located: a new task
        self.assertNotEqual(make_task(repacked), make_task(p))
        self._doc(repacked)
        n, failed = self._load()
        self.assertEqual(n, 0)
        self.assertEqual(len(failed), 1)
        self.assertIn("stale output: answered an older task", failed[0])

    def test_the_notes_and_aispend_loaders_check_too(self):
        import inspect
        from ledger.cli import aispend, notes
        for m in (notes, aispend):
            src = inspect.getsource(m.main)
            i = src.index("agent.stale(")
            self.assertLess(src.index("validate_output(obj", i) - i, 300, m.__name__)  # in --load, refused just before the output is validated and read

    def test_rules_keeps_every_loader_failure(self):
        """A refused notes or AI-spend output is logged as its failure class; `ledger rules` used to delete every exception
        but extraction_failed, so the refusal vanished. It keeps all four (proof.FAILURES)."""
        from ledger.cli import rules
        from ledger.checks.proof import FAILURES
        con = store.init(self.db)
        store.write(con, "exceptions", [{"exception_id": f"{r}|x", "rule_id": r, "severity": "block", "ticker": "NVDA", "field": None, "period": None, "subject": "x",
                                          "message": "stale output: answered an older task", "input_hash": "h"} for r in FAILURES], replace=True)
        con.close()
        rules.main(["--ticker", "NVDA", "--db", str(self.db)])
        con = store.init(self.db)
        self.assertEqual(sorted(r[0] for r in con.execute("select rule_id from exceptions where subject = 'x'").fetchall()), sorted(FAILURES))
        con.close()


class LateProposal(unittest.TestCase):
    T, N = "MU", "Buildings"

    def _p(self, member, at):
        return {"kind": "proposed", "ticker": self.T, "reported_name": self.N, "standard_type": member, "evidence": "Buildings", "confidence": "high", "reason": "r", "at": at}

    def test_reject_a_mapping_then_a_delayed_proposal_of_the_same_member_is_not_current(self):
        """T100 done-when (2)."""
        from ledger.review.mapper import by_name, propose
        log = Path(tempfile.mkdtemp()) / "mapping_proposals.jsonl"
        self.addCleanup(shutil.rmtree, log.parent, True)
        propose(self.T, {"prompt_version": "mapper@v1", "proposals": [{"reported_name": self.N, "standard_type": "BuildingMember", "evidence": "Buildings", "confidence": "high", "reason": "r"}]}, {"model": "m"}, log)
        from ledger.review.mapper import load_proposals, _append
        _append({"kind": "rejected", "ticker": self.T, "reported_name": self.N, "standard_type": "BuildingMember", "by": "Kenny Geiler", "reason": "no", "at": "2026-11-02T00:00:00+00:00"}, log)
        self.assertIsNone(by_name(self.T, load_proposals(log))[self.N]["proposal"])
        # the delayed answer of a run started before the rejection lands now, proposing the same member
        propose(self.T, {"prompt_version": "mapper@v1", "proposals": [{"reported_name": self.N, "standard_type": "BuildingMember", "evidence": "Buildings", "confidence": "high", "reason": "r"}]}, {"model": "m"}, log)
        e = by_name(self.T, load_proposals(log))[self.N]
        self.assertIsNone(e["proposal"])
        self.assertEqual([r["standard_type"] for r in e["reproposed"]], ["BuildingMember"])
        self.assertEqual(e["rejected"], ["BuildingMember"])  # the rejected list stays visible beside it

    def test_a_live_proposal_survives_a_late_reproposal(self):
        from ledger.review.mapper import by_name
        rej = {"kind": "rejected", "ticker": self.T, "reported_name": self.N, "standard_type": "BuildingMember", "by": "Kenny Geiler", "at": "2"}
        e = by_name(self.T, [self._p("BuildingMember", "1"), rej, self._p("BuildingsAndImprovementsGrossMember", "3"), self._p("BuildingMember", "4")])[self.N]
        self.assertEqual(e["proposal"]["standard_type"], "BuildingsAndImprovementsGrossMember")
        self.assertEqual([r["at"] for r in e["reproposed"]], ["4"])  # the first proposal was the one rejected, not a re-proposal

    def test_a_proposal_after_a_persons_approval_changes_nothing(self):
        from ledger.review.mapper import by_name, propose
        ok = {"kind": "approved", "ticker": self.T, "reported_name": self.N, "standard_type": "LandMember", "evidence": "Buildings", "by": "Kenny Geiler", "at": "2026-11-02",
              "confirmed_by": "Kenny Geiler", "confirmed_at": "2026-11-02"}
        e = by_name(self.T, [self._p("BuildingMember", "1"), ok, self._p("BuildingMember", "3")])[self.N]
        self.assertIsNone(e["proposal"])
        self.assertEqual(e["approved"]["standard_type"], "LandMember")
        self.assertEqual([r["at"] for r in e["late"]], ["3"])
        # and a proposal only ever appends to the log: taxonomy/asset_types.yaml is written by approve alone
        import inspect
        from ledger.review import mapper
        self.assertNotIn("_edit(", inspect.getsource(mapper.propose))


class RoundTrip(unittest.TestCase):
    """Review: pack, run (the agent mocked), load: a fresh task is never refused; a stale one is, and the failure stays
    through `ledger rules` until a re-run clears it."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        for d in ("tasks", "outputs"):
            (self.dir / d).mkdir()
        self.db = self.dir / "ledger.duckdb"

    def _con(self):
        return store.init(self.db)

    def _failures(self, rule):
        con = self._con()
        try:
            return [r[0] for r in con.execute("select message from exceptions where rule_id = ?", [rule]).fetchall()]
        finally:
            con.close()

    def _notes_doc(self):
        from ledger.ingest.statements import assemble, locate
        from ledger.ingest.tables import document_units, parse_tables
        from tests.test_extract import FIX
        doc = FIX.read_bytes()
        t = parse_tables(doc)
        loc, units = locate(t), document_units(doc)
        p = {"accession": ACCN, "ticker": "NVDA", "form": "10-K", "period": "2026-07-26", "tables": t,
             "statements": {k: assemble(t, loc[k], units) for k in ("income", "cash_flow")}}
        tp = self.dir / "tables.json"
        tp.write_text(json.dumps(p))
        con = self._con()
        con.execute("DELETE FROM documents")
        store.write(con, "documents", [{"accession": ACCN, "ticker": "NVDA", "cik": 1045810, "form": "10-K", "period": "2026-07-26", "filed": "2026-08-27",
                                        "url": "https://www.sec.gov/x", "sha256": "0" * 64, "bytes": 1, "parser_version": "t", "table_count": len(t), "tables_path": str(tp)}])
        con.close()
        return p, tp

    def _notes(self, *flags, answer=None):
        from ledger.extract import notes
        from ledger.cli import notes as cli
        calls = []

        def ask(agent_id, task, check):
            calls.append(task)
            obj = {"accession": ACCN, "prompt_version": notes.prompt_version(), "values": [], "not_found": [], "_run": {"model": "m", "seconds": 0.0, "attempts": 1}}
            check(obj)
            return obj
        with mock.patch.object(notes, "TASKS", self.dir / "tasks"), mock.patch.object(cli, "OUTPUTS", self.dir / "outputs"), \
                mock.patch.object(cli.agent, "ask", ask), mock.patch.object(cli, "fiscal_year_end", lambda t: "0126"), mock.patch.object(cli, "instance_facts", lambda c, a: {}):
            cli.main(["--ticker", "NVDA", *flags, "--db", str(self.db)])
        return calls

    def test_notes_pack_run_load_is_never_refused_and_a_rerun_clears_a_stale_failure(self):
        from ledger.cli import rules
        p, tp = self._notes_doc()
        self.assertEqual(len(self._notes("--run")), 1)  # packed, then asked once
        self._notes("--load")
        self.assertEqual(self._failures("note_extraction_failed"), [])  # the fingerprint --run wrote is the one --load rebuilds
        self.assertEqual(self._notes("--run"), [])  # nothing changed: nothing re-asked
        # repack: a statement re-located, so the note candidates change; the old answer is stale
        p["statements"]["income"] = []
        tp.write_text(json.dumps(p))
        self._notes("--load")
        self.assertEqual(len(self._failures("note_extraction_failed")), 1)
        rules.main(["--ticker", "NVDA", "--db", str(self.db)])
        self.assertIn("stale output", self._failures("note_extraction_failed")[0])  # rules keeps it
        self.assertEqual(len(self._notes("--run")), 1)  # --run re-asks exactly the stale one
        self._notes("--load")
        rules.main(["--ticker", "NVDA", "--db", str(self.db)])
        self.assertEqual(self._failures("note_extraction_failed"), [])  # the re-run cleared it, and rules does not bring it back

    def _texts(self, path):
        con = self._con()
        con.execute("DELETE FROM texts")
        store.write(con, "texts", [{"text_id": "NVDA|mdna|2026-01-25|abc", "ticker": "NVDA", "kind": "mdna", "accession": ACCN, "url": "https://www.sec.gov/x", "date": "2026-02-25",
                                    "period_end": "2026-01-25", "fiscal_year": 2026, "path": str(path), "sha256": "0" * 64, "chars": 1}])
        con.close()

    def _aispend(self, *flags):
        from ledger.extract import guidance
        from ledger.cli import aispend as cli
        calls = []

        def ask(agent_id, task, check):
            calls.append(task)
            obj = {"accession": "NVDA|mdna|2026-01-25|abc", "prompt_version": guidance.prompt_version(), "statements": [], "none_found": [{"field": "capex", "reason": "r"}],
                   "_run": {"model": "m", "seconds": 0.0, "attempts": 1}}
            check(obj)
            return obj
        with mock.patch.object(guidance, "TASKS", self.dir / "tasks"), mock.patch.object(cli, "OUTPUTS", self.dir / "outputs"), mock.patch.object(cli.agent, "ask", ask):
            cli.main(["--ticker", "NVDA", *flags, "--db", str(self.db)])
        return calls

    def test_aispend_pack_run_load_is_never_refused_and_a_missing_text_is_a_failure(self):
        text = self.dir / "mdna.txt"
        text.write_text("Item 7.\n\nWe increased capital expenditures to build data centers for AI and accelerated computing, and expect capital expenditures to grow next year.\n")
        self._texts(text)
        self.assertEqual(len(self._aispend("--run")), 1)
        self._aispend("--load")
        self.assertEqual(self._failures("ai_extraction_failed"), [])
        text.write_text(text.read_text() + "\nWe also spend on artificial intelligence research and development, with operating expenses up on AI headcount growth.\n")
        self._aispend("--load")
        self.assertIn("stale output", self._failures("ai_extraction_failed")[0])
        text.unlink()  # the text gone: the check cannot be made, and the load says so instead of trusting the task file
        self._aispend("--load")
        msg = self._failures("ai_extraction_failed")[0]
        self.assertIn("cannot rebuild the task", msg)
        self.assertIn(ACCN, msg)

    def test_extract_run_reasks_an_output_with_no_fingerprint(self):
        from ledger.extract import extract
        from ledger.cli import extract as cli
        p = parsed()
        p["tables"] = []
        tp = self.dir / "tables.json"
        tp.write_text(json.dumps(p))
        con = self._con()
        store.write(con, "documents", [{"accession": ACCN, "ticker": "NVDA", "cik": 1045810, "form": "10-K", "period": "2026-07-26", "filed": "2026-08-27",
                                        "url": "https://www.sec.gov/x", "sha256": "0" * 64, "bytes": 1, "parser_version": "t", "table_count": 0, "tables_path": str(tp)}])
        con.close()
        (self.dir / "outputs" / f"{ACCN}.json").write_text(json.dumps({"accession": ACCN, "prompt_version": "statements@v1", "values": [value()], "not_found": []}))  # by hand, no _run
        calls = []

        def ask(task, doc):
            calls.append(task)
            return {"accession": ACCN, "prompt_version": "statements@v1", "values": [value()], "not_found": [], "_run": {"model": "m", "seconds": 0.0, "attempts": 1}}
        with mock.patch.object(extract, "TASKS", self.dir / "tasks"), mock.patch.object(cli, "OUTPUTS", self.dir / "outputs"), mock.patch.object(cli.agent, "extract", ask), \
                mock.patch.object(store, "ROOT", self.dir):  # the CLI prints the task folder relative to the root
            cli.main(["--ticker", "NVDA", "--run", "--db", str(self.db)])
            self.assertEqual(len(calls), 1)
            self.assertEqual(json.loads((self.dir / "outputs" / f"{ACCN}.json").read_text())["_run"]["task_sha"], agent.task_sha(make_task(p)))
            cli.main(["--ticker", "NVDA", "--run", "--db", str(self.db)])
            self.assertEqual(len(calls), 1)  # now fingerprinted and current: not asked again

    def test_an_undone_approval_does_not_hide_later_proposals(self):
        from ledger.review.mapper import by_name
        ok = {"kind": "approved", "ticker": "MU", "reported_name": "Buildings", "standard_type": "LandMember", "by": "Kenny Geiler", "at": "2"}
        later = {"kind": "proposed", "ticker": "MU", "reported_name": "Buildings", "standard_type": "BuildingMember", "evidence": "Buildings", "confidence": "high", "reason": "r", "at": "3"}
        e = by_name("MU", [ok, later])["Buildings"]
        self.assertIsNone(e["proposal"])  # the approval stands: the late proposal changes nothing
        self.assertEqual([l["at"] for l in e["late"]], ["3"])
        e = by_name("MU", [ok, later], {"Buildings"})["Buildings"]  # the entry is no longer confirmed in the yaml: the approval was undone
        self.assertIsNone(e["approved"])
        self.assertEqual(e["proposal"]["standard_type"], "BuildingMember")
        import inspect
        from ledger.review import mapper
        self.assertIn("by_name(t, lines, set(names))", inspect.getsource(mapper.pending))  # pending passes its names: every one is unmapped or unconfirmed

if __name__ == "__main__":
    unittest.main()
