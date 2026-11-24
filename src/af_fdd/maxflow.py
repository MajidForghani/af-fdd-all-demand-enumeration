from __future__ import annotations

from collections import deque

from .model import Network


def max_flow_value(network: Network, capacities: tuple[int, ...] | list[int]) -> int:
    """Independent integer Dinic implementation, used by the oracle."""
    if len(capacities) != len(network.arcs):
        raise ValueError("capacity vector length mismatch")
    graph: list[list[list[int]]] = [[] for _ in range(network.n)]

    def add_edge(u: int, v: int, cap: int) -> None:
        graph[u].append([v, cap, len(graph[v])])
        graph[v].append([u, 0, len(graph[u]) - 1])

    for arc, cap in zip(network.arcs, capacities):
        add_edge(arc.tail, arc.head, int(cap))

    s, t = network.source, int(network.sink)
    total = 0
    inf = sum(capacities) + 1
    while True:
        level = [-1] * network.n
        level[s] = 0
        queue = deque([s])
        while queue:
            u = queue.popleft()
            for v, cap, _ in graph[u]:
                if cap > 0 and level[v] < 0:
                    level[v] = level[u] + 1
                    queue.append(v)
        if level[t] < 0:
            return total
        it = [0] * network.n

        def send(u: int, amount: int) -> int:
            if u == t:
                return amount
            while it[u] < len(graph[u]):
                edge = graph[u][it[u]]
                v, cap, rev = edge
                if cap > 0 and level[v] == level[u] + 1:
                    pushed = send(v, min(amount, cap))
                    if pushed:
                        edge[1] -= pushed
                        graph[v][rev][1] += pushed
                        return pushed
                it[u] += 1
            return 0

        while True:
            pushed = send(s, inf)
            if not pushed:
                break
            total += pushed

