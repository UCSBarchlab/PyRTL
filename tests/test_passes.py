import unittest
import random
import pyrtl

from helperfunctions import testmissing

class TestPasses(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()    

    def tearDown(self):
        pyrtl.reset_working_block()    

    def test_optimiziation_wire_on_inpu(self):
        inwire = pyrtl.Input(bitwidth=3)
        tempwire = pyrtl.WireVector()
        outwire = pyrtl.Output()
        tempwire <<= inwire
        outwire <<= tempwire
        pyrtl.optimize()
        # should remove the middle wire but keep the input
        result = str(pyrtl.working_block())
        self.assertTrue(result.startswith("tmp3/3O <-- w -- tmp1/3I"))

    def test_optimiziation_wire_on_inpu(self):
        inwire = pyrtl.Input(bitwidth=3)
        tempwire = pyrtl.WireVector()
        tempwire2 = pyrtl.WireVector()
        outwire = pyrtl.Output()
        tempwire <<= inwire
        tempwire2 <<= tempwire
        outwire <<= tempwire
        pyrtl.optimize()
        # should remove the middle wires but keep the input
        result = str(pyrtl.working_block())
        self.assertTrue(result.startswith("tmp4/3O <-- w -- tmp1/3I"))

    def test_sanity_check(self): 
        testmissing()


if __name__ == "__main__":
  unittest.main()
