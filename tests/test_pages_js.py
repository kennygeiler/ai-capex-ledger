"""Page logic run in node, the pure pieces of ledger/web/pages/*.js pulled out by name (the pattern tests.test_score.Page uses).

F-BF3: Explore's Save as view / Save changes / Delete sent no Content-Type and the server refused them 403. api() now adds
application/json to any request with a body, so no page can forget it."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

PAGES = Path(__file__).resolve().parents[1] / "ledger" / "web" / "pages"


def line(file: str, prefix: str) -> str:
    """The one top-level line of a page script that starts with `prefix` (a `const name = ...` helper)."""
    return next(l for l in (PAGES / file).read_text().splitlines() if l.startswith(prefix))


def block(file: str, start: str, end: str) -> str:
    s = (PAGES / file).read_text()
    i = s.index(start)
    return s[i:s.index(end, i) + len(end)]


def node(js: str, *args) -> str:
    return subprocess.run(["node", "-e", js, "--", *args], capture_output=True, text=True, check=True).stdout


@unittest.skipUnless(shutil.which("node"), "no node")
class JsonWrites(unittest.TestCase):
    def run_api(self, opts) -> dict:
        js = line("_shared.js", "const withJson") + "\n" + block("_shared.js", "async function api(", "\n}") + """
let seen; globalThis.fetch = async (p, o) => { seen = o || null; return {ok: true, json: async () => ({})}; };
api('/api/v1/views', JSON.parse(process.argv[process.argv.length - 1])).then(() => process.stdout.write(JSON.stringify(seen)));"""
        return json.loads(node(js, json.dumps(opts)))

    def test_a_body_gets_the_json_content_type(self):
        got = self.run_api({"method": "POST", "body": json.dumps({"by": "Kenny Geiler"})})
        self.assertEqual(got["headers"]["Content-Type"], "application/json")

    def test_a_callers_header_is_kept(self):
        got = self.run_api({"method": "POST", "body": "{}", "headers": {"content-type": "application/json; charset=utf-8"}})
        self.assertEqual(got["headers"], {"content-type": "application/json; charset=utf-8"})

    def test_a_get_is_unchanged(self):
        self.assertIsNone(self.run_api(None))

    def test_explore_writes_go_through_api(self):
        """Save as view, Save changes and Delete: every POST in explore.js is an api() call, none a bare fetch; Delete
        catches its error and shows it beside the button."""
        js = (PAGES / "explore.js").read_text()
        self.assertNotIn("fetch(", js)
        posts = re.findall(r"(\w+)\([^()]*\{method: 'POST'", js)
        self.assertEqual(sorted(set(posts)), ["api"])
        self.assertIn("catch (err) { delMsg.textContent = err.message", js)


@unittest.skipUnless(shutil.which("node"), "no node")
class BulkSelect(unittest.TestCase):
    """F-BF4: "Select all n" and the space key selected Category mapping rows too, and /api/resolve/bulk refused the whole
    batch (400). Only rows the bulk route takes are selectable."""

    def keys(self, rows):
        js = line("reconcile.js", "const bulkable") + "\n" + line("reconcile.js", "const bulkKeys") + \
            "\nprocess.stdout.write(JSON.stringify(bulkKeys(JSON.parse(process.argv[process.argv.length - 1]))));"
        return json.loads(node(js, json.dumps(rows)))

    def test_mapping_rows_are_never_selected(self):
        rows = [{"key": "finding_unconfirmed|GOOGL|capex|FY2024||jump|", "cause": "finding_unconfirmed", "bulk": True},
                {"key": "asset_types|GOOGL|Land", "cause": "asset_types", "bulk": True},  # even if a server said so
                {"key": "asset_types|GOOGL|Servers", "cause": "asset_types", "bulk": False},
                {"key": "blocked|AMD|capex|FY2023||x|", "cause": "blocked"}]  # no bulk flag: not selectable
        self.assertEqual(self.keys(rows), ["finding_unconfirmed|GOOGL|capex|FY2024||jump|"])

    def test_the_page_selects_through_bulkable_only(self):
        js = (PAGES / "reconcile.js").read_text()
        self.assertIn("for (const k of selectable) selected.add(k)", js)
        self.assertIn("if (!bulkable(r)) return; selected.has(r.key)", js)
        self.assertIn("const cb = !bulkable(r) ? '' :", js)
        self.assertNotIn("for (const r of open) selected.add(r.key)", js)


@unittest.skipUnless(shutil.which("node"), "no node")
class SignButton(unittest.TestCase):
    """F-BF5: Sign's enabled state was fixed at render; typing a name changed nothing. signState decides it from the
    checklist and the Signer box, and the page re-reads it on every input to the box."""

    def state(self, cl, name):
        js = line("release.js", "const signState") + "\nconst a = JSON.parse(process.argv[process.argv.length - 1]);\nprocess.stdout.write(JSON.stringify(signState(a[0], a[1])));"
        return json.loads(node(js, json.dumps([cl, name])))

    CL = {"version": "v1.9.0", "people": ["Kenny Geiler"], "lines": [{"required": True, "ok": True}, {"required": False, "ok": False}]}

    def test_enabled_only_for_a_name_on_the_list_with_every_required_line_green(self):
        self.assertEqual(self.state(self.CL, "Kenny Geiler"), [True, "Signs and publishes v1.9.0"])
        self.assertEqual(self.state(self.CL, " Kenny Geiler "), [True, "Signs and publishes v1.9.0"])
        self.assertEqual(self.state(self.CL, ""), [False, "Enter a signer name"])
        self.assertEqual(self.state(self.CL, "Mallory"), [False, "Not on the signer list"])
        red = {**self.CL, "lines": [{"required": True, "ok": False}]}
        self.assertEqual(self.state(red, "Kenny Geiler"), [False, "1 required check failing"])

    def test_the_page_rechecks_on_every_input_to_the_signer_box(self):
        js = (PAGES / "release.js").read_text()
        top = js[:js.index("async function releasePage")]
        body = js[js.index("async function releasePage"):]
        self.assertIn("document.addEventListener('input', (e) => { if (e.target.id === 'me' && releaseRecheck) releaseRecheck(); });", top)  # bound once, at load
        self.assertNotIn("addEventListener", body)  # never once per render (review item 10)
        self.assertIn("button.disabled = !canSign", js)


@unittest.skipUnless(shutil.which("node"), "no node")
class ExploreExport(unittest.TestCase):
    """F-BF7: Explore's JSON and CSV links dropped Measure, Category, Standard type and From / To (617 rows exported, 27
    charted). The chart's rows and both links come from one URL, listUrl, which carries every filter."""

    def url(self, st):
        js = line("explore.js", "const listUrl") + "\nprocess.stdout.write(listUrl(JSON.parse(process.argv[process.argv.length - 1])));"
        return node(js, json.dumps(st))

    def test_every_chart_filter_is_in_the_export_url(self):
        from urllib.parse import parse_qs, urlparse
        u = urlparse(self.url({"measure": "taxonomy", "tmeasure": "spent", "category": "capex", "standard_type": "LandMember", "from": "FY2023", "to": "FY2025",
                               "layer": "hyperscaler", "ticker": "MSFT,GOOGL", "field": "", "kind": ""}))
        self.assertEqual(u.path, "/api/v1/taxonomy")
        self.assertEqual({k: v[0] for k, v in parse_qs(u.query).items()},
                         {"measure": "spent", "category": "capex", "standard_type": "LandMember", "from": "FY2023", "to": "FY2025", "layer": "hyperscaler", "ticker": "MSFT,GOOGL"})

    def test_the_chart_and_the_links_read_one_url(self):
        js = (PAGES / "explore.js").read_text()
        self.assertIn("const fetchRows = async () => (await api(listUrl(st))).rows;", js)
        self.assertIn("const url = listUrl(st);", js)
        self.assertIn("h('a', {href: url + '&format=csv', class: 'small'}, 'CSV')", js)


@unittest.skipUnless(shutil.which("node"), "no node")
class PartialYears(unittest.TestCase):
    """F-BF10: Explore summed FY2026 over the 3 of 6 companies that had filed it and drew it as a complete bar, which read
    as a capex collapse. yearCoverage is the one test of a year complete for the set; a partial year is hatched, lighter and
    labelled "FY2026 · 3 of 6 companies"."""

    def cov(self, rows, key="fiscal_year"):
        js = line("explore.js", "const yearCoverage") + "\nprocess.stdout.write(JSON.stringify(yearCoverage(JSON.parse(process.argv[process.argv.length - 1]), 'fiscal_year')));"
        return json.loads(node(js, json.dumps(rows)))

    def test_a_year_fewer_companies_filed_is_not_complete(self):
        six = ["MSFT", "GOOGL", "AMZN", "NVDA", "APLD", "AMD"]
        rows = [{"ticker": t, "fiscal_year": "FY2025", "value": 1} for t in six] + [{"ticker": t, "fiscal_year": "FY2026", "value": 1} for t in ("MSFT", "NVDA", "APLD")]
        rows += [{"ticker": "MSFT", "fiscal_year": "FY2025", "value": 2}]  # two rows of one company count once
        got = self.cov(rows)
        self.assertEqual(got["FY2025"], {"n": 6, "of": 6, "complete": True})
        self.assertEqual(got["FY2026"], {"n": 3, "of": 6, "complete": False})

    def test_one_company_is_always_complete(self):
        self.assertEqual(self.cov([{"ticker": "A", "fiscal_year": "FY2024"}]), {"FY2024": {"n": 1, "of": 1, "complete": True}})

    def test_the_chart_marks_partial_years(self):
        js = (PAGES / "explore.js").read_text()
        self.assertIn("partial(x) ? `${x} · ${cov[x].n} of ${cov[x].of} companies`", js)
        self.assertIn("pattern: {shape: xs.map((x) => (partial(x) ? '/' : ''))", js)
        self.assertIn("`Incomplete: ${gaps.map(xLabel).join(', ')}`", js)


@unittest.skipUnless(shutil.which("node"), "no node")
class ReconcileSigners(unittest.TestCase):
    """F-BF13: Reconcile's Approve, Choose another and Reject (every needsMe button) disable for a name not on
    config.PEOPLE, which the reconcile feed sends as `people`, the same as Sign."""

    def run_js(self, people, names):
        js = "let me = '';\n" + "\n".join(line("reconcile.js", p) for p in ("let SIGNERS", "const isSigner", "const signerWhy")) + \
            "\nconst a = JSON.parse(process.argv[process.argv.length - 1]); SIGNERS = a[0];\nprocess.stdout.write(JSON.stringify(a[1].map((n) => [isSigner(n), signerWhy(n)])));"
        return json.loads(node(js, json.dumps([people, names])))

    def test_only_a_name_on_the_list_enables(self):
        got = self.run_js(["Kenny Geiler"], ["Kenny Geiler", " Kenny Geiler ", "Mallory", ""])
        self.assertEqual([g[0] for g in got], [True, True, False, False])
        self.assertEqual([got[2][1], got[3][1]], ["Not on the signer list", "Enter a signer name"])

    def test_every_mapping_write_button_goes_through_needs_me(self):
        js = (PAGES / "reconcile.js").read_text()
        self.assertEqual(js.count("const reject = needsMe(h('button'"), 2)
        self.assertIn("const choose = needsMe(h('button'", js)
        self.assertEqual(js.count("const approve = needsMe(h('button'"), 2)
        self.assertNotIn("!(me || '').trim()", js)
        self.assertIn("SIGNERS = d.people || [];", js)


APP = PAGES.parent / "app.html"


class VisualContract(unittest.TestCase):
    """V3-V8 (docs/ux-visual/problems.md): the shared rules every page draws with. The measured side is tests.test_layout."""

    def css(self) -> str:
        return APP.read_text()

    def test_one_segmented_control(self):
        """V3: every either/or choice is .seg, at least 28 px tall with 10 px sides; its selected segment is a neutral fill, never
        the primary action's colour."""
        css = self.css()
        self.assertIn(".seg > .btn { min-height: 1.75rem; padding: 0 .625rem;", css)
        sel = re.search(r"\.seg > \.btn\.active[^{]*\{([^}]*)\}", css).group(1)
        self.assertIn("background: color-mix(in srgb, var(--tblr-body-color) 13%, var(--tblr-bg-surface))", sel)
        self.assertNotIn("primary", sel)
        self.assertNotIn(".btn-group .btn.active { background: var(--tblr-primary)", css)
        for f in PAGES.glob("*.js"):
            for m in re.finditer(r"class: '(btn-group[^']*)'", f.read_text()):
                self.assertIn("seg", m.group(1).split(), f.name)
        self.assertIn("root.querySelectorAll('.btn-group[role=group]:not(.seg)').forEach((el) => el.classList.add('seg'))", (PAGES / "_shared.js").read_text())

    def test_controls_and_focus(self):
        """V3: small buttons, selects and inputs are at least 24 px (28); a link-styled button gets a 24 px box; Tab shows a
        2 px ring on every control, sort headers and segments included."""
        css = self.css()
        self.assertIn(".btn-sm, .form-select-sm, .form-control-sm { min-height: 1.75rem; }", css)
        self.assertIn(".btn-link.p-0 { min-height: 1.5rem;", css)
        ring = re.search(r"button:focus-visible, \.btn:focus-visible[^{]*\{([^}]*)\}", css)
        self.assertIsNotNone(ring)
        self.assertIn("outline: 2px solid var(--tblr-primary) !important", ring.group(1))
        self.assertIn("[tabindex]:focus-visible", css)

    def test_one_primary_fill_per_screen(self):
        """V3: a row's own action is outlined; the primary fill is the one Save, Sign or Export."""
        rec = (PAGES / "reconcile.js").read_text()
        self.assertIn("const confirm = h('button', {type: 'button', class: 'btn btn-sm btn-outline-primary'", rec)
        self.assertNotIn("(isMatch(r) ? 'btn-outline-primary' : 'btn-primary')", rec)
        self.assertNotIn("btn btn-primary btn-sm", (PAGES / "evidence.js").read_text())
        self.assertNotIn("'btn-primary' : 'btn-outline-secondary'", (PAGES / "proof.js").read_text())

    def test_sticky_table_headers(self):
        """V4: every .table keeps its header row on screen; a wrapper that fits lets it follow the page, a wide one scrolls inside."""
        css = self.css()
        self.assertIn(".table > thead > tr > th { position: sticky; top: 0;", css)
        self.assertIn(".table-responsive.fit { overflow: visible; }", css)
        self.assertIn(".table-responsive.wide { max-height: calc(100vh - 2rem); overflow: auto; }", css)
        self.assertIn("fitTables(root);", (PAGES / "_shared.js").read_text())

    def test_dataset_rows_page_at_most_100(self):
        """V4: Dataset Rows draws one page of at most 100 rows, with a pager."""
        n = int(re.search(r"^const PAGE_ROWS = (\d+);", (PAGES / "_shared.js").read_text(), re.M).group(1))
        self.assertLessEqual(n, 100)
        self.assertIn("table(filled(rows).map(tcol), rows, {detail, page: PAGE_ROWS})", (PAGES / "data.js").read_text())

    def test_page_head_band(self):
        """V5: the scope line sits in the page container above main, not in its own container under the navbar."""
        html = self.css()
        self.assertLess(html.index('id="scopeline"'), html.index('<main id="view"'))
        self.assertGreater(html.index('id="scopeline"'), html.index('<div class="container-xl">\n  <div'))
        self.assertNotIn("$('header').after(", (PAGES / "_router.js").read_text())

    def test_reconcile_fixed_layout_and_overlay_bulk_bar(self):
        """V8: fixed table layout with set widths; a detail row spans the table's own columns; the bulk bar is fixed, out of the flow."""
        css, rec = self.css(), (PAGES / "reconcile.js").read_text()
        self.assertIn("table.rec { table-layout: fixed; width: 100%; }", css)
        self.assertIn(".bulkbar { position: fixed;", css)
        self.assertIn("class: 'card bulkbar', hidden: true", rec)
        self.assertIn("colspan: t.tr.closest('table').querySelectorAll('thead th').length", rec)
        self.assertNotIn("colspan: 8", rec)


class VisualContract2(unittest.TestCase):
    """V9-V23 (docs/ux-visual/problems.md, measured in docs/ux-visual/verification/V9-V23.md): the drawing rules. The measured
    side is tests.test_layout."""

    def test_redrawn_tables_keep_the_kit(self):
        """V17: Find, Show rows and a bar click redraw with table(), whose sort headers carry the kit's classes; the buttons
        those pages draw after the router's skin() carry their own (never a bare native button)."""
        shared = (PAGES / "_shared.js").read_text()
        self.assertIn("th.append(h('button', {type: 'button', class: 'btn btn-link btn-sm p-0 align-baseline'", shared)
        for f in ("explore.js", "data.js"):
            for m in re.finditer(r"h\('button', \{type: 'button', class: '([^']*)'", (PAGES / f).read_text()):
                classes = m.group(1).split()
                self.assertIn("btn", classes, f)
                self.assertTrue({"btn-primary", "btn-link", "btn-outline-secondary", "btn-ghost-secondary"} & set(classes), (f, m.group(1)))


@unittest.skipUnless(shutil.which("node"), "no node")
class ExploreColours(unittest.TestCase):
    """V20 / DE28: a series' colour is fixed by what it is (a company by its place in the scope), never by the order a browser
    first saw it (the old localStorage register gave viewers different colours for the same company)."""

    def colours(self, scope, calls):
        js = line("explore.js", "const COLORS") + "\nconst INDUSTRY = {hyperscaler: 1, neocloud: 1, miner_to_hpc: 1, chip_seller: 1};\n" + block("explore.js", "const colorOf = ", "\n};") + \
            "\nconst a = JSON.parse(process.argv[process.argv.length - 1]); const SCOPE = a[0];\nprocess.stdout.write(JSON.stringify(a[1].map(([d, n, v]) => colorOf(d, n, v))));"
        return json.loads(node(js, json.dumps([scope, calls])))

    def test_a_company_keeps_its_colour_whatever_else_is_drawn(self):
        scope = ["MSFT", "GOOGL", "AMZN", "NVDA", "APLD", "AMD"]
        got = self.colours(scope, [["ticker", "AMD", []], ["ticker", "APLD", []], ["ticker", "AMD", ["AMD"]], ["layer", "hyperscaler", []], ["layer", "hyperscaler", ["x"]]])
        self.assertEqual(got[0], got[2])
        self.assertNotEqual(got[0], got[1])
        self.assertEqual(got[3], got[4])
        six = self.colours(scope, [["ticker", t, []] for t in scope])
        self.assertEqual(len(set(six)), 6)  # the six companies in scope never share a colour
        self.assertNotIn("localStorage", (PAGES / "explore.js").read_text())

    def test_controls_are_labelled_and_the_chart_waits_for_plotly(self):
        js = (PAGES / "explore.js").read_text()
        self.assertIn("const sel = (label, key, opts, {blank} = {}) => h('label', {class: 'exf'}, h('span', {class: 'exl'}, label)", js)
        self.assertNotIn("'then'", js)
        self.assertNotIn("`x: ${t}`", js)
        self.assertIn("if (!await plotlyReady())", js)
        self.assertIn("if (!await plotlyReady())", (PAGES / "proof.js").read_text())


@unittest.skipUnless(shutil.which("node"), "no node")
class FiguresInCells(unittest.TestCase):
    """V11: the server's finding text and a tie's detail are taken apart into labelled values; nothing is recomputed, and a
    text of an unknown shape is shown as written (null here)."""

    def run_js(self, fn, args):
        js = "const LABEL = {opex: 'Opex'};\n" + line("_shared.js", "const memberWords") + "\n" + block("_shared.js", f"function {fn}(", "\n}") + \
            f"\nprocess.stdout.write(JSON.stringify(JSON.parse(process.argv[process.argv.length - 1]).map({fn})));"
        return json.loads(node(js, json.dumps(args)))

    def test_a_tie_finding_becomes_cells(self):
        got = self.run_js("messageFacts", [
            "2 parts in 0001144879-26-000048 sum to $2,989.9M; the filing tags PaymentsToAcquireProductiveAssets $2,865.8M for 2026-05-31 (gap $124.2M, tolerance on the sum ±$1,500)",
            "opex moves 4.69× from FY2025 (83,985,000) to FY2026 (394,144,000)",
            "something else entirely"])
        self.assertEqual([k for k, *_ in got[0]], ["Parts", "Sum of parts", "Tagged as", "Tagged total", "Period end", "Gap", "Tolerance"])
        self.assertEqual(dict((k, v) for k, v, *_ in got[0])["Sum of parts"], "$2,989.9M")
        self.assertEqual(dict((k, v) for k, v, *_ in got[0])["Gap"], "$124.2M")
        self.assertEqual(got[1], [["Field", "Opex"], ["FY2025", "83,985,000"], ["FY2026", "394,144,000"], ["Change", "4.69×"]])
        self.assertIsNone(got[2])

    def test_a_ties_parts_become_a_list(self):
        got = self.run_js("tieParts", ["7 parts · tolerance ±$4,000 · Building $30.2M; Land $1.1M", "The two cost lines above gross profit."])
        self.assertEqual(got[0], {"n": "7 parts", "tolerance": "±$4,000", "parts": [["Building", "$30.2M"], ["Land", "$1.1M"]]})
        self.assertIsNone(got[1])

    def test_the_rules_score_is_cells(self):
        js = (PAGES / "rules.js").read_text()
        self.assertNotIn("`Caught ${of(f.caught, f.planted)} · Missed", js)
        for label in ("item('Caught', of(f.caught, f.planted))", "item('Missed', int(f.escaped))", "item('Caught without SEC XBRL', int(off.caught))", "item('Matches SEC XBRL', of(sc.twin.agree, sc.twin.of)"):
            self.assertIn(label, js)


@unittest.skipUnless(shutil.which("node"), "no node")
class MoneyUnits(unittest.TestCase):
    """V16: one unit per place. A chart's tooltip and Data table use the axis's unit; a Grid's cells one unit; Dataset Rows'
    money columns to the dollar with a $ (never a bare integer); the hand check's exact figures as filed are untouched."""

    def fmt(self, cases):
        js = block("_shared.js", "const usd = (n) => {", "\n};") + "\n" + block("_shared.js", "const usdIn = ", "\n};") + \
            "\nprocess.stdout.write(JSON.stringify(JSON.parse(process.argv[process.argv.length - 1]).map(([n, u]) => usdIn(n, u))));"
        return json.loads(node(js, json.dumps(cases)))

    def test_one_unit(self):
        self.assertEqual(self.fmt([[119016000000, "B"], [390000, "M"], [9800000, "M"], [-1500, "M"], [None, "M"], [513983000000, "M"]]),
                         ["$119.0B", "$0.39M", "$9.8M", "−$0.0015M", "—", "$513,983M"])

    def test_the_places_use_it(self):
        ex, data = (PAGES / "explore.js").read_text(), (PAGES / "data.js").read_text()
        self.assertIn("isShare ? pct(v) : usdIn(v, suffix)", ex)
        self.assertNotIn("row(s)", ex)
        self.assertIn("usdIn(r.value, gridUnit)", data)
        self.assertIn("MONEY_KEYS.has(k) && (!r.unit || /^usd$/i.test(r.unit)) ? usdExact(v)", data)
        self.assertIn("usdExact", (PAGES / "proof.js").read_text())  # the hand check reads to the dollar, as before


@unittest.skipUnless(shutil.which("node"), "no node")
class MachineWords(unittest.TestCase):
    """V22: a member's code name reads as words; a server line naming one keeps its words and reads the code as words."""

    def test_member_codes_read_as_words(self):
        js = line("_shared.js", "const memberWords") + "\n" + line("_shared.js", "const memberText") + \
            "\nprocess.stdout.write(JSON.stringify(JSON.parse(process.argv[process.argv.length - 1]).map(memberText)));"
        got = json.loads(node(js, json.dumps(["Company-specific tag: amzn:ServersAndNetworkingEquipmentMember", "us-gaap:LandMember and goog:TechnicalInfrastructureMember", "no code here"])))
        self.assertEqual(got, ["Company-specific tag: Servers and networking equipment", "Land and Technical infrastructure", "no code here"])

    def test_no_accession_printed_on_evidence(self):
        ev = (PAGES / "evidence.js").read_text()
        self.assertNotIn("· ${e.accession} ·", ev)
        self.assertNotIn("'text-secondary small mb-2 mono'}, e.accession", ev)


@unittest.skipUnless(shutil.which("node"), "no node")
class HandCheckNote(unittest.TestCase):
    """V4 / PB9: the note box shows only after Wrong or Can't say, or when a note is on file; never for Right or unchecked."""

    def shown(self, items):
        js = line("proof.js", "const noteShown") + "\nprocess.stdout.write(JSON.stringify(JSON.parse(process.argv[process.argv.length - 1]).map(noteShown)));"
        return json.loads(node(js, json.dumps(items)))

    def test_hidden_for_right(self):
        got = self.shown([{"verdict": "right"}, {"verdict": None}, {"verdict": "wrong"}, {"verdict": "cant_say"}, {"verdict": "right", "note": "see note 7"}, {"verdict": "right", "note": "  "}])
        self.assertEqual(got, [False, False, True, True, True, False])

    def test_the_note_input_reads_it(self):
        js = (PAGES / "proof.js").read_text()
        self.assertIn("'aria-label': `Note on ${it.id}`, hidden: !noteShown(it)}", js)
        self.assertIn("note.hidden = false; msg.replaceChildren(h('span', {class: 'text-red'}, 'Note required'))", js)


@unittest.skipUnless(shutil.which("node"), "no node")
class CropScale(unittest.TestCase):
    """Review risks 6-7: a cell whose ink is a dash (a few px) once asked for a scale of 4.5, an Evidence crop 7,200 px wide.
    Under MIN_INK the figure counts as not found (the filing's own size); no scale exceeds MAX_SCALE."""

    def scale(self, inks, px):
        js = "\n".join(line("_shared.js", p) for p in ("const FIG_PX", "const DIGIT_EM", "const MIN_INK", "const legibleScale")) + \
            f"\nprocess.stdout.write(JSON.stringify(JSON.parse(process.argv[process.argv.length - 1]).map((i) => legibleScale(i === null ? null : {{inkH: i}}, {px}))));"
        return json.loads(node(js, json.dumps(inks)))

    def test_tiny_ink_falls_back_and_nothing_is_unbounded(self):
        got = self.scale([None, 2, 4, 9, 10, 16, 40], "EV_FIG_PX")
        self.assertEqual(got[:4], [0.5, 0.5, 0.5, 0.5])
        self.assertTrue(all(0 < g <= 1 for g in got))
        self.assertAlmostEqual(got[5], 12.5 * 0.72 / 16)


if __name__ == "__main__":
    unittest.main()
