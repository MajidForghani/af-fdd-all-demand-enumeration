from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("inputs",type=Path,nargs="+")
    parser.add_argument("--output",type=Path,default=Path("study/results/summary.json")); args=parser.parse_args()
    rows=[]
    for path in args.inputs:
        with path.open(newline="",encoding="utf-8") as handle: rows.extend(csv.DictReader(handle))
    grouped=defaultdict(list)
    for row in rows: grouped[(row["instance_id"],row["algorithm"])].append(row)
    medians={}; digests=defaultdict(dict)
    for (instance,algorithm), values in grouped.items():
        ok=[v for v in values if v["status"]=="ok"]
        if ok:
            medians[(instance,algorithm)]=statistics.median(float(v["wall_seconds"]) for v in ok)
            digests[instance][algorithm]=ok[0]["digest"]
    algorithms=sorted({r["algorithm"] for r in rows}); summary={}
    for algorithm in algorithms:
        times=[value for (instance,a),value in medians.items() if a==algorithm]
        summary[algorithm]={"solved_instances":len(times),"median_seconds":statistics.median(times) if times else None,
                            "geometric_mean_seconds":math.exp(sum(math.log(max(x,1e-12)) for x in times)/len(times)) if times else None}
    disagreements={instance:values for instance,values in digests.items() if len(set(values.values()))>1}
    common=sorted(set.intersection(*[{i for i,a in medians if a==algorithm} for algorithm in algorithms])) if algorithms else []
    profile=[]
    for tau in (1,1.25,1.5,2,3,5,10):
        for algorithm in algorithms:
            solved=sum(medians[(i,algorithm)] <= tau*min(medians[(i,a)] for a in algorithms) for i in common)
            profile.append({"tau":tau,"algorithm":algorithm,"fraction":solved/len(common) if common else 0})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with (args.output.parent/"performance_profile.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=["tau","algorithm","fraction"]); writer.writeheader(); writer.writerows(profile)
    with (args.output.parent/"instance_medians.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=["instance_id","algorithm","median_wall_seconds"]); writer.writeheader()
        for (instance,algorithm),value in sorted(medians.items()): writer.writerow({"instance_id":instance,"algorithm":algorithm,"median_wall_seconds":value})
    payload={"algorithms":summary,"common_solved_instances":len(common),
             "digest_disagreements":disagreements,"rows":len(rows)}
    args.output.write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print(json.dumps(payload,indent=2))


if __name__ == "__main__": main()
