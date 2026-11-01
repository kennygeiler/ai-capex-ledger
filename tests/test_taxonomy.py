import unittest

import duckdb

from ledger import taxonomy

A, B = "0001018724-25-000004", "0001018724-26-000004"  # AMZN's FY2024 and FY2025 10-Ks
COMMA = "Land, buildings and leasehold improvements"  # a dimension with a comma: its extraction id holds one too


def _con():
    con = duckdb.connect()
    con.execute('create table "values" (ticker text, field text, period text, period_end text, value double, label text, extraction_ids text)')
    con.execute(f"""insert into "values" values ('AMZN','capex','FY2025','2025-12-31',131819e6,'agree','{B}|capex|2025-01-01|2025-12-31'), ('AMZN','revenue','FY2025','2025-12-31',700e9,'agree','y'),
        ('AMZN','capex','FY2024','2024-12-31',83000e6,'agree','{A}|capex|2024-01-01|2024-12-31'), ('AMZN','opex','FY2024','2024-12-31',1e9,'not_reported','{A}|opex|2024-01-01|2024-12-31')""")
    con.execute("create table documents (accession text, url text, filed text)")
    con.execute(f"insert into documents values ('{A}','https://www.sec.gov/a.htm','2025-02-07'), ('{B}','https://www.sec.gov/b.htm','2026-02-06')")
    con.execute("create table extractions (extraction_id text, ticker text, accession text, table_id text, row_label text, cell_text text)")
    con.execute(f"insert into extractions values ('{B}|capex|2025-01-01|2025-12-31','AMZN','{B}','t0035','Purchases of property and equipment','(131,819)'), ('{A}|capex|2024-01-01|2024-12-31','AMZN','{A}','t0033','Purchases of property and equipment','(83,000)')")
    con.execute("create table note_extractions (extraction_id text, ticker text, accession text, table_id text, row_label text, cell_text text)")
    con.execute(f"""insert into note_extractions values ('{B}|ppe|2025','AMZN','{B}','t0051','Servers and networking equipment','172,492'), ('{B}|ppe_category|{COMMA}|2025-12-31','AMZN','{B}','t0051','{COMMA}','9,000'),
        ('{A}|ppe|2024','AMZN','{A}','t0049','Servers and networking equipment','113,156'), ('{B}|ppe|warp','AMZN','{B}','t0051','Warp drives','1'),
        ('{B}|seg','AMZN','{B}','t0069','AWS','120,000'), ('{B}|seg2','AMZN','{B}','t0069','Other','5,000'), ('{B}|po','AMZN','{B}','t0080','Purchase commitments','84,772')""")
    con.execute("create table facts (ticker text, field text, dimension text, period text, period_end text, value double, label text, reference double, accession text, extraction_ids text)")
    con.execute(f"""insert into facts values
        ('AMZN','ppe_category','Servers and networking equipment','FY2024','2024-12-31',113156e6,'agree',113156e6,'{A}','{A}|ppe|2024'),
        ('AMZN','ppe_category','Servers and networking equipment','FY2025','2025-12-31',172492e6,'agree',172492e6,'{B}','{B}|ppe|2025'),
        ('AMZN','ppe_category','{COMMA}','FY2025','2025-12-31',9e9,'agree',9e9,'{B}','{A}|ppe_category|{COMMA}|2025-12-31,{B}|ppe_category|{COMMA}|2025-12-31'),
        ('AMZN','ppe_category','Warp drives','FY2025','2025-12-31',1e6,'no_reference',null,'{B}','{B}|ppe|warp'),
        ('AMZN','segment_revenue','AWS','FY2025','2025-12-31',120e9,'agree',120e9,'{B}','{B}|seg'),
        ('AMZN','segment_revenue','Other','FY2025','2025-12-31',5e9,'unresolved',6e9,'{B}','{B}|seg2'),
        ('AMZN','purchase_commitments','','FY2025','2025-12-31',84772e6,'no_reference',null,'{B}','{B}|po')""")
    con.execute("create table texts (text_id text, kind text, accession text, url text, date text)")
    con.execute(f"""insert into texts values ('t1','earnings_release','0001018724-26-000005','https://www.sec.gov/ex99.htm','2026-02-05'), ('t2','earnings_release',null,'https://ir.example/q1.htm','2024-04-30'),
        ('t3','transcript',null,'https://ir.example/call.pdf','2025-12-31'), ('t4','mdna','{B}','https://www.sec.gov/b.htm','2025-12-31')""")
    con.execute("create table ai_statements (ticker text, field text, period text, kind text, scope text, class text, amount_low double, amount_high double, share double, quote text, source text, text_id text)")
    con.execute("""insert into ai_statements values
        ('AMZN','capex','FY2026','outlook','total','explicit_amount',200e9,200e9,null,'We expect 2026 capital expenditures of about $200 billion.','earnings_release','t1'),
        ('AMZN','capex','FY2024','actual','ai','explicit_amount',1e9,1e9,null,'AI infrastructure capex of $1.0B in Q1.','earnings_release','t2'),
        ('AMZN','capex','FY2025','actual','ai','explicit_amount',2e9,2e9,null,'AI capex of $2.0B this year.','transcript','t3'),
        ('AMZN','capex','FY2027','actual','ai','explicit_amount',3e9,3e9,null,'AI capex of $3.0B in the quarter.','mdna','t4')""")
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
        self.assertEqual((po["check"], po["check_method"]), ("no_reference", "label:no_reference"))
        self.assertEqual((by[("spent", "segment_revenue", "Other", "FY2025")]["check"], by[("spent", "segment_revenue", "Other", "FY2025")]["check_method"]), ("differs", "xbrl"))
        self.assertNotIn("revenue", [r["category"] for r in rows if r["measure"] == "spent"])  # revenue is not spend
        self.assertTrue(all(tuple(r) == taxonomy.COLUMNS for r in rows))  # every row carries every column, in the declared order
        self.assertTrue(all("tags" not in r and "group" not in r for r in rows))  # T9, T11

    def test_check_from_the_label(self):
        self.assertEqual(taxonomy._checked("not_reported", None), ("explained", "label:not_reported"))
        self.assertEqual(taxonomy._checked("unresolved", {"state": "accept", "id": "ab12"}), ("explained", "resolution:ab12"))
        self.assertEqual(taxonomy._checked("unresolved", {"state": "explain"}), ("explained", "resolution"))  # an id-less resolution still names its kind, never "none"
        self.assertEqual(taxonomy._checked("unresolved", {"state": "fix", "id": "ab12"}), ("differs", "xbrl"))
        self.assertEqual(taxonomy._checked("unresolved", None, restated="cell from b, tag from a"), ("explained", "rule:restated_between_filings"))

    def test_the_source_is_followed_to_the_filing(self):
        rows = taxonomy.rows(_con(), ["AMZN"])
        capex = next(r for r in rows if r["category"] == "capex" and r["fiscal_year"] == "FY2025")
        self.assertEqual((capex["source"], capex["source_kind"], capex["accession"], capex["filed"]), (f"{B}|capex|2025-01-01|2025-12-31", "10-K table", B, "2026-02-06"))
        self.assertEqual((capex["source_table"], capex["source_url"]), ("t0035", "https://www.sec.gov/b.htm#:~:text=Purchases%20of%20property%20and%20equipment,131%2C819"))  # the parsed table in its own column; the filing at the row's words
        d = next(r for r in rows if r["measure"] == "derived" and r["fiscal_year"] == "FY2025" and r["reported_name"].startswith("Servers"))
        self.assertEqual((d["source_kind"], d["accession"], d["source_table"], d["source_url"]), ("10-K note", B, "t0051", "https://www.sec.gov/b.htm#:~:text=Servers%20and%20networking%20equipment,172%2C492"))
        comma = next(r for r in rows if r["reported_name"] == COMMA)  # the extraction ids hold the comma of the dimension: the last id is still found
        self.assertEqual((comma["source_table"], comma["source_url"]), ("t0051", "https://www.sec.gov/b.htm#:~:text=Land%2C%20buildings%20and%20leasehold%20improvements,9%2C000"))
        self.assertTrue(all(r["source_table"] is None for r in rows if r["source_kind"] not in ("10-K table", "10-K note")))
        g = next(r for r in rows if r["category"] == "guidance")
        self.assertEqual((g["source"], g["source_kind"], g["accession"], g["filed"]), ("t1", "8-K release", "0001018724-26-000005", "2026-02-05"))  # an 8-K's text date is its filing date
        self.assertTrue(g["source_url"].startswith("https://www.sec.gov/ex99.htm#:~:text=We%20expect%202026"))
        call = next(r for r in rows if r["source"] == "t3")
        self.assertEqual((call["source_kind"], call["accession"], call["filed"]), ("transcript", None, None))  # no filing, no filing date
        md = next(r for r in rows if r["source"] == "t4")
        self.assertEqual((md["source_kind"], md["accession"], md["filed"]), ("10-K MD&A", B, "2026-02-06"))  # the 10-K's filing date, through documents

    def test_derived_ppe_carries_the_mapping_and_the_change(self):
        rows = taxonomy.rows(_con(), ["AMZN"])
        d = [r for r in rows if r["measure"] == "derived" and r["reported_name"] == "Servers and networking equipment"]
        self.assertEqual([r["standard_type"] for r in d], ["TechnologyEquipmentMember", "TechnologyEquipmentMember"])
        self.assertEqual([r["change_from_prior"] for r in d], [None, 172492e6 - 113156e6])  # arithmetic on reported balances, in its own column (T10)
        self.assertEqual([r["value_high"] for r in d], [None, None])
        self.assertTrue(all(r["mapped"] for r in d))
        warp = next(r for r in rows if r["reported_name"] == "Warp drives")
        self.assertEqual((warp["standard_type"], warp["check"], warp["check_method"], warp["mapped"]), (None, "unmapped", "none", False))
        self.assertEqual(taxonomy.unmapped(_con(), ["AMZN"]), [{"ticker": "AMZN", "reported_name": COMMA}, {"ticker": "AMZN", "reported_name": "Warp drives"}])

    def test_periods_follow_the_fiscal_calendar(self):
        rows = taxonomy.rows(_con(), ["AMZN"])
        ai = {r["fiscal_year"]: r for r in rows if r["measure"] == "company_stated_ai" and r["source_kind"] != "gathered"}  # the statements read from texts (the gathered file has a real AMZN entry too)
        self.assertEqual((ai["FY2024"]["period_kind"], ai["FY2024"]["period_end"]), ("planned", None))  # a Q1 figure released 2024-04-30: FY2024 had not ended, whatever the reader called it
        self.assertEqual((ai["FY2025"]["period_kind"], ai["FY2025"]["period_end"]), ("reported", "2025-12-31"))  # FY2025 ended 2025-12-31, the call is dated that day
        self.assertEqual((ai["FY2027"]["period_kind"], ai["FY2027"]["period_end"]), ("planned", None))  # no 10-K reports FY2027: the calendar does not know its end
        self.assertEqual(taxonomy._period({("AMZN", "FY2024"): "2024-12-31"}, "AMZN", "FY2024", "2024-04-30"), {"period_end": None, "period_kind": "planned"})  # written before the year ended

    def test_planned_and_company_stated_are_verbatim_with_their_flags(self):
        rows = taxonomy.rows(_con(), ["AMZN"])
        g = next(r for r in rows if r["category"] == "guidance")
        self.assertEqual((g["measure"], g["value"], g["value_high"], g["check"], g["check_method"]), ("planned", 200e9, None, "verbatim", "quote"))  # a point figure has no range high
        self.assertEqual((g["period_kind"], g["period_end"], g["forward_looking"], g["part_year"], g["program"]), ("planned", None, True, False, False))
        ai = next(r for r in rows if r["measure"] == "company_stated_ai" and r["fiscal_year"] == "FY2024")
        self.assertEqual((ai["category"], ai["value"], ai["check"], ai["kind"], ai["forward_looking"]), ("ai_capex", 1e9, "verbatim", "actual", False))
        self.assertTrue(ai["part_year"])  # Q1: flagged, never turned into a year
        pj = next(r for r in rows if r["category"] == "project")
        self.assertEqual((pj["measure"], pj["reported_name"], pj["check"], pj["kind"]), ("planned", "Project Rainier", "verbatim", None))
        self.assertEqual((pj["project_kind"], pj["status"], pj["location"], pj["capacity_mw"]), ("data_center", "under_construction", "Indiana", 2200))
        self.assertEqual((pj["value"], pj["has_value"], pj["unit"], pj["forward_looking"]), (None, False, None, None))  # no amount: the row stays, valueless (T15), no unit; the source does not say forward-looking
        self.assertTrue(all(r["standard_concept"] for r in rows))

    def test_the_taxonomy_file_names_a_standard_for_every_category(self):
        t = taxonomy.load()
        self.assertEqual(t["version"], "taxonomy@v1")
        for m in ("spent", "committed", "planned"):
            for c in t["measures"][m]["categories"]:
                self.assertIn(c["standard"], list(t["standards"]) + ["none"], c["id"])


if __name__ == "__main__":
    unittest.main()
