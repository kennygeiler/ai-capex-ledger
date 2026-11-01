"""The Release page's checklist (T5, docs/PROOF.md).

Every line is what could make a signature wrong, with its count and the page that fixes it: the gates per company
(release.gates), open and blocked items in the scope (proof.board, the one definition of open), the decisions a run
left to confirm (resolutions.unconfirmed), unmapped asset types (taxonomy.unmapped), rows with no value by measure,
the diff in rows from the previous release (release.rows_diff), the golden test and the last test run
(reports/golden.json, reports/tests.json), and the packet as `ledger release` would build it, built in memory and
not written. `required` lines must pass before the Sign button enables; the rest inform.

reports/tests.json (T30 writes it; read here already): {"ok": bool, "count": int, "failures": [str], "at": iso}.
Absent means "not run": shown grey, and it does not block, until T30 lands and the runner writes it on every run."""
import csv
import io
import json
import re
from datetime import datetime, timezone

from . import api, proof, resolutions, store, taxonomy
from .agent import model
from .config import SCOPE
from .evidence import load_all
from .extract import prompt_version
from .ingest.tables import PARSER_VERSION
from .release import GATES, RELEASES, build, content_hash, failing, gates, releases, rows_diff, rows_diff_md, version_key
from .review import apply, decisions, open_items
from .rules import load as load_rules

VERSION = re.compile(r"^v\d+\.\d+\.\d+$")
GOLDEN = store.ROOT / "reports" / "golden.json"
TESTS = store.ROOT / "reports" / "tests.json"
GATE_FIX = {"G1": "proof", "G4": "reconcile", "G5": "proof", "G6": "reconcile?cause=to_confirm"}  # the page that fixes each gate's items
GATE_SHORT = {"G1": "Every filing read, no failure open", "G4": "No block without a decision", "G5": "Every value confirmed on the filing", "G6": "No decision left to confirm"}


def _rows(con, sql, p):
    cur = con.execute(sql, p)
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def next_version() -> str:
    """The minor bump of the last release folder (v1.7.0 → v1.8.0); v0.1.0 when there is none."""
    rel = releases()
    if not rel:
        return "v0.1.0"
    major, minor, _ = version_key(rel[-1].name)
    return f"v{major}.{minor + 1}.0"


def previous_of(version: str):
    """The release folder before `version` by number, or None."""
    before = [p for p in releases() if version_key(p.name) < version_key(version)]
    return before[-1] if before else None


def packet(con, version: str, stage: int = 3) -> dict:
    """The release as `ledger release` builds it, in memory: {version, files, hash, manifest, gates, previous}. The
    scope is config.SCOPE and nothing else (T2); DIFF.md carries the values diff, the files diff and the rows diff (T8)."""
    tickers = [list(SCOPE)]
    values = _rows(con, 'select * from "values" where ticker in (select unnest(?))', tickers)
    excs = _rows(con, "select * from exceptions where ticker in (select unnest(?))", tickers)
    exts = _rows(con, "select * from extractions where ticker in (select unnest(?))", tickers)
    ds = decisions()
    hc_path = store.ROOT / "golden" / f"stage{stage}-handcheck.json"
    cells = {e["extraction_id"]: e["cell_text"] for e in exts}
    confirmed = {i for i, r in load_all().items() if r["match"] and cells.get(i) == r["cell"]}
    g = gates(values, open_items(excs, ds), json.loads(hc_path.read_text()) if hc_path.exists() else None, confirmed, resolutions.unconfirmed())
    prev_dir = previous_of(version)
    previous = list(csv.DictReader((prev_dir / "values.csv").open())) if prev_dir else None
    ai = _rows(con, "select * from ai_spend where ticker in (select unnest(?))", tickers)
    facts = _rows(con, "select * from facts where ticker in (select unnest(?))", tickers)
    files = build(version, apply(values, excs, ds), exts, excs, previous, confirmed, ai, facts)
    want = set(tickers[0])
    for name in api.RELEASE_LISTS:  # one shape (C7): the release holds every list the API serves, as the API serves it
        rows = [r for r in api.fetch(con, name) if r.get("ticker", "") in want]
        files[f"{name}.csv"] = api.to_csv(rows)
    diff = {}
    if prev_dir:  # the shape of the packet is part of the diff
        before = set(json.loads((prev_dir / "manifest.json").read_text())["files"]) - {"manifest.json", "SIGNOFF.json"}
        gone, new = sorted(before - set(files)), sorted(set(files) - before)
        if gone or new:
            files["DIFF.md"] += "\n".join(["", "## Files"] + [f"- added `{f}`" for f in new] + [f"- removed `{f}`" for f in gone] + [""])
        diff = rows_diff(files, {f.name: f.open(newline="").read() for f in prev_dir.glob("*.csv")})
        files["DIFF.md"] += rows_diff_md(diff)
    h = content_hash(files)
    manifest = {"version": version, "stage": stage, "scope": list(SCOPE), "hash": h, "files": sorted(files), "prompt": prompt_version(), "parser": PARSER_VERSION,
                "model": model(), "rules": {r["id"]: r["file_sha256"][:12] for r in load_rules()}, "decisions": len(ds)}
    return {"version": version, "files": files, "hash": h, "manifest": manifest, "gates": g, "previous": prev_dir.name if prev_dir else None, "rows_diff": diff,
            "hand_check": hc_path.exists(), "values": len(values)}


def write(p: dict) -> dict:
    """releases/<version>/ from a packet. A folder that exists with the same hash is left alone; one with different
    content is refused: a shipped release is never edited."""
    out = RELEASES / p["version"]
    if out.exists():
        old = json.loads((out / "manifest.json").read_text())["hash"]
        if old != p["hash"]:
            raise ValueError(f"{p['version']} exists with different content; a shipped release is never edited. Use a new version.")
        return {"written": False, "hash": old}
    out.mkdir(parents=True)
    for name, text in p["files"].items():
        (out / name).write_text(text)
    (out / "manifest.json").write_text(json.dumps(p["manifest"], indent=1))
    return {"written": True, "hash": p["hash"]}


def _report(path) -> dict | None:
    try:
        return json.loads(path.read_text()) if path.exists() else None
    except (json.JSONDecodeError, OSError):
        return None


def _line(id_, label, required, count, state, link, note="", detail=None) -> dict:
    """state: pass | fail | info | not_run. A required line passes only on `pass`."""
    return {"id": id_, "label": label, "required": required, "count": count, "state": state, "ok": state == "pass", "link": link, "note": note, "detail": detail or []}


def checklist(con, version: str | None = None, stage: int = 3) -> dict:
    """The checklist for `version` (default: the next version). JSON the page renders as it is."""
    version = version or next_version()
    if not VERSION.match(version):
        raise ValueError(f"not a version: {version!r} (vMAJOR.MINOR.PATCH)")
    p = packet(con, version, stage)
    board = proof.board(con)
    lines = []
    # gates per company (T4): one line per gate, the failing companies named
    bad = failing(p["gates"])
    for gid in GATES:
        by_t = p["gates"][gid]
        n = sum(len(v) for v in by_t.values())
        detail = [{"ticker": t, "items": len(items), "example": items[0] if items else ""} for t, items in by_t.items()]
        lines.append(_line(f"gate_{gid}", f"{gid}: {GATE_SHORT[gid]}", True, n, "pass" if n == 0 else "fail", GATE_FIX[gid],
                           GATES[gid] + (f"; export the hand-check from reports/stage{stage}-validation.html to golden/stage{stage}-handcheck.json" if gid == "G5" and any(v == ["no hand-check file"] for v in by_t.values()) else ""), detail))
    # open and blocked in scope (T1): the one definition of open, from the Proof board
    blocked = sum(s["blocked"] for c in board["proven"] for s in c["stages"].values())
    open_ = board["open"] - blocked
    per_co = [{"ticker": c["ticker"], "open": c["open"] - sum(s["blocked"] for s in c["stages"].values()), "blocked": sum(s["blocked"] for s in c["stages"].values())} for c in board["proven"]]
    lines.append(_line("open", "Open items in scope", True, open_, "pass" if open_ == 0 else "fail", "reconcile", "neither checked nor explained; needs a rule, a definition or a decision", [x for x in per_co if x["open"]]))
    lines.append(_line("blocked", "Blocked items in scope", True, blocked, "pass" if blocked == 0 else "fail", "reconcile", "a block-severity rule or a person's decision refuses the release", [x for x in per_co if x["blocked"]]))
    # decisions a run left to confirm (T3)
    unc = resolutions.unconfirmed()
    lines.append(_line("unconfirmed", "Decisions left to confirm", True, len(unc), "pass" if not unc else "fail", "reconcile?cause=to_confirm",
                       "a run decided; a person confirms or overturns each (the same items G6 counts per company)", [{"key": r["key"], "state": r["state"], "reason": (r.get("reason") or "")[:160]} for r in unc]))
    # unmapped asset types in scope (T14: 0 required)
    um = taxonomy.unmapped(con, list(SCOPE))
    lines.append(_line("unmapped", "Unmapped asset types in scope", True, len(um), "pass" if not um else "fail", "rules", "every reported PP&E category maps to a us-gaap member (taxonomy/asset_types.yaml)", um))
    # rows with no value, by measure (T15: informational)
    tax = list(csv.DictReader(io.StringIO(p["files"]["taxonomy.csv"])))
    nv = {}
    for r in tax:
        if r.get("has_value") == "False":
            nv[r["measure"]] = nv.get(r["measure"], 0) + 1
    lines.append(_line("no_value", "Rows with no value", False, sum(nv.values()), "info", "data?list=taxonomy&has_value=false", "kept with value empty and has_value false; a project without an amount, a statement in words",
                       [{"measure": k, "rows": v} for k, v in sorted(nv.items())]))
    # diff from the previous release in rows (T8)
    d = p["rows_diff"]
    n_diff = sum(x["added"] + x["removed"] + x["changed"] for x in d.values())
    lines.append(_line("diff", f"Rows changed since {p['previous']}" if p["previous"] else "First release", False, n_diff, "info", "data",
                       "added + removed + changed across the lists; DIFF.md carries the same table and examples",
                       [{"list": k, "rows": x["rows"], "added": x["added"], "removed": x["removed"], "changed": x["changed"], "columns_added": x["columns_added"], "columns_removed": x["columns_removed"]} for k, x in d.items()]))
    # golden and the last test run (T30)
    g = _report(GOLDEN)
    g_state = "fail" if g is None else ("pass" if g.get("ok") else "fail")
    lines.append(_line("golden", "Golden test", True, 0 if g_state == "pass" else len((g or {}).get("diffs") or {}) or 1, g_state, "proof",
                       "not run" if g is None else f"{'equal' if g.get('ok') else 'differs'}, {g.get('at')}" + (f", failed at {g['failed_step']}" if g and g.get("failed_step") else ""),
                       [{"table": k, "only_in_run": v.get("n_only_in_run"), "only_in_expected": v.get("n_only_in_expected")} for k, v in ((g or {}).get("diffs") or {}).items()]))
    t = _report(TESTS)
    t_state = "not_run" if t is None else ("pass" if t.get("ok") else "fail")
    lines.append(_line("tests", "Test run", t is not None, 0 if t is None else len(t.get("failures") or []), t_state, "proof",
                       "not run (reports/tests.json; T30 writes it)" if t is None else f"{t.get('count')} tests, {len(t.get('failures') or [])} failing, {t.get('at')}",
                       [{"test": f} for f in (t or {}).get("failures") or []]))
    # the packet as it would be written
    exists = (RELEASES / version).exists()
    same = exists and json.loads((RELEASES / version / "manifest.json").read_text()).get("hash") == p["hash"]
    signed = exists and (RELEASES / version / "SIGNOFF.json").exists()
    pk_state = "fail" if (exists and not same) or signed else "pass"
    pk_note = (f"{version} is already signed" if signed else f"releases/{version}/ exists with different content; a shipped release is never edited" if exists and not same
               else f"releases/{version}/ exists unchanged, unsigned" if exists else f"built in memory, not written; {p['values']} values, {len(tax)} taxonomy rows")
    lines.append(_line("packet", f"Packet {version}", True, len(p["files"]), pk_state, "data", pk_note,
                       [{"file": n, "bytes": len(text.encode()), "rows": max(0, text.count("\n") - 1) if n.endswith(".csv") else None} for n, text in sorted(p["files"].items())]))
    required = [l for l in lines if l["required"]]
    return {"version": version, "previous": p["previous"], "scope": list(SCOPE), "stage": stage, "hash": p["hash"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "ok": all(l["ok"] for l in required), "red": [l["id"] for l in required if not l["ok"]], "lines": lines,
            "gates": {"table": p["gates"], "failing": bad}, "open": open_, "blocked": blocked, "unconfirmed": len(unc), "unmapped": len(um),
            "diff": d, "golden": g, "tests": t, "exists": exists, "signed": signed}
