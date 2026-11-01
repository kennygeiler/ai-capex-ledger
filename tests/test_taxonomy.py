import unittest

import duckdb

from ledger import taxonomy


def _con():
    con = duckdb.connect()
    con.execute('create table "values" (ticker text, field text, period text, period_end text, value double, label text, extraction_ids text)')
    con.execute("insert into \"values\" values ('AMZN','capex','FY2025','2025-12-31',131819e6,'agree','0001018724-26-000004|capex|2025-01-01|2025-12-31'), ('AMZN','revenue','FY2025','2025-12-31',700e9,'agree','y')")
    con.execute("create table documents (accession text, url text, filed text)")
    con.execute("insert into documents values ('0001018724-25-000004','https://www.sec.gov/a.htm','2025-02-07'), ('0001018724-26-000004','https://www.sec.gov/b.htm','2026-02-06')")
    con.execute("create table extractions (extraction_id text, ticker text, accession text, row_label text, cell_text text)")
    con.execute("insert into extractions values ('0001018724-26-000004|capex|2025-01-01|2025-12-31','AMZN','0001018724-26-000004','Purchases of property and equipment','(131,819)')")
    con.execute("create table note_extractions (extraction_id text, ticker text, accession text, row_label text, cell_text text)")
    con.execute("insert into note_extractions values ('0001018724-26-000004|ppe|2025','AMZN','0001018724-26-000004','Servers and networking equipment','172,492')")
    con.execute("create table facts (ticker text, field text, dimension text, period text, period_end text, value double, label text, reference double, accession text, extraction_ids text)")
    con.execute("""insert into facts values
        ('AMZN','ppe_category','Servers and networking equipment','FY2024','2024-12-31',113156e6,'agree',113156e6,'0001018724-25-000004','0001018724-25-000004|ppe|2024'),
        ('AMZN','ppe_category','Servers and networking equipment','FY2025','2025-12-31',172492e6,'agree',172492e6,'0001018724-26-000004','0001018724-26-000004|ppe|2025'),
        ('AMZN','ppe_category','Warp drives','FY2025','2025-12-31',1e6,'no_reference',null,'0001018724-26-000004','0001018724-26-000004|ppe|warp'),
        ('AMZN','segment_revenue','AWS','FY2025','2025-12-31',120e9,'agree',120e9,'0001018724-26-000004','0001018724-26-000004|seg'),
        ('AMZN','segment_revenue','Other','FY2025','2025-12-31',5e9,'unresolved',6e9,'0001018724-26-000004','0001018724-26-000004|seg2'),
        ('AMZN','purchase_commitments','','FY2025','2025-12-31',84772e6,'no_reference',null,'0001018724-26-000004','0001018724-26-000004|po')""")
    con.execute("create table texts (text_id text, kind text, accession text, url text, date text)")
    con.execute("insert into texts values ('t1','earnings_release','0001018724-26-000005','https://www.sec.gov/ex99.htm','2026-02-05'), ('t2','earnings_release',null,'https://ir.example/q1.htm','2024-04-30')")
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
        self.assertEqual((capex["standard_concept"], capex["value"], capex["check"], capex["check_method"]), ("PaymentsToAcquirePropertyPlantAndEquipment", 131819e6, "agree", "xbrl"))
        self.assertEqual((capex["period_end"], capex["period_kind"], capex["unit"], capex["scale"], capex["currency"]), ("2025-12-31", "reported", "USD", 1, "USD"))
        seg = by[("spent", "segment_revenue", "AWS", "FY2025")]
        self.assertIn("StatementBusinessSegmentsAxis", seg["standard_concept"])
        po = by[("committed", "purchase_obligations", "purchase commitments", "FY2025")]
        self.assertEqual((po["check"], po["check_method"]), ("no_reference", "none"))
        self.assertEqual((by[("spent", "segment_revenue", "Other", "FY2025")]["check"], by[("spent", "segment_revenue", "Other", "FY2025")]["check_method"]), ("differs", "xbrl"))
        self.assertNotIn("revenue", [r["category"] for r in rows if r["measure"] == "spent"])  # revenue is not spend
        self.assertTrue(all(tuple(r) == taxonomy.COLUMNS for r in rows))  # every row carries every column, in the declared order
        self.assertTrue(all("tags" not in r and "group" not in r for r in rows))  # T9, T11

    def test_the_source_is_followed_to_the_filing(self):
        rows = taxonomy.rows(_con(), ["AMZN"])
        capex = next(r for r in rows if r["category"] == "capex")
        self.assertEqual((capex["source"], capex["source_kind"], capex["accession"], capex["filed"]), ("0001018724-26-000004|capex|2025-01-01|2025-12-31", "10-K table", "0001018724-26-000004", "2026-02-06"))
        self.assertEqual(capex["source_url"], "https://www.sec.gov/b.htm#:~:text=Purchases%20of%20property%20and%20equipment,131%2C819")  # the filing, at the cited row
        d = next(r for r in rows if r["measure"] == "derived" and r["fiscal_year"] == "FY2025" and r["reported_name"].startswith("Servers"))
        self.assertEqual((d["source_kind"], d["accession"], d["source_url"]), ("10-K note", "0001018724-26-000004", "https://www.sec.gov/b.htm#:~:text=Servers%20and%20networking%20equipment,172%2C492"))
        g = next(r for r in rows if r["category"] == "guidance")
        self.assertEqual((g["source"], g["source_kind"], g["accession"], g["filed"]), ("t1", "8-K release", "0001018724-26-000005", "2026-02-05"))
        self.assertTrue(g["source_url"].startswith("https://www.sec.gov/ex99.htm#:~:text=We%20expect%202026"))

    def test_derived_ppe_carries_the_mapping_and_the_change(self):
        rows = taxonomy.rows(_con(), ["AMZN"])
        d = [r for r in rows if r["measure"] == "derived" and r["reported_name"] == "Servers and networking equipment"]
        self.assertEqual([r["standard_type"] for r in d], ["TechnologyEquipmentMember", "TechnologyEquipmentMember"])
        self.assertEqual([r["change_from_prior"] for r in d], [None, 172492e6 - 113156e6])  # arithmetic on reported balances, in its own column (T10)
        self.assertEqual([r["value_high"] for r in d], [None, None])
        self.assertTrue(all(r["mapped"] for r in d))
        warp = next(r for r in rows if r["reported_name"] == "Warp drives")
        self.assertEqual((warp["standard_type"], warp["check"], warp["check_method"], warp["mapped"]), (None, "unmapped", "none", False))
        self.assertEqual(taxonomy.unmapped(_con(), ["AMZN"]), [{"ticker": "AMZN", "reported_name": "Warp drives"}])

    def test_planned_and_company_stated_are_verbatim_with_their_flags(self):
        rows = taxonomy.rows(_con(), ["AMZN"])
        g = next(r for r in rows if r["category"] == "guidance")
        self.assertEqual((g["measure"], g["value"], g["value_high"], g["check"], g["check_method"]), ("planned", 200e9, None, "verbatim", "quote"))  # a point figure has no range high
        self.assertEqual((g["period_kind"], g["period_end"], g["forward_looking"], g["part_year"], g["program"]), ("planned", None, True, False, False))
        ai = next(r for r in rows if r["measure"] == "company_stated_ai")
        self.assertEqual((ai["category"], ai["value"], ai["check"], ai["kind"]), ("ai_capex", 1e9, "verbatim", "actual"))
        self.assertTrue(ai["part_year"])  # Q1: flagged, never turned into a year
        self.assertEqual((ai["period_kind"], ai["period_end"], ai["forward_looking"]), ("reported", None, False))  # FY2024 has no values row here, so no period end is known
        pj = next(r for r in rows if r["category"] == "project")
        self.assertEqual((pj["measure"], pj["reported_name"], pj["check"]), ("planned", "Project Rainier", "verbatim"))
        self.assertEqual((pj["kind"], pj["status"], pj["location"], pj["capacity_mw"]), ("data_center", "under_construction", "Indiana", 2200))
        self.assertEqual((pj["value"], pj["has_value"], pj["unit"]), (None, False, "MW"))  # no amount: the row stays, valueless (T15), sized in megawatts (T17)
        self.assertTrue(all(r["standard_concept"] for r in rows))

    def test_the_taxonomy_file_names_a_standard_for_every_category(self):
        t = taxonomy.load()
        self.assertEqual(t["version"], "taxonomy@v1")
        for m in ("spent", "committed", "planned"):
            for c in t["measures"][m]["categories"]:
                self.assertIn(c["standard"], list(t["standards"]) + ["none"], c["id"])


if __name__ == "__main__":
    unittest.main()
