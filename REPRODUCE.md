# Reproduction instructions

All commands below are run from the repository root. The definitive timings in
the paper were obtained under Windows 11 with 64-bit Anaconda Python. Functional
validation is platform independent, but wall time and resident memory are not.

## 1. Create the environment

```bash
conda env create -f environment.yml
conda activate af-fdd-reproduction
python -m pip install -e .
```

Alternatively, with an existing Python 3.12 environment:

```bash
python -m pip install -e .
python -m pip install pytest
```

## 2. Run tests and exact validation

```bash
python -m pytest -q
python -m af_fdd.validation
```

The independent oracle enumerates the complete capacity box and applies the
definition of a \(d\)-MP using maximum-flow tests. It does not invoke the
acyclic-flow characterization.

## 3. Verify the frozen files

```bash
python verify_release.py
```

This checks every entry in `MANIFEST_SHA256.txt`. The manifest intentionally
does not contain its own hash.

## 4. Regenerate the balanced instances

Generate into a temporary directory and compare the resulting SHA-256 values
with `instances/balanced/manifest.csv`:

```bash
python -m af_fdd.generate_study --output regenerated/balanced --replications 25
```

The command should report 1,200 synthetic and 72 SNDlib-derived instances.
The master seed and deterministic per-instance seed derivation are recorded in
`instances/balanced/design.json` and the source.

## 5. Reanalyze the supplied definitive runs

The exact analysis products used by the manuscript are already retained under
the two `results` directories. They can be rebuilt as follows:

```bash
python -m af_fdd.analyze_comprehensive \
  results/balanced/raw.csv \
  --instances instances/balanced/synthetic.jsonl instances/balanced/sndlib.jsonl \
  --output-dir results/balanced/analysis_rebuilt

python -m af_fdd.analyze_comprehensive \
  results/challenge/raw.csv \
  --instances instances/challenge/challenge_selected.jsonl \
  --output-dir results/challenge/analysis_rebuilt
```

On Windows, place each command on one line or replace the backslash with `^`.
Any nonempty digest-disagreement report is a stop condition.

Regenerate the supplied manuscript figures after installing the analysis
dependencies:

```bash
python -m pip install -e ".[analysis]"
python make_manuscript_figures.py
```

## 6. Rerun the balanced experiment

The included runner accepts the frozen JSONL files directly:

```bash
python -m af_fdd.study_runner \
  instances/balanced/synthetic.jsonl instances/balanced/sndlib.jsonl \
  --output rerun/balanced/raw.csv \
  --algorithms AF-FDD-v0.2.2 Bai-2021 Yeh-2024 \
  --mode enumerate --repetitions 3 --timeout 600 --memory-gib 12 \
  --path-limit 2000000 --rotate-algorithms --conditional-repetitions
```

## 7. Rerun the conditionally selected challenge corpus

```bash
python -m af_fdd.study_runner \
  instances/challenge/challenge_selected.jsonl \
  --output rerun/challenge/raw.csv \
  --algorithms AF-FDD-v0.2.2 Bai-2021 Yeh-2024 \
  --mode enumerate --repetitions 3 --timeout 600 --memory-gib 12 \
  --path-limit 2000000 --rotate-algorithms --conditional-repetitions
```

Run only one benchmark worker at a time on the benchmark machine and disable
unrelated workloads. The process-isolated runner performs an untimed tiny
warm-up, rotates algorithm order, records stage times and samples process-tree
resident memory. Repetition 0 screens every pair; repetitions 1 and 2 run only
when repetition 0 succeeds.

## 8. Output verification

Explicit vectors are streamed through an order-independent digest containing a
count, XOR accumulator and modular-sum accumulator. Equality of counts and
digests is checked on jointly solved cases. These checks complement, but do not
replace, the formal proof and the independent exhaustive oracle.

# Follow-up phase diagnostic

The archived follow-up measurements are in `results/phase_diagnostic/` and
come from a separate Linux/Python environment described in the accompanying
JSON file, not from the definitive Windows computer. After installing the
package, reproduce their selection and cross-check against the frozen digests:

```bash
python scripts/phase_ablation.py instances/balanced/synthetic.jsonl instances/balanced/manifest.csv phase_rerun.csv
python scripts/summarize_phase_ablation.py phase_rerun.csv results/balanced/raw.csv
```

The first command can take several minutes because each process has a
30-second time limit. The summary script compares completed output digests
with the archived definitive raw file. Times are expected to vary by machine.

