# Held-out large-instance challenge protocol

## Purpose

This collection estimates the regime in which differences are practically
material. It supplements rather than replaces the balanced 1,272-instance
study. Easy cases remain in the balanced study and may not be removed because
another algorithm is faster on them.

## Frozen candidate design

The candidate design has 51 cells and uses source 0 and sink `n-1` fixed by a
constructive path-rich topology. The families are layered and mesh networks at
`n = 22, 26, 30, 34`; dense DAG and sparse cyclic networks at
`n = 22, 26, 30`; and dense cyclic networks at `n = 10, 12, 14`. Every cell is
crossed with capacities sampled independently from U{1,2}, U{1,2,3}, or
U{1,...,5}.

The seed is derived by SHA-256 from master seed `2026102301`, the split, and
all factor labels. The four pilot replications per cell use indices 0--3. The
ten held-out replications use indices 100--109 and a distinct split label.
Thus the pilot has 204 cases and the untouched candidate set has 510 cases.

## Cell-selection rule

Selection is performed on the pilot only, never on an individual case. A cell
is eligible for the final challenge set when:

1. at least two of its four pilot cases are solved by at least two algorithms;
2. at least two pilot cases are practically nontrivial, meaning that either
   two algorithms take at least 1 second or at least one algorithm reaches a
   resource limit; and
3. no unresolved output-digest disagreement occurs.

All ten untouched replications from every eligible cell enter the final set.
The rule, limits, software, and candidate files are frozen before the pilot is
run. If too few or no cells qualify, the result is reported; thresholds are
not relaxed after observing outcomes.

## Interpretation

The challenge set is deliberately conditional on difficult structural cells,
so it must be labelled as such. It supports conclusions about large/path-rich
instances, not about universal average performance. Results from the balanced
study and the challenge study must be reported separately.

Do not claim that real-world networks are invariably large or difficult.
The defensible motivation is that practical network models can be large or
path-rich and exact all-demand enumeration can become computationally
demanding; millisecond differences on easy cases have limited practical
importance but remain part of the complete evidence.
