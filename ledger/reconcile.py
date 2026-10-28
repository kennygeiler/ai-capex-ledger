"""T60: quarterly values from extractions, each labelled against the XBRL reference.

agree         within the coarser rounding of the two sources
no_reference  XBRL has no value for that quarter
unresolved    they differ; the xbrl_reconcile rule raises it for review
"""
import hashlib
import json

from .basis import first_reported, generation, restatement_dates
from .config import MVP_FIELDS, MVP_QUARTERS
from .derive import quarters


def _rounding(v: int) -> int:
    return 1_000_000 if v % 1_000_000 == 0 else 1_000 if v % 1_000 == 0 else 1


def _single_basis(d, by_id, dates):
    """The derived value, or None when its inputs span restatement generations (no single basis)."""
    return d["value"] if d and len({generation(by_id[i], dates) for i in d["extraction_ids"]}) == 1 else None


def values_for(ticker: str, extractions: list[dict], reference: dict, fye: str | None, docs: dict) -> list[dict]:
    """extractions: rows joined with their document's form and filed date. reference: (field, cal_q) -> value.
    docs: accession -> (sha256, parser_version), folded into each value's input hash so a reparse reopens decisions."""
    derived, first = quarters(extractions, fye), quarters(first_reported(extractions), fye)
    by_id = {x["extraction_id"]: x for x in extractions}
    scale = {i: x["scale"] for i, x in by_id.items()}
    dates = restatement_dates(extractions)
    out = []
    for f in MVP_FIELDS:
        for cq in MVP_QUARTERS:
            d, r = derived[f].get(cq), reference.get((f, cq))
            if d is None:
                continue  # a gap: the coverage rule reports it
            gens = {generation(by_id[i], dates) for i in d["extraction_ids"]}
            basis = "mixed" if len(gens) > 1 else "restated" if gens.pop() else "as_reported"
            value = None if basis == "mixed" else d["value"]
            tol = max([scale[i] for i in d["extraction_ids"]] + ([_rounding(r)] if r is not None else [])) // 2
            label = "mixed_basis" if value is None else "no_reference" if r is None else "agree" if abs(value - r) <= tol else "unresolved"
            sources = sorted({docs[i.split("|")[0]] for i in d["extraction_ids"]})
            h = hashlib.sha256(json.dumps([d["value"], d["method"], d["extraction_ids"], r, sources]).encode()).hexdigest()[:16]
            out.append({"ticker": ticker, "field": f, "cal_q": cq, "fiscal_period": d["fiscal_period"], "value": value,
                        "source": "agent" if value is not None else "missing", "method": d["method"], "label": label, "basis": basis,
                        "first_reported": _single_basis(first[f].get(cq), by_id, dates),
                        "extraction_ids": ",".join(d["extraction_ids"]), "input_hash": h})
    return out
