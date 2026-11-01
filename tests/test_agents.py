"""Agent changes are versioned and attributed: a prompt is never edited in place."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger import agents


class Versions(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "prompts").mkdir()
        for v in ("statements@v1", "statements@v2"):
            (self.dir / "prompts" / f"{v}.md").write_text(f"# {v}\nReturn prompt_version {v}.\n")
        (self.dir / "agents.json").write_text(json.dumps({"reader": {"prompt": "statements@v2", "llm": {"model": "claude-opus-5-5"}, "history": []}}))
        self.patch = mock.patch.multiple(agents, CONFIG=self.dir / "agents.json", PROMPTS=self.dir / "prompts")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.dir)

    def test_a_change_becomes_the_next_version_and_keeps_the_old_one(self):
        new = agents.save_prompt("reader", "# statements@v2\nReturn prompt_version statements@v2. Be careful.", "Kenny Geiler", "be careful")
        self.assertEqual(new, "statements@v3")
        self.assertEqual(agents.versions("reader"), ["statements@v1", "statements@v2", "statements@v3"])
        self.assertIn("statements@v3", agents.prompt_text(new))  # the copy names itself, so outputs cite the right version
        self.assertNotIn("statements@v2", agents.prompt_text(new))
        self.assertEqual(agents.prompt_text("statements@v2"), "# statements@v2\nReturn prompt_version statements@v2.\n")
        a = agents.load()["reader"]
        self.assertEqual(a["prompt"], "statements@v2")  # saved, not switched on: that is a second, explicit step
        self.assertEqual(a["history"][-1]["by"], "Kenny Geiler")
        agents.use_prompt("reader", new, "Kenny Geiler")
        self.assertEqual(agents.load()["reader"]["prompt"], "statements@v3")

    def test_a_change_needs_who_and_why(self):
        with self.assertRaises(ValueError):
            agents.save_prompt("reader", "text", "", "why")
        with self.assertRaises(ValueError):
            agents.save_prompt("reader", "text", "Kenny Geiler", " ")

    def test_switching_back_and_model_are_logged(self):
        agents.use_prompt("reader", "statements@v1", "Kenny Geiler")
        agents.set_model("reader", "claude-sonnet-5-5", "Kenny Geiler")
        a = agents.load()["reader"]
        self.assertEqual((a["prompt"], a["llm"]["model"]), ("statements@v1", "claude-sonnet-5-5"))
        self.assertEqual([h["change"] for h in a["history"]], ["switched to statements@v1", "model claude-sonnet-5-5"])
        with self.assertRaises(ValueError):
            agents.use_prompt("reader", "statements@v9", "Kenny Geiler")
        with self.assertRaises(ValueError):
            agents.set_model("reader", "rm -rf /", "Kenny Geiler")


if __name__ == "__main__":
    unittest.main()


class Retired(unittest.TestCase):
    """The attribution agent is retired with the inferred layer (2ee2e6f): marked in agents.json with a date, its prompts
    kept on disk, left out of /api/agents and the Rules page (T48)."""

    def test_the_attributor_is_marked_retired_not_deleted(self):
        import json
        cfg = json.loads((agents.ROOT / "agents" / "agents.json").read_text())
        a = cfg["attributor"]
        self.assertTrue(a["retired"])
        self.assertEqual(a["retired_at"], "2026-10-30")
        self.assertEqual(a["prompt"], "attribution@v2")
        self.assertTrue((agents.PROMPTS / "attribution@v1.md").exists() and (agents.PROMPTS / "attribution@v2.md").exists())
        self.assertEqual([k for k, v in cfg.items() if v.get("retired")], ["attributor"])
        live = [k for k, v in cfg.items() if not v.get("retired")]
        self.assertEqual(live, ["reader", "ai_reader", "notes_reader", "projects_reader", "mapper"])


class Charters(unittest.TestCase):
    """Every agent has a charter file (T48, T50): what it owns, what it never touches, its input and output, model, tools,
    prompts and the checks that judge it, written from the code. The retired attributor's says why it is retired."""

    def test_every_agent_has_a_charter_that_names_its_model_and_prompt(self):
        cfg = json.loads((agents.ROOT / "agents" / "agents.json").read_text())
        for aid, a in cfg.items():
            path = agents.ROOT / a["charter"]
            self.assertEqual(a["charter"], f"agents/charters/{aid}.md")
            self.assertTrue(path.exists(), path)
            text = path.read_text()
            if a.get("retired"):
                self.assertIn("retired", text.lower())
                self.assertIn("2ee2e6f", text)
                continue
            for word in ("Owns", "Never touches", "Input", "Output", "Model and tools", "Prompts", "Checks that judge it", a["llm"]["model"], a["prompt"], "claude -p"):
                self.assertIn(word, text, f"{aid}: {word}")
            for v in agents.versions(aid):
                self.assertIn(v, text, f"{aid} charter must list {v}")

    def test_charter_blocks_split_on_blank_lines_with_headings(self):
        blocks = agents.charter("reader")
        self.assertEqual(blocks[0], {"kind": "heading", "text": "Reader"})
        self.assertEqual([b["text"] for b in blocks if b["kind"] == "heading"][1:], ["Owns", "Never touches", "Input", "Output", "Model and tools", "Prompts", "Checks that judge it"])
        self.assertTrue(all("\n" not in b["text"] for b in blocks))
        for rule in ("citation_resolves", "xbrl_reconcile", "statement_tie"):
            self.assertIn(rule, " ".join(b["text"] for b in blocks))


class RunsPerCompany(unittest.TestCase):
    """The runs table per agent and company (T48): the step names the agent, the latest load of each subject counts once,
    an output read before the runner metered calls counts as read, not as a call."""

    def test_by_agent_from_the_runs_table(self):
        from ledger import cost, store
        con = store.init(":memory:")
        store.write(con, "documents", [{"accession": "0000789019-25-000001", "ticker": "MSFT", "cik": 1, "form": "10-K", "period": "2025-06-30", "filed": "2025-07-30", "url": "u", "sha256": "0" * 64, "bytes": 1,
                                        "parser_version": "p", "table_count": 1, "income_tables": "", "cash_flow_tables": "", "tables_path": "t"},
                                       {"accession": "0000789019-24-000001", "ticker": "MSFT", "cik": 1, "form": "10-K", "period": "2024-06-30", "filed": "2024-07-30", "url": "u", "sha256": "0" * 64, "bytes": 1,
                                        "parser_version": "p", "table_count": 1, "income_tables": "", "cash_flow_tables": "", "tables_path": "t"}], replace=True)
        meta = {"model": "claude-opus-5-5", "seconds": 10.0, "input_tokens": 1000, "output_tokens": 100, "attempts": 2}
        store.write(con, "runs", [
            {"run_id": "extract-1", "step": "extract", "subject": "0000789019-25-000001", "started_at": "2026-10-01T00:00:00+00:00", "seconds": 0.0, "outcome": "ok", "versions": "{}", "detail": json.dumps({"values": 4, **meta})},
            {"run_id": "extract-2", "step": "extract", "subject": "0000789019-25-000001", "started_at": "2026-10-02T00:00:00+00:00", "seconds": 0.0, "outcome": "ok", "versions": "{}", "detail": json.dumps({"values": 4, **meta})},  # the same output loaded again
            {"run_id": "extract-2", "step": "extract", "subject": "0000789019-24-000001", "started_at": "2026-10-02T00:00:00+00:00", "seconds": 0.0, "outcome": "ok", "versions": "{}", "detail": json.dumps({"values": 4})},  # read before `_run` existed
            {"run_id": "notes-1", "step": "notes", "subject": "0000789019-25-000001", "started_at": "2026-10-02T00:00:00+00:00", "seconds": 0.0, "outcome": "failed", "versions": "{}", "detail": json.dumps({"error": "x"})}], replace=True)
        r = cost.by_agent(con, "reader", ["MSFT", "NVDA"])
        self.assertEqual((r["step"], r["subject"]), ("extract", "filing"))
        self.assertEqual([c["ticker"] for c in r["companies"]], ["MSFT", "NVDA"])
        msft, nvda = r["companies"]
        self.assertEqual({k: msft[k] for k in ("read", "calls", "input_tokens", "output_tokens", "seconds", "attempts", "failed")},
                         {"read": 2, "calls": 1, "input_tokens": 1000, "output_tokens": 100, "seconds": 10.0, "attempts": 2, "failed": 0})
        self.assertEqual(nvda["read"], 0)
        self.assertEqual(r["total"]["calls"], 1)
        n = cost.by_agent(con, "notes_reader", ["MSFT"])["companies"][0]
        self.assertEqual((n["read"], n["calls"], n["failed"]), (1, 1, 1))
        self.assertIn("no agent column", cost.by_agent(con, "reader", ["MSFT"])["note"])
