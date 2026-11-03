"""publish against a real Postgres: a column an older release published as text is retyped boolean although the
current_* view depends on it (the view is dropped for the retype and recreated by the publish).

Needs a Postgres: LEDGER_TEST_PG (a connection string), or the ephemeral one in the docstring of `_url`. Skipped with the
reason otherwise."""
import os
import unittest

from ledger.release import publish


def _url() -> str | None:
    """LEDGER_TEST_PG, else a local throwaway on port 55433 (`docker run --rm -e POSTGRES_PASSWORD=x -p 55433:5432 postgres:16`) when it answers."""
    url = os.environ.get("LEDGER_TEST_PG") or "postgresql://postgres:x@127.0.0.1:55433/postgres"
    try:
        import psycopg
        with psycopg.connect(url, connect_timeout=2):
            return url
    except Exception:
        return None


URL = _url()


@unittest.skipIf(URL is None, "no Postgres reachable: set LEDGER_TEST_PG or run the throwaway container named in tests/test_publish_pg.py")
class RetypeUnderAView(unittest.TestCase):
    def test_text_column_becomes_boolean_although_current_view_depends_on_it(self):
        import psycopg
        table, stem = "ledger_taxonomy_test", "taxonomy_test"
        with psycopg.connect(URL) as con:
            con.execute(f"DROP VIEW IF EXISTS current_{stem}")
            con.execute(f"DROP TABLE IF EXISTS {table}")
            con.execute(f"CREATE TABLE {table} (release text NOT NULL, ticker text, proven text)")  # as v1.7.0 published it
            con.execute(f"INSERT INTO {table} VALUES ('v1.7.0', 'MSFT', 'True'), ('v1.7.0', 'MU', 'False')")
            con.execute(f"CREATE VIEW current_{stem} AS SELECT t.* FROM {table} t")
            con.commit()
            header = ["ticker", "proven", "mapped"]
            with con.transaction():  # the steps publish() runs for one table
                for stmt in publish.adds(table, header):
                    con.execute(stmt)
                fixes = publish.retypes(table, header, publish._types(con, table))
                self.assertEqual(len(fixes), 1)
                with self.assertRaises(psycopg.errors.FeatureNotSupported):  # what the block found: the view holds the column's type
                    with con.transaction():
                        con.execute(fixes[0])
                con.execute(f"DROP VIEW IF EXISTS current_{stem}")
                for stmt in fixes:
                    con.execute(stmt)
                con.execute(f"CREATE OR REPLACE VIEW current_{stem} AS SELECT t.* FROM {table} t")
            self.assertEqual(publish._types(con, table)["proven"], "boolean")
            self.assertEqual(con.execute(f"SELECT ticker, proven FROM current_{stem} ORDER BY ticker").fetchall(), [("MSFT", True), ("MU", False)])
            self.assertEqual(publish.retypes(table, header, publish._types(con, table)), [])  # once
            con.execute(f"DROP VIEW current_{stem}")
            con.execute(f"DROP TABLE {table}")
            con.commit()


if __name__ == "__main__":
    unittest.main()
