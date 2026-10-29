"""The ledger's pipeline as an Airflow DAG: one task per `ledger` step, in the order `ledger run` uses, on stage 3.

A thin wrapper, nothing more: each task is the same command a person would type, so the pipeline, its caching and
its logging (`runs`, `data/jobs/progress.json`) stay in the ledger. Airflow adds the schedule, retries and a view of
which step is running. Point Airflow at this folder (AIRFLOW__CORE__DAGS_FOLDER=airflow/dags) and set
LEDGER_CLAUDE in Airflow's environment so the agents run on the subscription."""
import os
import sys
from datetime import datetime
from pathlib import Path

try:  # Airflow 3
    from airflow.sdk import DAG
    from airflow.providers.standard.operators.bash import BashOperator
except ImportError:  # Airflow 2
    from airflow import DAG
    from airflow.operators.bash import BashOperator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ledger.steps import STEPS  # noqa: E402  the one list of steps, shared with `ledger run` and DATAHQ

with DAG(dag_id="capex_ledger", description="10-Ks to signed values: every ledger step on stage 3",
         schedule="@daily", start_date=datetime(2026, 10, 29), catchup=False, max_active_runs=1,
         default_args={"retries": 0}, tags=["capex-ledger"]) as dag:
    prev = None
    for i, (cmd, extra, label) in enumerate(STEPS, 1):
        task = BashOperator(task_id=f"{i:02d}_{cmd}{'_' + extra[0].strip('-') if extra else ''}", doc_md=label, cwd=str(ROOT),
                            bash_command=f"uv run python -m ledger {cmd} {' '.join(extra)} --stage 3",
                            env={**os.environ, "LEDGER_CLAUDE": os.environ.get("LEDGER_CLAUDE", "claude")}, append_env=True)
        if prev is not None:
            prev >> task
        prev = task
