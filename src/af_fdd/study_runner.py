from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil


FIELDS = ["instance_id","collection","algorithm","implementation_version","mode","repetition","status","error_type","error",
          "wall_seconds","process_wall_seconds","worker_wall_seconds","algorithm_seconds",
          "preprocess_seconds","enumerate_seconds","output_seconds","peak_rss_bytes",
          "outputs","digest","binary_paths","diagram_states","frontier_width","candidates","stats_json"]


def read_records(paths: list[Path]):
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip(): yield json.loads(line)


def _tree_rss(process: psutil.Process) -> int:
    total = 0
    # On Windows, very short-lived workers may disappear while psutil is
    # enumerating descendants.  Treat that as zero additional live memory;
    # it is a normal sampling race, not a benchmark failure.
    try:
        items = [process] + process.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        items = [process]
    for item in items:
        try: total += item.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    return total


def one_run(record: dict, algorithm: str, mode: str, repetition: int,
            timeout: float, memory_gib: float, path_limit: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="af_fdd_") as directory:
        record_path=Path(directory)/"instance.json"; record_path.write_text(json.dumps(record),encoding="utf-8")
        command=[sys.executable,"-m","af_fdd.study_worker","--record",str(record_path),
                 "--algorithm",algorithm,"--mode",mode,"--path-limit",str(path_limit)]
        start=time.perf_counter(); child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try: process=psutil.Process(child.pid)
        except psutil.NoSuchProcess: process=None
        peak=0; status=None
        while child.poll() is None:
            if process is not None:
                peak=max(peak,_tree_rss(process))
            elapsed=time.perf_counter()-start
            if elapsed > timeout: status="timeout"
            if memory_gib and peak > memory_gib*(1024**3): status="memory_limit"
            if status:
                if process is not None:
                    try:
                        descendants = process.children(recursive=True)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        descendants = []
                    for descendant in descendants:
                        try: descendant.kill()
                        except psutil.Error: pass
                    try: process.kill()
                    except psutil.Error: pass
                break
            time.sleep(0.02)
        stdout,stderr=child.communicate(); elapsed=time.perf_counter()-start
        base={"instance_id":record["instance_id"],"collection":record["collection"],
              "algorithm":algorithm,"mode":mode,"repetition":repetition,
              "peak_rss_bytes":peak,"wall_seconds":elapsed,
              "process_wall_seconds":elapsed}
        if status:
            return {**base,"status":status,"error":stderr[-1000:]}
        try:
            payload=json.loads(stdout.strip().splitlines()[-1])
        except Exception:
            return {**base,"status":"crash","error":stderr[-1000:] or stdout[-1000:]}
        payload.pop("worker_peak_rss_bytes",None)
        worker_wall = payload.pop("wall_seconds", None)
        return {**base,**payload,"wall_seconds":elapsed,"process_wall_seconds":elapsed,
                "worker_wall_seconds":worker_wall,"peak_rss_bytes":peak}


def main():
    parser=argparse.ArgumentParser(description="Resumable, process-isolated AF-FDD benchmark")
    parser.add_argument("instances",type=Path,nargs="+",help="JSONL corpus files")
    parser.add_argument("--output",type=Path,default=Path("study/results/raw.csv"))
    parser.add_argument("--algorithms",nargs="+",default=["AF-FDD","Bai-2021","Yeh-2024"])
    parser.add_argument("--mode",choices=["enumerate","count"],default="enumerate")
    parser.add_argument("--repetitions",type=int,default=3); parser.add_argument("--timeout",type=float,default=600)
    parser.add_argument("--memory-gib",type=float,default=12); parser.add_argument("--path-limit",type=int,default=2_000_000)
    parser.add_argument("--rotate-algorithms",action="store_true",
                        help="rotate algorithm execution order across instances/repetitions")
    parser.add_argument("--conditional-repetitions", action="store_true",
                        help=("run repetition 0 for every algorithm-instance pair, then run "
                              "later repetitions only when repetition 0 succeeded"))
    parser.add_argument("--shard",type=int,default=0); parser.add_argument("--shards",type=int,default=1)
    parser.add_argument("--limit",type=int); args=parser.parse_args()
    records=[r for i,r in enumerate(read_records(args.instances)) if i%args.shards==args.shard]
    if args.limit is not None: records=records[:args.limit]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    completed=set()
    recorded_status={}
    if args.output.exists():
        with args.output.open(newline="",encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key=(row["instance_id"],row["algorithm"],row["mode"],int(row["repetition"]))
                completed.add(key)
                recorded_status[key]=row.get("status","")
    new_file=not args.output.exists() or args.output.stat().st_size==0
    with args.output.open("a",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=FIELDS,extrasaction="ignore")
        if new_file: writer.writeheader(); handle.flush()
        for record_index, record in enumerate(records):
            for repetition in range(args.repetitions):
                algorithms = list(args.algorithms)
                if args.rotate_algorithms and algorithms:
                    shift = (record_index + repetition) % len(algorithms)
                    algorithms = algorithms[shift:] + algorithms[:shift]
                for algorithm in algorithms:
                    algorithm_mode=args.mode if algorithm.startswith("AF-FDD") else "enumerate"
                    key=(record["instance_id"],algorithm,algorithm_mode,repetition)
                    if key in completed: continue
                    first_key=(record["instance_id"],algorithm,algorithm_mode,0)
                    if (args.conditional_repetitions and repetition > 0 and
                            recorded_status.get(first_key) != "ok"):
                        continue
                    row=one_run(record,algorithm,algorithm_mode,repetition,args.timeout,args.memory_gib,args.path_limit)
                    writer.writerow({name:row.get(name,"") for name in FIELDS}); handle.flush()
                    completed.add(key)
                    recorded_status[key]=row.get("status","")
                    print(row["instance_id"],algorithm,repetition,row["status"],f"{row['wall_seconds']:.3f}s",flush=True)


if __name__ == "__main__": main()
