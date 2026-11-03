"""Tests run offline by default (LEDGER_OFFLINE=1, ledger/ingest/edgar.py): SEC reads come from data/raw whatever their
age and anything uncached raises Offline, so no SEC_USER_AGENT is needed. `ledger test --online` sets it to 0."""
import os

os.environ.setdefault("LEDGER_OFFLINE", "1")
