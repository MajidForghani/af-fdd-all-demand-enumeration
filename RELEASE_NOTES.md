# Release notes: v1.0.0

Initial reproducibility release for the AF-FDD all-demand enumeration study.

Included:

- AF-FDD v0.2.2 and the audited Bai-2021 and Yeh-2024 reconstructions;
- frozen balanced and conditionally selected challenge instances;
- 10,774 definitive raw process records across both collections;
- exhaustive-oracle validation records;
- complete analysis products and manuscript-figure generator;
- deterministic seeds, instance hashes, environment records and run commands.

Repository-assembly correction:

- `analyze_comprehensive.py` now leaves an internal-stage speedup blank when an
  older raw record lacks `algorithm_seconds`; this affects neither algorithms
  nor any reported wall-time or coverage result.

The subsequent package update adds the two manuscript authors, supplied hardware
details, and the nine-instance phase diagnostic from the revised manuscript.
Before public release, confirm the remaining `HARDWARE.md` fields and add the
repository URL. No original definitive benchmark records were changed.

