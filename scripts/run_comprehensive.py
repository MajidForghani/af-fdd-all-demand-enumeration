from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ALGORITHMS = ["AF-FDD-v0.2.2", "Bai-2021", "Yeh-2024"]


def main():
    parser = argparse.ArgumentParser(description="Staged comprehensive all-d benchmark")
    parser.add_argument("--profile", choices=["smoke", "calibration", "definitive",
                                                "challenge-pilot", "challenge-definitive"],
                        required=True)
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--memory-gib", type=float, default=12.0)
    parser.add_argument("--path-limit", type=int, default=2_000_000)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    instance_dir = root / "study" / "instances"
    result_dir = root / "study" / "results" / args.profile
    result_dir.mkdir(parents=True, exist_ok=True)
    if args.profile == "smoke":
        inputs = [instance_dir / "calibration.jsonl"]
        repetitions = args.repetitions or 1
        limit = args.limit or 2
    elif args.profile == "calibration":
        inputs = [instance_dir / "calibration.jsonl", instance_dir / "sndlib.jsonl"]
        repetitions = args.repetitions or 1
        limit = args.limit
    elif args.profile == "definitive":
        inputs = [instance_dir / "synthetic.jsonl", instance_dir / "sndlib.jsonl"]
        repetitions = args.repetitions or 3
        limit = args.limit
    elif args.profile == "challenge-pilot":
        inputs = [instance_dir / "challenge_pilot.jsonl"]
        repetitions = args.repetitions or 1
        limit = args.limit
    else:
        inputs = [instance_dir / "challenge_selected.jsonl"]
        if not inputs[0].exists():
            raise SystemExit("challenge_selected.jsonl does not exist; freeze pilot cell selection first")
        repetitions = args.repetitions or 3
        limit = args.limit

    conditional_repetitions = args.profile in {"definitive", "challenge-definitive"}

    suffix = f"_shard{args.shard:02d}-of-{args.shards:02d}" if args.shards > 1 else ""
    raw = result_dir / f"raw{suffix}.csv"
    environment = {
        "created_utc": datetime.now(timezone.utc).isoformat(), "profile": args.profile,
        "package_version": "0.4.1-heldout-final",
        "python": sys.version, "platform": platform.platform(), "processor": platform.processor(),
        "algorithms": ALGORITHMS, "repetitions": repetitions, "timeout_seconds": args.timeout,
        "memory_gib": args.memory_gib, "path_limit": args.path_limit,
        "conditional_repetitions": conditional_repetitions,
        "shard": args.shard, "shards": args.shards, "limit": limit,
    }
    (result_dir / f"environment{suffix}.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")

    command = [sys.executable, "-m", "af_fdd.study_runner", *map(str, inputs),
               "--output", str(raw), "--algorithms", *ALGORITHMS,
               "--mode", "enumerate", "--repetitions", str(repetitions),
               "--timeout", str(args.timeout), "--memory-gib", str(args.memory_gib),
               "--path-limit", str(args.path_limit), "--rotate-algorithms",
               "--shard", str(args.shard), "--shards", str(args.shards)]
    if conditional_repetitions:
        command.append("--conditional-repetitions")
    if limit is not None:
        command.extend(["--limit", str(limit)])
    print(f"Profile: {args.profile}; repetitions: {repetitions}; output: {raw}", flush=True)
    subprocess.run(command, check=True)

    # A single shard can be analyzed immediately.  Multi-shard definitive runs
    # are analyzed together with analyze_results.py after all shards finish.
    if args.shards == 1:
        analysis = result_dir / "analysis"
        command = [sys.executable, "-m", "af_fdd.analyze_comprehensive", str(raw),
                   "--instances", *map(str, inputs), "--output-dir", str(analysis),
                   "--repetitions", str(repetitions), "--timeout", str(args.timeout),
                   "--algorithms", *ALGORITHMS]
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
