from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterator, Literal, TextIO

from .maxflow import max_flow_value
from .model import Network
from .ordering import candidate_orders, capacity_frontier_order, greedy_frontier_order, natural_order


PackedState = tuple[int, int]  # mixed-radix balance code, packed reachability rows


@dataclass(frozen=True, slots=True)
class AFOptions:
    mode: Literal["enumerate", "count"] = "enumerate"
    incremental_closure: bool = True
    balance_bounds: bool = True
    cut_bounds: bool = False
    cut_width_limit: int = 10
    residual_test: bool = False
    residual_cache: bool = True
    order_trials: int = 12
    order_seed: int = 4217
    probe_state_limit: int | None = None
    path_relevance: bool = True
    terminal_bounds: bool = True
    component_bounds: bool = True
    productive_output: bool = True
    legacy_output_reorder: bool = False


@dataclass(slots=True)
class BuildStats:
    preprocessing_seconds: float = 0.0
    build_seconds: float = 0.0
    nodes: int = 0
    transitions: int = 0
    attempted_branches: int = 0
    cycle_pruned: int = 0
    balance_pruned: int = 0
    forgotten_balance_pruned: int = 0
    cut_pruned: int = 0
    residual_pruned: int = 0
    residual_calls: int = 0
    residual_cache_hits: int = 0
    merged_transitions: int = 0
    max_width: int = 0
    outputs: int = 0
    peak_live_states: int = 0
    order_estimation_seconds: float = 0.0
    layers_built: int = 0
    truncated: bool = False
    irrelevant_arcs: int = 0
    terminal_pruned: int = 0
    component_pruned: int = 0
    unproductive_nodes: int = 0


@dataclass(frozen=True, slots=True)
class _LayerPlan:
    current: tuple[int, ...]
    next: tuple[int, ...]
    work: tuple[int, ...]
    old_to_work: tuple[int, ...]
    next_from_work: tuple[int, ...]
    tail: int
    head: int
    forgotten: tuple[int, ...]
    cut_tests: tuple[tuple[tuple[int, ...], int, int], ...]
    component_tests: tuple[tuple[tuple[int, ...], int], ...]


class AFFDD:
    """Optimized frontier DD for all bounded acyclic integral s-t flows.

    ``mode='count'`` streams layers and retains no output graph. Enumeration
    mode stores compact transition arrays and supports streamed output.
    """

    def __init__(
        self,
        network: Network,
        ordering: str | tuple[int, ...] = "auto",
        options: AFOptions | None = None,
    ) -> None:
        preprocessing_start = perf_counter()
        self.network = network
        self.options = options or AFOptions()
        self.effective_capacities = self._effective_capacities()
        order_start = perf_counter()
        if ordering == "v011-auto":
            # Frozen AF-FDD 0.1.1 selector retained solely for paired version
            # comparisons. It deliberately uses the original network and the
            # original four-order shortlist plus required orders.
            estimates = candidate_orders(network, self.options.order_trials, self.options.order_seed)
            shortlist = []
            required = {natural_order(network), greedy_frontier_order(network),
                        capacity_frontier_order(network)}
            for estimate in estimates:
                if len(shortlist) < 4 or estimate.order in required:
                    shortlist.append(estimate.order)
            probes = []
            for order in dict.fromkeys(shortlist):
                probe_options = AFOptions(
                    mode="count", cut_bounds=False, residual_test=False,
                    order_trials=0, probe_state_limit=5_000,
                    path_relevance=False, terminal_bounds=False,
                    component_bounds=False, productive_output=False,
                    legacy_output_reorder=True,
                )
                probe = AFFDD(network, order, probe_options).build()
                score = (probe.stats.truncated, -probe.stats.layers_built,
                         probe.stats.nodes, probe.stats.max_width, order)
                probes.append((score, order))
            self.order = min(probes)[1]
        elif ordering == "auto":
            order_network = Network.from_tuples(
                network.n,
                ((a.tail, a.head, c) for a, c in zip(network.arcs, self.effective_capacities)),
                network.source, int(network.sink),
            )
            reduced_estimates = candidate_orders(
                order_network, self.options.order_trials, self.options.order_seed)

            def probe_orders(orders, limit):
                answers = []
                for order in orders:
                    probe_options = AFOptions(
                        mode="count", cut_bounds=False, residual_test=False,
                        order_trials=0, probe_state_limit=limit,
                        path_relevance=self.options.path_relevance,
                        terminal_bounds=self.options.terminal_bounds,
                        component_bounds=self.options.component_bounds,
                    )
                    probe = AFFDD(network, order, probe_options).build()
                    score = (probe.stats.truncated, -probe.stats.layers_built,
                             probe.stats.nodes, probe.stats.max_width, order)
                    answers.append((score, order))
                return answers

            # First use the reduced graph, which normally gives the best
            # frontier view and avoids needless probes on easy instances.
            reduced_orders = [estimate.order for estimate in reduced_estimates]
            probes = probe_orders(reduced_orders, 1_500)
            completed = [item for item in probes if not item[0][0]]
            if completed:
                self.order = min(completed)[1]
                probes = []
            finalists = [order for _, order in sorted(probes)[:3]]
            deep = probe_orders(finalists, 30_000)
            completed_deep = [item for item in deep if not item[0][0]]
            if completed_deep:
                self.order = min(completed_deep)[1]
            elif deep:
                # Only hard/truncated reduced-view probes justify consulting
                # the original graph.  This recovers strong cyclic orders
                # without imposing dual-view overhead on small diagrams.
                seen_orders = set(reduced_orders)
                original_orders = [estimate.order for estimate in candidate_orders(
                    network, self.options.order_trials, self.options.order_seed)
                    if estimate.order not in seen_orders]
                original_shallow = probe_orders(original_orders, 1_500)
                original_finalists = [order for _, order in sorted(original_shallow)[:3]]
                original_deep = probe_orders(original_finalists, 30_000)
                self.order = min(deep + original_deep)[1]
        elif ordering == "capacity":
            self.order = capacity_frontier_order(network)
        elif ordering == "greedy":
            self.order = greedy_frontier_order(network)
        elif ordering == "natural":
            self.order = natural_order(network)
        elif isinstance(ordering, tuple):
            if sorted(ordering) != list(range(len(network.arcs))):
                raise ValueError("custom ordering is not a permutation")
            self.order = ordering
        else:
            raise ValueError("unknown ordering")
        self.stats = BuildStats(order_estimation_seconds=perf_counter() - order_start,
                                irrelevant_arcs=sum(c == 0 for c in self.effective_capacities))
        self.ordered_arcs = tuple(network.arcs[i] for i in self.order)
        self.vertices_by_layer = self._frontiers()
        self.remaining_bounds = self._remaining_balance_bounds()
        self.balance_specs = self._balance_specs()
        self.plans = self._layer_plans()
        self.layers: list[list[PackedState]] = []
        self.node_ids: list[dict[PackedState, int]] = []
        self.edges: list[tuple[tuple[int, int], ...]] = []
        self.accepting: dict[int, int] = {}
        self.productive = bytearray()
        self._counts: dict[int, int] = {}
        self._residual_cache: dict[tuple[int, int], bool] = {}
        self._built = False
        self.stats.preprocessing_seconds = perf_counter() - preprocessing_start

    def _effective_capacities(self) -> tuple[int, ...]:
        """Force arcs outside every directed s-t path to zero.

        In an acyclic feasible s-t flow, every positive-support arc belongs to
        an s-t path.  Thus this is an exact reduction, not a heuristic.
        """
        if not self.options.path_relevance:
            return tuple(a.capacity for a in self.network.arcs)
        outgoing = [[] for _ in range(self.network.n)]
        incoming = [[] for _ in range(self.network.n)]
        for arc in self.network.arcs:
            outgoing[arc.tail].append(arc.head)
            incoming[arc.head].append(arc.tail)

        def reachable(start: int, adjacency: list[list[int]]) -> set[int]:
            seen = {start}; stack = [start]
            while stack:
                for w in adjacency[stack.pop()]:
                    if w not in seen:
                        seen.add(w); stack.append(w)
            return seen

        from_source = reachable(self.network.source, outgoing)
        to_sink = reachable(int(self.network.sink), incoming)
        s, t = self.network.source, int(self.network.sink)
        caps = tuple(a.capacity if (a.tail in from_source and a.head in to_sink
                                    and a.head != s and a.tail != t) else 0
                     for a in self.network.arcs)
        return caps

    def _frontiers(self) -> list[tuple[int, ...]]:
        m = len(self.ordered_arcs)
        first = [m + 1] * self.network.n
        last = [-1] * self.network.n
        for i, arc in enumerate(self.ordered_arcs):
            if self.effective_capacities[self.order[i]] == 0:
                continue
            for v in (arc.tail, arc.head):
                first[v] = min(first[v], i)
                last[v] = max(last[v], i)
        terminals = {self.network.source, int(self.network.sink)}
        return [tuple(sorted(terminals | {v for v in range(self.network.n) if first[v] < k <= last[v]}))
                for k in range(m + 1)]

    def _remaining_balance_bounds(self) -> list[dict[int, tuple[int, int]]]:
        m = len(self.ordered_arcs)
        result: list[dict[int, tuple[int, int]]] = []
        out_cap = [0] * self.network.n
        in_cap = [0] * self.network.n
        for i, arc in enumerate(self.ordered_arcs):
            cap = self.effective_capacities[self.order[i]]
            out_cap[arc.tail] += cap
            in_cap[arc.head] += cap
        for k in range(m + 1):
            result.append({v: (-in_cap[v], out_cap[v]) for v in range(self.network.n)})
            if k < m:
                arc = self.ordered_arcs[k]
                cap = self.effective_capacities[self.order[k]]
                out_cap[arc.tail] -= cap
                in_cap[arc.head] -= cap
        return result

    def _balance_specs(self) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
        processed_out = [0] * self.network.n
        processed_in = [0] * self.network.n
        specs: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        for layer, vertices in enumerate(self.vertices_by_layer):
            lows = tuple(-processed_in[v] for v in vertices)
            radices: list[int] = []
            multiplier = 1
            for v, low in zip(vertices, lows):
                radices.append(multiplier)
                multiplier *= processed_out[v] - low + 1
            specs.append((lows, tuple(radices)))
            if layer < len(self.ordered_arcs):
                arc = self.ordered_arcs[layer]
                cap = self.effective_capacities[self.order[layer]]
                processed_out[arc.tail] += cap
                processed_in[arc.head] += cap
        return specs

    def _encode_balances(self, layer: int, balances: tuple[int, ...]) -> int:
        lows, radices = self.balance_specs[layer]
        return sum((value - low) * radix for value, low, radix in zip(balances, lows, radices))

    def _decode_balances(self, layer: int, code: int) -> tuple[int, ...]:
        lows, radices = self.balance_specs[layer]
        values = []
        for i, (low, radix) in enumerate(zip(lows, radices)):
            if i + 1 < len(radices):
                base = radices[i + 1] // radix
                digit = (code // radix) % base
            else:
                digit = code // radix
            values.append(low + digit)
        return tuple(values)

    @staticmethod
    def _unpack_rows(bits: int, width: int) -> list[int]:
        mask = (1 << width) - 1
        return [(bits >> (i * width)) & mask for i in range(width)]

    @staticmethod
    def _pack_rows(rows: list[int], width: int) -> int:
        return sum(row << (i * width) for i, row in enumerate(rows))

    def _cut_tests(self, layer: int, vertices: tuple[int, ...]) -> tuple[tuple[tuple[int, ...], int, int], ...]:
        if not self.options.cut_bounds or len(vertices) > self.options.cut_width_limit:
            return ()
        tests: list[tuple[tuple[int, ...], int, int]] = []
        s, t = self.network.source, int(self.network.sink)
        remaining = [(a, self.effective_capacities[self.order[i]])
                     for i, a in enumerate(self.ordered_arcs[layer:], start=layer)]
        # Complementary cuts are equivalent, so fix the first frontier vertex outside.
        for mask in range(1, 1 << len(vertices)):
            if mask & 1:
                continue
            chosen = {vertices[i] for i in range(len(vertices)) if mask & (1 << i)}
            if (s in chosen) != (t in chosen):
                continue
            incoming = sum(c for a, c in remaining if a.tail not in chosen and a.head in chosen)
            outgoing = sum(c for a, c in remaining if a.tail in chosen and a.head not in chosen)
            tests.append((tuple(i for i, v in enumerate(vertices) if v in chosen), incoming, outgoing))
        return tuple(tests)

    def _component_tests(self, layer: int, vertices: tuple[int, ...]) -> tuple[tuple[tuple[int, ...], int], ...]:
        """Remaining-undirected-component balance invariants.

        The sum of current balances in a component of the remaining graph can
        no longer change.  Its required sign is determined by which terminals
        it contains (0: neither/both, +1: source only, -1: sink only).
        """
        if not self.options.component_bounds:
            return ()
        parent = list(range(self.network.n))
        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        def union(a: int, b: int) -> None:
            a, b = find(a), find(b)
            if a != b: parent[b] = a
        for i in range(layer, len(self.ordered_arcs)):
            if self.effective_capacities[self.order[i]]:
                a = self.ordered_arcs[i]; union(a.tail, a.head)
        groups: dict[int, list[int]] = {}
        for i, v in enumerate(vertices):
            groups.setdefault(find(v), []).append(i)
        sroot, troot = find(self.network.source), find(int(self.network.sink))
        tests = []
        for root, indices in groups.items():
            sign = 1 if root == sroot and root != troot else -1 if root == troot and root != sroot else 0
            tests.append((tuple(indices), sign))
        return tuple(tests)

    def _layer_plans(self) -> list[_LayerPlan]:
        plans = []
        for layer, arc in enumerate(self.ordered_arcs):
            current = self.vertices_by_layer[layer]
            nxt = self.vertices_by_layer[layer + 1]
            work = tuple(sorted(set(current) | {arc.tail, arc.head}))
            position = {v: i for i, v in enumerate(work)}
            plans.append(_LayerPlan(
                current, nxt, work,
                tuple(position[v] for v in current),
                tuple(position[v] for v in nxt),
                position[arc.tail], position[arc.head],
                tuple(position[v] for v in work if v not in set(nxt)),
                self._cut_tests(layer + 1, nxt),
                self._component_tests(layer + 1, nxt),
            ))
        return plans

    def _expand_reach(self, layer: int, packed: int) -> list[int]:
        plan = self.plans[layer]
        old = self._unpack_rows(packed, len(plan.current))
        rows = [0] * len(plan.work)
        for old_i, new_i in enumerate(plan.old_to_work):
            row = 0
            for old_j, new_j in enumerate(plan.old_to_work):
                if old[old_i] & (1 << old_j):
                    row |= 1 << new_j
            rows[new_i] = row
        return rows

    def _positive_reach(self, rows: list[int], u: int, v: int) -> list[int] | None:
        if u == v or rows[v] & (1 << u):
            self.stats.cycle_pruned += 1
            return None
        result = rows.copy()
        if not self.options.incremental_closure:
            result[u] |= 1 << v
            for k in range(len(result)):
                for i in range(len(result)):
                    if result[i] & (1 << k):
                        result[i] |= result[k]
            return result
        successors = result[v] | (1 << v)
        predecessor_mask = 1 << u
        for i, row in enumerate(result):
            if row & (1 << u):
                predecessor_mask |= 1 << i
        for i in range(len(result)):
            if predecessor_mask & (1 << i):
                result[i] |= successors
        return result

    def _project_reach(self, rows: list[int], indices: tuple[int, ...]) -> int:
        projected = []
        for old_i in indices:
            row = 0
            for new_j, old_j in enumerate(indices):
                if rows[old_i] & (1 << old_j):
                    row |= 1 << new_j
            projected.append(row)
        return self._pack_rows(projected, len(indices))

    def _passes_bounds(self, layer: int, balances: tuple[int, ...], plan: _LayerPlan) -> bool:
        terminals = {self.network.source, int(self.network.sink)}
        if self.options.balance_bounds:
            for v, bal in zip(plan.next, balances):
                if v in terminals:
                    continue
                low, high = self.remaining_bounds[layer + 1][v]
                if not (bal + low <= 0 <= bal + high):
                    self.stats.balance_pruned += 1
                    return False
        if self.options.terminal_bounds:
            positions = {v: i for i, v in enumerate(plan.next)}
            s, t = self.network.source, int(self.network.sink)
            bs, bt = balances[positions[s]], balances[positions[t]]
            sl, sh = self.remaining_bounds[layer + 1][s]
            tl, th = self.remaining_bounds[layer + 1][t]
            # A common strictly positive final demand must remain possible.
            if max(1, bs + sl, -(bt + th)) > min(bs + sh, -(bt + tl)):
                self.stats.terminal_pruned += 1
                return False
        for indices, sign in plan.component_tests:
            total = sum(balances[i] for i in indices)
            if (sign == 0 and total != 0) or (sign > 0 and total <= 0) or (sign < 0 and total >= 0):
                self.stats.component_pruned += 1
                return False
        for indices, incoming, outgoing in plan.cut_tests:
            total = sum(balances[i] for i in indices)
            if not (total - incoming <= 0 <= total + outgoing):
                self.stats.cut_pruned += 1
                return False
        if self.options.residual_test and not self._residual_feasible(layer + 1, plan.next, balances):
            self.stats.residual_pruned += 1
            return False
        return True

    def _residual_feasible(self, layer: int, vertices: tuple[int, ...], balances: tuple[int, ...]) -> bool:
        code = self._encode_balances(layer, balances)
        key = (layer, code)
        if self.options.residual_cache and key in self._residual_cache:
            self.stats.residual_cache_hits += 1
            return self._residual_cache[key]
        self.stats.residual_calls += 1
        # Complete the partial assignment iff a remaining transshipment exists.
        n = self.network.n
        ss, tt = n, n + 1
        arcs = [(a.tail, a.head, a.capacity) for a in self.ordered_arcs[layer:]]
        total_capacity = sum(a.capacity for a in self.ordered_arcs[layer:]) + sum(abs(x) for x in balances)
        arcs.append((int(self.network.sink), self.network.source, max(1, total_capacity)))
        full_balance = [0] * n
        for v, value in zip(vertices, balances):
            full_balance[v] = value
        supply = 0
        for v, value in enumerate(full_balance):
            required_out = -value
            if required_out > 0:
                arcs.append((ss, v, required_out))
                supply += required_out
            elif required_out < 0:
                arcs.append((v, tt, -required_out))
        feasible = max_flow_value(Network.from_tuples(n + 2, arcs, ss, tt), tuple(c for _, _, c in arcs)) == supply
        if self.options.residual_cache:
            self._residual_cache[key] = feasible
        return feasible

    def _children(self, layer: int, state: PackedState) -> Iterator[tuple[int, PackedState]]:
        plan = self.plans[layer]
        arc = self.ordered_arcs[layer]
        capacity = self.effective_capacities[self.order[layer]]
        balances = self._decode_balances(layer, state[0])
        work_bal = [0] * len(plan.work)
        for old_i, new_i in enumerate(plan.old_to_work):
            work_bal[new_i] = balances[old_i]
        zero_rows = self._expand_reach(layer, state[1])
        positive_rows = self._positive_reach(zero_rows, plan.tail, plan.head) if capacity else None
        next_set = set(plan.next)
        terminals = {self.network.source, int(self.network.sink)}
        for value in range(capacity + 1):
            self.stats.attempted_branches += 1
            rows = zero_rows if value == 0 else positive_rows
            if rows is None:
                continue
            candidate = work_bal.copy()
            if value:
                candidate[plan.tail] += value
                candidate[plan.head] -= value
            invalid = False
            for work_i in plan.forgotten:
                vertex = plan.work[work_i]
                if vertex not in terminals and vertex not in next_set and candidate[work_i] != 0:
                    self.stats.forgotten_balance_pruned += 1
                    invalid = True
                    break
            if invalid:
                continue
            next_balances = tuple(candidate[i] for i in plan.next_from_work)
            if not self._passes_bounds(layer, next_balances, plan):
                continue
            yield value, (self._encode_balances(layer + 1, next_balances),
                          self._project_reach(rows, plan.next_from_work))

    def build(self) -> "AFFDD":
        if self._built:
            return self
        start = perf_counter()
        root_bal = tuple(0 for _ in self.vertices_by_layer[0])
        root = (self._encode_balances(0, root_bal), 0)
        if self.options.mode == "count":
            self._build_count(root)
        else:
            self._build_enumeration(root)
        self.stats.build_seconds = perf_counter() - start
        self._built = True
        return self

    def _final_d(self, state: PackedState) -> int | None:
        balances = self._decode_balances(len(self.ordered_arcs), state[0])
        vertices = self.vertices_by_layer[-1]
        d = balances[vertices.index(self.network.source)]
        return d if d > 0 and balances[vertices.index(int(self.network.sink))] == -d else None

    def _build_count(self, root: PackedState) -> None:
        current = {root: 1}
        self.stats.nodes = 1
        for layer in range(len(self.ordered_arcs)):
            nxt: dict[PackedState, int] = {}
            for state, ways in current.items():
                for _, child in self._children(layer, state):
                    self.stats.transitions += 1
                    if child in nxt:
                        self.stats.merged_transitions += 1
                        nxt[child] += ways
                    else:
                        nxt[child] = ways
            self.stats.nodes += len(nxt)
            self.stats.max_width = max(self.stats.max_width, len(nxt))
            self.stats.peak_live_states = max(self.stats.peak_live_states, len(current) + len(nxt))
            current = nxt
            self.stats.layers_built = layer + 1
            if self.options.probe_state_limit is not None and self.stats.nodes > self.options.probe_state_limit:
                self.stats.truncated = True
                return
        for state, ways in current.items():
            d = self._final_d(state)
            if d is not None:
                self._counts[d] = self._counts.get(d, 0) + ways
        self.stats.outputs = sum(self._counts.values())

    def _build_enumeration(self, root: PackedState) -> None:
        self.layers = [[root]]
        self.node_ids = [{root: 0}]
        self.edges = [()]
        next_id = 1
        for layer in range(len(self.ordered_arcs)):
            new_states: list[PackedState] = []
            new_ids: dict[PackedState, int] = {}
            for state in self.layers[layer]:
                parent = self.node_ids[layer][state]
                outgoing = []
                for value, child_state in self._children(layer, state):
                    child = new_ids.get(child_state)
                    if child is None:
                        child = next_id
                        next_id += 1
                        new_ids[child_state] = child
                        new_states.append(child_state)
                        self.edges.append(())
                    else:
                        self.stats.merged_transitions += 1
                    outgoing.append((value, child))
                    self.stats.transitions += 1
                self.edges[parent] = tuple(outgoing)
            self.layers.append(new_states)
            self.node_ids.append(new_ids)
            self.stats.max_width = max(self.stats.max_width, len(new_states))
            self.stats.peak_live_states = max(self.stats.peak_live_states, len(new_states))
            self.stats.layers_built = layer + 1
        for state in self.layers[-1]:
            d = self._final_d(state)
            if d is not None:
                self.accepting[self.node_ids[-1][state]] = d
        self.stats.nodes = next_id
        self._counts = self._graph_counts()
        self.stats.outputs = sum(self._counts.values())
        if self.options.productive_output:
            self._mark_productive()

    def _mark_productive(self) -> None:
        productive = bytearray(self.stats.nodes)
        for node in self.accepting:
            productive[node] = 1
        for layer in range(len(self.ordered_arcs) - 1, -1, -1):
            for state in self.layers[layer]:
                node = self.node_ids[layer][state]
                if any(productive[child] for _, child in self.edges[node]):
                    productive[node] = 1
        self.productive = productive
        self.stats.unproductive_nodes = self.stats.nodes - sum(productive)

    def _graph_counts(self) -> dict[int, int]:
        counts = {0: 1}
        for layer in range(len(self.ordered_arcs)):
            nxt: dict[int, int] = {}
            for state in self.layers[layer]:
                parent = self.node_ids[layer][state]
                for _, child in self.edges[parent]:
                    nxt[child] = nxt.get(child, 0) + counts.get(parent, 0)
            counts = nxt
        answer: dict[int, int] = {}
        for node, d in self.accepting.items():
            answer[d] = answer.get(d, 0) + counts.get(node, 0)
        return dict(sorted(answer.items()))

    def count_by_d(self) -> dict[int, int]:
        if not self._built:
            self.build()
        return dict(sorted(self._counts.items()))

    def iter_solutions(self, limit: int | None = None) -> Iterator[tuple[int, tuple[int, ...]]]:
        if not self._built:
            self.build()
        if self.options.mode != "enumerate":
            raise RuntimeError("explicit solutions require mode='enumerate'")
        m = len(self.ordered_arcs)
        # Store choices directly in original arc coordinates.  This avoids an
        # O(m) Python reordering loop for every emitted vector.
        chosen = [0] * m
        emitted = 0

        def visit(layer: int, node: int) -> Iterator[tuple[int, tuple[int, ...]]]:
            nonlocal emitted
            if limit is not None and emitted >= limit:
                return
            if layer == m:
                d = self.accepting.get(node)
                if d is not None:
                    emitted += 1
                    if self.options.legacy_output_reorder:
                        original = [0] * m
                        for ordered_i, original_i in enumerate(self.order):
                            original[original_i] = chosen[ordered_i]
                        yield d, tuple(original)
                    else:
                        yield d, tuple(chosen)
                return
            for value, child in self.edges[node]:
                if self.options.productive_output and not self.productive[child]:
                    continue
                if self.options.legacy_output_reorder:
                    chosen[layer] = value
                else:
                    chosen[self.order[layer]] = value
                yield from visit(layer + 1, child)

        yield from visit(0, 0)

    def stream_solutions(
        self,
        target: str | Path | TextIO | Callable[[int, tuple[int, ...]], None],
        limit: int | None = None,
    ) -> int:
        close = False
        if isinstance(target, (str, Path)):
            handle: TextIO | None = Path(target).open("w", encoding="utf-8")
            close = True
            callback = None
        elif callable(target):
            handle = None
            callback = target
        else:
            handle = target
            callback = None
        count = 0
        try:
            for d, vector in self.iter_solutions(limit):
                if callback:
                    callback(d, vector)
                else:
                    assert handle is not None
                    handle.write(f"{d}," + ",".join(map(str, vector)) + "\n")
                count += 1
        finally:
            if close and handle is not None:
                handle.close()
        return count

    def solution_sets(self) -> dict[int, set[tuple[int, ...]]]:
        answer: dict[int, set[tuple[int, ...]]] = {}
        for d, state in self.iter_solutions():
            answer.setdefault(d, set()).add(state)
        return answer
