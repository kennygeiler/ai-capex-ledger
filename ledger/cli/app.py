"""python -m ledger app [--port 3610] [--host 0.0.0.0]   ->  DATAHQ on http://127.0.0.1:3610

LEDGER_READONLY=1 serves a read-only copy (a hosted DATAHQ): every page reads, no POST lands. PORT, when set, wins over --port."""
import argparse
import os

from ..app import serve


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger app")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 3610)))
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args(argv)
    serve(a.port, a.host)
    return 0
