"""The Release page's checklist and the Sign button (T5, T6, T7): a red line refuses, a green one builds, signs with
the checklist and publishes, in that order, through the real write and signoff into a temporary releases folder; the
read-only copy refuses with 403, a non-JSON or foreign-Origin POST with 403; the dry run on the real database refuses
while any required line is red and touches nothing."""
import http.client
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

from ledger.release import checklist
from ledger.core import store
from ledger.cli import signoff
from ledger.release.release import content_hash

FILES = {"values.csv": "ticker,field,period,value\nNVDA,capex,FY2026,5\n", "DIFF.md": "# Changes in v9.9.0\n"}
HASH = content_hash(FILES)


def _cl(ok: bool, red=(), version="v9.9.0", h=HASH) -> dict:
    lines = [{"id": "gate_G6", "label": "G6", "required": True, "count": 0 if ok else 7, "state": "pass" if ok else "fail", "ok": ok, "link": "reconcile", "note": "", "detail": []},
             {"id": "tests", "label": "Test run", "required": True, "count": 0, "state": "not_run", "ok": False, "link": "proof", "note": "not run", "detail": []}]
    return {"version": version, "previous": "v1.7.0", "scope": ["MSFT", "NVDA"], "stage": 3, "hash": h, "at": "2026-11-02T00:00:00+00:00", "ok": ok, "red": list(red),
            "lines": lines, "gates": {}, "open": 1, "blocked": 2, "unconfirmed": 0, "unmapped": 3, "diff": {"values": {"added": 1, "removed": 0, "changed": 0, "examples": {"added": [["X"]]}}},
            "golden": {"ok": True}, "tests": None, "exists": False, "signed": False, "folder": "none"}


def _packet(version="v9.9.0") -> dict:
    return {"version": version, "files": dict(FILES), "hash": HASH, "manifest": {"version": version, "hash": HASH, "files": sorted(FILES)}}


def _clean_checkout(case):
    """Patch checklist._live to a clean checkout for `case` (Sign refuses on uncommitted code first, F20)."""
    for p in (mock.patch.object(checklist, "_live", return_value={"head": "abc1234", "dirty": False, "code": "c1"}),
              mock.patch.object(checklist, "preflight", return_value={"head": "abc1234", "dirty": False, "code": "c1"})):
        p.start()
        case.addCleanup(p.stop)


class TempReleases(unittest.TestCase):
    """Every test here signs into its own releases folder: checklist.RELEASES and signoff.RELEASES point at it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="releases-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for m in (checklist, signoff):
            patcher = mock.patch.object(m, "RELEASES", self.tmp)
            patcher.start()
            self.addCleanup(patcher.stop)
        for patcher in (mock.patch.object(checklist, "_live", return_value={"head": "abc1234", "dirty": False, "code": "c1"}),  # a clean checkout: Sign reads it first (F20)
                        mock.patch.object(checklist, "preflight", return_value={"head": "abc1234", "dirty": False, "code": "c1"})):  # its gate holds (tests.test_trust tests it)
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

    def test_refuses_a_name_off_config_people_before_the_checklist(self):
        """F-BF5: Sign checks the name like every other write (T80): a name not on config.PEOPLE is a ValueError (400),
        refused before the checklist is built or anything is written."""
        with mock.patch.object(checklist, "checklist") as cl:
            for by in ("Mallory", "claude", "kenny geiler"):
                with self.assertRaises(ValueError) as e:
                    checklist.sign(None, "v9.9.0", by)
                self.assertIn("config.PEOPLE", str(e.exception))
            cl.assert_not_called()
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_refuses_while_a_required_line_is_red_and_writes_nothing(self):
        with mock.patch.object(checklist, "checklist", return_value=_cl(False, ["gate_G6", "unconfirmed"])), mock.patch("ledger.release.publish.publish") as p:
            with self.assertRaises(ValueError) as e:
                checklist.sign(None, "v9.9.0", "Kenny Geiler")
            self.assertIn("gate_G6", str(e.exception))
            p.assert_not_called()
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_green_builds_signs_with_the_checklist_then_publishes_and_records_it(self):
        calls = []
        with mock.patch.object(checklist, "checklist", side_effect=lambda con, v, st: calls.append("checklist") or _cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()), \
                mock.patch("ledger.release.publish.publish", side_effect=lambda v: calls.append(("publish", v)) or {"rows": {"values": 1}}):
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
                mock.patch("ledger.release.publish.publish", side_effect=SystemExit("Set DATABASE_URL in .env")):
            r = checklist.sign(None, "v9.9.0", "Kenny Geiler")
        self.assertFalse(r["published"])
        self.assertIn("DATABASE_URL", r["publish_error"])
        s = self.signoff_json()
        self.assertEqual((s["signed_by"], s["published"]), ("Kenny Geiler", False))
        self.assertIn("DATABASE_URL", s["publish_error"])
        self.assertNotIn("published_at", s)

    def test_a_red_second_pass_refuses_and_leaves_the_folder_unsigned(self):
        with mock.patch.object(checklist, "checklist", side_effect=[_cl(True), _cl(False, ["open"])]), mock.patch.object(checklist, "packet", return_value=_packet()), \
                mock.patch("ledger.release.publish.publish") as p:
            with self.assertRaises(ValueError) as e:
                checklist.sign(None, "v9.9.0", "Kenny Geiler")
            p.assert_not_called()
        self.assertIn("open", str(e.exception))
        self.assertTrue((self.tmp / "v9.9.0" / "manifest.json").exists())
        self.assertFalse((self.tmp / "v9.9.0" / "SIGNOFF.json").exists())
        self.assertEqual(checklist.next_version(), "v9.9.0")  # the unsigned folder is the next version to sign, never skipped

    def test_the_data_changing_between_checklist_and_packet_refuses(self):
        with mock.patch.object(checklist, "checklist", return_value=_cl(True, h="other")), mock.patch.object(checklist, "packet", return_value=_packet()):
            with self.assertRaises(ValueError):
                checklist.sign(None, "v9.9.0", "Kenny Geiler")
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_an_existing_folder_with_a_different_hash_or_a_signature_refuses(self):
        d = self.tmp / "v9.9.0"
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({"hash": "stale"}))
        self.assertEqual(checklist.folder_state("v9.9.0", HASH)[0], "different")
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()):
            with self.assertRaises(ValueError) as e:
                checklist.sign(None, "v9.9.0", "Kenny Geiler")
        self.assertIn("built before this release's checks; delete and rebuild", str(e.exception))
        (d / "manifest.json").write_text(json.dumps({"hash": HASH}))
        (d / "SIGNOFF.json").write_text("{}")
        self.assertEqual(checklist.folder_state("v9.9.0", HASH)[0], "signed")
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()):
            with self.assertRaises(ValueError) as e:
                checklist.sign(None, "v9.9.0", "Kenny Geiler")
        self.assertIn("already signed", str(e.exception))
        (d / "manifest.json").unlink()
        (d / "SIGNOFF.json").unlink()
        self.assertEqual(checklist.folder_state("v9.9.0", HASH), ("broken", "releases/v9.9.0/ has no manifest.json: unsigned, broken; delete and rebuild"))

    def test_a_record_that_fails_after_a_successful_publish_is_reported_not_undone(self):
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()), \
                mock.patch("ledger.release.publish.publish", return_value={"rows": {"values": 1}}), mock.patch("ledger.cli.signoff.record", side_effect=OSError("disk full")) as rec:
            r = checklist.sign(None, "v9.9.0", "Kenny Geiler")
        self.assertEqual((r["published"], r["rows"], r["record_error"]), (True, {"values": 1}, "disk full"))
        self.assertEqual(rec.call_count, 1)
        self.assertEqual(rec.call_args.kwargs["published"], True)  # never a record(published=False) after a publish that succeeded
        s = self.signoff_json()
        self.assertEqual(s["signed_by"], "Kenny Geiler")
        self.assertNotIn("published", s)  # the note did not land; the reply said so

    def test_folder_state_reads_a_manifest_of_the_right_shape_only(self):
        d = self.tmp / "v9.9.0"
        d.mkdir()
        (d / "manifest.json").write_text("[1, 2]")  # a list
        self.assertEqual(checklist.folder_state("v9.9.0", HASH)[0], "broken")
        (d / "manifest.json").write_text(json.dumps({"hash": 5}))  # not a str hash
        self.assertEqual(checklist.folder_state("v9.9.0", HASH)[0], "broken")
        (d / "manifest.json").write_bytes(b"\xff\xfe{")  # not UTF-8
        self.assertEqual(checklist.folder_state("v9.9.0", HASH)[0], "broken")
        (d / "manifest.json").write_text(json.dumps({"hash": HASH}))
        self.assertEqual(checklist.folder_state("v9.9.0", HASH)[0], "same")

    def test_two_signatures_at_once_leave_one(self):
        results = []
        with mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()), \
                mock.patch("ledger.release.publish.publish", return_value={"rows": {}}):
            def go():
                try:
                    results.append(checklist.sign(None, "v9.9.0", "Kenny Geiler"))
                except ValueError as e:
                    results.append(e)
            ts = [threading.Thread(target=go) for _ in range(4)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1)
        self.assertEqual(sum(isinstance(r, ValueError) for r in results), 3)
        self.assertEqual(self.signoff_json()["signed_by"], "Kenny Geiler")


class SignoffFile(TempReleases):
    def test_signoff_json_carries_the_checklist_the_cli_does_not_and_a_signature_is_never_replaced(self):
        d = self.tmp / "v9.9.0"
        d.mkdir()
        for n, t in FILES.items():
            (d / n).write_text(t)
        (d / "manifest.json").write_text(json.dumps({"version": "v9.9.0", "hash": HASH, "files": sorted(FILES)}))
        with self.assertRaises(ValueError):
            signoff.sign("v8.0.0", "Kenny Geiler")  # no such release
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
        self.assertEqual(signoff.main(["v9.9.0", "--by", "CLI"]), 1)  # F18: a name off config.PEOPLE never signs, from the command line either
        self.assertFalse((d / "SIGNOFF.json").exists())
        self.assertEqual(signoff.main(["v9.9.0", "--by", "Kenny Geiler"]), 0)
        self.assertNotIn("checklist", self.signoff_json())  # the command line signs without one
        (d / "SIGNOFF.json").unlink()
        (d / "values.csv").write_text("ticker\nY\n")
        with self.assertRaises(ValueError):
            signoff.sign("v9.9.0", "Kenny Geiler")  # the files no longer match their hash


class Versions(TempReleases):
    def test_next_version_is_the_lowest_unsigned_folder_else_the_minor_bump(self):
        self.assertEqual(checklist.next_version(), "v0.1.0")
        for v, signed in (("v1.7.0", True), ("v1.10.0", True)):
            (self.tmp / v).mkdir()
            (self.tmp / v / "manifest.json").write_text(json.dumps({"hash": "h"}))
            (self.tmp / v / "values.csv").write_text("ticker\n")
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

    def test_a_folder_that_is_not_a_version_never_blocks_the_next(self):
        (self.tmp / "v1.7.0").mkdir()
        (self.tmp / "v1.7.0" / "SIGNOFF.json").write_text("{}")
        (self.tmp / "v1.8.0-old").mkdir()
        (self.tmp / "v1.8.0.bak").write_text("")
        self.assertEqual([p.name for p in checklist._releases()], ["v1.7.0"])
        self.assertEqual(checklist.next_version(), "v1.8.0")

    def test_a_broken_previous_folder_is_skipped_and_named(self):
        good = self.tmp / "v1.6.0"
        good.mkdir()
        (good / "manifest.json").write_text(json.dumps({"hash": "h", "files": ["values.csv"]}))
        (good / "values.csv").write_text("ticker\n")
        (good / "SIGNOFF.json").write_text("{}")
        for name, broken in (("v1.7.0", lambda d: None), ("v1.7.1", lambda d: (d / "manifest.json").write_text("[]")),
                             ("v1.7.2", lambda d: (d / "manifest.json").write_text(json.dumps({"hash": "h"})))):  # no manifest; a list; no values.csv
            (self.tmp / name).mkdir()
            broken(self.tmp / name)
        self.assertEqual(checklist.previous_of("v1.8.0").name, "v1.6.0")
        self.assertEqual(checklist.broken_before("v1.8.0"), ["v1.7.0", "v1.7.1", "v1.7.2"])
        self.assertEqual(checklist.broken_before("v1.7.0"), [])

    def test_a_bad_version_is_a_value_error(self):
        for v in ("bad", "1.8.0", 5):
            with self.assertRaises(ValueError):
                checklist.checklist(None, v)


class Endpoints(unittest.TestCase):
    """The HTTP layer: every POST needs Content-Type application/json and, when a browser names an Origin, this server's
    own; /api/release/sign is 403 on the read-only copy and 400 on a red checklist or a bad name; the checklist GET is
    served before the /api/v1/ catch-all."""

    def setUp(self):
        _clean_checkout(self)

    def _serve(self):
        from ledger.web import app
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
        from ledger.web import app
        base = self._serve()
        with mock.patch.object(app, "READONLY", True), mock.patch("ledger.release.checklist.sign") as s:
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "Kenny Geiler"})
            s.assert_not_called()
        self.assertEqual(code, 403)
        self.assertIn("read-only", body["error"])

    def test_text_plain_and_foreign_origin_posts_are_refused_before_any_route(self):
        base = self._serve()
        with mock.patch("ledger.release.checklist.sign") as s, mock.patch("ledger.review.resolutions.resolve") as r:
            code, body = self._post(base + "/api/release/sign", None, ctype="text/plain", raw=b'{"version":"v9.9.0","by":"K"}')
            self.assertEqual(code, 403)
            self.assertIn("application/json", body["error"])
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "Kenny Geiler"}, origin="https://evil.example")
            self.assertEqual(code, 403)
            self.assertIn("own pages", body["error"])
            code, body = self._post(base + "/api/resolve", {"key": "k"}, ctype="text/plain", raw=b"{}")  # every POST, not only sign
            self.assertEqual(code, 403)
            code, body = self._post(base + "/api/resolve", {"key": "k"}, origin="http://127.0.0.1:1")
            self.assertEqual(code, 403)
            s.assert_not_called()
            r.assert_not_called()
        with mock.patch("ledger.web.app._con", return_value=mock.MagicMock()), mock.patch("ledger.release.checklist.sign", return_value={"ok": 1}) as s:
            for origin in (f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}", None):  # the server's own origin, or none (curl)
                code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "Kenny Geiler"}, ctype="application/json; charset=utf-8", origin=origin)
                self.assertEqual((code, body), (200, {"ok": 1}))
            self.assertEqual(s.call_count, 3)

    def test_a_red_checklist_or_a_bad_name_refuses_with_400(self):
        base = self._serve()
        with mock.patch("ledger.web.app._con", return_value=mock.MagicMock()), mock.patch("ledger.release.checklist.sign", side_effect=ValueError("v9.9.0 not signed: gate_G6 is red on the checklist")):
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "Kenny Geiler"})
        self.assertEqual(code, 400)
        self.assertIn("gate_G6", body["error"])
        with mock.patch("ledger.web.app._con", return_value=mock.MagicMock()), mock.patch("ledger.release.checklist.checklist") as cl:
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": 7})  # a non-string name: refused before the checklist
            cl.assert_not_called()
        self.assertEqual(code, 400)
        self.assertIn("name", body["error"])

    def test_a_list_body_or_a_bad_content_length_is_400_on_every_route(self):
        base = self._serve()
        with mock.patch("ledger.release.checklist.sign") as s, mock.patch("ledger.review.resolutions.resolve") as r:
            for path in ("/api/release/sign", "/api/resolve"):
                code, body = self._post(base + path, [1, 2])
                self.assertEqual((code, body["error"]), (400, "send a JSON object"))
                c = http.client.HTTPConnection("127.0.0.1", self.port)
                c.putrequest("POST", path)
                c.putheader("Content-Type", "application/json")
                c.putheader("Content-Length", "abc")
                c.endheaders()
                resp = c.getresponse()
                self.assertEqual(resp.status, 400)
                self.assertIn("Content-Length", json.loads(resp.read())["error"])
                c.close()
            s.assert_not_called()
            r.assert_not_called()

    def test_a_name_off_config_people_is_400_on_sign_and_mapping_reject(self):
        """F-BF5: the server refuses Sign and a mapping Reject by a name not on config.PEOPLE, as it does every other write."""
        base = self._serve()
        with mock.patch("ledger.web.app._con", return_value=mock.MagicMock()), mock.patch.object(checklist, "checklist") as cl, \
                mock.patch("ledger.review.mapper._append") as ap, mock.patch("ledger.review.mapper._edit") as ed:
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "Mallory"})
            self.assertEqual(code, 400)
            self.assertIn("config.PEOPLE", body["error"])
            code, body = self._post(base + "/api/mapping/reject", {"ticker": "MSFT", "reported_name": "Land", "standard_type": "us-gaap:LandMember", "by": "Mallory"})
            self.assertEqual(code, 400)
            self.assertIn("config.PEOPLE", body["error"])
            cl.assert_not_called()
            ap.assert_not_called()
            ed.assert_not_called()

    def test_checklist_get_is_not_the_v1_catch_all(self):
        base = self._serve()
        with mock.patch("ledger.web.app._con", return_value=mock.MagicMock()), mock.patch("ledger.release.checklist.checklist", return_value=_cl(True)):
            with request.urlopen(base + "/api/v1/release/checklist?version=v9.9.0") as r:
                self.assertEqual(json.loads(r.read())["version"], "v9.9.0")

    def test_a_red_checklist_over_the_real_handler_into_a_temp_releases_folder(self):
        """The real sign() behind the real Handler: a red checklist is a 400 and the temp releases folder stays empty."""
        base = self._serve()
        tmp = Path(tempfile.mkdtemp(prefix="releases-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        with mock.patch("ledger.web.app._con", return_value=mock.MagicMock()), mock.patch.object(checklist, "RELEASES", tmp), mock.patch.object(signoff, "RELEASES", tmp), \
                mock.patch.object(checklist, "checklist", return_value=_cl(False, ["unconfirmed"])), mock.patch("ledger.release.publish.publish") as p:
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "Kenny Geiler"})
            p.assert_not_called()
        self.assertEqual(code, 400)
        self.assertIn("unconfirmed", body["error"])
        self.assertEqual(list(tmp.iterdir()), [])

    def test_a_failed_publish_over_the_real_handler_is_200_published_false_and_recorded(self):
        base = self._serve()
        tmp = Path(tempfile.mkdtemp(prefix="releases-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        with mock.patch("ledger.web.app._con", return_value=mock.MagicMock()), mock.patch.object(checklist, "RELEASES", tmp), mock.patch.object(signoff, "RELEASES", tmp), \
                mock.patch.object(checklist, "checklist", return_value=_cl(True)), mock.patch.object(checklist, "packet", return_value=_packet()), \
                mock.patch("ledger.release.publish.publish", side_effect=RuntimeError("connection refused")):
            code, body = self._post(base + "/api/release/sign", {"version": "v9.9.0", "by": "Kenny Geiler"})
        self.assertEqual(code, 200)
        self.assertEqual((body["published"], body["signed_by"]), (False, "Kenny Geiler"))
        self.assertIn("connection refused", body["publish_error"])
        s = json.loads((tmp / "v9.9.0" / "SIGNOFF.json").read_text())
        self.assertEqual((s["published"], s["publish_error"]), (False, "connection refused"))


def fix_in_links_land_on_their_item(t, cl):
    """F-BF11: every Fix in opens the place that fixes the line: Hand check on Proof's hand check at the first unchecked
    company, Needs review on Reconcile's rule findings, Proposed on Category mapping when it holds any; a line fixed on
    Release itself (or on disk) has no Fix in; a per-company row in a line's detail links to that company."""
    L = {l["id"]: l for l in cl["lines"]}
    hc = L["hand_check"]
    if hc["state"] != "pass":
        first = next((d["company"] for d in hc["detail"] if "company" in d), None)
        if first:
            t.assertEqual(hc["link"], f"proof?gold={first}")
    t.assertEqual(L["open"]["link"], "reconcile?cause=finding_unconfirmed")
    if cl["gates"]["table"]["G6"] and any(d.get("key", "").startswith("asset_types|") for d in L["gate_G6"]["detail"]):
        t.assertEqual(L["gate_G6"]["link"], "reconcile?cause=asset_types")
    t.assertEqual((L["limitations"]["link"], L["previous"]["link"]), ("", ""))
    t.assertFalse([l["id"] for l in cl["lines"] if (l["link"] or "").split("?")[0] == "release"])
    for d in L["open"]["detail"]:
        if "ticker" in d:
            t.assertEqual(d["link"], f"reconcile?cause=finding_unconfirmed&scope={d['ticker']}")


class FixIn(unittest.TestCase):
    def test_scoped_links(self):
        self.assertEqual(checklist._scoped("proof", "APLD"), "proof/APLD")
        self.assertEqual(checklist._scoped("reconcile", "APLD"), "reconcile?scope=APLD")
        self.assertEqual(checklist._scoped("reconcile?cause=asset_types", "APLD"), "reconcile?cause=asset_types&scope=APLD")


class DryRun(unittest.TestCase):
    """On the real database (git-ignored; skipped without it). The checklist's hash equals what `ledger release` writes,
    into a temporary releases folder; and while any required line is red, Sign refuses before it writes, signs or
    publishes. When the checklist is green there is nothing to dry-run without writing, so that part skips."""

    def setUp(self):
        _clean_checkout(self)

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
                self.assertEqual([l["id"] for l in cl["lines"]], ["gate_G1", "gate_G4", "gate_G5", "gate_G6", "open", "blocked", "complete", "evidenced", "no_value", "diff", "limitations", "claims", "claims_doc", "known_gaps", "hand_check", "regression", "tests", "previous", "packet"])
                fix_in_links_land_on_their_item(self, cl)  # F-BF11
                comp = next(l for l in cl["lines"] if l["id"] == "complete")  # T81: required, and 0 on the six
                self.assertEqual((comp["required"], comp["state"], comp["count"]), (True, "pass", 0), comp["detail"][:3])
                lim = next(l for l in cl["lines"] if l["id"] == "limitations")  # T68: informs, never red
                self.assertEqual((lim["required"], lim["state"], lim["count"]), (False, "info", 2))
                self.assertEqual(sorted(d["id"] for d in lim["detail"]), ["no_monitoring_thresholds", "survivor_bias"])
                self.assertTrue(next(l for l in cl["lines"] if l["id"] == "previous")["ok"])
                broken = tmp / "v0.0.1"  # a broken folder before this version: a red required line, the page still renders
                broken.mkdir()
                (broken / "manifest.json").write_text("[]")
                cl2 = checklist.checklist(con, cl["version"])
                self.assertEqual(cl2["hash"], cl["hash"])
                self.assertIn("previous", cl2["red"])
                self.assertIn("previous release v0.0.1 is broken: delete and rebuild", next(l for l in cl2["lines"] if l["id"] == "previous")["note"])
                shutil.rmtree(broken)
                # into the temp folder the version is unseen, so the packet line is "built in memory"; the other lines are the repo's
                code = cli.main([cl["version"]])
                if (tmp / cl["version"] / "manifest.json").exists():
                    self.assertEqual(code, 0)
                    self.assertEqual(json.loads((tmp / cl["version"] / "manifest.json").read_text())["hash"], cl["hash"])
                    self.assertEqual((tmp / cl["version"] / "DIFF.md").read_text(), checklist.packet(con, cl["version"])["files"]["DIFF.md"])
                    assert_readme_matches_headers(self, {f.name: f.read_text() for f in (tmp / cl["version"]).iterdir() if f.suffix in (".csv", ".md")})  # T64
                else:
                    self.assertEqual(code, 1)  # a red line the folder does not cause (gates, open, golden): the CLI refused too
            if cl["ok"]:
                self.skipTest(f"{cl['version']} is green: a dry run would sign")
            with mock.patch.object(checklist, "write") as w, mock.patch("ledger.cli.signoff.sign") as s, mock.patch("ledger.release.publish.publish") as p:
                with self.assertRaises(ValueError) as e:
                    checklist.sign(con, None, "Kenny Geiler")
                w.assert_not_called(); s.assert_not_called(); p.assert_not_called()
            for lid in cl["red"]:
                self.assertIn(lid, str(e.exception))
        finally:
            con.close()


class Parity(unittest.TestCase):
    """Plumbing bug A: the Release checklist said "Items to review 45" while Reconcile's header said Needs review 16 ·
    Proposed 29: the 45 was 16 + 29, Needs review and Proposed together, and "Decisions left to confirm" counted the 29
    again. Each line now counts one bucket, named as Reconcile names it, with the same counting function (states.tally)."""

    def test_each_line_counts_a_distinct_bucket_by_its_row_word(self):
        item = lambda state, by: {"state": state, "by": by}
        board = {"proven": [{"ticker": "X", "stages": {"facts": {"all": [item("open", "rule:jump"), item("open", "rule:jump")]},
                                                      "mapping": {"all": [item("open", "label:to_confirm"), item("open", "label:to_confirm"), item("open", "label:to_confirm")]},
                                                      "release": {"all": [item("blocked", "rule:b")]}, "values": {"all": [item("checked", "xbrl")]}}}], "open": 6}
        rc = checklist.review_counts(board, [{"key": "finding_unconfirmed|X|capex|FY2024||jump|"}])  # unconfirmed() gives live keys only
        self.assertEqual((rc["bad"], rc["wait"], rc["blocked"]), (2, 3 + 1, 1))  # 2 + 4 + 1 = 7: every open item once, the old line said 5 then 3 again
        self.assertEqual(rc["bad"] + rc["wait"] - 1 + rc["blocked"], board["open"])  # Proof's open (6) = bad + wait items + blocked; the run decision is not a Proof item
        self.assertEqual(checklist.review_counts({"proven": []}, []), {"bad": 0, "wait": 0, "blocked": 0, "off_board": [], "per_company": []})  # nothing to count is zero, per bucket

    def test_an_unmapped_name_no_board_row_lists_still_blocks(self):
        item = lambda state, by, name=None: {"state": state, "by": by, **({"name": name} if name else {})}
        board = {"proven": [{"ticker": "X", "stages": {"mapping": {"all": [item("open", "label:unmapped", "Land")]}}}]}
        um = [{"ticker": "X", "reported_name": "Land"}, {"ticker": "X", "reported_name": "Servers"}]  # Servers has no board row
        rc = checklist.review_counts(board, [], um)
        self.assertEqual((rc["bad"], [m["reported_name"] for m in rc["off_board"]]), (2, ["Servers"]))  # Land once (on the board), Servers added
        self.assertEqual(rc["per_company"][0]["open"], 2)
        self.assertEqual(checklist.review_counts({"proven": []}, [], um)["bad"], 2)  # no board at all: every unmapped name still counts

    def test_g6_links_to_the_page_that_holds_its_items_and_lists_every_key(self):
        unc = [{"key": "finding_unconfirmed|X|capex|||jump|", "state": "explain", "reason": "a run decided"}]
        utc = [{"ticker": "X", "reported_name": "Land", "standard_type": "us-gaap:LandMember", "by": "mapper"}]
        self.assertEqual(checklist.g6_link(unc, utc), "reconcile?cause=asset_types")  # F-BF11: Proposed opens Category mapping
        self.assertEqual(checklist.g6_link(unc, []), "reconcile?cause=to_confirm")
        self.assertEqual(checklist.g6_link([], utc), "reconcile?cause=asset_types")
        d = checklist.g6_detail(unc, utc)
        self.assertEqual([(x["key"], x["reason"], x["link"]) for x in d],
                         [("finding_unconfirmed|X|capex|||jump|", "a run decided", "reconcile?cause=to_confirm"),
                          ("asset_types|X|Land", "us-gaap:LandMember proposed by mapper", "reconcile?scope=X&cause=asset_types")])

    @unittest.skipUnless(store.DEFAULT_DB.exists() and not os.environ.get("LEDGER_SKIP_DB"), "no data/ledger.duckdb")
    def test_release_lines_equal_reconcile_header_buckets_on_the_real_database(self):
        from ledger.review import workbench
        from ledger.web import app
        flow = app._flow("all")
        con = app._con()
        try:
            head = workbench.items(con, flow)["by_state"]
            cl = checklist.checklist(con)
        finally:
            con.close()
        lines = {l["id"]: l for l in cl["lines"]}
        for lid, bucket in (("open", "bad"), ("gate_G6", "wait"), ("blocked", "blocked")):
            self.assertEqual((lines[lid]["label"], lines[lid]["count"]), (stateword(bucket), head.get(bucket, 0)), lid)
        self.assertEqual(sum(l["label"] == stateword("wait") for l in cl["lines"]), 1)  # one line counts the proposals, not two
        self.assertNotIn("unconfirmed", lines)


def stateword(s):
    from ledger.core.states import word
    return word("row", s)


if __name__ == "__main__":
    unittest.main()


class Provenance(unittest.TestCase):
    """T66: the manifest names what produced the rows, not the versions in use at build time. A packet that mixes prompt
    versions lists both; a row whose run has no model on record is counted as unrecorded, never guessed; the inputs are the
    files' sha256; git is read from the checkout, null without git."""
    RUNS = [{"run_id": "r1", "step": "extract", "subject": "A1", "versions": json.dumps({"prompt": "statements@v1", "model": "claude-opus-5-5"})},
            {"run_id": "r2", "step": "extract", "subject": "A2", "versions": json.dumps({"prompt": "statements@v2", "model": None})},
            {"run_id": "r3", "step": "aispend", "subject": "T1", "versions": json.dumps({"prompt": "aispend@v4", "model": "claude-sonnet-5"})}]
    VALUES = [{"ticker": "X", "field": "revenue", "period": "FY2025", "extraction_ids": "0000000001-25-000001|revenue|a|b"},
              {"ticker": "X", "field": "opex", "period": "FY2025", "extraction_ids": "0000000002-25-000001|revenue|a|b,0000000002-25-000001|cost_of_revenue_part|a|b|Fuel, purchased power"},
              {"ticker": "X", "field": "capex", "period": "FY2025", "extraction_ids": None}]
    EXTS = [{"extraction_id": "0000000001-25-000001|revenue|a|b", "accession": "A1", "prompt_version": "statements@v1", "run_id": "r1"},
            {"extraction_id": "0000000002-25-000001|revenue|a|b", "accession": "A2", "prompt_version": "statements@v2", "run_id": "r2"},
            {"extraction_id": "0000000002-25-000001|cost_of_revenue_part|a|b|Fuel, purchased power", "accession": "A2", "prompt_version": "statements@v2", "run_id": "r2"},
            {"extraction_id": "A9|revenue|a|b", "accession": "A9", "prompt_version": "statements@v0", "run_id": "r9"}]  # not cited by a shipped value: not provenance

    def test_mixed_prompt_versions_are_both_listed_and_an_unrecorded_row_is_counted(self):
        p = checklist.provenance(self.VALUES, self.EXTS, [], statements=[{"text_id": "T1", "prompt_version": "aispend@v4", "run_id": "r3"}],
                                 documents=[{"accession": "A1", "parser_version": "tables@12"}, {"accession": "A2", "parser_version": "tables@15"}, {"accession": "A3", "parser_version": "tables@12"}],
                                 runs=self.RUNS, git=("abc1234", False), inputs={"definitions/companies.yaml": "x"})
        self.assertEqual(p["prompts"], {"reader": ["statements@v1", "statements@v2"], "notes_reader": [], "ai_reader": ["aispend@v4"], "projects_reader": []})
        self.assertEqual(p["models"], ["claude-opus-5-5", "claude-sonnet-5"])
        self.assertEqual(p["parser_versions"], ["tables@12", "tables@15"])
        self.assertEqual(p["unrecorded"], {"reader": 2, "notes_reader": 0, "ai_reader": 0, "projects_reader": 0})  # the two A2 cells: run r2 has no model
        self.assertEqual(p["git"], {"head": "abc1234", "dirty": False})
        self.assertEqual(p["inputs"], {"definitions/companies.yaml": "x"})

    def test_inputs_are_the_files_sha256_and_a_missing_file_is_null(self):
        import hashlib
        root = Path(tempfile.mkdtemp(prefix="inputs-"))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "definitions").mkdir(); (root / "taxonomy").mkdir(); (root / "decisions").mkdir()
        (root / "definitions" / "companies.yaml").write_text("a: 1\n")
        (root / "taxonomy" / "taxonomy.yaml").write_text("b: 2\n")
        (root / "taxonomy" / "asset_types.yaml").write_text("c: 3\n")
        h = checklist.input_hashes(root)
        self.assertEqual(list(h), ["definitions/companies.yaml", "taxonomy/asset_types.yaml", "taxonomy/taxonomy.yaml", "decisions/resolutions.jsonl"])
        self.assertEqual(h["definitions/companies.yaml"], hashlib.sha256(b"a: 1\n").hexdigest())
        self.assertEqual(h["taxonomy/asset_types.yaml"], hashlib.sha256(b"c: 3\n").hexdigest())
        self.assertIsNone(h["decisions/resolutions.jsonl"])
        real = checklist.input_hashes()  # the checkout's own: every taxonomy/*.yaml, hashed as the file is
        for path, digest in real.items():
            f = store.ROOT / path
            self.assertEqual(digest, hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None, path)
        self.assertTrue(any(k.startswith("taxonomy/") for k in real))

    def test_git_is_read_from_the_checkout_and_null_without_git(self):
        import subprocess
        with mock.patch.object(subprocess, "run", side_effect=OSError("no git")):
            p = checklist.provenance([], [], [], inputs={})
        self.assertEqual(p["git"], {"head": None, "dirty": None})
        head, dirty = checklist.git_state()
        if head is not None:
            self.assertRegex(head, r"^[0-9a-f]{7,}$")
            self.assertIsInstance(dirty, bool)

    def test_the_diff_names_the_correction_once_when_the_previous_manifest_has_no_provenance(self):
        note = checklist.provenance_note("v1.8.0", "v1.9.0")
        self.assertIn("v1.8.0's manifest named the versions in use at build time; from v1.9.0 the manifest names the versions that produced the rows", note)

    def test_the_packet_notes_the_correction_once_against_a_previous_manifest_without_provenance_and_never_with(self):
        """Packet-level: the real `packet` over mocked rows, into a temp releases folder whose previous release has a manifest
        with or without `provenance`."""
        tmp = Path(tempfile.mkdtemp(prefix="releases-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        value = {"ticker": "NVDA", "field": "capex", "period": "FY2026", "period_end": "2026-01-25", "value": 5, "basis": "reported", "first_reported": None,
                 "source": "agent", "label": "agree", "extraction_ids": None}
        prev = tmp / "v1.0.0"
        prev.mkdir()
        (prev / "values.csv").write_text("ticker,field,period,period_end,value,basis,first_reported,source,xbrl,citations\nNVDA,capex,FY2026,2026-01-25,5,reported,,agent,agree,\n")
        rows = lambda con, sql, p: [value] if '"values"' in sql else []
        for manifest, times in (({"hash": "x", "files": ["values.csv"]}, 1), ({"hash": "x", "files": ["values.csv"], "provenance": {}}, 0)):
            (prev / "manifest.json").write_text(json.dumps(manifest))
            with mock.patch.object(checklist, "RELEASES", tmp), mock.patch.object(checklist, "_rows", side_effect=rows), mock.patch.object(checklist, "decisions", return_value=[]), \
                    mock.patch.object(checklist, "load_all", return_value={}), mock.patch.object(checklist, "gates", return_value={}), mock.patch.object(checklist, "load_rules", return_value=[]), \
                    mock.patch.object(checklist.api, "fetch", return_value=[]), mock.patch.object(checklist, "_provenance_rows", return_value={}), \
                    mock.patch.object(checklist, "git_state", return_value=(None, None)), mock.patch.object(checklist, "input_hashes", return_value={}):
                p = checklist.packet(mock.MagicMock(), "v1.1.0")
            self.assertEqual(p["files"]["DIFF.md"].count("Provenance:"), times, manifest)
            self.assertEqual(p["previous"], "v1.0.0")
            self.assertIn("provenance", p["manifest"])


def assert_readme_matches_headers(tc: unittest.TestCase, files: dict):
    """T64: the README's column tables are the CSV headers that ship, one table per CSV, every column in the file's order,
    and no column in a table that the file does not carry."""
    import re
    readme = files["README.md"]
    tables = {m.group(1): re.findall(r"^\| `([^`]+)` \|", m.group(2), re.M)
              for m in re.finditer(r"^## Columns of (\S+\.csv)\n\n(.*?)(?=^## |\Z)", readme, re.M | re.S)}
    csvs = {n for n in files if n.endswith(".csv")}
    tc.assertEqual(set(tables), csvs, "one column table per CSV in the packet")
    for name in sorted(csvs):
        header = files[name].splitlines()[0].split(",") if files[name] else []
        tc.assertEqual(tables[name], header, f"{name}: the README's table is the header that ships")


class PacketColumns(unittest.TestCase):
    """T64: values.csv ships the columns the README promises (first_reported, filed, accession, citations), the README's
    column tables are written from the headers that ship, and a row without a value is not in values.csv but is counted."""

    def _packet(self, tmp: Path, hc=None):
        from ledger.core.store import TABLES, TAXONOMY
        value = {"ticker": "NVDA", "field": "capex", "period": "FY2026", "period_end": "2026-01-25", "value": 5, "basis": "as_reported", "first_reported": 5,
                 "source": "agent", "label": "agree", "extraction_ids": "0000000001-26-000001|capex|2025-01-27|2026-01-25"}
        blank = {**value, "field": "opex", "value": None, "first_reported": None, "source": "missing", "label": "not_reported", "extraction_ids": None}
        api_cols = {  # the columns the read API serves per list (ledger/web/api.py fetch), the columns a release ships
            "values": ["ticker", "field", "period", "period_end", "value", "check_label", "basis", "first_reported", "source", "extraction_ids", "accession", "filed", "citations", "layer", "proven", "status", "flag"],
            "facts": ["ticker", "field", "dimension", "period", "period_end", "value", "check_label", "xbrl", "accession", "basis", "layer", "proven", "status", "flag"],
            "statements": ["statement_id", "ticker", "field", "period", "kind", "scope", "class", "amount_low", "amount_high", "amount_mid", "share", "quote", "source", "date", "url", "layer", "proven"],
            "projects": [c.name for c in TABLES["projects"].cols] + ["layer", "proven"],
            "companies": ["ticker", "name", "layer", "group", "role", "note", "sic", "sic_description", "proven"],
            "taxonomy": [c.name for c in TAXONOMY.cols] + ["layer", "proven"]}
        fetch = lambda con, name: [{c: ("NVDA" if c == "ticker" else "") for c in api_cols[name]}]
        rows = lambda con, sql, p: [value, blank] if '"values"' in sql else []
        with mock.patch.object(checklist, "RELEASES", tmp), mock.patch.object(checklist, "_rows", side_effect=rows), mock.patch.object(checklist, "decisions", return_value=[]), \
                mock.patch.object(checklist, "load_all", return_value={}), mock.patch.object(checklist, "gates", return_value={}), mock.patch.object(checklist, "load_rules", return_value=[]), \
                mock.patch.object(checklist.api, "fetch", side_effect=fetch), mock.patch.object(checklist, "_provenance_rows", return_value={}), \
                mock.patch.object(checklist, "git_state", return_value=(None, None)), mock.patch.object(checklist, "input_hashes", return_value={}), \
                mock.patch.object(checklist.store, "ROOT", tmp):
            if hc is not None:
                (tmp / "golden").mkdir(exist_ok=True)
                (tmp / "golden" / "stage3-handcheck.json").write_text(json.dumps(hc))
            return checklist.packet(mock.MagicMock(), "v1.1.0")

    def test_every_csv_header_is_the_readme_table_and_values_carries_the_promised_columns(self):
        tmp = Path(tempfile.mkdtemp(prefix="releases-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        p = self._packet(tmp)
        files = p["files"]
        assert_readme_matches_headers(self, files)
        header = files["values.csv"].splitlines()[0].split(",")
        for col in ("first_reported", "filed", "accession", "citations", "check_label"):
            self.assertIn(col, header)
        self.assertNotIn("xbrl", header)  # the API's name is check_label; the old README named a column the file never had
        self.assertIn("10-K gives no figure for is not a row here (1 in this release: NVDA 1", files["README.md"])
        self.assertIn("1 rows without a value, not in values.csv (not_reported: 1)", files["QUALITY.md"])
        self.assertIn("1 rows without a value, not in values.csv (not_reported: 1).", files["DIFF.md"])
        self.assertNotIn("Added:", files["DIFF.md"])  # the blank row is not a value added (DC6)
        self.assertIn("By a person: no hand-check for this release", files["QUALITY.md"])
        self.assertNotIn("by a person where it can't", files["QUALITY.md"])
        self.assertFalse(p["hand_check"])
        self.assertIn("| `systematic_without_xbrl` |", files["LIMITATIONS.md"])  # T68: in every packet, counted over the shipped lists
        self.assertIn("0 of 1 values in values.csv agree", files["LIMITATIONS.md"])  # the shipped values.csv (api.fetch's, mocked here with an empty check_label), not build's
        self.assertIn("LIMITATIONS.md", p["manifest"]["files"])

    def test_a_hand_check_file_is_named_with_its_count_and_a_previous_release_diffs_without_blank_rows(self):
        tmp = Path(tempfile.mkdtemp(prefix="releases-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        prev = tmp / "v1.0.0"
        prev.mkdir()
        (prev / "values.csv").write_text("ticker,field,period,period_end,value,basis,first_reported,source,xbrl,citations\n")  # no rows: NVDA capex is new
        (prev / "manifest.json").write_text(json.dumps({"hash": "x", "files": ["values.csv"], "provenance": {}}))
        hc = {"stage": 3, "values": [{"ticker": "NVDA", "field": "capex", "period": "FY2026", "value": 5, "verified": True},
                                     {"ticker": "NVDA", "field": "revenue", "period": "FY2026", "value": 9, "verified": True}]}  # revenue is not a shipped row: not counted
        p = self._packet(tmp, hc)
        self.assertTrue(p["hand_check"])
        self.assertIn("By a person: 1 values verified on the filing in golden/stage3-handcheck.json, at the value released", p["files"]["QUALITY.md"])
        self.assertIn("Added: 1 values for NVDA.", p["files"]["DIFF.md"])  # the value, not the blank opex row
        self.assertIn("1 rows without a value, not in values.csv (not_reported: 1).", p["files"]["DIFF.md"])

    def test_an_undocumented_column_refuses_to_ship(self):
        from ledger.release.release import column_doc, readme
        with self.assertRaises(KeyError):
            column_doc("values", "made_up")
        with self.assertRaises(KeyError):
            readme("v0.0.1", [{"ticker": "NVDA", "period": "FY2026", "value": 1}], [], {"values.csv": "ticker,made_up\nNVDA,1\n"})
        self.assertEqual(column_doc("values", "field")[0], "`revenue`, `capex`, `opex`")  # the shipped set, not the table's enum
        self.assertEqual(column_doc("taxonomy", "measure")[0], "`spent`, `committed`, `derived`, `planned`, `company_stated_ai`")


class HistoricSignatures(unittest.TestCase):
    """Review question 11: the PEOPLE check is on the act of signing only (checklist.sign). A release already signed is a
    record: nothing that reads releases/*/SIGNOFF.json checks its signed_by against config.PEOPLE, so a historic signer
    ("K", or anyone since removed from the list) stays readable and publishable. Pinned with the list emptied."""

    def test_signed_releases_read_and_check_with_nobody_on_the_list(self):
        from ledger.core import config
        from ledger.release import publish
        from ledger.web import app
        signed = [d for d in checklist._releases() if (d / "SIGNOFF.json").exists()]
        self.assertTrue(signed)
        with mock.patch.object(config, "PEOPLE", []):
            for d in [d for d in signed if "files" in json.loads((d / "manifest.json").read_text())]:  # manifests before the files list cannot be re-hashed, signer or not
                self.assertEqual(publish.check(d.name)["signoff"]["signed_by"], json.loads((d / "SIGNOFF.json").read_text())["signed_by"])
            self.assertEqual({r["version"] for r in app.outputs()["releases"] if r["signed_by"]}, {d.name for d in signed})
