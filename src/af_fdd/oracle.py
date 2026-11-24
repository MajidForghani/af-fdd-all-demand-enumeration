from __future__ import annotations

from itertools import product

from .maxflow import max_flow_value
from .model import Network


def is_dmp_by_definition(network: Network, state: tuple[int, ...]) -> int | None:
    """Return d if state is a d-MP, using only the defining max-flow tests."""
    d = max_flow_value(network, state)
    if d <= 0:
        return None
    for i, value in enumerate(state):
        if value:
            reduced = list(state)
            reduced[i] -= 1
            if max_flow_value(network, reduced) >= d:
                return None
    return d


def enumerate_dmp_oracle(network: Network) -> dict[int, set[tuple[int, ...]]]:
    """Exhaust the complete capacity box. Intended only for small validation cases."""
    answer: dict[int, set[tuple[int, ...]]] = {}
    for state in product(*(range(c + 1) for c in network.capacities)):
        d = is_dmp_by_definition(network, state)
        if d is not None:
            answer.setdefault(d, set()).add(state)
    return answer

