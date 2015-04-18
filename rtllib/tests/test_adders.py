import unittest
import pyrtl
from pyrtl import *
import rtllib
from rtllib import adders


class TestKogge(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_kogge_stone_1(self):
        a, b = Input(35, "a"), Input(32, "b")
        sum = Output(36, "sum")
        sum <<= adders.kogge_stone(a, b)

        # import random
        # x = [int(random.uniform(0, 2**32-1)) for i in range(20)]
        # y = [int(random.uniform(0, 2**32-1)) for i in range(20)]

        xvals = [1, 7, 586, 2267275008L, 1960203963, 1438786826, 3920164814L, 2497854937L,
                 950945689, 3375205901L, 2934141195L, 3224744287L, 1456551815, 3177554781L,
                 2251451835L, 2665797053L, 2259947879L, 72946011, 2662761821L, 2663591183L]
        yvals = [3, 11, 2849,  3196081010L, 2278925643L, 616604441, 2452658437L, 1635565464,
                 1177093299, 872396978, 3052657213L, 3076295239L, 2784261621L, 1351851103,
                 2736090721L, 1560635723, 2032723202, 1942488293, 2137620320, 3248404693L]

        sim_trace = SimulationTrace()
        sim = Simulation(tracer=sim_trace)
        for cycle in range(len(xvals)):
            sim.step({a: xvals[cycle], b: yvals[cycle]})

        true_result = [a + b for a, b in zip(xvals, yvals)]
        adder_result = sim_trace.trace[sum]
        sim_trace.render_trace(symbol_len=12)
        assert (adder_result == true_result)
        print "test passed!"

    def test_kogge_stone_2(self):
        pass
