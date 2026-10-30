"""Every rule has a fixture it passes and a fixture it fails, and the registry loads cleanly."""
import copy
from datetime import date
import unittest
from pathlib import Path

from ledger.ingest.statements import assemble, locate
from ledger.ingest.tables import document_units, parse_tables
from ledger.rules import CHECKS, Context, load, run

FIX = Path(__file__).parent / "fixtures" / "filings" / "ORCL_10-K_2026-05-31.html"
ACC = "0001193125-26-277521"
RULES = {r["id"]: r for r in load()}


def parsed():
    doc = FIX.read_bytes()
    t = parse_tables(doc)
    loc, u = locate(t), document_units(doc)
    return {"accession": ACC, "ticker": "ORCL", "statements": {k: assemble(t, loc[k], u) for k in ("income", "cash_flow")}}


def ext(field, start, end, value, cell, row, col, table="t0000", accession=ACC, unit_source="table", filed="2026-06-20"):
    return {"extraction_id": f"{accession}|{field}|{start}|{end}", "accession": accession, "ticker": "ORCL", "field": field, "filed": filed,
            "period_start": start, "period_end": end, "value": value, "unit_stated": "(in millions)", "unit_source": unit_source,
            "scale": 1_000_000, "table_id": table, "row_label": row, "column_label": col, "cell_text": cell}


def val(field, period, value, ids="", label="agree", source="override"):
    return {"ticker": "ORCL", "field": field, "period": period, "value": value, "source": source, "method": "reported", "label": label, "extraction_ids": ids}


# Oracle has no cost-of-revenue line, so the statement tie is checked on NVIDIA's income statement.
NVDA = Path(__file__).parent / "fixtures" / "filings" / "NVDA_10-Q_2026-07-26.html"


def nvda_parsed():
    doc = NVDA.read_bytes()
    t = parse_tables(doc)
    loc, u = locate(t), document_units(doc)
    return {"accession": "nvda", "ticker": "NVDA", "statements": {k: assemble(t, loc[k], u) for k in ("income", "cash_flow")}}


# One real 10-K cell (Oracle FY2026 total revenues) plus synthetic fiscal-year cells for the cross-filing rules.
REV = ext("revenue", "2025-06-01", "2026-05-31", 67357000000, "67,357", "Total revenues", "Year Ended May 31, | 2026")
GOOD = Context(
    values=[val("revenue", "FY2026", 67357000000, REV["extraction_id"], source="agent"), val("capex", "FY2026", 25000000000),
            val("revenue", "FY2025", 57399000000), val("capex", "FY2025", 21215000000),
            val("revenue", "FY2024", 52961000000), val("capex", "FY2024", 18000000000),
            val("revenue", "FY2023", 49954000000), val("capex", "FY2023", 16000000000)],
    extractions=[REV,
                 ext("operating_income", "2023-06-01", "2024-05-31", 15353, "15,353", "Operating income", "x", accession="0000950170-24-075605"),
                 ext("operating_income", "2024-06-01", "2025-05-31", 17678, "17,678", "Operating income", "x", accession="0000950170-25-087926"),
                 ext("operating_income", "2025-06-01", "2026-05-31", 20606, "20,606", "Operating income", "x")],
    parsed={ACC: parsed(), "nvda": nvda_parsed()}, years=["FY2023", "FY2024", "FY2025", "FY2026"],
)
for x in GOOD.extractions[1:]:
    x["scale"] = 1


# The good fixture carries every field only for revenue; the coverage rule is checked on that field alone.
PARAMS = {"coverage": {"fields": ["revenue"]}}


# The fixture's cross-filing cells are synthetic; the citation rule is checked on the one real cell (REV).
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
    "citation_resolves": lambda c: c.extractions[0].update(cell_text="67,358"),  # checked whether or not the cell ships
    "cost_lines_summed": lambda c: c.extractions.append(ext("cost_of_revenue_part", "2025-06-01", "2026-05-31", 1, "1", "Hardware", "x")),
    "unit_from_document": lambda c: c.extractions[0].update(unit_source="document"),
    "period_length": lambda c: c.extractions[0].update(period_start="2025-12-01"),
    "column_matches_period": lambda c: c.extractions[0].update(column_label="Year Ended May 31, | 2025"),
    "row_label_switch": lambda c: c.extractions[2].update(row_label="Income from operations"),
    "definition_note": lambda c: c.extractions.append(ext("capex", "2025-06-01", "2026-05-31", 1, "1", "Purchases of property and equipment and intangible assets", "x")),
    "statement_tie": lambda c: next(r for r in c.parsed["nvda"]["statements"]["income"][0]["rows"] if r["label"] == "Operating income")["cells"][0].update(value=60000),
    "sign": lambda c: c.values[1].update(value=-25000000000),
    "jump": lambda c: c.values[0].update(value=300000000000),
    "coverage": lambda c: c.values.pop(2),
    "no_10k_yet": lambda c: c.tickers.append("SPCX"),
    "restated": lambda c: c.extractions.append({**c.extractions[2], "accession": "0001193125-26-000099", "value": 99999}),
    "xbrl_reconcile": lambda c: c.values[0].update(label="unresolved"),
    "outlier_vs_own_history": lambda c: c.values[1].update(value=150000000000),
    "ai_amount_within_capex": lambda c: c.ai_spend.append({"ticker": "ORCL", "field": "capex", "period": "FY2026", "kind": "actual", "scope": "ai", "class": "explicit_amount",
                                                           "amount_low": 30000000000, "amount_high": 30000000000, "share": None, "ai_amount": 30000000000,
                                                           "quote": "We spent $30 billion on AI infrastructure.", "accession": ACC, "statement_ids": "x", "input_hash": "h"}),
}


class Registry(unittest.TestCase):
    def test_every_rule_loads_with_rationale_and_owner(self):
        self.assertEqual(len(RULES), 16)
        for r in RULES.values():
            self.assertTrue(r["rationale"].strip() and r["owner"].strip(), r["id"])

    def test_every_rule_has_a_failing_fixture(self):
        self.assertEqual(set(FAIL), set(RULES))


class EachRule(unittest.TestCase):
    pass


class Restated(unittest.TestCase):
    PART = ("cost_of_revenue_part", "2024-06-01", "2025-05-31")

    def test_separate_cost_lines_in_one_filing_are_not_a_restatement(self):
        lines = lambda c: c.extractions.extend([ext(*self.PART, 11_569_000_000, "11,569", "Cloud and license", "2025"),
                                                ext(*self.PART, 782_000_000, "782", "Hardware", "2025")])
        self.assertEqual(findings("restated", bad(lines)), [])

    def test_one_cost_line_changed_between_filings_is(self):
        moved = lambda c: c.extractions.extend([ext(*self.PART, 782_000_000, "782", "Hardware", "2025"),
                                                ext(*self.PART, 790_000_000, "790", "Hardware", "2025", accession="0001193125-26-000099")])
        self.assertEqual(len(findings("restated", bad(moved))), 1)


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


class Coverage(unittest.TestCase):
    def test_a_year_whose_10k_isnt_due_is_not_missing(self):
        vals = [{**val("revenue", "FY2025", 1), "period_end": "2025-12-31"}]
        ctx = lambda today: Context(values=vals, extractions=[], years=["FY2025", "FY2026"], today=today)
        self.assertEqual(run(ctx(date(2026, 10, 28)), [RULES["coverage"] | {"params": {"fields": ["revenue"], "filing_days": 90}}]), [])
        self.assertTrue(run(ctx(date(2027, 4, 1)), [RULES["coverage"] | {"params": {"fields": ["revenue"], "filing_days": 90}}]))


class StatementTie(unittest.TestCase):
    def test_operating_lines_outside_the_opex_block_count(self):  # Core Scientific's layout
        row = lambda label, v=None: {"label": label, "cells": [] if v is None else [{"col": 0, "value": v}]}
        rows = [row("Total revenue", 640), row("Total cost of revenue", 632), row("Gross profit", 8), row("Impairment of goodwill", -1059),
                row("Operating expenses:"), row("General and administrative", 213), row("Total operating expenses", 253), row("Operating (loss) income", -1304)]
        doc = lambda rs: {"x": {"ticker": "CORZ", "statements": {"income": [{"id": "t0", "columns": ["2022"], "rows": rs}]}}}
        tie = lambda rs: CHECKS["statement_tie"](Context(values=[], extractions=[], parsed=doc(rs)), RULES["statement_tie"]["params"])
        self.assertEqual(tie(rows), [])
        self.assertTrue(tie(rows[:-1] + [row("Operating (loss) income", -1300)]))


class CostLines(unittest.TestCase):
    def test_row_switch_ignores_cost_lines(self):
        lines = lambda c: c.extractions.extend(ext("cost_of_revenue_part", "2025-06-01", "2026-05-31", 1, "1", n, "x") for n in ("Hardware", "Services"))
        self.assertEqual(findings("row_label_switch", bad(lines)), [])

    def test_a_year_with_different_cost_lines_is_caught(self):
        def lines(c):
            for end, names in (("2025-05-31", ("Hardware", "Services")), ("2026-05-31", ("Services", "Services"))):
                c.extractions.extend({**ext("cost_of_revenue_part", end[:4] + "-06-01", end, 1, "1", n, "x"), "extraction_id": f"{end}|{i}"} for i, n in enumerate(names))
        self.assertTrue(findings("row_label_switch", bad(lines)))


class Engine(unittest.TestCase):
    def test_run_is_deterministic_and_ids_are_stable(self):
        ctx = bad(FAIL["sign"])
        a, b = run(ctx, list(RULES.values())), run(ctx, list(RULES.values()))
        self.assertEqual(a, b)
        self.assertTrue(any(e["exception_id"].startswith("sign|ORCL|capex|FY2026") for e in a))

    def test_unknown_check_fails_at_load(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            Path(d, "x.yaml").write_text("id: x\nseverity: block\ndescription: d\nrationale: r\nowner: o\ntitle: t\nplain: p\naction: a\ncheck: no_such_check\n")
            with self.assertRaises(ValueError):
                load(Path(d))


if __name__ == "__main__":
    unittest.main()


class FiftyThreeWeekYear(unittest.TestCase):
    def test_column_named_by_prior_year_is_accepted(self):
        from ledger import rules as R
        ctx = type("C", (), {})()
        ok = {"ticker": "CDNS", "field": "capex", "column_label": "2020", "period_end": "2021-01-02", "period_start": "2019-12-29", "extraction_id": "e1"}
        bad = {**ok, "column_label": "2019", "extraction_id": "e2"}
        plain = {**ok, "column_label": "2020", "period_end": "2021-06-30", "period_start": "2020-07-01", "extraction_id": "e3"}
        ctx.extractions = [ok, bad, plain]
        out = R._column_period(ctx, {})
        self.assertEqual(sorted(f.subject for f in out), ["e2", "e3"])
