import unittest

import duckdb

from ledger import taxonomy


def _con():
    con = duckdb.connect()
    con.execute('create table "values" (ticker text, field text, period text, value double, label text, extraction_ids text)')
    con.execute("insert into \"values\" values ('AMZN','capex','FY2025',131819e6,'agree','x|capex|2025-01-01|2025-12-31'), ('AMZN','revenue','FY2025',700e9,'agree','y')")
    con.execute("create table facts (ticker text, field text, dimension text, period text, value double, label text, accession text, extraction_ids text)")
    con.execute("""insert into facts values
        ('AMZN','ppe_category','Servers and networking equipment','FY2024',113156e6,'agree','a','a|ppe|2024'),
        ('AMZN','ppe_category','Servers and networking equipment','FY2025',172492e6,'agree','b','b|ppe|2025'),
        ('AMZN','ppe_category','Warp drives','FY2025',1e6,'no_reference','b','b|ppe|warp'),
        ('AMZN','segment_revenue','AWS','FY2025',120e9,'agree','b','b|seg'),
        ('AMZN','purchase_commitments','','FY2025',84772e6,'no_reference','b','b|po')""")
    con.execute("create table texts (text_id text, date text)")
    con.execute("insert into texts values ('t1','2026-02-05'), ('t2','2024-04-30')")
    con.execute("create table ai_statements (ticker text, field text, period text, kind text, scope text, class text, amount_low double, amount_high double, share double, quote text, source text, text_id text)")
    con.execute("""insert into ai_statements values
        ('AMZN','capex','FY2026','outlook','total','explicit_amount',200e9,200e9,null,'We expect 2026 capital expenditures of about $200 billion.','earnings_release','t1'),
        ('AMZN','capex','FY2024','actual','ai','explicit_amount',1e9,1e9,null,'AI infrastructure capex of $1.0B in Q1.','earnings_release','t2')""")
    con.execute("create table projects (ticker text, period text, name text, kind text, status text, location text, amount_low double, amount_high double, capacity_mw double, quote text, text_id text, latest boolean)")
    con.execute("insert into projects values ('AMZN','FY2025','Project Rainier','data_center','under_construction','Indiana',null,null,2200,'Project Rainier, 2.2 GW in Indiana.','t1',true)")
    return con


class Rows(unittest.TestCase):
    def test_every_measure_appears_with_its_standard(self):
        rows = taxonomy.rows(_con(), ["AMZN"])
        by = {(r["measure"], r["category"], r["reported_name"], r["fiscal_year"]): r for r in rows}
        capex = by[("spent", "capex", "capital expenditures (cash-flow line)", "FY2025")]
        self.assertEqual((capex["standard_concept"], capex["value"], capex["check"]), ("PaymentsToAcquirePropertyPlantAndEquipment", 131819e6, "agree"))
        seg = by[("spent", "segment_revenue", "AWS", "FY2025")]
        self.assertIn("StatementBusinessSegmentsAxis", seg["standard_concept"])
        po = by[("committed", "purchase_obligations", "purchase commitments", "FY2025")]
        self.assertEqual(po["check"], "no_reference")
        self.assertNotIn("revenue", [r["category"] for r in rows if r["measure"] == "spent"])  # revenue is not spend

    def test_derived_ppe_carries_the_mapping_and_the_change(self):
        rows = taxonomy.rows(_con(), ["AMZN"])
        d = [r for r in rows if r["measure"] == "derived" and r["reported_name"] == "Servers and networking equipment"]
        self.assertEqual([r["standard_type"] for r in d], ["TechnologyEquipmentMember", "TechnologyEquipmentMember"])
        self.assertEqual([r["value_high"] for r in d], [None, 172492e6 - 113156e6])  # the change in value_high, arithmetic on reported balances
        warp = next(r for r in rows if r["reported_name"] == "Warp drives")
        self.assertEqual((warp["standard_type"], warp["check"]), (None, "unmapped"))
        self.assertEqual(taxonomy.unmapped(_con(), ["AMZN"]), [{"ticker": "AMZN", "reported_name": "Warp drives"}])

    def test_planned_and_company_stated_are_verbatim_with_tags(self):
        rows = taxonomy.rows(_con(), ["AMZN"])
        g = next(r for r in rows if r["category"] == "guidance")
        self.assertEqual((g["measure"], g["value"], g["check"]), ("planned", 200e9, "verbatim"))
        self.assertIn("forward_looking", g["tags"])
        ai = next(r for r in rows if r["measure"] == "company_stated_ai")
        self.assertEqual((ai["category"], ai["value"], ai["check"]), ("ai_capex", 1e9, "verbatim"))
        self.assertIn("part_year", ai["tags"])  # Q1: tagged, never turned into a year
        pj = next(r for r in rows if r["category"] == "project")
        self.assertEqual((pj["measure"], pj["reported_name"], pj["check"]), ("planned", "Project Rainier", "verbatim"))
        self.assertIn("capacity_mw:2200", pj["tags"])
        self.assertTrue(all(r["standard_concept"] for r in rows))

    def test_the_taxonomy_file_names_a_standard_for_every_category(self):
        t = taxonomy.load()
        self.assertEqual(t["version"], "taxonomy@v1")
        for m in ("spent", "committed", "planned"):
            for c in t["measures"][m]["categories"]:
                self.assertIn(c["standard"], list(t["standards"]) + ["none"], c["id"])


if __name__ == "__main__":
    unittest.main()
