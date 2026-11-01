"""python -m ledger resolutions migrate-keys [--dry-run] [--log PATH] [--archive PATH]

T62: before it, app.flow() keyed a queue item kind|ticker|where (`where` the display string "field period"), so two findings
on one field and year shared a key and resolving one un-resolved the other. The key is now resolutions.key_for(), from the
item's fields. This appends every legacy-keyed line of decisions/resolutions.jsonl again under the one queue item that
carries its legacy key today (`migrated_from` names the old key; id, hash, state, reason, by, at untouched), copies the
lines that map to no item or to several into decisions/archive/resolutions-keys-<date>.jsonl behind a note, and removes
nothing. Prints migrated / archived / untouched; exit 0."""
import argparse
from pathlib import Path

from .. import resolutions


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger resolutions")
    ap.add_argument("what", choices=["migrate-keys"])
    ap.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    ap.add_argument("--log", type=Path, default=None, help="another log than decisions/resolutions.jsonl (tests)")
    ap.add_argument("--archive", type=Path, default=None, help="another archive file than decisions/archive/resolutions-keys-<date>.jsonl")
    a = ap.parse_args(argv)
    from ..app import _flow
    lines = resolutions.load(a.log)
    plan = resolutions.migrate_keys(lines, lambda t: _flow(t)["queue"])
    for r in plan["migrated"]:
        print(f"migrate  {r['migrated_from']}  ->  {r['key']}  ({r['state']}, by {r['by']}, hash {'current' if r['current'] else 'EXPIRED'})")
    for r in plan["archived"]:
        print(f"archive  {r['key']}  ({r['state']}, by {r['by']}): {r['note']}")
    if not a.dry_run:
        resolutions.write_migration(plan, a.log, a.archive)
    print(f"{'would migrate' if a.dry_run else 'migrated'} {len(plan['migrated'])}, archived {len(plan['archived'])}, untouched {len(plan['untouched'])} of {len(lines)} lines")
    return 0
