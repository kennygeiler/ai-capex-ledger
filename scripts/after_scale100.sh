#!/bin/zsh
# After the 100-company run (scripts/scale100.sh) has finished: switch the theses and attribution@v2 on, add the
# projects step, rerun what depends on them, and run every step for stage 3 so the companies batch 1 missed get
# rules, faults, evidence and the report. Idempotent; agent outputs are cached unless the task changed.
set -e
cd "$(dirname "$0")/.."
export LEDGER_CLAUDE="${LEDGER_CLAUDE:-$CLAUDE_CODE_EXECPATH}"
uv run python - <<'PY'
from ledger.agents import load, use_model, use_prompt, model_versions
cfg = load()["attributor"]
for layer in cfg["models"]:
    newest = model_versions(layer)[-1]
    if cfg["models"][layer] != newest:
        use_model(layer, newest, "Kenny Geiler")
        print("model", layer, "->", newest)
if cfg["prompt"] != "attribution@v2":
    use_prompt("attributor", "attribution@v2", "Kenny Geiler")
    print("prompt attributor -> attribution@v2")
PY
uv run python - <<'PY'
import re
p = "ledger/steps.py"; s = open(p).read()
if '("projects", ["--run"]' not in s:
    s = s.replace('''         ("attribution", ["--run"],''', '''         ("projects", ["--run"], "The Projects reader reads named projects with size and stage from every text"),
         ("projects", ["--load"], "Check every quote; one row per project mention, the newest marked latest"),
         ("attribution", ["--run"],''')
    open(p, "w").write(s); print("projects step added to ledger/steps.py")
PY
uv run python -m ledger attribution --stage 3 --run --rerun
uv run python -m ledger attribution --stage 3 --load
uv run python -m ledger projects --stage 3 --run
uv run python -m ledger projects --stage 3 --load
uv run python -m ledger run --stage 3
echo "##### AFTER DONE $(date -u +%FT%TZ)"
