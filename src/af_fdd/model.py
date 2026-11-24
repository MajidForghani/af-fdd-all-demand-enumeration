from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class Arc:
    tail: int
    head: int
    capacity: int
    name: str = ""

    def __post_init__(self) -> None:
        if self.tail == self.head:
            raise ValueError("Self-loops are excluded; they can never be positive in a d-MP.")
        if self.capacity < 0:
            raise ValueError("Arc capacities must be nonnegative integers.")


@dataclass(frozen=True, slots=True)
class Network:
    n: int
    arcs: tuple[Arc, ...]
    source: int = 0
    sink: int | None = None

    def __post_init__(self) -> None:
        sink = self.n - 1 if self.sink is None else self.sink
        object.__setattr__(self, "sink", sink)
        if self.n < 2:
            raise ValueError("A two-terminal network needs at least two vertices.")
        if not (0 <= self.source < self.n and 0 <= sink < self.n):
            raise ValueError("Source and sink must be valid vertices.")
        if self.source == sink:
            raise ValueError("Source and sink must be distinct.")
        for arc in self.arcs:
            if not (0 <= arc.tail < self.n and 0 <= arc.head < self.n):
                raise ValueError(f"Invalid endpoint in arc {arc!r}.")

    @classmethod
    def from_tuples(
        cls,
        n: int,
        arcs: Iterable[tuple[int, int, int]],
        source: int = 0,
        sink: int | None = None,
    ) -> "Network":
        return cls(n, tuple(Arc(u, v, int(c), f"a{i}") for i, (u, v, c) in enumerate(arcs)), source, sink)

    @property
    def capacities(self) -> tuple[int, ...]:
        return tuple(a.capacity for a in self.arcs)

    def reordered(self, order: Sequence[int]) -> "Network":
        if sorted(order) != list(range(len(self.arcs))):
            raise ValueError("order must be a permutation of all arc indices")
        return Network(self.n, tuple(self.arcs[i] for i in order), self.source, self.sink)

