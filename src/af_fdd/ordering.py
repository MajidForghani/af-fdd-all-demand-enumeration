from __future__ import annotations

from dataclasses import dataclass
import random

from .model import Network


def natural_order(network: Network) -> tuple[int, ...]:
    return tuple(range(len(network.arcs)))


def _greedy(network: Network, capacity_weight: bool, jitter: dict[int, float] | None = None) -> tuple[int, ...]:
    m = len(network.arcs)
    remaining = set(range(m))
    processed_incident = [0] * network.n
    total_incident = [0] * network.n
    weighted_total = [0] * network.n
    weighted_processed = [0] * network.n
    for arc in network.arcs:
        if arc.capacity == 0:
            continue
        total_incident[arc.tail] += 1
        total_incident[arc.head] += 1
        weighted_total[arc.tail] += arc.capacity
        weighted_total[arc.head] += arc.capacity
    result: list[int] = []
    while remaining:
        best = None
        best_score = None
        for idx in remaining:
            arc = network.arcs[idx]
            if arc.capacity == 0:
                # Fixed-zero arcs do not affect the frontier; place them after
                # all effective decisions for stable, cheap singleton layers.
                score = (10**30, 10**30, 1, 1,
                         jitter.get(idx, 0.0) if jitter else 0.0, 0, idx)
                if best_score is None or score < best_score:
                    best_score, best = score, idx
                continue
            active = weighted_active = 0
            introduced = 0
            for v in range(network.n):
                p = processed_incident[v] + (1 if v == arc.tail or v == arc.head else 0)
                if 0 < p < total_incident[v]:
                    active += 1
                    wp = weighted_processed[v] + (arc.capacity if v == arc.tail or v == arc.head else 0)
                    weighted_active += min(wp, weighted_total[v] - wp)
                if processed_incident[v] == 0 and p > 0:
                    introduced += 1
            continuity_penalty = int(
                bool(result)
                and processed_incident[arc.tail] == 0
                and processed_incident[arc.head] == 0
            )
            primary = weighted_active if capacity_weight else active
            score = (primary, active, continuity_penalty, introduced,
                     jitter.get(idx, 0.0) if jitter else 0.0, -arc.capacity, idx)
            if best_score is None or score < best_score:
                best_score, best = score, idx
        assert best is not None
        remaining.remove(best)
        result.append(best)
        arc = network.arcs[best]
        if arc.capacity == 0:
            continue
        processed_incident[arc.tail] += 1
        processed_incident[arc.head] += 1
        weighted_processed[arc.tail] += arc.capacity
        weighted_processed[arc.head] += arc.capacity
    return tuple(result)


def greedy_frontier_order(network: Network) -> tuple[int, ...]:
    """Greedy order minimizing unweighted active-frontier size."""
    return _greedy(network, False)


def capacity_frontier_order(network: Network) -> tuple[int, ...]:
    """Greedy order accounting for balance ranges as well as frontier size."""
    return _greedy(network, True)


@dataclass(frozen=True, slots=True)
class OrderEstimate:
    order: tuple[int, ...]
    max_frontier: int
    frontier_area: int
    exponential_area: int
    weighted_area: int

    @property
    def score(self) -> tuple[int, int, int, int, tuple[int, ...]]:
        return (self.max_frontier, self.exponential_area, self.weighted_area,
                self.frontier_area, self.order)


def estimate_order(network: Network, order: tuple[int, ...]) -> OrderEstimate:
    remaining = [0] * network.n
    processed = [0] * network.n
    capacity_remaining = [0] * network.n
    capacity_processed = [0] * network.n
    for arc in network.arcs:
        if arc.capacity == 0:
            continue
        for v in (arc.tail, arc.head):
            remaining[v] += 1
            capacity_remaining[v] += arc.capacity
    maximum = area = exponential = weighted = 0
    terminals = {network.source, int(network.sink)}
    for idx in order:
        arc = network.arcs[idx]
        if arc.capacity == 0:
            continue
        for v in (arc.tail, arc.head):
            remaining[v] -= 1
            processed[v] += 1
            capacity_remaining[v] -= arc.capacity
            capacity_processed[v] += arc.capacity
        active = [v for v in range(network.n) if v in terminals or (processed[v] and remaining[v])]
        width = len(active)
        maximum = max(maximum, width)
        area += width
        exponential += 1 << min(width, 60)
        weighted += sum(1 + min(capacity_processed[v], capacity_remaining[v]) for v in active)
    return OrderEstimate(order, maximum, area, exponential, weighted)


def candidate_orders(network: Network, trials: int = 12, seed: int = 4217) -> list[OrderEstimate]:
    rng = random.Random(seed)
    candidates = {natural_order(network), greedy_frontier_order(network), capacity_frontier_order(network)}
    candidates |= {tuple(reversed(order)) for order in tuple(candidates)}
    for _ in range(max(0, trials - len(candidates))):
        jitter = {i: rng.random() for i in range(len(network.arcs))}
        candidates.add(_greedy(network, bool(rng.getrandbits(1)), jitter))
    return sorted((estimate_order(network, order) for order in candidates), key=lambda item: item.score)


def auto_order(network: Network, trials: int = 12, seed: int = 4217) -> tuple[int, ...]:
    """Static-only selector; AFFDD(ordering='auto') additionally runs bounded DD probes."""
    return candidate_orders(network, trials, seed)[0].order

