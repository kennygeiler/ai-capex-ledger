"""The headless agent loop: a rejected answer is retried once with the reason; run evidence is kept."""
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger import agent
from ledger.extract import Invalid, prompt_version


class _Invalid(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason
from tests.test_rules import ACC, parsed

GOOD = {"accession": ACC, "prompt_version": prompt_version(), "not_found": [],
        "values": [{"field": "revenue", "table_id": "t0000", "row_label": "Total revenues", "column_label": "Year Ended May 31, | 2026",
                    "cell_text": "67,357", "period_end": "2026-05-31", "months": 12, "value": 67357000000, "confidence": 1}]}
BAD = {**GOOD, "values": [{**GOOD["values"][0], "cell_text": "99,999"}]}


def fake_claude(d: str, first: dict, second: dict) -> None:
    """A stand-in `claude` that answers `first`, then `second` once told its answer was rejected."""
    script = Path(d) / os.path.basename(agent.CLI)
    reply = lambda o: json.dumps({"is_error": False, "result": "```json\n" + json.dumps(o) + "\n```", "modelUsage": {"claude-test": {"outputTokens": 5}, "claude-small": {"outputTokens": 1}},
                                  "usage": {"input_tokens": 10, "output_tokens": 5}})
    script.write_text(f"#!/usr/bin/env python3\nimport sys\nprint({reply(second)!r} if 'rejected' in sys.stdin.read() else {reply(first)!r})\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)


class Agent(unittest.TestCase):
    def run_with(self, first, second):
        with tempfile.TemporaryDirectory() as d:
            fake_claude(d, first, second)
            with mock.patch.dict(agent.ENV, {"PATH": d + os.pathsep + os.environ["PATH"]}):
                return agent.extract("task", parsed())

    def test_a_bad_citation_is_retried_with_the_reason(self):
        out = self.run_with(BAD, GOOD)
        self.assertEqual((out["values"][0]["cell_text"], out["_run"]["attempts"], out["_run"]["model"]), ("67,357", 2, "claude-test"))

    def test_gives_up_after_one_retry(self):
        with self.assertRaises(Invalid):
            self.run_with(BAD, BAD)


class EveryReaderIsRetried(unittest.TestCase):
    def test_any_reader_invalid_is_retried_and_kept(self):
        answers = iter(['{"a": 1}', '{"a": 2}'])
        calls = []
        with mock.patch.object(agent, "_ask", lambda prompt, m: (calls.append(prompt), (next(answers), {"model": "m", "seconds": 1.0, "input_tokens": 10, "output_tokens": 5}))[1]), \
             mock.patch.object(agent.agents, "load", lambda: {"notes_reader": {"prompt": "notes@v3", "llm": {"model": "m"}}}), \
             mock.patch.object(agent, "model", lambda a: "m"), mock.patch.object(agent.agents, "prompt_text", lambda v: "P"):
            def check(obj):
                raise _Invalid(f"bad {obj['a']}")
            with self.assertRaises(_Invalid) as cm:
                agent.ask("notes_reader", "T", check)
        self.assertEqual(len(calls), 2)
        self.assertIn("rejected: bad 1", calls[1])
        self.assertIn("after 2 attempts", cm.exception.reason)
        self.assertEqual(cm.exception.answer, '{"a": 2}')


if __name__ == "__main__":
    unittest.main()
