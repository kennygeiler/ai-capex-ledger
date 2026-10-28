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
        self.assertEqual(a["prompt"], "statements@v3")
        self.assertEqual(a["history"][-1]["by"], "Kenny Geiler")

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
