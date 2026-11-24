from __future__ import annotations

import hashlib
import json
import math
import random
from collections import deque
from pathlib import Path

from .model import Network

MASTER_SEED = 2026101901
FAMILIES = ("dag_sparse", "dag_dense", "cyclic_sparse", "cyclic_dense", "layered", "mesh")
SIZE_CLASSES = (10, 14, 18, 22)
CAPACITY_REGIMES = ("small", "moderate")
CHALLENGE_MASTER_SEED = 2026102301
CHALLENGE_CAPACITY_UPPERS = (2, 3, 5)
CHALLENGE_FAMILY_SIZES = {
    "layered_path_rich": (22, 26, 30, 34),
    "mesh_path_rich": (22, 26, 30, 34),
    "dag_dense_path_rich": (22, 26, 30),
    "cyclic_sparse_path_rich": (22, 26, 30),
    "cyclic_dense_path_rich": (10, 12, 14),
}


def derived_seed(*parts: object, master: int = MASTER_SEED) -> int:
    payload = "|".join(map(str, (master,) + parts)).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _reachable_pairs(n: int, arcs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    outgoing = [[] for _ in range(n)]
    for u, v in arcs: outgoing[u].append(v)
    answer = []
    for s in range(n):
        seen = {s}; queue = deque([s])
        while queue:
            u = queue.popleft()
            for v in outgoing[u]:
                if v not in seen: seen.add(v); queue.append(v)
        answer.extend((s, t) for t in seen if t != s)
    return answer


def _relabel(n: int, arcs: list[tuple[int, int]], s: int, t: int, rng: random.Random):
    middle = [v for v in range(n) if v not in (s, t)]; rng.shuffle(middle)
    mapping = {s: 0, t: n - 1, **{v: i + 1 for i, v in enumerate(middle)}}
    relabeled = [(mapping[u], mapping[v]) for u, v in arcs]
    rng.shuffle(relabeled)
    return relabeled


def _capacitate(arcs: list[tuple[int, int]], regime: str, rng: random.Random):
    upper = 2 if regime == "small" else 5
    return [(u, v, rng.randint(1, upper)) for u, v in arcs]


def _sample_directed(n: int, m: int, acyclic: bool, rng: random.Random):
    for attempt in range(1, 10001):
        if acyclic:
            permutation = list(range(n)); rng.shuffle(permutation)
            possible = [(permutation[i], permutation[j]) for i in range(n) for j in range(i + 1, n)]
        else:
            possible = [(u, v) for u in range(n) for v in range(n) if u != v]
        arcs = rng.sample(possible, min(m, len(possible)))
        # Preserve the conditioning principle in the supplied benchmark guide:
        # reject disconnected draws rather than silently changing their density.
        undirected = [[] for _ in range(n)]
        for u, v in arcs:
            undirected[u].append(v); undirected[v].append(u)
        seen = {0}; queue = deque([0])
        while queue:
            u = queue.popleft()
            for v in undirected[u]:
                if v not in seen: seen.add(v); queue.append(v)
        if len(seen) != n:
            continue
        pairs = _reachable_pairs(n, arcs)
        if pairs:
            s, t = rng.choice(pairs)
            return _relabel(n, arcs, s, t, rng), attempt
    raise RuntimeError("failed to generate reachable directed graph")


def _layered(target_n: int, rng: random.Random):
    width = max(2, round(math.sqrt(target_n)))
    layers = max(2, round((target_n - 2) / width))
    sizes = [width] * layers
    while sum(sizes) + 2 > target_n: sizes[-1] -= 1
    while sum(sizes) + 2 < target_n: sizes[rng.randrange(layers)] += 1
    nodes = []; nxt = 1
    for size in sizes: nodes.append(list(range(nxt, nxt + size))); nxt += size
    sink = target_n - 1; arcs = []
    for v in nodes[0]: arcs.append((0, v))
    for left, right in zip(nodes, nodes[1:]):
        probability = 0.65 if target_n <= 14 else 0.45
        for u in left:
            selected = [v for v in right if rng.random() < probability]
            if not selected: selected = [rng.choice(right)]
            arcs.extend((u, v) for v in selected)
        for v in right:
            if not any(b == v for _, b in arcs): arcs.append((rng.choice(left), v))
    arcs.extend((u, sink) for u in nodes[-1])
    rng.shuffle(arcs)
    return arcs


def _mesh(target_n: int, rng: random.Random):
    rows = max(2, round(math.sqrt(target_n))); cols = math.ceil(target_n / rows)
    undirected = set()
    for v in range(target_n):
        r, c = divmod(v, cols)
        for dr, dc in ((0, 1), (1, 0), (1, 1)):
            w = (r + dr) * cols + c + dc
            if r + dr < rows and c + dc < cols and w < target_n:
                undirected.add((min(v, w), max(v, w)))
    arcs = []
    for u, v in sorted(undirected):
        if rng.random() < 0.30: arcs.extend(((u, v), (v, u)))
        elif rng.random() < 0.5: arcs.append((u, v))
        else: arcs.append((v, u))
    pairs = _reachable_pairs(target_n, arcs)
    if not pairs: return _mesh(target_n, rng)
    s, t = rng.choice(pairs)
    return _relabel(target_n, arcs, s, t, rng)


def generate_synthetic(family: str, n: int, regime: str, replication: int):
    seed = derived_seed("synthetic", family, n, regime, replication)
    rng = random.Random(seed); attempts = 1
    if family == "dag_sparse": arcs, attempts = _sample_directed(n, round(1.7 * n), True, rng)
    elif family == "dag_dense": arcs, attempts = _sample_directed(n, round(2.8 * n), True, rng)
    elif family == "cyclic_sparse": arcs, attempts = _sample_directed(n, round(2.0 * n), False, rng)
    elif family == "cyclic_dense": arcs, attempts = _sample_directed(n, round(4.0 * n), False, rng)
    elif family == "layered": arcs = _layered(n, rng)
    elif family == "mesh": arcs = _mesh(n, rng)
    else: raise ValueError(family)
    network = Network.from_tuples(n, _capacitate(arcs, regime, rng))
    metadata = {"collection": "synthetic", "family": family, "size_class": n,
                "capacity_regime": regime, "replication": replication, "seed": seed,
                "attempts": attempts, "n": n, "m": len(network.arcs), "source": 0, "sink": n - 1,
                "max_capacity": max(network.capacities)}
    return network, metadata


def _challenge_mesh(n: int, rng: random.Random):
    rows = max(2, round(math.sqrt(n))); cols = math.ceil(n / rows)
    arcs = set()
    for u in range(n):
        row, col = divmod(u, cols)
        for dr, dc in ((0, 1), (1, 0), (1, 1)):
            v = (row + dr) * cols + col + dc
            if row + dr < rows and col + dc < cols and v < n:
                arcs.add((u, v))
                if u not in (0, n - 1) and v not in (0, n - 1) and rng.random() < 0.30:
                    arcs.add((v, u))
    # The row-major spine guarantees reachability even for incomplete last rows.
    arcs.update((u, u + 1) for u in range(n - 1))
    answer = list(arcs); rng.shuffle(answer); return answer


def _challenge_random(n: int, target_m: int, acyclic: bool, rng: random.Random):
    arcs = {(u, u + 1) for u in range(n - 1)}
    if acyclic:
        possible = [(u, v) for u in range(n) for v in range(u + 1, n)]
    else:
        # Excluding arcs into the source and out of the sink avoids trivial
        # preprocessing artifacts while permitting cycles among interior nodes.
        possible = [(u, v) for u in range(n - 1) for v in range(1, n) if u != v]
    rng.shuffle(possible)
    for arc in possible:
        arcs.add(arc)
        if len(arcs) >= target_m: break
    answer = list(arcs); rng.shuffle(answer); return answer


def generate_challenge(family: str, n: int, capacity_upper: int, replication: int,
                       split: str):
    seed = derived_seed("challenge", split, family, n, capacity_upper, replication,
                        master=CHALLENGE_MASTER_SEED)
    rng = random.Random(seed)
    if family == "layered_path_rich":
        arcs = _layered(n, rng)
    elif family == "mesh_path_rich":
        arcs = _challenge_mesh(n, rng)
    elif family == "dag_dense_path_rich":
        arcs = _challenge_random(n, round(4.0 * n), True, rng)
    elif family == "cyclic_sparse_path_rich":
        arcs = _challenge_random(n, round(2.6 * n), False, rng)
    elif family == "cyclic_dense_path_rich":
        arcs = _challenge_random(n, round(5.0 * n), False, rng)
    else:
        raise ValueError(family)
    capacities = [rng.randint(1, capacity_upper) for _ in arcs]
    network = Network.from_tuples(n, [(u, v, c) for (u, v), c in zip(arcs, capacities)])
    metadata = {
        "collection": f"challenge_{split}", "family": family, "size_class": n,
        "capacity_regime": f"U1-{capacity_upper}", "capacity_upper": capacity_upper,
        "replication": replication, "seed": seed, "n": n, "m": len(arcs),
        "source": 0, "sink": n - 1, "max_capacity": capacity_upper,
        "terminal_rule": "fixed_constructive_path_rich_pair",
    }
    return network, metadata


def _simple_path_count(n: int, edges: list[tuple[int, int]], s: int, t: int, limit: int = 100000):
    adjacency = [[] for _ in range(n)]
    for u, v in edges: adjacency[u].append(v); adjacency[v].append(u)
    count = 0
    def visit(u, seen):
        nonlocal count
        if count >= limit: return
        if u == t: count += 1; return
        for v in adjacency[u]:
            if v not in seen: seen.add(v); visit(v, seen); seen.remove(v)
    visit(s, {s}); return count


def _sndlib_pairs(n: int, edges: list[tuple[int, int]]):
    scored = [( _simple_path_count(n, edges, s, t), s, t)
              for s in range(n) for t in range(s + 1, n)]
    scored.sort()
    return [(scored[0][1], scored[0][2], "few_paths"),
            (scored[len(scored)//2][1], scored[len(scored)//2][2], "median_paths"),
            (scored[-1][1], scored[-1][2], "many_paths")]


def load_sndlib_cases(data_dir: Path):
    for topology in ("abilene", "polska", "nobel-us"):
        raw = json.loads((data_dir / f"{topology}.json").read_text())
        n = len(raw["nodes"]); edges = [(e["source"], e["target"]) for e in raw["edges"]]
        for s, t, pair_class in _sndlib_pairs(n, edges):
            for orientation in ("acyclic", "bidirected"):
                for profile, upper in (("unit", 1), ("small", 2), ("medium", 3), ("moderate", 5)):
                    seed = derived_seed("sndlib", topology, s, t, orientation, profile)
                    rng = random.Random(seed)
                    mapping_middle = [v for v in range(n) if v not in (s, t)]; rng.shuffle(mapping_middle)
                    mapping = {s: 0, t: n-1, **{v:i+1 for i,v in enumerate(mapping_middle)}}
                    if orientation == "bidirected":
                        arcs = [(mapping[u], mapping[v]) for u,v in edges for _ in (0,)] + [(mapping[v], mapping[u]) for u,v in edges]
                    else:
                        adjacency=[[] for _ in range(n)]
                        for u,v in edges: adjacency[u].append(v); adjacency[v].append(u)
                        dist=[10**9]*n; dist[s]=0; q=deque([s])
                        while q:
                            u=q.popleft()
                            for v in adjacency[u]:
                                if dist[v]>dist[u]+1: dist[v]=dist[u]+1; q.append(v)
                        tie={v:rng.random() for v in range(n)}
                        arcs=[]
                        for u,v in edges:
                            a,b=(u,v) if (dist[u],tie[u]) < (dist[v],tie[v]) else (v,u)
                            arcs.append((mapping[a],mapping[b]))
                    rng.shuffle(arcs)
                    capacities=[1 if upper==1 else rng.randint(1,upper) for _ in arcs]
                    network=Network.from_tuples(n, [(u,v,c) for (u,v),c in zip(arcs,capacities)])
                    meta={"collection":"sndlib","topology":topology,"pair_class":pair_class,
                          "original_source":s,"original_sink":t,"orientation":orientation,
                          "capacity_regime":profile,"seed":seed,"n":n,"m":len(arcs),
                          "source":0,"sink":n-1,"max_capacity":upper}
                    yield network,meta


def serialize_network(network: Network, metadata: dict):
    record=dict(metadata); record["arcs"]=[[a.tail,a.head,a.capacity] for a in network.arcs]
    canonical=json.dumps(record,sort_keys=True,separators=(",",":")); record["sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    return record


def deserialize_network(record: dict):
    return Network.from_tuples(record["n"], [tuple(a) for a in record["arcs"]], record["source"], record["sink"])
