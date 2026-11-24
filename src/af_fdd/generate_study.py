from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .study_generators import (CAPACITY_REGIMES, FAMILIES, MASTER_SEED,
                               SIZE_CLASSES, generate_synthetic,
                               load_sndlib_cases, serialize_network)


def generate(output: Path, replications: int = 25) -> dict[str, int]:
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for family in FAMILIES:
        for n in SIZE_CLASSES:
            for regime in CAPACITY_REGIMES:
                for replication in range(replications):
                    network, meta = generate_synthetic(family, n, regime, replication)
                    record = serialize_network(network, meta)
                    record["instance_id"] = f"syn-{family}-n{n}-{regime}-r{replication:02d}"
                    records.append(record)
    synthetic_count = len(records)
    data_dir = Path(__file__).resolve().parents[2] / "data" / "sndlib"
    for network, meta in load_sndlib_cases(data_dir):
        record = serialize_network(network, meta)
        record["instance_id"] = (f"snd-{meta['topology']}-{meta['pair_class']}-"
                                 f"{meta['orientation']}-{meta['capacity_regime']}")
        records.append(record)
    for collection in ("synthetic", "sndlib"):
        with (output / f"{collection}.jsonl").open("w", encoding="utf-8") as handle:
            for record in records:
                if record["collection"] == collection:
                    handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    fields = ["instance_id", "collection", "family", "topology", "size_class", "pair_class",
              "orientation", "capacity_regime", "replication", "seed", "n", "m",
              "max_capacity", "attempts", "sha256"]
    with (output / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)
    design = {"master_seed": MASTER_SEED, "prng": "Python random.Random (MT19937)",
              "synthetic_cells": len(FAMILIES) * len(SIZE_CLASSES) * len(CAPACITY_REGIMES),
              "replications_per_cell": replications, "synthetic_instances": synthetic_count,
              "sndlib_instances": len(records) - synthetic_count, "total_instances": len(records)}
    (output / "design.json").write_text(json.dumps(design, indent=2), encoding="utf-8")
    return {"synthetic": synthetic_count, "sndlib": len(records)-synthetic_count,
            "total": len(records)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the frozen AF-FDD study corpus")
    parser.add_argument("--output", type=Path, default=Path("study/instances"))
    parser.add_argument("--replications", type=int, default=25)
    args = parser.parse_args()
    print(json.dumps(generate(args.output, args.replications), indent=2))


if __name__ == "__main__":
    main()
