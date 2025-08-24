import doctest
import random
import unittest

import pyrtl
import pyrtl.rtllib.testingutils as utils
from pyrtl.rtllib.positadder import posit_add
from pyrtl.positutils import decimal_to_posit

class TestDocTests(unittest.TestCase):
    """Test documentation examples."""

    def test_doctests(self):
        failures, tests = doctest.testmod(m=pyrtl.rtllib.positadder)
        self.assertGreater(tests, 0)
        self.assertEqual(failures, 0)

class TestPositAdder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        random.seed(42)

    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()
    
    def test_posit_adder(self):
        nbits_list = [8, 16, 32]
        es_list = [0, 1, 2, 3, 4]
        nbits, es = random.choice(nbits_list), random.choice(es_list)
        a = pyrtl.Input(bitwidth=nbits, name="a")
        b = pyrtl.Input(bitwidth=nbits, name="b")
        out = pyrtl.Output(name="out")

        out <<= posit_add(a, b, nbits, es)

        useed = 2 ** (2 ** es)
        maxpos = useed ** (nbits - 2)

        wires = [a, b]
        vals_raw = [[random.randint(0, maxpos) for _ in range(7)] for _ in wires]
        vals = [[decimal_to_posit(j, nbits, es) for j in i] for i in vals_raw]

        out_vals = utils.sim_and_ret_out(out, wires, vals)
        true_result_raw = [x + y for x, y in zip(vals_raw[0], vals_raw[1])]
        true_result = [decimal_to_posit(i, nbits, es) for i in true_result_raw]

        for sim, expected in zip(out_vals, true_result):
            self.assertLessEqual(abs(sim - expected), 1)

if __name__ == "__main__":
    unittest.main()