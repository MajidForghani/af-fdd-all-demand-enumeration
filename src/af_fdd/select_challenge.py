from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


ALGORITHMS = ("AF-FDD-v0.2.2", "Bai-2021", "Yeh-2024")


def _load_jsonl(path: Path):
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _cell(record):
    return record["family"], int(record["size_class"]), int(record["capacity_upper"])


def main():
    parser = argparse.ArgumentParser(description="Apply the frozen whole-cell challenge rule")
    parser.add_argument("pilot_raw", type=Path)
    parser.add_argument("--pilot", type=Path, default=Path("study/instances/challenge_pilot.jsonl"))
    parser.add_argument("--heldout", type=Path, default=Path("study/instances/challenge_heldout.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("study/instances/challenge_selected.jsonl"))
    args = parser.parse_args()

    pilot = _load_jsonl(args.pilot); heldout = _load_jsonl(args.heldout)
    by_id = {record["instance_id"]: record for record in pilot}
    rows = defaultdict(dict)
    with args.pilot_raw.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows[row["instance_id"]][row["algorithm"]] = row

    instances_by_cell = defaultdict(list)
    for record in pilot: instances_by_cell[_cell(record)].append(record)
    decisions = []
    selected = set()
    for cell, records in sorted(instances_by_cell.items()):
        solved_by_two = 0; nontrivial = 0; digest_issue = False
        for record in records:
            observed = rows.get(record["instance_id"], {})
            ok = [row for row in observed.values() if row.get("status") == "ok"]
            if len(ok) >= 2: solved_by_two += 1
            slow = sum(float(row.get("wall_seconds") or 0) >= 1.0 for row in ok) >= 2
            limited = any(row.get("status") in {"timeout", "memory_limit"} or
                          "path limit" in (row.get("error", "").lower())
                          for row in observed.values())
            if slow or limited: nontrivial += 1
            digests = {row.get("digest") for row in ok if row.get("digest")}
            if len(digests) > 1: digest_issue = True
        eligible = solved_by_two >= 2 and nontrivial >= 2 and not digest_issue
        if eligible: selected.add(cell)
        decisions.append({"family": cell[0], "size_class": cell[1], "capacity_upper": cell[2],
                          "pilot_instances": len(records), "solved_by_two_instances": solved_by_two,
                          "nontrivial_instances": nontrivial, "digest_issue": int(digest_issue),
                          "eligible": int(eligible)})

    chosen = [record for record in heldout if _cell(record) in selected]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for record in chosen:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    audit = args.output.with_name("challenge_selection_audit.csv")
    with audit.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(decisions[0]))
        writer.writeheader(); writer.writerows(decisions)
    summary = {"pilot_cells": len(decisions), "eligible_cells": len(selected),
               "selected_heldout_instances": len(chosen), "output": str(args.output),
               "audit": str(audit)}
    args.output.with_name("challenge_selection_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
