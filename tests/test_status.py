"""One definition of open (T1): `status.state` is what Proof and Reconcile both read, so their open counts agree.

The semantics on hand-built rows, and the agreement on the fixtures: the frozen tables of the proven set are loaded
into a fresh database in a temporary repo layout (LEDGER_ROOT, the way the golden harness does it, without running the
code stages), then `proof.board()` and `workbench.items()` are read in a subprocess and compared per company."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ledger import golden, status, store
from ledger.config import PROVEN

SCRIPT = """
import json, duckdb
from ledger import app, proof, store, workbench
from ledger.config import PROVEN
con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
b = proof.board(con)
it = workbench.items(con, app.flow("all"))
print(json.dumps({"proof": {c["ticker"]: c["open"] for c in b["proven"]}, "proof_total": b["open"],
                  "reconcile": {t: sum(1 for r in it["rows"] if r["open"] and r["ticker"] == t) for t in PROVEN},
                  "states": sorted({r["state"] for r in it["rows"]}),
                  "by": sorted({r["by"].split(":")[0] for r in it["rows"] if r["ticker"] in PROVEN})}))
"""


class Definition(unittest.TestCase):
    def test_checked_explained_open_blocked(self):
        self.assertEqual(status.state({"check": "xbrl"})["state"], "checked")
        self.assertEqual(status.state({"check": "quote"})["by"], "quote")
        self.assertEqual(status.state({"check": "mapping", "mapping_to": "us-gaap:EquipmentMember"})["by"], "mapping:us-gaap:EquipmentMember")
        self.assertEqual(status.state({"definition": "cost_lines"}), {"state": "explained", "reason": "a definition on file: cost_lines", "by": "definition:cost_lines"})
        self.assertEqual(status.state({"rule": "restated_between_filings"})["state"], "explained")  # a guard counts as info
        self.assertEqual(status.state({"rule": "definition_note", "severity": "info"})["by"], "rule:definition_note")
        self.assertEqual(status.state({"label": "not_reported"})["by"], "label:not_reported")
        self.assertEqual(status.state({"rule": "sign", "severity": "block"})["state"], "blocked")
        self.assertEqual(status.state({"rule": "jump", "severity": "warn"})["state"], "open")  # a warn rule alone explains nothing
        self.assertEqual(status.state({}), {"state": "open", "reason": "neither checked nor explained", "by": ""})

    def test_a_person_resolves_what_nothing_on_file_covers(self):
        acc = {"id": "r1", "state": "accept", "reason": "right as is"}
        self.assertEqual(status.state({"resolution": acc}), {"state": "explained", "reason": "right as is", "by": "resolution:r1"})
        self.assertEqual(status.state({"resolution": {**acc, "state": "fix"}})["state"], "open")
        self.assertEqual(status.state({"resolution": {**acc, "state": "blocks"}})["state"], "blocked")
        # precedence: blocks beats a check; a check beats a fix; a fix beats a definition
        self.assertEqual(status.state({"check": "xbrl", "resolution": {**acc, "state": "blocks"}})["state"], "blocked")
        self.assertEqual(status.state({"check": "xbrl", "resolution": {**acc, "state": "fix"}})["state"], "checked")
        self.assertEqual(status.state({"definition": "revenue", "resolution": {**acc, "state": "fix"}})["state"], "open")
        self.assertTrue(status.is_open(status.state({"resolution": {**acc, "state": "blocks"}})))

    def test_a_warn_finding_takes_the_state_of_its_rows(self):
        jump = {"rule_id": "jump", "severity": "warn", "message": "capex moves 4×"}
        agree = status.of_value({"field": "capex", "period": "FY2025", "label": "agree"})
        gap = status.of_value({"field": "opex", "period": "FY2026", "label": "definition_gap"})
        unres = status.of_value({"field": "capex", "period": "FY2024", "label": "unresolved"})
        self.assertEqual(status.of_exception(jump, None, [agree])["state"], "checked")
        self.assertEqual(status.of_exception(jump, None, [gap])["by"], "definition:cost_lines")
        self.assertEqual(status.of_exception(jump, None, [agree, unres])["state"], "open")
        self.assertEqual(status.of_exception(jump, None, [])["state"], "open")
        self.assertEqual(status.of_exception({**jump, "severity": "block"}, None, [agree])["state"], "blocked")
        self.assertEqual(status.of_exception({**jump, "severity": "info"}, None, [])["state"], "explained")
        self.assertEqual(status.of_exception(jump, {"id": "r2", "state": "accept", "reason": "a real move"}, [unres])["by"], "resolution:r2")

    def test_fact_rows(self):
        self.assertEqual(status.of_fact({"label": "agree"})["by"], "xbrl")
        self.assertEqual(status.of_fact({"label": "no_reference"})["state"], "explained")
        self.assertEqual(status.of_fact({"label": "unresolved"})["state"], "open")
        r = status.of_fact({"label": "unresolved"}, None, "cell from a, tag from b")
        self.assertEqual((r["state"], r["by"], r["reason"]), ("explained", "rule:restated_between_filings", "cell from a, tag from b"))


def fixture_root() -> Path:
    """A repo layout in a temporary folder holding the proven set's frozen tables (fixtures/expected) in a fresh database,
    the way the golden harness lays it out, without running the code stages. The caller removes it."""
    seed = json.loads((golden.FIXTURES / "seed.json").read_text())
    root = Path(tempfile.mkdtemp(prefix="ledger-status-"))
    for name in golden.SHARED:  # taxonomy/ (the asset-type mappings the mapping stage reads) is in SHARED since T31
        if (store.ROOT / name).exists():
            os.symlink(store.ROOT / name, root / name)
    shutil.copytree(golden.FIXTURES / "data", root / "data")
    (root / "reports").mkdir()
    (root / "reports" / "stage3-faults.json").write_text("[]")
    con = store.init(root / "data" / "ledger.duckdb")
    store.write(con, "documents", seed["documents"])
    store.write(con, "texts", seed["texts"])
    if seed.get("reference_values"):
        store.write(con, "reference_values", seed["reference_values"])
    for name, skip in golden.TABLES.items():  # the frozen tables, with the per-run columns the freeze left out filled in
        f = golden.EXPECTED / f"{name}.csv"
        if f.exists() and f.read_text().strip():
            cols = {r[0]: (r[1], r[2] == "YES") for r in con.execute("select column_name, data_type, is_nullable from information_schema.columns where table_name = ?", [name]).fetchall()}
            head = con.execute("select * from read_csv(?, header = true, all_varchar = true) limit 0", [str(f)]).description
            sel = [(f"nullif({c}, '')" if nullable or typ != "VARCHAR" else f"coalesce({c}, '')") + f"::{typ} as {c}" for c in [h[0] for h in head] for typ, nullable in [cols[c]]]  # an empty cell is NULL where the schema allows it, '' where it does not
            sel += [f"'fixture' as {c}" if c == "run_id" else f"md5(concat_ws('|', rule_id, ticker, field, period, subject)) as {c}" for c in skip if c in cols]
            con.execute(f'insert into "{name}" by name select {", ".join(sel)} from read_csv(?, header = true, all_varchar = true)', [str(f)])
    con.close()
    return root


@unittest.skipIf(not (golden.FIXTURES / "seed.json").exists(), "no fixtures")
class ProofAgreesWithReconcile(unittest.TestCase):
    """On the frozen tables of the proven set, Proof's open count equals Reconcile's, company by company."""

    def test_open_counts_agree_on_the_fixtures(self):
        root = fixture_root()
        try:
            out = subprocess.run([sys.executable, "-c", SCRIPT], cwd=store.ROOT, env={**os.environ, "LEDGER_ROOT": str(root)}, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            r = json.loads(out.stdout.strip().splitlines()[-1])
        finally:
            shutil.rmtree(root, ignore_errors=True)
        self.assertEqual(sorted(r["proof"]), sorted(PROVEN))
        self.assertEqual(r["proof"], r["reconcile"], f"Proof and Reconcile disagree on what is open: {r}")
        self.assertEqual(r["proof_total"], sum(r["reconcile"].values()))
        self.assertTrue(set(r["states"]) <= set(status.STATES), r["states"])


if __name__ == "__main__":
    unittest.main()
