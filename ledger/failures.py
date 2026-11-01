"""The failure types docs/INGESTION.md logged, as data (taxonomy/failures.yaml, T54).

Each type has a cause class, an origin and the check in code that catches it (a rule id, a guard id, a fault kind) or
`none`, which is itself a finding. `load` refuses a class, origin or check that is not in the vocabulary, so the file
can never name a check that does not exist. `pareto` and `by_check` are what a chart reads."""
from pathlib import Path

import yaml

from .store import ROOT

FILE = ROOT / "taxonomy" / "failures.yaml"
CLASSES = ("units", "period", "scope", "locator", "agent misread", "document error", "pipeline")
ORIGINS = ("agent", "document", "code", "reference")
REQUIRED = ("name", "class", "origin", "check", "source", "by", "at")


def known_checks() -> set[str]:
    """Every id a `check` may name: the rule ids in rules/, the guard ids in proof.GUARDS, the fault kinds in faults.FAULTS."""
    from .faults import FAULTS
    from .proof import GUARDS
    from .rules import load as load_rules
    return {r["id"] for r in load_rules()} | {g["id"] for g in GUARDS} | set(FAULTS)


def load(path: Path = FILE) -> list[dict]:
    """The types as a list sorted by id, each with `id` set, validated against the vocabulary and the ids in code."""
    raw = yaml.safe_load(path.read_text()) or {}
    checks = known_checks()
    out = []
    for key, e in raw.items():
        if not isinstance(key, int) or not isinstance(e, dict):
            raise ValueError(f"failures: type {key!r} must be an integer id with a mapping")
        missing = [k for k in REQUIRED if not e.get(k)]
        if missing:
            raise ValueError(f"failures: type {key} is missing {missing}")
        if e["class"] not in CLASSES:
            raise ValueError(f"failures: type {key} has class {e['class']!r}; one of {list(CLASSES)}")
        if e["origin"] not in ORIGINS:
            raise ValueError(f"failures: type {key} has origin {e['origin']!r}; one of {list(ORIGINS)}")
        if e["check"] != "none" and e["check"] not in checks:
            raise ValueError(f"failures: type {key} names check {e['check']!r}, which is not a rule, guard or fault id in code")
        if e["check"] == "none" and not e.get("check_note"):
            raise ValueError(f"failures: type {key} has check none and no check_note")
        if e.get("count") is None and not e.get("count_note"):
            raise ValueError(f"failures: type {key} has no count and no count_note")
        out.append({"id": key, **e})
    return sorted(out, key=lambda e: e["id"])


def _tally(types: list[dict], key: str) -> list[dict]:
    n = {}
    for t in types:
        n[t[key]] = n.get(t[key], 0) + 1
    return [{key: k, "types": v} for k, v in sorted(n.items(), key=lambda kv: (-kv[1], str(kv[0])))]


def pareto(types: list[dict] | None = None) -> dict:
    """Counts of types by class, by origin and by check (`none` counted as its own bar), largest first; `total` is the number of types."""
    types = load() if types is None else types
    return {"total": len(types), "by_class": _tally(types, "class"), "by_origin": _tally(types, "origin"), "by_check": _tally(types, "check"),
            "none": sum(1 for t in types if t["check"] == "none")}


def by_check(types: list[dict] | None = None) -> dict[str, list[dict]]:
    """{check id or 'none': [types it catches]}, for the chart to list what sits behind each bar."""
    types = load() if types is None else types
    out = {}
    for t in types:
        out.setdefault(t["check"], []).append(t)
    return out
