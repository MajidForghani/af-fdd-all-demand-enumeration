from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .study_generators import (CHALLENGE_CAPACITY_UPPERS, CHALLENGE_FAMILY_SIZES,
                               CHALLENGE_MASTER_SEED, generate_challenge,
                               serialize_network)


def _records(split: str, replications: range):
    for family, sizes in CHALLENGE_FAMILY_SIZES.items():
        for n in sizes:
            for capacity_upper in CHALLENGE_CAPACITY_UPPERS:
                for replication in replications:
                    network, meta = generate_challenge(
                        family, n, capacity_upper, replication, split)
                    record = serialize_network(network, meta)
                    record["instance_id"] = (
                        f"challenge-{split}-{family}-n{n}-U{capacity_upper}-"
                        f"r{replication:03d}")
                    yield record


def generate(output: Path, pilot_replications: int = 4,
             heldout_replications: int = 10):
    output.mkdir(parents=True, exist_ok=True)
    pilot = list(_records("pilot", range(pilot_replications)))
    # A disjoint replication namespace makes accidental pilot/held-out overlap
    # evident in both the IDs and the deterministic seed derivation.
    heldout = list(_records("heldout", range(100, 100 + heldout_replications)))
    for name, records in (("challenge_pilot", pilot), ("challenge_heldout", heldout)):
        with (output / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    fields = ["instance_id", "collection", "family", "size_class", "capacity_regime",
              "capacity_upper", "replication", "seed", "n", "m", "source", "sink",
              "terminal_rule", "sha256"]
    with (output / "challenge_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(pilot + heldout)
    design = {
        "design_version": "1.0-frozen", "master_seed": CHALLENGE_MASTER_SEED,
        "prng": "Python random.Random (MT19937)",
        "families_and_sizes": CHALLENGE_FAMILY_SIZES,
        "capacity_uppers": CHALLENGE_CAPACITY_UPPERS,
        "cells": sum(len(v) for v in CHALLENGE_FAMILY_SIZES.values()) * len(CHALLENGE_CAPACITY_UPPERS),
        "pilot_replications_per_cell": pilot_replications,
        "heldout_replications_per_cell": heldout_replications,
        "pilot_instances": len(pilot), "heldout_candidate_instances": len(heldout),
        "terminal_rule": "source=0 and sink=n-1, fixed by constructive path-rich design",
        "selection_unit": "entire design cell only; never an individual instance",
        "prohibition": "held-out records must not be run before pilot-cell selection is frozen",
    }
    (output / "challenge_design.json").write_text(json.dumps(design, indent=2), encoding="utf-8")
    return design


def main():
    parser = argparse.ArgumentParser(description="Generate frozen held-out challenge candidates")
    parser.add_argument("--output", type=Path, default=Path("study/instances"))
    args = parser.parse_args()
    print(json.dumps(generate(args.output), indent=2))


if __name__ == "__main__":
    main()
