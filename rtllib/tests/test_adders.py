import unittest
import pyrtl
import rtllib
from rtllib import adders
import random


class TestAdders(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        random.seed(8492049)

    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def adder2_t_base_1(self, adder_func):
        # a generic test for add
        a, b = pyrtl.Input(35, "a"), pyrtl.Input(32, "b")
        sum = pyrtl.Output(36, "sum")
        sum <<= adder_func(a, b)

        xvals = [int(2**random.uniform(1, 32) - 2) for i in range(40)]
        yvals = [int(2**random.uniform(1, 32) - 2) for i in range(40)]

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(len(xvals)):
            sim.step({a: xvals[cycle], b: yvals[cycle]})

        true_result = [c + d for c, d in zip(xvals, yvals)]
        adder_result = sim_trace.trace[sum]
        sim_trace.render_trace(symbol_len=12)
        assert (adder_result == true_result)
        print "test passed!"

    def test_kogge_stone_1(self):
        self.adder2_t_base_1(adders.kogge_stone)

    def test_ripple_1(self):
        self.adder2_t_base_1(adders.ripple_add)
