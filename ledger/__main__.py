"""Capex Ledger command line: python -m ledger <command>.

Commands are filled in ticket by ticket (see docs/TICKETS.md); unfinished ones say so and exit non-zero.
"""
import argparse
import sys

COMMANDS = {
    "reference": "Pull XBRL from EDGAR and build the reference set (today's pipeline).",
    "ingest": "List MVP filings, fetch primary documents, parse statement tables.",
    "extract": "Pack extraction tasks and collect agent outputs.",
    "reconcile": "Line up agent, XBRL and derived values and label every disagreement.",
    "rules": "Run the rule registry and write exceptions.",
    "review": "Work the exception queue and record decisions.",
    "score": "Score against XBRL and the golden set, with 95%% intervals.",
    "release": "Build a versioned release (refuses while any gate fails).",
    "signoff": "Record who signed a release.",
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m ledger", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", metavar="command")
    for name, help_ in COMMANDS.items():
        sub.add_parser(name, help=help_, add_help=False)
    args, rest = p.parse_known_args(argv)
    if not args.cmd:
        p.print_help()
        return 0
    if args.cmd == "reference":
        from .reference.run import main as run
        sys.argv = ["ledger reference", *rest]
        run()
        return 0
    import importlib
    try:
        mod = importlib.import_module(f".cli.{args.cmd}", __package__)
    except ModuleNotFoundError:
        print(f"'{args.cmd}' is not built yet. See docs/TICKETS.md.", file=sys.stderr)
        return 2
    return mod.main(rest) or 0


if __name__ == "__main__":
    sys.exit(main())
