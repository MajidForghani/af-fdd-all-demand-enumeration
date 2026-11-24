import unittest

from af_fdd.baselines import bai2021, support_is_acyclic, yeh2024
from af_fdd.model import Network


BAI_PATHS = [
    (1, 0, 0, 1, 0, 0, 0, 1, 0),
    (1, 0, 0, 1, 0, 0, 1, 0, 1),
    (1, 0, 1, 0, 1, 0, 0, 1, 0),
    (1, 0, 1, 0, 1, 0, 1, 0, 1),
    (1, 0, 1, 0, 0, 1, 0, 0, 1),
    (0, 1, 0, 0, 1, 0, 0, 1, 0),
    (0, 1, 0, 0, 1, 0, 1, 0, 1),
    (0, 1, 0, 0, 0, 1, 0, 0, 1),
]


def bai_network():
    return Network.from_tuples(6, [
        (0, 1, 2), (0, 2, 2), (1, 2, 1), (1, 3, 1), (2, 3, 2),
        (2, 4, 1), (3, 4, 1), (3, 5, 2), (4, 5, 2),
    ])


YEH_PATHS = [
    (1, 0, 0, 0, 1, 0),
    (1, 0, 1, 0, 0, 1),
    (0, 1, 0, 0, 0, 1),
    (0, 1, 0, 1, 1, 0),
]


def yeh_network():
    return Network.from_tuples(4, [
        (0, 1, 3), (0, 2, 2), (1, 2, 1), (2, 1, 1), (1, 3, 1), (2, 3, 2),
    ])


class LiteratureExampleTests(unittest.TestCase):
    def test_bai_2021_worked_example(self):
        result = bai2021(bai_network(), paths=BAI_PATHS)
        self.assertEqual(result.audit["dmax"], 4)
        self.assertEqual(result.audit["rho_one_based"], [[], [3, 6], [], [6], [6, 7], [], [], []])
        self.assertEqual(result.audit["path_lambda_one_based"], [
            [1, 2], [1, 2, 4, 7], [3, 4, 5], [2, 3, 4, 5, 7],
            [3, 4, 5, 8], [], [2, 4, 7], [5, 8],
        ])
        by_d = {}
        for vector in result.vectors:
            by_d.setdefault(sum(vector[i] for i in (0, 1)), []).append(vector)
        self.assertEqual({d: len(v) for d, v in by_d.items()}, {1: 8, 2: 16, 3: 8, 4: 1})
        expected_d3 = {
            (2,1,1,1,2,0,1,2,1), (2,1,1,1,1,1,0,2,1),
            (2,1,1,1,1,1,1,1,2), (1,2,0,1,2,0,1,2,1),
            (1,2,0,1,1,1,0,2,1), (1,2,0,1,1,1,1,1,2),
            (1,2,1,0,2,1,0,2,1), (1,2,1,0,2,1,1,1,2),
        }
        self.assertEqual(set(by_d[3]), expected_d3)
        self.assertEqual(set(by_d[4]), {(2,2,1,1,2,1,1,2,2)})
        self.assertEqual(result.counters["unexpected_duplicates"], 0)

    def test_yeh_2024_worked_example(self):
        result = yeh2024(yeh_network(), paths=YEH_PATHS)
        self.assertEqual(result.audit["bounds"], [1, 1, 2, 1])
        self.assertEqual(result.audit["dmax"], 3)
        self.assertEqual(result.counters["ibat_states"], 14)
        self.assertEqual(result.counters["sequentially_feasible"], 9)
        self.assertEqual(result.counters["cycle_pruned"], 2)
        expected_order = [
            (1,1,0,0),(1,0,1,0),(0,1,1,0),(1,1,1,0),(0,0,2,0),(1,0,2,0),
            (0,1,2,0),(1,0,0,1),(0,1,0,1),(1,1,0,1),(0,0,1,1),(1,0,1,1),
            (0,1,1,1),(0,0,2,1),
        ]
        # Reconstruct the candidates via the private trace's feasible subset and
        # the paper counts; exact complete order is independently checked below.
        from af_fdd.baselines import _bounded_sum_states
        self.assertEqual(_bounded_sum_states([1,1,2,1], 2, 3), expected_order)
        expected_final = {
            (2,0,1,0,1,1), (1,1,0,0,1,1), (1,1,1,0,0,2),
            (2,1,1,0,1,2), (0,2,0,0,0,2), (1,2,0,0,1,2),
            (0,2,0,1,1,1),
        }
        self.assertEqual(result.vectors - set(YEH_PATHS), expected_final)
        self.assertTrue(all(not support_is_acyclic(yeh_network(), row["arc_state"])
                            for row in result.audit["trace"] if row["cycle"]))

    def test_iterative_ibat_is_statewise_equivalent_to_recursive_reference(self):
        from af_fdd.baselines import _bounded_sum_states

        def recursive_reference(bounds, lower, upper):
            states = []
            def generate(i, remaining, values):
                if i < 0:
                    if remaining == 0:
                        states.append(tuple(values))
                    return
                for value in range(min(bounds[i], remaining) + 1):
                    values[i] = value
                    generate(i - 1, remaining - value, values)
            for total in range(lower, upper + 1):
                generate(len(bounds) - 1, total, [0] * len(bounds))
            radices = []
            multiplier = 1
            for bound in bounds:
                radices.append(multiplier)
                multiplier *= bound + 1
            states.sort(key=lambda state: sum(v * r for v, r in zip(state, radices)))
            return states

        for bounds in ([1, 1, 2, 1], [2, 0, 3], [1, 2, 1, 2, 1], [3]):
            upper = min(5, sum(bounds))
            self.assertEqual(_bounded_sum_states(list(bounds), 0, upper),
                             recursive_reference(list(bounds), 0, upper))

    def test_iterative_ibat_handles_more_than_recursion_limit_paths(self):
        from af_fdd.baselines import _bounded_sum_states
        bounds = [1, 1] + [0] * 1_198
        states = _bounded_sum_states(bounds, 2, 2)
        self.assertEqual(len(states), 1)
        self.assertEqual(states[0][:2], (1, 1))
        self.assertTrue(all(value == 0 for value in states[0][2:]))


if __name__ == "__main__":
    unittest.main()
