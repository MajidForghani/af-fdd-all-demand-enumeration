from __future__ import annotations

import random

from .model import Network


def random_network(
    rng: random.Random,
    n: int,
    m: int,
    capacity_max: int = 2,
    acyclic: bool = False,
) -> Network:
    if m < n - 1:
        raise ValueError("m must allow a guaranteed source-sink backbone")
    possible = [(u, v) for u in range(n) for v in range(n) if u != v]
    if acyclic:
        possible = [(u, v) for u, v in possible if u < v]
    chosen: set[tuple[int, int]] = {(i, i + 1) for i in range(n - 1)}
    candidates = [a for a in possible if a not in chosen]
    rng.shuffle(candidates)
    chosen.update(candidates[: max(0, m - len(chosen))])
    arcs = [(u, v, rng.randint(1, capacity_max)) for u, v in sorted(chosen)]
    return Network.from_tuples(n, arcs)


def layered_network(width: int, layers: int, capacity: int = 1) -> Network:
    """Complete bipartite connections between consecutive layers."""
    if width < 1 or layers < 1:
        raise ValueError("width and layers must be positive")
    source = 0
    layer_nodes: list[list[int]] = []
    next_vertex = 1
    for _ in range(layers):
        nodes = list(range(next_vertex, next_vertex + width))
        layer_nodes.append(nodes)
        next_vertex += width
    sink = next_vertex
    arcs: list[tuple[int, int, int]] = []
    for v in layer_nodes[0]:
        arcs.append((source, v, capacity))
    for left, right in zip(layer_nodes, layer_nodes[1:]):
        for u in left:
            for v in right:
                arcs.append((u, v, capacity))
    for u in layer_nodes[-1]:
        arcs.append((u, sink, capacity))
    return Network.from_tuples(sink + 1, arcs, source, sink)


def grid_network(rows: int, cols: int, capacity: int = 1) -> Network:
    """Right/down directed rectangular grid."""
    if rows < 2 or cols < 2:
        raise ValueError("grid dimensions must be at least two")
    arcs: list[tuple[int, int, int]] = []
    idx = lambda r, c: r * cols + c
    for r in range(rows):
        for c in range(cols):
            if c + 1 < cols:
                arcs.append((idx(r, c), idx(r, c + 1), capacity))
            if r + 1 < rows:
                arcs.append((idx(r, c), idx(r + 1, c), capacity))
    return Network.from_tuples(rows * cols, arcs)

