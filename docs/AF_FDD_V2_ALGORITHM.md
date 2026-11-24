# AF-FDD v0.2.2: authoritative algorithm description

## Why this revision was made

The first comprehensive calibration revealed two different costs: state
explosion during diagram construction, especially on dense cyclic networks,
and traversal of diagram branches that terminate at nonaccepting final states.
Version 0.2 addresses both without changing the represented solution set.

## Lemma 1: positive arcs lie on source-sink paths

Let `x` be a nonzero feasible integral source-sink flow whose positive support
is acyclic. Every arc with positive flow belongs to a directed source-sink path
in that support.

Proof. Take a positive arc `(u,v)`. Repeatedly trace a positive predecessor
from `u`. At a non-source vertex, conservation guarantees such a predecessor.
Because the support is finite and acyclic, this tracing cannot repeat a vertex
and must terminate at the source. Symmetrically, repeatedly tracing a positive
successor from `v` must terminate at the sink. Concatenating the two chains and
`(u,v)` gives a directed source-sink path. Consequently, no positive arc enters
the source or leaves the sink. QED.

This proves the safety of the path-relevance preprocessing. The implementation
uses cheap directed reachability as a sufficient zero-fixing test and also
applies the two terminal-incidence consequences explicitly. It does not claim
that every retained arc occurs in a simple source-sink path.

## Lemma 2: terminal interval bound

At layer `k`, let `b_s,b_t` be the processed net-outflow balances of the source
and sink. Let `[L_s,U_s]` and `[L_t,U_t]` be their possible balance adjustments
on the remaining arcs. A completion requires a common integer demand

`d in [b_s+L_s,b_s+U_s] intersect [-b_t-U_t,-b_t-L_t] intersect [1,infinity)`.

If this intersection is empty, the state is safely rejected.

## Lemma 3: remaining-component invariant

Ignore directions and partition the remaining positive-capacity arcs into
connected components. No later arc crosses between two such components, so
the sum of processed balances in each component is invariant. Its required
final value is zero if the component contains neither terminal or both
terminals, strictly positive if it contains only the source, and strictly
negative if it contains only the sink. A state violating this condition cannot
be completed.

## Productive-node reduction

After an enumeration diagram is built, begin with all accepting terminal nodes
and scan layers backwards. Mark a node productive exactly when it has a child
already marked productive. Explicit output traversal follows only productive
edges. This does not remove any accepted root-to-terminal path and prevents
time from being spent expanding rejected full assignments. Productive flags
are stored in a byte array indexed by node identifier.

## Adaptive order selection in v0.2.2

Fixed-zero arcs are ignored by the reduced-graph frontier estimates and placed
after effective decisions. The selector shallowly probes all deterministic
orders generated on that reduced view. If a shallow probe completes, its best
completed order is used. Otherwise the best three candidates receive deeper
probes. Original-graph candidate orders are consulted only when the reduced-
graph deep probes all remain truncated; their best three shallow candidates
are then deeply probed and compared with the reduced-view finalists. This
conditional fallback preserves difficult cyclic-network robustness without
paying two-view probing overhead on easy instances.

## Default configuration

The default uses path relevance, terminal bounds, remaining-component bounds,
incremental bit closure, and productive output. Exponential frontier-subset
cuts and per-state residual max-flow tests remain optional. They are not
enabled globally because their Python overhead exceeded their pruning benefit
in the controlled tests.

## Experimental rule

All current results must be generated afresh and labelled `AF-FDD-0.2.2`.
Correctness comparisons should use complete output digests whenever feasible;
count-only runs are not substitutes for explicit-enumeration timing.
