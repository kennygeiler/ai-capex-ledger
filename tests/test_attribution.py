"""The attribution contract: revenue exposure uses segment_revenue facts, committed rows use commitment facts, and code
recomputes every amount."""
import unittest
from unittest import mock

from ledger import attribution as A

PACK = {
    "value:X|capex|FY2025": {"kind": "value", "field": "capex", "period": "FY2025", "value": 1_000},
    "value:X|revenue|FY2025": {"kind": "value", "field": "revenue", "period": "FY2025", "value": 10_000},
    "fact:X|segment_revenue|Data Center|FY2025": {"kind": "fact", "field": "segment_revenue", "dimension": "Data Center", "period": "FY2025", "value": 8_000},
    "fact:X|segment_capex|HPC|FY2025": {"kind": "fact", "field": "segment_capex", "dimension": "HPC", "period": "FY2025", "value": 600},
    "fact:X|purchase_commitments|total|FY2025": {"kind": "fact", "field": "purchase_commitments", "dimension": "total", "period": "FY2025", "value": 5_000},
}


def row(**kw):
    base = {"field": "capex", "period": "FY2025", "kind": "actual", "method": "segment", "ai_amount": 600, "ai_share": 0.6,
            "inputs": [{"id": "fact:X|segment_capex|HPC|FY2025", "value": 600}], "basis": "b", "confidence": 0.8}
    return {**base, **kw}


def obj(*rows, none=()):
    return {"ticker": "X", "prompt_version": "attribution@v2", "model": "neocloud@v2", "rows": list(rows), "none_found": list(none)}


class Contract(unittest.TestCase):
    def setUp(self):
        self.p = [mock.patch.object(A, "prompt_versions", lambda: ("attribution@v1", "attribution@v2")), mock.patch.object(A, "model_for", lambda t, o=None: "neocloud@v2")]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()

    def test_capex_segment_still_works(self):
        A.validate_output(obj(row()), "X", PACK)

    def test_revenue_segment_uses_segment_revenue(self):
        A.validate_output(obj(row(field="revenue", ai_amount=8_000, ai_share=0.8, inputs=[{"id": "fact:X|segment_revenue|Data Center|FY2025", "value": 8_000}])), "X", PACK)
        with self.assertRaises(A.Invalid) as cm:
            A.validate_output(obj(row(field="revenue", ai_amount=600, ai_share=0.06)), "X", PACK)
        self.assertIn("segment_revenue", cm.exception.reason)
        with self.assertRaises(A.Invalid):  # revenue facts never feed capex
            A.validate_output(obj(row(ai_amount=8_000, ai_share=None, inputs=[{"id": "fact:X|segment_revenue|Data Center|FY2025", "value": 8_000}])), "X", PACK)

    def test_committed_uses_commitment_facts(self):
        A.validate_output(obj(row(kind="committed", method="commitment", ai_amount=5_000, ai_share=None, inputs=[{"id": "fact:X|purchase_commitments|total|FY2025", "value": 5_000}])), "X", PACK)
        with self.assertRaises(A.Invalid):  # wrong amount
            A.validate_output(obj(row(kind="committed", method="commitment", ai_amount=4_000, ai_share=None, inputs=[{"id": "fact:X|purchase_commitments|total|FY2025", "value": 5_000}])), "X", PACK)
        with self.assertRaises(A.Invalid):  # commitment method needs kind committed
            A.validate_output(obj(row(method="commitment", ai_amount=5_000, ai_share=None, inputs=[{"id": "fact:X|purchase_commitments|total|FY2025", "value": 5_000}])), "X", PACK)
        with self.assertRaises(A.Invalid):  # a committed row cannot use segment capex
            A.validate_output(obj(row(kind="committed")), "X", PACK)

    def test_none_found_accepts_revenue(self):
        A.validate_output(obj(none=[{"field": "revenue", "reason": "a buyer"}]), "X", PACK)
        with self.assertRaises(A.Invalid):
            A.validate_output(obj(none=[{"field": "sales", "reason": "x"}]), "X", PACK)
