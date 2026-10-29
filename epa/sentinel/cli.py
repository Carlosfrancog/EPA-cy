"""Local verifier CLI: no publication, no signature claims."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from epa.sentinel.policy import Verdict, load_and_verify


def main() -> int:
    parser = argparse.ArgumentParser(prog="epa-sentinel")
    subs = parser.add_subparsers(dest="cmd", required=True)
    verify = subs.add_parser("verify")
    verify.add_argument("--manifest", required=True, type=Path)
    verify.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    decision = load_and_verify(args.manifest, args.root)
    print(json.dumps({"verdict": decision.verdict.value, "reasons": decision.reasons}, ensure_ascii=False))
    return 0 if decision.verdict == Verdict.PERMIT else 1


if __name__ == "__main__":
    raise SystemExit(main())
