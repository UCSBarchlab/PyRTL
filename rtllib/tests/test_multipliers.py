import unittest
import pyrtl
import rtllib
from rtllib import multipliers


class TestWallace(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_wallace_tree_1(self):
        a, b = pyrtl.Input(35, "a"), pyrtl.Input(32, "b")
        product = pyrtl.Output(64, "product")
        product <<= multipliers.wallace_tree(a, b)
        # import random
        # x = [int(random.uniform(0, 2**32-1)) for i in range(20)]
        # y = [int(random.uniform(0, 2**32-1)) for i in range(20)]

        xvals = [1, 22, 3, 1781633272, 2526496920, 1317859324, 1260477579, 1445476831, 1661574934,
                 3153223506, 3665960485, 1245627052, 200621347, 2524588247, 2727552806, 1036440456,
                 2342353743, 1552838139, 3714525390, 1032398488]
        yvals = [3, 21, 1581472009, 1890090907, 4277569953, 1962262591, 2628711298, 3803069523,
                 3729934380, 2613886118, 2953151095, 147816102, 4152319597, 1997891783, 1730619637,
                 3982325303, 3295060912, 4014860795, 1922107284, 2458815385]

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(len(xvals)):
            sim.step({a: xvals[cycle], b: yvals[cycle]})

        true_result = [a * b for a, b in zip(xvals, yvals)]
        multiplier_result = sim_trace.trace[product]
        sim_trace.render_trace(symbol_len=12)  # so that enough bits are printed in the render trace
        assert (multiplier_result == true_result)
        print "test passed!"

    def test_wallace_tree_2(self):
        pass
