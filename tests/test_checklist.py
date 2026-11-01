"""The Release page's checklist and the Sign button (T5, T6, T7): a red line refuses, a green one builds, signs with
the checklist and publishes, in that order, through the real write and signoff into a temporary releases folder; the
read-only copy refuses with 403, a non-JSON or foreign-Origin POST with 403; the dry run on the real database refuses
while any required line is red and touches nothing."""
import json
import os
import shutil
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

FILES = {"values.csv": "ticker,field,period,value\nNVDA,capex,FY2026,5\n", "DIFF.md": "# Changes in v9.9.0\n"}
HASH = content_hash(FILES)


def _cl(ok: bool, red=(), version="v9.9.0", h=HASH) -> dict:
    lines = [{"id": "gate_G6", "label": "G6", "required": True, "count": 0 if ok else 7, "state": "pass" if ok else "fail", "ok": ok, "link": "reconcile", "note": "", "detail": []},
             {"id": "tests", "label": "Test run", "required": False, "count": 0, "state": "not_run", "ok": False, "link": "proof", "note": "not run", "detail": []}]
    return {"version": version, "previous": "v1.7.0", "scope": ["MSFT", "NVDA"], "stage": 3, "hash": h, "at": "2026-11-02T00:00:00+00:00", "ok": ok, "red": list(red),
            "lines": lines, "gates": {}, "open": 1, "blocked": 2, "unconfirmed": 0, "unmapped": 3, "diff": {"values": {"added": 1, "removed": 0, "changed": 0, "examples": {"added": [["X"]]}}},
            "golden": {"ok": True}, "tests": None, "exists": False, "signed": False, "folder": "none"}


def _packet(version="v9.9.0") -> dict:
    return {"version": version, "files": dict(FILES), "hash": HASH, "manifest": {"version": version, "hash": HASH, "files": sorted(FILES)}}


class TempReleases(unittest.TestCase):
    """Every test here signs into its own releases folder: checklist.RELEASES and signoff.RELEASES point at it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="releases-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for m in (checklist, signoff):
            patcher = mock.patch.object(m, "RELEASES", self.tmp)
            patcher.start()
            self.addCleanup(patcher.stop)

    def signoff_json(self, version="v9.9.0") -> dict:
        return json.loads((self.tmp / version / "SIGNOFF.json").read_text())


class Sign(TempReleases):
    def test_refuses_without_a_name_or_with_a_non_string_name_and_calls_nothing(self):
        with mock.patch.object(checklist, "checklist") as cl:
            for by in ("  ", None, 3, ["K"]):
                with self.assertRaises(ValueError):
                    checklist.sign(None, "v9.9.0", by)
            cl.assert_not_called()
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_refuses_while_a_required_line_is_red_and_writes_nothing(self):
        with mock.patch.object(checklist, "checklist", return_value=_cl(False, ["gate_G6", "unconfirmed"])), mock.patch("ledger.publish.publish") as p:
            with self.assertRaises(ValueError) as e:
                checklist.sign(None, "v9.9.0", "Kenny Geiler")
            self.assertIn("gate_G6", str(e.exception))
            p.assert_not_called()
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_green_builds_signs_with_the_checklist_then_publishes_and_records_it(self):
        calls = []
        with mock.patch.object(checklist, "checklist", side_effect=lambda con, v, st: calls.append("checklist") or _cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()), \
                mock.patch("ledger.publish.publish", side_effect=lambda v: calls.append(("publish", v)) or {"rows": {"values": 1}}):
            r = checklist.sign(None, "v9.9.0", " Kenny Geiler ")
        self.assertEqual(calls, ["checklist", "checklist", ("publish", "v9.9.0")])  # checked twice: before the write and on the folder as written
        self.assertTrue((self.tmp / "v9.9.0" / "manifest.json").exists())
        self.assertFalse(list(self.tmp.glob(".*.writing")))  # the temporary folder is gone: renamed into place
        s = self.signoff_json()
        self.assertEqual((s["signed_by"], s["hash"], s["published"], s["rows"]), ("Kenny Geiler", HASH, True, {"values": 1}))
        self.assertTrue(s["published_at"])
        self.assertEqual(s["checklist"]["lines"][0]["id"], "gate_G6")  # the checklist as it was at signing
        self.assertNotIn("examples", s["checklist"]["diff"]["values"])  # counts only; DIFF.md has the examples
        self.assertEqual((r["published"], r["rows"], r["signed_by"]), (True, {"values": 1}, "Kenny Geiler"))

    def test_a_failed_publish_leaves_the_signature_and_records_the_failure(self):
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()), \
                mock.patch("ledger.publish.publish", side_effect=SystemExit("Set DATABASE_URL in .env")):
            r = checklist.sign(None, "v9.9.0", "K")
        self.assertFalse(r["published"])
        self.assertIn("DATABASE_URL", r["publish_error"])
        s = self.signoff_json()
        self.assertEqual((s["signed_by"], s["published"]), ("K", False))
        self.assertIn("DATABASE_URL", s["publish_error"])
        self.assertNotIn("published_at", s)

    def test_a_red_second_pass_refuses_and_leaves_the_folder_unsigned(self):
        with mock.patch.object(checklist, "checklist", side_effect=[_cl(True), _cl(False, ["open"])]), mock.patch.object(checklist, "packet", return_value=_packet()), \
                mock.patch("ledger.publish.publish") as p:
            with self.assertRaises(ValueError) as e:
                checklist.sign(None, "v9.9.0", "K")
            p.assert_not_called()
        self.assertIn("open", str(e.exception))
        self.assertTrue((self.tmp / "v9.9.0" / "manifest.json").exists())
        self.assertFalse((self.tmp / "v9.9.0" / "SIGNOFF.json").exists())
        self.assertEqual(checklist.next_version(), "v9.9.0")  # the unsigned folder is the next version to sign, never skipped

    def test_the_data_changing_between_checklist_and_packet_refuses(self):
        with mock.patch.object(checklist, "checklist", return_value=_cl(True, h="other")), mock.patch.object(checklist, "packet", return_value=_packet()):
            with self.assertRaises(ValueError):
                checklist.sign(None, "v9.9.0", "K")
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_an_existing_folder_with_a_different_hash_or_a_signature_refuses(self):
        d = self.tmp / "v9.9.0"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({"hash": "stale"}))
        self.assertEqual(checklist.folder_state("v9.9.0", HASH)[0], "different")
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()):
            with self.assertRaises(ValueError) as e:
                checklist.sign(None, "v9.9.0", "K")
        self.assertIn("built before this release's checks; delete and rebuild", str(e.exception))
        (d / "manifest.json").write_text(json.dumps({"hash": HASH}))
        (d / "SIGNOFF.json").write_text("{}")
        self.assertEqual(checklist.folder_state("v9.9.0", HASH)[0], "signed")
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()):
            with self.assertRaises(ValueError) as e:
                checklist.sign(None, "v9.9.0", "K")
        self.assertIn("already signed", str(e.exception))
        (d / "manifest.json").unlink()
        (d / "SIGNOFF.json").unlink()
        self.assertEqual(checklist.folder_state("v9.9.0", HASH), ("broken", "releases/v9.9.0/ has no manifest.json: unsigned, broken; delete and rebuild"))

    def test_two_signatures_at_once_leave_one(self):
        results = []
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()), \
                mock.patch("ledger.publish.publish", return_value={"rows": {}}):
            def go():
                try:
                    results.append(checklist.sign(None, "v9.9.0", "K"))
                except ValueError as e:
                    results.append(e)
            ts = [threading.Thread(target=go) for _ in range(4)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1)
        self.assertEqual(sum(isinstance(r, ValueError) for r in results), 3)
        self.assertEqual(self.signoff_json()["signed_by"], "K")


class SignoffFile(TempReleases):
    def test_signoff_json_carries_the_checklist_the_cli_does_not_and_a_signature_is_never_replaced(self):
        d = self.tmp / "v9.9.0"
        d.mkdir()
        for n, t in FILES.items():
            (d / n).write_text(t)
        (d / "manifest.json").write_text(json.dumps({"version": "v9.9.0", "hash": HASH, "files": sorted(FILES)}))
        with self.assertRaises(ValueError):
            signoff.sign("v8.0.0", "K")  # no such release
        s = signoff.sign("v9.9.0", "Kenny Geiler", _cl(True))
        got = self.signoff_json()
        self.assertEqual((s["version"], got["signed_by"], got["checklist"]["scope"]), ("v9.9.0", "Kenny Geiler", ["MSFT", "NVDA"]))
        self.assertEqual(checklist.summary(got["checklist"]), {"open": 3, "unmapped": 3, "scope": ["MSFT", "NVDA"], "unconfirmed": 0, "at": "2026-11-02T00:00:00+00:00"})
        self.assertEqual(signoff.main(["v9.9.0", "--by", "CLI"]), 1)  # signed already: refused, by the page and by the command line
        self.assertEqual(self.signoff_json()["signed_by"], "Kenny Geiler")
        signoff.record("v9.9.0", published=False, publish_error="no url", signed_by="Mallory")
        got = self.signoff_json()
        self.assertEqual((got["signed_by"], got["published"], got["publish_error"]), ("Kenny Geiler", False, "no url"))  # record never touches the signed fields
        (d / "SIGNOFF.json").unlink()
        self.assertEqual(signoff.main(["v9.9.0", "--by", "CLI"]), 0)
        self.assertNotIn("checklist", self.signoff_json())  # the command line signs without one
        (d / "SIGNOFF.json").unlink()
        (d / "values.csv").write_text("ticker\nY\n")
        with self.assertRaises(ValueError):
            signoff.sign("v9.9.0", "K")  # the files no longer match their hash


class Versions(TempReleases):
    def test_next_version_is_the_lowest_unsigned_folder_else_the_minor_bump(self):
        self.assertEqual(checklist.next_version(), "v0.1.0")
        for v, signed in (("v1.7.0", True), ("v1.10.0", True)):
            (self.tmp / v).mkdir()
            if signed:
                (self.tmp / v / "SIGNOFF.json").write_text("{}")
        self.assertEqual(checklist.next_version(), "v1.11.0")
        self.assertEqual(checklist.previous_of("v1.8.0").name, "v1.7.0")
        self.assertIsNone(checklist.previous_of("v0.1.0"))
        (self.tmp / "v1.2.0").mkdir()  # unsigned and older than a signed release: superseded, never the next
        self.assertEqual(checklist.next_version(), "v1.11.0")
        (self.tmp / "v1.11.0").mkdir()
        (self.tmp / "v1.12.0").mkdir()
        self.assertEqual(checklist.next_version(), "v1.11.0")  # two unsigned folders after the last signed: the lowest, so no selector is needed

    def test_a_bad_version_is_a_value_error(self):
        for v in ("bad", "1.8.0", 5):
            with self.assertRaises(ValueError):
                checklist.checklist(None, v)


class Endpoints(unittest.TestCase):
    """The HTTP layer: every POST needs Content-Type application/json and, when a browser names an Origin, this server's
    own; /api/release/sign is 403 on the read-only copy and 400 on a red checklist or a bad name; the checklist GET is
    served before the /api/v1/ catch-all."""

    def _serve(self):
        from ledger import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(srv.shutdown)
        self.port = srv.server_address[1]
        return f"http://127.0.0.1:{self.port}"

    def _post(self, url, body, ctype="application/json", origin=None, raw=None):
        headers = {"Content-Type": ctype}
        if origin:
            headers["Origin"] = origin
        req = request.Request(url, data=raw if raw is not None else json.dumps(body).encode(), headers=headers, method="POST")
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

    def test_text_plain_and_foreign_origin_posts_are_refused_before_any_route(self):
        base = self._serve()
        with mock.patch("ledger.checklist.sign") as s, mock.patch("ledger.resolutions.resolve") as r:
            code, body = self._post(base + "/api/release/sign", None, ctype="text/plain", raw=b'{"version":"v9.9.0","by":"K"}')
            self.assertEqual(code, 403)
            self.assertIn("application/json", body["error"])
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "K"}, origin="https://evil.example")
            self.assertEqual(code, 403)
            self.assertIn("own pages", body["error"])
            code, body = self._post(base + "/api/resolve", {"key": "k"}, ctype="text/plain", raw=b"{}")  # every POST, not only sign
            self.assertEqual(code, 403)
            code, body = self._post(base + "/api/resolve", {"key": "k"}, origin="http://127.0.0.1:1")
            self.assertEqual(code, 403)
            s.assert_not_called()
            r.assert_not_called()
        with mock.patch("ledger.app._con", return_value=mock.MagicMock()), mock.patch("ledger.checklist.sign", return_value={"ok": 1}) as s:
            for origin in (f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}", None):  # the server's own origin, or none (curl)
                code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "K"}, ctype="application/json; charset=utf-8", origin=origin)
                self.assertEqual((code, body), (200, {"ok": 1}))
            self.assertEqual(s.call_count, 3)

    def test_a_red_checklist_or_a_bad_name_refuses_with_400(self):
        base = self._serve()
        with mock.patch("ledger.app._con", return_value=mock.MagicMock()), mock.patch("ledger.checklist.sign", side_effect=ValueError("v9.9.0 not signed: gate_G6 is red on the checklist")):
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "K"})
        self.assertEqual(code, 400)
        self.assertIn("gate_G6", body["error"])
        with mock.patch("ledger.app._con", return_value=mock.MagicMock()), mock.patch("ledger.checklist.checklist") as cl:
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": 7})  # a non-string name: refused before the checklist
            cl.assert_not_called()
        self.assertEqual(code, 400)
        self.assertIn("name", body["error"])

    def test_checklist_get_is_not_the_v1_catch_all(self):
        base = self._serve()
        with mock.patch("ledger.app._con", return_value=mock.MagicMock()), mock.patch("ledger.checklist.checklist", return_value=_cl(True)):
            with request.urlopen(base + "/api/v1/release/checklist?version=v9.9.0") as r:
                self.assertEqual(json.loads(r.read())["version"], "v9.9.0")

    def test_a_red_checklist_over_the_real_handler_into_a_temp_releases_folder(self):
        """The real sign() behind the real Handler: a red checklist is a 400 and the temp releases folder stays empty."""
        base = self._serve()
        tmp = Path(tempfile.mkdtemp(prefix="releases-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        with mock.patch("ledger.app._con", return_value=mock.MagicMock()), mock.patch.object(checklist, "RELEASES", tmp), mock.patch.object(signoff, "RELEASES", tmp), \
                mock.patch.object(checklist, "checklist", return_value=_cl(False, ["unconfirmed"])), mock.patch("ledger.publish.publish") as p:
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "K"})
            p.assert_not_called()
        self.assertEqual(code, 400)
        self.assertIn("unconfirmed", body["error"])
        self.assertEqual(list(tmp.iterdir()), [])

    def test_a_failed_publish_over_the_real_handler_is_200_published_false_and_recorded(self):
        base = self._serve()
        tmp = Path(tempfile.mkdtemp(prefix="releases-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        with mock.patch("ledger.app._con", return_value=mock.MagicMock()), mock.patch.object(checklist, "RELEASES", tmp), mock.patch.object(signoff, "RELEASES", tmp), \
                mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()), \
                mock.patch("ledger.publish.publish", side_effect=RuntimeError("connection refused")):
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "K"})
        self.assertEqual(code, 200)
        self.assertEqual((body["published"], body["signed_by"]), (False, "K"))
        self.assertIn("connection refused", body["publish_error"])
        s = json.loads((tmp / "v9.9.0" / "SIGNOFF.json").read_text())
        self.assertEqual((s["published"], s["publish_error"]), (False, "connection refused"))


class DryRun(unittest.TestCase):
    """On the real database (git-ignored; skipped without it). The checklist's hash equals what `ledger release` writes,
    into a temporary releases folder; and while any required line is red, Sign refuses before it writes, signs or
    publishes. When the checklist is green there is nothing to dry-run without writing, so that part skips."""

    @unittest.skipUnless(store.DEFAULT_DB.exists() and not os.environ.get("LEDGER_SKIP_DB"), "no data/ledger.duckdb")
    def test_the_checklist_hash_is_what_the_cli_writes_and_sign_refuses_while_red(self):
        import duckdb
        from ledger.cli import release as cli
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        tmp = Path(tempfile.mkdtemp(prefix="releases-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        for d in checklist._releases():  # the signed releases as they are, so the previous release and the next version are the repo's
            if (d / "SIGNOFF.json").exists():
                os.symlink(d, tmp / d.name)
        try:
            with mock.patch.object(checklist, "RELEASES", tmp), mock.patch.object(signoff, "RELEASES", tmp), mock.patch.object(store, "init", return_value=con):
                cl = checklist.checklist(con)
                self.assertEqual([l["id"] for l in cl["lines"]], ["gate_G1", "gate_G4", "gate_G5", "gate_G6", "open", "blocked", "unconfirmed", "unmapped", "no_value", "diff", "golden", "tests", "packet"])
                # into the temp folder the version is unseen, so the packet line is "built in memory"; the other lines are the repo's
                code = cli.main([cl["version"]])
                if (tmp / cl["version"] / "manifest.json").exists():
                    self.assertEqual(code, 0)
                    self.assertEqual(json.loads((tmp / cl["version"] / "manifest.json").read_text())["hash"], cl["hash"])
                    self.assertEqual((tmp / cl["version"] / "DIFF.md").read_text(), checklist.packet(con, cl["version"])["files"]["DIFF.md"])
                else:
                    self.assertEqual(code, 1)  # a red line the folder does not cause (gates, open, golden): the CLI refused too
            if cl["ok"]:
                self.skipTest(f"{cl['version']} is green: a dry run would sign")
            with mock.patch.object(checklist, "write") as w, mock.patch("ledger.cli.signoff.sign") as s, mock.patch("ledger.publish.publish") as p:
                with self.assertRaises(ValueError) as e:
                    checklist.sign(con, None, "dry run")
                w.assert_not_called(); s.assert_not_called(); p.assert_not_called()
            for lid in cl["red"]:
                self.assertIn(lid, str(e.exception))
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()
