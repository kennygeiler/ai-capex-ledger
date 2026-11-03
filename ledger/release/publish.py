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

ROOT = Path(os.environ["LEDGER_ROOT"]).resolve() if os.environ.get("LEDGER_ROOT") else Path(__file__).resolve().parents[2]
TABLES = {"values": "ledger_values", "facts": "ledger_facts", "ai_spend": "ledger_ai_spend", "companies": "ledger_companies",
          "statements": "ledger_statements", "projects": "ledger_projects", "taxonomy": "ledger_taxonomy"}  # one shape: the API's lists (C7); a release without a file skips it
NUMERIC = {"value", "value_high", "change_from_prior", "xbrl_value", "first_reported", "amount_low", "amount_high", "share", "amount_mid", "capacity_mw", "scale", "sic", "gpus"}
DATE = {"period_end", "filed", "date"}
BOOLEAN = {"mapped", "has_value", "forward_looking", "part_year", "program", "proven", "latest"}  # schema v11 (taxonomy.csv) and the lists' own flags


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
    files = {n: (d / n).open(newline="").read() for n in m["files"]}  # exact bytes: the hash was taken before the write
    if content_hash(files) != m["hash"] or s["hash"] != m["hash"]:
        raise NotPublishable(f"{version} files no longer match the signed hash; not published")
    return {"manifest": m, "signoff": s, "dir": d}


def columns(header: list[str]) -> list[tuple[str, str]]:
    return [(c, "numeric" if c in NUMERIC else "date" if c in DATE else "boolean" if c in BOOLEAN else "text") for c in header]


def ddl(name: str, header: list[str]) -> str:
    cols = ", ".join(f'"{c}" {t}' for c, t in columns(header))
    return f'CREATE TABLE IF NOT EXISTS {name} (release text NOT NULL, {cols})'


def adds(name: str, header: list[str]) -> list[str]:
    """One ALTER per column, so a release with a new column (v1.6.0 added status and flag) loads into a table an older
    release created; a column that exists is left alone, and older releases' rows carry NULL in the new one."""
    return [f'ALTER TABLE {name} ADD COLUMN IF NOT EXISTS "{c}" {t}' for c, t in columns(header)]


def retypes(name: str, header: list[str], current: dict[str, str]) -> list[str]:
    """One ALTER per column whose published type is text but whose declared type is now boolean (v1.7.0 published
    `proven` as text; schema v11 types it boolean): the column is converted in place, 'True'/'true' to true, the rest
    false, once. `current` is {column: data_type} from information_schema; a column already boolean gets nothing."""
    return [f'ALTER TABLE {name} ALTER COLUMN "{c}" TYPE boolean USING ("{c}" = \'True\' OR "{c}" = \'true\')'
            for c, t in columns(header) if t == "boolean" and current.get(c, "boolean") != "boolean"]


def _types(con, name: str) -> dict[str, str]:
    return {c: t for c, t in con.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s", (name,)).fetchall()}


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
                if not (d / f"{stem}.csv").exists():
                    continue  # an older release without this list
                header, body = rows(d / f"{stem}.csv")
                con.execute(ddl(table, header))
                for stmt in adds(table, header):
                    con.execute(stmt)
                fixes = retypes(table, header, _types(con, table))  # a column an older release published as text, typed boolean now
                if fixes:
                    con.execute(f"DROP VIEW IF EXISTS current_{stem}")  # the view depends on every column, so Postgres refuses the retype while it stands; recreated below
                    for stmt in fixes:
                        con.execute(stmt)
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
