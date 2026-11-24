"""One-factor diagnostics on frozen balanced instances; Python standard library + AF-FDD."""
import csv
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from time import perf_counter


def worker(record, variant):
    from af_fdd.diagram import AFFDD, AFOptions
    from af_fdd.study_worker import _digest, _warmup, deserialize_network
    from af_fdd.baselines import simple_path_vectors

    network = deserialize_network(record)
    _warmup()
    options = AFOptions(incremental_closure=variant != "full_closure")
    diagram = AFFDD(network, "natural" if variant == "natural" else "auto", options)
    diagram.build()
    start = perf_counter()
    digest, outputs = _digest(diagram.iter_solutions())
    output = perf_counter() - start
    return dict(order_s=diagram.stats.order_estimation_seconds,
                setup_s=diagram.stats.preprocessing_seconds-diagram.stats.order_estimation_seconds,
                build_s=diagram.stats.build_seconds, output_s=output,
                states=diagram.stats.nodes, outputs=outputs, digest=digest,
                paths=len(simple_path_vectors(network, 2_000_000)))


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--worker":
        record, variant = json.load(sys.stdin)
        print(json.dumps(worker(record, variant)))
    else:
        instances, manifest, output = map(Path, sys.argv[1:])
        sizes = {"dag_sparse": "22", "layered": "22", "cyclic_dense": "10"}
        with manifest.open(newline="", encoding="utf-8-sig") as handle:
            chosen = {r["instance_id"]: r["family"] for r in csv.DictReader(handle)
                      if r["size_class"] == sizes.get(r["family"])
                      and r["capacity_regime"] == "small" and r["replication"] in {"0","1","2"}}
        assert len(chosen) == 9, chosen
        records = {r["instance_id"]: r for line in instances.open(encoding="utf-8")
                   if (r := json.loads(line))["instance_id"] in chosen}
        assert records.keys() == chosen.keys()
        variants = ("default", "natural", "full_closure")
        output.with_suffix(".json").write_text(json.dumps(
            dict(python=sys.version, platform=platform.platform(), logical_cpus=os.cpu_count(),
                 timeout_seconds=30, repetitions=3, selected_ids=sorted(chosen)), indent=2)+"\n")
        with output.open("w", newline="") as handle:
            fields = "instance_id family variant rep status order_s setup_s build_s output_s states outputs digest paths".split()
            writer = csv.DictWriter(handle, fields)
            writer.writeheader()
            for key, record in sorted(records.items()):
                for rep in range(3):
                    for variant in variants[rep:] + variants[:rep]:
                        row = dict(instance_id=key, family=chosen[key], variant=variant, rep=rep)
                        try:
                            result = subprocess.run([sys.executable, __file__, "--worker"],
                                input=json.dumps([record, variant]), capture_output=True,
                                text=True, check=True, timeout=30)
                            row.update(status="ok", **json.loads(result.stdout))
                        except subprocess.TimeoutExpired:
                            row["status"] = "timeout"
                        writer.writerow(row)
                        handle.flush()
