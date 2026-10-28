"""Restatements (standard practice: keep both versions, release one declared basis, flag it).

For each field, a restatement is a filing that changes a number an earlier filing reported for the same period by more
than 1% (and more than rounding). Each restatement starts a new generation of that field. A value's generation is the
number of the field's restatements filed on or before its own filing. Generation 0 is as first reported; anything
later is restated. A quarter built from inputs of different generations has no single basis and ships blank.
"""


def restatement_dates(extractions: list[dict]) -> dict[str, list[str]]:
    by = {}
    for e in extractions:
        by.setdefault((e["field"], e["period_start"], e["period_end"]), []).append(e)
    dates = {}
    for (field, _, _), es in by.items():
        es = sorted(es, key=lambda e: e["filed"])
        first = es[0]["value"]
        for e in es[1:]:
            if abs(e["value"] - first) > max(max(x["scale"] for x in es) // 2, abs(first) // 100):
                dates.setdefault(field, set()).add(e["filed"])
    return {f: sorted(d) for f, d in dates.items()}


def generation(e: dict, dates: dict[str, list[str]]) -> int:
    return sum(d <= e["filed"] for d in dates.get(e["field"], []))


def first_reported(extractions: list[dict]) -> list[dict]:
    """Only the first-filed value for each field and period: the as-first-reported view."""
    out = {}
    for e in sorted(extractions, key=lambda e: e["filed"]):
        out.setdefault((e["field"], e["period_start"], e["period_end"]), e)
    return list(out.values())
