"""Publish a signed release to the production database (Postgres).

What goes to production is the release folder, the plain files whose hash a person signed: never the working
DuckDB. One table per release file plus `ledger_releases`; every row carries its release version, so a consumer can
pin a version or read the `current_*` views, which follow the highest published version. Publishing the same
version again replaces its rows in one transaction, so a rerun cannot leave half a release behind.

DATABASE_URL lives in .env (git-ignored), never in code or in a log.
"""
import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .release import RELEASES, content_hash

ROOT = Path(__file__).resolve().parents[1]
TABLES = {"values": "ledger_values", "facts": "ledger_facts", "ai_spend": "ledger_ai_spend", "attribution": "ledger_attribution"}
NUMERIC = {"value", "xbrl_value", "first_reported", "amount_low", "amount_high", "share", "ai_amount", "ai_share", "confidence"}
DATE = {"period_end"}


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not url:
        raise SystemExit("Set DATABASE_URL in .env (a Postgres connection string). It is never committed.")
    return url


class NotPublishable(Exception):
    pass


def check(version: str) -> dict:
    """A release publishes only when it is signed and its files still match the signed hash."""
    d = RELEASES / version
    if not (d / "manifest.json").exists():
        raise NotPublishable(f"no release {version}")
    m = json.loads((d / "manifest.json").read_text())
    if not (d / "SIGNOFF.json").exists():
        raise NotPublishable(f"{version} is not signed; a release goes to production only after the owner signs it")
    s = json.loads((d / "SIGNOFF.json").read_text())
    files = {n: (d / n).read_text() for n in m["files"]}
    if content_hash(files) != m["hash"] or s["hash"] != m["hash"]:
        raise NotPublishable(f"{version} files no longer match the signed hash; not published")
    return {"manifest": m, "signoff": s, "dir": d}


def columns(header: list[str]) -> list[tuple[str, str]]:
    return [(c, "numeric" if c in NUMERIC else "date" if c in DATE else "text") for c in header]


def ddl(name: str, header: list[str]) -> str:
    cols = ", ".join(f'"{c}" {t}' for c, t in columns(header))
    return f'CREATE TABLE IF NOT EXISTS {name} (release text NOT NULL, {cols})'


RELEASES_DDL = """CREATE TABLE IF NOT EXISTS ledger_releases (
  version text PRIMARY KEY, ordinal bigint NOT NULL, hash text NOT NULL, stage integer, prompt text, parser text, model text,
  signed_by text NOT NULL, signed_at timestamptz NOT NULL, published_at timestamptz NOT NULL, rows jsonb NOT NULL)"""


def ordinal(version: str) -> int:
    """v1.4.0 -> 1004000: the current_* views follow the highest version, not the last one published."""
    a, b, c = (int(x) for x in version.lstrip("v").split("."))
    return a * 1_000_000 + b * 1_000 + c


def rows(path: Path) -> tuple[list[str], list[list]]:
    with path.open(newline="") as f:
        r = csv.reader(f)
        header = next(r)
        body = [[(None if v == "" else v) for v in row] for row in r]
    return header, body


def publish(version: str, url: str | None = None) -> dict:
    import psycopg

    rel = check(version)
    m, s, d = rel["manifest"], rel["signoff"], rel["dir"]
    counts = {}
    with psycopg.connect(url or database_url()) as con:
        with con.transaction():
            con.execute(RELEASES_DDL)
            for stem, table in TABLES.items():
                header, body = rows(d / f"{stem}.csv")
                con.execute(ddl(table, header))
                con.execute(f"DELETE FROM {table} WHERE release = %s", (version,))
                cols = ", ".join(f'"{c}"' for c in header)
                with con.cursor().copy(f"COPY {table} (release, {cols}) FROM STDIN") as cp:
                    for row in body:
                        cp.write_row([version, *row])
                counts[stem] = len(body)
                con.execute(f"CREATE INDEX IF NOT EXISTS {table}_release_ticker ON {table} (release, ticker)")
                # current_<stem>: the latest published release, by publish time
                con.execute(f"""CREATE OR REPLACE VIEW current_{stem} AS
                    SELECT t.* FROM {table} t WHERE t.release = (SELECT version FROM ledger_releases ORDER BY ordinal DESC LIMIT 1)""")
            con.execute("""INSERT INTO ledger_releases (version, ordinal, hash, stage, prompt, parser, model, signed_by, signed_at, published_at, rows)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (version) DO UPDATE SET hash = EXCLUDED.hash, published_at = EXCLUDED.published_at, rows = EXCLUDED.rows""",
                        (version, ordinal(version), m["hash"], m.get("stage"), m.get("prompt"), m.get("parser"), m.get("model"),
                         s["signed_by"], s["signed_at"], datetime.now(timezone.utc), json.dumps(counts)))
    return {"version": version, "hash": m["hash"], "rows": counts}


def status(url: str | None = None) -> list[dict]:
    import psycopg

    with psycopg.connect(url or database_url()) as con:
        if not con.execute("SELECT to_regclass('ledger_releases')").fetchone()[0]:
            return []
        cur = con.execute("SELECT version, hash, signed_by, signed_at, published_at, rows FROM ledger_releases ORDER BY ordinal DESC")
        return [dict(zip([c.name for c in cur.description], r)) for r in cur.fetchall()]
