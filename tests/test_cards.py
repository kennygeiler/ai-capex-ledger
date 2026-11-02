"""ledger/cards.py: the trail's evidence cards say, in plain words, what was found, where (a link to the row) and how
we know, and never change an item's state."""
import unittest

from ledger import cards, store


class Money(unittest.TestCase):
    def test_reads_like_people_read_money(self):
        self.assertEqual(cards.money(131_819_000_000), "$131,819M")
        self.assertEqual(cards.money(-384_809_000), "−$384.8M")
        self.assertEqual(cards.money(450_000), "$450,000")
        self.assertEqual(cards.money(None), "—")


class How(unittest.TestCase):
    def how(self, **it):
        return cards._how(it, "Amazon", {}, it.pop("found", None) if "found" in it else None)

    def test_each_kind_of_evidence_in_one_sentence(self):
        self.assertEqual(self.how(state="checked", by="xbrl", ref={"reference": 5_000_000})["tone"], "ok")
        self.assertIn("Matches SEC XBRL: $5M", self.how(state="checked", by="xbrl", ref={"reference": 5_000_000})["text"])
        self.assertIn("Quote matches source", self.how(state="checked", by="quote")["text"])
        nr = self.how(state="explained", by="label:no_reference")
        self.assertEqual(nr["tone"], "info")
        self.assertIn("No external source", nr["text"])
        wait = self.how(state="open", by="label:to_confirm")
        self.assertEqual(wait["tone"], "wait")
        self.assertIn("Reconcile", wait["text"])
        self.assertEqual(self.how(state="open", by="label:not_extracted")["tone"], "bad")

    def test_the_ladder_in_plain_words(self):
        """T92: a tie and a second reading are corroborated, between Verified (SEC XBRL) and citation only; readings that
        differ say both figures."""
        tie = self.how(state="checked", by="rule:ppe_categories_tie", ref={"tie": {"total": 30_000_000, "tolerance": 1_500, "dimensions": ["Buildings", "Land"],
                                                                            "parts": [{"dimension": "Buildings", "value": 20_000_000}, {"dimension": "Land", "value": 10_000_000}]}})
        # T92 review: the tie bounds the group's sum, so the card says so, with the bound and the members, once
        self.assertEqual(tie, {"tone": "corroborated", "text": "Group sums to reported total: $30M (SEC XBRL) · tolerance ±$1,500 · 2 parts (Buildings $20M; Land $10M)"})
        two = self.how(state="checked", by="reading:a1", ref={"readings": [{"accession": "a1", "value": 1}, {"accession": "a2", "value": 1}]})
        self.assertEqual(two, {"tone": "corroborated", "text": "Confirmed in 2 filings"})
        differ = self.how(state="open", by="rule:fact_readings_differ", ref={"readings": [{"value": 9_552_000, "filed": "2024-08-30"}, {"value": 1_760_000, "filed": "2025-07-30"}]})
        self.assertEqual(differ["tone"], "bad")
        self.assertEqual(differ["text"], "Readings differ: $9.6M (2024-08-30) vs $1.8M (2025-07-30)")
        fails = self.how(state="open", by="rule:segment_capex_tie", detail="2 parts sum to $985.8M; the filing tags $681.6M")
        self.assertIn("Does not tie to the reported total: 2 parts", fails["text"])
        self.assertEqual(self.how(state="checked", by="xbrl", ref={"reference": 5_000_000})["text"], "Matches SEC XBRL: $5M")
        self.assertEqual(self.how(state="explained", by="label:no_reference")["text"], "No external source. Citation verified only.")

    def test_no_internal_words(self):
        for it in ({"state": "checked", "by": "xbrl", "ref": {"reference": 1}}, {"state": "checked", "by": "located"}, {"state": "checked", "by": "gate"},
                   {"state": "explained", "by": "label:no_reference"}, {"state": "open", "by": "label:to_confirm"},
                   {"state": "checked", "by": "rule:ppe_categories_tie", "ref": {"tie": {"total": 1}}}, {"state": "checked", "by": "reading:a", "ref": {"readings": [{"accession": "a"}, {"accession": "b"}]}},
                   {"state": "open", "by": "rule:fact_readings_differ", "ref": {"readings": [{"value": 1}, {"value": 2}]}}):
            text = cards._how(it, "X", {})["text"].lower()
            for word in ("twin", "label:", "by:", "robot", "we "):
                self.assertNotIn(word, text, (it, text))


class Add(unittest.TestCase):
    def test_a_value_card_cites_its_cell_and_links_to_the_row(self):
        con = store.init(":memory:")
        con.execute("insert into documents (accession, ticker, cik, form, period, filed, url, sha256, bytes, parser_version, table_count, tables_path, income_tables, cash_flow_tables) "
                    "values ('A1', 'AMZN', '1', '10-K', '2025-12-31', '2026-02-06', 'https://sec.example/amzn.htm', 'x', 1, 'tables@15', 1, 'p', 't0', 't1')")
        con.execute("insert into extractions (extraction_id, accession, ticker, field, period_start, period_end, value, table_id, row_label, column_label, cell_text, scale, unit_stated, unit_source, confidence, prompt_version, run_id) "
                    "values ('A1|capex|x|y', 'A1', 'AMZN', 'capex', '2025-01-01', '2025-12-31', 131819000000, 't1', 'Purchases of property and equipment', 'Year | 2025', '(131,819)', 1000000, '(in millions)', 'table', 0.9, 'v', 'r')")
        con.execute("insert into \"values\" (ticker, field, period, period_end, value, source, method, label, basis, extraction_ids, input_hash) "
                    "values ('AMZN', 'capex', 'FY2025', '2025-12-31', 131819000000, 'agent', 'reported', 'agree', 'as_reported', 'A1|capex|x|y', 'h')")
        item = {"what": "capex FY2025", "state": "checked", "by": "xbrl", "ref": {"field": "capex", "period": "FY2025", "reference": 131819000000}}
        trail = {"ticker": "AMZN", "name": "Amazon", "stages": {"values": {"all": [item]}}}
        cards.add(con, trail)
        c = item["card"]
        self.assertEqual(c["found"], "$131,819M")
        self.assertIn("Purchases of property and equipment", c["where"][0]["label"])
        self.assertIn("Year 2025", c["where"][0]["label"])
        self.assertIn("#:~:text=Purchases%20of%20property%20and%20equipment", c["where"][0]["link"])
        self.assertEqual((item["state"], item["by"]), ("checked", "xbrl"))  # the card never changes the state


if __name__ == "__main__":
    unittest.main()


class SinceRelease(unittest.TestCase):
    def test_added_changed_removed_against_the_signed_release(self):
        con = store.init(":memory:")
        con.execute("insert into \"values\" (ticker, field, period, period_end, value, source, method, label, basis, extraction_ids, input_hash) values "
                    "('AMZN', 'revenue', 'FY2024', '2024-12-31', 100000000, 'agent', 'reported', 'agree', 'as_reported', 'x', 'h'), "
                    "('AMZN', 'capex', 'FY2024', '2024-12-31', 7000000, 'agent', 'reported', 'agree', 'as_reported', 'y', 'h')")
        rel = {"values": [{"ticker": "AMZN", "field": "capex", "period": "FY2024", "value": "5000000"},
                          {"ticker": "AMZN", "field": "opex", "period": "FY2024", "value": "3000000"}], "facts": []}
        out = cards.since_release(con, "AMZN", rel)
        self.assertEqual(out["added"], ["revenue · FY2024: $100M"])
        self.assertEqual(out["changed"], ["capex · FY2024: $5M → $7M"])
        self.assertEqual(out["removed"], ["opex · FY2024"])
        self.assertIsNone(cards.since_release(con, "AMZN", None))  # never shipped: nothing to compare with
