"""python -m ledger publish <version> | --status

Publishes a signed release (its plain files, never the working database) to the production Postgres named by
DATABASE_URL in .env. Refuses an unsigned release or one whose files no longer match the signed hash. Publishing the
same version again replaces its rows in one transaction. --status lists what production holds."""
import argparse

from ..release.publish import NotPublishable, publish, status


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger publish")
    ap.add_argument("version", nargs="?")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--db-url", help="override DATABASE_URL (tests)")
    a = ap.parse_args(argv)
    if a.status or not a.version:
        rels = status(a.db_url)
        if not rels:
            print("production holds no release yet")
        for r in rels:
            print(f"{r['version']}  {r['hash'][:12]}  signed by {r['signed_by']} {r['signed_at']:%Y-%m-%d}  published {r['published_at']:%Y-%m-%d %H:%M}Z  "
                  + ", ".join(f"{v} {k}" for k, v in r["rows"].items()))
        return 0
    try:
        r = publish(a.version, a.db_url)
    except NotPublishable as e:
        print(f"not published: {e}")
        return 1
    current = status(a.db_url)[0]["version"]
    print(f"{r['version']} ({r['hash'][:12]}) published: " + ", ".join(f"{v} {k}" for k, v in r["rows"].items())
          + (f"; current_* views point at it" if current == r["version"] else f"; current_* views stay on {current}, the highest version"))
    return 0
