from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ALGORITHMS = ("AF-FDD-v0.2.2", "Bai-2021", "Yeh-2024")


def _float(row: dict[str, str], key: str):
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return None


def _median(values):
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def _geomean(values):
    values = [value for value in values if value is not None and value > 0]
    return math.exp(sum(math.log(value) for value in values) / len(values)) if values else None


def _write(path: Path, fields: list[str], rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _load_metadata(paths: list[Path]):
    answer = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    answer[row["instance_id"]] = row
    return answer


def main():
    parser = argparse.ArgumentParser(description="Publication-grade AF-FDD comparison analysis")
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--instances", type=Path, nargs="*", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--algorithms", nargs="+", default=list(ALGORITHMS))
    args = parser.parse_args()

    rows = []
    for path in args.inputs:
        with path.open(newline="", encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata = _load_metadata(args.instances)
    algorithms = list(args.algorithms)
    instances = sorted({row["instance_id"] for row in rows})

    duplicates = Counter((row["instance_id"], row["algorithm"], row["mode"], row["repetition"])
                         for row in rows)
    duplicate_keys = [key for key, count in duplicates.items() if count > 1]
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["instance_id"], row["algorithm"])].append(row)

    pair_rows = []
    pair = {}
    digest_issues = []
    for instance in instances:
        for algorithm in algorithms:
            values = grouped.get((instance, algorithm), [])
            ok = [row for row in values if row.get("status") == "ok"]
            statuses = Counter(row.get("status", "") for row in values)
            repetitions = {int(row["repetition"]) for row in values if row.get("repetition", "") != ""}
            first_rows = [row for row in values if row.get("repetition", "") == "0"]
            first_status = first_rows[-1].get("status", "") if first_rows else ""
            complete = (len(values) == args.repetitions and
                        repetitions == set(range(args.repetitions)) and len(ok) == args.repetitions)
            screened_failure = bool(first_rows and first_status != "ok")
            incomplete_pending = bool(not complete and not screened_failure)
            digests = {row.get("digest", "") for row in ok if row.get("digest", "")}
            digest_stable = len(digests) <= 1
            if not digest_stable:
                digest_issues.append({"instance_id": instance, "algorithm": algorithm,
                                      "issue": "digest differs across repetitions"})
            item = {
                "instance_id": instance, "algorithm": algorithm,
                "complete_solved": int(complete), "successful_repetitions": len(ok),
                "recorded_repetitions": len(values),
                "first_screen_status": first_status,
                "screen_passed": int(first_status == "ok"),
                "screened_failure": int(screened_failure),
                "incomplete_pending": int(incomplete_pending),
                "statuses": json.dumps(dict(sorted(statuses.items())), sort_keys=True),
                "median_wall_seconds": _median([_float(row, "wall_seconds") for row in ok]) if complete else None,
                "median_process_wall_seconds": _median([_float(row, "process_wall_seconds") for row in ok]) if complete else None,
                "median_worker_wall_seconds": _median([_float(row, "worker_wall_seconds") for row in ok]) if complete else None,
                "median_algorithm_seconds": _median([_float(row, "algorithm_seconds") for row in ok]) if complete else None,
                "median_preprocess_seconds": _median([_float(row, "preprocess_seconds") for row in ok]) if complete else None,
                "median_enumerate_seconds": _median([_float(row, "enumerate_seconds") for row in ok]) if complete else None,
                "median_output_seconds": _median([_float(row, "output_seconds") for row in ok]) if complete else None,
                "median_peak_rss_bytes": _median([_float(row, "peak_rss_bytes") for row in ok]) if complete else None,
                "outputs": ok[0].get("outputs", "") if ok and digest_stable else "",
                "digest": next(iter(digests)) if len(digests) == 1 else "",
                "binary_paths": _median([_float(row, "binary_paths") for row in ok]),
                "diagram_states": _median([_float(row, "diagram_states") for row in ok]),
                "frontier_width": _median([_float(row, "frontier_width") for row in ok]),
                "candidates": _median([_float(row, "candidates") for row in ok]),
            }
            pair[(instance, algorithm)] = item
            pair_rows.append(item)

    cross_digest_issues = []
    for instance in instances:
        solved = [pair[(instance, algorithm)] for algorithm in algorithms
                  if pair[(instance, algorithm)]["complete_solved"]]
        if len(solved) >= 2:
            digests = {item["digest"] for item in solved}
            if len(digests) > 1:
                cross_digest_issues.append({"instance_id": instance,
                                            "algorithms": ",".join(item["algorithm"] for item in solved),
                                            "issue": "output digest disagreement"})

    common = [instance for instance in instances
              if all(pair[(instance, algorithm)]["complete_solved"] for algorithm in algorithms)]
    at_least_one = [instance for instance in instances
                    if any(pair[(instance, algorithm)]["complete_solved"] for algorithm in algorithms)]

    algorithm_rows = []
    for algorithm in algorithms:
        solved = [pair[(instance, algorithm)] for instance in instances
                  if pair[(instance, algorithm)]["complete_solved"]]
        common_times = [pair[(instance, algorithm)]["median_wall_seconds"] for instance in common]
        par2 = []
        for instance in instances:
            item = pair[(instance, algorithm)]
            par2.append(item["median_wall_seconds"] if item["complete_solved"] else 2 * args.timeout)
        status_counts = Counter(row.get("status", "") for row in rows if row["algorithm"] == algorithm)
        screened_failures = sum(pair[(instance, algorithm)]["screened_failure"] for instance in instances)
        pending = sum(pair[(instance, algorithm)]["incomplete_pending"] for instance in instances)
        algorithm_rows.append({
            "algorithm": algorithm, "instances": len(instances),
            "complete_solved_instances": len(solved), "common_solved_instances": len(common),
            "median_seconds_solved": _median([item["median_wall_seconds"] for item in solved]),
            "median_algorithm_seconds_solved": _median([item["median_algorithm_seconds"] for item in solved]),
            "geomean_seconds_common": _geomean(common_times),
            "median_peak_rss_mib_solved": (_median([item["median_peak_rss_bytes"] for item in solved]) or 0) / 2**20,
            "par2_mean_seconds": statistics.mean(par2) if par2 else None,
            "ok_runs": status_counts.get("ok", 0), "timeout_runs": status_counts.get("timeout", 0),
            "memory_limit_runs": status_counts.get("memory_limit", 0),
            "screened_failure_instances": screened_failures,
            "incomplete_pending_instances": pending,
            "error_or_crash_runs": sum(count for status, count in status_counts.items()
                                       if status not in {"ok", "timeout", "memory_limit"}),
        })

    speedup_rows = []
    af = algorithms[0]
    for baseline in algorithms[1:]:
        common_pair = [instance for instance in instances
                       if pair[(instance, af)]["complete_solved"] and pair[(instance, baseline)]["complete_solved"]]
        ratios = []
        internal_ratios = []
        for instance in common_pair:
            ratio = pair[(instance, baseline)]["median_wall_seconds"] / pair[(instance, af)]["median_wall_seconds"]
            baseline_internal = pair[(instance, baseline)]["median_algorithm_seconds"]
            af_internal = pair[(instance, af)]["median_algorithm_seconds"]
            internal_ratio = (baseline_internal / af_internal
                              if baseline_internal is not None and af_internal not in {None, 0}
                              else None)
            ratios.append(ratio)
            if internal_ratio is not None:
                internal_ratios.append(internal_ratio)
            speedup_rows.append({"instance_id": instance, "baseline": baseline,
                                 "baseline_over_af_speedup": ratio,
                                 "baseline_over_af_algorithm_speedup": internal_ratio})
        speedup_rows.append({"instance_id": "__SUMMARY__", "baseline": baseline,
                             "baseline_over_af_speedup": _geomean(ratios),
                             "baseline_over_af_algorithm_speedup": _geomean(internal_ratios),
                             "common_instances": len(common_pair)})

    profile_rows = []
    for tau in (1, 1.25, 1.5, 2, 3, 5, 10, 20, 50, 100):
        for algorithm in algorithms:
            count = 0
            for instance in at_least_one:
                best = min(pair[(instance, candidate)]["median_wall_seconds"] for candidate in algorithms
                           if pair[(instance, candidate)]["complete_solved"])
                item = pair[(instance, algorithm)]
                if item["complete_solved"] and item["median_wall_seconds"] <= tau * best:
                    count += 1
            profile_rows.append({"tau": tau, "algorithm": algorithm, "fraction": count / len(at_least_one) if at_least_one else 0,
                                 "denominator_instances": len(at_least_one)})

    # Long-form structural table.  Binary-path counts are taken from either
    # path-coordinate baseline; AF-FDD width and state counts come from AF-FDD.
    structure_rows = []
    for instance in instances:
        meta = metadata.get(instance, {})
        bai_paths = pair[(instance, "Bai-2021")]["binary_paths"] if "Bai-2021" in algorithms else None
        yeh_paths = pair[(instance, "Yeh-2024")]["binary_paths"] if "Yeh-2024" in algorithms else None
        binary_paths = bai_paths if bai_paths is not None else yeh_paths
        width = pair[(instance, af)]["frontier_width"]
        base = {key: meta.get(key, "") for key in
                ("collection", "family", "topology", "size_class", "pair_class", "orientation",
                 "capacity_regime", "n", "m", "max_capacity", "replication", "seed", "sha256")}
        base.update({"instance_id": instance, "binary_paths": binary_paths,
                     "af_frontier_width": width, "af_diagram_states": pair[(instance, af)]["diagram_states"],
                     "path_width_ratio": (binary_paths / max(1, width)) if binary_paths is not None and width is not None else None,
                     "outputs": pair[(instance, af)]["outputs"]})
        for algorithm in algorithms:
            item = pair[(instance, algorithm)]
            base[f"{algorithm}_complete_solved"] = item["complete_solved"]
            base[f"{algorithm}_median_seconds"] = item["median_wall_seconds"]
            base[f"{algorithm}_median_algorithm_seconds"] = item["median_algorithm_seconds"]
            base[f"{algorithm}_median_peak_rss_bytes"] = item["median_peak_rss_bytes"]
        structure_rows.append(base)

    pair_fields = list(pair_rows[0]) if pair_rows else []
    algorithm_fields = list(algorithm_rows[0]) if algorithm_rows else []
    speedup_fields = sorted({key for row in speedup_rows for key in row})
    profile_fields = list(profile_rows[0]) if profile_rows else []
    structure_fields = list(structure_rows[0]) if structure_rows else []
    _write(args.output_dir / "pair_summary.csv", pair_fields, pair_rows)
    _write(args.output_dir / "algorithm_summary.csv", algorithm_fields, algorithm_rows)
    _write(args.output_dir / "speedups.csv", speedup_fields, speedup_rows)
    _write(args.output_dir / "performance_profile.csv", profile_fields, profile_rows)
    _write(args.output_dir / "structural_data.csv", structure_fields, structure_rows)
    all_digest_issues = digest_issues + cross_digest_issues
    _write(args.output_dir / "digest_issues.csv", ["instance_id", "algorithm", "algorithms", "issue"], all_digest_issues)

    pending_pairs = sum(item["incomplete_pending"] for item in pair_rows)
    screened_failure_pairs = sum(item["screened_failure"] for item in pair_rows)
    payload = {
        "raw_rows": len(rows), "instances": len(instances), "expected_repetitions": args.repetitions,
        "algorithms": algorithms, "duplicate_keys": len(duplicate_keys),
        "complete_common_solved_instances": len(common), "instances_solved_by_at_least_one": len(at_least_one),
        "digest_issues": len(all_digest_issues), "timeout_seconds": args.timeout,
        "screened_failure_pairs": screened_failure_pairs,
        "incomplete_pending_pairs": pending_pairs,
        "stop_condition": bool(duplicate_keys or all_digest_issues or pending_pairs),
    }
    (args.output_dir / "analysis_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
