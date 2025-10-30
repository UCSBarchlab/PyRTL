import unittest

import pyrtl
from pyrtl.rtllib.pyrtlfloat import Float16WireVector, FloatOperations, RoundingMode


class TestMultiplication(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        a = pyrtl.Input(bitwidth=16, name="a")
        b = pyrtl.Input(bitwidth=16, name="b")
        a_floatwv = Float16WireVector()
        a_floatwv <<= a
        b_floatwv = Float16WireVector()
        b_floatwv <<= b
        FloatOperations.default_rounding_mode = RoundingMode.RNE
        result_add = pyrtl.Output(name="result_add")
        result_add <<= a_floatwv + b_floatwv
        result_sub = pyrtl.Output(name="result_sub")
        result_sub <<= a_floatwv - b_floatwv
        self.sim = pyrtl.Simulation()

    def test_multiplication_simple(self):
        self.sim.step({"a": 0b0100001000000000, "b": 0b0100010100000000})
        self.assertEqual(self.sim.inspect("result_add"), 0b0100100000000000)
        self.assertEqual(self.sim.inspect("result_sub"), 0b1100000000000000)


if __name__ == "__main__":
    unittest.main()
