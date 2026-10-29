"""What each 10-K says, in words, about how much of its capex and opex goes to AI.

Companies rarely book a line called "AI capex". The MD&A (Item 7) says things like "capital expenditures of $115 to
$135 billion in 2026 to support our AI efforts and core business" or "the majority of our capex supports AI". So the
output is graded, not one number: an explicit amount, an explicit share, a qualitative word, or nothing, each pointing
at the sentence it came from. Code checks the sentence is really in the filing; a person judges only what is unclear.

Table A, `ai_statements`: every statement the agent read, verbatim quote and all. Table B, `ai_spend`: one row per
company, field, fiscal year and kind (the year reported, or an outlook), the most specific statement, with an AI
dollar amount only where the filing supports one."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import agents
from .store import ROOT

TEXT = ROOT / "data" / "text"
TASKS = ROOT / "data" / "aispend" / "tasks"
OUTPUTS = ROOT / "data" / "aispend" / "outputs"
FIELDS = ("capex", "opex")
KINDS = ("actual", "outlook")
SCOPES = ("ai", "total")
CLASSES = ("explicit_amount", "explicit_share", "qualitative")

CAPEX = re.compile(r"capital expenditure|capital spending|purchases? of property|property and equipment|technical infrastructure|data ?cent(er|re)|servers?|GPU", re.I)
OPEX = re.compile(r"research and development|R&D|operating expenses|headcount|compensation|cost of revenue", re.I)
AI = re.compile(r"\bAI\b|artificial intelligence|machine learning|generative|accelerated computing|large language|\bLLM", re.I)
OUTLOOK = re.compile(r"\b(expect|anticipate|plan|intend|estimate|forecast|guidance)", re.I)
LIQUIDITY = re.compile(r"liquidity and capital resources", re.I)


def prompt_version() -> str:
    return agents.load()["ai_reader"]["prompt"]


def prompt_versions() -> tuple[str, ...]:
    return tuple(agents.versions("ai_reader"))


# ── text ───────────────────────────────────────────────────────────────────────────────────────────────────────────
def mdna_path(cik: int, accession: str) -> Path:
    return TEXT / f"{cik:010d}" / f"{accession}.mdna.txt"


def mdna_text(doc: dict) -> str:
    """Item 7 of the filing as plain text, through edgartools, cached on disk. Empty when the filing has no Item 7
    (a 10-K/A that amends Part III only)."""
    p = mdna_path(doc["cik"], doc["accession"])
    if p.exists():
        return p.read_text()
    from edgar import Filing, set_identity  # only the text step needs edgartools
    from .ingest.edgar import user_agent
    set_identity(user_agent())
    k = Filing(cik=doc["cik"], company=doc["ticker"], form=doc["form"], filing_date=doc["filed"], accession_no=doc["accession"]).obj()
    try:
        text = (k["Item 7"] if k is not None else "") or ""
    except (KeyError, TypeError):
        text = ""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return text


def passages(text: str, limit: int = 30) -> list[str]:
    """Paragraphs worth the agent's time, most relevant first: spend words next to AI words; then capex with an
    outlook word; then capex inside Liquidity and Capital Resources. Whole paragraphs, so a quote can be checked."""
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    paras = [p for p in paras if len(p) > 60]
    liq = next((i for i, p in enumerate(paras) if LIQUIDITY.search(p) and len(p) < 120), None)
    def rank(i, p):
        spend = CAPEX.search(p) or OPEX.search(p)
        if spend and AI.search(p):
            return 0
        if CAPEX.search(p) and OUTLOOK.search(p):
            return 1
        if liq is not None and i > liq and i - liq < 60 and CAPEX.search(p):
            return 2
        return None
    ranked = sorted(((r, i, p) for i, p in enumerate(paras) if (r := rank(i, p)) is not None))
    return [p for _, _, p in sorted(ranked[:limit], key=lambda x: x[1])]


def make_task(doc: dict, ps: list[str]) -> str:
    head = (f"# Task: {doc['ticker']} {doc['form']} for the fiscal year ended {doc['period']}\n\n"
            f"Accession: {doc['accession']}\nPrompt version: {prompt_version()}\n\n"
            f"The company's fiscal year that this filing reports ended {doc['period']}. Passages from Item 7 (MD&A), in filing order:\n")
    body = "\n\n".join(f"[p{i:02d}] {p}" for i, p in enumerate(ps, 1)) or "(no passage in this filing mentions AI together with capital or operating spending)"
    return head + "\n" + body + "\n"


def write_tasks(docs: list[dict]) -> list[Path]:
    TASKS.mkdir(parents=True, exist_ok=True)
    out = []
    for d in docs:
        path = TASKS / f"{d['accession']}.md"
        path.write_text(make_task(d, passages(mdna_text(d))))
        out.append(path)
    return out


def task_passages(task_text: str) -> dict[str, str]:
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"^\[(p\d\d)\] (.*)$", task_text, re.M)}


# ── output contract ────────────────────────────────────────────────────────────────────────────────────────────────
@dataclass
class Invalid(Exception):
    reason: str


def _norm(s: str) -> str:
    return re.sub(r"[\s ]+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


def validate_output(obj: dict, accession: str, ps: dict[str, str]) -> None:
    """The output contract (agents/schemas/aispend@v1.json) plus the one check that matters: every quote is really in
    the passage it cites. Raises Invalid(reason)."""
    if not isinstance(obj, dict):
        raise Invalid("output is not a JSON object")
    for k in ("accession", "prompt_version", "statements", "none_found"):
        if k not in obj:
            raise Invalid(f"missing '{k}'")
    if obj["accession"] != accession:
        raise Invalid(f"accession {obj['accession']!r} is not the task's {accession!r}")
    if obj["prompt_version"] not in (known := prompt_versions()):
        raise Invalid(f"prompt_version {obj['prompt_version']!r}, expected one of {known}")
    if not isinstance(obj["statements"], list) or not isinstance(obj["none_found"], list):
        raise Invalid("'statements' and 'none_found' must be lists")
    req = ("field", "fiscal_year", "kind", "scope", "class", "quote", "passage", "confidence")
    for i, s in enumerate(obj["statements"]):
        missing = [k for k in req if k not in s]
        if missing:
            raise Invalid(f"statements[{i}] missing {missing}")
        for k, allowed in (("field", FIELDS), ("kind", KINDS), ("scope", SCOPES), ("class", CLASSES)):
            if s[k] not in allowed:
                raise Invalid(f"statements[{i}].{k} {s[k]!r} is not one of {allowed}")
        if s["fiscal_year"] is not None and (not isinstance(s["fiscal_year"], int) or not 2015 <= s["fiscal_year"] <= 2035):
            raise Invalid(f"statements[{i}].fiscal_year {s['fiscal_year']!r} is not a year or null")
        if s["passage"] not in ps:
            raise Invalid(f"statements[{i}].passage {s['passage']!r} is not in the task")
        if not isinstance(s["quote"], str) or len(s["quote"]) < 20 or _norm(s["quote"]) not in _norm(ps[s["passage"]]):
            raise Invalid(f"statements[{i}].quote is not a verbatim sentence of passage {s['passage']}: {str(s['quote'])[:80]!r}")
        if s["class"] == "explicit_amount":
            lo, hi = s.get("amount_low"), s.get("amount_high")
            if not (isinstance(lo, int) and isinstance(hi, int) and not isinstance(lo, bool) and 0 < lo <= hi):
                raise Invalid(f"statements[{i}]: explicit_amount needs integer dollars amount_low <= amount_high")
        if s["class"] == "explicit_share":
            sh = s.get("share")
            if not (isinstance(sh, (int, float)) and not isinstance(sh, bool) and 0 < sh <= 1):
                raise Invalid(f"statements[{i}]: explicit_share needs share between 0 and 1")
        if not (isinstance(s["confidence"], (int, float)) and 0 <= s["confidence"] <= 1):
            raise Invalid(f"statements[{i}].confidence must be between 0 and 1")
    for i, n in enumerate(obj["none_found"]):
        if not isinstance(n, dict) or n.get("field") not in FIELDS or "reason" not in n:
            raise Invalid(f"none_found[{i}] needs a field (capex or opex) and a reason")


def period_of(s: dict, reported_year: int) -> tuple[str, str | None]:
    """The fiscal year a statement speaks to, and a note when code had to assign it: a sentence with no year is about
    the reported year (actual) or the one after it (outlook)."""
    if s["fiscal_year"] is not None:
        return f"FY{s['fiscal_year']}", None
    y = reported_year + (1 if s["kind"] == "outlook" else 0)
    return f"FY{y}", f"no year in the sentence: FY{y} assigned as the filing's reported year{' plus one' if s['kind'] == 'outlook' else ''}"


# ── table B ────────────────────────────────────────────────────────────────────────────────────────────────────────
RANK = {("ai", "explicit_amount"): 0, ("ai", "explicit_share"): 1, ("total", "explicit_amount"): 2, ("total", "explicit_share"): 3,
        ("ai", "qualitative"): 4, ("total", "qualitative"): 5}


def spend_rows(ticker: str, statements: list[dict], values: dict, filed: dict) -> list[dict]:
    """One row per (field, period, kind) from the newest filing that speaks to it, keeping the most specific statement.
    values: (field, period) -> our released value, for turning a share into dollars. filed: accession -> filing date."""
    by = {}
    for s in statements:
        by.setdefault((s["field"], s["period"], s["kind"]), []).append(s)
    out = []
    for (f, period, kind), ss in sorted(by.items()):
        newest = max(filed[s["accession"]] for s in ss)
        ss = sorted((s for s in ss if filed[s["accession"]] == newest), key=lambda s: (RANK[(s["scope"], s["class"])], -s["confidence"]))
        best = ss[0]
        amount = None
        if best["scope"] == "ai" and best["class"] == "explicit_amount":
            amount = (best["amount_low"] + best["amount_high"]) // 2
        elif best["scope"] == "ai" and best["class"] == "explicit_share" and kind == "actual" and values.get((f, period)):
            amount = round(best["share"] * values[(f, period)])
        ids = [s["statement_id"] for s in ss]
        h = hashlib.sha256(json.dumps([best["quote"], best["scope"], best["class"], amount, ids]).encode()).hexdigest()[:16]
        out.append({"ticker": ticker, "field": f, "period": period, "kind": kind, "scope": best["scope"], "class": best["class"],
                    "amount_low": best.get("amount_low"), "amount_high": best.get("amount_high"), "share": best.get("share"),
                    "ai_amount": amount, "quote": best["quote"], "accession": best["accession"], "statement_ids": ",".join(ids), "input_hash": h})
    return out
