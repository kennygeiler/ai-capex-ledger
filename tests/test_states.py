"""ledger/core/states.py: one place per state (docs/STATES.md). Three kinds of test, plus the consumers routed through it:
1. no illegal transition (declared moves only; a person's decision never makes a row checked);
2. no unknown, stale or missing input reads as a good state (every machine's absent case, and the pages' fallback);
3. every page word names exactly one state, every state has a word, and the pages read the words from states.py."""
import json
import re
import subprocess
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from ledger.web import cards
from ledger.release import checklist, claims
from ledger.core import states, status, store
from ledger.checks import ties

PAGES = store.ROOT / "ledger" / "web" / "pages"


class Declarations(unittest.TestCase):
    def test_every_machine_names_a_compute_function_that_imports(self):
        for m in states.MACHINES.values():
            self.assertIsNone(claims.function_imports(m.compute), m.id)

    def test_every_state_has_a_known_kind_and_resolves_to_a_word_and_a_tone(self):
        for mid, m in states.MACHINES.items():
            self.assertEqual(len(set(m.names())), len(m.names()), mid)
            for s in m.states:
                self.assertIn(s.kind, states.KINDS, (mid, s.name))
                self.assertFalse(s.label and s.alias, (mid, s.name, "a word or an alias, not both"))
                r = states.resolve(mid, s.name)
                self.assertTrue(r.label and r.tone, (mid, s.name))
                if s.alias:  # an alias is the same thing on a page: it cannot be good where its owner is not
                    self.assertEqual(s.kind == states.GOOD, r.kind == states.GOOD, (mid, s.name, s.alias))


class Transitions(unittest.TestCase):
    """(1) No illegal transition."""

    def test_declared_transitions_name_declared_states(self):
        for mid, m in states.MACHINES.items():
            for a, b in m.transitions:
                m.get(a), m.get(b)

    def test_allow_refuses_an_undeclared_move(self):
        states.allow("gold", "unchecked", "right")
        states.allow("gold", "right", "right")
        for machine, a, b in (("gold", "right", "unchecked"), ("crop", "located", "none"), ("mapping", "confirmed", "unmapped"), ("line", "pass", "not_run")):
            with self.assertRaises(states.IllegalTransition, msg=(machine, a, b)):
                states.allow(machine, a, b)
        with self.assertRaises(KeyError):
            states.allow("row", "ok", "certified")

    def test_a_persons_decision_never_makes_a_row_checked(self):
        for res, grp in states.DECISION_MOVES.items():
            for row in ({}, {"label": "no_reference"}, {"rule": "jump", "severity": "warn"}, {"label": "unresolved"}):
                st = status._state({**row, "resolution": {"id": "r", "state": res, "reason": "x"}})
                self.assertEqual(st["state"], grp, (res, row))
                self.assertNotEqual(states.group(states.row(st["state"], st["by"])), "checked")

    def test_a_gold_verdict_never_goes_back_to_unchecked(self):
        from ledger.review import gold
        with mock.patch.object(states, "allow", wraps=states.allow) as allow, self.assertRaises(Exception):
            gold.record("NOPE", "x", "right", "", "Kenny Geiler")
        for it in (i for p in sorted((store.ROOT / "gold").glob("*.json")) for i in json.loads(p.read_text()).get("items", [])):
            states.allow("gold", "unchecked", states.gold(it))  # every committed verdict is reachable from unchecked


class NothingAbsentReadsGood(unittest.TestCase):
    """(2) An unknown, stale or missing input is its own state, never a good one."""

    def kind(self, machine, name):
        return states.MACHINES[machine].get(name).kind

    def test_every_machine_says_what_an_absent_input_gives(self):
        for mid, m in states.MACHINES.items():
            self.assertTrue(m.absent, mid)
            if m.absent in m.names():
                self.assertNotEqual(self.kind(mid, m.absent), states.GOOD, mid)
            self.assertTrue(any(s.kind in states.NEVER_GOOD for s in m.states) or m.no_unknown_because, f"{mid} declares no unknown, stale or missing state, nor why")

    def test_the_absent_cases(self):
        old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        cases = [("row", states.row(None, "")), ("row", states.row("certified", "xbrl")), ("check", states.check(None)), ("check", states.check("bogus")),
                 ("ladder", states.ladder({})), ("gold", states.gold({})), ("gold", states.gold({"verdict": "maybe"})),
                 ("mapping", states.mapping(status.of_mapping(None))),
                 ("edgar", states.edgar(None)[0]), ("edgar", states.edgar("yesterday")[0]), ("edgar", states.edgar("2026-01-01T00:00:00")[0]), ("edgar", states.edgar(old)[0]),
                 ("line", checklist.tests_line(None)["state"]),
                 ("line", checklist.tests_line({"ok": True, "count": 1, "git": "abc", "dirty": True}, head="abc")["state"]),
                 ("line", checklist.tests_line({"ok": True, "count": 1, "git": "abc", "dirty": False}, head="def", changed=["ledger/x.py"])["state"])]
        from ledger.checks import crops
        cases.append(("crop", crops.state(None, {}, None, None)["state"]))
        for machine, name in cases:
            self.assertNotEqual(self.kind(machine, name), states.GOOD, (machine, name))
        self.assertEqual([n for _, n in cases[-4:-1]], ["not_run", "stale", "stale"])  # a stale test run is its own word, not Info

    def test_the_pages_fall_back_to_the_absent_state(self):
        shared = (PAGES / "_shared.js").read_text()
        helpers = shared[shared.index("// ── state words"):shared.index("// ── end states-helpers")]
        js = states.js() + helpers + "process.stdout.write(JSON.stringify(['row', 'crop', 'line', 'check', 'gold', 'edgar'].map((m) => stateWord(m, 'no-such-state'))));"
        got = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
        self.assertEqual([w for _, w in got], [states.word(m, states.MACHINES[m].absent) for m in ("row", "crop", "line", "check", "gold", "edgar")])


class PagesWithoutTheDeclarations(unittest.TestCase):
    """A failed /pages/_states.js load must not stop a page: every page reads STATES through _shared.js's guarded helpers."""

    def run_node(self, with_states: bool, tail: str) -> str:
        shared = (PAGES / "_shared.js").read_text()
        helpers = shared[shared.index("// ── state words"):shared.index("// ── end states-helpers")]
        stubs = ("const h = (tag, attrs = {}, ...kids) => kids.flat(Infinity).filter((k) => k !== '' && k != null && k !== false).join('');\n"
                 "const int = (n) => String(n); const document = {addEventListener: () => {}, getElementById: () => null}; let me = '';\n")
        js = (states.js() if with_states else "") + stubs + helpers + (PAGES / "proof.js").read_text() + "\n" + tail
        return subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout

    def test_proof_loads_and_renders_with_states_undefined(self):
        tail = ("process.stdout.write(JSON.stringify([typeof STATES, stageCell({checked: 5, done: 2, explained: 1, blocked: 0, open: [1]}), goldWord('right'), stateWord('row', 'ok')]));")
        typ, cell, gold, word = json.loads(self.run_node(False, tail))
        self.assertEqual((typ, gold, word), ("undefined", "right", ["text-secondary", "ok"]))
        self.assertIn("3", cell)
        _, cell, gold, word = json.loads(self.run_node(True, tail))
        self.assertEqual((gold, word), ("Right", ["text-green", "Verified"]))

    def test_the_page_scripts_share_one_scope_without_a_clash(self):
        """app.html's scripts share one global scope: a name declared twice (const) stops every page after it."""
        import tempfile
        html = (store.ROOT / "ledger" / "web" / "app.html").read_text()
        srcs = re.findall(r'<script src="/pages/([\w.]+)"', html)
        self.assertEqual(srcs[:2], ["_states.js", "_shared.js"])
        js = "\n".join(states.js() if s == "_states.js" else (PAGES / s).read_text() for s in srcs)
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(js)
        r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        Path(f.name).unlink()
        self.assertEqual(r.returncode, 0, r.stderr[:500])

    def test_no_page_reads_the_declarations_directly(self):
        for f in PAGES.glob("*.js"):
            code = "\n".join(l for l in f.read_text().splitlines() if not l.lstrip().startswith("//"))
            if f.name == "_shared.js":
                code = code[:code.find("const stateData")] + code[code.find("const checkWord"):]
            self.assertNotRegex(code, r"\bSTATE(S|_GROUPS|_ABSENT)\b", f.name)


class Words(unittest.TestCase):
    """(3) Every word names one state; every state has a word; the pages read them from states.py."""

    def test_every_word_names_exactly_one_state(self):
        for w, owners in states.words().items():
            if len(owners) == 1:
                continue
            # a group word may repeat the word of its only member, in the same machine
            (m1, a), (m2, b) = sorted(owners)[:2]
            self.assertEqual(len(owners), 2, (w, owners))
            self.assertEqual(m1, m2, (w, owners))
            grp, st = (a, b) if a.startswith("group:") else (b, a)
            self.assertEqual(states.MACHINES[m1].groups[grp.removeprefix("group:")][1], (st,), (w, owners))

    def test_the_groups_cover_the_row_states_and_status_states(self):
        members = [s for _, ms in states.ROW.groups.values() for s in ms]
        self.assertEqual(sorted(members), sorted(n for n in states.ROW.names() if n != "unknown"))
        self.assertEqual(set(states.ROW.groups), set(states.STATUS_OF_GROUP))
        self.assertEqual(set(states.STATUS_OF_GROUP.values()), set(status.STATES))
        for g, (_, members) in states.ROW.groups.items():  # the word Checked never covers a row nothing independent checked
            self.assertEqual(g == "checked", all(states.ROW.get(m).kind == states.GOOD for m in members), g)

    def test_the_scan_reads_the_words_from_states_py(self):
        sc = claims.scan()
        for w in states.words():
            self.assertIn("states.py", sc["strings"].get(w, []), w)

    def test_no_page_keeps_its_own_copy_of_a_state_word(self):
        words = set(states.words())
        for f in PAGES.glob("*.js"):
            pairs = {a or b for a, b in claims.PAIR.findall(f.read_text())}
            self.assertEqual(pairs & words, set(), f.name)
        for f, old in (("trail.js", "TRAIL_TONE"), ("reconcile.js", "STATE_BADGE"), ("release.js", "LINE_STATE"), ("_shared.js", "CROP_STATE"), ("_shared.js", "const CHECK =")):
            self.assertNotIn(old, (PAGES / f).read_text(), f)

    def test_the_server_serves_the_words(self):
        from http.server import ThreadingHTTPServer
        from urllib import request
        from ledger.web import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            with request.urlopen(base + "/pages/_states.js") as r:
                self.assertEqual(r.read().decode(), states.js())
            with request.urlopen(base + "/api/v1/states") as r:
                d = json.loads(r.read())
            self.assertEqual(set(d), set(states.MACHINES))
            self.assertEqual(d["row"]["states"]["ok"]["word"], "Verified")
        finally:
            srv.shutdown()
        self.assertLess((store.ROOT / "ledger" / "web" / "app.html").read_text().index("/pages/_states.js"), (store.ROOT / "ledger" / "web" / "app.html").read_text().index("/pages/_shared.js"))


class Consumers(unittest.TestCase):
    """Every consumer asks states.py: the cards' tone, Reconcile's word, the taxonomy check, the checklist line."""

    def test_the_cards_tone_is_the_row_state(self):
        for st, by in (("checked", "xbrl"), ("checked", "located"), ("checked", "source:doc"), ("checked", "rule:ppe_categories_tie"), ("explained", "label:no_reference"),
                       ("open", "label:to_confirm"), ("open", "rule:fact_readings_differ"), ("blocked", "rule:x"), (None, "")):
            self.assertEqual(cards._how({"state": st, "by": by}, "X", {})["tone"], states.row(st, by), (st, by))

    def test_a_checked_row_never_reads_unverified(self):
        """S-1: an answer key other than XBRL, a tie or a reading (source:, actual:, esef:) used to fall through to the
        info tone, Unverified, while Proof counted the row checked."""
        for by in ("source:doc", "actual:FY2025", "esef:x", "rule:statement_tie"):
            self.assertEqual(states.group(states.row("checked", by)), "checked", by)
            self.assertNotEqual(states.word("row", cards._how({"state": "checked", "by": by}, "X", {})["tone"]), "Unverified")

    def test_blocked_and_open_and_proposed_have_three_words(self):
        """S-2: the trail said Needs review for open, blocked and an unconfirmed proposal; Reconcile said Needs review,
        Blocks release and Proposed for the same three. Both now read states.row."""
        self.assertEqual(len({states.word("row", states.row(s, by)) for s, by in (("open", ""), ("blocked", "rule:x"), ("open", "label:to_confirm"))}), 3)

    def test_the_taxonomy_check_is_the_ladder(self):
        for st in ({"state": "checked", "by": "xbrl"}, {"state": "checked", "by": "mapping:filer_tag"}, {"state": "checked", "by": "rule:ppe_categories_tie"},
                   {"state": "checked", "by": "reading:a"}, {"state": "explained", "by": "label:no_reference"}, {"state": "explained", "by": "resolution:r"},
                   {"state": "open", "by": "rule:fact_readings_differ"}, {"state": "open", "by": "label:unresolved"}):
            self.assertEqual(ties.check_columns(st)[0], states.LADDER_CHECK[states.ladder(st)], st)
        self.assertEqual(ties.check_columns({"state": "open", "by": "label:unresolved"}), ("differs", "xbrl"))
        self.assertEqual(set(states.LADDER_CHECK), set(states.LADDER.names()))  # every rung has a check word
        self.assertEqual(ties.check_columns({}), ("not_checked", "none"))

    def test_a_checklist_line_refuses_an_undeclared_state(self):
        with self.assertRaises(ValueError):
            checklist._line("x", "X", True, 0, "green", "proof")

    def test_the_edgar_freshness_is_one_reading(self):
        """The trail (cards.status_line) and the claims register (claims._edgar) read states.edgar: one threshold."""
        import tempfile
        at = datetime(2026, 11, 2, tzinfo=timezone.utc)
        for hours in (1, 47.9, 48.1, 200):
            ts = (at - timedelta(hours=hours)).isoformat()
            sec = states.edgar(ts, at)[0]
            self.assertEqual(sec, "stale" if hours > states.STALE_HOURS else "fresh", hours)
            self.assertEqual(cards.status_line(None, {"ticker": "ZZZZ", "stages": {}}, None, {"checked_at": ts}, at)["sec_check"], sec)
            with tempfile.TemporaryDirectory() as d:
                w = Path(d) / "watch.json"
                w.write_text(json.dumps({"checked_at": ts}))
                with mock.patch.object(claims, "WATCH", w):
                    self.assertEqual(bool(claims._edgar({"live": True, "now": at})), sec == "stale", hours)

    @unittest.skipUnless(store.DEFAULT_DB.exists(), "no working database")
    def test_reconcile_proposed_is_exactly_what_g6_refuses(self):
        """S-1: Reconcile's Proposed count (rows whose word is Proposed: a run's decision to confirm, an asset type no
        person confirmed) is the Release line "Decisions left to confirm"; the to-confirm rows are open, like G6 says."""
        import duckdb
        from ledger.release import checklist as cl
        from ledger.review import workbench
        from ledger.web import app
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        try:
            it = workbench.items(con, app.flow("all"))
            line = next(l for l in cl.checklist(con)["lines"] if l["id"] == "unconfirmed")
        finally:
            con.close()
        wait = [r for r in it["rows"] if r["verification"] == "wait"]
        self.assertEqual(it["by_state"].get("wait", 0), len(wait))
        self.assertEqual(len(wait), line["count"])
        self.assertTrue(all(r["open"] for r in wait))
        self.assertEqual(sum(it["by_state"].values()), len(it["rows"]))

    def test_reconcile_rows_carry_the_row_state(self):
        src = (store.ROOT / "ledger" / "review" / "workbench.py").read_text()
        self.assertIn('r["verification"] = row_state(r["state"], r["by"])', src)
        self.assertIn("stateWord('row', r.verification)", (PAGES / "reconcile.js").read_text())


if __name__ == "__main__":
    unittest.main()
