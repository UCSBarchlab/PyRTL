import doctest
import random
import unittest
import pyrtl
import pyrtl.rtllib.testingutils as utils
from pyrtl.rtllib.positsub import posit_sub
from pyrtl.positutils import decimal_to_posit


class TestDocTests(unittest.TestCase):
    """Test documentation examples."""

    def test_doctests(self):
        failures, tests = doctest.testmod(m=pyrtl.rtllib.positsub)
        self.assertGreater(tests, 0)
        self.assertEqual(failures, 0)


class TestPositSubtractor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = 42
        random.seed(cls.seed)

    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_posit_subtractor(self):
        nbits_list = [8, 16, 32]
        es_list = [0, 1, 2, 3, 4]
        nbits, es = random.choice(nbits_list), random.choice(es_list)

        a = pyrtl.Input(bitwidth=nbits, name="a")
        b = pyrtl.Input(bitwidth=nbits, name="b")
        out = pyrtl.Output(name="out")
        out <<= posit_sub(a, b, nbits, es)

        useed = 2 ** (2 ** es)
        maxpos = useed ** (nbits - 2)

        wires = [a, b]
        core = [[random.randint(0, maxpos) for _ in range(5)] for _ in wires]

        core[0][:2] = [0, 1]
        core[1][:2] = [0, 1]
        core[0].append(123)
        core[1].append(123)
        core[0].append(124)
        core[1].append(123)

        vals_raw = core
        vals = [[decimal_to_posit(j, nbits, es) for j in row] for row in vals_raw]

        out_vals = utils.sim_and_ret_out(out, wires, vals)

        true_result_raw = [x - y for x, y in zip(vals_raw[0], vals_raw[1])]
        true_result = [decimal_to_posit(i, nbits, es) for i in true_result_raw]

        for idx, (sim, expected) in enumerate(zip(out_vals, true_result)):
            delta = abs(sim - expected)
            self.assertLessEqual(
                delta, 1,
                f"Mismatch at index {idx}: sim={sim}, expected={expected}, |sim-exp|={delta}"
            )


if __name__ == "__main__":
    unittest.main()
