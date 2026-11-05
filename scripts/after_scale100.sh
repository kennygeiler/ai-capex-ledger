#!/bin/zsh
# After the 100-company run (scripts/scale100.sh) has finished: make sure the projects step is in the pipeline, run it,
# and run every step for stage 3 so the companies batch 1 missed get rules, faults, evidence and the report. Idempotent;
# agent outputs are cached unless the task changed. The attribution steps this script once switched on were removed with
# the inferred AI layer (2ee2e6f); the attributor is retired (agents/charters/), so nothing here runs it.
set -e
cd "$(dirname "$0")/.."
export LEDGER_CLAUDE="${LEDGER_CLAUDE:-$CLAUDE_CODE_EXECPATH}"
uv run python - <<'PY'
from ledger.core import steps  # the pipeline's step list (ledger/core/steps.py)
if not any(s[0] == "projects" for s in steps.STEPS):
    raise SystemExit("ledger/core/steps.py has no projects step: add it there (projects --run, projects --load) before this script")
PY
uv run python -m ledger projects --stage 3 --run
uv run python -m ledger projects --stage 3 --load
uv run python -m ledger run --stage 3
uv run python -m ledger cost --stage 3
echo "##### AFTER DONE $(date -u +%FT%TZ)"
