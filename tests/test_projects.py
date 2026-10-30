"""The projects reader's contract: quotes must be in the passage, sizes and dates in range; latest keeps the newest mention."""
import unittest
from unittest import mock

from ledger import projects

PS = {"p01": "Hyperion, our data center in Louisiana, will scale to 2 GW by 2030. We expect to spend $10 billion on it.",
      "p02": "Capital expenditures were $39 billion in 2024."}
GOOD = {"name": "Hyperion", "kind": "data_center", "status": "under_construction", "location": "Louisiana", "counterparty": None,
        "amount_low": 10_000_000_000, "amount_high": 10_000_000_000, "capacity_mw": 2000, "gpus": None, "announced": None, "in_service": "2030",
        "quote": "Hyperion, our data center in Louisiana, will scale to 2 GW by 2030.", "passage": "p01", "confidence": 0.9}


def _obj(*ps):
    return {"accession": "t1", "prompt_version": "projects@v1", "projects": list(ps)}


class Contract(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.object(projects, "prompt_versions", lambda: ("projects@v1",))
        self.p.start()

    def tearDown(self):
        self.p.stop()

    def test_good(self):
        projects.validate_output(_obj(GOOD), "t1", PS)
        projects.validate_output(_obj(), "t1", PS)

    def test_quote_must_be_in_passage(self):
        with self.assertRaises(projects.Invalid) as cm:
            projects.validate_output(_obj({**GOOD, "quote": "Hyperion will scale to 3 GW by 2030, we said."}), "t1", PS)
        self.assertIn("verbatim", str(cm.exception.reason))
        with self.assertRaises(projects.Invalid):
            projects.validate_output(_obj({**GOOD, "passage": "p09"}), "t1", PS)

    def test_ranges(self):
        for bad in ({"amount_low": 5, "amount_high": 1}, {"amount_low": 5, "amount_high": None}, {"capacity_mw": -1}, {"in_service": "soon"}, {"kind": "office"}, {"status": "maybe"}, {"name": "ab"}):
            with self.assertRaises(projects.Invalid, msg=bad):
                projects.validate_output(_obj({**GOOD, **bad}), "t1", PS)

    def test_passages_need_a_project_word_and_a_size(self):
        text = "We opened a new data center campus of 300 MW in Texas this year.\n\nOur people are our greatest asset and we hired many.\n\nThe plant expansion in Ohio, announced last quarter, will cost about $2.1 billion over three years."
        self.assertEqual(len(projects.passages(text)), 2)


class Latest(unittest.TestCase):
    def test_newest_mention_wins(self):
        rows = [{"project_id": "a|0", "ticker": "META", "name": "Hyperion", "date": "2024-12-01", "status": "announced"},
                {"project_id": "b|0", "ticker": "META", "name": "hyperion", "date": "2025-07-30", "status": "under_construction"},
                {"project_id": "c|0", "ticker": "META", "name": "Prometheus", "date": "2025-07-30", "status": "announced"}]
        out = {r["name"].lower(): r for r in projects.latest(rows)}
        self.assertEqual(out["hyperion"]["status"], "under_construction")
        self.assertEqual(out["hyperion"]["mentions"], 2)
        self.assertEqual(out["prometheus"]["mentions"], 1)
