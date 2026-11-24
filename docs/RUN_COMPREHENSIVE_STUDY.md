# Running the comprehensive study (package 0.4.0)

For Windows with Anaconda, follow `README_FIRST.txt` and use the numbered BAT
files. The commands below provide the equivalent manual workflow.

Use Python 3.10 or later. From this directory:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .
python -m af_fdd.generate_study --output study/instances
```

The final command must report 1,200 synthetic and 72 SNDlib-derived instances.

## 1. Smoke test

```bash
python run_comprehensive.py --profile smoke --timeout 120 --memory-gib 12
```

## 2. Calibration

Create a stratified calibration file by selecting complete replication numbers 0–4 from every synthetic cell, plus all SNDlib-derived cases. Run one repetition. Do not select instances based on observed running time.

```bash
python -m af_fdd.select_calibration study/instances/synthetic.jsonl --output study/instances/calibration.jsonl --replications 5
python run_comprehensive.py --profile calibration --repetitions 1 --timeout 600 --memory-gib 12
```

If the baseline path list exceeds `--path-limit` (default 2,000,000), the result is an explicit error rather than an invalid partial answer. Raise this only if memory calibration supports it.

Run the controlled timing ablation without allocation tracing:

```bash
python -m af_fdd.ablation --no-tracemalloc --output study/results/ablation_no_tracemalloc
```

Send the complete calibration folder for review before the definitive run.

## 3. Definitive run

For a single publication-quality sequential run:

```bash
python run_comprehensive.py --profile definitive --repetitions 3 --timeout 600 --memory-gib 12
```

Repetition 0 screens every pair; later repetitions run only for successful
pairs. Medians require three successes. The runner is resumable. For four
separate machines, use one shard per machine and distinct output files:

```bash
python run_comprehensive.py --profile definitive --shards 4 --shard 0
python run_comprehensive.py --profile definitive --shards 4 --shard 1
python run_comprehensive.py --profile definitive --shards 4 --shard 2
python run_comprehensive.py --profile definitive --shards 4 --shard 3
```

Running four CPU-heavy jobs concurrently changes timing. For publication-quality wall times, one worker at a time is preferable; sharding is mainly for separate machines or for sequential execution. Preserve the raw CSVs, instance files, design JSON, Python/package versions, CPU model, operating system, and commit/archive hash.

```bash
python analyze_results.py study/results/definitive/raw_shard00-of-04.csv study/results/definitive/raw_shard01-of-04.csv study/results/definitive/raw_shard02-of-04.csv study/results/definitive/raw_shard03-of-04.csv
```

Any nonempty `digest_issues.csv` entry is a stop condition: diagnose correctness before making performance claims.

## 4. Separate challenge pilot

Do this only after the balanced definitive run, and never concurrently on the
same machine:

```bash
python run_comprehensive.py --profile challenge-pilot --repetitions 1 --timeout 600 --memory-gib 12
```

Send the complete pilot folder for whole-cell selection. Do not invoke the
`challenge-definitive` profile before the selection is frozen. The supplied
`challenge_heldout.jsonl` is an untouched candidate pool, not yet the selected
final set. See `CHALLENGE_CORPUS_PROTOCOL.md`.
