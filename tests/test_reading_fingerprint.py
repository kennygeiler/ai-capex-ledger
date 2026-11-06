"""F25: project readings loaded even when they answered an older task, and a statement, note or AI reading with no task
fingerprint loaded as if current with nothing to say so. The projects loader now refuses a stale output, as the other
three do; an output with no fingerprint still loads (no extraction is re-run here) and reads open, "Reading not
fingerprinted", on Proof and Reconcile, counted the same on both, until `<step> --run` re-asks it."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from ledger.core import states, store
from ledger.extract import agent

TEXT = {"text_id": "ZZZ|mdna|2025-12-31|abc", "ticker": "NVDA", "kind": "mdna", "accession": None, "url": "https://example.com/x", "date": "2026-01-30",
        "period_end": "2025-12-31", "fiscal_year": 2025, "path": "data/text/x.txt", "sha256": "0" * 64, "chars": 10}


class ReadingState(unittest.TestCase):
    def test_the_three_states(self):
        self.assertEqual(agent.reading_state({}), "unfingerprinted")
        self.assertEqual(agent.reading_state({"_run": {"task_sha": agent.task_sha("task")}}, "task"), "current")
        self.assertEqual(agent.reading_state({"_run": {"task_sha": agent.task_sha("old task")}}, "task"), "stale")
        self.assertEqual(states.READING.absent, "unfingerprinted")
        self.assertEqual(states.word("reading", "unfingerprinted"), "Reading not fingerprinted")


class ProjectsLoad(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        (self.dir / "outputs").mkdir()
        (self.dir / "tasks").mkdir()
        self.db = self.dir / "ledger.duckdb"
        con = store.init(self.db)
        store.write(con, "texts", [TEXT])
        con.close()
        for name, sub in (("OUTPUTS", "outputs"), ("TASKS", "tasks")):
            m = mock.patch(f"ledger.cli.projects.{name}", self.dir / sub)
            m.start()
            self.addCleanup(m.stop)

    def _load(self, answered: str) -> list:
        from ledger.cli import projects
        (self.dir / "tasks" / f"{TEXT['text_id']}.md").write_text("the current task")
        obj = {"accession": TEXT["text_id"], "prompt_version": "projects@v1", "projects": [], "_run": {"task_sha": agent.task_sha(answered)}}
        (self.dir / "outputs" / f"{TEXT['text_id']}.json").write_text(json.dumps(obj))
        with mock.patch("ledger.cli.projects.validate_output"):
            projects.main(["--ticker", "NVDA", "--db", str(self.db), "--load"])
        con = duckdb.connect(str(self.db), read_only=True)
        try:
            return [r[0] for r in con.execute("select message from exceptions where rule_id = 'projects_failed'").fetchall()]
        finally:
            con.close()

    def test_a_project_reading_of_an_older_task_is_refused(self):
        self.assertEqual(self._load("the current task"), [])
        failed = self._load("an older task")
        self.assertEqual(len(failed), 1)
        self.assertIn("stale output: answered an older task", failed[0])


@unittest.skipUnless(store.DEFAULT_DB.exists(), "needs the working database")
class Unfingerprinted(unittest.TestCase):
    def setUp(self):
        self.con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        self.addCleanup(self.con.close)

    def test_an_unfingerprinted_reading_is_open_on_proof_and_reconcile_alike(self):
        from ledger.checks import proof
        from ledger.extract import extract as ex
        from ledger.review import workbench
        from ledger.web import app
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        acc = self.con.execute("select accession from documents where ticker = 'AMD' order by period desc limit 1").fetchone()[0]
        src = json.loads((ex.OUTPUTS / f"{acc}.json").read_text())
        self.assertTrue(src["_run"]["task_sha"])
        src["_run"].pop("task_sha")
        (d / f"{acc}.json").write_text(json.dumps(src))  # the same reading, its fingerprint gone
        app._FLOW.clear()
        self.addCleanup(app._FLOW.clear)
        with mock.patch.object(ex, "OUTPUTS", d):
            items = [i for i in proof.company(self.con, "AMD")["stages"]["ingest"]["all"] if i["by"] == "label:unfingerprinted"]
            rows = [r for r in workbench.items(self.con, app._flow("AMD"))["rows"] if r["cause"] == "reading_unfingerprinted"]
        self.assertEqual([(i["state"], i["what"]) for i in items], [("open", f"Statement reading {acc}: Reading not fingerprinted")])
        self.assertEqual([(r["state"], r["verification"], r["bulk"]) for r in rows], [("open", "bad", False)])  # Needs review; no decision closes it
        self.assertEqual(agent.unfingerprinted(self.con, ["AMD"]), [])  # the files on disk all carry one


if __name__ == "__main__":
    unittest.main()
