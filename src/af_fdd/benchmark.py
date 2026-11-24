from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import resource
from pathlib import Path
from time import perf_counter

from .baselines import bai2021, simple_path_vectors, yeh2024
from .diagram import AFFDD
from .generators import grid_network, layered_network
from .model import Network


def _digest(vectors: set[tuple[int, ...]]) -> str:
    digest = hashlib.sha256()
    for vector in sorted(vectors):
        digest.update(bytes(str(vector), "ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _worker(algorithm: str, network: Network, queue: mp.Queue) -> None:
    try:
        if algorithm == "AF-FDD":
            total_start = perf_counter()
            diagram = AFFDD(network).build()
            build_s = diagram.stats.build_seconds
            preprocess_s = diagram.stats.preprocessing_seconds
            output_start = perf_counter()
            grouped = diagram.solution_sets()
            vectors = set().union(*grouped.values()) if grouped else set()
            output_s = perf_counter() - output_start
            enumerate_s = build_s
            counters = {
                "dd_nodes": diagram.stats.nodes,
                "dd_transitions": diagram.stats.transitions,
                "dd_max_width": diagram.stats.max_width,
                "merged_transitions": diagram.stats.merged_transitions,
                "cycle_pruned": diagram.stats.cycle_pruned,
                "balance_pruned": diagram.stats.balance_pruned + diagram.stats.forgotten_balance_pruned,
            }
            solve_s = perf_counter() - total_start
        elif algorithm == "Bai-2021":
            result = bai2021(network)
            vectors = result.vectors
            preprocess_s = result.preprocess_seconds
            enumerate_s = result.enumerate_seconds
            output_s = result.output_seconds
            solve_s = preprocess_s + enumerate_s + output_s
            build_s = 0.0
            counters = result.counters
        elif algorithm == "Yeh-2024":
            result = yeh2024(network)
            vectors = result.vectors
            preprocess_s = result.preprocess_seconds
            enumerate_s = result.enumerate_seconds
            output_s = result.output_seconds
            solve_s = preprocess_s + enumerate_s + output_s
            build_s = 0.0
            counters = result.counters
        else:
            raise ValueError(algorithm)
        queue.put({
            "status": "ok",
            "algorithm": algorithm,
            "preprocess_s": preprocess_s,
            "build_s": build_s,
            "enumerate_s": enumerate_s,
            "output_s": locals().get("output_s", 0.0),
            "total_s": solve_s,
            "outputs": len(vectors),
            "digest": _digest(vectors),
            "peak_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "counters": counters,
        })
    except BaseException as exc:
        queue.put({"status": "error", "algorithm": algorithm, "error": repr(exc)})


def _run_timed(algorithm: str, network: Network, timeout: float) -> dict[str, object]:
    # "spawn" is available on Windows, macOS, and Linux and keeps each timing
    # worker isolated from the parent's interpreter state.
    context = mp.get_context("spawn")
    queue: mp.Queue = context.Queue()
    process = context.Process(target=_worker, args=(algorithm, network, queue))
    process.start()
    process.join(timeout)
    if process.is_alive():
        process.terminate()
        process.join()
        return {"status": "timeout", "algorithm": algorithm, "total_s": timeout}
    if queue.empty():
        return {"status": "error", "algorithm": algorithm, "error": f"worker exit code {process.exitcode}"}
    return queue.get()


def benchmark_cases() -> list[tuple[str, Network]]:
    return [
        ("layer-w2-l8", layered_network(2, 8, 1)),
        ("layer-w3-l4", layered_network(3, 4, 1)),
        ("layer-w3-l5", layered_network(3, 5, 1)),
        ("layer-w3-l6", layered_network(3, 6, 1)),
        ("layer-w4-l3", layered_network(4, 3, 1)),
        ("grid-5x5", grid_network(5, 5, 1)),
        ("grid-6x6", grid_network(6, 6, 1)),
    ]


def run_benchmark(output: Path, timeout: float) -> list[dict[str, object]]:
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    instances: list[dict[str, object]] = []
    for name, network in benchmark_cases():
        path_start = perf_counter()
        paths = simple_path_vectors(network)
        path_probe_s = perf_counter() - path_start
        instances.append({"name": name, "n": network.n, "m": len(network.arcs),
                          "binary_paths": len(paths), "path_probe_s": path_probe_s})
        case_results: list[dict[str, object]] = []
        for algorithm in ("AF-FDD", "Bai-2021", "Yeh-2024"):
            result = _run_timed(algorithm, network, timeout)
            row: dict[str, object] = {
                "instance": name,
                "n": network.n,
                "m": len(network.arcs),
                "binary_paths": len(paths),
                "algorithm": algorithm,
                "timeout_limit_s": timeout,
                **result,
            }
            counters = row.pop("counters", {})
            row["counters_json"] = json.dumps(counters, sort_keys=True)
            rows.append(row)
            case_results.append(row)
        successful = [r for r in case_results if r["status"] == "ok"]
        if successful:
            reference = successful[0]
            for row in case_results:
                row["agrees"] = (row["status"] == "ok" and row.get("outputs") == reference.get("outputs")
                                  and row.get("digest") == reference.get("digest"))

    fieldnames = sorted({key for row in rows for key in row})
    with (output / "benchmark.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    (output / "instances.json").write_text(json.dumps(instances, indent=2), encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Pilot comparison of AF-FDD, Bai-2021, and Yeh-2024")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output", type=Path, default=Path("results/pilot"))
    args = parser.parse_args()
    rows = run_benchmark(args.output, args.timeout)
    for row in rows:
        value = f"{float(row['total_s']):.6f}" if "total_s" in row else "-"
        print(row["instance"], row["algorithm"], row["status"], value, row.get("outputs", "-"))


if __name__ == "__main__":
    main()

