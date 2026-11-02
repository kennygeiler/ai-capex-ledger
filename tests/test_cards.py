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

    def test_no_internal_words(self):
        for it in ({"state": "checked", "by": "xbrl", "ref": {"reference": 1}}, {"state": "checked", "by": "located"}, {"state": "checked", "by": "gate"},
                   {"state": "explained", "by": "label:no_reference"}, {"state": "open", "by": "label:to_confirm"}):
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
