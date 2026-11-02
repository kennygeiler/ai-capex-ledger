"""The category-mapping decision card: one per reported PP&E category, the same on the trail (Category mapping) and in
Reconcile's asset types group. `decisions(con, ticker)` is the one function both read, so the two pages cannot show a
category two ways.

A card puts beside the proposed us-gaap member what a person needs to judge it: the company's line (its name, the latest
balance and the years before, a link to the cell in the filing), the standard's own label and definition (verbatim from
taxonomy/us_gaap_members.yaml, which records the FASB files it was read from), what the company itself tagged in its
XBRL (ledger/filertag.py), the basis recorded on the entry, a few other members that plausibly fit (the company's own
tag when it differs, then members whose FASB label shares words with the reported name), and how many derived figures
move if the member changes. The card is presentation: the state comes from status.of_mapping, as on Proof.

    card = {"ticker", "name", "state": {state, by, label}, "line": {...}, "proposed": {member, label, definition} | None,
            "source", "tag": {status, text, member, label, definition, accession, period_end}, "basis", "by", "at",
            "alternatives": [{member, label, definition, why}], "affects": {rows, value, period, text},
            "members": [{member, label}], "confirmed_by", "confirmed_at"}
"""
from __future__ import annotations

import re
from functools import lru_cache

import yaml

from . import filertag, status, store
from .taxonomy import asset_types, deep_link

MEMBERS_FILE = store.ROOT / "taxonomy" / "us_gaap_members.yaml"
STOP = {"and", "or", "of", "the", "in", "for", "a", "to", "add", "not", "yet", "net", "type", "types", "asset", "assets", "property", "plant"}


@lru_cache(maxsize=4)
def _members_doc(path: str, mtime: float) -> dict:
    from pathlib import Path
    return yaml.safe_load(Path(path).read_text()) or {}


def fasb() -> dict:
    """taxonomy/us_gaap_members.yaml: {"source": {...}, "members": {Member: {label, definition}}}, re-read when it changes."""
    p = MEMBERS_FILE
    return _members_doc(str(p), p.stat().st_mtime) if p.exists() else {"source": {}, "members": {}}


def source_label(doc: dict | None = None) -> str:
    """The short name of the standard the definitions come from, as the file records it ("FASB US GAAP 2025")."""
    return ((doc or fasb()).get("source") or {}).get("short") or ""


def member_info(member: str | None, doc: dict | None = None) -> dict | None:
    """{member, label, definition} for a us-gaap member on file (a bare name or us-gaap:Name); None for one not on file
    (a company member, or a us-gaap member nobody copied into the file)."""
    if not member:
        return None
    m = filertag.bare(member)
    e = ((doc or fasb()).get("members") or {}).get(m)
    return {"member": m, "label": e["label"], "definition": e["definition"]} if e else None


def _words(s: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z]+", (s or "").lower()):
        if w in STOP:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w)
    return out


def alternatives(name: str, proposed: str | None, tag: dict | None, allowed: list[str], doc: dict | None = None, n: int = 3) -> list[dict]:
    """Up to `n` other members a person might pick, each with its FASB label and definition and why it is offered:
    the company's own us-gaap tag when it is not the proposal (one member, or each member when ambiguous or by year),
    then the allowed members whose FASB label shares words with the reported name, the closest first (shared words over
    all words, then the file's order). A simple heuristic, said as such: "Company's own tag" or "Shares words: ..."."""
    doc = doc or fasb()
    out, seen = [], {proposed}
    found = (tag or {}).get("member")
    for m in ([found] if isinstance(found, str) else found or []):
        b = filertag.bare(m)
        info = member_info(m, doc)
        if m.startswith("us-gaap:") and info and b not in seen:
            out.append({**info, "why": "Company's own tag"})
            seen.add(b)
    mine = _words(name)
    scored = []
    for i, m in enumerate(allowed):
        info = member_info(m, doc)
        if not info or m in seen:
            continue
        theirs = _words(info["label"])
        shared = mine & theirs
        if shared:
            scored.append((-len(shared) / len(mine | theirs), i, info, shared))
    for _, _, info, shared in sorted(scored, key=lambda x: (x[0], x[1])):
        if len(out) >= n:
            break
        out.append({**info, "why": "Shares words: " + ", ".join(sorted(shared))})
    return out[:n]


def tag_text(cmp: str, tag: dict | None, doc: dict | None = None) -> str:
    """The company's own tag in product words."""
    m = (tag or {}).get("member")

    def name(x):
        info = member_info(x, doc)
        return f"{info['label']} ({info['member']})" if info else x
    if cmp == "same":
        return "Same as proposed"
    if cmp == "differs":
        return f"Differs: {name(m)}"
    if cmp == "extension":
        return f"Company-specific tag: {m}"
    if cmp == "partial":
        return (f"Company-specific tag: {m}" if not m.startswith("us-gaap:") else f"Tagged: {name(m)}") + " · not every year"
    if cmp == "ambiguous":
        return "Ambiguous: " + ", ".join(m or [])
    if cmp == "inconsistent":
        return "Differs by year: " + ", ".join(m or [])
    if cmp == "zero":
        return "Not compared: zero value"
    if cmp == "not_checked":
        return "Not checked: instance not on file"
    return "Not tagged"


def state_label(st: dict, entry: dict | None) -> str:
    if st["by"] == filertag.FILER_TAG:
        return "Verified · matches company's own tag"
    if st["state"] == "checked":
        return f"Confirmed · {entry.get('confirmed_by')}"
    if (entry or {}).get("standard_type"):
        return "To confirm"
    return "Unmapped"


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def decisions(con, ticker: str, names: list[str] | None = None) -> dict[str, dict]:
    """{reported_name: card} for every reported PP&E category of `ticker` (or `names`). One read of everything."""
    from .cards import money
    from .mapper import members
    from .release import split_ids
    t = ticker.upper()
    doc = fasb()
    entries = asset_types().get(t) or {}
    tags = filertag.verdicts(con, [t])
    allowed = members()
    facts = _rows(con, "select * from facts where ticker = ? and field = 'ppe_category' order by dimension, period", t)  # every column the table has
    docs = {d["accession"]: d for d in _rows(con, "select * from documents where ticker = ?", t)}
    try:
        notes = {e["extraction_id"]: e for e in _rows(con, "select extraction_id, row_label, cell_text from note_extractions where ticker = ?", t)}
    except Exception:
        notes = {}
    by_name: dict = {}
    for f in facts:
        by_name.setdefault(f["dimension"], []).append(f)
    out = {}
    for name in sorted(names if names is not None else by_name):
        rows = by_name.get(name) or []
        e = entries.get(name) or {}
        member = e.get("standard_type")
        tag = tags.get((t, name))
        st = status.of_mapping(e or None, tag)
        last = rows[-1] if rows else None
        link = None
        if last:
            ids = split_ids(last.get("extraction_ids") or "")
            c = notes.get(ids[-1]) if ids else None
            link = deep_link((docs.get(last.get("accession")) or {}).get("url"), (c or {}).get("row_label"), (c or {}).get("cell_text"))
        cmp = filertag.compare(member, tag)
        latest_tag = ((tag or {}).get("readings") or [None])[-1] or {}
        tag_member = (tag or {}).get("member")
        out[name] = {
            "ticker": t, "name": name,
            "state": {"state": st["state"], "by": st["by"], "label": state_label(st, e)},
            "line": {"name": name, "latest": {"period": last["period"], "value": last["value"]} if last else None,
                     "series": [{"period": r["period"], "value": r["value"]} for r in rows], "link": link,
                     "accession": last.get("accession") if last else None, "filed": str((docs.get(last.get("accession")) or {}).get("filed") or "")[:10] if last else None},
            "proposed": member_info(member, doc) or ({"member": member, "label": None, "definition": None} if member else None),
            "source": source_label(doc),
            "tag": {"status": cmp, "text": tag_text(cmp, tag, doc), "member": tag_member,
                    **({k: v for k, v in (member_info(tag_member, doc) or {}).items() if k in ("label", "definition")} if isinstance(tag_member, str) else {}),
                    "accession": latest_tag.get("accession"), "period_end": latest_tag.get("period_end")},
            "basis": e.get("evidence"), "by": e.get("by"), "at": str(e.get("at")) if e.get("at") is not None else None,
            "confirmed_by": e.get("confirmed_by"), "confirmed_at": str(e.get("confirmed_at")) if e.get("confirmed_at") is not None else None,
            "alternatives": alternatives(name, member, tag, allowed, doc),
            "affects": {"rows": len(rows), "value": last["value"] if last else None, "period": last["period"] if last else None,
                        "text": f"{len(rows)} figure{'' if len(rows) == 1 else 's'} · {money(last['value'])} {last['period']}" if last else "No figures"},
            "members": [{"member": m, "label": (member_info(m, doc) or {}).get("label") or m} for m in allowed],
        }
    return out
