# Reproducibility audit: Bai et al. (2021) and Yeh (2024)

**Original audit date:** 19 October 2026  
**Implementation-fidelity recheck:** 22 October 2026  
**Purpose:** determine whether the two literature baselines are implemented faithfully enough for a publication-grade comparison with AF-FDD.

## Executive finding

The earlier Bai reconstruction was substantively close but did not apply the published infeasibility set, `Lambda(X)`, at the prescribed early-rejection point. The earlier Yeh reconstruction was **not a faithful runtime baseline**: it used a generic capacity-pruned recursion rather than Yeh's compact MP model, inequality BAT, sequential verification, MP-to-arc conversion, cycle test, and LPM. Both have now been replaced by auditable reconstructions.

The revised code exactly reproduces the worked numerical examples in both papers and agrees with an independent exhaustive oracle on 200 seeded random small networks. This establishes strong functional evidence, but not identity with the authors' unavailable source code or their machine-level timings.

## Scope and evidentiary limits

Every fully specified worked example, intermediate set, ordering rule, and reported count was reproduced. Published timing tables cannot be recreated exactly because the papers do not supply the original source code, compiler settings, complete instance files/random seeds, operating-system state, or original hardware. They are therefore treated as reported experiments, not reproducible worked examples.

Both papers take an ordered list of minimal paths as input. Path discovery time is included in preprocessing in our package; experiments may additionally report totals with a shared, precomputed path list.

No new pruning rule, candidate ordering, or bound has been added to either
literature baseline. Optimizations developed for AF-FDD are not shared with
Bai-2021 or Yeh-2024.

## Bai et al. (2021): line-by-line correspondence

| Paper condition | Implementation decision | Verification |
|---|---|---|
| Step 1: initialize `rho`, find `dmax`, calculate `Lambda(MP_i)` | Max flow and path-level infeasible-addition sets are preprocessing. | `dmax=4` and all eight sets match. |
| Step 2.1: use `j>=i` and `i` not in `Lambda(MP_j)` | Outer `i`, inner increasing `j`; Lambda is tested before addition. | Ordering matches Tables II and VII-VIII. |
| Step 2.2: remove cyclic candidates | Directed-support acyclicity is tested by topological sorting. | No worked-example 2-MP is cyclic, as reported. |
| Step 2.3: retain first equal vector; record later pair in `rho(MP_i)` | Exact vectors preserve traversal order and identify the later pair. | All five equalities and rho sets match. |
| Step 2.4: calculate `ccom`, `mincom`, and `Lambda` | Component indices are a nondecreasing tuple, preserving multiplicity. | Intermediate and final counts match. |
| Step 3.3: `mincom(previous)>=i` | Tested before construction. | Reverse-addition order is exact. |
| Step 3.3: `ccom(previous)` intersect `rho(MP_i)` is empty | Tested before construction. | No residual duplicate occurs. |
| Step 3.3: `i` not in `Lambda(previous)` | Tested before construction. | Capacity-infeasible additions are rejected early. |
| Step 3.4: remove cycles | Same directed-support test. | Final level counts match. |

### Reproduced Bai values

- All eight Table-I MPs.
- `Lambda(MP_1),...,Lambda(MP_8)` (one-based): `{1,2}`, `{1,2,4,7}`, `{3,4,5}`, `{2,3,4,5,7}`, `{3,4,5,8}`, empty, `{2,4,7}`, `{5,8}`.
- Duplicate pairs removed: `(2,3)`, `(2,6)`, `(4,6)`, `(5,6)`, `(5,7)`.
- `rho`: empty, `{3,6}`, empty, `{6}`, `{6,7}`, empty, empty, empty.
- Counts by demand: 8 at `d=1`, 16 at `d=2`, 8 at `d=3`, 1 at `d=4`.
- The eight published 3-MP vectors and maximum vector `(2,2,1,1,2,1,1,2,2)` are exact.

### Bai ambiguities and decisions

- “Two MPs are listed in Table II” means “2-MPs,” not two objects; 16 are retained.
- `ccom` is called a set although repeated use of one MP is legal. A tuple preserves multiplicity while giving the same membership, intersection, and minimum tests.
- “Recursive comparison” has no specified data structure. Exact tuple hashing implements the same retain-first relation without changing order.
- The ordered MP list is not assigned a universal enumeration rule. The paper's order is injected for reproduction; experiments must freeze an order.

## Yeh (2024): line-by-line correspondence

| Paper stage | Implementation decision | Verification |
|---|---|---|
| Complete MP model | One bound per path and one capacity inequality per distinct multi-path arc. | Bounds are `(1,1,2,1)`. |
| Simplification | Tighten bounds, remove redundant inequalities, repeat to a fixed point. | Eqs. (20)-(22) remain. |
| Compact model | Retain all nonredundant simplified inequalities. | Table-faithful and correctness-preserving. |
| Inequality BAT | Generate only total-flow-feasible bounded states; `f1` is least significant. | All 14 Table-2 states occur in order. |
| Sequential verification | Test in model order; stop at first violation. | Nine states remain. |
| MP-to-arc conversion | `x_k` sums flows on paths containing `a_k`. | All nine Table-3 vectors match. |
| Cycle test | Directed-support topological test. | Exactly states 7 and 9 are removed. |
| LPM | Compute the log-prime score and confirm equality by exact vector within a score bucket. | Displayed scores match; floating collisions cannot corrupt results. |

### Reproduced Yeh values

- Compact model: total flow 2 through 3; `f3+f4<=2`, `f1+f4<=1`, `f2+f3<=2`; bounds `(1,1,2,1)`.
- Inequality-BAT states: 14 in exact Table-2 order.
- Sequentially feasible states: 9.
- Transformed states: all nine Table-3 vectors.
- Cyclic states: `(1,1,1,1,1,1)` and `(1,2,1,1,1,2)`.
- Final noncyclic, unique outputs at levels at least 2: 7.

### Yeh contradictions and controlling decisions

| Inconsistency | Controlling interpretation |
|---|---|
| Illustrative upper bound 4 conflicts with Eq. (19), `dmax`, and Table 2 (3). | Use 3. |
| Prose says “two” arc inequalities; Eqs. (20)-(22) and Table 2 use three. | Use all three. |
| Greedy compact pseudocode may omit a nonredundant constraint because its variables occur elsewhere; coverage does not imply that constraint. | Default to all nonredundant inequalities. |
| Sequential pseudocode starts `i=0` for `F1,...` and rejection jumps to itself. | Use one-based semantics and advance after rejection. |
| Section 4.2 prose gives inconsistent rejected-state labels. | Evaluate Table-2 inequalities directly. |
| Illustrative conversion prints `x3=f3`, `x6=f3+f3`; Eq. (26)/Table 3 use `x3=f2`, `x6=f2+f3`. | Use Eq. (26)/Table 3. |
| Illustrative LPM set inserts the wrong score and later names the wrong state. | Recompute from the stated formula. |
| Step 10 lists nine states, including two cyclic ones; Table 3 and prose say seven remain. | Return seven. |

### Recursion-limit repair in the Yeh reconstruction

The candidate generator originally used Python recursion only as an
implementation device. With more than roughly 1,000 path coordinates, it could
raise `RecursionError` before evaluating a candidate; this limitation is not a
condition of Yeh's algorithm. It has been replaced by an explicit stack that
mechanically simulates the same depth-first loops. Bounds, total-flow range,
coordinate significance, final mixed-radix ordering, and all later tests are
unchanged. A regression test compares the recursive reference and iterative
implementation state-for-state on multiple bound vectors; another verifies
operation with 1,200 coordinates. This is classified as a language-level
correctness repair, not an algorithmic improvement.

The compact-model inconsistency remains visible. Retaining all nonredundant
arc inequalities is the table-consistent interpretation and is necessary to
reproduce the example and avoid accepting capacity-infeasible states. It is not
presented as an enhancement to Yeh's method. A literal reading of the conflicting
greedy prose may omit a necessary inequality; such a variant would not be used
as the principal baseline without being separately labelled and shown to be
correct.

## Ordering and duplicate prevention

Bai is order-dependent: the first equal arc vector is retained and the later pair defines rho. The implementation keeps the exact nested reverse-addition order.

Yeh treats `f1` as the least-significant mixed-radix coordinate. We generate only bounded compositions in the total-flow interval and order them by the equivalent rank, reproducing Table 2 without materializing the full Cartesian product. LPM remains an output filter. Exact tuple confirmation addresses the floating-point flaw already noted by Bai et al. (2021).

## Phase-separated timing

| Phase | Bai (2021) | Yeh (2024) |
|---|---|---|
| Preprocessing | MP generation, max flow, path Lambda sets | MP generation, max flow, bounds, complete/simplified inequalities |
| Enumeration | additions; Lambda/order/rho tests; cycle tests; records | inequality-BAT generation and sequential verification |
| Output | canonical materialization | MP-to-arc conversion, cycle test, LPM/exact duplicate confirmation |

Report all phases and total. A second total excluding common MP generation is legitimate only when all methods receive the same frozen path list. Do not mix conventions.

## Validation performed

- Eleven unit tests pass, including both complete literature examples and two
  iterative-generator equivalence/robustness tests.
- 200 seeded random directed networks (3-6 vertices, mixed capacities, with/without reverse arcs) were checked against exhaustive arc-state enumeration.
- Bai, Yeh, and the oracle produced identical sets in all 200 cases.
- Assertions cover Bai's exact Lambda/rho sets and 8/16/8/1 counts; Yeh's 14-state order, 9/2/7 filters, and final vectors.

Run:

```bash
cd af_fdd_prototype
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Publication conclusion

Bai-2021 and Yeh-2024 are defensible principal baselines as the most recent directly relevant methods identified from two major algorithm lines. “Latest” must not be presented as automatically “fastest”; any state-of-the-art claim needs the papers' comparison evidence.

The reconstructions are suitable for controlled benchmarking with two disclosures: they are independent implementations, not author-supplied programs; and Yeh's ambiguous compact rule uses the correctness-preserving, table-faithful interpretation. Any alternative greedy interpretation should be a separately labeled sensitivity run.
