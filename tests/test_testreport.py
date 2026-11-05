"""`ledger test` writes reports/tests.json (ledger/release/testreport.py) and the Release checklist's "Test run" line reads it
(checklist.tests_line): the writer's shape on a synthetic result, and the line on a passing, failing, stale and
missing file. No database, no git: the sha is passed in."""
import json
import tempfile
import unittest
from pathlib import Path

from ledger.release import checklist, testreport


class _T:
    def __init__(self, id_):
        self._id = id_

    def id(self):
        return self._id


def _result(run=5, failures=(), errors=(), skipped=(), started=None, lines=None):
    r = unittest.TestResult()
    r.testsRun = run
    r.failures = [(_T(i), "Traceback\n  ...\nAssertionError: " + m) for i, m in failures]
    r.errors = [(_T(i), "Traceback\n  ...\nKeyError: " + m) for i, m in errors]
    r.skipped = [(_T(i), "skipped") for i in skipped]
    if started is not None:
        r.started = started
    if lines is not None:
        r.lines = lines
    return r


G = testreport.GOLDEN_TEST


class Writer(unittest.TestCase):
    def test_shape_on_a_passing_run_with_golden(self):
        rep = testreport.report(_result(run=5, started=["a", "b", G]), seconds=31.26, git=("abc1234", False))
        self.assertEqual(set(rep), {"ok", "count", "failures", "skipped", "skipped_ids", "golden", "at", "git", "dirty", "seconds"})
        self.assertEqual((rep["ok"], rep["count"], rep["failures"], rep["skipped"], rep["golden"], rep["git"], rep["dirty"], rep["seconds"]),
                         (True, 5, [], 0, True, "abc1234", False, 31.3))
        self.assertTrue(rep["at"].endswith("+00:00"))

    def test_golden_is_null_when_skipped_and_false_when_it_failed(self):
        skipped = testreport.report(_result(run=5, skipped=[G], started=["a", G]), git=(None, None))
        self.assertIsNone(skipped["golden"])
        self.assertEqual(skipped["skipped"], 1)
        self.assertIsNone(skipped["git"])
        failed = testreport.report(_result(run=5, failures=[(G, "differences: values")], started=["a", G]), git=("abc1234", True))
        self.assertIs(failed["golden"], False)
        self.assertFalse(failed["ok"])
        self.assertEqual(failed["failures"], [f"{G}: AssertionError: differences: values"])
        self.assertTrue(failed["dirty"])

    def test_failures_are_one_line_each_from_the_result_lines_when_present(self):
        r = _result(run=3, failures=[("t.a", "x")], errors=[("t.b", "y")], started=["t.a", "t.b", "t.c"], lines=["t.a: AssertionError: x", "t.b: KeyError: 'y'"])
        rep = testreport.report(r, git=("abc1234", False))
        self.assertEqual(rep["failures"], ["t.a: AssertionError: x", "t.b: KeyError: 'y'"])
        self.assertIsNone(rep["golden"])  # the golden test never started

    def test_result_class_records_started_ids_and_first_error_lines(self):
        class Case(unittest.TestCase):
            def test_fails(self):
                self.fail("first line\nsecond line")

            def test_errors(self):
                raise KeyError("k")

            def test_ok(self):
                pass

        import io
        res = testreport.Result(io.StringIO(), True, 0)
        unittest.defaultTestLoader.loadTestsFromTestCase(Case).run(res)
        self.assertEqual(len(res.started), 3)
        self.assertEqual(sorted(l.split(".")[-1] for l in res.lines), ["test_errors: KeyError: 'k'", "test_fails: AssertionError: first line"])

    def test_write_makes_the_folder_and_pretty_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "reports" / "tests.json"
            testreport.write({"ok": True, "count": 1}, p)
            self.assertEqual(json.loads(p.read_text()), {"ok": True, "count": 1})


def _rep(ok=True, failures=(), golden=True, git="abc1234", dirty=False):
    return {"ok": ok, "count": 120, "failures": list(failures), "skipped": 0, "golden": golden, "at": "2026-11-02T10:00:00+00:00", "git": git, "dirty": dirty}


class Line(unittest.TestCase):
    def test_missing_file_is_not_run_and_blocks(self):
        l = checklist.tests_line(None, head="abc1234")
        self.assertEqual((l["state"], l["required"], l["ok"], l["count"]), ("not_run", True, False, 0))  # required: no run, no signature
        self.assertIn("not run", l["note"])

    def test_passing_on_head_is_green_and_required_with_golden_and_sha_in_the_note(self):
        l = checklist.tests_line(_rep(), head="abc1234")
        self.assertEqual((l["state"], l["required"], l["ok"], l["count"]), ("pass", True, True, 0))
        self.assertIn("regression test ok", l["note"])
        self.assertIn("abc1234", l["note"])
        self.assertIn("120 tests", l["note"])

    def test_failing_is_red_and_required_whatever_commit_it_ran_on(self):
        l = checklist.tests_line(_rep(ok=False, failures=["t.a: AssertionError: x", "t.b: KeyError: 'y'"], golden=False, git="0ld0000"), head="abc1234")
        self.assertEqual((l["state"], l["required"], l["ok"], l["count"]), ("fail", True, False, 2))
        self.assertEqual(l["detail"], [{"test": "t.a: AssertionError: x"}, {"test": "t.b: KeyError: 'y'"}])
        self.assertIn("regression test FAILED", l["note"])

    def test_passing_on_another_commit_or_a_dirty_tree_is_stale_and_blocks(self):
        other = checklist.tests_line(_rep(git="0ld0000"), head="abc1234", changed=["ledger/checks/rules.py", "reports/tests.json"])
        self.assertEqual((other["state"], other["required"], other["ok"]), ("stale", True, False))  # its own state (states.LINE), and it blocks
        self.assertIn("Stale", other["note"])
        self.assertIn("HEAD is abc1234", other["note"])
        self.assertEqual(other["link"], "proof")  # the page names no command: Fix in leads on (flow review #14)
        self.assertEqual(checklist.tests_line(_rep(git="0ld0000"), head="abc1234", changed=None)["state"], "stale")  # unknown sha: stale
        dirty = checklist.tests_line(_rep(dirty=True), head="abc1234", changed=[])
        self.assertEqual((dirty["state"], dirty["required"]), ("stale", True))
        self.assertIn("dirty tree", dirty["note"])

    def test_commits_since_the_run_that_only_recorded_it_are_forgiven(self):
        l = checklist.tests_line(_rep(git="0ld0000"), head="abc1234", changed=["reports/tests.json"])
        self.assertEqual((l["state"], l["required"], l["ok"]), ("pass", True, True))
        self.assertEqual(checklist.tests_line(_rep(git="0ld0000"), head="abc1234", changed=[])["state"], "pass")

    def test_without_git_on_either_side_the_commit_is_not_compared_and_the_line_blocks(self):
        for t, head in ((_rep(git=None, dirty=None), "abc1234"), (_rep(git="abc1234"), None), (_rep(git=None, dirty=None), None)):
            l = checklist.tests_line(t, head=head, changed=[])
            self.assertEqual((l["state"], l["required"], l["ok"]), ("info", True, False))  # no git: never a verified pass, so it blocks
            self.assertIn("commit not compared: no git", l["note"])
        self.assertNotIn(", on ", checklist.tests_line(_rep(git=None, dirty=None), head=None)["note"])
        self.assertEqual(checklist.tests_line(_rep(ok=False, failures=["t.a: x"], git=None), head=None)["state"], "fail")  # a failure is red even without git

    def test_golden_skipped_points_at_the_golden_line(self):
        self.assertIn("regression test skipped, see its own line", checklist.tests_line(_rep(golden=None), head="abc1234", changed=[])["note"])

    def test_dirty_counts_untracked_files_under_the_code_folders_only(self):
        import shutil
        import subprocess
        if not shutil.which("git"):
            self.skipTest("no git")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run = lambda *a: subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, check=True)
            run("init", "-q"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
            (root / "ledger").mkdir(); (root / "ledger" / "a.py").write_text("x\n")
            run("add", "."); run("commit", "-q", "-m", "one")
            sha, dirty = testreport.git_state(root)
            self.assertEqual((len(sha) >= 7, dirty), (True, False))
            (root / "reports").mkdir(); (root / "reports" / "tests.json").write_text("{}")
            (root / "scratch.txt").write_text("x")
            self.assertFalse(testreport.git_state(root)[1])  # the report and a stray file do not count
            (root / "tests").mkdir(); (root / "tests" / "test_new.py").write_text("x")
            self.assertTrue(testreport.git_state(root)[1])  # an untracked test does
            (root / "tests" / "test_new.py").unlink(); (root / "tests").rmdir()
            (root / "ledger" / "a.py").write_text("y\n")
            self.assertTrue(testreport.git_state(root)[1])  # a tracked change does
        self.assertEqual(testreport.git_state(Path("/nonexistent-root-for-ledger-test")), (None, None))

    def test_checklist_reads_the_file_from_its_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "tests.json"
            self.assertIsNone(checklist._report(p))
            p.write_text(json.dumps(_rep()))
            self.assertEqual(checklist._report(p)["count"], 120)
            p.write_text("{not json")
            self.assertIsNone(checklist._report(p))


if __name__ == "__main__":
    unittest.main()
