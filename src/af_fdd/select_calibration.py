from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description="Select whole replications from every synthetic design cell")
    parser.add_argument("source",type=Path); parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--replications",type=int,default=5); args=parser.parse_args()
    selected=[]
    with args.source.open(encoding="utf-8") as handle:
        for line in handle:
            record=json.loads(line)
            if int(record["replication"]) < args.replications: selected.append(record)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open("w",encoding="utf-8") as handle:
        for record in selected: handle.write(json.dumps(record,sort_keys=True,separators=(",",":"))+"\n")
    print(f"selected {len(selected)} instances")


if __name__ == "__main__": main()
