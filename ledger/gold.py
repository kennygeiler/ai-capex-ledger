"""The gold set (T82): a hand-verified sample per proven company, separate from golden.

Golden is a regression test: it says nothing changed, and it froze the Amazon blanks as expected (docs/DISCIPLINES.md,
"The root cause"). Gold is a correctness test: about 10 values and 10 facts per company, drawn at random and stratified
across fields and fiscal years, untagged notes facts (no XBRL twin, `no_reference`) oversampled because nothing
independent vouches for them. Each item records what it claims (ticker, field, dimension, period, value, the cited
cells) and a person's verdict: right, wrong or can't say, a note, `by` (on config.PEOPLE) and `at`.

- `draw` writes gold/<TICKER>.json. The seed includes the release version (config.GOLDEN_SEED|version|ticker), so the
  sample moves between releases. An item that already carries a verdict is never overwritten or dropped.
- `record` is the one writer of a verdict: under a lock, to a temporary file, moved into place (os.replace); `by` must
  be a person (status.is_person).
- `compare` is what `ledger golden --check` adds: every item with a verdict against the tables the code produced. Right
  must still equal the gold value; wrong must differ or be open. Items with no verdict are counted as unverified, never
  as a pass.
- `error_rate`: wrong of (right + wrong), with n and a Wilson 95% interval (ledger/stats.py); can't say is left out of
  the denominator and counted beside it."""
from __future__ import annotations

import json
import math
import os
import random
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import stats
from .config import GOLDEN_SEED, PROVEN
from .status import is_person
from .store import ROOT

GOLD = ROOT / "gold"
VERDICTS = ("right", "wrong", "cant_say")
VERDICT_WORD = {"right": "right", "wrong": "wrong", "cant_say": "can't say"}
PER_KIND = 10          # values and facts per company
UNTAGGED_SHARE = 0.6   # of the facts drawn, at least this share untagged (no XBRL twin) when the company has that many
EMPTY = {"verdict": None, "note": "", "by": None, "at": None}


# ── the claim ──────────────────────────────────────────────────────────────────────────────────────────────────────
def item_id(kind: str, ticker: str, field: str, dimension: str | None, period: str) -> str:
    """One gold item names one dataset row: value|AMZN|revenue||FY2024, fact|AMZN|segment_revenue|AWS|FY2024."""
    return "|".join((kind, ticker, field, dimension or "", period))


def num(v):
    """A value as an int (or None for a blank), whether it came from DuckDB, a CSV cell or JSON."""
    if v is None or v == "":
        return None
    f = float(v)
    return int(f) if f == int(f) else f


def deep_link(url, row_label, cell_text):
    from .taxonomy import deep_link as dl
    return dl(url, row_label, cell_text)


def _cites(ids: str, cells: dict, urls: dict, evidence: dict) -> list[dict]:
    from .release import split_ids  # a cost-line label may hold a comma
    out = []
    for eid in [i for i in split_ids(ids or "") if i]:
        c = cells.get(eid) or {}
        ev = evidence.get(eid) or {}
        img = ev.get("img") if ev.get("cell") == c.get("cell_text") else None  # a re-read counts only while it read the current cell
        out.append({"extraction_id": eid, "accession": c.get("accession") or eid.split("|")[0], "table": c.get("table_id"), "row": c.get("row_label"),
                    "column": c.get("column_label"), "cell_text": c.get("cell_text"), "url": deep_link(urls.get(c.get("accession") or eid.split("|")[0]), c.get("row_label"), c.get("cell_text")),
                    "screenshot": f"reports/evidence/{img}" if img else None, "rendered_match": ev.get("match") if ev.get("cell") == c.get("cell_text") and ev else None})
    return out


def candidates(con, ticker: str, evidence: dict | None = None) -> dict:
    """{"values": [...], "facts": [...]}: every row of the company's values and facts as a gold claim (no verdict)."""
    from .evidence import load_all
    evidence = load_all() if evidence is None else evidence
    q = lambda sql, *p: [dict(zip([c[0] for c in cur.description], r)) for cur in [con.execute(sql, list(p))] for r in cur.fetchall()]
    urls = {d["accession"]: d["url"] for d in q("select accession, url from documents where ticker = ?", ticker)}
    cells = {e["extraction_id"]: e for e in q("select extraction_id, accession, table_id, row_label, column_label, cell_text from extractions where ticker = ?", ticker)}
    cells |= {e["extraction_id"]: e for e in q("select extraction_id, accession, table_id, row_label, column_label, cell_text from note_extractions where ticker = ?", ticker)}
    xbrl = {(r["field"], r["period"]): r["value"] for r in q("select field, period, value from reference_values where ticker = ?", ticker)}
    vals = [{"id": item_id("value", ticker, v["field"], "", v["period"]), "kind": "value", "ticker": ticker, "field": v["field"], "dimension": "", "period": v["period"],
             "value": num(v["value"]), "label": v["label"], "untagged": False, "xbrl": num(xbrl.get((v["field"], v["period"]))),
             "cites": _cites(v["extraction_ids"], cells, urls, evidence), **EMPTY}
            for v in q('select field, period, value, label, extraction_ids from "values" where ticker = ? order by field, period', ticker)]
    facts = [{"id": item_id("fact", ticker, f["field"], f["dimension"], f["period"]), "kind": "fact", "ticker": ticker, "field": f["field"], "dimension": f["dimension"] or "", "period": f["period"],
              "value": num(f["value"]), "label": f["label"], "untagged": f["label"] == "no_reference", "xbrl": num(f["reference"]),
              "cites": _cites(f["extraction_ids"], cells, urls, evidence), **EMPTY}
             for f in q("select field, dimension, period, value, label, reference, extraction_ids from facts where ticker = ? order by field, dimension, period", ticker)]
    return {"values": vals, "facts": facts}


# ── the draw ───────────────────────────────────────────────────────────────────────────────────────────────────────
def seed(version: str, ticker: str) -> str:
    return f"{GOLDEN_SEED}|{version}|{ticker}"


def stratified(items: list[dict], n: int, rng: random.Random, strata=("field", "period")) -> list[dict]:
    """n items spread across the strata: each pick takes the item whose field, then year, has been picked least so far,
    ties broken by the seeded shuffle. So ten values over three fields and five years land 4/3/3 and two per year."""
    pool = list(items)
    rng.shuffle(pool)
    used = [dict() for _ in strata]
    out = []
    while pool and len(out) < n:
        best = min(range(len(pool)), key=lambda i: tuple(used[j].get(pool[i][s], 0) for j, s in enumerate(strata)) + (i,))
        it = pool.pop(best)
        for j, s in enumerate(strata):
            used[j][it[s]] = used[j].get(it[s], 0) + 1
        out.append(it)
    return out


def sample(cands: dict, version: str, ticker: str, per_kind: int = PER_KIND) -> list[dict]:
    """The draw for one company: values stratified by field and year; facts with the untagged ones oversampled (at least
    UNTAGGED_SHARE of the facts when the company has that many), each part stratified by field and year."""
    rng = random.Random(seed(version, ticker))
    vals = stratified(cands["values"], per_kind, rng)
    untagged = [f for f in cands["facts"] if f["untagged"]]
    tagged = [f for f in cands["facts"] if not f["untagged"]]
    k_un = min(len(untagged), max(math.ceil(per_kind * UNTAGGED_SHARE), per_kind - len(tagged)))
    facts = stratified(untagged, k_un, rng) + stratified(tagged, per_kind - k_un, rng)
    return vals + facts


def path(ticker: str, root: Path | None = None) -> Path:
    return (root or GOLD) / f"{ticker}.json"


def load(ticker: str, root: Path | None = None) -> dict | None:
    p = path(ticker, root)
    return json.loads(p.read_text()) if p.exists() else None


def load_all(root: Path | None = None) -> dict:
    """{ticker: the gold file} for every gold/<TICKER>.json."""
    d = root or GOLD
    return {p.stem: json.loads(p.read_text()) for p in sorted(d.glob("*.json"))} if d.exists() else {}


def has_verdict(it: dict) -> bool:
    return it.get("verdict") in VERDICTS


def merge(old: dict | None, drawn: list[dict]) -> list[dict]:
    """The new draw, with every item that already carries a verdict kept as it is (claim and verdict), whether the new
    draw picked it again or not. Items with no verdict are replaced by the draw."""
    kept = {it["id"]: it for it in (old or {}).get("items", []) if has_verdict(it)}
    out = [kept.pop(it["id"], it) for it in drawn]
    return out + list(kept.values())


def draw(con, version: str, tickers: list[str] | None = None, root: Path | None = None, per_kind: int = PER_KIND, evidence: dict | None = None) -> dict:
    """Write gold/<TICKER>.json for each company: the sample for `version`, merged with the verdicts on file. A file whose
    items would not change is left as it is. Returns {ticker: {items, values, facts, untagged, kept, written}}."""
    d = root or GOLD
    d.mkdir(parents=True, exist_ok=True)
    out = {}
    for t in tickers or PROVEN:
        old = load(t, d)
        items = merge(old, sample(candidates(con, t, evidence), version, t, per_kind))
        written = not old or old.get("items") != items or old.get("release") != version
        if written:
            doc = {"ticker": t, "release": version, "seed": seed(version, t), "drawn_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "per_kind": per_kind, "untagged_share": UNTAGGED_SHARE,
                   "how": "Values stratified by field and year; facts stratified by field and year with the untagged ones (no XBRL twin) oversampled. "
                          "A verdict is right, wrong or cant_say, given on the Proof page (Gold set); `ledger gold --draw` never overwrites one.",
                   "items": items}
            _write(path(t, d), doc)
        out[t] = {"items": len(items), "values": sum(i["kind"] == "value" for i in items), "facts": sum(i["kind"] == "fact" for i in items),
                  "untagged": sum(bool(i["untagged"]) for i in items), "kept": sum(has_verdict(i) for i in items), "written": written}
    return out


# ── the verdict: one writer ────────────────────────────────────────────────────────────────────────────────────────
def _write(p: Path, doc: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=f".{p.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(doc, indent=1, default=str) + "\n")
        os.replace(tmp, p)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def record(ticker: str, iid: str, verdict: str, note: str, by: str, root: Path | None = None) -> dict:
    """A person's verdict on one gold item, written under an exclusive lock (fcntl, a lock file beside the gold file),
    read once, changed in that one item, written to a temporary file and moved into place. Refuses a verdict off
    VERDICTS, a `by` that is not a person (status.is_person: config.PEOPLE), a company with no gold file and an item not
    in it; nothing is written then (ValueError, KeyError)."""
    import fcntl
    if verdict not in VERDICTS:
        raise ValueError(f"a verdict is one of {', '.join(VERDICTS)}, not {verdict!r}")
    by = str(by or "").strip()
    if not is_person(by):
        raise ValueError(f"{by!r} is not on config.PEOPLE, the people whose verdicts count; type your name in the signer box")
    if verdict in ("wrong", "cant_say") and not str(note or "").strip():
        raise ValueError(f"a {VERDICT_WORD[verdict]!r} verdict needs a note: what the filing shows")
    p = path(str(ticker), root)
    if not p.exists() or p.parent != (root or GOLD) or not str(ticker).isalnum():
        raise KeyError(f"no gold file for {ticker!r}")
    lock = p.with_name(f".{p.name}.lock")
    with open(lock, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            doc = json.loads(p.read_text())
            it = next((i for i in doc["items"] if i["id"] == iid), None)
            if it is None:
                raise KeyError(f"no gold item {iid!r} for {ticker}")
            it.update({"verdict": verdict, "note": str(note or "").strip(), "by": by, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            _write(p, doc)
            return it
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


# ── the error rate ─────────────────────────────────────────────────────────────────────────────────────────────────
def error_rate(items: list[dict]) -> dict:
    """wrong of (right + wrong), n, the Wilson 95% interval (fractions); can't say and unverified counted beside it."""
    c = {v: sum(i.get("verdict") == v for i in items) for v in VERDICTS}
    n = c["right"] + c["wrong"]
    ci = stats.wilson(c["wrong"], n)
    return {"wrong": c["wrong"], "right": c["right"], "cant_say": c["cant_say"], "n": n, "items": len(items),
            "unverified": sum(not has_verdict(i) for i in items), "rate": stats.share(c["wrong"], n),
            "interval": [round(ci[0], 4), round(ci[1], 4)] if ci else None,
            "untagged": {"items": sum(bool(i.get("untagged")) for i in items), "wrong": sum(bool(i.get("untagged")) and i.get("verdict") == "wrong" for i in items),
                         "n": sum(bool(i.get("untagged")) and i.get("verdict") in ("right", "wrong") for i in items)}}


def rate_line(r: dict) -> str:
    if not r["n"]:
        return f"no verdicts yet ({r['items']} items unverified)"
    lo, hi = r["interval"]
    return (f"{r['wrong']} wrong of {r['n']} ({100 * r['rate']:.1f}%, 95% interval {100 * lo:.1f}–{100 * hi:.1f}%); "
            f"{r['cant_say']} can't say, {r['unverified']} unverified")


# ── the check ──────────────────────────────────────────────────────────────────────────────────────────────────────
def live_index(values: list[dict], facts: list[dict]) -> dict:
    """{item id: the live row} for the values and facts tables as the code produced them."""
    out = {item_id("value", v["ticker"], v["field"], "", v["period"]): {**v, "_kind": "value"} for v in values}
    out |= {item_id("fact", f["ticker"], f["field"], f.get("dimension"), f["period"]): {**f, "_kind": "fact"} for f in facts}
    return out


def is_open(row: dict | None, looked_up: set | frozenset = frozenset(), xbrl: dict | None = None, res_index: dict | None = None) -> bool:
    """Whether a live row is open (status.state open or blocked), read the way Proof reads it: status.of_value or
    status.of_fact with the person's resolution on the row. No row, or a blank, is open: nothing ships there.
    `looked_up`: tickers whose XBRL was looked up (reference_values holds rows), `xbrl`: {(ticker, field, period): value}."""
    from . import resolutions, status
    if row is None or num(row.get("value")) is None:
        return True
    idx = res_index if res_index is not None else {}
    if row["_kind"] == "value":
        res = resolutions.resolution_of(idx, "values", row["ticker"], row["field"], "", row["period"])
        ref = {"looked_up": row["ticker"] in looked_up, "reference": (xbrl or {}).get((row["ticker"], row["field"], row["period"]))}
        return status.is_open(status.of_value(row, res, ref))
    res = resolutions.resolution_of(idx, "facts", row["ticker"], row["field"], row.get("dimension") or "", row["period"])
    return status.is_open(status.of_fact(row, res))


def what(it: dict) -> str:
    return f"{it['ticker']} {it['field']}{' ' + it['dimension'] if it.get('dimension') else ''} {it['period']}"


def compare(gold: dict, values: list[dict], facts: list[dict], reference: list[dict] = (), res_index: dict | None = None) -> dict:
    """Every gold item with a verdict against the live tables. right: the live value must equal the gold value (a blank,
    or a missing row, is not equal). wrong: the live value must differ from it, or the row must be open; a known-wrong
    value that still ships is a failure. cant_say passes nothing and fails nothing. Items with no verdict are counted
    as unverified, never as a pass. Returns {ok, failures: [str], checked, right, wrong, cant_say, unverified, items}."""
    live = live_index(values, facts)
    looked_up = {r["ticker"] for r in reference}
    xbrl = {(r["ticker"], r["field"], r["period"]): num(r["value"]) for r in reference}
    out = {"failures": [], "checked": 0, "right": 0, "wrong": 0, "cant_say": 0, "unverified": 0, "items": 0}
    for t, doc in sorted(gold.items()):
        for it in doc.get("items", []):
            out["items"] += 1
            v = it.get("verdict")
            if v not in VERDICTS:
                out["unverified"] += 1
                continue
            out[v] += 1
            if v == "cant_say":
                continue
            out["checked"] += 1
            row = live.get(it["id"])
            got = num(row.get("value")) if row else None
            if v == "right" and got != num(it["value"]):
                out["failures"].append(f"{it['id']}: gold says right at {it['value']} (by {it.get('by')}), the live table has "
                                       + ("no row" if row is None else f"{got if got is not None else 'a blank'} ({row.get('label')})"))
            if v == "wrong" and got == num(it["value"]) and not is_open(row, looked_up, xbrl, res_index):
                out["failures"].append(f"{it['id']}: gold says {it['value']} is wrong (by {it.get('by')}), and the live table still ships it ({row.get('label')}), not open")
    out["ok"] = not out["failures"]
    return out


def compare_db(con, gold: dict | None = None, res_index: dict | None = None) -> dict:
    """`compare` against a database's values, facts and reference_values (the golden run's temporary one, or the working one)."""
    from . import resolutions
    gold = load_all() if gold is None else gold
    tickers = sorted(gold)
    q = lambda sql: [dict(zip([c[0] for c in cur.description], r)) for cur in [con.execute(sql, [tickers])] for r in cur.fetchall()]
    return compare(gold, q('select ticker, field, period, value, label from "values" where ticker in (select unnest(?))'),
                   q("select ticker, field, dimension, period, value, label from facts where ticker in (select unnest(?))"),
                   q("select ticker, field, period, value from reference_values where ticker in (select unnest(?))"),
                   resolutions.by_row() if res_index is None else res_index)


def summary_line(c: dict) -> str:
    if not c["items"]:
        return "gold: no gold/ files"
    head = f"gold: {c['checked']} verdicts checked against the live tables, {len(c['failures'])} failing; {c['cant_say']} can't say; unverified: {c['unverified']} of {c['items']}"
    return head + "".join(f"\n  FAIL {f}" for f in c["failures"])
