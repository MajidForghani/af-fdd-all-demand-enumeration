from pathlib import Path
import unittest

from af_fdd.study_generators import (deserialize_network, generate_challenge,
                                     generate_synthetic, load_sndlib_cases,
                                     serialize_network)


class StudyGenerationTests(unittest.TestCase):
    def test_synthetic_is_deterministic_and_reachable(self):
        a, ma = generate_synthetic("dag_sparse", 10, "small", 0)
        b, mb = generate_synthetic("dag_sparse", 10, "small", 0)
        self.assertEqual(serialize_network(a, ma), serialize_network(b, mb))
        self.assertEqual(a, deserialize_network(serialize_network(a, ma)))

    def test_sndlib_design_has_72_cases(self):
        data = Path(__file__).resolve().parents[1] / "data" / "sndlib"
        cases = list(load_sndlib_cases(data))
        self.assertEqual(len(cases), 72)
        self.assertEqual({meta["topology"] for _, meta in cases},
                         {"abilene", "polska", "nobel-us"})

    def test_challenge_is_deterministic_reachable_and_split_separated(self):
        a, ma = generate_challenge("dag_dense_path_rich", 22, 3, 0, "pilot")
        b, mb = generate_challenge("dag_dense_path_rich", 22, 3, 0, "pilot")
        _, mc = generate_challenge("dag_dense_path_rich", 22, 3, 100, "heldout")
        self.assertEqual(serialize_network(a, ma), serialize_network(b, mb))
        self.assertNotEqual(ma["seed"], mc["seed"])
        self.assertTrue(any(arc.tail == 0 for arc in a.arcs))
        self.assertTrue(any(arc.head == a.sink for arc in a.arcs))


if __name__ == "__main__":
    unittest.main()
