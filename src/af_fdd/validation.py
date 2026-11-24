from __future__ import annotations

import argparse
import csv
import itertools
import json
import random
from pathlib import Path
from time import perf_counter

from .diagram import AFFDD
from .generators import random_network
from .model import Network
from .oracle import enumerate_dmp_oracle


def compare_one(network: Network, label: str) -> dict[str, object]:
    t0 = perf_counter()
    expected = enumerate_dmp_oracle(network)
    oracle_s = perf_counter() - t0
    diagram = AFFDD(network, "greedy").build()
    actual = diagram.solution_sets()
    return {
        "label": label,
        "n": network.n,
        "m": len(network.arcs),
        "capacity_box": _box_size(network),
        "oracle_s": oracle_s,
        "af_fdd_s": diagram.stats.build_seconds,
        "outputs": sum(len(v) for v in expected.values()),
        "levels": len(expected),
        "nodes": diagram.stats.nodes,
        "transitions": diagram.stats.transitions,
        "max_width": diagram.stats.max_width,
        "correct": expected == actual,
        "missing": sum(len(expected.get(d, set()) - actual.get(d, set())) for d in set(expected) | set(actual)),
        "extra": sum(len(actual.get(d, set()) - expected.get(d, set())) for d in set(expected) | set(actual)),
    }


def _box_size(network: Network) -> int:
    answer = 1
    for c in network.capacities:
        answer *= c + 1
    return answer


def exhaustive_topologies(n: int = 4, max_arcs: int = 5) -> list[Network]:
    """All small simple digraphs containing the fixed chain 0->...->n-1."""
    backbone = {(i, i + 1) for i in range(n - 1)}
    optional = [(u, v) for u in range(n) for v in range(n) if u != v and (u, v) not in backbone]
    networks: list[Network] = []
    for extra_count in range(max_arcs - len(backbone) + 1):
        for extra in itertools.combinations(optional, extra_count):
            arcs = [(u, v, 1) for u, v in sorted(backbone | set(extra))]
            networks.append(Network.from_tuples(n, arcs))
    return networks


def run_validation(random_cases: int, seed: int, output: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for i, network in enumerate(exhaustive_topologies()):
        rows.append(compare_one(network, f"exhaustive-{i:04d}"))
    rng = random.Random(seed)
    for i in range(random_cases):
        n = rng.randint(3, 6)
        max_possible = n * (n - 1) if rng.random() < 0.5 else n * (n - 1) // 2
        m = rng.randint(n - 1, min(n + 3, max_possible))
        cap_max = 1 if i < random_cases // 2 else 2
        network = random_network(rng, n, m, cap_max, acyclic=(i % 2 == 0))
        if _box_size(network) > 200_000:
            continue
        rows.append(compare_one(network, f"random-{i:04d}"))
    output.mkdir(parents=True, exist_ok=True)
    with (output / "validation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "cases": len(rows),
        "passed": sum(bool(r["correct"]) for r in rows),
        "failed": sum(not bool(r["correct"]) for r in rows),
        "seed": seed,
        "max_capacity_box": max(int(r["capacity_box"]) for r in rows),
        "total_outputs_checked": sum(int(r["outputs"]) for r in rows),
    }
    (output / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate AF-FDD against the defining brute-force oracle")
    parser.add_argument("--random-cases", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20261019)
    parser.add_argument("--output", type=Path, default=Path("results/validation"))
    args = parser.parse_args()
    rows = run_validation(args.random_cases, args.seed, args.output)
    failed = [r for r in rows if not r["correct"]]
    print(f"validated={len(rows)} passed={len(rows)-len(failed)} failed={len(failed)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

