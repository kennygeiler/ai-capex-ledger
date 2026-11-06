"""F15, F1: a resolution closes only the exact queue item, key and input hash, it was written for, on every page.
Reconcile matched the hash; Proof, the Release counts, the read API's status and the taxonomy rows read the latest
resolution by row and kept counting it after the item changed, and two items on one row shared one decision.
`resolutions.index` is the one reader now; these tests fail on the code before it."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from ledger.core import store
from ledger.review import resolutions
from ledger.review.resolutions import key_for


def _line(key, h, state="accept", at="2026-11-05T00:00:00+00:00"):
    return {"id": f"x{abs(hash((key, h))) % 10**8}", "key": key, "hash": h, "state": state, "reason": "checked", "by": "Kenny Geiler",
            "author_kind": "person", "at": at}


class Index(unittest.TestCase):
    """resolutions.index on synthetic queue items: the matching rule, apart from any database."""
    T = "ZZZ"
    CHANGED = key_for("fact_changed", T, "segment_capex", "FY2024", "Cloud")
    DIFFERS = key_for("fact_differs", T, "segment_capex", "FY2024", "Cloud")

    def _index(self, lines, queue):
        with mock.patch("ledger.review.queue.queue_items", return_value={"queue": queue}):
            return resolutions.index(None, None, lines)

    def test_a_resolution_on_a_changed_item_closes_nothing(self):
        lines = [_line(self.DIFFERS, "h1")]
        self.assertIn(("facts", self.T, "segment_capex", "Cloud", "FY2024", ""), self._index(lines, [{"key": self.DIFFERS, "hash": "h1"}]))
        self.assertEqual(self._index(lines, [{"key": self.DIFFERS, "hash": "h2"}]), {})

    def test_two_items_on_one_row_need_a_decision_each(self):
        # accepting the change since the release does not close the cell that still differs from SEC data
        lines = [_line(self.CHANGED, "c1")]
        self.assertEqual(self._index(lines, [{"key": self.CHANGED, "hash": "c1"}, {"key": self.DIFFERS, "hash": "d1"}]), {})
        both = self._index(lines + [_line(self.DIFFERS, "d1")], [{"key": self.CHANGED, "hash": "c1"}, {"key": self.DIFFERS, "hash": "d1"}])
        self.assertEqual(both[("facts", self.T, "segment_capex", "Cloud", "FY2024", "")]["status"], "accepted")

    def test_a_resolution_whose_item_is_gone_closes_nothing(self):
        self.assertEqual(self._index([_line(self.DIFFERS, "h1")], []), {})

    def test_no_live_resolution_builds_no_queue(self):
        with mock.patch("ledger.review.queue.queue_items", side_effect=AssertionError("built")):
            self.assertEqual(resolutions.index(None, None, []), {})

    def test_a_queue_that_cannot_be_built_stops_the_page_never_reopens_quietly(self):
        # review of F15: an empty match would reopen every decision on the page while Reconcile still counts them
        with mock.patch("ledger.review.queue.queue_items", side_effect=OSError("reports/stage3-faults.json")):
            with self.assertRaises(resolutions.Unmatched) as c:
                resolutions.index(None, None, [_line(self.DIFFERS, "h1")])
        self.assertIn("Resolutions not matched · queue not built", str(c.exception))
        src = (store.ROOT / "ledger" / "web" / "app.py").read_text()
        self.assertIn("except resolutions.Unmatched as e:", src[src.index("def _guard"):])  # a 503 on every page route

    def test_a_fix_on_one_item_does_not_speak_for_an_undecided_sibling(self):
        lines = [_line(self.CHANGED, "c1", state="fix")]
        self.assertEqual(self._index(lines, [{"key": self.CHANGED, "hash": "c1"}, {"key": self.DIFFERS, "hash": "d1"}]), {})
        self.assertEqual(self._index(lines, [{"key": self.CHANGED, "hash": "c1"}])[("facts", self.T, "segment_capex", "Cloud", "FY2024", "")]["status"], "fix_pending")

    def test_the_queue_is_built_once_per_stamp(self):
        from ledger.review import queue
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True) if store.DEFAULT_DB.exists() else None
        if con is None:
            self.skipTest("needs the working database")
        self.addCleanup(con.close)
        queue._ITEMS.clear()
        with mock.patch("ledger.review.queue.queue_items", return_value={"queue": [{"key": self.DIFFERS, "hash": "h1"}]}) as q:
            for _ in range(3):
                resolutions.index(con, None, [_line(self.DIFFERS, "h1")])
        self.assertEqual(q.call_count, 1)
        queue._ITEMS.clear()

    def test_the_queue_lives_outside_the_web_app(self):
        src = (store.ROOT / "ledger" / "review" / "resolutions.py").read_text()
        self.assertNotIn("web.app", src)  # review of F15: resolutions reads the queue from ledger/review/queue.py

    def test_no_page_reads_the_unmatched_index(self):
        # every reader outside Reconcile goes through index(); by_row() with no items is the matching rule's inside only
        import re
        for f in sorted((store.ROOT / "ledger").rglob("*.py")):
            if f.name == "resolutions.py":
                continue
            for m in re.finditer(r"by_row\(([^)]*)\)", f.read_text()):
                self.assertIn("items=", m.group(1), f"{f.relative_to(store.ROOT)} reads resolutions.by_row without the queue's items")


@unittest.skipUnless(store.DEFAULT_DB.exists(), "needs the working database")
class Surfaces(unittest.TestCase):
    """On the working database: a person's accept on an APLD finding counts on Proof, the read API and Reconcile while
    its hash is the item's, and on none of them once the item changed (F1: Proof used to keep it closed)."""

    def setUp(self):
        from ledger.web import app
        self.app = app
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        self.log = d / "resolutions.jsonl"
        m = mock.patch.object(resolutions, "LOG", self.log)
        m.start()
        self.addCleanup(m.stop)
        app._FLOW.clear()
        self.addCleanup(app._FLOW.clear)
        queue = app._flow("APLD")["queue"]
        self.tie = next(q for q in queue if q["kind"] == "finding_unconfirmed" and (q["detail"] or {}).get("rule") == "segment_capex_tie")
        self.jump = next(q for q in queue if q["kind"] == "finding_unconfirmed" and (q["detail"] or {}).get("kind") == "jump")

    def _write(self, *pairs):
        self.log.write_text("".join(json.dumps(_line(q["key"], h)) + "\n" for q, h in pairs))
        self.app._FLOW.clear()

    def _proof_item(self, con, q):
        from ledger.checks import proof
        d = q["detail"]
        c = proof.company(con, "APLD")
        want = f"{d['rule']}: {d['field']} {d['period']} ({d['subject']})"
        return next(i for i in c["stages"]["facts"]["all"] if i["what"] == want)

    def _api_status(self, con, q):
        from ledger.web import api
        d = q["detail"]
        return next(r["status"] for r in api.fetch(con, "values") if r["ticker"] == "APLD" and r["field"] == d["field"] and r["period"] == d["period"])

    def _reconcile(self, con, q):
        from ledger.review import workbench
        return next(r for r in workbench.items(con, self.app._flow("APLD"))["rows"] if r["key"] == q["key"])

    def test_current_hash_closes_a_changed_one_reopens_everywhere(self):
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        self.addCleanup(con.close)
        self._write((self.tie, self.tie["hash"]), (self.jump, self.jump["hash"]))
        self.assertEqual(self._proof_item(con, self.tie)["state"], "explained")
        self.assertFalse(self._reconcile(con, self.tie)["open"])
        self.assertEqual(self._api_status(con, self.jump), "accepted")
        self._write((self.tie, "000000000000"), (self.jump, "000000000000"))  # the items changed since the decision
        self.assertEqual(self._proof_item(con, self.tie)["state"], "open")
        self.assertTrue(self._reconcile(con, self.tie)["open"])
        self.assertEqual(self._api_status(con, self.jump), "")


if __name__ == "__main__":
    unittest.main()
