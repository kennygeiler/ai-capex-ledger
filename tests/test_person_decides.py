"""F-TR1: a block a run or an agent decided reads Proposed, and a person could make it theirs only with `ledger review …
decide --as person`. Reconcile now carries Confirm and Overturn on the proposed decision, posting to /api/decision,
which writes through review.decide with author_kind person and a name on config.PEOPLE; the controls are marked as
writes, so the read-only copy hides them."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger.core import store
from ledger.review import review
from tests.test_trust import AGENT, _dec, _exc


class PersonDecides(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        self.log = d / "decisions.jsonl"
        m = mock.patch.object(review, "LOG", self.log)
        m.start()
        self.addCleanup(m.stop)
        self.e = _exc()
        self.p = _dec(self.e["exception_id"], AGENT, kind="accept")
        self.log.write_text(json.dumps(self.p) + "\n")

    def test_confirm_writes_the_proposal_as_the_persons_and_closes_the_block(self):
        self.assertEqual(review.open_items([self.e], review.decisions()), [self.e])  # proposed: still open under G4
        d = review.person_decides(self.e, "confirm", "checked the filing", "Kenny Geiler", decision_id=self.p["decision_id"])
        self.assertEqual((d["kind"], d["author_kind"], d["reviewer"], d["input_hash"]), ("accept", "person", "Kenny Geiler", "h1"))
        self.assertEqual(review.open_items([self.e], review.decisions()), [])
        self.assertEqual(review.proposed([self.e], review.decisions()), [])

    def test_overturn_writes_another_kind(self):
        d = review.person_decides(self.e, "overturn", "the value is wrong", "Kenny Geiler", decision_id=self.p["decision_id"], kind="reject")
        self.assertEqual((d["kind"], d["author_kind"]), ("reject", "person"))
        with self.assertRaises(ValueError):  # the same kind is a confirm, not an overturn
            review.person_decides(self.e, "overturn", "x", "Kenny Geiler", decision_id=d["decision_id"], kind="reject")

    def test_refusals_write_nothing(self):
        before = self.log.read_text()
        for kw in ({"by": "Claude"}, {"by": "Someone Else"}, {"action": "approve"}, {"decision_id": "not-the-one"}):
            args = {"action": "confirm", "reason": "r", "by": "Kenny Geiler", "decision_id": self.p["decision_id"], **kw}
            with self.assertRaises(ValueError):
                review.person_decides(self.e, args.pop("action"), args.pop("reason"), args.pop("by"), **args)
        with self.assertRaises(review.Stale):
            review.person_decides(self.e, "confirm", "r", "Kenny Geiler", decision_id="not-the-one")
        with self.assertRaises(ValueError):  # a warn finding is not decided here
            review.person_decides({**self.e, "severity": "warn"}, "confirm", "r", "Kenny Geiler", decision_id=self.p["decision_id"])
        with self.assertRaises(ValueError):  # the finding changed: the proposal is on another input hash, none stands
            review.person_decides({**self.e, "input_hash": "h2"}, "confirm", "r", "Kenny Geiler", decision_id=self.p["decision_id"])
        self.assertEqual(self.log.read_text(), before)


class Route(unittest.TestCase):
    """POST /api/decision: the server reads the exception from the database; 400 on a refusal, 409 on a stale page."""

    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        self.db = d / "ledger.duckdb"
        con = store.init(self.db)
        self.e = _exc()
        store.write(con, "exceptions", [self.e])
        con.close()
        self.log = d / "decisions.jsonl"
        self.p = _dec(self.e["exception_id"], AGENT, kind="accept")
        self.log.write_text(json.dumps(self.p) + "\n")
        for target, val in (("ledger.review.review.LOG", self.log), ("ledger.core.store.DEFAULT_DB", self.db)):
            m = mock.patch(target, val)
            m.start()
            self.addCleanup(m.stop)

    def _post(self, body):
        from ledger.web import app
        return app.decide_route(body)

    def test_the_route_writes_a_persons_decision(self):
        out = self._post({"exception_id": self.e["exception_id"], "input_hash": "h1", "decision_id": self.p["decision_id"], "action": "confirm", "reason": "checked", "by": "Kenny Geiler"})
        self.assertEqual((out["author_kind"], out["kind"]), ("person", "accept"))
        lines = [json.loads(l) for l in self.log.read_text().splitlines()]
        self.assertEqual([l["author_kind"] for l in lines[1:]], ["person"])

    def test_a_changed_finding_or_a_name_off_the_list_is_refused(self):
        from ledger.review.review import Stale
        with self.assertRaises(Stale):  # the page showed another input hash: the finding changed since
            self._post({"exception_id": self.e["exception_id"], "input_hash": "h0", "decision_id": self.p["decision_id"], "action": "confirm", "reason": "r", "by": "Kenny Geiler"})
        with self.assertRaises(ValueError):
            self._post({"exception_id": self.e["exception_id"], "input_hash": "h1", "decision_id": self.p["decision_id"], "action": "confirm", "reason": "r", "by": "Gemini"})
        with self.assertRaises(KeyError):
            self._post({"exception_id": "nope", "input_hash": "h1", "decision_id": self.p["decision_id"], "action": "confirm", "reason": "r", "by": "Kenny Geiler"})
        self.assertEqual(len(self.log.read_text().splitlines()), 1)


class Page(unittest.TestCase):
    def test_reconcile_carries_confirm_and_overturn_as_writes(self):
        js = (store.ROOT / "ledger" / "web" / "pages" / "reconcile.js").read_text()
        i = js.index("function proposedDecision(")
        block = js[i:js.index("\n  }\n", i)]
        self.assertIn("'/api/decision'", block)
        self.assertIn("needsMe(", block)  # disabled for a name off the signer list, marked data-write (hidden on the read-only copy)
        self.assertIn("'Confirm'", block)
        self.assertIn("'Overturn'", block)
        app = (store.ROOT / "ledger" / "web" / "app.py").read_text()
        self.assertIn('if u.path == "/api/decision":', app)

    def test_the_read_only_copy_refuses_the_route(self):
        # every POST is refused on the read-only copy before any route runs (app.do_POST): /api/decision is one more POST
        app = (store.ROOT / "ledger" / "web" / "app.py").read_text()
        self.assertLess(app.index("def do_POST"), app.index('if u.path == "/api/decision":'))


if __name__ == "__main__":
    unittest.main()
