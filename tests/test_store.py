"""Schema, contracts and data dictionary."""
import unittest

from ledger.store import SCHEMA, ContractError, data_dictionary, init, write

GOOD_VALUE = {"ticker": "NVDA", "field": "revenue", "period": "FY2026", "period_end": "2026-01-25", "value": 96221000000, "source": "agent",
              "method": "reported", "label": "agree", "basis": "as_reported", "first_reported": 96221000000, "extraction_ids": "x", "input_hash": "h"}


class Schema(unittest.TestCase):
    def test_init_creates_every_table_with_its_key(self):
        con = init(":memory:")
        names = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
        self.assertTrue({t.name for t in SCHEMA} <= names)
        self.assertEqual(len(SCHEMA), 8)

    def test_a_valid_row_round_trips(self):
        con = init(":memory:")
        write(con, "values", [GOOD_VALUE])
        self.assertEqual(con.execute('select value from "values"').fetchone()[0], 96221000000)


class Contracts(unittest.TestCase):
    def bad(self, table, row, needle):
        with self.assertRaises(ContractError) as e:
            write(init(":memory:"), table, [row])
        self.assertIn(needle, str(e.exception))

    def test_required(self):
        self.bad("values", {**GOOD_VALUE, "input_hash": None}, "values.input_hash is required")

    def test_type(self):
        self.bad("values", {**GOOD_VALUE, "value": 96.2}, "values.value must be BIGINT")

    def test_enum(self):
        self.bad("values", {**GOOD_VALUE, "field": "ebitda"}, "values.field must be one of")
        self.bad("values", {**GOOD_VALUE, "label": "close_enough"}, "values.label must be one of")

    def test_pattern(self):
        self.bad("values", {**GOOD_VALUE, "period": "2026"}, "does not match")

    def test_unknown_column(self):
        self.bad("values", {**GOOD_VALUE, "colour": "red"}, "unknown column")

    def test_missing_means_null_value(self):
        self.bad("values", {**GOOD_VALUE, "source": "missing"}, "null exactly when source is 'missing'")

    def test_override_needs_value(self):
        self.bad("decisions", {"decision_id": "d1", "exception_id": "e1", "kind": "override", "value": None, "reason": "r",
                               "reviewer": "Kenny Geiler", "decided_at": "2026-10-28T00:00:00Z", "input_hash": "h"}, "override needs a value")

    def test_duplicate_key_in_one_write(self):
        with self.assertRaises(ContractError):
            write(init(":memory:"), "values", [GOOD_VALUE, dict(GOOD_VALUE)])

    def test_key_collision_with_stored_row_rolls_back(self):
        con = init(":memory:")
        write(con, "values", [GOOD_VALUE])
        with self.assertRaises(ContractError):
            write(con, "values", [{**GOOD_VALUE, "period": "FY2025"}, GOOD_VALUE])
        self.assertEqual(con.execute('select count(*) from "values"').fetchone()[0], 1)


class Dictionary(unittest.TestCase):
    def test_every_column_is_documented(self):
        d = data_dictionary()
        for t in SCHEMA:
            self.assertIn(f"## `{t.name}`", d)
            for c in t.cols:
                self.assertIn(f"| `{c.name}` |", d)


if __name__ == "__main__":
    unittest.main()
