import unittest
import random

import pyrtl
from pyrtl.rtllib import barrel


class TestBarrel(unittest.TestCase):
    # @classmethod
    # def setUpClass(cls):
    #     # this is to ensure reproducibility
    #     random.seed(777906374)

    def setUp(self):
        pyrtl.reset_working_block()
        self.inp_val = pyrtl.Input(8, 'inp_val')
        self.inp_shift = pyrtl.Input(2, 'inp_shift')
        self.out_zeros = pyrtl.Output(18, 'out_zeros')
        self.out_ones = pyrtl.Output(18, 'out_ones')

    def test_shift_left(self):
        random.seed(777906373)
        zero = pyrtl.Const(0, 1)
        one = pyrtl.Const(1, 1)
        self.out_zeros <<= barrel.barrel_shifter(self.inp_val, zero, one, self.inp_shift)
        self.out_ones <<= barrel.barrel_shifter(self.inp_val, one, one, self.inp_shift)
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        vals = [random.randint(0, 20) for v in range(20)]
        shifts = [random.randint(0, 3) for s in range(20)]
        for i in range(len(vals)):
            sim.step({
                self.inp_val: vals[i],
                self.inp_shift: shifts[i]
            })
            base_sum = vals[i] * pow(2, shifts[i])
            self.assertEqual(sim.inspect(self.out_zeros), base_sum)
            self.assertEqual(sim.inspect(self.out_ones), base_sum + pow(2, shifts[i]) - 1)

    def test_shift_right(self):
        random.seed(777906374)
        zero = pyrtl.Const(0, 1)
        one = pyrtl.Const(1, 1)
        self.out_zeros <<= barrel.barrel_shifter(self.inp_val, zero, zero, self.inp_shift)
        self.out_ones <<= barrel.barrel_shifter(self.inp_val, one, zero, self.inp_shift)
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        vals = [random.randint(0, 20) for v in range(20)]
        shifts = [random.randint(0, 3) for s in range(20)]
        for i in range(len(vals)):
            sim.step({
                self.inp_val: vals[i],
                self.inp_shift: shifts[i]
            })
            base_sum = int(vals[i] / pow(2, shifts[i]))
            self.assertEqual(sim.inspect(self.out_zeros), base_sum, "failed on value %d" % vals[i])
            extra_sum = sum([pow(2, len(self.inp_val) - b - 1) for b in range(shifts[i])])
            self.assertEqual(sim.inspect(self.out_ones), base_sum + extra_sum,
                             "failed on value %d" % vals[i])
