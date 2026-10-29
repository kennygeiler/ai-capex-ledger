"""python -m ledger release <version> --stage N   ->  releases/<version>/ (refuses while a gate fails)"""
import argparse
import csv
import json

from .. import store
from ..agent import model
from ..config import STAGES, stage_tickers
from ..extract import prompt_version
from ..ingest.tables import PARSER_VERSION
from ..release import GATES, RELEASES, build, content_hash, gates, releases, version_key
from ..review import apply, decisions, open_items
from ..rules import load
from ..evidence import load_all

def _rows(con, sql, p):
    cur = con.execute(sql, p)
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger release")
    ap.add_argument("version")
    ap.add_argument("--stage", type=int, default=1, choices=STAGES)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con, tickers = store.init(a.db), [stage_tickers(a.stage)]
    values = _rows(con, 'select * from "values" where ticker in (select unnest(?))', tickers)
    excs = _rows(con, "select * from exceptions where ticker in (select unnest(?))", tickers)
    exts = _rows(con, "select * from extractions where ticker in (select unnest(?))", tickers)
    ds = decisions()
    hc_path = store.ROOT / "golden" / f"stage{a.stage}-handcheck.json"
    cells = {e["extraction_id"]: e["cell_text"] for e in exts}
    confirmed = {i for i, r in load_all().items() if r["match"] and cells.get(i) == r["cell"]}
    failing = gates(values, open_items(excs, ds), json.loads(hc_path.read_text()) if hc_path.exists() else None, confirmed)
    if any(failing.values()):
        print(f"{a.version} not built. Failing gates:")
        for g, items in failing.items():
            if items:
                print(f"  {g} {GATES[g]}: {len(items)} item(s), e.g. {items[0]}")
        if failing["G5"] == ["no hand-check file"]:
            print(f"  (export the hand-check from reports/stage{a.stage}-validation.html to {hc_path.relative_to(store.ROOT)})")
        return 1
    prev_dir = ([p for p in releases() if version_key(p.name) < version_key(a.version)] or [None])[-1]
    previous = list(csv.DictReader((prev_dir / "values.csv").open())) if prev_dir else None
    files = build(a.version, apply(values, excs, ds), exts, excs, previous, confirmed)
    h = content_hash(files)
    out = RELEASES / a.version
    if out.exists():
        old = json.loads((out / "manifest.json").read_text())["hash"]
        print(f"{a.version} exists " + ("unchanged." if old == h else "with different content; a shipped release is never edited. Use a new version."))
        return 0 if old == h else 1
    out.mkdir(parents=True)
    for name, text in files.items():
        (out / name).write_text(text)
    manifest = {"version": a.version, "stage": a.stage, "hash": h, "files": sorted(files), "prompt": prompt_version(), "parser": PARSER_VERSION, "model": model(),
                "rules": {r["id"]: r["file_sha256"][:12] for r in load()}, "decisions": len(ds)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"built {a.version}: {len(values)} values, hash {h[:12]}. Sign with: python -m ledger signoff {a.version} --by \"<name>\"")
    return 0
