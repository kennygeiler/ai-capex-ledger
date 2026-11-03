"""LEDGER_OFFLINE=1: the SEC client serves the data/raw cache whatever its age and refuses anything uncached, without a
contact and without touching the network (ledger/ingest/edgar.py)."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from ledger.ingest import edgar


class Offline(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"LEDGER_OFFLINE": "1", "SEC_USER_AGENT": ""})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.net = mock.patch.object(edgar.urllib.request, "urlopen", side_effect=AssertionError("offline mode reached the network"))
        self.net.start()
        self.addCleanup(self.net.stop)

    def test_an_uncached_url_is_refused_without_reaching_the_network(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(edgar.Offline):
                edgar._cached("https://www.sec.gov/Archives/never-cached.json", Path(d) / "never-cached.json", False, 24)
            with self.assertRaises(edgar.Offline):
                edgar._get("https://www.sec.gov/Archives/never-cached.json")

    def test_a_cached_file_is_served_whatever_its_age(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "old.json"
            p.write_text('{"a": 1}')
            p.with_suffix(".meta.json").write_text(json.dumps({"url": "u", "fetched_at": "2020-01-01T00:00:00+00:00", "bytes": 8}))
            old = time.time() - 400 * 24 * 3600
            os.utime(p, (old, old))
            body, meta = edgar._cached("u", p, False, 24)
            self.assertEqual(body, b'{"a": 1}')
            self.assertEqual(meta["cache"], "hit")
            body, _ = edgar._cached("u", p, True, 24)  # refresh asks for the network; offline still serves the cache
            self.assertEqual(body, b'{"a": 1}')

    def test_online_is_the_default_outside_tests(self):
        with mock.patch.dict(os.environ, {"LEDGER_OFFLINE": "0"}):
            self.assertFalse(edgar.offline())
        self.assertTrue(edgar.offline())

    def test_the_pdf_and_edgartools_paths_refuse_too(self):
        from ledger.ingest import texts
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(edgar.Offline):
                texts._pdf_text("https://example.com/never.pdf", Path(d) / "never.txt")
        with self.assertRaises(edgar.Offline):
            texts._identity()

    def test_watch_refuses_before_any_fetch(self):
        """ledger watch writes checked_at=now: offline it would stamp a cached submissions file as a fresh check."""
        from ledger.cli import watch
        out = Path("/nonexistent/watch.json")
        with mock.patch.object(watch, "list_filings", side_effect=AssertionError("fetched")) as lf, mock.patch.object(watch, "OUT", out):
            with self.assertRaises(SystemExit):
                watch.main(["--ticker", "MSFT"])
            lf.assert_not_called()
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
