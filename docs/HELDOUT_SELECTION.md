# Frozen held-out challenge selection

The challenge pilot contained 204 instances in 51 predeclared cells. The
frozen whole-cell eligibility rule selected seven cells and therefore 70
untouched held-out instances (ten replications per cell):

| Family | Vertices | Capacities |
|---|---:|---|
| sparse cyclic/path-rich | 22 | U{1,2} |
| layered/path-rich | 22 | U{1,2} |
| layered/path-rich | 22 | U{1,2,3} |
| layered/path-rich | 26 | U{1,2} |
| layered/path-rich | 26 | U{1,2,3} |
| layered/path-rich | 26 | U{1,...,5} |
| layered/path-rich | 30 | U{1,2} |

The selected records are exact copies of records in the previously frozen
`challenge_heldout.jsonl` candidate pool. Their IDs, seeds, arc order,
capacities, and SHA-256 instance hashes have not been regenerated or changed.

The selection audit is stored in
`study/instances/challenge_selection_audit.csv`; the machine-readable summary
is `study/instances/challenge_selection_summary.json`.

Every algorithm-instance pair receives repetition 0. Repetitions 1 and 2 are
run only after a successful first run. A median is reported only after three
successful repetitions. The 600-second and 12-GiB limits and the 2,000,000
binary-path limit are unchanged.

The raw results preserve three timing measures:

- `process_wall_seconds`: complete parent-observed process time;
- `worker_wall_seconds`: worker time after its untimed warm-up;
- `algorithm_seconds`: preprocessing + enumeration/build + explicit output.

The legacy `wall_seconds` field remains identical to
`process_wall_seconds` for compatibility with the balanced-study analysis.
