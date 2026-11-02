"""python -m ledger claims [--check | --deployed]

Writes docs/CLAIMS.md from claims/claims.yaml and claims/findings.jsonl (ledger/claims.py). Run it after every merge: the
file is generated and merges by union (.gitattributes), so a merged copy is stale until regenerated and
tests.test_claims.Doc fails loudly. --check exits 1 when the file is stale; --deployed records the hosted copy's deploy."""
from .. import claims


def main(argv=None) -> int:
    return claims.main(list(argv or []))
