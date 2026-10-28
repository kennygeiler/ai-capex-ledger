"""Run one extraction task headless: `claude -p` on the user's Claude subscription, no paid API, no tools.

The agent gets the frozen prompt and the task (statement tables only) and must answer with the output JSON. The answer
is checked here (schema, then every citation against the parsed filing); a rejected answer gets one retry with the
reason. Model, tokens, seconds and attempts go into the output's `_run`, which `extract --load` records in `runs`."""
import json
import os
import re
import subprocess
import tempfile
import time

from .extract import PROMPT_VERSION, Invalid, resolve, validate_output
from .store import ROOT

PROMPT = ROOT / "agents" / "prompts" / f"{PROMPT_VERSION}.md"
MODEL = "claude-opus-5-5"  # pinned, so a rerun reads with the same model; needs Claude Code 2.1.280 or later
CLI = os.environ.get("LEDGER_CLAUDE", "claude")  # path to a newer claude when the installed one is too old
# Only the basics: the desktop app's session variables route requests to its own token, not the user's login.
ENV = {k: os.environ[k] for k in ("HOME", "PATH", "USER", "LANG") if k in os.environ}
CMD = [CLI, "-p", "--output-format", "json", "--tools", "", "--model", MODEL, "--setting-sources", "project",
       "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"]


class AgentUnavailable(RuntimeError):
    """claude -p can't run at all (not logged in, not installed): stop, don't record per-filing failures."""


def _ask(text: str) -> tuple[str, dict]:
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory() as cwd:  # an empty folder: no project instructions leak into the prompt
        try:
            p = subprocess.run(CMD, input=text, capture_output=True, text=True, env=ENV, cwd=cwd, timeout=1200)
        except FileNotFoundError as e:
            raise AgentUnavailable("the claude command is not installed") from e
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise AgentUnavailable(f"claude -p gave no JSON: {(p.stderr or p.stdout)[:300]}") from e
    if d.get("is_error"):
        raise AgentUnavailable(f"claude -p failed: {str(d.get('result'))[:300]}")
    u = d.get("usage", {})
    used = d.get("modelUsage", {})
    return d.get("result", ""), {"model": max(used, key=lambda k: used[k].get("outputTokens", 0)) if used else MODEL, "seconds": round(time.monotonic() - t0, 1),
                                 "input_tokens": u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
                                 "output_tokens": u.get("output_tokens", 0)}


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)  # the object, without any code fence or sentence around it
    if not m:
        raise Invalid("the answer has no JSON object")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise Invalid(f"the JSON doesn't parse: {e}") from e


def extract(task: str, parsed: dict) -> dict:
    """Returns a valid output with `_run`, or raises Invalid with the last reason after one retry."""
    base = f"{PROMPT.read_text()}\n\n---\n\n{task}\n\nReply with the JSON object only."
    run, reason = {"model": None, "seconds": 0.0, "input_tokens": 0, "output_tokens": 0, "attempts": 0}, None
    for _ in range(2):
        text, m = _ask(base if not reason else f"{base}\n\nYour previous answer was rejected: {reason}\nFix that and reply with the JSON object only.")
        run = {**run, "model": m["model"], "attempts": run["attempts"] + 1, **{k: round(run[k] + m[k], 1) for k in ("seconds", "input_tokens", "output_tokens")}}
        try:
            obj = _json(text)
            validate_output(obj, parsed["accession"])
            bad = []
            for i, v in enumerate(obj["values"]):
                try:
                    resolve(v, parsed)
                except Invalid as e:
                    bad.append(f"values[{i}] ({v['field']} {v['column_label']}): {e.reason}")
            if bad:
                raise Invalid("these citations don't match the tables: " + "; ".join(bad[:10]))
            return {**obj, "_run": run}
        except Invalid as e:
            reason = e.reason
    raise Invalid(f"{reason} (after {run['attempts']} attempts)")
