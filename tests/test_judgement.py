"""T36, resolve by rule: one explanation on one company, written once as a rule, closes the same cause on a second company
with no person; a definition lands in definitions/companies.yaml in the file's format with by, why and at; the writers
refuse a name off config.PEOPLE and anything beyond the one addition; POST /api/judgement through the real Handler."""
import json
import shutil
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib import error, request

import yaml

from ledger import definitions, judgement, proof, resolutions, rules, status, store, workbench

REPO_RULES = store.ROOT / "rules"
DEF_HEADER = """# Per-company definitions: a header the writer must keep.

XOM:
  revenue:
    line: Sales and other operating revenue
    why: The SEC's Revenues tag is total revenues and other income.
    by: Kenny Geiler
    at: 2026-10-28
"""
OLD, NEW = "Purchases of property and equipment", "Capital expenditures"


def _ext(ticker, acc, label, end, value, field="capex"):
    return {"extraction_id": f"{acc}|{field}|{end}", "accession": acc, "ticker": ticker, "field": field, "period_start": f"{end[:4]}-01-01",
            "period_end": end, "value": value, "unit_stated": "millions", "unit_source": "table", "scale": 1_000_000, "table_id": "t1", "row_label": label,
            "column_label": f"December 31, {end[:4]}", "cell_text": str(value), "confidence": 0.99, "notes": None, "prompt_version": "v1", "run_id": "r"}


def _company(ticker, labels):
    """Two 10-Ks; capex read from labels[0] in the first and labels[1] in the second (a renamed line). FY2024 disagrees
    with XBRL (unresolved), so the rename finding is one the SEC's data can't confirm."""
    xs = [_ext(ticker, f"{ticker}-1", labels[0], "2023-12-31", 100), _ext(ticker, f"{ticker}-2", labels[1], "2024-12-31", 140)]
    vals = [{"ticker": ticker, "field": "capex", "period": "FY2023", "period_end": "2023-12-31", "value": 100_000_000, "source": "agent", "method": "reported", "label": "agree", "basis": "as_reported", "first_reported": None, "extraction_ids": xs[0]["extraction_id"], "input_hash": "h1"},
            {"ticker": ticker, "field": "capex", "period": "FY2024", "period_end": "2024-12-31", "value": 140_000_000, "source": "agent", "method": "reported", "label": "unresolved", "basis": "as_reported", "first_reported": None, "extraction_ids": xs[1]["extraction_id"], "input_hash": "h2"}]
    ref = [{"ticker": ticker, "field": "capex", "period": "FY2023", "value": 100_000_000}, {"ticker": ticker, "field": "capex", "period": "FY2024", "value": 150_000_000}]
    return xs, vals, ref


def _db(companies):
    con = store.init(":memory:")
    for xs, vals, ref in companies:
        for x in xs:
            cols = list(x)
            con.execute(f"insert into extractions ({', '.join(cols)}) values ({', '.join('?' * len(cols))})", [x[c] for c in cols])
        for v in vals:
            cols = list(v)
            con.execute(f'insert into "values" ({", ".join(cols)}) values ({", ".join("?" * len(cols))})', [v[c] for c in cols])
        for r in ref:
            con.execute("insert into reference_values (ticker, field, period, value, method, concept, period_start, period_end, accession, restated) values (?, ?, ?, ?, 'tag', 'us-gaap:PaymentsToAcquirePropertyPlantAndEquipment', '', '', 'x', false)",
                        [r["ticker"], r["field"], r["period"], r["value"]])
    return con


def _context(con, tickers):
    q = lambda sql: [dict(zip([c[0] for c in con.execute(sql).description], r)) for r in con.execute(sql).fetchall()]
    return rules.Context(values=q('select * from "values"'), extractions=q("select * from extractions"),
                         reference={(r["ticker"], r["field"], r["period"]): r for r in q("select * from reference_values")},
                         years=["FY2023", "FY2024"], tickers=tickers)


def _run_rules(con, tickers, rules_dir):
    excs = rules.run(_context(con, tickers), rules.load(rules_dir))
    con.execute("delete from exceptions")
    store.write(con, "exceptions", excs)
    return excs


def _finding_item(ticker):
    key = resolutions.key_for("finding_unconfirmed", ticker, "capex", None, rule_id="row_label_switch")
    return key, {"kind": "finding_unconfirmed", "key": key, "ticker": ticker, "resolution": None,
                 "detail": {"rule": "row_label_switch", "kind": "row_switch", "field": "capex", "period": None, "subject": None, "message": "capex is read from different rows"}}


class Propagation(unittest.TestCase):
    """The done line: AAA's renamed capex line explained once and written as a rule; BBB, renamed the same way, is
    explained by that rule on the next rules run with no person; CCC, renamed to a different line, is not."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.rules_dir = self.tmp / "rules"
        shutil.copytree(REPO_RULES, self.rules_dir)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.con = _db([_company("AAA", [OLD, NEW]), _company("BBB", [OLD.upper(), NEW]), _company("CCC", ["Purchases of intangible assets", NEW])])

    def states(self, xp):
        idx = {}
        return {t: workbench._state(self.con, _finding_item(t)[1], idx, xp) for t in ("AAA", "BBB", "CCC")}

    def test_one_explanation_closes_the_same_cause_on_another_company(self):
        excs = _run_rules(self.con, ["AAA", "BBB", "CCC"], self.rules_dir)
        self.assertEqual(sorted(e["ticker"] for e in excs if e["rule_id"] == "row_label_switch"), ["AAA", "BBB", "CCC"])
        before = self.states(workbench._explained(self.con, ["AAA", "BBB", "CCC"]))
        self.assertEqual({t: s["state"] for t, s in before.items()}, {"AAA": "open", "BBB": "open", "CCC": "open"})

        # the person explains AAA's item in Reconcile, then writes it as a rule (the reason prefilled from the explanation)
        key, _ = _finding_item("AAA")
        why = "Purchases of property and equipment was renamed Capital expenditures; the same line"
        out = judgement.encode(self.con, key, "rule", why, "Kenny Geiler", rules_dir=self.rules_dir, at="2026-11-01")
        self.assertEqual((out["rule"], out["field"], out["row_labels"]), ("row_label_switch", "capex", [NEW, OLD]))
        written = yaml.safe_load((self.rules_dir / f"{out['id']}.yaml").read_text())
        self.assertEqual((written["severity"], written["check"], written["by"], written["why"], written["at"], written["source"]), ("info", "explains", "Kenny Geiler", why, "2026-11-01", key))

        # the next rules run: BBB closes with no person; CCC (a different line) stays open; AAA closes by the same rule
        excs = _run_rules(self.con, ["AAA", "BBB", "CCC"], self.rules_dir)
        self.assertEqual(sorted(e["ticker"] for e in excs if e["rule_id"] == out["id"]), ["AAA", "BBB"])
        on_file = mock.patch.object(rules, "RULES_DIR", self.rules_dir)  # the rules on file are the temporary copy's
        on_file.start()
        self.addCleanup(on_file.stop)
        after = self.states(workbench._explained(self.con, ["AAA", "BBB", "CCC"]))
        self.assertEqual((after["BBB"]["state"], after["BBB"]["by"]), ("explained", f"rule:{out['id']}"))
        self.assertEqual(after["CCC"]["state"], "open")
        self.assertEqual(after["AAA"]["by"], f"rule:{out['id']}")

        # Proof reads the same: BBB's finding item on the values stage is explained by the rule, and T80's walk holds
        with mock.patch.object(proof, "asset_types", return_value={}), mock.patch.object(proof, "decisions", return_value=[]):
            co = proof.company(self.con, "BBB", idx={}, defs={})
            item = next(i for i in co["stages"]["values"]["all"] if i["what"].startswith("row_label_switch"))
            self.assertEqual((item["state"], item["by"]), ("explained", f"rule:{out['id']}"))
            value = next(i for i in co["stages"]["values"]["all"] if i["what"].startswith("capex FY2024"))
            self.assertEqual(value["state"], "open")  # the rule explains the rename, not the XBRL disagreement: one cause per rule
            ev = {"definitions": {}, "rules": proof.rule_severities(rules.load(self.rules_dir)), "resolutions": {}, "person_ids": set(), "asset_types": {}, "text": lambda t: None, "quote": lambda i: []}
            self.assertIsNone(status.evidence_gap(item, ev))

    def test_precedence_a_rule_never_explains_a_checked_or_blocked_row_or_overrides_a_fix(self):
        e = {"rule_id": "jump", "severity": "warn", "message": "m"}
        self.assertEqual(status.of_exception(e, None, [status.state({"check": "xbrl"})], "explains_x")["state"], "checked")
        self.assertEqual(status.of_exception(e, None, [status.state({"rule": "sign", "severity": "block"})], "explains_x")["state"], "blocked")
        self.assertEqual(status.of_exception(e, {"id": "r1", "state": "fix", "reason": "wrong"}, [], "explains_x")["state"], "open")
        self.assertEqual(status.of_exception(e, None, [], "explains_x")["by"], "rule:explains_x")

    def test_the_rule_writer_refuses(self):
        key, _ = _finding_item("AAA")
        snap = sorted(p.name for p in self.rules_dir.iterdir())
        for by, msg in (("Claude Fable 5.1", "not a person's name"), ("Jane Doe", "not on config.PEOPLE"), ("", "not a person's name")):
            with self.assertRaises(ValueError) as c:
                judgement.encode(self.con, key, "rule", "a reason", by, rules_dir=self.rules_dir)
            self.assertIn(msg, str(c.exception))
        with self.assertRaises(ValueError):  # a block finding is never explained by a rule
            judgement.encode(self.con, resolutions.key_for("blocked", "AAA", "capex", "FY2024", rule_id="xbrl_reconcile"), "rule", "r", "Kenny Geiler", rules_dir=self.rules_dir)
        with self.assertRaises(ValueError):  # no lines, no rule
            judgement.write_rule("row_label_switch", "capex", [], "r", "Kenny Geiler", rules_dir=self.rules_dir)
        with self.assertRaises(ValueError):  # an info rule is explained already
            judgement.write_rule("restated", "capex", [OLD], "r", "Kenny Geiler", rules_dir=self.rules_dir)
        with self.assertRaises(ValueError):
            judgement.encode(self.con, key, "rule", "   ", "Kenny Geiler", rules_dir=self.rules_dir)
        self.assertEqual(sorted(p.name for p in self.rules_dir.iterdir() if not p.name.startswith(".")), [n for n in snap if not n.startswith(".")])
        judgement.encode(self.con, key, "rule", "renamed", "Kenny Geiler", rules_dir=self.rules_dir)
        with self.assertRaises(ValueError) as c:  # the same explanation twice
            judgement.encode(self.con, key, "rule", "renamed again", "Kenny Geiler", rules_dir=self.rules_dir)
        self.assertIn("already", str(c.exception))

    def test_the_loader_refuses_a_rule_that_does_not_name_its_rows(self):
        base = {"id": "explains_bad", "severity": "info", "description": "d", "rationale": "r", "owner": "Kenny Geiler", "check": "explains", "title": "t", "plain": "p", "action": "a"}
        for params, msg in (({"rule": "row_label_switch", "field": "capex", "condition": {"row_labels": []}}, "non-empty"),
                            ({"rule": "row_label_switch", "field": "capex", "condition": {"pattern": ".*"}}, "condition"),
                            ({"rule": "row_label_switch", "field": "", "condition": {"row_labels": [OLD]}}, "one field"),
                            ({"rule": "sign", "field": "capex", "condition": {"row_labels": [OLD]}}, "warn rule"),
                            ({"rule": "row_label_switch", "condition": {"row_labels": [OLD]}}, "exactly")):
            (self.rules_dir / "explains_bad.yaml").write_text(yaml.safe_dump({**base, "params": params}))
            with self.assertRaises(ValueError) as c:
                rules.load(self.rules_dir)
            self.assertIn(msg, str(c.exception))
        (self.rules_dir / "explains_bad.yaml").write_text(yaml.safe_dump({**base, "severity": "warn", "params": {"rule": "row_label_switch", "field": "capex", "condition": {"row_labels": [OLD]}}}))
        with self.assertRaises(ValueError):
            rules.load(self.rules_dir)


class Definition(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.path = self.tmp / "companies.yaml"
        self.path.write_text(DEF_HEADER)

    def test_a_definition_is_written_in_the_files_format(self):
        out = judgement.write_definition("msft", "opex", "Microsoft's OperatingExpenses tag includes cost of revenue: revenue and operating income agree", "Kenny Geiler", path=self.path, at="2026-11-01")
        self.assertEqual((out["ticker"], out["kind"], out["by"], out["at"]), ("MSFT", "opex", "Kenny Geiler", "2026-11-01"))
        text = self.path.read_text()
        self.assertTrue(text.startswith(DEF_HEADER.rstrip("\n")))  # the header and XOM's entry untouched
        self.assertIn('\nMSFT:\n  opex:\n    why: "Microsoft\'s OperatingExpenses tag includes cost of revenue: revenue and operating income agree"\n    by: Kenny Geiler\n    at: 2026-11-01\n', text)
        d = definitions.load(self.path)
        self.assertEqual((d["MSFT"]["opex"]["by"], str(d["MSFT"]["opex"]["at"])), ("Kenny Geiler", "2026-11-01"))
        self.assertTrue(definitions.opex_gap_explained(d, "MSFT"))
        # into an existing block, with lines
        judgement.write_definition("XOM", "cost_lines", "ExxonMobil reports no cost-of-revenue total", "Kenny Geiler", lines=["Crude oil purchases", 'Production, "manufacturing"'], path=self.path, at="2026-11-01")
        d = definitions.load(self.path)
        self.assertEqual(d["XOM"]["cost_lines"]["lines"], ["Crude oil purchases", 'Production, "manufacturing"'])
        self.assertEqual(d["XOM"]["revenue"]["line"], "Sales and other operating revenue")
        self.assertLess(self.path.read_text().index("  cost_lines:"), self.path.read_text().index("MSFT:"))  # inside XOM's block

    def test_the_definition_writer_refuses(self):
        cases = ((("MSFT", "opex", "why", "Claude"), "not a person's name"), (("MSFT", "opex", "why", "Jane Doe"), "not on config.PEOPLE"),
                 (("XOM", "revenue", "again", "Kenny Geiler"), "already has a revenue definition"), (("MSFT", "capex", "why", "Kenny Geiler"), "a definition is one of"),
                 (("MSFT", "opex", "  ", "Kenny Geiler"), "needs a reason"), (("MSFT", "cost_lines", "why", "Kenny Geiler"), "names the lines"))
        for args, msg in cases:
            with self.assertRaises(ValueError) as c:
                judgement.write_definition(*args, path=self.path)
            self.assertIn(msg, str(c.exception))
        self.assertEqual(self.path.read_text(), DEF_HEADER)

    def test_offers_from_the_item(self):
        con = _db([_company("AAA", [OLD, NEW])])
        defs, rs = {"XOM": {"revenue": {}}}, rules.load(REPO_RULES)
        o = judgement.offers(con, resolutions.parse_key(_finding_item("AAA")[0]), defs, rs)
        self.assertEqual((o["rule"]["rule"], o["rule"]["row_labels"]), ("row_label_switch", [NEW, OLD]))
        self.assertIn("why_not", o["definition"])
        o = judgement.offers(con, resolutions.parse_key(resolutions.key_for("blocked", "AAA", "opex", "FY2024", rule_id="xbrl_reconcile")), defs, rs)
        self.assertEqual(o["definition"], {"kind": "opex", "ticker": "AAA"})
        self.assertIn("why_not", o["rule"])
        o = judgement.offers(con, resolutions.parse_key(resolutions.key_for("blocked", "XOM", "revenue", "FY2024", rule_id="xbrl_reconcile")), defs, rs)
        self.assertIn("already has", o["definition"]["why_not"])


class Route(unittest.TestCase):
    def _serve(self):
        from ledger import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        return f"http://127.0.0.1:{srv.server_address[1]}"

    def _post(self, url, body):
        req = request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_judgement_route(self):
        from ledger import app
        base = self._serve()
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        rules_dir, defs = tmp / "rules", tmp / "companies.yaml"
        shutil.copytree(REPO_RULES, rules_dir)
        defs.write_text(DEF_HEADER)
        con = _db([_company("AAA", [OLD, NEW])])
        key = _finding_item("AAA")[0]
        body = {"key": key, "as": "rule", "why": "the same line, renamed", "by": "Kenny Geiler"}
        with mock.patch.object(app, "READONLY", True):
            code, d = self._post(base + "/api/judgement", body)
        self.assertEqual(code, 403)
        conn = mock.MagicMock(wraps=con)
        conn.close = lambda: None
        with mock.patch.object(judgement, "RULES_DIR", rules_dir), mock.patch.object(judgement, "DEF_FILE", defs), mock.patch("ledger.app._con", return_value=conn):
            code, d = self._post(base + "/api/judgement", {**body, "by": "Jane Doe"})
            self.assertEqual(code, 400)
            self.assertIn("not on config.PEOPLE", d["error"])
            code, d = self._post(base + "/api/judgement", {**body, "as": "definition"})  # a rename is no definition
            self.assertEqual(code, 400)
            self.assertEqual(sorted(p.name for p in rules_dir.glob("explains_*.yaml")), [])
            code, d = self._post(base + "/api/judgement", body)
            self.assertEqual(code, 200, d)
            self.assertTrue((rules_dir / f"{d['id']}.yaml").exists())
            dkey = resolutions.key_for("blocked", "AAA", "opex", "FY2024", rule_id="xbrl_reconcile")
            code, d = self._post(base + "/api/judgement", {"key": dkey, "as": "definition", "why": "the tag includes cost of revenue", "by": "Kenny Geiler"})
            self.assertEqual(code, 200, d)
            self.assertEqual(definitions.load(defs)["AAA"]["opex"]["by"], "Kenny Geiler")
        self.assertEqual(defs.read_text().count("XOM:"), 1)


if __name__ == "__main__":
    unittest.main()
