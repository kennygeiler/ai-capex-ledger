"""The golden test: the pipeline proves itself on a frozen set of companies (docs/PROOF.md).

`freeze` copies, for the proven set, what the code stages read (the parsed tables, the texts, the agents' answers,
the documents and texts rows) into fixtures/ and writes the tables the code produces from them into
fixtures/expected/. `check` rebuilds a repo layout in a temporary folder (LEDGER_ROOT), seeds a fresh database from
the fixtures, runs every code stage (nothing is fetched, no agent is asked), and compares the tables it gets with
fixtures/expected/, column by column, row by row. Any change to a parser, a rule, a loader or the taxonomy has to leave
the comparison equal or update the expectation on purpose.

Agents are frozen here on purpose: their answers are inputs. The checks on those answers (XBRL, the rendered cell, the
verbatim quote) are what the proof board shows."""
from __future__ import annotations

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import store
from .config import PROVEN

FIXTURES = store.ROOT / "fixtures"
EXPECTED = FIXTURES / "expected"
# the tables the code stages produce, and the columns that vary run to run (left out of the comparison)
TABLES = {"values": ("run_id",), "facts": (), "ai_statements": ("run_id",), "ai_spend": (), "projects": ("run_id",),
          "extractions": ("run_id",), "note_extractions": ("run_id",), "exceptions": ("exception_id",)}
STEPS = [["extract", "--pack"], ["extract", "--load"], ["reconcile"], ["aispend", "--pack"], ["aispend", "--load"], ["notes", "--pack"], ["notes", "--load"],
         ["projects", "--pack"], ["projects", "--load"], ["rules"]]  # pack rebuilds the task files the loaders check quotes against; the agents' answers are the frozen inputs
LISTS = ("taxonomy",)  # computed lists frozen too (T31): the taxonomy rows the code builds from the tables, as taxonomy.csv in a release
# what the temporary root needs besides data/: the config the stages read, as it is in the repo
SHARED = ("agents", "definitions", "gold", "rules", "decisions", "sources", "taxonomy", ".env")  # .env: the SEC client checks the contact at import; nothing is fetched. taxonomy/: the asset-type mappings and stated figures the taxonomy rows read. decisions/: a person's decisions and resolutions, read by freeze (from the repo) and check (from the root) alike, so a decision is part of the expectation and a new one shows as a diff


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _csv(rows: list[dict], skip: tuple = ()) -> str:
    if not rows:
        return ""
    cols = [c for c in rows[0] if c not in skip]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in sorted(rows, key=lambda r: json.dumps([r.get(c) for c in cols], default=str)):
        w.writerow({c: ("" if r.get(c) is None else r[c]) for c in cols})
    return buf.getvalue()


def freeze(con, tickers: list[str] | None = None) -> dict:
    """Copy the inputs for the proven set into fixtures/ and the tables the code makes from them into fixtures/expected/."""
    tickers = tickers or PROVEN
    if FIXTURES.exists():
        shutil.rmtree(FIXTURES)
    (FIXTURES / "data").mkdir(parents=True)
    docs = _rows(con, "select * from documents where ticker in (select unnest(?)) order by ticker, period", tickers)
    texts = _rows(con, "select * from texts where ticker in (select unnest(?)) order by ticker, date", tickers)
    copied = 0
    for d in docs:
        for rel in (d["tables_path"],):
            src = store.ROOT / rel
            if src.exists():
                dst = FIXTURES / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
        inst = store.ROOT / "data" / "raw" / f"{int(d['cik']):010d}" / "filings" / f"{d['accession']}.facts.json"  # the distilled XBRL instance (dimensions.instance_facts)
        if not inst.exists():
            from .reference.dimensions import instance_facts
            instance_facts(int(d["cik"]), d["accession"])
        if inst.exists():
            dst = FIXTURES / inst.relative_to(store.ROOT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(inst, dst)
            copied += 1
        for sub in ("extract", "notes"):
            src = store.ROOT / "data" / sub / "outputs" / f"{d['accession']}.json"
            if src.exists():
                dst = FIXTURES / "data" / sub / "outputs" / f"{d['accession']}.json"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
    for t in texts:
        src = store.ROOT / t["path"]
        if src.exists():
            dst = FIXTURES / t["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        for sub in ("aispend", "projects"):
            src = store.ROOT / "data" / sub / "outputs" / f"{t['text_id']}.json"
            if src.exists():
                dst = FIXTURES / "data" / sub / "outputs" / f"{t['text_id']}.json"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
    xbrl = _rows(con, "select * from reference_values where ticker in (select unnest(?))", tickers) if store_has(con, "reference_values") else []
    (FIXTURES / "seed.json").write_text(json.dumps({"tickers": tickers, "documents": docs, "texts": texts, "reference_values": xbrl}, indent=1, default=str))
    shutil.copy2(store.ROOT / "data" / "companies.json", FIXTURES / "data" / "companies.json")
    EXPECTED.mkdir(parents=True)
    for name, skip in TABLES.items():
        rows = _rows(con, f'select * from "{name}" where ticker in (select unnest(?))', tickers) if store_has(con, name) else []
        (EXPECTED / f"{name}.csv").write_text(_csv(rows, skip))
    (EXPECTED / "taxonomy.csv").write_text(taxonomy_csv(con, tickers))
    return {"tickers": tickers, "documents": len(docs), "texts": len(texts), "files": copied, "xbrl_facts": len(xbrl)}


def taxonomy_csv(con, tickers: list[str] | None = None) -> str:
    """The taxonomy rows (ledger/taxonomy.py) as the frozen CSV: every column of store.TAXONOMY, rows sorted."""
    from .taxonomy import rows
    return _csv(rows(con, tickers))


def _taxonomy_in(root: Path, db: Path, tickers: list[str]) -> str:
    """The taxonomy rows built in the temporary root: a subprocess with LEDGER_ROOT, so the asset-type mappings, the
    stated figures, the resolutions and the distilled XBRL instances are read from there, like every other stage."""
    code = "import sys, json; from ledger import golden, store; con = store.init(sys.argv[1]); sys.stdout.write(golden.taxonomy_csv(con, json.loads(sys.argv[2])))"
    r = subprocess.run([sys.executable, "-c", code, str(db), json.dumps(tickers)], cwd=store.ROOT, env={**os.environ, "LEDGER_ROOT": str(root)}, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    return r.stdout


def store_has(con, name: str) -> bool:
    return bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [name]).fetchone()[0])


def check(keep: bool = False, verbose: bool = False) -> dict:
    """Run the code stages on the fixtures in a temporary root and compare every table with fixtures/expected/."""
    seed = json.loads((FIXTURES / "seed.json").read_text())
    root = Path(tempfile.mkdtemp(prefix="ledger-golden-"))
    try:
        for name in SHARED:
            src = store.ROOT / name
            if src.exists():
                os.symlink(src, root / name)
        shutil.copytree(FIXTURES / "data", root / "data")
        (root / "reports").mkdir()
        db = root / "data" / "ledger.duckdb"
        con = store.init(db)
        store.write(con, "documents", seed["documents"])
        store.write(con, "texts", seed["texts"])
        if seed.get("reference_values"):
            store.write(con, "reference_values", seed["reference_values"])
        con.close()
        env = {**os.environ, "LEDGER_ROOT": str(root)}
        log = []
        for step in STEPS:
            cmd = [sys.executable, "-m", "ledger", *step, "--ticker", *seed["tickers"], "--db", str(db)]
            r = subprocess.run(cmd, cwd=store.ROOT, env=env, capture_output=True, text=True)
            log.append({"step": " ".join(step), "exit": r.returncode, "out": r.stdout[-2000:], "err": r.stderr[-2000:]})
            if verbose:
                print(f"== {' '.join(step)} (exit {r.returncode})\n{r.stdout.strip()[-800:]}\n{r.stderr.strip()[-800:]}")
            if r.returncode not in (0, 2):  # 2: a step found exceptions, which the expected tables carry too
                return {"ok": False, "root": str(root), "log": log, "diffs": {}, "failed_step": " ".join(step)}
        got_lists = {name: _taxonomy_in(root, db, seed["tickers"]) for name in LISTS}  # before this process opens the database: DuckDB takes one writer lock
        con = store.init(db)
        diffs = {}
        for name, skip in {**TABLES, **{n: () for n in LISTS}}.items():
            got = got_lists[name] if name in LISTS else _csv(_rows(con, f'select * from "{name}"'), skip) if store_has(con, name) else ""
            want = (EXPECTED / f"{name}.csv").read_text() if (EXPECTED / f"{name}.csv").exists() else ""
            if got != want:
                g, w = got.splitlines(), want.splitlines()
                only_got, only_want = sorted(set(g) - set(w)), sorted(set(w) - set(g))
                diffs[name] = {"rows_got": max(0, len(g) - 1), "rows_want": max(0, len(w) - 1), "only_in_run": only_got[:5], "only_in_expected": only_want[:5],
                               "n_only_in_run": len(only_got), "n_only_in_expected": len(only_want)}
        con.close()
        return {"ok": not diffs, "root": str(root), "log": log, "diffs": diffs}
    finally:
        if not keep:
            shutil.rmtree(root, ignore_errors=True)
