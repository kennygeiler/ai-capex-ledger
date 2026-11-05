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


if __name__ == "__main__":
    unittest.main()
