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

from ledger import agent, store
from ledger.extract import make_task

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
        from ledger.proof import FAILURES
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
        from ledger.mapper import by_name, propose
        log = Path(tempfile.mkdtemp()) / "mapping_proposals.jsonl"
        self.addCleanup(shutil.rmtree, log.parent, True)
        propose(self.T, {"prompt_version": "mapper@v1", "proposals": [{"reported_name": self.N, "standard_type": "BuildingMember", "evidence": "Buildings", "confidence": "high", "reason": "r"}]}, {"model": "m"}, log)
        from ledger.mapper import load_proposals, _append
        _append({"kind": "rejected", "ticker": self.T, "reported_name": self.N, "standard_type": "BuildingMember", "by": "Kenny Geiler", "reason": "no", "at": "2026-11-02T00:00:00+00:00"}, log)
        self.assertIsNone(by_name(self.T, load_proposals(log))[self.N]["proposal"])
        # the delayed answer of a run started before the rejection lands now, proposing the same member
        propose(self.T, {"prompt_version": "mapper@v1", "proposals": [{"reported_name": self.N, "standard_type": "BuildingMember", "evidence": "Buildings", "confidence": "high", "reason": "r"}]}, {"model": "m"}, log)
        e = by_name(self.T, load_proposals(log))[self.N]
        self.assertIsNone(e["proposal"])
        self.assertEqual([r["standard_type"] for r in e["reproposed"]], ["BuildingMember"])
        self.assertEqual(e["rejected"], ["BuildingMember"])  # the rejected list stays visible beside it

    def test_a_live_proposal_survives_a_late_reproposal(self):
        from ledger.mapper import by_name
        rej = {"kind": "rejected", "ticker": self.T, "reported_name": self.N, "standard_type": "BuildingMember", "by": "Kenny Geiler", "at": "2"}
        e = by_name(self.T, [self._p("BuildingMember", "1"), rej, self._p("BuildingsAndImprovementsGrossMember", "3"), self._p("BuildingMember", "4")])[self.N]
        self.assertEqual(e["proposal"]["standard_type"], "BuildingsAndImprovementsGrossMember")
        self.assertEqual([r["at"] for r in e["reproposed"]], ["4"])  # the first proposal was the one rejected, not a re-proposal

    def test_a_proposal_after_a_persons_approval_changes_nothing(self):
        from ledger.mapper import by_name, propose
        ok = {"kind": "approved", "ticker": self.T, "reported_name": self.N, "standard_type": "LandMember", "evidence": "Buildings", "by": "Kenny Geiler", "at": "2026-11-02",
              "confirmed_by": "Kenny Geiler", "confirmed_at": "2026-11-02"}
        e = by_name(self.T, [self._p("BuildingMember", "1"), ok, self._p("BuildingMember", "3")])[self.N]
        self.assertIsNone(e["proposal"])
        self.assertEqual(e["approved"]["standard_type"], "LandMember")
        self.assertEqual([r["at"] for r in e["late"]], ["3"])
        # and a proposal only ever appends to the log: taxonomy/asset_types.yaml is written by approve alone
        import inspect
        from ledger import mapper
        self.assertNotIn("_edit(", inspect.getsource(mapper.propose))


if __name__ == "__main__":
    unittest.main()
