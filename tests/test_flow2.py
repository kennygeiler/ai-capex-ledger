"""The second flow batch (docs/ux-flow/report.md #6, #8, #10-#14; docs/ux-flow/verification-2.md): rule findings in
groups with a deliberate Save, the packet on Release, Proof with one job, the condensed trail, Docs from Start here, one
Verification filter on the Dataset, and the read-only copy's scope line."""
import json
import shutil
import unittest
from pathlib import Path

from tests.test_pages_js import PAGES, block, line, node


def _run(js: str, arg):
    return json.loads(node(js + "\nconst A = JSON.parse(process.argv[process.argv.length - 1]);\n", json.dumps(arg)) or "null")


def _call(prelude: str, expr: str, arg):
    return json.loads(node(prelude + "\nconst A = JSON.parse(process.argv[process.argv.length - 1]);\nprocess.stdout.write(JSON.stringify(" + expr + "));", json.dumps(arg)))


@unittest.skipUnless(shutil.which("node"), "no node")
class RuleFindingGroups(unittest.TestCase):
    """#6: rule findings grouped by company + field + check; no decision preselected; a prefilled reason for readings that
    differ where the dataset uses the newest filing; Fix says the item stays open; an "N left · Release" link."""

    PRE = "\n".join(line("reconcile.js", p) for p in ("const ruleGroupKey", "const ruleOrder", "const ruleGroups"))

    def test_rows_group_by_company_field_and_check(self):
        R = lambda t, f, c, p: {"cause": "finding_unconfirmed", "ticker": t, "field": f, "cause_label": c, "period": p}
        rows = [R("GOOGL", "segment_revenue", "Does not tie", "FY2024"), R("APLD", "segment_capex", "Does not tie", "FY2023"),
                R("GOOGL", "segment_revenue", "Does not tie", "FY2025"), R("APLD", "ppe_category", "Readings differ", "FY2024"),
                R("APLD", "segment_capex", "Does not tie", "FY2026")]
        got = _call(self.PRE, "ruleGroups([...A].sort(ruleOrder)).map((g) => [g.key, g.rows.map((r) => r.period)])", rows)
        self.assertEqual(got, [["APLD|ppe_category|Readings differ", ["FY2024"]], ["APLD|segment_capex|Does not tie", ["FY2026", "FY2023"]],
                               ["GOOGL|segment_revenue|Does not tie", ["FY2025", "FY2024"]]])
        self.assertIsNone(_call(self.PRE, "ruleGroupKey(A)", {"cause": "fact_differs", "ticker": "X"}))  # only rule findings group

    def test_a_decision_starts_unchosen_and_save_waits_for_one(self):
        st = lambda r: _call(line("reconcile.js", "const startState"), "startState(A)", r)
        self.assertIsNone(st(None))
        self.assertIsNone(st({"key": "k"}))  # before: 'accept'
        self.assertEqual(st({"resolution": {"state": "explain"}}), "explain")  # a saved row reopens on its own decision
        page = (PAGES / "reconcile.js").read_text()
        self.assertIn("let state = startState(r);", page)
        self.assertIn("disabled: !state, title: state ? null : 'Choose a decision first'", page)
        self.assertIn("finally { save.disabled = !state; }", page)

    def test_fix_says_the_item_stays_open(self):
        eff = _call(line("reconcile.js", "const RES_EFFECT"), "A.map((s) => RES_EFFECT[s])", ["fix", "accept"])
        self.assertEqual(eff, ["Item stays open until the next run", "Closes the item"])
        self.assertIn("effect.textContent = RES_EFFECT[s]", (PAGES / "reconcile.js").read_text())

    def test_readings_differ_prefills_the_reason_when_the_newest_reading_is_used(self):
        pre = line("reconcile.js", "const laterReading") + "\n" + line("reconcile.js", "const prefillReason")
        f = lambda eid, filed: {"extraction_id": eid, "form": "10-K", "filed": filed}
        rs = lambda used: {"cause": "finding_unconfirmed", "evidence": {"restatement": {"used": used, "steps": [{"filings": [f("a", "2024-08-30")]}, {"filings": [f("b", "2025-07-30")]}]}}}
        self.assertEqual(_call(pre, "prefillReason(A)", [rs(f("b", "2025-07-30"))]), "Later filing’s reading used · 10-K 2025-07-30")
        self.assertEqual(_call(pre, "prefillReason(A)", [rs(f("b", "2025-07-30")), rs(f("b", "2025-07-30"))]), "Later filing’s reading used")
        self.assertEqual(_call(pre, "prefillReason(A)", [rs(f("a", "2024-08-30"))]), "")  # the dataset uses the older reading: nothing to prefill
        self.assertEqual(_call(pre, "prefillReason(A)", [rs(f("b", "2025-07-30")), {"cause": "finding_unconfirmed", "evidence": {}}]), "")  # a mixed batch
        self.assertEqual(_call(pre, "prefillReason(A)", [{"cause": "fact_differs", "evidence": rs(f("b", "x"))["evidence"]}]), "")

    def test_the_way_back_to_release(self):
        page = (PAGES / "reconcile.js").read_text()
        self.assertIn("`${int(openRows.length)} left · Release`", page)
        self.assertIn("status.replaceChildren(`Saved · ${int(left)} left · `, h('a', {href: '#release'}, 'Release'))", page)
        self.assertIn("tbody.append(ruleGroupRow(groupOf.get(r)))", page)
        self.assertIn("const cb = keys.length ? writes(h('input'", page)  # the group tick is a write control: hidden on the read-only copy


@unittest.skipUnless(shutil.which("node"), "no node")
class PacketOnRelease(unittest.TestCase):
    """#8: after a signature the page stays on Release with the packet's download; the releases table lives on Release
    with one primary, the newest signed; packet file names link to their Dataset list. No test signs a real release."""

    def test_after_a_signature_the_download_not_a_redirect(self):
        pre = line("release.js", "const packetHref") + "\n" + line("release.js", "const signedNext")
        self.assertEqual(_call(pre, "signedNext(A)", {"version": "v9.9.9-test", "published": True}), {"href": "/packet/v9.9.9-test.zip", "label": "Download v9.9.9-test"})
        self.assertIsNone(_call(pre, "signedNext(A)", {"version": "v9.9.9-test", "published": False}))  # a failed publish offers no download
        page = (PAGES / "release.js").read_text()
        self.assertNotIn("go('proof')", page)  # before: setTimeout(() => go('proof'), 2500)
        self.assertIn("const next = signedNext(r);", page)

    def test_one_latest_signed_release(self):
        rel = lambda v, by, packet=True: {"version": v, "signed_by": by, "packet": packet}
        pick = lambda rels: _call(line("release.js", "const latestSigned"), "(latestSigned(A) || {}).version || null", rels)
        self.assertEqual(pick([rel("v1.7.0", "K"), rel("v1.8.0", "K"), rel("v1.9.0", None, False)]), "v1.8.0")  # an unsigned next version is not it
        self.assertIsNone(pick([rel("v1.9.0", None, False)]))
        page = (PAGES / "release.js").read_text()
        self.assertIn("r === latest ? h('a', {href: packetHref(r.version), class: 'btn btn-sm btn-outline-primary'}", page)
        self.assertIn("view.append(head, lines, releases);", page)

    def test_packet_files_link_to_their_dataset_list(self):
        from ledger.release.checklist import packet_detail
        got = {r["file"]: r.get("link") for r in packet_detail({"values.csv": "h\na\n", "ai_spend.csv": "h\n", "README.md": "x", "taxonomy.csv": "h\n"})}
        self.assertEqual(got, {"README.md": None, "ai_spend.csv": None, "taxonomy.csv": "data?list=taxonomy", "values.csv": "data?list=values"})


class ProofOneJob(unittest.TestCase):
    """#11: Proof is the stage board, what is open and the hand check. Failure types on Rules, releases on Release, one
    regression line (the header's)."""

    def test_proof_draws_no_failure_types_releases_or_second_regression_line(self):
        page = (PAGES / "proof.js").read_text()
        for gone in ("failureTypes", "/api/outputs", "dtable('Releases'", "'Regression test'"):
            self.assertNotIn(gone, page)
        self.assertIn("view.append(head, table_, goldSet(), keyTable);", page)
        self.assertIn("h('details', {class: 'fold mt-3'}, h('summary', {}, h('span', {class: 'fw-semibold'}, 'Verification source')", page)  # folded (DI6)

    def test_rules_draws_the_failure_types(self):
        page = (PAGES / "rules.js").read_text()
        self.assertIn("function failureTypes()", page)
        self.assertIn("...open, types);", page)  # folded under the work list, drawn on first open
        self.assertIn("if (types.open && !types.dataset.drawn) { types.dataset.drawn = '1'; failureTypes.draw(); }", page)


@unittest.skipUnless(shutil.which("node"), "no node")
class TrailCondensed(unittest.TestCase):
    """#10 (STORY-014): a check flag folds into its figure's row; identical rows with nothing to tell apart are one row
    with a count; a stage with nothing open folds; one Decide in Reconcile link per stage; Back keeps the scroll."""

    PRE = "\n".join(line("trail.js", p) for p in ("const ORDER", "const trailOrder", "const flagKey")) + "\n" + block("trail.js", "function foldFlags(", "\n}") + "\n" + block("trail.js", "function groupSame(", "\n}")

    def test_a_check_flag_folds_into_its_figure(self):
        fig = lambda f, p, st="checked": {"what": f"{f} {p}", "state": st, "ref": {"field": f, "period": p}}
        flag = lambda rule, f, p, st="checked": {"what": f"{rule}: {f} {p}", "state": st, "ref": {"field": f, "period": p}, "show": {"rule": rule}, "card": {"how": {"tone": "info"}}}
        items = [fig("opex", "FY2026", "explained"), fig("capex", "FY2025"), flag("jump", "opex", "FY2026", "explained"), flag("jump", "capex", "FY2025", "open"), flag("row_label_switch", "revenue", "FY2022")]
        got = _call(self.PRE, "foldFlags(A).map((i) => [i.what, (i.flags || []).map((f) => f.rule), trailOrder(i)])", items)
        self.assertEqual(got, [["opex FY2026", ["jump"], 1], ["capex FY2025", ["jump"], 0],  # an open flag makes its figure open
                               ["row_label_switch: revenue FY2022", [], 2]])  # no figure row of its own: stays a row

    def test_identical_empty_rows_are_one_row_with_a_count(self):
        empty = lambda p: {"what": p, "state": "explained", "card": {"how": {"tone": "info", "text": "Part-year amount"}, "where": []}}
        quoted = {"what": "FY2025", "state": "checked", "card": {"found": "“quote”", "how": {"tone": "ok"}, "where": [{}]}}
        items = [empty("FY2025")] * 7 + [quoted, quoted, empty("FY2026")]
        got = _call(self.PRE, "groupSame(A, (i) => i.what).map((i) => [i.what, i.count])", items)
        self.assertEqual(got, [["FY2025", 7], ["FY2025", 1], ["FY2025", 1], ["FY2026", 1]])  # rows with a value or source are never merged

    def test_one_link_per_stage_and_complete_stages_fold(self):
        page = (PAGES / "trail.js").read_text()
        self.assertEqual(page.count("'Decide in Reconcile →'"), 1)  # in the stage header, not on every mapping card
        self.assertNotIn("mappingDecision(", page)  # a mapping is one row on the trail; the card is Reconcile's
        self.assertIn("if (rest.length) body.push(h('details', {class: 'px-3 py-2'}", page)  # before: shown open when 12 or fewer
        self.assertIn("waitingTotal ? '' : h('a', {href: `#reconcile?scope=${c.ticker}`", page)  # one Reconcile link in the head area

    def test_back_returns_to_the_scroll_it_left(self):
        js = line("_router.js", "const landAt") + """
const A = JSON.parse(process.argv[process.argv.length - 1]);
globalThis.history = {state: A.state};
const view = {querySelector: (s) => (A.land ? {id: 'x'} : null)};
process.stdout.write(JSON.stringify(landAt(A.ev ? {type: A.ev} : undefined, view)));"""
        land = lambda **a: json.loads(node(js, json.dumps(a)))
        self.assertEqual(land(ev="hashchange", state={"y": 640}), {"y": 640})  # Back onto an entry that kept its place
        self.assertEqual(land(ev="hashchange", state=None), {"y": 0})  # a new link: the top
        self.assertEqual(land(state={"y": 640}), {"y": 0})  # a page's own re-render (route()) is no Back
        self.assertEqual(land(ev="hashchange", state=None, land=True), {"el": {"id": "x"}})
        self.assertIn("history.replaceState({...(history.state || {}), y: Math.round(window.scrollY)}, '')", (PAGES / "_router.js").read_text())


@unittest.skipUnless(shutil.which("node"), "no node")
class DocsStartHere(unittest.TestCase):
    """#12 (STORY-068): Start here is first and the default #docs route; `docs/X.md` written as code is a link; a link to
    a heading on the page stays on the page (?at=) and lands there; the docs use the UI's words."""

    def _links(self, md, **opts):
        safe = line("_shared.js", "const safeHref")
        prog = ("const h=(tag,attrs={},...kids)=>({tag,attrs,kids:kids.flat(Infinity)});\n" + safe + "\n" + (PAGES / "_markdown.js").read_text() +
                "\nconst A = JSON.parse(process.argv[process.argv.length - 1]); const acc=[];"
                "const walk=(n)=>{if(n&&n.tag==='a')acc.push(n.attrs.href);if(n&&n.tag&&/^h[2-4]$/.test(n.tag)&&n.attrs['data-land']!=null)acc.push('land:'+n.attrs.id);if(n&&n.kids)n.kids.forEach(walk);};"
                "mdRender(A.md, A.opts).forEach(walk); process.stdout.write(JSON.stringify(acc));")
        return json.loads(node(prog, json.dumps({"md": md, "opts": {"files": {"MAP.md": "map"}, "served": ["PROOF.md"], **opts}})))

    def test_start_here_is_first(self):
        from ledger.web import docs
        self.assertEqual(docs.SIDEBAR[0], ("handoff", "Start here", "HANDOFF.md"))  # before: "Handoff", last of nine
        self.assertEqual(docs.index()["pages"][0]["slug"], "handoff")  # docs.js opens pages[0] for a bare #docs
        self.assertIn("idx.pages[0].slug", (PAGES / "docs.js").read_text())

    def test_doc_references_in_code_are_links(self):
        got = self._links("See `docs/MAP.md`, `docs/PROOF.md`, `docs/TICKETS.md`, `docs/archive/REPLICATION.md` and `ledger/web/app.py`.")
        self.assertEqual(got, ["#docs/map", "/docs/PROOF.md", "https://github.com/kennygeiler/ai-capex-ledger/blob/main/docs/TICKETS.md",
                               "https://github.com/kennygeiler/ai-capex-ledger/blob/main/docs/archive/REPLICATION.md"])  # a code path that is no doc stays code

    def test_a_link_to_a_heading_stays_on_the_page_and_lands(self):
        md = "# Start here\n\nGo to [setup](#setup) or [Proof](#proof).\n\n## Setup\n\ntext\n"
        self.assertEqual(self._links(md, page="handoff"), ["#docs/handoff?at=setup", "#proof"])  # an app route stays an app route
        self.assertEqual(self._links(md, page="handoff", at="setup"), ["#docs/handoff?at=setup", "#proof", "land:setup"])

    def test_docs_use_the_ui_words(self):
        root = PAGES.parents[2] / "docs"
        for f in ("HANDOFF.md", "OPERATIONS.md", "MAP.md", "PROOF.md"):
            text = (root / f).read_text()
            self.assertNotIn('"asset types" group', text, f)
            self.assertNotIn("asset types group", text, f)
            self.assertNotIn("Approve or Edit", text, f)
            self.assertNotIn("**Edit**", text, f)
        self.assertNotIn("[Handoff](HANDOFF.md)", (root / "OVERVIEW.md").read_text())


class DatasetVerification(unittest.TestCase):
    """#13 (STORY-055): one Verification filter bound to `check` on every list (the taxonomy's `check`, values' and
    facts' `check_label`) and on the Grid, in the display words of ledger/core/states.py; filters kept across Rows and
    Grid; the Grid's export is the server's CSV; one export control."""

    def test_check_filters_the_verdict_column_of_every_list(self):
        from ledger.web import api
        rows = [{"ticker": "X", "check_label": "agree"}, {"ticker": "X", "check_label": "unresolved"}, {"ticker": "Y", "check": "differs"}, {"ticker": "Z", "quote": "q"}]
        got = api.apply(rows, {"check": "unresolved,differs"})
        self.assertEqual(got, [rows[1], rows[2], rows[3]])  # before: check_label rows were all kept; a list with no verdict column keeps its rows

    def test_the_grid_export_is_the_server_csv_with_its_columns(self):
        from ledger.web import app
        d = {"names": {"X": "Xco"}, "rows": [{"ticker": "X", "field": "capex", "dimension": "", "period": "FY2025", "kind": "spent", "value": 5, "check": "agree", "basis": "b",
                                                "prov": {"url": "https://www.sec.gov/x", "extractions": "e1"}}]}
        self.assertEqual(app.data_csv(d), "ticker,company,field,dimension,period,kind,value,check,basis,source_url,provenance\nX,Xco,capex,,FY2025,spent,5,agree,b,https://www.sec.gov/x,e1\n")
        page = (PAGES / "data.js").read_text()
        self.assertNotIn("createObjectURL", page)  # before: the Grid built its CSV in the browser
        self.assertNotIn("'JSON')", page)  # one export control
        self.assertIn("'/api/data?' + new URLSearchParams(", page)

    @unittest.skipUnless(shutil.which("node"), "no node")
    def test_one_vocabulary_and_filters_kept_across_views(self):
        stubs = ("const KNOWN = ['agree', 'unresolved', 'no_reference']; const stateKnown = (m, s) => m === 'check' && KNOWN.includes(s);"
                 " const checkWord = (v) => ({agree: 'Verified', unresolved: 'Differs from SEC XBRL', no_reference: 'Unverified · citation only'})[v];"
                 " const stateWord = (m, s) => ['', {ok: 'Verified', corroborated: 'Corroborated', info: 'Unverified', bad: 'Needs review', wait: 'Proposed', unknown: 'Not checked'}[s]];\n")
        pre = stubs + "\n".join(line("data.js", p) for p in ("const VERDICT_ROW", "const verdictWord", "const verdictOf", "const verdictKeep", "const switchQ")) + "\n" + block("data.js", "const verdictOptions", "\n};")
        self.assertEqual(_call(pre, "verdictOptions(A, '')", ["agree", "verbatim", "to_confirm", "corroborated", "differs", None, "agree"]),
                         [["agree,verbatim", "Verified"], ["corroborated", "Corroborated"], ["differs", "Needs review"], ["to_confirm", "Proposed"]])  # one word, one option
        self.assertEqual(_call(pre, "verdictOptions(A, 'unresolved,flag')", ["agree"]), [["agree", "Verified"], ["unresolved,flag", "Differs from SEC XBRL"]])  # an address from elsewhere stays named
        self.assertEqual(_call(pre, "A.map((r) => verdictKeep(r, 'unresolved,flag'))", [{"check": "unresolved"}, {"check": "agree", "flag": "differs_from_xbrl"}, {"check_label": "agree"}]), [True, True, False])
        self.assertEqual(_call(pre, "[switchQ(A, 'grid'), switchQ({view: 'grid', t: 'APLD', f: 'capex', check: 'agree', list: 'facts'}, 'rows')]", {"list": "facts", "ticker": "APLD", "check": "unresolved"}),
                         [{"view": "grid", "list": "facts", "t": "APLD", "check": "unresolved"}, {"list": "facts", "ticker": "APLD", "check": "agree"}])


class ReadOnlyScopeLine(unittest.TestCase):
    """#14: the read-only copy's scope line names the release it serves and its code, and flags an older release than the
    latest signed or code other than the checkout's, from the deploy record (claims/hosted.json); nothing is fetched."""

    def status(self, record, last, head):
        from unittest import mock
        from ledger.release import claims
        with mock.patch.object(claims, "_hosted_record", return_value=record), mock.patch.object(claims, "latest_signed", return_value=last), \
                mock.patch.object(claims, "_head", return_value=head), mock.patch.object(claims, "_same_code", side_effect=lambda a, b: bool(a and b and b.startswith(a))):
            return claims.copy_status()

    def test_what_the_copy_serves_and_when_it_is_stale(self):
        rec = {"release": "v1.8.0", "commit": "c0635f3", "deployed_at": "2026-11-03T02:27:34+00:00"}
        s = self.status(rec, "v1.8.0", "c0635f3aaaa")
        self.assertEqual((s["release"], s["commit"], s["older"], s["code"]), ("v1.8.0", "c0635f3", False, "same"))
        s = self.status(rec, "v1.9.0", "901b9b9ffff")
        self.assertEqual((s["older"], s["code"], s["head"]), (True, "differs", "901b9b9"))
        self.assertEqual(self.status(rec, "v1.8.0", None)["code"], "unknown")  # the hosted image has no git: never called same
        s = self.status(None, "v1.8.0", "x")
        self.assertEqual((s["recorded"], s["code"], s["older"]), (False, "unknown", None))

    @unittest.skipUnless(shutil.which("node"), "no node")
    def test_the_line(self):
        js = ("const h = (tag, attrs, ...kids) => ({tag, cls: attrs.class, text: kids.flat(Infinity).join('')});\n" + block("_router.js", "const copyLine", "\n};") +
              "\nconst A = JSON.parse(process.argv[process.argv.length - 1]);\nprocess.stdout.write(JSON.stringify(A.map((c) => copyLine(c).flat(Infinity).filter((x) => x !== '').map((x) => (typeof x === 'string' ? x : `[${x.text}]`)).join(''))));")
        got = json.loads(node(js, json.dumps([None, {"recorded": False}, {"recorded": True, "release": "v1.8.0", "commit": "c0635f3", "older": False, "code": "same"},
                                              {"recorded": True, "release": "v1.8.0", "commit": "c0635f3", "older": True, "latest_signed": "v1.9.0", "code": "differs", "head": "901b9b9"}])))
        self.assertEqual(got, ["", " · [Deploy not recorded]", " · Serves v1.8.0 · Code c0635f3", " · Serves v1.8.0 · Code c0635f3 · [Older than v1.9.0] · [Code differs from 901b9b9]"])
        self.assertIn('"copy": copy_status() if READONLY else None', (PAGES.parent / "app.py").read_text())


if __name__ == "__main__":
    unittest.main()
