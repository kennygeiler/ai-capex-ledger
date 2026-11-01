"""The Release page's checklist and the Sign button (T5, T6, T7): a red line refuses, a green one builds, signs with
the checklist and publishes, in that order; the read-only copy refuses with 403; the dry run on the real database
refuses while any required line is red and touches nothing."""
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib import error, request

from ledger import checklist, store
from ledger.cli import signoff
from ledger.release import content_hash


def _cl(ok: bool, red=()) -> dict:
    lines = [{"id": "gate_G6", "label": "G6", "required": True, "count": 0 if ok else 7, "state": "pass" if ok else "fail", "ok": ok, "link": "reconcile", "note": "", "detail": []},
             {"id": "tests", "label": "Test run", "required": False, "count": 0, "state": "not_run", "ok": False, "link": "proof", "note": "not run", "detail": []}]
    return {"version": "v9.9.0", "previous": "v1.7.0", "scope": ["MSFT", "NVDA"], "stage": 3, "hash": "h", "at": "2026-11-02T00:00:00+00:00", "ok": ok, "red": list(red),
            "lines": lines, "gates": {}, "open": 1, "blocked": 2, "unconfirmed": 0, "unmapped": 3, "diff": {"values": {"added": 1, "removed": 0, "changed": 0, "examples": {"added": [["X"]]}}},
            "golden": {"ok": True}, "tests": None, "exists": False, "signed": False}


class Sign(unittest.TestCase):
    def test_refuses_without_a_name_and_calls_nothing(self):
        with mock.patch.object(checklist, "checklist") as cl, mock.patch.object(checklist, "write") as w:
            with self.assertRaises(ValueError):
                checklist.sign(None, "v9.9.0", "  ")
            cl.assert_not_called()
            w.assert_not_called()

    def test_refuses_while_a_required_line_is_red_and_writes_nothing(self):
        with mock.patch.object(checklist, "checklist", return_value=_cl(False, ["gate_G6", "unconfirmed"])), mock.patch.object(checklist, "write") as w, \
                mock.patch("ledger.cli.signoff.sign") as s, mock.patch("ledger.publish.publish") as p:
            with self.assertRaises(ValueError) as e:
                checklist.sign(None, "v9.9.0", "Kenny Geiler")
            self.assertIn("gate_G6", str(e.exception))
            w.assert_not_called(); s.assert_not_called(); p.assert_not_called()

    def test_green_builds_signs_with_the_checklist_then_publishes(self):
        calls = []
        pk = {"version": "v9.9.0", "hash": "h", "files": {}, "manifest": {}}
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=pk), \
                mock.patch.object(checklist, "write", side_effect=lambda p: calls.append("write") or {"written": True, "hash": "h"}), \
                mock.patch("ledger.cli.signoff.sign", side_effect=lambda v, by, c: calls.append(("sign", v, by, c)) or {"signed_by": by, "signed_at": "t"}), \
                mock.patch("ledger.publish.publish", side_effect=lambda v: calls.append(("publish", v)) or {"rows": {"values": 2}}):
            r = checklist.sign(None, "v9.9.0", " Kenny Geiler ")
        self.assertEqual([c if isinstance(c, str) else c[0] for c in calls], ["write", "sign", "publish"])
        signed = calls[1]
        self.assertEqual(signed[1:3], ("v9.9.0", "Kenny Geiler"))
        self.assertEqual(signed[3]["lines"][0]["id"], "gate_G6")  # the checklist as it was at signing
        self.assertNotIn("examples", signed[3]["diff"]["values"])  # counts only; DIFF.md has the examples
        self.assertEqual(r["published"], True)
        self.assertEqual(r["rows"], {"values": 2})

    def test_a_failed_publish_leaves_the_signature_and_says_so(self):
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value={"version": "v9.9.0", "hash": "h", "files": {}, "manifest": {}}), \
                mock.patch.object(checklist, "write", return_value={"written": True, "hash": "h"}), mock.patch("ledger.cli.signoff.sign", return_value={"signed_by": "K", "signed_at": "t"}), \
                mock.patch("ledger.publish.publish", side_effect=SystemExit("Set DATABASE_URL in .env")):
            r = checklist.sign(None, "v9.9.0", "K")
        self.assertFalse(r["published"])
        self.assertIn("DATABASE_URL", r["publish_error"])

    def test_the_data_changing_between_checklist_and_packet_refuses(self):
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value={"version": "v9.9.0", "hash": "other", "files": {}, "manifest": {}}), \
                mock.patch.object(checklist, "write") as w:
            with self.assertRaises(ValueError):
                checklist.sign(None, "v9.9.0", "K")
            w.assert_not_called()


class SignoffFile(unittest.TestCase):
    def test_signoff_json_carries_the_checklist_and_the_cli_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "v9.9.0"
            d.mkdir()
            files = {"values.csv": "ticker\nX\n"}
            (d / "values.csv").write_text(files["values.csv"])
            (d / "manifest.json").write_text(json.dumps({"version": "v9.9.0", "hash": content_hash(files), "files": ["values.csv"]}))
            with mock.patch.object(signoff, "RELEASES", Path(tmp)):
                s = signoff.sign("v9.9.0", "Kenny Geiler", _cl(True))
                got = json.loads((d / "SIGNOFF.json").read_text())
                self.assertEqual(got["signed_by"], "Kenny Geiler")
                self.assertEqual(got["checklist"]["scope"], ["MSFT", "NVDA"])
                self.assertEqual(checklist.summary(got["checklist"]), {"open": 3, "unmapped": 3, "scope": ["MSFT", "NVDA"], "unconfirmed": 0, "at": "2026-11-02T00:00:00+00:00"})
                self.assertEqual(signoff.main(["v9.9.0", "--by", "CLI"]), 0)
                self.assertNotIn("checklist", json.loads((d / "SIGNOFF.json").read_text()))  # the command line signs without one
                (d / "values.csv").write_text("ticker\nY\n")
                with self.assertRaises(ValueError):
                    signoff.sign("v9.9.0", "K")
        self.assertEqual(s["version"], "v9.9.0")


class Versions(unittest.TestCase):
    def test_next_version_bumps_the_minor_of_the_last_folder(self):
        with mock.patch.object(checklist, "releases", return_value=[Path("v1.7.0"), Path("v1.10.0")]):
            self.assertEqual(checklist.next_version(), "v1.11.0")
        with mock.patch.object(checklist, "releases", return_value=[]):
            self.assertEqual(checklist.next_version(), "v0.1.0")
        with mock.patch.object(checklist, "releases", return_value=[Path("v1.7.0"), Path("v1.8.0")]):
            self.assertEqual(checklist.previous_of("v1.8.0").name, "v1.7.0")
            self.assertIsNone(checklist.previous_of("v0.1.0"))


class Endpoints(unittest.TestCase):
    """The HTTP layer: /api/release/sign is 403 on the read-only copy and 400 on a red checklist; the checklist GET is served
    before the /api/v1/ catch-all."""

    def _serve(self):
        from ledger import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(srv.shutdown)
        return f"http://127.0.0.1:{srv.server_address[1]}"

    def _post(self, url, body):
        req = request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_readonly_refuses_with_403(self):
        from ledger import app
        base = self._serve()
        with mock.patch.object(app, "READONLY", True), mock.patch("ledger.checklist.sign") as s:
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "K"})
            s.assert_not_called()
        self.assertEqual(code, 403)
        self.assertIn("read-only", body["error"])

    def test_a_red_checklist_refuses_with_400(self):
        base = self._serve()
        with mock.patch("ledger.app._con", return_value=mock.MagicMock()), mock.patch("ledger.checklist.sign", side_effect=ValueError("v9.9.0 not signed: gate_G6 is red on the checklist")):
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "K"})
        self.assertEqual(code, 400)
        self.assertIn("gate_G6", body["error"])

    def test_checklist_get_is_not_the_v1_catch_all(self):
        base = self._serve()
        with mock.patch("ledger.app._con", return_value=mock.MagicMock()), mock.patch("ledger.checklist.checklist", return_value=_cl(True)):
            with request.urlopen(base + "/api/v1/release/checklist?version=v9.9.0") as r:
                self.assertEqual(json.loads(r.read())["version"], "v9.9.0")


class DryRun(unittest.TestCase):
    """On the real database (git-ignored; skipped without it): while any required line is red, Sign refuses before it
    writes, signs or publishes. When the checklist is green there is nothing to dry-run without writing, so it skips."""

    @unittest.skipUnless(store.DEFAULT_DB.exists() and not os.environ.get("LEDGER_SKIP_DB"), "no data/ledger.duckdb")
    def test_sign_refuses_while_a_required_line_is_red(self):
        import duckdb
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        try:
            cl = checklist.checklist(con)
            if cl["ok"]:
                self.skipTest(f"{cl['version']} is green: a dry run would sign")
            with mock.patch.object(checklist, "write") as w, mock.patch("ledger.cli.signoff.sign") as s, mock.patch("ledger.publish.publish") as p:
                with self.assertRaises(ValueError) as e:
                    checklist.sign(con, None, "dry run")
                w.assert_not_called(); s.assert_not_called(); p.assert_not_called()
            for lid in cl["red"]:
                self.assertIn(lid, str(e.exception))
            self.assertEqual([l["id"] for l in cl["lines"]], ["gate_G1", "gate_G4", "gate_G5", "gate_G6", "open", "blocked", "unconfirmed", "unmapped", "no_value", "diff", "golden", "tests", "packet"])
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()
