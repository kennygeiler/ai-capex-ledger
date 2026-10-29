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

from . import agents
from .extract import Invalid, resolve, validate_output

CLI = os.environ.get("LEDGER_CLAUDE", "claude")  # path to a newer claude when the installed one is too old
# Only the basics: the desktop app's session variables route requests to its own token, not the user's login.
ENV = {k: os.environ[k] for k in ("HOME", "PATH", "USER", "LANG") if k in os.environ}


def model(agent_id: str = "reader") -> str:
    """Pinned in agents/agents.json, read at call time, so a rerun uses what the file says now."""
    return agents.load()[agent_id]["llm"]["model"]


def _cmd(m: str) -> list[str]:
    return [CLI, "-p", "--output-format", "json", "--tools", "", "--model", m, "--setting-sources", "project",
            "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"]


class AgentUnavailable(RuntimeError):
    """claude -p can't run at all (not logged in, not installed): stop, don't record per-filing failures."""


def _ask(text: str, m: str) -> tuple[str, dict]:
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory() as cwd:  # an empty folder: no project instructions leak into the prompt
        try:
            p = subprocess.run(_cmd(m), input=text, capture_output=True, text=True, env=ENV, cwd=cwd, timeout=1200)
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
    return d.get("result", ""), {"model": max(used, key=lambda k: used[k].get("outputTokens", 0)) if used else m, "seconds": round(time.monotonic() - t0, 1),
                                 "input_tokens": u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
                                 "output_tokens": u.get("output_tokens", 0)}


def _json(text: str) -> dict:
    start = text.find("{")  # the first object, without any code fence or sentence around it, or anything after it
    if start < 0:
        raise Invalid("the answer has no JSON object")
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
        return obj
    except json.JSONDecodeError as e:
        raise Invalid(f"the JSON doesn't parse: {e}") from e


def ask(agent_id: str, task: str, check) -> dict:
    """Run one task on the named agent and return a valid output with `_run`, or raise Invalid with the last reason
    after one retry. `check(obj)` raises Invalid when the answer breaks its contract."""
    pv, m = agents.load()[agent_id]["prompt"], model(agent_id)
    base = f"{agents.prompt_text(pv)}\n\n---\n\n{task}\n\nReply with the JSON object only."
    run, reason = {"model": None, "seconds": 0.0, "input_tokens": 0, "output_tokens": 0, "attempts": 0}, None
    for _ in range(2):
        text, u = _ask(base if not reason else f"{base}\n\nYour previous answer was rejected: {reason}\nFix that and reply with the JSON object only.", m)
        run = {**run, "model": u["model"], "attempts": run["attempts"] + 1, **{k: round(run[k] + u[k], 1) for k in ("seconds", "input_tokens", "output_tokens")}}
        try:
            obj = _json(text)
            check(obj)
            return {**obj, "_run": run}
        except Invalid as e:
            reason = e.reason
    raise Invalid(f"{reason} (after {run['attempts']} attempts)")


def extract(task: str, parsed: dict) -> dict:
    """The Reader: statement cells, every citation resolved against the parsed filing."""
    def check(obj):
        validate_output(obj, parsed["accession"])
        bad = []
        for i, v in enumerate(obj["values"]):
            try:
                resolve(v, parsed)
            except Invalid as e:
                bad.append(f"values[{i}] ({v['field']} {v['column_label']}): {e.reason}")
        if bad:
            raise Invalid("these citations don't match the tables: " + "; ".join(bad[:10]))
    return ask("reader", task, check)
