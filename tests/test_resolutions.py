import json
import unittest

from ledger import resolutions
from ledger.resolutions import key_for


class Keys(unittest.TestCase):
    def test_key_is_built_from_fields_and_round_trips(self):
        k = key_for("fact_differs", "IRM", "segment_capex", "FY2023", "GLOBAL DATA CENTER BUSINESS")
        self.assertEqual(k, "fact_differs|IRM|segment_capex|FY2023|GLOBAL DATA CENTER BUSINESS||")
        self.assertEqual(resolutions.parse_key(k), {"kind": "fact_differs", "ticker": "IRM", "field": "segment_capex", "period": "FY2023", "dimension": "GLOBAL DATA CENTER BUSINESS", "rule_id": "", "subject": ""})
        # a '|' inside a part (XOM's "Chemical Products | Non-U.S.", a rule's subject) never breaks the seven parts
        k = key_for("finding_unconfirmed", "CLSK", "capex", None, None, "unit_from_document", "0000950170-22-026564|capex|2020-10-01|2021-09-30")
        self.assertEqual(k.count("|"), 6)
        self.assertEqual(resolutions.parse_key(k)["subject"], "0000950170-22-026564|capex|2020-10-01|2021-09-30")
        self.assertEqual(resolutions.parse_key(key_for("fact_changed", "XOM", "segment_capex", "FY2020", "Chemical Products | Non-U.S."))["dimension"], "Chemical Products | Non-U.S.")
        self.assertIsNone(resolutions.parse_key("finding_unconfirmed|LITE|operating_income"))  # the shape before T62

    def test_parse_each_kind(self):
        self.assertEqual(resolutions._parse(key_for("fact_differs", "IRM", "segment_capex", "FY2023", "GLOBAL DATA CENTER BUSINESS")), ("facts", "IRM", "segment_capex", "GLOBAL DATA CENTER BUSINESS", "FY2023", ""))
        self.assertEqual(resolutions._parse(key_for("finding_unconfirmed", "LITE", "operating_income", rule_id="row_label_switch")), ("values", "LITE", "operating_income", "", "", ""))
        self.assertEqual(resolutions._parse(key_for("finding_unconfirmed", "T", "opex", "FY2022", rule_id="jump")), ("values", "T", "opex", "", "FY2022", ""))
        self.assertEqual(resolutions._parse(key_for("blocked", "T", "opex", "FY2022", rule_id="cost_lines_summed", subject="x|y")), ("values", "T", "opex", "", "FY2022", ""))
        self.assertIsNone(resolutions._parse(key_for("new_filing", "X", "10-K", "2025-12-31")))
        # kinds the inferred layer produced (2ee2e6f removed it) name no row today; nor does a legacy-shaped key
        self.assertIsNone(resolutions._parse(key_for("reference_disagrees", "AMD", "AI revenue", "FY2024")))
        self.assertIsNone(resolutions._parse("finding_unconfirmed|LITE|operating_income"))

    def test_live_kinds_are_what_the_queue_produces(self):
        import re
        src = (resolutions.ROOT / "ledger" / "app.py").read_text()
        produced = set(re.findall(r'queue\.append\(\{"kind": "([a-z_]+)"', src))
        self.assertEqual(produced - {"value_missing"}, set(resolutions.LIVE_KINDS))  # value_missing (T65) takes no resolution: the fix is a re-read, so it is never live
        self.assertIn("value_missing", produced)
        self.assertEqual(len(re.findall(r'"key": resolutions\.key_for\(', src)), len(resolutions.LIVE_KINDS))  # every live kind keys through key_for
        self.assertNotIn("q_['where']}\"", src)  # never the display string
        self.assertTrue(resolutions.is_live(key_for("fact_differs", "IRM", "segment_capex", "FY2023", "X")))
        self.assertFalse(resolutions.is_live(key_for("value_missing", "AMD", "revenue", "FY2022")))
        self.assertFalse(resolutions.is_live(key_for("reference_disagrees", "AMD", "AI revenue", "FY2024")))
        self.assertFalse(resolutions.is_live("fact_differs|IRM|segment_capex X FY2023"))  # legacy shape: migrated or archived, not live

    def test_by_row_takes_the_latest_and_status_of_falls_back_to_the_field(self):
        k1, k2 = key_for("fact_differs", "TSLA", "segment_capex", "FY2024", "Energy"), key_for("finding_unconfirmed", "LITE", "operating_income", rule_id="row_label_switch")
        rs = [{"key": k1, "hash": "a", "state": "accept", "reason": "r", "by": "k", "at": "1"},
              {"key": k1, "hash": "a", "state": "fix", "reason": "r", "by": "k", "at": "2"},
              {"key": k2, "hash": "b", "state": "explain", "reason": "r", "by": "k", "at": "3"},
              {"key": key_for("reference_disagrees", "TSLA", "AI capex", "FY2024"), "hash": "c", "state": "fix", "reason": "stale", "by": "k", "at": "4"}]
        idx = resolutions.by_row(rs)
        self.assertEqual(idx[("facts", "TSLA", "segment_capex", "Energy", "FY2024", "")]["status"], "fix_pending")
        self.assertEqual(resolutions.status_of(idx, "facts", "TSLA", "segment_capex", "Energy", "FY2024"), "fix_pending")
        self.assertEqual(resolutions.status_of(idx, "facts", "TSLA", "segment_capex", "Energy", "FY2025"), "")
        self.assertFalse([k for k in idx if k[0] == "attribution"])  # a stale kind maps onto no row
        self.assertEqual(resolutions.status_of(idx, "values", "LITE", "operating_income", "", "FY2023"), "explained")  # no period in the key: every year

    def test_two_findings_on_one_field_and_year_both_stay_resolved(self):
        """T62: a jump and an opex-over-revenue on RIOT opex FY2025 are two keys; resolving the second keeps the first."""
        a, b = key_for("finding_unconfirmed", "RIOT", "opex", "FY2025", rule_id="jump"), key_for("finding_unconfirmed", "RIOT", "opex", "FY2025", rule_id="opex_over_revenue")
        self.assertNotEqual(a, b)
        rs = [{"id": "1", "key": a, "hash": "h1", "state": "accept", "reason": "the jump is real", "by": "Kenny Geiler", "at": "2026-11-01T00:00:00"},
              {"id": "2", "key": b, "hash": "h2", "state": "explain", "reason": "opex includes impairments", "by": "Kenny Geiler", "at": "2026-11-01T00:01:00"}]
        lt = resolutions.latest(rs)
        self.assertEqual((lt[a]["state"], lt[b]["state"]), ("accept", "explain"))
        self.assertEqual(resolutions.status_of(resolutions.by_row(rs), "values", "RIOT", "opex", "", "FY2025"), "explained")  # the row carries the latest of the two
        # the same rule on two filings (unit_from_document on CLSK capex) is two keys too
        self.assertNotEqual(key_for("finding_unconfirmed", "CLSK", "capex", rule_id="unit_from_document", subject="0000950170-22-026564|capex|2020-10-01|2021-09-30"),
                            key_for("finding_unconfirmed", "CLSK", "capex", rule_id="unit_from_document", subject="0000950170-23-000001|capex|2021-10-01|2022-09-30"))

    def test_a_row_takes_the_worst_of_its_findings_and_stays_open_with_an_unresolved_sibling(self):
        """T62 review: HUT capex FY2023 carries a jump and a capex_intensity finding, two keys on one row."""
        a, b = key_for("finding_unconfirmed", "HUT", "capex", "FY2023", rule_id="jump"), key_for("finding_unconfirmed", "HUT", "capex", "FY2023", rule_id="outlier_vs_own_history")
        row = ("values", "HUT", "capex", "", "FY2023", "")
        ra = {"id": "1", "key": a, "hash": "ha", "state": "accept", "reason": "r", "by": "Kenny Geiler", "at": "1"}
        rb = {"id": "2", "key": b, "hash": "hb", "state": "fix", "reason": "r", "by": "Kenny Geiler", "at": "2"}
        self.assertEqual(resolutions.by_row([ra, rb])[row]["status"], "fix_pending")  # worst wins, whatever the order
        self.assertEqual(resolutions.by_row([rb, ra])[row]["status"], "fix_pending")
        self.assertEqual(resolutions.by_row([ra, {**rb, "state": "blocks"}])[row]["status"], "blocks")
        self.assertEqual(resolutions.by_row([ra, {**rb, "state": "explain"}])[row]["status"], "explained")
        items = [{"key": a, "hash": "ha"}, {"key": b, "hash": "hb"}]
        self.assertEqual(resolutions.by_row([ra, {**rb, "state": "accept"}], items)[row]["status"], "accepted")
        self.assertNotIn(row, resolutions.by_row([ra], items))  # one accepted, one with no resolution: the row reads open
        self.assertNotIn(row, resolutions.by_row([ra, {**rb, "hash": "stale"}], items))  # an expired sibling is unresolved too
        self.assertEqual(resolutions.by_row([ra, {**rb, "hash": "stale"}], items[:1])[row]["status"], "fix_pending")  # a queue without the sibling: its hash cannot be judged, its resolution counts as written
        self.assertIn(row, resolutions.by_row([ra], None))  # no queue given (exports): the resolutions alone

    def test_the_hash_is_the_pre_t62_hash(self):
        """T62 review: only the fields hq added for the key are left out, per kind, so no live resolution expired."""
        import hashlib
        from ledger.app import content_hash
        pre = lambda d: hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:12]
        q = {"detail": None, "exception_id": "cost_lines_summed|T|opex|FY2022|None", "ticker": "T", "company": "AT&T", "rule": "cost_lines_summed", "severity": "block", "title": "t", "why": "w", "field": "opex", "period": "FY2022", "message": "m"}
        self.assertEqual(content_hash("blocked", {**q, "subject": None}), pre(q))  # a question carried `rule` before T62
        f = {"ticker": "HUT", "company": "Hut 8", "field": "capex", "period": "FY2023", "confirmed": False, "message": "m", "kind": "jump", "before": 1, "after": 3, "from": "FY2022", "size": 3.0}
        self.assertEqual(content_hash("finding_unconfirmed", {**f, "rule": "jump", "subject": None}), pre(f))
        self.assertEqual(content_hash("fact_differs", f), pre(f))

    def test_resolve_refuses_a_key_that_is_not_a_queue_items(self):
        with self.assertRaises(ValueError):
            resolutions.resolve("finding_unconfirmed|LITE|operating_income", "h", "accept", "r", "Kenny Geiler")  # legacy shape
        with self.assertRaises(ValueError):
            resolutions.resolve(key_for("reference_disagrees", "AMD", "AI revenue", "FY2024"), "h", "accept", "r", "Kenny Geiler")  # stale kind
        with self.assertRaises(ValueError):
            resolutions.resolve("", "h", "accept", "r", "Kenny Geiler")

    def test_the_resolve_route_answers_400_to_a_bad_key(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib import error, request
        from ledger import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        req = request.Request(f"http://127.0.0.1:{srv.server_address[1]}/api/resolve", data=json.dumps({"key": "finding_unconfirmed|LITE|operating_income", "hash": "h", "state": "accept", "reason": "r", "by": "Kenny Geiler"}).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(error.HTTPError) as cm:
            request.urlopen(req)
        self.assertEqual(cm.exception.code, 400)
        self.assertIn("not a queue item's key", json.loads(cm.exception.read())["error"])
        self.assertEqual(resolutions.load()[-1]["by"], "Kenny Geiler")  # nothing appended: the last line is still the migrated one

    def test_the_stage3_queue_has_no_duplicate_keys(self):
        """T62 done-when: over every company the database holds (the 21 keys of 1 Nov were HUT, RIOT, CEG, T, VST, ...)."""
        from collections import Counter
        from ledger import app, store
        if not store.DEFAULT_DB.exists():
            self.skipTest("no working database")
        for t in sorted(c["ticker"] for c in app.tracked()):
            c = Counter(q["key"] for q in app._flow(t)["queue"])
            self.assertEqual([k for k, n in c.items() if n > 1], [], t)

    def test_log_is_at_the_repo_root_and_tracked(self):
        self.assertEqual(resolutions.LOG, resolutions.ROOT / "decisions" / "resolutions.jsonl")
        self.assertNotIn("resolutions.jsonl", (resolutions.ROOT / ".gitignore").read_text())


class MigrateKeys(unittest.TestCase):
    """T62: the one-off from kind|ticker|where to key_for(), on a temp copy of a synthetic log."""

    QUEUE = {"LITE": [{"kind": "finding_unconfirmed", "ticker": "LITE", "where": "operating_income", "hash": "29c944176fef", "key": key_for("finding_unconfirmed", "LITE", "operating_income", rule_id="row_label_switch")}],
             "RIOT": [{"kind": "finding_unconfirmed", "ticker": "RIOT", "where": "opex FY2025", "hash": "h1", "key": key_for("finding_unconfirmed", "RIOT", "opex", "FY2025", rule_id="jump")},
                      {"kind": "finding_unconfirmed", "ticker": "RIOT", "where": "opex FY2025", "hash": "h2", "key": key_for("finding_unconfirmed", "RIOT", "opex", "FY2025", rule_id="opex_over_revenue")}],
             "GONE": []}
    LINES = [{"id": "a", "key": "finding_unconfirmed|LITE|operating_income", "hash": "29c944176fef", "state": "accept", "reason": "confirmed", "by": "Kenny Geiler", "at": "2026-11-01T02:01:26+00:00"},
             {"id": "b", "key": "finding_unconfirmed|RIOT|opex FY2025", "hash": "h1", "state": "accept", "reason": "x", "by": "Claude, for Kenny to confirm", "at": "2026-10-30T00:00:00"},
             {"id": "c", "key": "finding_unconfirmed|GONE|capex FY2024", "hash": "h", "state": "fix", "reason": "y", "by": "Claude, for Kenny to confirm", "at": "2026-10-30T00:00:00"},
             {"id": "d", "key": key_for("fact_differs", "AMD", "capex", "FY2024"), "hash": "h", "state": "accept", "reason": "z", "by": "Kenny Geiler", "at": "2026-10-31T00:00:00"}]

    def test_plan_one_mappable_one_ambiguous_one_orphan_one_already_new(self):
        plan = resolutions.migrate_keys(self.LINES, lambda t: self.QUEUE[t], now="2026-11-01T12:00:00+00:00")
        self.assertEqual([r["id"] for r in plan["migrated"]], ["a"])
        m = plan["migrated"][0]
        self.assertEqual((m["key"], m["migrated_from"], m["by"], m["hash"], m["at"]), (self.QUEUE["LITE"][0]["key"], "finding_unconfirmed|LITE|operating_income", "Kenny Geiler", "29c944176fef", "2026-11-01T02:01:26+00:00"))
        self.assertNotIn("current", m)  # the CLI prints it; the log never carries it
        self.assertEqual(plan["current"], {"a": True})
        self.assertEqual([r["id"] for r in plan["archived"]], ["b", "c"])
        self.assertIn("2 queue items carry this key", plan["archived"][0]["note"])
        self.assertIn("no queue item", plan["archived"][1]["note"])
        self.assertEqual([r["id"] for r in plan["untouched"]], ["d"])

    def test_write_appends_and_archives_and_removes_nothing(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            log, arch = Path(d) / "resolutions.jsonl", Path(d) / "archive" / "resolutions-keys.jsonl"
            log.write_text("".join(json.dumps(r) + "\n" for r in self.LINES))
            plan = resolutions.migrate_keys(resolutions.load(log), lambda t: self.QUEUE[t])
            resolutions.write_migration(plan, log, arch)
            rows = resolutions.load(log)
            self.assertEqual([r["id"] for r in rows], ["a", "b", "c", "d", "a"])  # the old lines stay; the migrated one is appended
            self.assertEqual(rows[-1]["by"], "Kenny Geiler")
            self.assertEqual(resolutions.unconfirmed(rows), [])  # b and c are legacy-shaped: not live, not counted
            self.assertEqual(resolutions.latest(rows)[self.QUEUE["LITE"][0]["key"]]["state"], "accept")
            a = resolutions.load(arch)
            self.assertIn("note", a[0])
            self.assertEqual([r["id"] for r in a[1:]], ["b", "c"])
            # a second run, reading the archive too, finds nothing left to do
            again = resolutions.migrate_keys(rows, lambda t: self.QUEUE[t], archived_before=[r for r in a if "key" in r])
            self.assertEqual((again["migrated"], again["archived"], len(again["untouched"])), ([], [], 5))


if __name__ == "__main__":
    unittest.main()


class ToConfirm(unittest.TestCase):
    """T3: the decisions a run made for a person to confirm stay flagged until that person resolves the same key."""

    def test_unconfirmed_is_the_latest_per_key_that_says_to_confirm(self):
        from ledger.resolutions import unconfirmed
        ka, kb, kc, kd = key_for("fact_differs", "A", "x", "FY2024", "d"), key_for("blocked", "B", "y", "FY2024", rule_id="r"), key_for("new_filing", "C", "10-K", "2025-12-31"), key_for("fact_changed", "D", "z", "FY2023")
        rs = [{"id": "a", "key": ka, "hash": "h", "state": "fix", "reason": "x", "by": "Replication run (Claude), for Kenny to confirm", "at": "2026-10-30T00:00:00"},
              {"id": "b", "key": ka, "hash": "h", "state": "accept", "reason": "y", "by": "Claude, for Kenny Geiler to confirm", "at": "2026-10-31T00:00:00"},
              {"id": "c", "key": kb, "hash": "h", "state": "explain", "reason": "fine, to confirm later", "by": "Claude", "at": "2026-10-29T00:00:00"},
              {"id": "d", "key": kc, "hash": "h", "state": "accept", "reason": "confirmed", "by": "Kenny Geiler", "at": "2026-10-28T00:00:00"},
              {"id": "e", "key": kd, "hash": "h", "state": "accept", "reason": "z", "by": "Claude, for Kenny to confirm", "at": "2026-10-27T00:00:00"},
              {"id": "f", "key": kd, "hash": "h", "state": "accept", "reason": "yes", "by": "Kenny Geiler", "at": "2026-10-31T01:00:00"}]
        self.assertEqual([r["id"] for r in unconfirmed(rs)], ["c", "b"])  # k3 was a person's own; k4 was confirmed by a later resolution

    def test_the_log_on_file_is_live_and_confirmed_and_the_stale_ones_are_archived(self):
        """After the 2 Nov sweep: the live log holds only live kinds; the one decision left (LITE operating_income, a
        finding_unconfirmed) was confirmed by Kenny Geiler on 2 Nov, so nothing waits; the 12 stale lines sit under
        decisions/archive/ behind a note line. After T62 (1 Nov): its three lines sit there twice, the legacy key and
        the migrated one (`migrated_from`), and every legacy line has a migrated successor."""
        from ledger.resolutions import LOG, ROOT, is_live, load, parse_key, unconfirmed
        self.assertEqual(unconfirmed(), [])
        rows = load()
        self.assertTrue(all(kind_live for kind_live in (r["key"].partition("|")[0] in resolutions.LIVE_KINDS for r in rows)), "stale kinds belong in decisions/archive/")
        migrated = {r["migrated_from"] for r in rows if r.get("migrated_from")}
        self.assertTrue(all(is_live(r["key"]) or r["key"] in migrated for r in rows), "a legacy key without a migrated line: run `ledger resolutions migrate-keys`")
        lite = [r for r in rows if r["key"] == key_for("finding_unconfirmed", "LITE", "operating_income", rule_id="row_label_switch")]
        self.assertEqual((lite[-1]["by"], lite[-1]["state"], lite[-1]["migrated_from"]), ("Kenny Geiler", "accept", "finding_unconfirmed|LITE|operating_income"))
        self.assertTrue(all(parse_key(r["key"]) for r in rows if r.get("migrated_from")))
        arch = [json.loads(l) for l in (ROOT / "decisions" / "archive" / "resolutions-stale-2026-11-02.jsonl").read_text().splitlines() if l.strip()]
        self.assertIn("2ee2e6f", arch[0]["note"])
        self.assertEqual(len(arch) - 1, 12)
        self.assertTrue(all(not is_live(r["key"]) for r in arch[1:]))
        self.assertEqual(LOG, ROOT / "decisions" / "resolutions.jsonl")

    def test_unconfirmed_ignores_stale_kinds_even_if_present(self):
        from ledger.resolutions import unconfirmed
        rs = [{"id": "a", "key": key_for("reference_disagrees", "GOOGL", "AI capex", "FY2024"), "hash": "h", "state": "explain", "reason": "x", "by": "Claude, for Kenny to confirm", "at": "2026-10-30T00:00:00"},
              {"id": "b", "key": key_for("attribution_moved", "LITE", "revenue", "FY2025"), "hash": "h", "state": "fix", "reason": "y", "by": "Claude, for Kenny to confirm", "at": "2026-10-30T00:00:00"},
              {"id": "c", "key": key_for("finding_unconfirmed", "LITE", "operating_income", rule_id="row_label_switch"), "hash": "h", "state": "accept", "reason": "z", "by": "Claude, for Kenny to confirm", "at": "2026-10-30T00:00:00"},
              {"id": "d", "key": "finding_unconfirmed|LITE|operating_income", "hash": "h", "state": "accept", "reason": "z", "by": "Claude, for Kenny to confirm", "at": "2026-10-30T00:00:00"}]  # legacy shape: not live
        self.assertEqual([r["id"] for r in unconfirmed(rs)], ["c"])

    def test_the_release_gate_fails_while_any_live_one_remains(self):
        from ledger.release import gates
        k = key_for("finding_unconfirmed", "GOOGL", "opex", "FY2024", rule_id="jump")
        g = gates([], [], {"values": []}, frozenset(), [{"key": k}], tickers=["GOOGL"])
        self.assertEqual(g["G6"], {"GOOGL": [k]})
        self.assertEqual(gates([], [], {"values": []}, tickers=["GOOGL"])["G6"], {"GOOGL": []})
        stale = gates([], [], {"values": []}, frozenset(), [{"key": key_for("reference_disagrees", "GOOGL", "AI capex", "FY2024")}], tickers=["GOOGL"])
        self.assertEqual(stale["G6"], {"GOOGL": []})  # a stale kind is never a G6 failure, and adds no company
