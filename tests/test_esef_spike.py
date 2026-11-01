"""T44: the ESEF inline XBRL reader on a synthetic snippet shaped like ASML's 2025 report (Workiva: scale="6",
ixt:num-dot-decimal, ixt:fixed-zero, sign="-", pageView divs)."""
import unittest
from decimal import Decimal

from ledger.spikes import esef

SNIPPET = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
      xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
      xmlns:iso4217="http://www.xbrl.org/2003/iso4217" xmlns:ifrs-full="https://xbrl.ifrs.org/taxonomy/2024-03-27/ifrs-full"
      xmlns:asml="http://www.asml.com/20251231" xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2022-02-16">
<body>
<div style="display:none"><ix:header><ix:resources>
  <xbrli:unit id="u-1"><xbrli:measure>iso4217:EUR</xbrli:measure></xbrli:unit>
  <xbrli:unit id="u-2"><xbrli:divide><xbrli:unitNumerator><xbrli:measure>iso4217:EUR</xbrli:measure></xbrli:unitNumerator>
    <xbrli:unitDenominator><xbrli:measure>xbrli:shares</xbrli:measure></xbrli:unitDenominator></xbrli:divide></xbrli:unit>
  <xbrli:context id="c-3"><xbrli:entity><xbrli:identifier scheme="http://standards.iso.org/iso/17442">724500Y6DUVHQD6OXN27</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:startDate>2025-01-01</xbrli:startDate><xbrli:endDate>2025-12-31</xbrli:endDate></xbrli:period></xbrli:context>
  <xbrli:context id="c-5"><xbrli:entity><xbrli:identifier scheme="http://standards.iso.org/iso/17442">724500Y6DUVHQD6OXN27</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>
  <xbrli:context id="c-9"><xbrli:entity><xbrli:identifier scheme="http://standards.iso.org/iso/17442">724500Y6DUVHQD6OXN27</xbrli:identifier>
    <xbrli:segment><xbrldi:explicitMember dimension="ifrs-full:ClassesOfPropertyPlantAndEquipmentAxis">ifrs-full:LandAndBuildingsMember</xbrldi:explicitMember></xbrli:segment></xbrli:entity>
    <xbrli:period><xbrli:instant>2025-12-31</xbrli:instant></xbrli:period></xbrli:context>
</ix:resources></ix:header></div>
<div class="pageView"><p>Consolidated statement of cash flows</p>
  <span>( <ix:nonFraction unitRef="u-1" contextRef="c-3" decimals="-5" name="ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"
     format="ixt:num-dot-decimal" scale="6" id="f-545">1,573.6</ix:nonFraction> )</span>
  <span><ix:nonFraction unitRef="u-1" contextRef="c-3" decimals="-5" sign="-" name="ifrs-full:OtherAdjustments" scale="6" id="f-68">12.1</ix:nonFraction></span>
  <span><ix:nonFraction unitRef="u-1" contextRef="c-3" decimals="-5" name="ifrs-full:GainsLossesOnDisposal" format="ixt:fixed-zero" scale="6" id="f-73">—</ix:nonFraction></span>
</div>
<div class="pageView"><p>Statement of financial position</p>
  <span><ix:nonFraction unitRef="u-1" contextRef="c-5" decimals="-5" name="ifrs-full:PropertyPlantAndEquipment" format="ixt:num-dot-decimal" scale="6" id="f-200">7,893.8</ix:nonFraction></span>
  <span><ix:nonFraction unitRef="u-1" contextRef="c-9" decimals="-5" name="ifrs-full:PropertyPlantAndEquipment" format="ixt:num-dot-decimal" scale="6" id="f-201">6,421.1</ix:nonFraction></span>
  <span><ix:nonFraction unitRef="u-2" contextRef="c-3" decimals="2" name="ifrs-full:BasicEarningsLossPerShare" format="ixt:num-dot-decimal" scale="0" id="f-300">26.14</ix:nonFraction></span>
  <span><ix:nonFraction unitRef="u-1" contextRef="c-3" decimals="-5" name="asml:Odd" format="ixt:num-comma-decimal" scale="6" id="f-400">1.234,5</ix:nonFraction></span>
  <span><ix:nonFraction unitRef="u-1" contextRef="c-3" decimals="-5" name="asml:BareDash" scale="6" id="f-401">—</ix:nonFraction></span>
  <span><ix:nonFraction unitRef="u-1" contextRef="c-3" decimals="-5" name="asml:Empty" format="ixt:num-dot-decimal" scale="6" id="f-402"></ix:nonFraction></span>
</div>
<div class="pageView"><p>Five-year summary: the same facts again</p>
  <span><ix:nonFraction unitRef="u-1" contextRef="c-3" decimals="-5" name="ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"
     format="ixt:num-dot-decimal" scale="6" id="f-900">1,573.6</ix:nonFraction></span>
  <span><ix:nonFraction unitRef="u-1" contextRef="c-5" decimals="-5" name="ifrs-full:PropertyPlantAndEquipment" format="ixt:num-dot-decimal" scale="6" id="f-901">7,893.9</ix:nonFraction></span>
</div>
</body></html>"""


class EsefReader(unittest.TestCase):
    def setUp(self):
        self.root = esef.load(SNIPPET)
        self.facts = esef.facts(self.root)

    def test_contexts_and_units(self):
        ctx = esef.contexts(self.root)
        self.assertEqual(ctx["c-3"], ("2025-01-01/2025-12-31", ()))
        self.assertEqual(ctx["c-5"], ("2025-12-31", ()))
        self.assertEqual(ctx["c-9"], ("2025-12-31", ("ifrs-full:ClassesOfPropertyPlantAndEquipmentAxis=ifrs-full:LandAndBuildingsMember",)))
        self.assertEqual(esef.units(self.root), {"u-1": "iso4217:EUR", "u-2": "iso4217:EUR/xbrli:shares"})

    def test_scale_and_thousands_separator(self):
        f = esef.select(self.facts, "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", "2025-01-01/2025-12-31")
        self.assertEqual(f["value"], Decimal("1573600000"))
        self.assertEqual((f["scale"], f["decimals"], f["text"], f["id"]), (6, "-5", "1,573.6", "f-545"))

    def test_sign_attribute_not_parentheses(self):
        # the cash-flow outflow is shown in parentheses but tagged positive; the sign lives only in sign="-"
        self.assertEqual(esef.select(self.facts, "ifrs-full:OtherAdjustments", "2025-01-01/2025-12-31")["value"], Decimal("-12100000"))

    def test_fixed_zero_dash(self):
        self.assertEqual(esef.select(self.facts, "ifrs-full:GainsLossesOnDisposal", "2025-01-01/2025-12-31")["value"], Decimal(0))

    def test_a_dash_or_empty_text_without_fixed_zero_is_not_zero(self):
        self.assertIsNone(esef.select(self.facts, "asml:BareDash", "2025-01-01/2025-12-31")["value"])
        self.assertIsNone(esef.select(self.facts, "asml:Empty", "2025-01-01/2025-12-31")["value"])
        self.assertIsNone(esef.parse_number("", "ixt:num-dot-decimal", "6", None))
        self.assertEqual(esef.parse_number("", "ixt:fixed-zero", "6", None), Decimal(0))

    def test_a_fact_tagged_twice_is_recorded_and_a_disagreement_named(self):
        same = esef.select(self.facts, "ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", "2025-01-01/2025-12-31")
        self.assertEqual((same["id"], same["duplicates"]), ("f-545", [("f-900", Decimal("1573600000"))]))
        differs = esef.select(self.facts, "ifrs-full:PropertyPlantAndEquipment", "2025-12-31")
        self.assertEqual(differs["duplicates"], [("f-901", Decimal("7893900000"))])
        self.assertEqual(list(esef.conflicts(self.facts)), [("ifrs-full:PropertyPlantAndEquipment", "2025-12-31", "iso4217:EUR", ())])
        self.assertEqual(esef.conflicts(self.facts)[("ifrs-full:PropertyPlantAndEquipment", "2025-12-31", "iso4217:EUR", ())],
                         [("f-200", Decimal("7893800000")), ("f-901", Decimal("7893900000"))])

    def test_dimension_kept_apart_from_consolidated(self):
        self.assertEqual(esef.select(self.facts, "ifrs-full:PropertyPlantAndEquipment", "2025-12-31")["value"], Decimal("7893800000"))
        member = ("ifrs-full:ClassesOfPropertyPlantAndEquipmentAxis=ifrs-full:LandAndBuildingsMember",)
        self.assertEqual(self.facts[("ifrs-full:PropertyPlantAndEquipment", "2025-12-31", "iso4217:EUR", member)]["value"], Decimal("6421100000"))

    def test_per_share_unit_and_unknown_format(self):
        self.assertEqual(esef.select(self.facts, "ifrs-full:BasicEarningsLossPerShare", "2025-01-01/2025-12-31", "iso4217:EUR/xbrli:shares")["value"], Decimal("26.14"))
        odd = esef.select(self.facts, "asml:Odd", "2025-01-01/2025-12-31")
        self.assertIsNone(odd["value"])  # a format the reader does not know is not guessed
        self.assertEqual(odd["text"], "1.234,5")

    def test_fact_pages(self):
        pages = esef.fact_pages(self.root)
        self.assertEqual(pages["f-545"], 1)
        self.assertEqual(pages["f-200"], 2)
        self.assertEqual(pages["f-400"], 2)
        self.assertEqual(pages["f-900"], 3)


if __name__ == "__main__":
    unittest.main()
