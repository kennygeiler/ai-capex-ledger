"""The company's own tag as evidence for a category mapping (docs/PROOF.md, "The company's own tag").

A reported PP&E category ("Construction in progress") is mapped to a us-gaap PropertyPlantAndEquipmentByTypeAxis member
in taxonomy/asset_types.yaml. The filer's own XBRL instance often tags the same balance with a member: when it tags
exactly the member proposed, unambiguously, the mapping is checked by `mapping:filer_tag`, a twin-kind answer key (the
filer's classification, in a separate machine-readable document), and it leaves the person's queue.

Unambiguous, for one category of one company, means every one of these holds (`verdicts`):
  - every row of the category (every fiscal year extracted for it in `facts`) has its filing's instance on disk
    (data/raw/<cik>/filings/<accession>.facts.json; never fetched here);
  - no row's value is zero or missing (an empty prior-year column matches every empty member);
  - in each row's own instance exactly one member of PropertyPlantAndEquipmentGross on the row's balance date has the
    row's value (the cell's value, never the reconcile reference: the check is of the figure we carry);
  - that member is the same in every extracted year, and it is a us-gaap member.
It is a value match against the filer's own classification, not an audit of it.
Then `status` is "tagged" with that member. Anything else is a person's decision: "extension" (one company member,
consistent: nothing to compare), "ambiguous" (two members share the value), "inconsistent" (members differ by year),
"partial" (tagged in some years, not in others), "not_tagged", "zero", "not_checked" (an instance not on disk, or no
facts to read). `verified(entry, verdict)` is the one test the pages, the taxonomy rows, the gate and the walk read.

Nothing here is written anywhere: the verdict is recomputed from disk on every read, and the trail item carries what it
rested on (`ref.filer_tag`: the member and every reading, accession, balance date, value) so T80's walk
(status.evidence_gap) can recompute it and refuse a forged or stale one."""
from __future__ import annotations

import json
import math
from pathlib import Path

CONCEPT = "PropertyPlantAndEquipmentGross"
FILER_TAG = "mapping:filer_tag"  # the `by` of a mapping the company's own tag checks
STATUSES = ("tagged", "extension", "ambiguous", "inconsistent", "partial", "not_tagged", "zero", "not_checked")


def _rows(con, tickers):
    cur = con.execute("""select f.ticker, f.dimension, f.period, f.period_end, f.value, f.accession, d.cik
                         from facts f left join documents d on d.accession = f.accession
                         where f.field = 'ppe_category' and f.ticker in (select unnest(?)) order by f.ticker, f.dimension, f.period""", [list(tickers)])
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


_PARSED: dict = {}  # path -> ((mtime_ns, size), parsed): one parse per instance file version, across requests


def whole(value) -> int | None:
    """A figure as a whole number, or None when it is missing, not a number, or not finite (NaN, inf)."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return round(f) if math.isfinite(f) else None


def instance(cik, accession, cache: dict | None = None) -> dict | None:
    """The distilled instance of a filing as {(concept, member, date): value}, or None when it is not on disk. Parsed
    once per file version: memoised by path, modification time and size, so an instance that changes on disk is read
    again and never served stale."""
    from ..ingest.edgar import RAW
    cache = {} if cache is None else cache
    key = (cik, accession)
    if key not in cache:
        try:
            p = Path(RAW) / f"{int(cik):010d}" / "filings" / f"{accession}.facts.json"
            st = p.stat()
            stamp = (st.st_mtime_ns, st.st_size)
            hit = _PARSED.get(str(p))
            if not hit or hit[0] != stamp:
                hit = (stamp, {tuple(k.split("\t")): v for k, v in json.loads(p.read_text()).items()})
                _PARSED[str(p)] = hit
            cache[key] = hit[1]
        except Exception:  # not on disk, unreadable, or a cik that is not a number
            cache[key] = None
    return cache[key]


def members_at(inst: dict, period_end, value) -> list[str]:
    """The members whose PropertyPlantAndEquipmentGross on `period_end` equals `value`, sorted. A total (no member) never
    counts; a zero, missing, non-numeric or non-finite value matches nothing."""
    v = whole(value)
    if not v:
        return []
    return sorted({m for (c, m, d), x in inst.items() if c == CONCEPT and m and d == str(period_end) and whole(x) == v})


def verdicts(con, tickers) -> dict:
    """{(ticker, reported_name): verdict} for every ppe_category of `tickers` (verdicts_ok without the flag). A verdict:
    {"status": one of STATUSES, "member": the member when one is consistent (tagged, extension) or the members found,
     "readings": [{"period", "period_end", "accession", "value", "members"}] in year order, "why": a short phrase}.
    A query that fails gives {} (every category not checked; never "verified")."""
    return verdicts_ok(con, tickers)[0]


def verdicts_ok(con, tickers) -> tuple[dict, bool]:
    """(verdicts, ok): ok is False when the facts could not be read, so a caller says "not read", never "0 verified"."""
    try:
        rows = _rows(con, tickers)
    except Exception:
        return {}, False
    by: dict = {}
    for r in rows:
        by.setdefault((r["ticker"], r["dimension"]), []).append(r)
    cache: dict = {}
    out = {}
    for key, rs in by.items():
        readings, missing, zero = [], False, False
        for r in rs:
            inst = instance(r["cik"], r["accession"], cache) if r["cik"] is not None and r["accession"] else None
            if inst is None:
                missing = True
            v = whole(r["value"])
            if not v:  # zero, missing, not a number, or not finite
                zero = True
            readings.append({"period": r["period"], "period_end": str(r["period_end"]) if r["period_end"] is not None else None, "accession": r["accession"],
                             "value": v, "members": members_at(inst or {}, r["period_end"], r["value"]) if inst is not None else None})
        out[key] = judge(readings, missing, zero)
    return out, True


def judge(readings: list[dict], missing: bool = False, zero: bool = False) -> dict:
    """The verdict from the readings (see the module doc). Order matters: what was not read is never "not tagged"."""
    found = sorted({m for r in readings for m in (r.get("members") or [])})
    base = {"readings": readings, "member": None}
    if not readings or missing:
        return {**base, "status": "not_checked", "member": found or None, "why": "instance not on file" if readings else "no figures"}
    if zero:
        return {**base, "status": "zero", "member": found or None, "why": "a zero, missing or non-numeric value"}
    if any(len(r["members"]) > 1 for r in readings):
        return {**base, "status": "ambiguous", "member": found, "why": "two or more members share the value"}
    if not found:
        return {**base, "status": "not_tagged", "why": "no member has the value"}
    if len(found) > 1:
        return {**base, "status": "inconsistent", "member": found, "why": "members differ by year"}
    if any(not r["members"] for r in readings):
        return {**base, "status": "partial", "member": found[0], "why": "not tagged in every extracted year"}
    m = found[0]
    return {**base, "status": "tagged" if m.startswith("us-gaap:") else "extension", "member": m, "why": "one member, every extracted year" if m.startswith("us-gaap:") else "a company-specific member"}


def bare(member: str | None) -> str | None:
    """us-gaap:LandMember -> LandMember; a company member keeps its prefix."""
    return member.split(":", 1)[1] if member and member.startswith("us-gaap:") else member


def compare(proposed: str | None, v: dict | None) -> str:
    """How the company's own tag stands against the proposed member: same | differs | tagged_no_proposal (the company
    tags a us-gaap member and nothing is proposed: nothing to differ from) | extension | ambiguous | inconsistent |
    partial | not_tagged | zero | not_checked."""
    if not v:
        return "not_checked"
    if v["status"] == "tagged":
        if not proposed:
            return "tagged_no_proposal"
        return "same" if bare(v["member"]) == proposed else "differs"
    return v["status"]


def verified(entry: dict | None, v: dict | None) -> bool:
    """The one test: the entry proposes a member and the company's own tag is that us-gaap member, unambiguously."""
    member = (entry or {}).get("standard_type")
    return bool(member) and bool(v) and v.get("status") == "tagged" and v.get("member") == f"us-gaap:{member}"


def record(v: dict) -> dict:
    """What a trail item carries on `ref.filer_tag`: the member and the readings it rested on (accession, balance date,
    value, members), so the walk can recompute it."""
    return {"member": v["member"], "readings": [{k: r.get(k) for k in ("accession", "period_end", "value", "members")} for r in v["readings"]]}


def gap(ref: dict, entry: dict | None, on_file: dict | None) -> str | None:
    """T80 for `mapping:filer_tag`: None when the item's recorded tag is the one on file and verifies the entry; else why.
    `on_file` is verdicts() recomputed from disk for the item's (ticker, name); never the item's own word."""
    by = FILER_TAG
    ref = ref or {}
    name = ref.get("name") or ref.get("dimension")  # a mapping item names the category; a fact item its dimension
    rec = ref.get("filer_tag")
    if not isinstance(rec, dict) or not rec.get("member") or not rec.get("readings"):
        return f"{by}: no company tag recorded on the row"
    if not entry or not entry.get("standard_type"):
        return f"{by}: no entry for {ref.get('ticker')} {name!r} in taxonomy/asset_types.yaml"
    if rec["member"] != f"us-gaap:{entry['standard_type']}":
        return f"{by}: the recorded tag {rec['member']} is not the entry's member {entry['standard_type']}"
    if on_file is None:
        return f"{by}: no company tag on file for {ref.get('ticker')} {name!r}"
    if on_file.get("status") != "tagged":
        return f"{by}: on file the company's tag is {on_file.get('status')} ({on_file.get('why')})"
    if record(on_file) != rec:
        return f"{by}: the recorded readings are not the ones on file"
    return None


def tally(tickers: list[str] | None = None) -> dict:
    """The one count of category mappings for the claims check and every packet's limitations line (and, through the
    same verdicts and status.of_mapping, the mapping stage): {"entries", "confirmed", "verified", "waiting", "read"}
    over the entries of taxonomy/asset_types.yaml (`tickers`: those companies only). `waiting` = entries neither a
    person confirmed nor the company's own tag checks. The tags are read from the database read-only and the instances
    on disk; `read` False when that failed, and then nothing counts as verified."""
    from ..core import store
    from ..core.status import confirmed
    from ..release.taxonomy import asset_types
    types = asset_types()
    pairs = [(t, n, e) for t, block in types.items() if isinstance(block, dict) and (tickers is None or t in tickers) for n, e in block.items()]
    tags, read = {}, False
    try:
        import duckdb
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        try:
            tags, read = verdicts_ok(con, sorted({t for t, _, _ in pairs}))
        finally:
            con.close()
    except Exception:
        tags, read = {}, False
    conf = sum(1 for _, _, e in pairs if confirmed(e))
    ver = sum(1 for t, n, e in pairs if not confirmed(e) and verified(e, tags.get((t, n))))
    return {"entries": len(pairs), "confirmed": conf, "verified": ver, "waiting": len(pairs) - conf - ver, "read": read}
