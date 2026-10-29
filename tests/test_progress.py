"""DATAHQ's add-a-company progress comes from the file `ledger run` writes after each step, not from parsing its log."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger import app, progress


class Job(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.job, self.file = self.dir / "current.json", self.dir / "progress.json"
        self.job.write_text(json.dumps({"ticker": "AMD", "log": str(self.dir / "AMD.log"), "started": "2026-10-28T10:00:00+00:00", "pid": 999999999}))
        self.patch = mock.patch.multiple(app, JOB=self.job, _proc=None)
        self.patch.start()
        self.patch2 = mock.patch.object(progress, "FILE", self.file)
        self.patch2.start()

    def tearDown(self):
        self.patch.stop()
        self.patch2.stop()
        shutil.rmtree(self.dir)

    def test_steps_come_from_the_progress_file(self):
        steps = [{"step": "ingest", "extra": [], "label": "x", "subject": "AMD", "started_at": "t", "seconds": 1.0, "code": 0, "summary": "5 filings found"}]
        progress.write("run-1", "AMD", ["AMD"], steps, running=False)
        j = app.job()
        self.assertEqual([s["state"] for s in j["steps"]], ["done"] + ["waiting"] * 15)
        self.assertEqual((j["steps"][0]["summary"], j["running"], j["exit"]), ("5 filings found", False, 0))

    def test_another_scope_is_not_this_job(self):
        progress.write("run-2", "NVDA", ["NVDA"], [{"step": "ingest", "extra": [], "label": "x", "subject": "NVDA", "started_at": "t", "seconds": 1.0, "code": 0, "summary": "s"}], running=True)
        j = app.job()
        self.assertEqual(([s["state"] for s in j["steps"]], j["exit"]), (["waiting"] * 16, None))

    def test_the_step_list_is_the_pipeline(self):
        self.assertEqual([s[0] for s in progress.STEPS], ["ingest", "extract", "extract", "reconcile", "texts", "aispend", "aispend", "notes", "notes", "attribution", "attribution", "eval", "rules", "faults", "evidence", "report"])


if __name__ == "__main__":
    unittest.main()
