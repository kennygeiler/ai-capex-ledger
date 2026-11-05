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
        self.assertIn("document.addEventListener('input', (e) => { if (e.target.id === 'me') recheck(); });", js)
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


if __name__ == "__main__":
    unittest.main()
