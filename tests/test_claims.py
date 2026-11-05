"""The claims register (ledger/release/claims.py, docs/BUILD.md). Each class answers one way the register itself could lie, from
the eight patterns of docs/BUILD.md: a declared status read as proven (1), nothing to check read as passed (2), one
finding closing or rewriting another (3), the doc, the API, the checklist and the packet disagreeing (4), degenerate
registers (5), a finding overwritten instead of appended (6), a claim on a page the register does not know (7), stale
inputs read as fresh (8)."""
import json
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib import request

from ledger.release import claims as C

REAL_TEST = "tests.test_claims.Compute.test_a_declared_proven_never_survives_a_fact_against_it"
RAN = {"recorded": True, "skipped": set(), "failed": set(), "at": None}


def entry(**kw):
    e = {"id": "x", "claim": "X", "where": [], "shown": [], "backed_by": {"functions": ["ledger.release.claims.load"], "tests": [REAL_TEST]},
         "status": "proven", "gaps": [], "ticket": "none", "checks": []}
    e.update(kw)
    return e


def run(e, fs=(), live=True, now=None, ran=RAN):
    return C.computed(live, now=now, entries=[e], fs=list(fs), run=ran)[0]


def finding(**kw):
    f = {"id": "F1", "source": "t", "severity": "low", "text": "t", "where": "w", "claim": "x", "ticket": "none", "status": "open", "at": "2026-11-02"}
    f.update(kw)
    return f


def phrases(r):
    return [x["phrase"] for x in r["reasons"]]


class Compute(unittest.TestCase):
    """(1) A label standing in for a check: the declared status is never the answer when a fact says worse."""

    def test_a_declared_proven_never_survives_a_fact_against_it(self):
        self.assertEqual(run(entry())["status"], "proven")  # everything backs it: proven stays
        for e, why in [(entry(backed_by={"functions": [], "tests": ["tests.test_claims.Nope.test_nope"]}), "a backing test does not exist"),
                       (entry(backed_by={"functions": ["ledger.release.claims.no_such_thing"], "tests": [REAL_TEST]}), "a backing function does not import"),
                       (entry(backed_by={"functions": ["ledger.no_such_module.f"], "tests": [REAL_TEST]}), "a backing function does not import"),
                       (entry(gaps=["one gap"]), "gaps listed")]:
            r = run(e)
            self.assertEqual(r["status"], "partial", why)
            self.assertTrue(r["worse"])
            self.assertIn(why, phrases(r))
        self.assertEqual(run(entry(), [finding()])["status"], "partial")

    def test_a_skipped_failed_or_unrecorded_backing_test_is_not_a_pass(self):
        self.assertEqual(run(entry(), ran={**RAN, "skipped": {REAL_TEST}})["status"], "partial")
        self.assertIn("a backing test was skipped", phrases(run(entry(), ran={**RAN, "skipped": {REAL_TEST}})))
        self.assertEqual(run(entry(), ran={**RAN, "failed": {REAL_TEST}})["status"], "stub")
        self.assertEqual(run(entry(), ran={**RAN, "recorded": False})["status"], "partial")
        with tempfile.TemporaryDirectory() as d:  # an old report without skipped_ids cannot tell a skip from a pass
            p = Path(d) / "tests.json"
            p.write_text(json.dumps({"ok": True, "failures": [f"{REAL_TEST}: AssertionError"], "skipped": 2}))
            t = C.test_run(p)
            self.assertEqual((t["recorded"], t["failed"]), (False, {REAL_TEST}))
            self.assertFalse(C.test_run(Path(d) / "none.json")["recorded"])

    def test_a_module_that_raises_at_import_is_a_reason_not_a_crash(self):
        with mock.patch("importlib.import_module", side_effect=RuntimeError("boom")):
            why = C.function_imports("ledger.release.claims.load")
        self.assertIn("raises at import", why)
        self.assertIsNone(C.function_imports("ledger.release.claims.load"))

    def test_without_checks_the_declaration_is_a_ceiling_and_with_checks_the_facts_decide(self):
        for s in ("partial", "stale", "stub", "planned"):
            self.assertEqual(run(entry(status=s))["status"], s)
        with mock.patch.dict(C.CHECKS, {"gold": lambda ctx: []}):
            r = run(entry(status="stale", checks=["gold"]))
        self.assertEqual((r["status"], r["better"]), ("proven", True))  # a declared stale is not a permanent floor
        with mock.patch.dict(C.CHECKS, {"gold": lambda ctx: [("stub", "no gold verdicts", "0 of 4")]}):
            r = run(entry(status="proven", checks=["gold"]))
        self.assertEqual((r["status"], r["facts"]), ("stub", ["0 of 4"]))  # the gap text is the fact, not a typed line

    def test_a_check_that_cannot_run_is_stale_not_a_pass(self):
        with mock.patch.dict(C.CHECKS, {"gold": mock.Mock(side_effect=RuntimeError("boom"))}):
            r = run(entry(checks=["gold"]))
        self.assertEqual(r["status"], "stale")
        self.assertIn("check gold could not run", phrases(r))

    def test_the_real_register_backs_what_it_names(self):
        """A typo in backed_by fails the suite, not only the claim: every test exists, every function imports."""
        for r in C.computed():
            bad = [x for x in r["reasons"] if x["phrase"] in ("a backing test does not exist", "a backing function does not import")]
            self.assertEqual(bad, [], r["id"])

    def test_the_real_register_today(self):
        rows = {r["id"]: r for r in C.computed(live=False)}
        from ledger.review import gold
        items = [i for d in gold.load_checked()[0].values() for i in d["items"]]
        given = sum(gold.has_verdict(i) for i in items)  # Kenny gives verdicts over time: stub at 0, partial until all 120
        self.assertIn(rows["gold_error_rate"]["status"], ("stale", "stub"))  # the golden report is read live only, and tested rows never read above their declaration (stub) in the static view
        live = {r["id"]: r for r in C.computed(live=True)}
        self.assertNotEqual(live["gold_error_rate"]["status"], "proven" if given < len(items) else None)
        if not given:
            self.assertEqual(live["gold_error_rate"]["status"], "stub")
        self.assertEqual(rows["hosted_copy"]["status"], "stale")     # no deploy record
        self.assertEqual(rows["edgar_checked"]["status"], "stale")   # freshness is checked live only
        self.assertNotEqual(rows["golden_equal"]["status"], "proven")  # gold unverified is never a golden pass


class Vacuous(unittest.TestCase):
    """(2) Nothing to check never reads as passed."""

    def test_no_test_is_never_proven_but_planned_is_left_planned(self):
        self.assertEqual(run(entry(backed_by={"functions": [], "tests": []}))["status"], "partial")
        r = run(entry(status="planned", backed_by={"functions": [], "tests": []}))
        self.assertEqual((r["status"], r["reasons"]), ("planned", []))

    def test_an_empty_or_missing_gold_folder_is_a_stub(self):
        with tempfile.TemporaryDirectory() as d:
            for root in (Path(d), Path(d) / "missing"):
                with mock.patch("ledger.review.gold.GOLD", root):
                    self.assertEqual(run(entry(checks=["gold"]))["status"], "stub")

    def test_gold_with_some_verdicts_is_partial_and_all_is_no_cap(self):
        docs = {"MSFT": {"items": [{"verdict": "right"}, {"verdict": None}]}}
        with mock.patch("ledger.review.gold.load_checked", return_value=(docs, [])):
            self.assertEqual(run(entry(checks=["gold"]))["status"], "partial")
        docs["MSFT"]["items"][1]["verdict"] = "wrong"
        with mock.patch("ledger.review.gold.load_checked", return_value=(docs, [])):
            self.assertEqual(run(entry(checks=["gold"]))["status"], "proven")

    def test_test_exists_reads_the_source_or_the_deploy_record(self):
        self.assertTrue(C.test_exists(REAL_TEST))
        for t in ("tests.test_claims.Compute.nope", "tests.nope.A.b", "test_claims.Compute", "ledger.x.Y.z"):
            self.assertFalse(C.test_exists(t), t)
        with tempfile.TemporaryDirectory() as d:  # the hosted copy: no tests/, the record answers, an unrecorded id is absent
            h = Path(d) / "hosted.json"
            h.write_text(json.dumps({"tests": {REAL_TEST: True, "tests.a.B.c": False}}))
            with mock.patch.object(C, "HOSTED", h):
                none = Path(d) / "no-tests"
                self.assertTrue(C.test_exists(REAL_TEST, none))
                self.assertFalse(C.test_exists("tests.a.B.c", none))
                self.assertFalse(C.test_exists("tests.test_claims.Compute.other", none))

    def test_a_scan_of_nothing_fails(self):
        with tempfile.TemporaryDirectory() as d:
            probs = C.unregistered(entries=[], pages=Path(d), py=Path(d), html=Path(d) / "none.html")
        self.assertEqual(probs[0]["kind"], "nothing_scanned")

    def test_the_scan_finds_the_label_maps_on_the_real_pages(self):
        sc = C.scan()
        self.assertGreaterEqual(sc["pages"], 9)
        for w in ("Verified", "Corroborated", "Unverified", "Needs review", "Pass", "Fail", "Not run", "Proposed", "SEC never checked",
                  "Not in scope", "Statements located", "Decision on file", "Cell located", "No crop", "Does not tie to reported total", "Readings differ across filings"):
            self.assertIn(w, sc["strings"])


class OneFindingOneItem(unittest.TestCase):
    """(3) A finding's state changes by its own id only, and a later line changes nothing but its status and time."""

    def write(self, d, *lines):
        p = Path(d) / "f.jsonl"
        p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
        return p

    def test_latest_line_per_id_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as d:
            fs = C.findings(self.write(d, finding(id="F1"), finding(id="F2"), finding(id="F1", status="fixed", at="2026-11-03")), ids={"x"})
        self.assertEqual({f["id"]: f["status"] for f in fs}, {"F1": "fixed", "F2": "open"})
        self.assertEqual(run(entry(), fs)["open_findings"], ["F2"])

    def test_a_later_line_may_change_only_status_and_at(self):
        with tempfile.TemporaryDirectory() as d:
            for change in ({"text": "softer words"}, {"severity": "high"}, {"claim": "y"}, {"ticket": "T1"}, {"where": "elsewhere"}):
                with self.assertRaises(ValueError, msg=str(change)):
                    C.findings(self.write(d, finding(), finding(**{**change, "status": "fixed"})), ids={"x", "y"})

    def test_an_id_is_taken_once_and_a_close_needs_an_earlier_open(self):
        """Merge friction: findings.jsonl merges by union, so two branches that pick one id must fail here, not land."""
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):  # the same id opened twice (two branches, same words)
                C.findings(self.write(d, finding(id="F-AB1"), finding(id="F-AB1")), ids={"x"})
            for closed in ("fixed", "wontfix"):  # a close with no open line before it
                with self.assertRaises(ValueError):
                    C.findings(self.write(d, finding(id="F-AB2", status=closed)), ids={"x"})
            for bad in ("F31", "F-1", "X-1", "f-ab1"):  # a new plain F<n> past the legacy ones, or a malformed id
                with self.assertRaises(ValueError, msg=bad):
                    C.findings(self.write(d, finding(id=bad)), ids={"x"})
            fs = C.findings(self.write(d, finding(id="F-AB3"), finding(id="F-AB3", status="fixed"), finding(id="F-AB3", status="open"), finding(id="S-1")), ids={"x"})
            self.assertEqual({f["id"]: f["status"] for f in fs}, {"F-AB3": "open", "S-1": "open"})  # reopen after a fix is allowed

    def test_the_real_log_has_unique_ids_by_first_appearance(self):
        seen = set()
        for n, line in enumerate(C.FINDINGS.read_text().splitlines(), 1):
            if not line.strip():
                continue
            f = json.loads(line)
            if f["id"] not in seen:
                self.assertEqual(f["status"], "open", f"line {n}: {f['id']} first appears {f['status']}")
                seen.add(f["id"])
        C.findings(ids={e["id"] for e in C.load()})  # the loader's own rules hold on the committed log

    def test_a_finding_on_an_unknown_claim_or_with_a_bad_field_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in (finding(claim="nope"), finding(severity="urgent"), finding(status="done"), {"id": "F9"}, finding(ticket="soon"), ["a list"]):
                with self.assertRaises(ValueError):
                    C.findings(self.write(d, bad), ids={"x"})
            (Path(d) / "f.jsonl").write_text("{not json\n")
            with self.assertRaises(ValueError):
                C.findings(Path(d) / "f.jsonl")


class OneAnswer(unittest.TestCase):
    """(4) The Gaps page (API), the Release checklist and the packet read the same computation; the packet never
    depends on the clock or the commit."""

    def test_api_checklist_and_counts_agree(self):
        from ledger.web import app
        from ledger.release import checklist
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        with request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/api/v1/claims") as r:
            d = json.loads(r.read())
        self.assertEqual(len(d["claims"]), len(C.load()))
        self.assertEqual(d["counts"], C.counts(C.computed(), C.findings()))
        self.assertEqual(d["problems"], [])
        self.assertGreater(d["scanned"]["strings"], 80)
        reg, _doc, gaps = checklist.claims_lines()
        self.assertEqual((reg["id"], reg["required"], reg["state"]), ("claims", True, "pass"))
        self.assertIn(f"{d['scanned']['strings']} strings", reg["note"])
        self.assertEqual(gaps["count"], d["counts"]["stub"] + d["counts"]["stale"] + d["counts"]["open_findings"])
        self.assertFalse(gaps["required"])
        self.assertEqual([r["status"] for r in d["claims"]], sorted((r["status"] for r in d["claims"]), key=lambda s: C.PAGE_ORDER[s]))

    def test_the_packet_lists_the_stub_and_stale_claims(self):
        from ledger.release.limitations import markdown
        md = markdown("v9.9.9", {})
        self.assertIn("## Claims not yet proven", md)
        for r in C.computed(live=False):
            if r["status"] in ("stub", "stale"):
                self.assertIn(r["claim"].replace("|", "\\|"), md)

    def test_the_packet_hash_ignores_the_clock_and_head(self):
        from ledger.release.limitations import markdown
        from ledger.release.release import content_hash
        hashes = set()
        for when, head in ((datetime(2026, 11, 2, tzinfo=timezone.utc), "aaaaaaa"), (datetime(2027, 3, 1, tzinfo=timezone.utc), "bbbbbbb")):
            with mock.patch.object(C, "_now", return_value=when), mock.patch.object(C, "_head", return_value=head):
                hashes.add(content_hash({"LIMITATIONS.md": markdown("v9.9.9", {})}))
        self.assertEqual(len(hashes), 1)

    def test_a_red_scan_or_a_crash_turns_the_required_line_red(self):
        from ledger.release import checklist
        with mock.patch.object(C, "unregistered", return_value=[{"kind": "unregistered", "what": "'Proven'", "where": "ledger/web/pages/x.js"}]):
            reg = checklist.claims_lines()[0]
        self.assertEqual((reg["state"], reg["count"]), ("fail", 1))
        for err in (ValueError("bad register"), RuntimeError("a module raised")):
            with mock.patch.object(C, "load", side_effect=err):
                [reg] = checklist.claims_lines()
            self.assertEqual(reg["state"], "fail")
        with mock.patch.object(C, "computed", side_effect=RuntimeError("boom")):
            self.assertIn("could not be read", "\n".join(C.packet_section()))


class Degenerate(unittest.TestCase):
    """(5) An empty register, a repeated id, an unknown status or check, checks on a planned row, a built row with
    nothing to look for."""

    def test_an_empty_register_fails_the_scan(self):
        self.assertTrue(C.unregistered(entries=[]))

    def test_load_refuses_bad_entries(self):
        import yaml
        good = {k: v for k, v in entry().items() if k != "checks"}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.yaml"
            for bad in ([good, good], [{**good, "status": "done"}], [{**good, "checks": ["vibes"]}], [{**good, "ticket": "soon"}],
                        [{k: v for k, v in good.items() if k != "gaps"}], [{**good, "backed_by": ["x"]}], {"x": good},
                        [{**good, "status": "planned", "checks": ["gold"]}]):
                p.write_text(yaml.safe_dump(bad))
                with self.assertRaises(ValueError, msg=str(bad)[:80]):
                    C.load(p)

    def test_a_built_row_with_nothing_shown_fails(self):
        probs = C.unregistered(entries=[entry(shown=[])], pages=Path(tempfile.gettempdir()) / "none")
        self.assertIn("no_marker", [p["kind"] for p in probs])
        probs = C.unregistered(entries=[entry(status="planned", shown=[])], pages=Path(tempfile.gettempdir()) / "none")
        self.assertNotIn("no_marker", [p["kind"] for p in probs])


class AppendOnly(unittest.TestCase):
    """(6) claims/findings.jsonl only grows: every committed version is a prefix of the working one."""

    def test_every_committed_version_is_a_prefix(self):
        a = C.append_only()
        if not a["enforced"]:
            self.skipTest(a["note"])
        self.assertEqual(a["problems"], [])

    def test_an_edited_line_in_any_earlier_commit_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            git = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, check=True)
            try:
                git("init", "-q")
            except (OSError, subprocess.CalledProcessError):
                self.skipTest("no git")
            git("config", "user.email", "t@t")
            git("config", "user.name", "t")
            f = repo / "f.jsonl"
            f.write_text('{"id":"F1"}\n')
            git("add", "f.jsonl")
            git("commit", "-qm", "one")
            f.write_text('{"id":"F1"}\n{"id":"F2"}\n')
            git("commit", "-qam", "two")
            f.write_text('{"id":"F1"}\n{"id":"F2"}\n{"id":"F3"}\n')
            ok = C.append_only(f, "f.jsonl", repo)
            self.assertEqual((ok["enforced"], ok["commits"], ok["problems"]), (True, 2, []))
            f.write_text('{"id":"F1","text":"rewritten"}\n{"id":"F2"}\n')
            self.assertEqual(len(C.append_only(f, "f.jsonl", repo)["problems"]), 2)

    def test_a_merged_branch_is_checked_on_main_only(self):
        """Two branches append in parallel; main's history (first parent) stays a prefix, an edit on main is still caught."""
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            git = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, check=True)
            try:
                git("init", "-q", "-b", "main")
            except (OSError, subprocess.CalledProcessError):
                self.skipTest("no git")
            git("config", "user.email", "t@t")
            git("config", "user.name", "t")
            f = repo / "f.jsonl"
            f.write_text('{"id":"F1"}\n')
            git("add", "f.jsonl")
            git("commit", "-qm", "one")
            git("checkout", "-qb", "side")
            f.write_text('{"id":"F1"}\n{"id":"S1"}\n')
            git("commit", "-qam", "side")
            git("checkout", "-q", "main")
            f.write_text('{"id":"F1"}\n{"id":"M1"}\n')
            git("commit", "-qam", "main")
            subprocess.run(["git", "merge", "-q", "side"], cwd=repo, capture_output=True, text=True)
            f.write_text('{"id":"F1"}\n{"id":"M1"}\n{"id":"S1"}\n')
            git("commit", "-qam", "merge")
            self.assertEqual(C.append_only(f, "f.jsonl", repo)["problems"], [])
            f.write_text('{"id":"F1"}\n{"id":"S1"}\n')
            self.assertEqual(len(C.append_only(f, "f.jsonl", repo)["problems"]), 2)

    def test_interleaved_new_lines_pass_and_an_edit_fails(self):
        self.assertTrue(C._kept_in_order(["a", "b", "c"], ["a", "b", "x", "c", "y"]))
        self.assertFalse(C._kept_in_order(["a", "b", "c"], ["a", "c", "b"]))
        self.assertFalse(C._kept_in_order(["a", "b"], ["a", "b2"]))

    def test_without_git_it_says_not_enforced(self):
        with mock.patch.object(C, "_git", return_value=None):
            a = C.append_only()
        self.assertEqual((a["enforced"], a["note"]), (False, "append-only not enforced here: no git"))


class Scan(unittest.TestCase):
    """(7) Wording: every claim string a page or its Python shows has a row, and every row's words are where it says."""

    def test_every_scanned_string_has_a_row(self):
        self.assertEqual(C.unregistered(), [])

    def test_a_new_tone_word_map_entry_card_or_cause_without_a_row_fails(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "trail.js").write_text("const TRAIL_TONE = {ok: ['text-green', 'Certified']};\nh('span', {class: 'badge bg-green-lt'}, `${n} audited`);")
            (d / "release.js").write_text("const LINE_STATE = {pass: ['blessed', 'bg-green-lt']};")
            (d / "cards.py").write_text('    if x:\n        return {"tone": "ok", "text": f"Audited by KPMG: {x}"}\n')
            (d / "workbench.py").write_text('CAUSES = {"a": "Proven by magic"}\n')
            got = {p["what"] for p in C.unregistered(entries=[], pages=d, py=d, html=d / "none.html")}
        self.assertTrue({"Certified", "audited", "blessed", "Audited by KPMG", "Proven by magic"} <= got, got)

    def test_the_gaps_page_own_chips_are_not_claims_but_its_other_words_are(self):
        found = C.strings_in("gaps.js", "const CLAIM_ORDER = {}; h('span', {class: 'badge bg-red-lt'}, 'stub'); h('span', {class: 'text-green'}, 'All clear')")
        self.assertEqual(found, {"All clear"})

    def test_a_row_whose_words_left_the_page_fails(self):
        none = Path(tempfile.gettempdir()) / "none"
        probs = C.unregistered(entries=[entry(where=["ledger/web/pages/trail.js"], shown=["Audited by KPMG"])], pages=none)
        self.assertIn({"kind": "not_shown", "what": "Audited by KPMG", "where": "x"}, probs)
        probs = C.unregistered(entries=[entry(where=["ledger/web/pages/nope.js"], shown=["x"])], pages=none)
        self.assertIn("missing_file", [p["kind"] for p in probs])


class Stale(unittest.TestCase):
    """(8) An old input never reads as fresh."""

    def test_edgar_older_than_48_hours_missing_naive_or_future_is_stale(self):
        now = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as d:
            w = Path(d) / "watch.json"
            e = entry(checks=["edgar_watch"])
            with mock.patch.object(C, "WATCH", w):
                self.assertEqual(run(e, now=now)["status"], "stale")  # missing
                for ts, want in (((now - timedelta(hours=49)).isoformat(), "stale"), ((now - timedelta(hours=47)).isoformat(), "proven"),
                                 ("2026-11-02T11:00:00", "stale"), ((now + timedelta(days=2)).isoformat(), "stale"), ("soon", "stale")):
                    w.write_text(json.dumps({"checked_at": ts}))
                    self.assertEqual(run(e, now=now)["status"], want, ts)
                w.write_text(json.dumps({"checked_at": (now - timedelta(hours=1)).isoformat()}))
                r = run(e, live=False)
                self.assertEqual(r["status"], "stale")  # the static doc and the packet cannot know: checked live only
                self.assertIn("EDGAR freshness checked live only", phrases(r))

    def test_hosted_copy_unknown_older_release_or_other_commit_is_stale(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d) / "hosted.json"
            e = entry(checks=["hosted_copy"])
            with mock.patch.object(C, "HOSTED", h), mock.patch.object(C, "latest_signed", return_value="v1.9.0"), \
                    mock.patch.object(C, "_head", return_value="abc1234"):
                r = run(e)
                self.assertEqual(r["status"], "stale")  # not recorded: unknown, never proven
                self.assertIn("unknown", r["facts"][0])
                h.write_text(json.dumps({"release": "v1.8.0", "commit": "abc1234"}))
                r = run(e)
                self.assertEqual(r["status"], "stale")
                self.assertIn("Hosted copy serves v1.8.0; latest signed release is v1.9.0", r["facts"])  # the gap text is generated
                h.write_text(json.dumps({"release": "v1.9.0", "commit": "0000000"}))
                with mock.patch("ledger.release.testreport.changed_since", return_value=["ledger/web/app.py", "claims/hosted.json"]):
                    self.assertEqual(run(e)["status"], "stale")
                with mock.patch("ledger.release.testreport.changed_since", return_value=["claims/hosted.json"]):  # the commit that recorded the deploy
                    self.assertEqual(run(e)["status"], "proven")
                h.write_text(json.dumps({"release": "v1.9.0", "commit": "abc1234"}))
                self.assertEqual(run(e)["status"], "proven")
                self.assertEqual(run(e, live=False)["status"], "stale")  # the code it runs is a live question

    def test_record_deploy_refuses_a_dirty_tree_or_no_git(self):
        for state in (("abc1234", True), (None, None)):
            with mock.patch("ledger.release.testreport.git_state", return_value=state), mock.patch.object(C, "HOSTED", Path(tempfile.gettempdir()) / "never.json"):
                with self.assertRaises(ValueError):
                    C.record_deploy()

    def test_golden_missing_is_stale_differing_a_stub_and_gold_unverified_partial(self):
        with tempfile.TemporaryDirectory() as d:
            g = Path(d) / "golden.json"
            e = entry(checks=["golden_report"])
            with mock.patch.object(C, "GOLDEN_REPORT", g):
                self.assertEqual(run(e)["status"], "stale")
                g.write_text(json.dumps({"ok": False, "tables_ok": False, "gold": {"state": "pass"}}))
                self.assertEqual(run(e)["status"], "stub")
                g.write_text(json.dumps({"ok": False, "tables_ok": True, "gold": {"state": "unverified", "unverified": 120, "items": 120}}))
                r = run(e)
                self.assertEqual(r["status"], "partial")
                self.assertIn("Hand check unverified: 120 of 120 items have no verdict", r["facts"])
                g.write_text(json.dumps({"ok": False, "tables_ok": True, "gold": {"state": "fail", "failures": ["x"]}}))
                self.assertEqual(run(e)["status"], "stub")
                g.write_text(json.dumps({"ok": True, "tables_ok": True, "gold": {"state": "pass"}}))
                self.assertEqual(run(e)["status"], "proven")


class Doc(unittest.TestCase):
    def test_a_stale_or_union_merged_claims_doc_blocks_signing(self):
        """docs/CLAIMS.md merges by union: a merged copy with duplicate rows, or a missing one, is a red required line."""
        from ledger.release import checklist
        with tempfile.TemporaryDirectory() as d:
            doc = Path(d) / "CLAIMS.md"
            doc.write_text("# x\n| a |\n")
            self.assertEqual(checklist.doc_line(doc, "# x\n| a |\n")["state"], "pass")
            doc.write_text("# x\n| a |\n| a |\n")  # what a union merge leaves
            l = checklist.doc_line(doc, "# x\n| a |\n")
            self.assertEqual((l["state"], l["required"], l["ok"]), ("fail", True, False))
            self.assertEqual(checklist.doc_line(Path(d) / "none.md", "x")["state"], "fail")
        self.assertEqual(checklist.doc_line()["state"], "pass")  # the committed file is current

    def test_the_static_doc_reads_no_test_run_and_no_golden_report(self):
        """Plumbing bug B: docs/CLAIMS.md depended on reports/tests.json and reports/golden.json, which every `ledger test`
        rewrites, so each run left it stale and "Claims doc current" red. Two runs that disagree on every fact the doc
        could read (skips, failures, golden tables, gold state) give the same doc; the live view still reads them."""
        with tempfile.TemporaryDirectory() as d:
            t, g = Path(d) / "tests.json", Path(d) / "golden.json"
            docs, live = [], []
            for run_, gold_ in (({"ok": True, "failures": [], "skipped_ids": [], "at": "2026-11-03T01:00:00"}, {"ok": True, "tables_ok": True, "gold": {"state": "pass"}, "at": "a"}),
                                ({"ok": False, "failures": [f"{REAL_TEST}: boom"], "skipped_ids": [REAL_TEST], "at": "2026-11-03T02:00:00"}, {"ok": False, "tables_ok": False, "gold": {"state": "fail", "failures": ["x"]}, "at": "b"}),
                                (None, None)):
                for p_, body in ((t, run_), (g, gold_)):
                    p_.unlink(missing_ok=True)
                    if body is not None:
                        p_.write_text(json.dumps(body))
                with mock.patch.object(C, "TEST_REPORT", t), mock.patch.object(C, "GOLDEN_REPORT", g):
                    docs.append(C.markdown())
                    live.append({r["id"]: r["status"] for r in C.computed(True)})
            self.assertEqual(docs[0], docs[1])
            self.assertEqual(docs[1], docs[2])
            self.assertIn("see the Release page", docs[0])
            self.assertNotEqual(live[0], live[1])  # the live register still reads the run and the golden report

    def test_a_failing_backing_test_never_makes_the_doc_read_proven_or_above_its_declaration(self):
        """Review HIGH: the static view skips the last run, so it must cap the row instead: a row backed by tests never
        reads proven there and never better than declared, and its Computed cell says the tests are read live."""
        failing = {**RAN, "failed": {REAL_TEST}}
        with mock.patch.dict(C.CHECKS, {"gold": lambda ctx: []}):
            for declared in ("partial", "proven", "stub", "stale"):
                e = entry(status=declared, checks=["gold"])
                live, static = run(e, ran=failing), run(e, live=False, ran=failing)
                self.assertEqual(live["status"], "stub")
                self.assertNotEqual(static["status"], "proven", declared)
                self.assertGreaterEqual(C.RANK[static["status"]], C.RANK[declared], declared)
                self.assertTrue(static["tests_live"])
            with mock.patch.object(C, "load", return_value=[entry(status="partial", checks=["gold"])]), mock.patch.object(C, "findings", return_value=[]), \
                    mock.patch.object(C, "test_run", return_value=failing):
                doc = C.markdown()
        self.assertIn(f"| **partial** · {C.TESTS_LIVE} |", doc)
        self.assertNotIn("**proven**", doc)

    def test_claims_md_is_current(self):
        self.assertEqual(C.DOC.read_text(), C.markdown(), "docs/CLAIMS.md is stale: run uv run python -m ledger claims")


if __name__ == "__main__":
    unittest.main()
