"""The table parser and statement locator on real filing excerpts (tests/fixtures/filings/)."""
import json
import unittest
from pathlib import Path

from ledger.ingest.statements import assemble, locate
from ledger.ingest.tables import document_units, parse_number, parse_tables

FIX = Path(__file__).parent / "fixtures" / "filings"


def statement(name: str, kind: str) -> list[dict]:
    doc = (FIX / name).read_bytes()
    tables = parse_tables(doc)
    return assemble(tables, locate(tables)[kind], document_units(doc))


def cell(tables: list[dict], label: str, column: str) -> dict:
    for t in tables:
        for r in t["rows"]:
            if r["label"] == label:
                for c in r["cells"]:
                    if t["columns"][c["col"]] == column:
                        return c
    raise AssertionError(f"no cell {label!r} / {column!r}")


class Numbers(unittest.TestCase):
    def test_reader_conventions(self):
        self.assertEqual(parse_number("96,221"), 96221)
        self.assertEqual(parse_number("(4,434)"), -4434)
        self.assertEqual(parse_number("—"), 0)
        self.assertEqual(parse_number("1.5"), 1.5)
        self.assertIsNone(parse_number("Revenue"))
        self.assertIsNone(parse_number(""))


class Nvidia10Q(unittest.TestCase):
    """Quarter and year-to-date columns side by side; cash flow is year-to-date only."""

    def test_income_statement(self):
        t = statement("NVDA_10-Q_2026-07-26.html", "income")
        self.assertEqual((t[0]["scale"], t[0]["unit_source"]), (1_000_000, "table"))
        self.assertEqual(t[0]["columns"][0], "Three Months Ended | Jul 26, 2026")
        self.assertEqual(cell(t, "Revenue", "Three Months Ended | Jul 26, 2026")["text"], "96,221")
        self.assertEqual(cell(t, "Cost of revenue", "Three Months Ended | Jul 26, 2026")["value"], 24079)
        self.assertEqual(cell(t, "Operating income", "Six Months Ended | Jul 26, 2026")["value"], 117270)

    def test_cash_flow_capex_is_negative_and_year_to_date(self):
        t = statement("NVDA_10-Q_2026-07-26.html", "cash_flow")
        self.assertEqual(t[0]["columns"], ["Six Months Ended | Jul 26, 2026", "Six Months Ended | Jul 27, 2025"])
        c = cell(t, "Purchases related to property and equipment and intangible assets", "Six Months Ended | Jul 26, 2026")
        self.assertEqual((c["text"], c["value"]), ("(4,434)", -4434))


class Oracle10K(unittest.TestCase):
    """Annual columns only, no cost-of-revenue line, dashes for zero."""

    def test_income_statement(self):
        t = statement("ORCL_10-K_2026-05-31.html", "income")
        self.assertEqual(cell(t, "Total revenues", "Year Ended May 31, | 2026")["value"], 67357)
        self.assertEqual(cell(t, "Operating income", "Year Ended May 31, | 2025")["value"], 17678)
        self.assertFalse(any(r["label"].lower().startswith("cost of revenue") for x in t for r in x["rows"]))

    def test_cash_flow(self):
        t = statement("ORCL_10-K_2026-05-31.html", "cash_flow")
        self.assertEqual(cell(t, "Capital expenditures", "Year Ended May 31, | 2026")["value"], -55663)
        self.assertEqual(cell(t, "Increase in other deferred revenues", "Year Ended May 31, | 2024")["value"], 656)
        dash = [c for x in t for r in x["rows"] for c in r["cells"] if c["text"] == "—"]
        self.assertTrue(dash and all(c["value"] == 0 for c in dash))


class Iren10K(unittest.TestCase):
    """Header spans shifted against the numbers, a footnote-reference column, a cash-flow statement split at a page break."""

    def test_note_column_is_separate(self):
        t = statement("IREN_10-K_2026-06-30.html", "income")
        self.assertEqual(t[0]["columns"][0], "Years ended June 30, | Note")
        self.assertEqual(cell(t, "AI Cloud Services Revenue", "Years ended June 30, | 2026")["value"], 128795)
        self.assertEqual(cell(t, "Total revenue", "Years ended June 30, | 2025")["value"], 501023)

    def test_split_cash_flow_inherits_columns_and_unit(self):
        t = statement("IREN_10-K_2026-06-30.html", "cash_flow")
        self.assertEqual(len(t), 2)
        self.assertEqual(t[1]["columns"], t[0]["columns"])
        self.assertEqual((t[1]["scale"], t[1]["unit_source"]), (1000, "statement"))
        c = cell(t, "Payments for property, plant and equipment, net of computer hardware", "Years ended June 30, | 2026")
        self.assertEqual(c["value"], -2998006)


class Hygiene(unittest.TestCase):
    def test_no_xbrl_tag_names_reach_the_output(self):
        for f in FIX.glob("*.html"):
            out = json.dumps(parse_tables(f.read_bytes()))
            self.assertNotIn("us-gaap", out, f.name)
            self.assertNotIn("nonFraction", out, f.name)

    def test_parsing_is_deterministic(self):
        doc = (FIX / "NVDA_10-Q_2026-07-26.html").read_bytes()
        self.assertEqual(json.dumps(parse_tables(doc)), json.dumps(parse_tables(doc)))


class Locator(unittest.TestCase):
    def _t(self, id_, before, labels):
        return {"id": id_, "before": before, "columns": ["2025", "2024"], "unit_text": "(in millions)", "scale": 1_000_000,
                "rows": [{"label": l, "cells": [{"col": "2025", "text": "1"}, {"col": "2024", "text": "1"}]} for l in labels]}

    def test_a_reconciliation_table_loses_to_the_statement(self):  # Intel: adjusted free cash flow scores like the cash-flow statement
        rows = ["Net cash provided by operating activities", "Investing activities", "Additions to property, plant and equipment", "Financing activities"]
        tables = [self._t("t0001", "Non-GAAP adjusted free cash flow reconciliation", rows), self._t("t0002", "Consolidated statements of cash flows", rows)]
        self.assertEqual(locate(tables)["cash_flow"], ["t0002"])

    def test_a_highlights_table_loses_to_the_statement(self):  # IBM: the snapshot comes first and scores like the income statement
        rows = ["Revenue", "Net income", "Earnings per share", "Provision for income taxes"]
        tables = [self._t("t0001", "MANAGEMENT DISCUSSION SNAPSHOT", rows + ["Assets", "Liabilities", "Equity"]), self._t("t0002", "", rows)]
        self.assertEqual(locate(tables)["income"], ["t0002"])
        tables = [self._t("t0001", "Selected data", rows + ["Total assets"]), self._t("t0002", "Consolidated Income Statement", rows)]
        self.assertEqual(locate(tables)["income"], ["t0002"])


if __name__ == "__main__":
    unittest.main()


class NoteLocator(unittest.TestCase):
    def test_a_renamed_ppe_table_is_a_candidate(self):
        from ledger.extract.notes import locate
        rows = ["Technical infrastructure(1)", "Office space", "Corporate and other assets", "Property and equipment, in service", "Less: accumulated depreciation", "Property and equipment, net"]
        t = {"id": "t0130", "before": "Property and equipment, net, consisted of the following (in millions):", "rows": [{"label": l, "cells": [{"col": 0, "text": "1", "value": 1}]} for l in rows]}
        self.assertIn("t0130", locate([t], set())["ppe"])



class ThousandsAsZeros(unittest.TestCase):
    HTML = """<html><body><p>Coherent Corp. and Subsidiaries Consolidated Statements of Cash Flows</p>
    <table><tr><td></td><td>Year Ended June 30,</td><td></td></tr><tr><td></td><td>2023</td><td>2022</td></tr><tr><td>($000)</td><td></td><td></td></tr>
    <tr><td>Net earnings (loss)</td><td>(259,458)</td><td>234,759</td></tr>
    <tr><td>Additions to property, plant &amp; equipment</td><td>(436,060)</td><td>(314,332)</td></tr>
    <tr><td>Net cash provided by operating activities</td><td>783,962</td><td>597,603</td></tr></table></body></html>"""

    def test_dollar_000_is_thousands(self):
        t = parse_tables(self.HTML)[0]
        self.assertEqual(t["scale"], 1_000)
        self.assertIn("000", t["unit_text"])
        self.assertEqual(t["columns"], ["Year Ended June 30, | 2023", "Year Ended June 30, | 2022"])
        self.assertEqual([u["scale"] for u in document_units(self.HTML)], [1_000])


class PercentColumnsNeverWin(unittest.TestCase):
    def test_mdna_percent_of_revenue_table_loses_to_the_statement(self):
        html_ = """<html><body><p>The following table sets forth select items from our Consolidated Statements of Earnings (Loss) ($ in millions):</p>
        <table><tr><td></td><td>2023</td><td>% of Revenues</td></tr><tr><td>Revenues</td><td>5,160</td><td>100%</td></tr><tr><td>Cost of goods sold</td><td>3,542</td><td>69%</td></tr>
        <tr><td>Operating income</td><td>205</td><td>4%</td></tr><tr><td>Income tax expense</td><td>40</td><td>1%</td></tr><tr><td>Net earnings</td><td>(259)</td><td>(5)%</td></tr><tr><td>Diluted earnings per share</td><td>(1.83)</td><td></td></tr></table>
        <p>Consolidated Statements of Earnings (Loss)</p>
        <table><tr><td></td><td>2023</td><td>2022</td></tr><tr><td>($000, except per share data)</td><td></td><td></td></tr><tr><td>Revenues</td><td>5,160,100</td><td>3,316,616</td></tr>
        <tr><td>Cost of goods sold</td><td>3,541,817</td><td>2,051,120</td></tr><tr><td>Operating income</td><td>205,000</td><td>400,000</td></tr><tr><td>Income tax expense</td><td>40,000</td><td>50,000</td></tr><tr><td>Net earnings (loss)</td><td>(259,458)</td><td>234,759</td></tr><tr><td>Diluted earnings per share</td><td>(1.83)</td><td>1.62</td></tr></table></body></html>"""
        tables = parse_tables(html_)
        self.assertEqual(len(tables), 2)
        self.assertEqual(locate(tables)["income"], [tables[1]["id"]])
        self.assertEqual(tables[1]["scale"], 1_000)


class EquityMethodIsNotABalanceSheetLine(unittest.TestCase):
    def test_amazon_income_statement_is_not_a_snapshot(self):
        """Type 73: "Equity-method investment activity, net of tax" matched the balance-sheet marker, so the snapshot test
        rejected Amazon's income statement and the cash-flow table (with net income and tax lines) was located for both."""
        html_ = """<html><body><p>CONSOLIDATED STATEMENTS OF CASH FLOWS (in millions)</p>
        <table><tr><td></td><td>2024</td><td>2025</td></tr><tr><td>Net income</td><td>59,248</td><td>77,650</td></tr><tr><td>Deferred income taxes</td><td>(4,201)</td><td>(5,000)</td></tr>
        <tr><td>Net cash provided by (used in) operating activities</td><td>115,877</td><td>130,000</td></tr><tr><td>Purchases of property and equipment</td><td>(83,004)</td><td>(131,819)</td></tr>
        <tr><td>Net cash provided by (used in) investing activities</td><td>(94,342)</td><td>(120,000)</td></tr><tr><td>Net cash provided by (used in) financing activities</td><td>(11,812)</td><td>(10,000)</td></tr></table>
        <p>CONSOLIDATED STATEMENTS OF OPERATIONS (in millions, except per share data)</p>
        <table><tr><td></td><td>2024</td><td>2025</td></tr><tr><td>Total net sales</td><td>637,959</td><td>716,924</td></tr><tr><td>Cost of sales</td><td>326,288</td><td>350,000</td></tr>
        <tr><td>Operating income</td><td>68,593</td><td>85,000</td></tr><tr><td>Provision for income taxes</td><td>(9,265)</td><td>(10,000)</td></tr><tr><td>Equity-method investment activity, net of tax</td><td>(101)</td><td>(50)</td></tr>
        <tr><td>Net income</td><td>59,248</td><td>77,650</td></tr><tr><td>Diluted earnings per share</td><td>5.53</td><td>7.20</td></tr></table></body></html>"""
        tables = parse_tables(html_)
        loc = locate(tables)
        self.assertEqual((loc["income"], loc["cash_flow"]), ([tables[1]["id"]], [tables[0]["id"]]))

    def test_equity_in_earnings_is_not_a_balance_sheet_line_either(self):
        from ledger.ingest.statements import BALANCE
        for line in ("Equity in earnings of affiliates", "Equity in (losses) earnings of unconsolidated affiliates", "Equity earnings", "Equity income"):
            self.assertIsNone(BALANCE.search(line), line)
        for line in ("Total equity", "Total stockholders' equity", "Shareholders' equity", "Total assets", "Liabilities"):
            self.assertIsNotNone(BALANCE.search(line), line)


class QuarterlyNeverRaisesTheBar(unittest.TestCase):
    def test_quarterly_table_with_more_markers_loses_to_the_statement(self):
        html_ = """<html><body><p>Quarterly financial information (unaudited)</p>
        <table><tr><td></td><td>FirstQuarter</td><td>SecondQuarter</td><td>FullYear</td></tr><tr><td>Net sales</td><td>5,209</td><td>5,597</td><td>22,952</td></tr>
        <tr><td>Operating income</td><td>400</td><td>500</td><td>2,000</td></tr><tr><td>Income tax provision</td><td>50</td><td>60</td><td>240</td></tr>
        <tr><td>Net income</td><td>300</td><td>400</td><td>1,600</td></tr><tr><td>Diluted earnings per share</td><td>0.45</td><td>0.60</td><td>2.40</td></tr></table>
        <p>Consolidated Statements of Income (in millions)</p>
        <table><tr><td></td><td>2024</td><td>2023</td></tr><tr><td>Net sales</td><td>22,952</td><td>22,331</td></tr><tr><td>Cost of sales</td><td>15,000</td><td>14,800</td></tr>
        <tr><td>Operating income</td><td>2,000</td><td>1,900</td></tr><tr><td>Net income</td><td>1,600</td><td>1,500</td></tr></table></body></html>"""
        tables = parse_tables(html_)
        self.assertEqual(len(tables), 2)
        self.assertEqual(locate(tables)["income"], [tables[1]["id"]])


class ZerosAreCounted(unittest.TestCase):
    def test_scales(self):
        from ledger.ingest.tables import scale_of
        self.assertEqual(scale_of("($000)"), 1_000)
        self.assertEqual(scale_of("(000,000)"), 1_000_000)
        self.assertEqual(scale_of("($000,000, except per share)"), 1_000_000)
        self.assertEqual(scale_of("(in millions)"), 1_000_000)
        self.assertEqual([u["scale"] for u in document_units("<p>Consolidated Statements of Income (000,000)</p>")], [1_000_000])


class WholeDollars(unittest.TestCase):
    def test_expressed_in_us_dollars_is_scale_one(self):
        from ledger.ingest.tables import scale_of
        html_ = """<html><body><p>Notes (in thousands)</p><table><tr><td></td><td>2025</td></tr><tr><td>Lease cost</td><td>1,200</td></tr><tr><td>Total lease cost</td><td>1,200</td></tr><tr><td>Short-term lease cost</td><td>50</td></tr></table>
        <p>BIT DIGITAL, INC. CONSOLIDATED STATEMENTS OF OPERATIONS (Expressed in US dollars, except for the number of shares)</p>
        <table><tr><td></td><td>2025</td><td>2024</td></tr><tr><td>Revenue</td><td>105,012,000</td><td>108,117,000</td></tr><tr><td>Cost of revenue</td><td>60,000,000</td><td>55,000,000</td></tr>
        <tr><td>Operating income</td><td>5,000,000</td><td>4,000,000</td></tr><tr><td>Income tax expense</td><td>100,000</td><td>90,000</td></tr><tr><td>Net income</td><td>4,000,000</td><td>3,500,000</td></tr><tr><td>Diluted earnings per share</td><td>0.03</td><td>0.03</td></tr></table></body></html>"""
        tables = parse_tables(html_)
        self.assertEqual(tables[1]["scale"], 1)
        self.assertEqual(scale_of("(in thousands of dollars)"), 1_000)
        self.assertEqual(sorted(u["scale"] for u in document_units(html_)), [1, 1_000])


class NoUnitAnywhere(unittest.TestCase):
    def test_filing_without_any_unit_statement_is_whole_dollars(self):
        html_ = """<html><body><p>Consolidated Statements of Operations</p>
        <table><tr><td></td><td>2022</td><td>2021</td></tr><tr><td>Revenues</td><td>131,524,860</td><td>39,315,000</td></tr><tr><td>Cost of revenues</td><td>60,000,000</td><td>20,000,000</td></tr>
        <tr><td>Operating loss</td><td>(5,000,000)</td><td>(4,000,000)</td></tr><tr><td>Income tax expense</td><td>100,000</td><td>90,000</td></tr><tr><td>Net loss</td><td>(57,000,000)</td><td>(21,000,000)</td></tr><tr><td>Diluted loss per share</td><td>(1.35)</td><td>(0.80)</td></tr></table></body></html>"""
        tables = parse_tables(html_)
        parts = assemble(tables, locate(tables)["income"], document_units(html_))
        self.assertEqual((parts[0]["scale"], parts[0]["unit_source"]), (1, "document"))


class QuarterEndDatesAreQuarterly(unittest.TestCase):
    def test_dates(self):
        from ledger.ingest.statements import _quarterly
        self.assertTrue(_quarterly([{"columns": ["2022 | March 31,", "2022 | June 30,", "2022 | September 30,", "2022 | December 31,"], "rows": []}]))
        self.assertFalse(_quarterly([{"columns": ["Year Ended December 31, | 2023", "Year Ended December 31, | 2022"], "rows": []}]))
