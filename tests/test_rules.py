"""Every rule has a fixture it passes and a fixture it fails, and the registry loads cleanly."""
import copy
from datetime import date
import unittest
from pathlib import Path

from ledger.ingest.statements import assemble, locate
from ledger.ingest.tables import document_units, parse_tables
from ledger.checks.rules import CHECKS, Context, load, run

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


# T92: the note figures. One filing (ACC) prints PP&E by category, segment revenue and segment capex that tie to its
# tagged totals; an untagged category is read the same in two filings.
OLD = "0000950170-25-087926"


def nx(field, dim, end, value, accession=ACC, filed="2026-06-20", scale=1000):
    return {"extraction_id": f"{accession}|{field}|{dim}|{end}", "accession": accession, "ticker": "ORCL", "field": field, "dimension": dim,
            "period_end": end, "value": value, "scale": scale, "filed": filed}


def fx(field, dim, period, end, value, ids, accession=ACC, label="no_reference"):
    return {"ticker": "ORCL", "field": field, "dimension": dim, "period": period, "period_end": end, "value": value, "label": label, "accession": accession, "extraction_ids": ",".join(ids)}


NOTES = [nx("ppe_category", "Land", "2026-05-31", 10_000_000), nx("ppe_category", "Buildings", "2026-05-31", 20_000_000),
         nx("ppe_category", "Land", "2025-05-31", 9_000_000, OLD, "2025-06-20"), nx("ppe_category", "Land", "2025-05-31", 9_000_000),
         nx("segment_revenue", "Cloud", "2026-05-31", 40_000_000_000, scale=1_000_000), nx("segment_revenue", "Hardware", "2026-05-31", 20_000_000_000, scale=1_000_000),
         nx("segment_capex", "Cloud", "2026-05-31", 20_000_000_000, scale=1_000_000),
         nx("segment_revenue", "Services", "2026-05-31", 7_357_000_000, scale=1_000_000), nx("segment_capex", "Hardware", "2026-05-31", 5_000_000_000, scale=1_000_000)]
GOOD.note_extractions = NOTES
GOOD.facts = [fx("ppe_category", "Land", "FY2026", "2026-05-31", 10_000_000, [NOTES[0]["extraction_id"]]),
              fx("ppe_category", "Buildings", "FY2026", "2026-05-31", 20_000_000, [NOTES[1]["extraction_id"]]),
              fx("ppe_category", "Land", "FY2025", "2025-05-31", 9_000_000, [NOTES[2]["extraction_id"], NOTES[3]["extraction_id"]]),
              fx("segment_revenue", "Cloud", "FY2026", "2026-05-31", 40_000_000_000, [NOTES[4]["extraction_id"]], label="agree"),
              fx("segment_revenue", "Hardware", "FY2026", "2026-05-31", 20_000_000_000, [NOTES[5]["extraction_id"]]),
              fx("segment_capex", "Cloud", "FY2026", "2026-05-31", 20_000_000_000, [NOTES[6]["extraction_id"]]),
              fx("segment_revenue", "Services", "FY2026", "2026-05-31", 7_357_000_000, [NOTES[7]["extraction_id"]]),
              fx("segment_capex", "Hardware", "FY2026", "2026-05-31", 5_000_000_000, [NOTES[8]["extraction_id"]])]
GOOD.totals = {(ACC, "PropertyPlantAndEquipmentGross", "2026-05-31"): 30_000_000, (ACC, "Revenues", "2026-05-31"): 67_357_000_000,
               (ACC, "RevenueFromContractWithCustomerExcludingAssessedTax", "2026-05-31"): 60_000_000_000,  # a component tag: the largest is the total
               (ACC, "PaymentsToAcquirePropertyPlantAndEquipment", "2026-05-31"): 25_000_000_000}


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


def _resegment(c):
    """A re-segmentation: the newer 10-K (ACC) prints Cloud FY2025 differently from the older one (OLD), and FY2024 is
    only in OLD, so the series ships FY2024 on the old basis and FY2025 on the new one."""
    o24, o25 = nx("segment_revenue", "Cloud", "2024-05-31", 25_000_000_000, OLD, "2025-06-20", 1_000_000), nx("segment_revenue", "Cloud", "2025-05-31", 30_000_000_000, OLD, "2025-06-20", 1_000_000)
    n25 = nx("segment_revenue", "Cloud", "2025-05-31", 35_000_000_000, scale=1_000_000)
    c.note_extractions.extend([o24, o25, n25])
    c.facts.extend([fx("segment_revenue", "Cloud", "FY2024", "2024-05-31", 25_000_000_000, [o24["extraction_id"]], OLD, label="agree"),
                    fx("segment_revenue", "Cloud", "FY2025", "2025-05-31", 35_000_000_000, [o25["extraction_id"], n25["extraction_id"]], label="agree")])


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
    "ppe_categories_tie": lambda c: c.note_extractions[1].update(value=21_000_000),  # a misread category
    "segment_revenue_tie": lambda c: c.note_extractions.pop(7),  # a segment missing from the read: the sum falls short of the total
    "segment_capex_tie": lambda c: c.totals.update({(ACC, "PaymentsToAcquirePropertyPlantAndEquipment", "2026-05-31"): 20_000_000_000}),  # accrual segment capex above cash capex
    "fact_readings_differ": lambda c: c.note_extractions[2].update(value=9_552_000),
    "segment_basis_mixed": lambda c: _resegment(c),
    "statement_tables_distinct": lambda c: c.documents.append({"accession": "0001018724-26-000004", "ticker": "AMZN", "form": "10-K", "period": "2025-12-31", "income_tables": "t0034", "cash_flow_tables": "t0034"}),
}


class Registry(unittest.TestCase):
    def test_every_rule_loads_with_rationale_and_owner(self):
        self.assertEqual(len(RULES), 21)
        for r in RULES.values():
            self.assertTrue(r["rationale"].strip() and r["owner"].strip(), r["id"])

    def test_every_rule_has_a_failing_fixture(self):
        self.assertEqual(set(FAIL), set(RULES))


class EachRule(unittest.TestCase):
    pass


class NoteTies(unittest.TestCase):
    """T92: the parts one filing prints against the total it tags; the readings of an untagged figure across filings."""

    def test_segment_capex_holds(self):
        from ledger.checks import ties
        g = ties.groups("segment_capex_tie", RULES["segment_capex_tie"]["params"], GOOD.facts, GOOD.note_extractions, GOOD.totals)
        self.assertEqual([(x["sum"], x["total"], x["holds"]) for x in g], [(25_000_000_000, 25_000_000_000, True)])

    def test_degenerate_groups_are_not_judged(self):
        """T92 review: one part equal to the total, a part labelled as a total, or all zeros prove nothing: no tie, no finding."""
        from ledger.checks import ties
        p = RULES["ppe_categories_tie"]["params"]
        one = bad(lambda c: (c.note_extractions.pop(1), c.totals.update({(ACC, "PropertyPlantAndEquipmentGross", "2026-05-31"): 10_000_000})))
        self.assertEqual(ties.groups("ppe_categories_tie", p, one.facts, one.note_extractions, one.totals), [])
        for label in ("Total", "Subtotal", "gross", "Net", "Total:"):
            tot = bad(lambda c, label=label: c.note_extractions[1].update(dimension=label))
            self.assertEqual(ties.groups("ppe_categories_tie", p, tot.facts, tot.note_extractions, tot.totals), [], label)
        self.assertIsNone(ties.degenerate([{"dimension": "Total network equipment", "value": 1}, {"dimension": "Land", "value": 1}], 2))  # a word, not the whole label
        zeros = bad(lambda c: (c.note_extractions[0].update(value=0), c.note_extractions[1].update(value=0), c.totals.update({(ACC, "PropertyPlantAndEquipmentGross", "2026-05-31"): 0})))
        self.assertEqual(ties.groups("ppe_categories_tie", p, zeros.facts, zeros.note_extractions, zeros.totals), [])
        self.assertEqual(findings("ppe_categories_tie", zeros), [])

    def test_offsetting_misreads_tie_the_known_limitation(self):
        """Pins taxonomy/limitations.yaml tie_offsetting_errors: two misreads that offset inside a group still tie. A tie
        bounds the sum; the second reading and the gold sample are what catch this."""
        swapped = bad(lambda c: (c.note_extractions[0].update(value=15_000_000), c.note_extractions[1].update(value=15_000_000)))
        self.assertEqual(findings("ppe_categories_tie", swapped), [])

    def test_the_largest_revenue_tag_is_named_on_the_finding(self):
        f = findings("segment_revenue_tie", bad(FAIL["segment_revenue_tie"]))
        self.assertIn("Revenues, the largest of 2 revenue tags it carries", f[0].message)

    def test_instance_totals_reads_the_distilled_key_format(self):
        """ties.instance_totals on a real .facts.json shape: "concept\tmember\tend" keys, the company total has no member."""
        import json, tempfile
        from unittest import mock
        from ledger.checks import ties
        from ledger.ingest import edgar
        d = Path(tempfile.mkdtemp())
        (d / "0001144879" / "filings").mkdir(parents=True)
        (d / "0001144879" / "filings" / "acc.facts.json").write_text(json.dumps({
            "PropertyPlantAndEquipmentGross\t\t2025-05-31": 1278843000, "PropertyPlantAndEquipmentGross\tus-gaap:LandMember\t2025-05-31": 5000,
            "Revenues\t\t2025-05-31": 1}))
        with mock.patch.object(edgar, "RAW", d):
            got = ties.instance_totals(1144879, "acc", {"PropertyPlantAndEquipmentGross"})
            self.assertEqual(ties.instance_totals(1144879, "missing", {"PropertyPlantAndEquipmentGross"}), {})
        self.assertEqual(got, {("acc", "PropertyPlantAndEquipmentGross", "2025-05-31"): 1278843000})

    def test_a_scenario_dimension_is_never_a_company_total(self):
        """T92 review: a context whose dimension sits under <scenario> is not a total, in the instance reader the ties
        read (dimensions.instance_facts) and the reference's (xbrl_instance.parse_instance)."""
        import tempfile
        from unittest import mock
        from ledger.ingest.reference import dimensions, xbrl_instance
        xml = b"""<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:us-gaap="http://fasb.org/us-gaap/2024">
          <xbrli:context id="tot"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2025-05-31</xbrli:instant></xbrli:period></xbrli:context>
          <xbrli:context id="scn"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2025-05-31</xbrli:instant></xbrli:period>
            <xbrli:scenario><xbrldi:explicitMember dimension="srt:RestatementAxis">srt:ScenarioPreviouslyReportedMember</xbrldi:explicitMember></xbrli:scenario></xbrli:context>
          <xbrli:context id="dur"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:startDate>2024-06-01</xbrli:startDate><xbrli:endDate>2025-05-31</xbrli:endDate></xbrli:period>
            <xbrli:scenario><xbrldi:explicitMember dimension="srt:RestatementAxis">srt:ScenarioPreviouslyReportedMember</xbrldi:explicitMember></xbrli:scenario></xbrli:context>
          <xbrli:unit id="usd"><xbrli:measure>iso4217:USD</xbrli:measure></xbrli:unit>
          <us-gaap:PropertyPlantAndEquipmentGross contextRef="tot" unitRef="usd">100</us-gaap:PropertyPlantAndEquipmentGross>
          <us-gaap:PropertyPlantAndEquipmentGross contextRef="scn" unitRef="usd">90</us-gaap:PropertyPlantAndEquipmentGross>
          <us-gaap:Revenues contextRef="dur" unitRef="usd">7</us-gaap:Revenues>
        </xbrli:xbrl>"""
        d = Path(tempfile.mkdtemp())
        with mock.patch.object(dimensions, "RAW", d), mock.patch.object(dimensions, "_instance_name", lambda c, a: "u"), mock.patch.object(dimensions, "_cached", lambda *a: (xml, {})):
            got = dimensions.instance_facts(1, "acc")
        self.assertEqual(got[("PropertyPlantAndEquipmentGross", "", "2025-05-31")], 100)  # the plain total, not the previously reported one
        self.assertEqual(got.get(("PropertyPlantAndEquipmentGross", "srt:ScenarioPreviouslyReportedMember", "2025-05-31")), 90)  # a member fact, never the total
        self.assertNotIn(("Revenues", "", "2025-05-31"), got)
        self.assertEqual(xbrl_instance.parse_instance(xml, "acc", "10-K", "2025-07-30").get("Revenues", []), [])

    def test_an_amendment_is_not_a_second_reading(self):
        """T92 review: a 10-K/A re-printing the year folds into its original 10-K; only a later fiscal year's 10-K (its
        comparative column) is a second reading."""
        from ledger.checks import ties
        orig = {"accession": "a1", "filed": "2025-07-30", "form": "10-K", "period": "2025-05-31", "value": 9_000_000, "scale": 1000}
        amend = {**orig, "accession": "a1a", "filed": "2025-09-01", "form": "10-K/A"}
        later = {**orig, "accession": "a2", "filed": "2026-07-30", "period": "2026-05-31"}
        self.assertFalse(ties.corroborated([orig, amend]))
        self.assertTrue(ties.corroborated([orig, amend, later]))
        self.assertEqual(ties.second_accession([orig, amend, later], "a2"), "a1")
        self.assertIsNone(ties.second_accession([orig, amend], "a1a"))

    def test_within_rounding_ties_and_beyond_does_not(self):
        # two parts in thousands: each can be half a thousand off, and the total too: 1,500 dollars of slack
        close = bad(lambda c: c.note_extractions[1].update(value=20_001_000))
        self.assertEqual(findings("ppe_categories_tie", close), [])
        far = bad(lambda c: c.note_extractions[1].update(value=20_002_000))
        f = findings("ppe_categories_tie", far)
        self.assertEqual([(x.ticker, x.field, x.period, x.subject) for x in f], [("ORCL", "ppe_category", "FY2026", ACC)])
        self.assertIn("$30.0M", f[0].message)

    def test_a_segment_set_that_leaves_out_a_reconciling_line_fails_honestly(self):
        """GOOGL's segments leave out hedging gains: the sum misses total revenue, and the finding names the gap, nothing is
        added to force it."""
        hedging = bad(lambda c: c.totals.update({(ACC, "Revenues", "2026-05-31"): 67_593_000_000}))
        f = findings("segment_revenue_tie", hedging)
        self.assertEqual(len(f), 1)
        self.assertIn("gap −$236M", f[0].message)

    def test_no_tagged_total_no_tie_and_only_shipped_groups(self):
        none = bad(lambda c: c.totals.clear())
        for rid in ("ppe_categories_tie", "segment_revenue_tie", "segment_capex_tie"):
            self.assertEqual(findings(rid, none), [], rid)
        # a comparative column a later 10-K replaced ships nothing: its group is not judged, however it sums
        old = bad(lambda c: (c.note_extractions.append(nx("ppe_category", "Land", "2026-05-31", 1, OLD, "2025-06-20")),
                             c.totals.update({(OLD, "PropertyPlantAndEquipmentGross", "2026-05-31"): 999})))
        self.assertEqual(findings("ppe_categories_tie", old), [])

    def test_groups_carry_the_evidence(self):
        from ledger.checks import ties
        g = ties.groups("ppe_categories_tie", RULES["ppe_categories_tie"]["params"], GOOD.facts, GOOD.note_extractions, GOOD.totals)
        self.assertEqual([(x["period"], x["sum"], x["total"], x["concept"], x["holds"], x["dimensions"]) for x in g],
                         [("FY2026", 30_000_000, 30_000_000, "PropertyPlantAndEquipmentGross", True, ["Buildings", "Land"])])
        rev = ties.groups("segment_revenue_tie", RULES["segment_revenue_tie"]["params"], GOOD.facts, GOOD.note_extractions, GOOD.totals)
        self.assertEqual((rev[0]["concept"], rev[0]["total"]), ("Revenues", 67_357_000_000))  # the largest revenue tag, not the component

    def test_readings(self):
        from ledger.checks import ties
        by_id = {e["extraction_id"]: e for e in GOOD.note_extractions}
        two = ties.readings_of(GOOD.facts[2], by_id)
        self.assertEqual([r["accession"] for r in two], [OLD, ACC])  # oldest filing first
        self.assertTrue(ties.corroborated(two))
        self.assertFalse(ties.corroborated(two[:1]))  # one filing is no second reading
        self.assertFalse(ties.corroborated([two[0], dict(two[0])]))  # nor is one filing counted twice
        differ = [two[0], {**two[1], "value": 9_552_000}]
        self.assertTrue(ties.differ(differ))
        self.assertFalse(ties.corroborated(differ))
        self.assertIn("$9M in 0000950170-25-087926 (filed 2025-06-20) vs $9.6M", ties.differ_message(differ))
        tagged = bad(lambda c: (c.facts[2].update(label="agree"), c.note_extractions[2].update(value=9_552_000)))
        self.assertEqual(findings("fact_readings_differ", tagged), [])  # a tagged fact has its tag and the restatement guard


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

    def test_a_null_row_counts_as_present_only_with_a_stated_reason(self):
        """T65: a not_reported row (no such line, no XBRL value) is a stated reason; a not_extracted row is a missing value."""
        rule = RULES["coverage"] | {"params": {"fields": ["revenue"], "filing_days": 90}}
        row = lambda label: {**val("revenue", "FY2024", None, label=label), "period_end": "2024-12-31"}
        ctx = lambda label: Context(values=[row(label), {**val("revenue", "FY2025", 1), "period_end": "2025-12-31"}], extractions=[], years=["FY2024", "FY2025"], today=date(2026, 10, 28))
        self.assertEqual(run(ctx("not_reported"), [rule]), [])
        found = run(ctx("not_extracted"), [rule])
        self.assertEqual([(f["field"], f["period"]) for f in found], [("revenue", "FY2024")])


class StatementTablesDistinct(unittest.TestCase):
    """T65 / type 73: the locator named the cash-flow table as the income statement, or an income table with no revenue row."""
    RULE = RULES["statement_tables_distinct"]

    def doc(self, **kw):
        return {"accession": "0001018724-26-000004", "ticker": "AMZN", "form": "10-K", "period": "2025-12-31", "income_tables": "t0035", "cash_flow_tables": "t0034", **kw}

    def test_same_table_for_both_statements_blocks(self):
        found = run(Context(values=[], extractions=[], documents=[self.doc(income_tables="t0034")]), [self.RULE])
        self.assertEqual([(f["severity"], f["ticker"], f["subject"]) for f in found], [("block", "AMZN", "0001018724-26-000004")])
        self.assertIn("both t0034", found[0]["message"])

    def test_an_income_table_without_a_revenue_row_blocks(self):
        income = [{"id": "t0035", "rows": [{"label": "Net income", "cells": []}, {"label": "Diluted earnings per share", "cells": []}]}]
        ctx = Context(values=[], extractions=[], documents=[self.doc()], parsed={"0001018724-26-000004": {"statements": {"income": income}}})
        self.assertEqual(len(run(ctx, [self.RULE])), 1)
        income[0]["rows"].insert(0, {"label": "Total net sales", "cells": []})
        self.assertEqual(run(ctx, [self.RULE]), [])

    def test_a_partial_overlap_blocks(self):
        found = run(Context(values=[], extractions=[], documents=[self.doc(income_tables="t0034,t0035", cash_flow_tables="t0034")]), [self.RULE])
        self.assertEqual(len(found), 1)
        self.assertIn("both t0034", found[0]["message"])

    def _income(self, *labels):
        income = [{"id": "t0035", "rows": [{"label": l, "cells": []} for l in labels]}]
        return Context(values=[], extractions=[], documents=[self.doc()], parsed={"0001018724-26-000004": {"statements": {"income": income}}})

    def test_expense_lines_that_mention_sales_are_not_revenue(self):
        ctx = self._income("Cost of sales", "Sales and marketing", "Selling, general and administrative", "Operating income")
        self.assertEqual(len(run(ctx, [self.RULE])), 1)

    def test_a_bank_layout_passes(self):
        self.assertEqual(run(self._income("Total interest income", "Net interest income", "Noninterest income", "Noninterest expense"), [self.RULE]), [])

    def test_a_named_revenue_line_passes(self):
        self.assertEqual(run(self._income("Hosting revenue", "Cost of revenues", "Operating loss"), [self.RULE]), [])

    def test_distinct_tables_with_a_revenue_row_pass_and_a_part_iii_amendment_is_not_its_case(self):
        ctx = Context(values=[], extractions=[], documents=[self.doc(), self.doc(accession="0000002488-26-000021", ticker="AMD", form="10-K/A", income_tables="t0005,t0006", cash_flow_tables=None)],
                      parsed={"0000002488-26-000021": {"statements": {"income": [{"id": "t0005", "rows": [{"label": "Salary", "cells": []}]}]}}})
        self.assertEqual(run(ctx, [self.RULE]), [])  # AMD's amendment: a compensation table, explained by proof.amendment_without_statements


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
        from ledger.checks import rules as R
        ctx = type("C", (), {})()
        ok = {"ticker": "CDNS", "field": "capex", "column_label": "2020", "period_end": "2021-01-02", "period_start": "2019-12-29", "extraction_id": "e1"}
        bad = {**ok, "column_label": "2019", "extraction_id": "e2"}
        plain = {**ok, "column_label": "2020", "period_end": "2021-06-30", "period_start": "2020-07-01", "extraction_id": "e3"}
        ctx.extractions = [ok, bad, plain]
        out = R._column_period(ctx, {})
        self.assertEqual(sorted(f.subject for f in out), ["e2", "e3"])
