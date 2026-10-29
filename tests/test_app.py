"""A money-flow model is never edited in place: a change is the next version, switched on as a second step, both logged."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger import agents


class Models(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "models").mkdir()
        (self.dir / "models" / "neocloud@v1.md").write_text("# Money-flow model: neocloud (neocloud@v1)\nAll capex is AI.\n")
        (self.dir / "agents.json").write_text(json.dumps({"attributor": {"prompt": "attribution@v1", "models": {"neocloud": "neocloud@v1"}, "llm": {"model": "claude-opus-5-5"}, "history": []}}))
        self.patch = mock.patch.multiple(agents, CONFIG=self.dir / "agents.json", MODELS=self.dir / "models")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        shutil.rmtree(self.dir)

    def test_an_edit_becomes_the_next_version_and_is_switched_on_separately(self):
        v = agents.save_model("neocloud", "# Money-flow model: neocloud (neocloud@v1)\nAll capex is AI. Leases too.\n", "Kenny Geiler", "count leases")
        self.assertEqual((v, agents.model_versions("neocloud")), ("neocloud@v2", ["neocloud@v1", "neocloud@v2"]))
        self.assertIn("neocloud@v2", agents.model_text(v))
        self.assertEqual(agents.load()["attributor"]["models"]["neocloud"], "neocloud@v1")
        agents.use_model("neocloud", v, "Kenny Geiler")
        self.assertEqual(agents.load()["attributor"]["models"]["neocloud"], "neocloud@v2")
        self.assertEqual([x["by"] for x in agents.load()["attributor"]["history"]], ["Kenny Geiler", "Kenny Geiler"])
        with self.assertRaises(ValueError):
            agents.save_model("neocloud", "text", "", "why")
        with self.assertRaises(ValueError):
            agents.use_model("neocloud", "neocloud@v9", "Kenny Geiler")


if __name__ == "__main__":
    unittest.main()
