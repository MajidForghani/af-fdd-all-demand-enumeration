"""Frozen pre-optimization AF-FDD engine used only for ablation studies."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from time import perf_counter

from .model import Network
from .ordering import greedy_frontier_order, natural_order

LegacyState = tuple[tuple[int, ...], tuple[int, ...]]


@dataclass(slots=True)
class LegacyStats:
    build_seconds: float = 0.0
    nodes: int = 0
    transitions: int = 0
    max_width: int = 0
    outputs: int = 0


class LegacyAFFDD:
    """Original matrix-closure, tuple-state implementation (September 2026)."""

    def __init__(self, network: Network, ordering: str | tuple[int, ...] = "greedy") -> None:
        self.network = network
        if ordering == "greedy":
            self.order = greedy_frontier_order(network)
        elif ordering == "natural":
            self.order = natural_order(network)
        elif isinstance(ordering, tuple):
            self.order = ordering
        else:
            raise ValueError(ordering)
        self.arcs = tuple(network.arcs[i] for i in self.order)
        self.frontiers = self._frontiers()
        self.bounds = self._bounds()
        self.layers: list[list[LegacyState]] = []
        self.ids: list[dict[LegacyState, int]] = []
        self.edges: dict[int, list[tuple[int, int]]] = {}
        self.accepting: dict[int, int] = {}
        self.stats = LegacyStats()

    def _frontiers(self):
        m = len(self.arcs); first = [m + 1] * self.network.n; last = [-1] * self.network.n
        for i, arc in enumerate(self.arcs):
            for v in (arc.tail, arc.head): first[v] = min(first[v], i); last[v] = max(last[v], i)
        terminals = {self.network.source, int(self.network.sink)}
        return [tuple(sorted(terminals | {v for v in range(self.network.n) if first[v] < k <= last[v]}))
                for k in range(m + 1)]

    def _bounds(self):
        out = [0] * self.network.n; inc = [0] * self.network.n; answer = []
        for arc in self.arcs: out[arc.tail] += arc.capacity; inc[arc.head] += arc.capacity
        for k in range(len(self.arcs) + 1):
            answer.append({v: (-inc[v], out[v]) for v in range(self.network.n)})
            if k < len(self.arcs):
                arc = self.arcs[k]; out[arc.tail] -= arc.capacity; inc[arc.head] -= arc.capacity
        return answer

    @staticmethod
    def _decode(rows, n): return [[bool(rows[i] & (1 << j)) for j in range(n)] for i in range(n)]

    @staticmethod
    def _encode(matrix):
        return tuple(sum(1 << j for j, value in enumerate(row) if value) for row in matrix)

    def _transition(self, layer, state, value):
        current, nxt, arc = self.frontiers[layer], self.frontiers[layer + 1], self.arcs[layer]
        balances, rows = state; work = tuple(sorted(set(current) | {arc.tail, arc.head}))
        old_pos = {v:i for i,v in enumerate(current)}; pos = {v:i for i,v in enumerate(work)}
        bal = [0] * len(work)
        for v,i in old_pos.items(): bal[pos[v]] = balances[i]
        old = self._decode(rows, len(current)); reach = [[False]*len(work) for _ in work]
        for u,oi in old_pos.items():
            for v,oj in old_pos.items(): reach[pos[u]][pos[v]] = old[oi][oj]
        if value:
            u,v = pos[arc.tail],pos[arc.head]
            if reach[v][u]: return None
            reach[u][v] = True
            for k in range(len(work)):
                for i in range(len(work)):
                    if reach[i][k]:
                        for j in range(len(work)): reach[i][j] = reach[i][j] or reach[k][j]
            bal[u] += value; bal[v] -= value
        next_set = set(nxt); terminals = {self.network.source, int(self.network.sink)}
        for v,i in pos.items():
            if v not in next_set and v not in terminals and bal[i] != 0: return None
        next_bal = tuple(bal[pos[v]] for v in nxt)
        for v,b in zip(nxt,next_bal):
            if v not in terminals:
                low,high=self.bounds[layer+1][v]
                if not (b+low <= 0 <= b+high): return None
        indices=[pos[v] for v in nxt]
        matrix=[[reach[i][j] for j in indices] for i in indices]
        return next_bal,self._encode(matrix)

    def build(self):
        start=perf_counter(); root=(tuple(0 for _ in self.frontiers[0]),tuple(0 for _ in self.frontiers[0]))
        self.layers=[[root]]; self.ids=[{root:0}]; next_id=1
        for layer,arc in enumerate(self.arcs):
            states=[]; ids={}
            for state in self.layers[layer]:
                parent=self.ids[layer][state]; outgoing=[]
                for value in range(arc.capacity+1):
                    child_state=self._transition(layer,state,value)
                    if child_state is None: continue
                    child=ids.get(child_state)
                    if child is None: child=next_id; next_id+=1; ids[child_state]=child; states.append(child_state)
                    outgoing.append((value,child)); self.stats.transitions+=1
                self.edges[parent]=outgoing
            self.layers.append(states); self.ids.append(ids); self.stats.max_width=max(self.stats.max_width,len(states))
        final=self.frontiers[-1]; si=final.index(self.network.source); ti=final.index(int(self.network.sink))
        for state in self.layers[-1]:
            d=state[0][si]
            if d>0 and state[0][ti]==-d: self.accepting[self.ids[-1][state]]=d
        self.stats.nodes=next_id; self.stats.build_seconds=perf_counter()-start
        self.stats.outputs=sum(self.count_by_d().values()); return self

    def count_by_d(self):
        counts={0:1}
        for layer in range(len(self.arcs)):
            nxt={}
            for state in self.layers[layer]:
                parent=self.ids[layer][state]
                for _,child in self.edges.get(parent,()): nxt[child]=nxt.get(child,0)+counts.get(parent,0)
            counts=nxt
        answer={}
        for node,d in self.accepting.items(): answer[d]=answer.get(d,0)+counts.get(node,0)
        return answer
