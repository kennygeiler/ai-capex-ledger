"""python -m ledger app [--port 3610]   ->  DATAHQ on http://127.0.0.1:3610"""
import argparse

from ..app import serve


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger app")
    ap.add_argument("--port", type=int, default=3610)
    serve(ap.parse_args(argv).port)
    return 0
