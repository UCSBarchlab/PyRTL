import unittest

import pyrtl
from pyrtl.rtllib.pyrtlfloat import Float16Operations, FloatOperations, RoundingMode


class TestMultiplication(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        a = pyrtl.Input(bitwidth=16, name="a")
        b = pyrtl.Input(bitwidth=16, name="b")
        FloatOperations.default_rounding_mode = RoundingMode.RNE
        result_rne = pyrtl.Output(name="result_rne")
        result_rne <<= Float16Operations.mul(a, b)
        FloatOperations.default_rounding_mode = RoundingMode.RTZ
        result_rtz = pyrtl.Output(name="result_rtz")
        result_rtz <<= Float16Operations.mul(a, b)
        self.sim = pyrtl.Simulation()

    def test_multiplication_simple(self):
        self.sim.step({"a": 0b0011111000000000, "b": 0b0011110000000001})
        self.assertEqual(self.sim.inspect("result_rne"), 0b0011111000000010)
        self.assertEqual(self.sim.inspect("result_rtz"), 0b0011111000000001)


if __name__ == "__main__":
    unittest.main()
