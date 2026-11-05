"""The trust findings closed on branch `trust` (claims/findings.jsonl F11, F14, F16, F18, F20, F21): each class holds
the tests that fail on the code before its fix."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger.core import store

PERSON = "Kenny Geiler"
AGENT = "Claude Code, for Kenny Geiler to confirm"  # the 12 accepts on blocks in decisions/decisions.jsonl are by this name


def _exc(eid="xbrl_reconcile|ZZB|revenue|FY2024|None", sev="block", h="h1", ticker="ZZB", field="revenue", period="FY2024"):
    return {"exception_id": eid, "rule_id": eid.split("|")[0], "severity": sev, "ticker": ticker, "field": field, "period": period, "subject": None, "message": "m", "input_hash": h}


def _dec(eid, by, kind="accept", h="h1", value=None, at="2026-11-01T00:00:00+00:00", **kw):
    return {"decision_id": by[:3] + at, "exception_id": eid, "kind": kind, "value": value, "reason": kw.pop("reason", "a reason"), "reviewer": by,
            "decided_at": at, "input_hash": h, "supersedes": None, **kw}


class DecisionAuthors(unittest.TestCase):
    """F14: a decision by an agent or "to confirm" closed a block finding; now it is Proposed until a person decides."""

    def setUp(self):
        from ledger.review import review
        self.review = review
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        p = mock.patch.object(review, "LOG", self.tmp / "decisions.jsonl")
        p.start()
        self.addCleanup(p.stop)

    def test_a_run_decision_never_closes_a_block_and_is_proposed(self):
        e = _exc()
        ds = [_dec(e["exception_id"], AGENT)]
        self.assertEqual([x["exception_id"] for x in self.review.open_items([e], ds)], [e["exception_id"]])  # still open: G4 fails on it
        self.assertEqual([(x["exception_id"], x["decision"]["reviewer"]) for x in self.review.proposed([e], ds)], [(e["exception_id"], AGENT)])
        self.assertEqual(self.review.open_items([e], [_dec(e["exception_id"], PERSON)]), [])  # a person's decision closes it
        self.assertEqual(self.review.proposed([e], [_dec(e["exception_id"], PERSON)]), [])
        self.assertEqual(self.review.open_items([e], [_dec(e["exception_id"], PERSON, author_kind="run")]), [e])  # author_kind decides when present
        self.assertEqual(self.review.open_items([e], [_dec(e["exception_id"], PERSON, reason="accepted, to confirm")]), [e])  # the old rule's words

    def test_a_run_decision_on_a_warning_still_closes_it(self):
        w = _exc(sev="warn")
        self.assertEqual(self.review.open_items([w], [_dec(w["exception_id"], AGENT)]), [])
        self.assertEqual(self.review.proposed([w], [_dec(w["exception_id"], AGENT)]), [])

    def test_a_run_decision_never_supersedes_a_persons_on_the_same_input(self):
        e = _exc()
        ds = [_dec(e["exception_id"], PERSON, kind="reject"), _dec(e["exception_id"], AGENT, kind="accept", at="2026-11-02T00:00:00+00:00")]
        self.assertEqual(self.review.latest(ds)[e["exception_id"]]["reviewer"], PERSON)
        self.assertEqual(self.review.open_items([e], ds), [])

    def test_a_run_override_on_a_block_changes_no_released_value(self):
        e = _exc()
        v = {"ticker": "ZZB", "field": "revenue", "period": "FY2024", "value": 5}
        self.assertEqual(self.review.apply([v], [e], [_dec(e["exception_id"], AGENT, kind="override", value=9)])[0]["value"], 5)
        self.assertEqual(self.review.apply([v], [e], [_dec(e["exception_id"], PERSON, kind="override", value=9)])[0]["value"], 9)

    def test_every_new_decision_records_its_author_and_kind(self):
        e = _exc()
        with self.assertRaises(ValueError):
            self.review.decide(e, "accept", "why", "")  # no author
        with self.assertRaises(ValueError):
            self.review.decide(e, "accept", "why", "Somebody Else")  # a person's decision by a name off config.PEOPLE
        self.assertFalse(self.review.LOG.exists())
        d = self.review.decide(e, "accept", "why", PERSON)
        r = self.review.decide(e, "accept", "why", "mapper agent", author_kind="run")
        lines = [json.loads(l) for l in self.review.LOG.read_text().splitlines()]
        self.assertEqual([(l["reviewer"], l["author_kind"]) for l in lines], [(PERSON, "person"), ("mapper agent", "run")])
        self.assertEqual((d["author_kind"], r["author_kind"]), ("person", "run"))
        self.assertEqual(self.review.open_items([e], self.review.decisions()), [])  # the person's stands; the run's is not newer than it

    def test_the_cli_records_a_person_or_a_run(self):
        from ledger.cli import review as cli
        e = _exc()
        con = store.init(":memory:")
        store.write(con, "exceptions", [e])
        with mock.patch.object(cli.store, "init", return_value=con), mock.patch.object(cli, "decide", wraps=self.review.decide) as dec:
            self.assertEqual(cli.main(["decide", e["exception_id"], "accept", "--reason", "r", "--by", "Somebody Else", "--ticker", "ZZB"]), 1)
            self.assertEqual(cli.main(["decide", e["exception_id"], "accept", "--reason", "r", "--by", "an agent", "--run", "--ticker", "ZZB"]), 0)
        self.assertEqual(dec.call_args.kwargs["author_kind"], "run")
        self.assertEqual([json.loads(l)["author_kind"] for l in self.review.LOG.read_text().splitlines()], ["run"])

    def test_g4_and_g6_both_name_a_proposed_block(self):
        from ledger.release.release import gates
        e = _exc()
        ds = [_dec(e["exception_id"], AGENT)]
        g = gates([], self.review.open_items([e], ds), {"values": []}, tickers=["ZZB"], proposed=self.review.proposed([e], ds))
        self.assertEqual(g["G4"]["ZZB"], [e["exception_id"]])
        self.assertEqual(g["G6"]["ZZB"], [f"decisions|ZZB|{e['exception_id']}"])
        g = gates([], self.review.open_items([e], [_dec(e["exception_id"], PERSON)]), {"values": []}, tickers=["ZZB"], proposed=[])
        self.assertEqual((g["G4"]["ZZB"], g["G6"]["ZZB"]), ([], []))

    def test_proof_and_reconcile_read_it_proposed(self):
        from ledger.checks import proof
        from ledger.core.states import row
        from ledger.review import workbench
        from ledger.web import cards
        e = _exc()
        con = store.init(":memory:")
        store.write(con, "exceptions", [e])
        fake = [{"ticker": "ZZB", "name": "Block Co"}]
        with mock.patch.object(proof, "tracked", return_value=fake), mock.patch.object(proof, "asset_types", return_value={}), \
                mock.patch.object(proof, "decisions", return_value=[_dec(e["exception_id"], AGENT)]):
            co = proof.company(con, "ZZB", idx={}, defs={}, rset=([], None))
        it = co["stages"]["release"]["all"][0]
        self.assertEqual(row(it["state"], it["by"]), "wait")  # Proposed, not Blocks release, and never gone (the old code dropped it)
        self.assertEqual(cards._words(it, "", {})["text"], "Proposed decision. Review in Reconcile.")
        q = {"kind": "blocked", "ticker": "ZZB", "detail": {"rule": "xbrl_reconcile", "message": "m"}, "resolution": None, "proposed": {"kind": "accept", "reviewer": AGENT}}
        st = workbench._state(con, q, {})
        self.assertEqual(row(st["state"], st["by"]), "wait")
        st = workbench._state(con, {**q, "proposed": None}, {})
        self.assertEqual(row(st["state"], st["by"]), "blocked")


if __name__ == "__main__":
    unittest.main()
