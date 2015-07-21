import unittest
import pyrtl
import rtllib
from rtllib import multipliers
import random
import xestcase_utils as utils


class TestWallace(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # this is to ensure reproducibility
        random.seed(777906376)

    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_wallace_tree_1(self):
        """
        Arithmatic tester version 2015.05
        """

        # Creating the logic nets
        a, b = pyrtl.Input(13, "a"), pyrtl.Input(14, "b")
        product = pyrtl.Output(27, "product")
        product <<= multipliers.tree_multiplier(a, b)

        # creating the testing values and the correct results
        xvals = [int(random.uniform(0, 2**13-1)) for i in range(20)]
        yvals = [int(random.uniform(0, 2**14-1)) for i in range(20)]
        true_result = [i * j for i, j in zip(xvals, yvals)]

        # Setting up and running the tests
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(len(xvals)):
            sim.step({a: xvals[cycle], b: yvals[cycle]})

        # Extracting the values and verifying correctness
        multiplier_result = sim_trace.trace[product]
        self.assertEquals(multiplier_result, true_result)

        # now executing the same test using FastSim
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.FastSimulation(tracer=sim_trace)
        for cycle in range(len(xvals)):
            sim.step({a: xvals[cycle], b: yvals[cycle]})

        multiplier_result = sim_trace.trace[product]
        self.assertEquals(multiplier_result, true_result)
        # test passed!

    def test_wallace_tree_2(self):
        pass
