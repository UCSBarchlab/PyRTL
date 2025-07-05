import doctest
import random
import unittest

import pyrtl
from pyrtl.rtllib.barrel import Direction, barrel_shifter


class TestDocTests(unittest.TestCase):
    """Test documentation examples."""

    def test_doctests(self):
        failures, tests = doctest.testmod(m=pyrtl.rtllib.barrel)
        self.assertGreater(tests, 0)
        self.assertEqual(failures, 0)


class TestBarrel(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.inp_val = pyrtl.Input(8, "inp_val")
        self.inp_shift = pyrtl.Input(2, "inp_shift")
        self.out_zeros = pyrtl.Output(18, "out_zeros")
        self.out_ones = pyrtl.Output(18, "out_ones")

    def test_shift_left(self):
        random.seed(777906373)
        self.out_zeros <<= barrel_shifter(
            self.inp_val, bit_in=0, direction=Direction.LEFT, shift_dist=self.inp_shift
        )
        self.out_ones <<= barrel_shifter(
            self.inp_val, bit_in=1, direction=Direction.LEFT, shift_dist=self.inp_shift
        )

        sim = pyrtl.Simulation()
        vals = [random.randint(0, 20) for v in range(20)]
        shifts = [random.randint(0, 3) for s in range(20)]
        for i in range(len(vals)):
            sim.step({self.inp_val: vals[i], self.inp_shift: shifts[i]})
            base_sum = vals[i] * pow(2, shifts[i])
            self.assertEqual(sim.inspect(self.out_zeros), base_sum)
            self.assertEqual(
                sim.inspect(self.out_ones), base_sum + pow(2, shifts[i]) - 1
            )

    def test_shift_right(self):
        random.seed(777906374)
        self.out_zeros <<= barrel_shifter(
            self.inp_val, bit_in=0, direction=Direction.RIGHT, shift_dist=self.inp_shift
        )
        self.out_ones <<= barrel_shifter(
            self.inp_val, bit_in=1, direction=Direction.RIGHT, shift_dist=self.inp_shift
        )

        sim = pyrtl.Simulation()
        vals = [random.randint(0, 20) for v in range(20)]
        shifts = [random.randint(0, 3) for s in range(20)]
        for i in range(len(vals)):
            sim.step({self.inp_val: vals[i], self.inp_shift: shifts[i]})
            base_sum = int(vals[i] / pow(2, shifts[i]))
            self.assertEqual(
                sim.inspect(self.out_zeros), base_sum, f"failed on value {vals[i]}"
            )
            extra_sum = sum(
                [pow(2, len(self.inp_val) - b - 1) for b in range(shifts[i])]
            )
            self.assertEqual(
                sim.inspect(self.out_ones),
                base_sum + extra_sum,
                f"failed on value {vals[i]}",
            )


if __name__ == "__main__":
    unittest.main()
