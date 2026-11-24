"""Summarize the phase diagnostic and cross-check its frozen output digests."""
import csv
import sys
from collections import defaultdict
from statistics import median


def rows(path):
    with open(path, newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main(phase_csv, frozen_csv):
    phase = rows(phase_csv)
    assert len(phase) == 81
    grouped = defaultdict(list)
    frozen = {r["instance_id"]: r["digest"] for r in rows(frozen_csv)
              if r["algorithm"] == "AF-FDD-v0.2.2" and r["status"] == "ok"}
    for r in phase:
        grouped[r["instance_id"], r["family"], r["variant"]].append(r)
        if r["status"] == "ok":
            assert r["digest"] == frozen[r["instance_id"]], r
    metrics = "paths outputs states order_s setup_s build_s output_s".split()
    cells = defaultdict(list)
    for (key, family, variant), repetitions in grouped.items():
        assert {r["rep"] for r in repetitions} == {"0","1","2"}
        if any(r["status"] != "ok" for r in repetitions):
            print("incomplete", key, variant, [r["status"] for r in repetitions])
            continue
        values = {k: median(float(r[k]) for r in repetitions) for k in metrics}
        values["total_s"] = median(sum(float(r[k]) for k in metrics[3:]) for r in repetitions)
        cells[family, variant].append(values)
        print(key, variant, {k: float(f"{v:.5g}") for k,v in values.items()})
    for (family, variant), instances in sorted(cells.items()):
        print(family, variant, len(instances),
              {k: float(f"{median(item[k] for item in instances):.5g}")
               for k in metrics + ["total_s"]})


if __name__ == "__main__":
    main(*sys.argv[1:])
