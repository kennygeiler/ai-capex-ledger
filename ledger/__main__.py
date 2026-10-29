"""Capex Ledger command line: python -m ledger <command> (each takes --stage N or --ticker X Y; see --help)."""
import argparse
import importlib
import sys

COMMANDS = {
    "run": "One command from tickers to their validation page: every step below, then the scorecard.",
    "watch": "Ask the SEC for 10-Ks the ledger hasn't read (data/watch.json); --run reads them.",
    "ingest": "List 10-Ks, fetch and parse them, locate the statements, load the XBRL answer key.",
    "extract": "Pack agent tasks, run the agent headless (--run), load and check its citations (--load).",
    "reconcile": "Build fiscal-year values and label each against the XBRL answer key.",
    "aispend": "Read what each 10-K's MD&A says about AI's part of capex and opex (--run), check every quote and load it (--load).",
    "rules": "Run the rule registry and write exceptions.",
    "faults": "Corrupt real extractions one at a time and report what catches each fault.",
    "evidence": "Re-read every cited cell on the rendered 10-K and screenshot it, boxed.",
    "report": "Write the validation page (reports/<name>-validation.html).",
    "review": "List open items and record decisions.",
    "release": "Build a versioned release (refuses while any gate fails).",
    "signoff": "Record who signed a release.",
    "app": "DATAHQ web app: dashboard, each company's pipeline, the agents, and an outputs explorer (http://127.0.0.1:3610).",
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m ledger", description=__doc__)
    sub = p.add_subparsers(dest="cmd", metavar="command")
    for name, help_ in COMMANDS.items():
        sub.add_parser(name, help=help_, add_help=False)
    args, rest = p.parse_known_args(argv)
    if not args.cmd:
        p.print_help()
        return 0
    return importlib.import_module(f".cli.{args.cmd}", __package__).main(rest) or 0


if __name__ == "__main__":
    sys.exit(main())
