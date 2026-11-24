from __future__ import annotations

import argparse
import csv
import json
import tracemalloc
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from .diagram import AFFDD, AFOptions
from .generators import grid_network, layered_network
from .legacy_diagram import LegacyAFFDD


def instances():
    return [
        ("layer-2x6", layered_network(2, 6, 1)),
        ("layer-3x3", layered_network(3, 3, 1)),
        ("layer-3x4", layered_network(3, 4, 1)),
        ("grid-4x4", grid_network(4, 4, 1)),
        ("grid-5x5", grid_network(5, 5, 1)),
    ]


def _measure(factory, use_tracemalloc=True):
    if use_tracemalloc: tracemalloc.start()
    start = perf_counter()
    diagram = factory().build()
    elapsed = perf_counter() - start
    if use_tracemalloc:
        _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    else:
        peak = ""
    return diagram, elapsed, peak


def run(output: Path, use_tracemalloc: bool = True):
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, network in instances():
        selected = AFFDD(network, "auto", AFOptions(mode="count", cut_bounds=False)).order
        configurations = [
            ("A0-legacy-natural", lambda: LegacyAFFDD(network, "natural")),
            ("A1-legacy-greedy", lambda: LegacyAFFDD(network, "greedy")),
            ("A2-legacy-auto-order", lambda: LegacyAFFDD(network, selected)),
            ("A3-packed-full-closure", lambda: AFFDD(network, selected, AFOptions(
                incremental_closure=False, cut_bounds=False))),
            ("A4-incremental-closure", lambda: AFFDD(network, selected, AFOptions(
                cut_bounds=False))),
            ("A5-cut-bounds", lambda: AFFDD(network, selected, AFOptions(
                cut_bounds=True))),
            ("A6-residual-test", lambda: AFFDD(network, selected, AFOptions(
                cut_bounds=True, residual_test=True))),
            ("A7-count-streaming", lambda: AFFDD(network, selected, AFOptions(
                mode="count", cut_bounds=True))),
        ]
        reference = None
        for label, factory in configurations:
            diagram, elapsed, peak = _measure(factory, use_tracemalloc)
            counts = diagram.count_by_d()
            if reference is None:
                reference = counts
            rows.append({
                "instance": name, "n": network.n, "m": len(network.arcs),
                "configuration": label, "seconds": elapsed,
                "peak_tracemalloc_bytes": peak, "nodes": diagram.stats.nodes,
                "transitions": diagram.stats.transitions, "max_width": diagram.stats.max_width,
                "outputs": sum(counts.values()), "correct": counts == reference,
                "order": json.dumps(list(diagram.order)),
                "stats": json.dumps(asdict(diagram.stats), sort_keys=True),
            })
    with (output / "ablation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    summary = {}
    for config in sorted({row["configuration"] for row in rows}):
        selected = [row for row in rows if row["configuration"] == config]
        summary[config] = {
            "geometric_mean_seconds": __import__("math").exp(
                sum(__import__("math").log(max(float(row["seconds"]), 1e-12)) for row in selected) / len(selected)),
            "max_peak_bytes": max((int(row["peak_tracemalloc_bytes"]) for row in selected
                                   if row["peak_tracemalloc_bytes"] != ""), default=None),
            "all_correct": all(bool(row["correct"]) for row in selected),
        }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results/ablation"))
    parser.add_argument("--no-tracemalloc", action="store_true",
                        help="recommended for timing-focused controlled ablation")
    args = parser.parse_args()
    rows = run(args.output, not args.no_tracemalloc)
    for row in rows:
        print(row["instance"], row["configuration"], f'{row["seconds"]:.6f}', row["nodes"])


if __name__ == "__main__":
    main()
