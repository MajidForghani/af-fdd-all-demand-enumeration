# AF-FDD: all-demand d-minimal-path enumeration

This repository is the reproducibility package for the manuscript
**“An Arc-Flow Frontier Decision Diagram for Duplicate-Free Enumeration of All
\(d\)-Minimal Paths at All Demand Levels”**, by Majid Forghani-elahabad and
Wei-Chang Yeh.

It contains the frozen AF-FDD v0.2.2 implementation, independent
paper-faithful reconstructions of Bai-2021 and Yeh-2024, the benchmark
generators and frozen instances, exhaustive-oracle validation records, raw
per-process measurements, and the scripts used to obtain the reported
summaries.

> **Status before public release.** The supplied CPU and RAM details are
> documented in `HARDWARE.md`, along with core counts and the verified NVMe
> SSDs. Benchmark-machine attribution and workload conditions still need
> confirmation. Add the repository URL and a permanent
> archive identifier after those are created.

## Main results included

| Collection | Instances | AF-FDD solved | Bai-2021 solved | Yeh-2024 solved |
|---|---:|---:|---:|---:|
| Balanced corpus | 1,272 | 1,140 | 1,121 | 990 |
| Conditionally selected challenge corpus | 70 | 65 | 50 | 8 |

The balanced corpus is the primary evidence. The 70-instance challenge corpus
is outcome-informed: seven structural cells were selected using separate pilot
outcomes, while replications 100--109 within the selected cells were untouched.
It is therefore a targeted stress corpus, not an unbiased held-out population.

All algorithms produced identical output counts and order-independent digests
on every jointly solved instance. The 2,000,000 binary-path safety threshold
caused **zero** terminations in both definitive collections.

## Repository map

```text
src/af_fdd/                 AF-FDD, Bai-2021, Yeh-2024, generators and runners
tests/                      unit, audit and literature-example tests
data/sndlib/                source topology data and its license notice
instances/balanced/         frozen 1,272-instance balanced corpus
instances/challenge/        frozen selected challenge corpus and audit trail
results/balanced/           10,318 raw process records and derived analysis
results/challenge/          456 raw process records and derived analysis
results/validation/         exhaustive-oracle validation records
results/phase_diagnostic/   nine-instance phase-timing diagnostic and metadata
docs/                       algorithm, design and literature-audit documents
scripts/                    Windows helpers and manual study entry points
figures/                    vector and raster manuscript figures
make_manuscript_figures.py  regenerates the two reported figures
HARDWARE.md                 benchmark machine details and remaining questions
REPRODUCE.md                commands for validation, reruns and reanalysis
PROVENANCE.md               versions, seeds, naming and interpretation notes
MANIFEST_SHA256.txt         release-file integrity hashes
```

## Quick validation

With Anaconda Prompt or another Python environment:

```bash
conda env create -f environment.yml
conda activate af-fdd-reproduction
python -m pip install -e .
python -m pytest -q
python -m af_fdd.validation
```

The full definitive experiment can require many days because every
algorithm--instance pair is isolated, limited to 600 seconds and 12 GiB, and
successful pairs are measured three times. See [`REPRODUCE.md`](REPRODUCE.md)
before starting it.

## Baseline scope

The Bai-2021 and Yeh-2024 programs are independent reconstructions from their
published algorithms; they are not author-supplied executables. The published
worked examples, pseudocode conditions and ambiguity resolutions were audited.
Yeh's recursive control flow was translated into an equivalent explicit stack
to avoid Python recursion-depth failure; its mathematical search rules were not
strengthened. See [`docs/LITERATURE_AUDIT.md`](docs/LITERATURE_AUDIT.md).

## License and third-party data

The source code is released under the MIT License. SNDlib-derived topology data
retain the notice in `data/sndlib/TOPOHUB_LICENSE.txt`. If journal or repository
policy requires a different treatment of those topology files, retain the
generators and replace the distributed topology copies with documented download
instructions.

## Citation

`CITATION.cff` names the manuscript authors. Add the actual GitHub URL and,
if an archive is created, its DOI when available. Until the paper is published,
cite the repository release and manuscript title.

