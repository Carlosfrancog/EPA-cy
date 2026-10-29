"""EPA Ledger local CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from epa.ledger.journal import read_verified


def main() -> int:
    parser = argparse.ArgumentParser(prog="epa-ledger")
    p = parser.add_subparsers(dest="cmd", required=True)
    verify = p.add_parser("verify")
    verify.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    try:
        events = read_verified(args.journal)
    except (ValueError, OSError, UnicodeError) as exc:
        print(json.dumps({"status": "INVALID", "reason": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "CONSISTENT_LOCAL_CHAIN", "events": len(events)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
