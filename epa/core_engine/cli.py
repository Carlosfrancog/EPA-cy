"""Run a documented synthetic baseline, writing a JSON report only."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from epa.core_engine.experiment import run

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",required=True,type=Path)
    parser.add_argument("--seed",type=int,default=20261029)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=run(args.dataset,args.seed)
    content=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        if args.output.exists():
            parser.error("output already exists (immutable evidence)")
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(content,encoding="utf-8")
    else:
        print(content)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
