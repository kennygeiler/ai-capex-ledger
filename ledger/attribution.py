"""AI's part of each company's capex, opex and revenue, attributed by an agent that reads the money-flow model for the
company's industry (agents/models/<industry>@vN.md) and the company's cleaned data, and must show its inputs.

The data pack is everything the ledger holds for the company: values, facts from the notes, and what the company
said (ai_spend statements). Every number the agent gives rests on pack items it names by id; code looks the items
up and recomputes the number by the method's arithmetic. Edit the model, rerun only the attributor, and the dataset
changes; nothing is re-read from filings."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import agents
from .config import industry
from .store import ROOT

MODELS = ROOT / "agents" / "models"
TASKS = ROOT / "data" / "attribution" / "tasks"
OUTPUTS = ROOT / "data" / "attribution" / "outputs"
FIELDS = ("capex", "opex", "revenue")  # capex allocation, opex, revenue exposure (docs/THESIS.md)
KINDS = ("actual", "outlook", "committed")  # spent, planned, committed (docs/THESIS.md)
METHODS = ("stated_share", "stated_amount", "segment", "ppe_category", "whole_business", "commitment", "qualitative", "none")
NUMERIC = ("stated_share", "stated_amount", "segment", "ppe_category", "whole_business", "commitment")


def prompt_version() -> str:
    return agents.load()["attributor"]["prompt"]


def prompt_versions() -> tuple[str, ...]:
    return tuple(agents.versions("attributor"))


DRYRUN = ROOT / "data" / "attribution" / "dryrun"


def model_for(ticker: str, override: str | None = None) -> str:
    """The model version in use for the company's industry, from agents/agents.json; or an override of the same
    family (a dry run of a saved version)."""
    if override:
        if override.split("@")[0] != industry(ticker):
            raise ValueError(f"{override} is not a {industry(ticker)} model")
        return override
    return agents.load()["attributor"]["models"][industry(ticker)]


def model_text(name: str) -> str:
    return (MODELS / f"{name}.md").read_text()


# ── the data pack ──────────────────────────────────────────────────────────────────────────────────────────────────
def pack(con, ticker: str) -> dict:
    """Every pack item by id, so the agent can cite it and code can look it up."""
    rows = lambda sql: [dict(zip([c[0] for c in con.execute(sql, [ticker]).description], r)) for r in con.execute(sql, [ticker]).fetchall()]
    items = {}
    for v in rows('select field, period, period_end, value, label from "values" where ticker = ? and value is not null order by field, period'):
        items[f"value:{ticker}|{v['field']}|{v['period']}"] = {"kind": "value", **v}
    for f in rows("select field, dimension, period, period_end, value, label from facts where ticker = ? order by field, dimension, period"):
        items[f"fact:{ticker}|{f['field']}|{f['dimension']}|{f['period']}"] = {"kind": "fact", **f}
    for s in rows("select statement_id, field, period, kind as stmt_kind, scope, class, amount_low, amount_high, share, quote, source, confidence from ai_statements where ticker = ? order by field, period, kind"):
        items[f"stmt:{s['statement_id']}"] = {"kind": "statement", **s}
    return items


def _usd(n) -> str:
    return f"{n:,}" if n is not None else "—"


def render_pack(ticker: str, items: dict) -> str:
    out = ["## Values (released: revenue, capex, opex; whole US dollars)", "", "| id | value | vs SEC data |", "|---|---|---|"]
    out += [f"| `{k}` | {_usd(v['value'])} | {v['label']} |" for k, v in items.items() if v["kind"] == "value"]
    out += ["", "## Facts from the notes (whole US dollars; balances at the year end, flows for the year)", "", "| id | value | vs filing's XBRL |", "|---|---|---|"]
    out += [f"| `{k}` | {_usd(v['value'])} | {v['label']} |" for k, v in items.items() if v["kind"] == "fact"]
    out += ["", "## What the company said (verbatim quotes)", ""]
    for k, s in items.items():
        if s["kind"] == "statement":
            amt = f"{_usd(s['amount_low'])}–{_usd(s['amount_high'])}" if s["amount_low"] is not None else (f"share {s['share']}" if s["share"] is not None else "words only")
            out.append(f"- `{k}` · {s['field']} {s['period']} {s['stmt_kind']} · scope {s['scope']}, {s['class']}, {amt} · from the {s['source'].replace('_', ' ')}: \"{s['quote']}\"")
    return "\n".join(out)


def make_task(ticker: str, items: dict, model: str) -> str:
    head = (f"# Task: attribute {ticker}'s capex, opex and revenue to AI\n\nTicker: {ticker}\nPrompt version: {prompt_version()}\nModel: {model}\n"
            f"Industry: {industry(ticker)}\n\n")
    return head + "# Money-flow model\n\n" + model_text(model) + "\n\n# Data pack\n\n" + render_pack(ticker, items) + "\n"


def write_task(ticker: str, items: dict, override: str | None = None) -> Path:
    d = TASKS if not override else DRYRUN / override / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{ticker}.md"
    p.write_text(make_task(ticker, items, model_for(ticker, override)))
    return p


# ── the contract, with arithmetic ──────────────────────────────────────────────────────────────────────────────────
@dataclass
class Invalid(Exception):
    reason: str


def _tol(items: dict, inputs: list[dict]) -> int:
    """Rounding: half of the coarsest scale among the inputs (a value in millions rounds to the nearest 500k)."""
    return 500_000


def validate_output(obj: dict, ticker: str, items: dict, override: str | None = None) -> None:
    if not isinstance(obj, dict):
        raise Invalid("output is not a JSON object")
    for k in ("ticker", "prompt_version", "model", "rows", "none_found"):
        if k not in obj:
            raise Invalid(f"missing '{k}'")
    if obj["ticker"] != ticker:
        raise Invalid(f"ticker {obj['ticker']!r} is not the task's {ticker!r}")
    if obj["prompt_version"] not in (known := prompt_versions()):
        raise Invalid(f"prompt_version {obj['prompt_version']!r}, expected one of {known}")
    if obj["model"] != model_for(ticker, override):
        raise Invalid(f"model {obj['model']!r} is not the task's {model_for(ticker, override)!r}")
    if not isinstance(obj["rows"], list) or not isinstance(obj["none_found"], list):
        raise Invalid("'rows' and 'none_found' must be lists")
    seen = set()
    for i, r in enumerate(obj["rows"]):
        missing = [k for k in ("field", "period", "kind", "method", "ai_amount", "ai_share", "inputs", "basis", "confidence") if k not in r]
        if missing:
            raise Invalid(f"rows[{i}] missing {missing}")
        if r["field"] not in FIELDS or r["kind"] not in KINDS or r["method"] not in METHODS:
            raise Invalid(f"rows[{i}]: field, kind or method out of range")
        if not re.fullmatch(r"FY\d{4}", str(r["period"])):
            raise Invalid(f"rows[{i}].period {r['period']!r} is not FYyyyy")
        key = (r["field"], r["period"], r["kind"])
        if key in seen:
            raise Invalid(f"rows[{i}]: two rows for {key}")
        seen.add(key)
        if not (isinstance(r["confidence"], (int, float)) and 0 <= r["confidence"] <= 1):
            raise Invalid(f"rows[{i}].confidence must be between 0 and 1")
        if not isinstance(r["inputs"], list) or any(not isinstance(x, dict) or "id" not in x or "value" not in x for x in r["inputs"]):
            raise Invalid(f"rows[{i}].inputs must be a list of {{id, value}}")
        for x in r["inputs"]:
            if x["id"] not in items:
                raise Invalid(f"rows[{i}]: input {x['id']!r} is not in the data pack")
            it = items[x["id"]]
            have = it.get("value") if it["kind"] != "statement" else (it["share"] if it["share"] is not None else ((it["amount_low"] + it["amount_high"]) // 2 if it["amount_low"] is not None else None))
            if have is not None and abs(float(x["value"]) - float(have)) > 1:
                raise Invalid(f"rows[{i}]: input {x['id']} is {have}, not {x['value']}")
        if r["method"] == "commitment" and r["kind"] != "committed" or r["kind"] == "committed" and r["method"] not in ("commitment", "stated_amount", "stated_share", "qualitative", "none"):
            raise Invalid(f"rows[{i}]: the commitment method goes with kind committed, and a committed row uses commitment, a stated figure, or words")
        if r["method"] in NUMERIC:
            _check_arithmetic(r, items, i)
        else:
            if r["ai_amount"] is not None or r["inputs"]:
                raise Invalid(f"rows[{i}]: {r['method']} carries no amount and no inputs")
    for i, n in enumerate(obj["none_found"]):
        if not isinstance(n, dict) or n.get("field") not in FIELDS or "reason" not in n:
            raise Invalid(f"none_found[{i}] needs a field and a reason")


PART_YEAR = re.compile(r"\b(Q[1-4]|[1-4]Q|H[12]|(first|second|third|fourth) (quarter|half)|(first|last) (three|six|nine) months|nine months|six months|three months|quarter)\b", re.I)


def part_year(quote: str) -> str | None:
    """The words that make a stated amount cover part of a year, or None (type 68)."""
    m = PART_YEAR.search(quote or "")
    return m.group(0) if m else None


def _check_arithmetic(r: dict, items: dict, i: int) -> None:
    m, amt, ins = r["method"], r["ai_amount"], r["inputs"]
    if not isinstance(amt, int) or isinstance(amt, bool) or amt < 0:
        raise Invalid(f"rows[{i}]: {m} needs a non-negative integer ai_amount")
    tol = _tol(items, ins)
    kinds = [items[x["id"]]["kind"] for x in ins]
    if m == "stated_amount":
        stmts = [x for x in ins if items[x["id"]]["kind"] == "statement"]
        if len(stmts) != 1 or items[stmts[0]["id"]]["scope"] != "ai" or items[stmts[0]["id"]]["class"] != "explicit_amount":
            raise Invalid(f"rows[{i}]: stated_amount needs exactly one statement input with scope ai and an explicit amount")
        s = items[stmts[0]["id"]]
        if abs(amt - (s["amount_low"] + s["amount_high"]) // 2) > tol:
            raise Invalid(f"rows[{i}]: ai_amount {amt} is not the statement's midpoint {(s['amount_low'] + s['amount_high']) // 2}")
        if r["kind"] == "actual" and part_year(s.get("quote") or ""):  # type 68: a quarter's amount used as the year's actual (Tesla Q1 2024)
            raise Invalid(f"rows[{i}]: the statement covers part of the year ({part_year(s['quote'])}); a part-year amount is not the year's actual. Use qualitative and name the part-year figure in basis.")
    elif m == "stated_share":
        stmts = [x for x in ins if items[x["id"]]["kind"] == "statement"]
        vals = [x for x in ins if items[x["id"]]["kind"] == "value"]
        if len(stmts) != 1 or len(vals) != 1 or items[stmts[0]["id"]]["scope"] != "ai" or items[stmts[0]["id"]]["share"] is None:
            raise Invalid(f"rows[{i}]: stated_share needs one statement with an AI share and one value input")
        want = round(items[stmts[0]["id"]]["share"] * items[vals[0]["id"]]["value"])
        if abs(amt - want) > tol:
            raise Invalid(f"rows[{i}]: ai_amount {amt} ≠ share × value = {want}")
    elif m == "segment":
        facts = [items[x["id"]] for x in ins]
        want = "segment_revenue" if r["field"] == "revenue" else "segment_capex"
        if not facts or any(f["kind"] != "fact" or f["field"] not in ("segment_capex", "segment_revenue") for f in facts):
            raise Invalid(f"rows[{i}]: segment needs {want} fact inputs")
        if r["field"] != "revenue" and any(f["field"] == "segment_revenue" for f in facts):
            raise Invalid(f"rows[{i}]: segment revenue is the seller side, not AI spend")
        if r["field"] == "revenue" and any(f["field"] == "segment_capex" for f in facts):
            raise Invalid(f"rows[{i}]: revenue exposure needs segment_revenue facts, not segment capex")
        if abs(amt - sum(f["value"] for f in facts)) > tol:
            raise Invalid(f"rows[{i}]: ai_amount {amt} ≠ sum of {want} {sum(f['value'] for f in facts)}")
    elif m == "ppe_category":
        facts = [items[x["id"]] for x in ins]
        if len(facts) != 2 or any(f["kind"] != "fact" or f["field"] != "ppe_category" for f in facts) or facts[0]["dimension"] != facts[1]["dimension"]:
            raise Invalid(f"rows[{i}]: ppe_category needs two facts of the same category, newer first")
        if abs(amt - (facts[0]["value"] - facts[1]["value"])) > tol:
            raise Invalid(f"rows[{i}]: ai_amount {amt} ≠ gross(t) − gross(t−1) = {facts[0]['value'] - facts[1]['value']}")
    elif m == "commitment":
        facts = [items[x["id"]] for x in ins]
        if not facts or any(f["kind"] != "fact" or f["field"] not in ("purchase_commitments", "finance_lease_liability") for f in facts):
            raise Invalid(f"rows[{i}]: commitment needs purchase_commitments or finance_lease_liability fact inputs")
        if abs(amt - sum(f["value"] for f in facts)) > tol:
            raise Invalid(f"rows[{i}]: ai_amount {amt} ≠ sum of commitments {sum(f['value'] for f in facts)}")
    elif m == "whole_business":
        vals = [items[x["id"]] for x in ins]
        if len(vals) != 1 or vals[0]["kind"] != "value" or vals[0]["field"] != r["field"] or vals[0]["period"] != r["period"]:
            raise Invalid(f"rows[{i}]: whole_business needs the company's own {r['field']} value for {r['period']} as its one input")
        if abs(amt - vals[0]["value"]) > tol:
            raise Invalid(f"rows[{i}]: ai_amount {amt} ≠ value {vals[0]['value']}")
    ticker = next(iter(ins))["id"].split(":", 1)[1].split("|")[0]
    base = items.get(f"value:{ticker}|{r['field']}|{r['period']}")
    if r["ai_share"] is not None:
        if base is None:
            raise Invalid(f"rows[{i}]: ai_share given but the company has no {r['field']} value for {r['period']}")
        if abs(r["ai_share"] - amt / base["value"]) > 0.02:
            raise Invalid(f"rows[{i}]: ai_share {r['ai_share']} ≠ ai_amount ÷ {r['field']} = {amt / base['value']:.3f}")


# ── table ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def rows_for(ticker: str, obj: dict, model: str, model_sha: str, run_id: str) -> list[dict]:
    out = []
    for r in obj["rows"]:
        ids = [x["id"] for x in r["inputs"]]
        h = hashlib.sha256(json.dumps([r["method"], r["ai_amount"], ids, model_sha]).encode()).hexdigest()[:16]
        out.append({"ticker": ticker, "field": r["field"], "period": r["period"], "kind": r["kind"], "method": r["method"],
                    "ai_amount": r["ai_amount"], "ai_share": None if r["ai_share"] is None else float(r["ai_share"]), "confidence": float(r["confidence"]),
                    "basis": r["basis"], "inputs": ",".join(ids), "model": model, "model_sha256": model_sha, "prompt_version": obj["prompt_version"],
                    "run_id": run_id, "input_hash": h})
    return out
