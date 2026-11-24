# Provenance and frozen-study notes

## Algorithms

- `AF-FDD-v0.2.2`: frozen proposed implementation reported in the manuscript.
- `Bai-2021`: independent reconstruction of Bai et al. (2021).
- `Yeh-2024`: independent reconstruction of Yeh (2024), with recursion replaced
  by an equivalent explicit stack only.

The baseline reconstructions were not augmented with AF-FDD ordering, bounds,
state representations or pruning rules.

## Balanced corpus

The balanced corpus contains 1,200 synthetic cases from a full factorial design
and 72 SNDlib-derived cases. Its master seed is 2026101901. Frozen instance
digests are stored in `instances/balanced/manifest.csv`.

## Challenge corpus terminology

Some source filenames and historical documents contain `heldout`, because that
was the working name when the experiment was frozen. The manuscript and this
repository describe the collection more precisely as an **outcome-informed,
conditionally selected challenge corpus**. Pilot results selected seven whole
structural cells. Replications 100--109 were not used during selection. The
selection audit is retained under `instances/challenge/`.

## Definitive records

- Balanced: 10,318 raw process rows; 1,272 instances.
- Challenge: 456 raw process rows; 70 instances.
- No crash, pending repetition or digest disagreement was recorded.
- No path-limit termination occurred.

Raw files are preserved byte for byte. Derived tables should be recreated in a
new directory rather than overwriting the supplied analysis.

The repository copy of `analyze_comprehensive.py` contains one release-only
robustness correction: an internal-stage speedup is left blank when an older
raw row has no `algorithm_seconds` value. This does not alter any algorithm,
wall-time statistic, solved count, memory result or supplied raw record.

## Validation

The package retains the two validation batches used during AF-FDD development.
The final validation report records 1,546 networks, capacities in \(\{1,2\}\),
capacity boxes up to 13,122 states, 6,487 exact output vectors, and zero
disagreements with the definition-based oracle. The per-batch CSV filenames are
historical and should not be renumbered.

## Nine-instance phase diagnostic

The revised manuscript additionally reports a phase-timing and one-factor
diagnostic on nine fixed balanced-corpus instances: replications 0--2 for
small-capacity sparse DAGs and layered networks at 22 vertices, and dense cyclic
networks at 10 vertices. Family choices were informed by prior balanced-study
outcomes, whereas replications were selected by index before these reruns.
The diagnostic was run separately on Linux with Python 3.12.14, not on the
Windows benchmark PC. The environment metadata is in
`results/phase_diagnostic/phase_ablation_final.json`.

There are 81 attempted runs: 69 completed and 12 timed out. The completed
digests agree with the original AF-FDD records. The tested variants were the
default, input order without probing, and full closure in final construction;
the full-closure variant kept default order probes. The construction time
includes graph-count and productive-node marking, and output time includes
digesting. This is a small descriptive follow-up, not a new cross-algorithm
benchmark or a statistically independent test population.

