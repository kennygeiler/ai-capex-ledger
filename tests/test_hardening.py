"""F-BF12, the code review's small items: the crop renderer loads only the document it was sent to; the crop route opens the
database inside _guard (busy is a 503); crops' module memo is read and written under a lock; scripts name modules and
commands that exist."""
import json
import re
import shutil
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib import error, request

from ledger.checks import crops, evidence
from ledger.web import app

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path("/Applications/Google Chrome.app").exists() or shutil.which("google-chrome")


@unittest.skipUnless(CHROME, "no Chrome")
class OnlyTheDocument(unittest.TestCase):
    def test_another_local_file_and_a_remote_url_are_aborted(self):
        from playwright.sync_api import sync_playwright
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / "secret.txt").write_text("not the filing")
        (d / "pic.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        doc = d / "filing.htm"
        doc.write_text('<html><body><table><tr><td>1</td></tr></table><img src="pic.png"><img src="https://example.com/x.png">'
                       '<iframe src="secret.txt"></iframe></body></html>')
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            try:
                page = b.new_page()
                blocked = evidence.offline(page)
                uri = evidence.goto_doc(page, doc)
                self.assertEqual(page.evaluate("document.querySelector('td').textContent"), "1")  # the document itself loaded
                self.assertEqual(uri, doc.resolve().as_uri())
            finally:
                b.close()
        self.assertIn((d / "pic.png").resolve().as_uri(), blocked)
        self.assertIn((d / "secret.txt").resolve().as_uri(), blocked)
        self.assertIn("https://example.com/x.png", blocked)


class CropRouteBusy(unittest.TestCase):
    def test_a_busy_database_is_a_503_not_a_dropped_connection(self):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        with mock.patch.object(crops, "extraction_of", return_value="x"), mock.patch.object(app, "_con", side_effect=app.Busy("database busy")):
            try:
                request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/evidence/crops/0000000000aa.png")
                self.fail("expected an HTTP error")
            except error.HTTPError as e:
                self.assertEqual((e.code, json.loads(e.read())["error"]), (503, "database busy"))


class MemoLock(unittest.TestCase):
    def test_record_now_and_extraction_of_hold_the_lock(self):
        held = []

        class Spy:
            def __enter__(self):
                held.append(True)

            def __exit__(self, *a):
                return False
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        f = d / "crops.json"
        f.write_text("{}")
        with mock.patch.object(crops, "_MEMO_LOCK", Spy()), mock.patch.object(crops, "_MEMO", {}), mock.patch.object(crops, "load", return_value={"e1": {"img": "a.png"}}):
            self.assertEqual(crops.record_now(f), {"e1": {"img": "a.png"}})
            self.assertEqual(crops.extraction_of("a.png", f), "e1")
        self.assertGreaterEqual(len(held), 3)


class Scripts(unittest.TestCase):
    def test_every_ledger_module_and_command_a_script_names_exists(self):
        import importlib
        from ledger.__main__ import COMMANDS
        for sh in (ROOT / "scripts").glob("*.sh"):
            text = sh.read_text()
            with self.subTest(script=sh.name):
                for cmd in re.findall(r"python -m ledger (\w+)", text):
                    self.assertIn(cmd, COMMANDS)
                for mod, names in re.findall(r"from (ledger[\w.]*) import ([\w, ]+)", text):
                    m = importlib.import_module(mod)
                    for n in [x.strip() for x in names.split(",")]:
                        self.assertTrue(hasattr(m, n) or importlib.util.find_spec(f"{mod}.{n}"), f"{mod}.{n}")
                for path in re.findall(r"(ledger/[\w/]+\.py)", text):
                    self.assertTrue((ROOT / path).exists(), path)


if __name__ == "__main__":
    unittest.main()
