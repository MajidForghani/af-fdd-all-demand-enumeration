from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from .baselines import bai2021, simple_path_vectors, yeh2024
from .diagram import AFFDD, AFOptions
from .model import Network
from .study_generators import deserialize_network


def _digest(items):
    xor = 0; total = 0; count = 0; modulus = 1 << 128
    for d, vector in items:
        blob = d.to_bytes(8, "little") + bytes(str(tuple(vector)), "ascii")
        value = int.from_bytes(hashlib.blake2b(blob, digest_size=16).digest(), "big")
        xor ^= value; total = (total + value) % modulus; count += 1
    return f"{count}:{xor:032x}:{total:032x}", count


def _warmup():
    tiny = Network.from_tuples(4, [(0,1,1),(0,2,1),(1,3,1),(2,3,1)])
    AFFDD(tiny, "natural", AFOptions(mode="count", order_trials=0)).build().count_by_d()


def execute(record: dict, algorithm: str, mode: str, path_limit: int | None) -> dict:
    network = deserialize_network(record); _warmup(); started = perf_counter()
    row = {"instance_id": record["instance_id"], "algorithm": algorithm, "mode": mode}
    if algorithm in {"AF-FDD", "AF-FDD-v0.2.0", "AF-FDD-v0.2.1", "AF-FDD-v0.2.2", "AF-FDD-v0.1.1"}:
        if algorithm == "AF-FDD-v0.1.1":
            options = AFOptions(
                mode="count" if mode == "count" else "enumerate",
                cut_bounds=True, path_relevance=False, terminal_bounds=False,
                component_bounds=False, productive_output=False,
                legacy_output_reorder=True,
            )
            ordering = "v011-auto"
            implementation_version = "AF-FDD-0.1.1-frozen"
        else:
            # AF-FDD 0.2 uses the cheap exact reductions by default.
            options = AFOptions(mode="count" if mode == "count" else "enumerate", cut_bounds=False)
            ordering = "auto"
            implementation_version = "AF-FDD-0.2.2"
        diagram = AFFDD(network, ordering, options).build()
        verify_start = perf_counter()
        if mode == "count":
            counts = diagram.count_by_d(); digest = "counts:" + json.dumps(counts, sort_keys=True)
            outputs = sum(counts.values())
        else:
            digest, outputs = _digest(diagram.iter_solutions())
        row.update({"implementation_version": implementation_version,
                    "preprocess_seconds": diagram.stats.preprocessing_seconds,
                    "enumerate_seconds": diagram.stats.build_seconds,
                    "output_seconds": perf_counter()-verify_start,
                    "binary_paths": "", "diagram_states": diagram.stats.nodes,
                    "frontier_width": diagram.stats.max_width,
                    "candidates": diagram.stats.attempted_branches,
                    "stats_json": json.dumps(asdict(diagram.stats), sort_keys=True)})
    else:
        paths_start = perf_counter(); paths = simple_path_vectors(network, path_limit)
        path_seconds = perf_counter()-paths_start
        result = bai2021(network, paths=paths) if algorithm == "Bai-2021" else yeh2024(network, paths=paths, collect_audit=False)
        verify_start = perf_counter()
        digest, outputs = _digest((sum(v for a,v in zip(network.arcs, x) if a.tail==network.source)
                                   - sum(v for a,v in zip(network.arcs, x) if a.head==network.source), x)
                                  for x in result.vectors)
        row.update({"implementation_version": ("Bai-2021-independent-paper-reconstruction"
                                                  if algorithm == "Bai-2021" else
                                                  "Yeh-2024-independent-paper-reconstruction-iterative-IBAT"),
                    "preprocess_seconds": path_seconds + result.preprocess_seconds,
                    "enumerate_seconds": result.enumerate_seconds,
                    "output_seconds": result.output_seconds + perf_counter()-verify_start,
                    "binary_paths": len(paths), "diagram_states": "", "frontier_width": "",
                    "candidates": result.counters.get("candidate_additions", result.counters.get("ibat_states", "")),
                    "stats_json": json.dumps(result.counters, sort_keys=True)})
    row["algorithm_seconds"] = sum(float(row[key]) for key in
                                   ("preprocess_seconds", "enumerate_seconds", "output_seconds"))
    row.update({"status":"ok", "outputs":outputs, "digest":digest,
                "wall_seconds":perf_counter()-started,
                "worker_peak_rss_bytes":""})
    return row


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--record",type=Path,required=True)
    parser.add_argument("--algorithm",choices=["AF-FDD","AF-FDD-v0.1.1","AF-FDD-v0.2.0","AF-FDD-v0.2.1","AF-FDD-v0.2.2",
                                                "Bai-2021","Yeh-2024"],required=True)
    parser.add_argument("--mode",choices=["enumerate","count"],default="enumerate")
    parser.add_argument("--path-limit",type=int,default=2_000_000)
    args=parser.parse_args()
    try:
        record=json.loads(args.record.read_text(encoding="utf-8"))
        answer=execute(record,args.algorithm,args.mode,args.path_limit)
    except BaseException as error:
        answer={"status":"error","error_type":type(error).__name__,"error":str(error)}
    print(json.dumps(answer,sort_keys=True))


if __name__ == "__main__": main()
