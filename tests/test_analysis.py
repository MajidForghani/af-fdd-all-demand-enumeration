import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ComprehensiveAnalysisTests(unittest.TestCase):
    def test_complete_triplet_and_digest_check(self):
        fields = ["instance_id", "collection", "algorithm", "implementation_version", "mode",
                  "repetition", "status", "error_type", "error", "wall_seconds",
                  "process_wall_seconds", "worker_wall_seconds", "algorithm_seconds",
                  "preprocess_seconds", "enumerate_seconds", "output_seconds", "peak_rss_bytes",
                  "outputs", "digest", "binary_paths", "diagram_states", "frontier_width",
                  "candidates", "stats_json"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.csv"
            with raw.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for algorithm, seconds in (("AF-FDD-v0.2.2", 1.0), ("Bai-2021", 2.0), ("Yeh-2024", 3.0)):
                    writer.writerow({"instance_id": "i1", "collection": "synthetic",
                                     "algorithm": algorithm, "mode": "enumerate", "repetition": 0,
                                     "status": "ok", "wall_seconds": seconds,
                                     "process_wall_seconds": seconds,
                                     "worker_wall_seconds": seconds - 0.01,
                                     "algorithm_seconds": 1.0 if algorithm.startswith("AF-FDD") else seconds,
                                     "preprocess_seconds": 0.1, "enumerate_seconds": 0.8,
                                     "output_seconds": 0.1, "peak_rss_bytes": 1048576,
                                     "outputs": 4, "digest": "same", "binary_paths": 2,
                                     "diagram_states": 3 if algorithm.startswith("AF-FDD") else "",
                                     "frontier_width": 2 if algorithm.startswith("AF-FDD") else "",
                                     "candidates": 5, "stats_json": "{}"})
            instances = root / "instances.jsonl"
            instances.write_text(json.dumps({"instance_id": "i1", "collection": "synthetic",
                                             "family": "dag_sparse", "n": 4, "m": 4}) + "\n",
                                 encoding="utf-8")
            output = root / "analysis"
            env = dict(os.environ)
            source = str(Path(__file__).resolve().parents[1] / "src")
            env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
            subprocess.run([sys.executable, "-m", "af_fdd.analyze_comprehensive", str(raw),
                            "--instances", str(instances), "--output-dir", str(output),
                            "--repetitions", "1"], check=True, env=env,
                           stdout=subprocess.PIPE, text=True)
            summary = json.loads((output / "analysis_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["complete_common_solved_instances"], 1)
            self.assertEqual(summary["digest_issues"], 0)
            self.assertFalse(summary["stop_condition"])


if __name__ == "__main__":
    unittest.main()
