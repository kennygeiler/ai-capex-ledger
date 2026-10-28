"""T60: quarterly values from extractions, each labelled against the XBRL reference.

agree         within the coarser rounding of the two sources
no_reference  XBRL has no value for that quarter
unresolved    they differ; the xbrl_reconcile rule raises it for review
"""
import hashlib
import json

from .config import MVP_FIELDS, MVP_QUARTERS
from .derive import quarters


def _rounding(v: int) -> int:
    return 1_000_000 if v % 1_000_000 == 0 else 1_000 if v % 1_000 == 0 else 1


def values_for(ticker: str, extractions: list[dict], reference: dict, fye: str | None, docs: dict) -> list[dict]:
    """extractions: rows joined with their document's form and filed date. reference: (field, cal_q) -> value.
    docs: accession -> (sha256, parser_version), folded into each value's input hash so a reparse reopens decisions."""
    derived = quarters(extractions, fye)
    scale = {x["extraction_id"]: x["scale"] for x in extractions}
    out = []
    for f in MVP_FIELDS:
        for cq in MVP_QUARTERS:
            d, r = derived[f].get(cq), reference.get((f, cq))
            if d is None:
                continue  # a gap: the coverage rule reports it
            tol = max([scale[i] for i in d["extraction_ids"]] + ([_rounding(r)] if r is not None else [])) // 2
            label = "no_reference" if r is None else "agree" if abs(d["value"] - r) <= tol else "unresolved"
            sources = sorted({docs[i.split("|")[0]] for i in d["extraction_ids"]})
            h = hashlib.sha256(json.dumps([d["value"], d["method"], d["extraction_ids"], r, sources]).encode()).hexdigest()[:16]
            out.append({"ticker": ticker, "field": f, "cal_q": cq, "fiscal_period": d["fiscal_period"], "value": d["value"],
                        "source": "agent", "method": d["method"], "label": label,
                        "extraction_ids": ",".join(d["extraction_ids"]), "input_hash": h})
    return out
