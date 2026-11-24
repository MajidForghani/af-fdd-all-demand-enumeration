from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import log
from time import perf_counter

from .maxflow import max_flow_value
from .model import Network


Vector = tuple[int, ...]


@dataclass(slots=True)
class BaselineResult:
    algorithm: str
    vectors: set[Vector]
    preprocess_seconds: float
    enumerate_seconds: float
    output_seconds: float = 0.0
    counters: dict[str, int] = field(default_factory=dict)
    audit: dict[str, object] = field(default_factory=dict)


def support_is_acyclic(network: Network, x: Vector) -> bool:
    adjacency = [[] for _ in range(network.n)]
    indegree = [0] * network.n
    active: set[int] = set()
    for arc, value in zip(network.arcs, x):
        if value:
            adjacency[arc.tail].append(arc.head)
            indegree[arc.head] += 1
            active.update((arc.tail, arc.head))
    queue = deque(v for v in active if indegree[v] == 0)
    seen = 0
    while queue:
        u = queue.popleft()
        seen += 1
        for v in adjacency[u]:
            indegree[v] -= 1
            if indegree[v] == 0:
                queue.append(v)
    return seen == len(active)


def simple_path_vectors(network: Network, limit: int | None = None) -> list[Vector]:
    paths: list[Vector] = []
    outgoing: list[list[int]] = [[] for _ in range(network.n)]
    for i, arc in enumerate(network.arcs):
        outgoing[arc.tail].append(i)

    def visit(u: int, visited: set[int], chosen: list[int]) -> None:
        if limit is not None and len(paths) >= limit:
            raise OverflowError("binary path limit exceeded")
        if u == network.sink:
            vector = [0] * len(network.arcs)
            for i in chosen:
                vector[i] = 1
            paths.append(tuple(vector))
            return
        for i in outgoing[u]:
            v = network.arcs[i].head
            if v not in visited:
                visited.add(v)
                chosen.append(i)
                visit(v, visited, chosen)
                chosen.pop()
                visited.remove(v)

    visit(network.source, {network.source}, [])
    return sorted(paths)


def _lambda_set(network: Network, x: Vector, paths: list[Vector]) -> frozenset[int]:
    """Bai's Lambda(X): MP indices whose addition would exceed a capacity."""
    return frozenset(
        i for i, path in enumerate(paths)
        if any(x[k] + path[k] > network.arcs[k].capacity for k in range(len(x)))
    )


@dataclass(frozen=True, slots=True)
class _BaiRecord:
    vector: Vector
    components: tuple[int, ...]
    infeasible_additions: frozenset[int]


def bai2021(network: Network, *, paths: list[Vector] | None = None) -> BaselineResult:
    """Bai et al. (2021), preserving reverse-addition and rho test order.

    ``paths`` is accepted because the published method takes an ordered MP list
    as input, and its rho sets (and therefore its work) are order-dependent.
    Indices stored internally are zero-based.
    """
    start = perf_counter()
    paths = list(paths) if paths is not None else simple_path_vectors(network)
    dmax = max_flow_value(network, network.capacities)
    path_lambdas = [_lambda_set(network, path, paths) for path in paths]
    prep = perf_counter() - start
    start = perf_counter()
    m = len(network.arcs)
    found: set[Vector] = set(paths)
    rho = [set() for _ in paths]
    records: list[_BaiRecord] = []
    first: set[Vector] = set()
    counters = {"binary_paths": len(paths), "candidate_additions": 0,
                "lambda_prevented": 0, "cycle_pruned": 0,
                "rho_pairs_recorded": 0, "rho_prevented": 0,
                "order_prevented": 0, "unexpected_duplicates": 0}
    for i in range(len(paths)):
        for j in range(i, len(paths)):
            # Paper Step 2.1: i not in Lambda(MP_j), before vector addition.
            if i in path_lambdas[j]:
                counters["lambda_prevented"] += 1
                continue
            x = tuple(paths[i][k] + paths[j][k] for k in range(m))
            counters["candidate_additions"] += 1
            if not support_is_acyclic(network, x):
                counters["cycle_pruned"] += 1
                continue
            if x in first:
                rho[i].add(j)
                counters["rho_pairs_recorded"] += 1
                continue
            first.add(x)
            records.append(_BaiRecord(x, (i, j), _lambda_set(network, x, paths)))
            found.add(x)
    for _d in range(3, dmax + 1):
        next_records: list[_BaiRecord] = []
        seen: set[Vector] = set()
        for i, path in enumerate(paths):
            for previous in records:
                if min(previous.components) < i:
                    counters["order_prevented"] += 1
                    continue
                if set(previous.components) & rho[i]:
                    counters["rho_prevented"] += 1
                    continue
                if i in previous.infeasible_additions:
                    counters["lambda_prevented"] += 1
                    continue
                x = tuple(path[k] + previous.vector[k] for k in range(m))
                counters["candidate_additions"] += 1
                if not support_is_acyclic(network, x):
                    counters["cycle_pruned"] += 1
                    continue
                if x in seen:
                    counters["unexpected_duplicates"] += 1
                    continue
                seen.add(x)
                components = (i,) + previous.components
                next_records.append(_BaiRecord(x, components, _lambda_set(network, x, paths)))
                found.add(x)
        records = next_records
        if not records:
            break
    enum = perf_counter() - start
    out_start = perf_counter()
    vectors = set(found)
    output = perf_counter() - out_start
    audit = {
        "rho_one_based": [[j + 1 for j in sorted(values)] for values in rho],
        "dmax": dmax,
        "path_lambda_one_based": [[j + 1 for j in sorted(values)] for values in path_lambdas],
    }
    return BaselineResult("Bai-2021", vectors, prep, enum, output, counters, audit)


def _bounded_sum_states(bounds: list[int], lower: int, upper: int) -> list[tuple[int, ...]]:
    """IBAT solution order without dependence on Python's recursion limit.

    The explicit stack is a mechanical simulation of the former depth-first
    recursion: coordinates are visited from the last to the first and each
    value is tried in increasing order.  The final mixed-radix sort, bounds,
    and candidate set are unchanged; this is an implementation repair rather
    than an additional pruning or search rule.
    """
    states: list[tuple[int, ...]] = []
    if not bounds or upper < lower:
        return states
    for total in range(lower, upper + 1):
        values = [0] * len(bounds)
        # Frames are (coordinate, remaining total, next value to try).
        stack = [(len(bounds) - 1, total, 0)]
        while stack:
            i, remaining, value = stack.pop()
            maximum = min(bounds[i], remaining)
            if value > maximum:
                continue
            stack.append((i, remaining, value + 1))
            values[i] = value
            if i == 0:
                if value == remaining:
                    states.append(tuple(values))
            else:
                stack.append((i - 1, remaining - value, 0))
    radices = []
    multiplier = 1
    for bound in bounds:
        radices.append(multiplier)
        multiplier *= bound + 1
    states.sort(key=lambda state: sum(v * r for v, r in zip(state, radices)))
    return states


def _first_primes(count: int) -> list[int]:
    primes: list[int] = []
    value = 2
    while len(primes) < count:
        if all(value % p for p in primes if p * p <= value):
            primes.append(value)
        value += 1
    return primes


def yeh2024(network: Network, *, paths: list[Vector] | None = None,
            collect_audit: bool = True) -> BaselineResult:
    """Yeh (2024) hybrid inequality-BAT reconstruction.

    The paper's worked model retains every nonredundant simplified arc
    inequality, although its compact-model prose says that a greedy cover may
    omit some.  Retaining all is the correctness-preserving, table-faithful
    interpretation used here; see the audit report.
    """
    start = perf_counter()
    paths = list(paths) if paths is not None else simple_path_vectors(network)
    m = len(network.arcs)
    bounds = [min((network.arcs[k].capacity for k, used in enumerate(path) if used), default=0)
              for path in paths]
    dmax = max_flow_value(network, network.capacities)
    # Complete arc inequalities, deduplicated. Singleton constraints are
    # already represented by the variable bounds.
    inequalities: list[tuple[tuple[int, ...], int]] = []
    seen_ineq: set[tuple[tuple[int, ...], int]] = set()
    for k, arc in enumerate(network.arcs):
        variables = tuple(i for i, path in enumerate(paths) if path[k])
        item = (variables, arc.capacity)
        if len(variables) > 1 and item not in seen_ineq:
            inequalities.append(item)
            seen_ineq.add(item)
    changed = True
    while changed:
        changed = False
        for variables, capacity in inequalities:
            for i in variables:
                if bounds[i] > capacity:
                    bounds[i] = capacity
                    changed = True
        reduced = [(variables, capacity) for variables, capacity in inequalities
                   if sum(bounds[i] for i in variables) > capacity]
        if len(reduced) != len(inequalities):
            inequalities = reduced
            changed = True
    prep = perf_counter() - start

    start = perf_counter()
    upper = min(dmax, sum(bounds))
    candidates = _bounded_sum_states(bounds, 2, upper)
    feasible_states: list[tuple[int, ...]] = []
    failed_by_inequality = [0] * len(inequalities)
    for state in candidates:
        for q, (variables, capacity) in enumerate(inequalities):
            if sum(state[i] for i in variables) > capacity:
                failed_by_inequality[q] += 1
                break
        else:
            feasible_states.append(state)
    enum = perf_counter() - start

    out_start = perf_counter()
    found: set[Vector] = set(paths)
    primes = _first_primes(m)
    lpm_buckets: dict[float, set[Vector]] = {}
    cycle_pruned = duplicate_removed = 0
    trace: list[dict[str, object]] = []
    for state in feasible_states:
        x = tuple(sum(state[i] * paths[i][k] for i in range(len(paths))) for k in range(m))
        cyclic = not support_is_acyclic(network, x)
        score = sum(value * log(prime) for value, prime in zip(x, primes))
        duplicate = False
        if cyclic:
            cycle_pruned += 1
        else:
            bucket = lpm_buckets.setdefault(score, set())
            # Exact vector confirmation prevents floating-point LPM collisions.
            duplicate = x in bucket or x in found
            if duplicate:
                duplicate_removed += 1
            else:
                bucket.add(x)
                found.add(x)
        if collect_audit:
            trace.append({"path_state": state, "arc_state": x, "cycle": cyclic,
                          "lpm": score, "duplicate": duplicate})
    output = perf_counter() - out_start
    counters = {"binary_paths": len(paths), "ibat_states": len(candidates),
                "sequentially_feasible": len(feasible_states),
                "inequality_rejections": len(candidates) - len(feasible_states),
                "cycle_pruned": cycle_pruned, "duplicates_removed": duplicate_removed}
    audit = {"bounds": bounds, "dmax": dmax, "inequalities": inequalities,
             "failed_by_inequality": failed_by_inequality, "trace": trace}
    return BaselineResult("Yeh-2024", found, prep, enum, output, counters, audit)

