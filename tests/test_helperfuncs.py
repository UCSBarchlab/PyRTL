import unittest
import random
import pyrtl
import StringIO

from helperfunctions import testmissing

# ---------------------------------------------------------------


class TestBlock(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in xrange(8):
            sim.step({})
        output = StringIO.StringIO()
        sim_trace.print_trace(output)
        print output.getvalue()
        self.assertEqual(output.getvalue(), correct_string)
