from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Analyze one or more comprehensive-study raw CSV files")
    parser.add_argument("raw", type=Path, nargs="+")
    parser.add_argument("--profile", choices=["calibration", "definitive"], default="definitive")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    instance_dir = root / "study" / "instances"
    instances = ([instance_dir / "calibration.jsonl", instance_dir / "sndlib.jsonl"]
                 if args.profile == "calibration" else
                 [instance_dir / "synthetic.jsonl", instance_dir / "sndlib.jsonl"])
    output = args.output_dir or root / "study" / "results" / args.profile / "analysis"
    command = [sys.executable, "-m", "af_fdd.analyze_comprehensive", *map(str, args.raw),
               "--instances", *map(str, instances), "--output-dir", str(output),
               "--repetitions", str(args.repetitions), "--timeout", str(args.timeout),
               "--algorithms", "AF-FDD-v0.2.2", "Bai-2021", "Yeh-2024"]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
