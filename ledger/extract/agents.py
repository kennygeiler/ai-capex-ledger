"""The named agents: every place an LLM makes a decision, with its model and prompt, in agents/agents.json.

A prompt is never edited in place: a change is saved as the next version (statements@v3), so every past output still
points at the exact text that produced it. Saving and switching on are two separate steps by a person, each logged
with who did it; the model change is logged the same way."""
import json
import re
from datetime import datetime, timezone

from ..core.store import ROOT

CONFIG = ROOT / "agents" / "agents.json"
PROMPTS = ROOT / "agents" / "prompts"


def load() -> dict:
    return json.loads(CONFIG.read_text())


def _save(cfg: dict) -> None:
    CONFIG.write_text(json.dumps(cfg, indent=1) + "\n")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def versions(agent_id: str) -> list[str]:
    """Every saved version of the agent's prompt family, oldest first."""
    family = load()[agent_id]["prompt"].split("@")[0]
    return sorted((p.stem for p in PROMPTS.glob(f"{family}@v*.md")), key=lambda v: int(v.split("@v")[1]))


def prompt_text(version: str) -> str:
    return (PROMPTS / f"{version}.md").read_text()


def charter(agent_id: str) -> list[dict]:
    """The agent's charter (agents/charters/<id>.md, T48) as blocks the page can show without a markdown library:
    {"kind": "heading"|"paragraph", "text"}. Split on blank lines; a line starting with '#' is a heading."""
    path = ROOT / load()[agent_id].get("charter", f"agents/charters/{agent_id}.md")
    if not path.exists():
        return []
    out = []
    for block in re.split(r"\n\s*\n", path.read_text().strip()):
        text = " ".join(line.strip() for line in block.splitlines()).strip()
        if not text:
            continue
        if text.startswith("#"):
            out.append({"kind": "heading", "text": text.lstrip("#").strip()})
        else:
            out.append({"kind": "paragraph", "text": text})
    return out


def _person(by: str) -> None:
    """F18: an agent change is written under a name on config.PEOPLE (status.is_person), like every other write; 400 otherwise."""
    from ..core.status import is_person
    if not is_person(by):
        raise ValueError(f"{str(by or '').strip()!r} is not on config.PEOPLE, the people who may change an agent")


def save_prompt(agent_id: str, text: str, by: str, note: str) -> str:
    """Save `text` as the next version. It is not in use until `use_prompt`: a person switches it on, on purpose."""
    if not text.strip() or not by.strip() or not note.strip():
        raise ValueError("a prompt change needs the text, who made it and why")
    _person(by)
    cfg = load()
    a = cfg[agent_id]
    family, last = a["prompt"].split("@")[0], versions(agent_id)[-1]
    new = f"{family}@v{int(last.split('@v')[1]) + 1}"
    # The prompt names its own version (the agent copies it into its output), so the copy carries the new name.
    text = re.sub(rf"\b{re.escape(family)}@v\d+\b", new, text)
    (PROMPTS / f"{new}.md").write_text(text if text.endswith("\n") else text + "\n")
    a["history"].append({"at": _now(), "by": by, "change": f"{new} saved, not in use: {note}"})
    _save(cfg)
    return new


def use_prompt(agent_id: str, version: str, by: str) -> None:
    _person(by)
    if version not in versions(agent_id):
        raise ValueError(f"no prompt {version}")
    cfg = load()
    cfg[agent_id]["prompt"] = version
    cfg[agent_id]["history"].append({"at": _now(), "by": by, "change": f"switched to {version}"})
    _save(cfg)

def set_model(agent_id: str, model: str, by: str) -> None:
    _person(by)
    if not re.fullmatch(r"[a-z0-9][a-z0-9.\-]{2,60}", model):
        raise ValueError("a model id looks like claude-opus-5-5")
    cfg = load()
    cfg[agent_id]["llm"]["model"] = model
    cfg[agent_id]["history"].append({"at": _now(), "by": by, "change": f"model {model}"})
    _save(cfg)
