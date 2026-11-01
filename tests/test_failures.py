"""taxonomy/failures.yaml loads; every type has a class and a check or none; every named check exists in code; the
Pareto sums to the number of types."""
import tempfile
import unittest
from pathlib import Path

from ledger.failures import CLASSES, ORIGINS, by_check, known_checks, load, pareto
from ledger.faults import FAULTS
from ledger.proof import GUARDS
from ledger.rules import load as load_rules


class Failures(unittest.TestCase):
    def test_the_file_loads_with_a_class_and_a_check_per_type(self):
        types = load()
        self.assertGreater(len(types), 0)
        ids = [t["id"] for t in types]
        self.assertEqual(ids, sorted(set(ids)))  # unique, sorted
        for t in types:
            self.assertIn(t["class"], CLASSES, t["id"])
            self.assertIn(t["origin"], ORIGINS, t["id"])
            self.assertTrue(t["check"], t["id"])

    def test_every_named_check_exists_in_code(self):
        in_code = {r["id"] for r in load_rules()} | {g["id"] for g in GUARDS} | set(FAULTS)
        self.assertEqual(known_checks(), in_code)
        for t in load():
            if t["check"] != "none":
                self.assertIn(t["check"], in_code, t["id"])

    def test_pareto_sums_to_the_number_of_types(self):
        types = load()
        p = pareto(types)
        self.assertEqual(p["total"], len(types))
        for key in ("by_class", "by_origin", "by_check"):
            self.assertEqual(sum(b["types"] for b in p[key]), len(types), key)
        self.assertEqual(p["none"], sum(1 for t in types if t["check"] == "none"))
        self.assertIn("none", {b["check"] for b in p["by_check"]})  # a none is counted as its own bar
        self.assertEqual(sum(len(v) for v in by_check(types).values()), len(types))

    def test_an_unknown_class_origin_or_check_is_refused(self):
        p = Path(tempfile.mkdtemp()) / "failures.yaml"
        ok = "name: x\n  origin: code\n  source: s\n  by: k\n  at: 2026-11-01\n  count: 1\n"
        p.write_text(f"1:\n  {ok}  class: weather\n  check: none\n  check_note: n\n")
        with self.assertRaises(ValueError):
            load(p)
        p.write_text(f"1:\n  {ok}  class: units\n  check: no_such_rule\n")
        with self.assertRaises(ValueError):
            load(p)
        p.write_text("1:\n  name: x\n  class: units\n  origin: elsewhere\n  check: sign\n  source: s\n  by: k\n  at: 2026-11-01\n  count: 1\n")
        with self.assertRaises(ValueError):
            load(p)
        p.write_text(f"1:\n  {ok}  class: units\n  check: sign\n")
        self.assertEqual(load(p)[0]["check"], "sign")

    def test_a_none_needs_a_note_a_null_count_needs_a_note_and_an_id_is_an_integer(self):
        p = Path(tempfile.mkdtemp()) / "failures.yaml"
        base = "name: x\n  class: units\n  origin: code\n  source: s\n  by: k\n  at: 2026-11-01\n"
        p.write_text(f"1:\n  {base}  check: none\n  count: 1\n")  # none without check_note
        with self.assertRaises(ValueError):
            load(p)
        p.write_text(f"1:\n  {base}  check: sign\n  count: null\n")  # null count without count_note
        with self.assertRaises(ValueError):
            load(p)
        p.write_text(f"one:\n  {base}  check: sign\n  count: 1\n")  # id not an integer
        with self.assertRaises(ValueError):
            load(p)
        p.write_text(f"1:\n  {base}  check: none\n  check_note: n\n  count: null\n  count_note: every filing\n")
        self.assertEqual(load(p)[0]["id"], 1)
