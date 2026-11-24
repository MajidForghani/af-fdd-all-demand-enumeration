import random
import unittest

from af_fdd import AFFDD, AFOptions, Network, enumerate_dmp_oracle
from af_fdd.generators import random_network


class AFFDDTests(unittest.TestCase):
    def assert_agrees(self, network: Network) -> None:
        self.assertEqual(enumerate_dmp_oracle(network), AFFDD(network).build().solution_sets())

    def test_single_arc(self) -> None:
        self.assert_agrees(Network.from_tuples(2, [(0, 1, 3)]))

    def test_parallel_routes_and_cycle(self) -> None:
        self.assert_agrees(Network.from_tuples(4, [
            (0, 1, 2), (1, 3, 2), (0, 2, 2), (2, 3, 2), (1, 2, 1), (2, 1, 1)
        ]))

    def test_random_small(self) -> None:
        rng = random.Random(4217)
        for i in range(50):
            n = rng.randint(3, 5)
            self.assert_agrees(random_network(rng, n, rng.randint(n - 1, n + 2), 2, i % 2 == 0))

    def test_optimized_modes_and_safe_bounds(self) -> None:
        rng = random.Random(7741)
        for i in range(30):
            n = rng.randint(3, 5)
            network = random_network(rng, n, rng.randint(n - 1, n + 2), 2, i % 2 == 0)
            expected = enumerate_dmp_oracle(network)
            expected_counts = {d: len(vectors) for d, vectors in expected.items()}
            for cut, residual in ((False, False), (True, False), (True, True)):
                explicit = AFFDD(network, "auto", AFOptions(cut_bounds=cut, residual_test=residual)).build()
                counted = AFFDD(network, "auto", AFOptions(
                    mode="count", cut_bounds=cut, residual_test=residual)).build()
                self.assertEqual(explicit.solution_sets(), expected)
                self.assertEqual(counted.count_by_d(), expected_counts)

    def test_streamed_output(self) -> None:
        network = Network.from_tuples(4, [(0, 1, 2), (1, 3, 2), (0, 2, 1), (2, 3, 1)])
        diagram = AFFDD(network).build()
        streamed = []
        count = diagram.stream_solutions(lambda d, vector: streamed.append((d, vector)))
        self.assertEqual(count, diagram.stats.outputs)
        self.assertEqual(set(streamed), {(d, vector) for d, vectors in diagram.solution_sets().items()
                                         for vector in vectors})

    def test_terminal_incident_arcs_are_exactly_forced_to_zero(self) -> None:
        network = Network.from_tuples(5, [
            (0, 1, 2), (1, 4, 2), (0, 2, 1), (2, 4, 1),
            (1, 0, 2), (4, 2, 2), (2, 1, 1), (1, 2, 1),
        ])
        expected = enumerate_dmp_oracle(network)
        diagram = AFFDD(network).build()
        self.assertEqual(diagram.solution_sets(), expected)
        self.assertEqual(diagram.effective_capacities[4:6], (0, 0))
        self.assertTrue(all(vector[4] == vector[5] == 0
                            for vectors in expected.values() for vector in vectors))

    def test_productive_filter_preserves_outputs(self) -> None:
        network = Network.from_tuples(5, [
            (0, 1, 2), (1, 4, 2), (0, 2, 2), (2, 4, 2),
            (1, 2, 2), (2, 1, 2), (3, 1, 2),
        ])
        filtered = AFFDD(network, options=AFOptions(productive_output=True)).build()
        unfiltered = AFFDD(network, options=AFOptions(productive_output=False)).build()
        self.assertEqual(list(filtered.iter_solutions()), list(unfiltered.iter_solutions()))
        self.assertGreaterEqual(filtered.stats.unproductive_nodes, 0)


if __name__ == "__main__":
    unittest.main()

