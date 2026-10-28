"""T33: every rule has a fixture it passes and a fixture it fails, and the registry loads cleanly."""
import copy
import unittest
from pathlib import Path

from ledger.ingest.statements import assemble, locate
from ledger.ingest.tables import document_units, parse_tables
from ledger.rules import CHECKS, Context, load, run

FIX = Path(__file__).parent / "fixtures" / "filings" / "NVDA_10-Q_2026-07-26.html"
ACC = "0001045810-26-000075"
RULES = {r["id"]: r for r in load()}


def parsed():
    doc = FIX.read_bytes()
    t = parse_tables(doc)
    loc, u = locate(t), document_units(doc)
    return {"accession": ACC, "ticker": "NVDA", "statements": {k: assemble(t, loc[k], u) for k in ("income", "cash_flow")}}


def ext(field, start, end, value, cell, row, col, table="t0000", accession=ACC, unit_source="table"):
    return {"extraction_id": f"{accession}|{field}|{start}|{end}", "accession": accession, "ticker": "NVDA", "field": field, "filed": "2026-08-26",
            "period_start": start, "period_end": end, "value": value, "unit_stated": "(In millions)", "unit_source": unit_source,
            "scale": 1_000_000, "table_id": table, "row_label": row, "column_label": col, "cell_text": cell}


def val(field, q, value, ids="", label="agree", source="override"):
    return {"ticker": "NVDA", "field": field, "cal_q": q, "value": value, "source": source, "method": "reported", "label": label, "extraction_ids": ids}


REV = ext("revenue", "2026-04-27", "2026-07-26", 96221000000, "96,221", "Revenue", "Three Months Ended | Jul 26, 2026")
GOOD = Context(
    values=[val("revenue", "2026Q2", 96221000000, REV["extraction_id"], source="agent"), val("cost_of_revenue", "2026Q2", 24079000000),
            val("operating_income", "2026Q2", 63734000000), val("capex", "2026Q2", 2677000000),
            val("revenue", "2026Q1", 81615000000), val("capex", "2026Q1", 1757000000),
            val("revenue", "2025Q4", 68127000000), val("capex", "2025Q4", 1500000000),
            val("revenue", "2025Q3", 57006000000), val("capex", "2025Q3", 1600000000)],
    extractions=[REV,
                 ext("operating_income", "2026-01-26", "2026-04-26", 30, "30", "Operating income", "x"),
                 ext("operating_income", "2026-04-27", "2026-07-26", 30, "30", "Operating income", "x", accession="0001045810-26-000076"),
                 ext("operating_income", "2026-07-27", "2026-10-25", 40, "40", "Operating income", "x", accession="0001045810-26-000077"),
                 ext("operating_income", "2026-01-26", "2026-10-25", 100, "100", "Operating income", "x", accession="0001045810-26-000077")],
    parsed={ACC: parsed()}, quarters=["2025Q3", "2025Q4", "2026Q1", "2026Q2"],
)
# The good context's extractions sum: 30 + 30 + 40 = 100 for the nine-month cell. Values above are in dollars but the
# sum rule only compares extractions with each other, so small numbers keep the fixture readable.
GOOD.extractions[1]["scale"] = GOOD.extractions[2]["scale"] = GOOD.extractions[3]["scale"] = GOOD.extractions[4]["scale"] = 1


# The good fixture carries every field only for revenue; the coverage rule is checked on that field alone.
PARAMS = {"coverage": {"fields": ["revenue"]}}


# The fixture's sum-check cells are synthetic; the citation rule is checked on the one real cell (REV).
ONLY_REAL_CELL = {"citation_resolves"}


def findings(rule_id, ctx):
    r = RULES[rule_id]
    if rule_id in ONLY_REAL_CELL:
        ctx = copy.copy(ctx)
        ctx.extractions = ctx.extractions[:1]
    return CHECKS[r["check"]](ctx, PARAMS.get(rule_id, r["params"]))


def bad(mutate):
    ctx = copy.deepcopy(GOOD)
    mutate(ctx)
    return ctx


FAIL = {
    "citation_resolves": lambda c: c.extractions[0].update(cell_text="96,222"),  # checked whether or not the cell ships
    "unit_from_document": lambda c: c.extractions[0].update(unit_source="document"),
    "period_length": lambda c: c.extractions[0].update(period_start="2026-05-27"),
    "column_matches_period": lambda c: c.extractions[0].update(column_label="Three Months Ended | Jul 27, 2025"),
    "row_label_switch": lambda c: c.extractions[2].update(row_label="Income from operations"),
    "definition_note": lambda c: c.extractions.append(ext("capex", "2026-01-26", "2026-07-26", 4434000000, "(4,434)", "Purchases related to property and equipment and intangible assets", "Six Months Ended | Jul 26, 2026", "t0001")),
    "quarters_sum_to_ytd": lambda c: c.extractions[4].update(value=110),
    "statement_tie": lambda c: next(r for r in c.parsed[ACC]["statements"]["income"][0]["rows"] if r["label"] == "Operating income")["cells"][0].update(value=63000),
    "sign": lambda c: c.values[3].update(value=-2677000000),
    "magnitude": lambda c: c.values[1].update(value=99000000000),
    "jump": lambda c: c.values[4].update(value=10000000000),
    "coverage": lambda c: c.values.pop(4),
    "restated": lambda c: c.extractions.append({**c.extractions[2], "accession": "0001045810-26-000099", "value": 31}),
    "xbrl_reconcile": lambda c: c.values[0].update(label="unresolved"),
    "outlier_vs_own_history": lambda c: c.values[3].update(value=20000000000),
}


class Registry(unittest.TestCase):
    def test_every_rule_loads_with_rationale_and_owner(self):
        self.assertEqual(len(RULES), 15)
        for r in RULES.values():
            self.assertTrue(r["rationale"].strip() and r["owner"].strip(), r["id"])

    def test_every_rule_has_a_failing_fixture(self):
        self.assertEqual(set(FAIL), set(RULES))


class EachRule(unittest.TestCase):
    pass


def _make(rule_id):
    def passes(self):
        self.assertEqual(findings(rule_id, GOOD), [], f"{rule_id} fired on the good fixture")

    def fails(self):
        self.assertTrue(findings(rule_id, bad(FAIL[rule_id])), f"{rule_id} did not fire on its failing fixture")
    return passes, fails


for _rid in sorted(RULES):
    _p, _f = _make(_rid)
    setattr(EachRule, f"test_{_rid}_passes", _p)
    setattr(EachRule, f"test_{_rid}_fails", _f)


class Engine(unittest.TestCase):
    def test_run_is_deterministic_and_ids_are_stable(self):
        ctx = bad(FAIL["sign"])
        a, b = run(ctx, list(RULES.values())), run(ctx, list(RULES.values()))
        self.assertEqual(a, b)
        self.assertTrue(any(e["exception_id"].startswith("sign|NVDA|capex|2026Q2") for e in a))

    def test_unknown_check_fails_at_load(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            Path(d, "x.yaml").write_text("id: x\nseverity: block\ndescription: d\nrationale: r\nowner: o\ntitle: t\nplain: p\naction: a\ncheck: no_such_check\n")
            with self.assertRaises(ValueError):
                load(Path(d))


if __name__ == "__main__":
    unittest.main()
