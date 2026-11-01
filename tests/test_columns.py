"""T32: every column of the taxonomy rows has one meaning and one vocabulary (store.TAXONOMY, schema v11).

Asserted on the synthetic rows of test_taxonomy and, when the golden fixtures carry it, on fixtures/expected/taxonomy.csv
(the frozen rows of the proven set)."""
import csv
import re
import unittest

from ledger import golden, status, store, taxonomy
try:
    from test_taxonomy import _con  # unittest discover -s tests
except ImportError:
    from tests.test_taxonomy import _con

NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def frozen() -> list[dict]:
    """The frozen taxonomy rows, typed back from CSV the way the API types a release file."""
    f = golden.EXPECTED / "taxonomy.csv"
    if not f.exists():
        return []
    with f.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            r[k] = None if v == "" else True if v == "True" else False if v == "False" else (float(v) if "." in v else int(v)) if NUMBER.match(v) else v
    return rows


class OneMeaningPerColumn(unittest.TestCase):
    def sets(self):
        return [("synthetic", taxonomy.rows(_con(), ["AMZN"])), ("frozen", frozen())]

    def test_every_row_has_every_declared_column_and_no_other(self):
        for name, rows in self.sets():
            for r in rows:
                self.assertEqual(tuple(r), taxonomy.COLUMNS, name)

    def test_vocabularies(self):
        for name, rows in self.sets():
            for c in store.TAXONOMY.cols:
                for r in rows:
                    v = r[c.name]
                    if v is None:
                        self.assertTrue(c.nullable, f"{name}: {c.name} is required, empty in {r['ticker']} {r['fiscal_year']} {r['category']} {r['reported_name']}")
                        continue
                    if c.enum:
                        self.assertIn(v, c.enum, f"{name}: {c.name}")
                    if c.pattern:
                        self.assertRegex(str(v), c.pattern, f"{name}: {c.name}")
                    if c.type == "BOOLEAN":
                        self.assertIsInstance(v, bool, f"{name}: {c.name}")

    def test_value_high_is_only_a_range_high(self):
        for name, rows in self.sets():
            for r in rows:
                if r["value_high"] is not None:
                    self.assertIn(r["measure"], ("planned", "company_stated_ai"), name)
                    self.assertIsNotNone(r["value"], name)
                    self.assertGreater(r["value_high"], r["value"], f"{name}: a range high is above its low")
                if r["measure"] in ("spent", "committed", "derived"):
                    self.assertIsNone(r["value_high"], name)

    def test_change_from_prior_is_only_the_derived_change(self):
        for name, rows in self.sets():
            for r in rows:
                if r["measure"] != "derived":
                    self.assertIsNone(r["change_from_prior"], name)
            derived = [r for r in rows if r["measure"] == "derived"]
            by = {(r["ticker"], r["reported_name"], r["fiscal_year"]): r for r in derived}
            for r in derived:
                if r["change_from_prior"] is not None:
                    prior = max((p for (t, n, y), p in by.items() if t == r["ticker"] and n == r["reported_name"] and y < r["fiscal_year"]), key=lambda p: p["fiscal_year"])
                    self.assertEqual(r["change_from_prior"], r["value"] - prior["value"], f"{name}: arithmetic on two reported balances, nothing else")

    def test_mapped_has_value_and_units_say_one_thing_each(self):
        for name, rows in self.sets():
            for r in rows:
                self.assertEqual(r["mapped"], r["check"] != "unmapped", name)
                self.assertEqual(r["has_value"], r["value"] is not None or r["share"] is not None, name)
                self.assertEqual((r["scale"], r["currency"]), (1, "USD"), name)
                self.assertEqual(r["unit"] == "share", r["share"] is not None, name)
                self.assertEqual(r["unit"] is None, not r["has_value"], f"{name}: no figure, no unit")
                if r["unit"] == "share":
                    self.assertIsNone(r["value"], name)

    def test_periods(self):
        for name, rows in self.sets():
            for r in rows:
                if r["measure"] in ("spent", "committed", "derived"):
                    self.assertEqual(r["period_kind"], "reported", name)
                    self.assertIsNotNone(r["period_end"], name)
                if r["measure"] == "planned":
                    self.assertEqual((r["period_kind"], r["period_end"]), ("planned", None), name)
                if r["measure"] == "company_stated_ai":  # reported only when the calendar knows the year's end and the source came after it
                    self.assertEqual(r["period_kind"] == "reported", r["period_end"] is not None, f"{name}: {r['ticker']} {r['fiscal_year']}")
                    if r["period_end"] and r["filed"]:
                        self.assertLessEqual(r["period_end"], r["filed"], name)
                    if r["kind"] == "outlook":
                        self.assertEqual(r["period_kind"], "planned", name)
                if r["period_kind"] == "planned":
                    self.assertIsNone(r["period_end"], name)

    def test_the_unpacked_tags_sit_only_where_the_measure_has_them(self):
        for name, rows in self.sets():
            for r in rows:
                verbatim = r["check"] == "verbatim"
                self.assertEqual(verbatim, r["quote"] is not None or r["measure"] in ("planned", "company_stated_ai"), name)
                if not verbatim:
                    for c in ("kind", "project_kind", "relation", "status", "location", "capacity_mw", "forward_looking", "part_year", "program", "period_as_stated", "quote"):
                        self.assertIsNone(r[c], f"{name}: {c} on a reported row")
                self.assertEqual(r["kind"] is not None, r["measure"] == "company_stated_ai" and r["source_kind"] != "gathered", name)  # one meaning: the statement's kind
                self.assertEqual(r["project_kind"] is not None, r["category"] == "project", name)
                self.assertEqual(r["relation"] is not None, r["source_kind"] == "gathered", name)
                if r["category"] == "project" or r["source_kind"] == "gathered":
                    self.assertIsNone(r["forward_looking"], f"{name}: the source does not say")
                if r["check_method"] == "quote" and r["category"] != "project":
                    self.assertIsNotNone(r["forward_looking"], name)
                if r["category"] == "project":
                    self.assertIsNotNone(r["status"], name)
                else:
                    for c in ("status", "location", "capacity_mw"):
                        self.assertIsNone(r[c], f"{name}: {c} off a project row")
                if r["category"] == "guidance":
                    self.assertTrue(r["forward_looking"], name)

    def test_check_method_is_a_known_kind(self):
        """An open vocabulary: `<kind>` or `<kind>:<id>`, the kind in status.METHOD_KINDS (one place; a new answer key is one entry there)."""
        for name, rows in self.sets():
            for r in rows:
                self.assertIn(status.method_kind(r["check_method"]), status.METHOD_KINDS, f"{name}: {r['check_method']}")

    def test_check_and_its_method_agree(self):
        for name, rows in self.sets():
            for r in rows:
                c, m = r["check"], r["check_method"]
                if c == "agree" or c == "differs":
                    self.assertEqual(m, "xbrl", name)
                if c == "no_reference":
                    self.assertEqual(m, "label:no_reference", name)
                if c == "unmapped":
                    self.assertEqual(m, "none", name)
                if c == "explained":
                    self.assertRegex(m, r"^(rule|definition|resolution):", name)
                if c == "verbatim":
                    self.assertIn(m, ("quote", "gathered"), name)
                    self.assertEqual(m == "gathered", r["source_kind"] == "gathered", name)
                if c == "unmapped":
                    self.assertEqual((r["measure"], r["standard_type"]), ("derived", None), name)

    def test_the_source_is_followed(self):
        for name, rows in self.sets():
            for r in rows:
                self.assertIsNotNone(r["source"], name)
                if r["source_kind"] in ("10-K table", "10-K note"):
                    self.assertIsNotNone(r["accession"], name)
                    self.assertIsNotNone(r["source_url"], name)
                    self.assertIn("sec.gov", r["source_url"], name)
                if r["source_kind"] == "gathered":
                    self.assertIsNone(r["accession"], name)


class Filters(unittest.TestCase):
    def test_a_boolean_filter_matches_false(self):
        from ledger import api
        rows = [{"ticker": "A", "has_value": True, "mapped": True}, {"ticker": "B", "has_value": False, "mapped": True}, {"ticker": "C", "has_value": None, "mapped": False}]
        self.assertEqual([r["ticker"] for r in api.apply(rows, {"has_value": "false"})], ["B"])  # False is a value, not an empty cell
        self.assertEqual([r["ticker"] for r in api.apply(rows, {"has_value": "true"})], ["A"])
        self.assertEqual([r["ticker"] for r in api.apply(rows, {"mapped": "FALSE"})], ["C"])


class GoldenRoot(unittest.TestCase):
    def test_decisions_are_part_of_the_expectation(self):
        """freeze reads the repo's decisions/ and check symlinks it into the root, so a person's resolution on a row is in the frozen check column and a new one shows as a diff."""
        self.assertIn("decisions", golden.SHARED)
        self.assertIn("taxonomy", golden.SHARED)
        self.assertTrue((store.ROOT / "decisions" / "resolutions.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
