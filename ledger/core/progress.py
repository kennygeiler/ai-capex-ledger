"""Where a `ledger run` stands, for Kenny's Data Emporium's add-a-company page: data/jobs/progress.json.

`ledger run` writes it before the first step and after every step. Each step's one-line summary comes from what the
step left behind (rows in the store, the fault and evidence reports), never from what it printed, so a changed print
can't blank the page."""
import json
from datetime import datetime, timezone
from pathlib import Path

from . import store
from ..extract.extract import OUTPUTS
from ..extract.guidance import OUTPUTS as AI_OUTPUTS
from ..extract.notes import OUTPUTS as NOTE_OUTPUTS
from .steps import STEPS  # noqa: F401  re-exported: `ledger run`, Kenny's Data Emporium and the Airflow DAG all read it from here or from steps

FILE = store.ROOT / "data" / "jobs" / "progress.json"

def write(run_id: str, name: str, tickers: list[str], steps: list[dict], running: bool) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps({"run_id": run_id, "scope": name, "tickers": tickers, "running": running, "steps": steps,
                                "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=1))


def read() -> dict | None:
    return json.loads(FILE.read_text()) if FILE.exists() else None


def summary(con, cmd: str, extra: list[str], tickers: list[str], name: str, started_at: str) -> str:
    """One plain sentence on what the step left in the store and the report files."""
    one = lambda sql: con.execute(sql, [tickers]).fetchone()
    t = "where ticker in (select unnest(?))"
    if cmd == "ingest":
        n, missing = one(f"select count(*), count(*) filter (where form = '10-K' and (income_tables is null or cash_flow_tables is null)) from documents {t}")
        return f"{n} filings found; " + ("statements located in every one" if not missing else f"{missing} without both statements located")
    if cmd == "extract" and extra == ["--run"]:
        since = datetime.fromisoformat(started_at).timestamp()
        outs = [OUTPUTS / f"{a}.json" for (a,) in con.execute(f"select accession from documents {t}", [tickers]).fetchall()]
        fresh = [json.loads(o.read_text()).get("_run") or {} for o in outs if o.exists() and o.stat().st_mtime >= since]
        return f"Read {len(fresh)} filing{'s' * (len(fresh) != 1)}, {sum(max(r.get('attempts', 1) - 1, 0) for r in fresh)} retries" if fresh else "Every filing was already read"
    if cmd == "extract":
        n, = one(f"select count(*) from extractions {t}")
        failed, = one(f"select count(*) from exceptions {t} and rule_id = 'extraction_failed'")
        return f"{n} cited cells checked against the tables; {failed} failed"
    if cmd == "reconcile":
        n, agree = one(f"select count(*), count(*) filter (where label = 'agree') from \"values\" {t}")
        return f"{n} yearly values; {agree} match the SEC's data"
    if cmd == "texts":
        n, kinds = one(f"select count(*), count(distinct kind) from texts {t}")
        return f"{n} texts of {kinds} kind{'s' * (kinds != 1)}"
    if cmd == "aispend" and extra == ["--run"]:
        since = datetime.fromisoformat(started_at).timestamp()
        outs = [AI_OUTPUTS / f"{i}.json" for (i,) in con.execute(f"select text_id from texts {t}", [tickers]).fetchall()]
        fresh = [o for o in outs if o.exists() and o.stat().st_mtime >= since]
        return f"Read {len(fresh)} text{'s' * (len(fresh) != 1)}" if fresh else "Every text was already read"
    if cmd == "aispend":
        n, = one(f"select count(*) from ai_statements {t}")
        rows, ai = one(f"select count(*), count(*) filter (where scope = 'ai' and class <> 'qualitative') from ai_spend {t}")
        return f"{n} statements quoted; {rows} company-years speak to AI spend, {ai} with a stated AI figure"
    if cmd == "notes" and extra == ["--run"]:
        since = datetime.fromisoformat(started_at).timestamp()
        outs = [NOTE_OUTPUTS / f"{a}.json" for (a,) in con.execute(f"select accession from documents {t}", [tickers]).fetchall()]
        fresh = [o for o in outs if o.exists() and o.stat().st_mtime >= since]
        return f"Read {len(fresh)} filing{'s' * (len(fresh) != 1)}" if fresh else "Every filing was already read"
    if cmd == "notes":
        n, = one(f"select count(*) from note_extractions {t}")
        rows, agree = one(f"select count(*), count(*) filter (where label = 'agree') from facts {t}")
        return f"{n} cited cells; {rows} facts, {agree} match the filing's XBRL"
    if cmd == "rules":
        r, = con.execute("select count(*) from rules").fetchone()
        b, w, i = one(f"select count(*) filter (where severity = 'block'), count(*) filter (where severity = 'warn'), count(*) filter (where severity = 'info') from exceptions {t}")
        return f"{r} checks: {b} blocking, {w} warnings, {i} note{'s' * (i != 1)}"
    if cmd == "faults":
        f = store.ROOT / "reports" / f"{name}-faults.json"
        from ..checks.faults import rows_of
        rows = rows_of(json.loads(f.read_text())) if f.exists() else []
        return f"{len(rows):,} planted mistakes, {sum(r['outcome'] == 'escaped' for r in rows)} got through" if rows else "No faults planted"
    if cmd == "evidence":
        f = store.ROOT / "reports" / "evidence" / f"{name}.json"
        res = json.loads(f.read_text()) if f.exists() else {}
        return f"{sum(bool(r['match']) for r in res.values())} of {len(res)} cited cells confirmed on the rendered 10-K"
    if cmd == "report":
        return "Review page written" if (store.ROOT / "reports" / f"{name}-validation.html").exists() else "No page written"
    return ""
