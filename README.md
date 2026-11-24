# AF-FDD: all-demand d-minimal-path enumeration

This repository is the reproducibility package for the manuscript
**“An Arc-Flow Frontier Decision Diagram for Duplicate-Free Enumeration of All
*d*-Minimal Paths at All Demand Levels”**, by Majid Forghani-elahabad and
Wei-Chang Yeh.

It contains the frozen AF-FDD v0.2.2 implementation, independent
paper-faithful reconstructions of Bai-2021 and Yeh-2024, the benchmark
generators and frozen instances, exhaustive-oracle validation records, raw
per-process measurements, and the scripts used to obtain the reported
summaries.

## Benchmark computer

The definitive balanced and challenge experiments ran on the same Dell
OptiPlex SFF Plus 7010 under 64-bit Windows 11, with an Intel Core i7-13700
processor (16 physical cores and 24 logical processors), 32 GB of RAM, and
KIOXIA BG6 NVMe SSD storage. The balanced experiments used 64-bit Anaconda
Python 3.12.15 and the challenge experiments used 3.12.16. See
[`HARDWARE.md`](HARDWARE.md) for the environment and run limits.

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
retain the notice in [`data/sndlib/TOPOHUB_LICENSE.txt`](data/sndlib/TOPOHUB_LICENSE.txt).

## Citation

Citation metadata for this repository is available in
[`CITATION.cff`](CITATION.cff). When citing the computational artifact, include
the release tag or commit hash you used.

