import unittest
import random
import pyrtl

from helperfunctions import testmissing

class TestBlock(unittest.TestCase):

    def setUp(self):
        self.block = pyrtl.Block()
    
    def tearDown(self):
        pass

    def test_add_wirevector_simple(self):
        w = pyrtl.WireVector(block=self.block, name='testwire')
        self.block.add_wirevector(w)
        self.assertTrue(w in self.block.wirevector_set)
        self.assertTrue('testwire' in self.block.wirevector_by_name)

    def test_add_net(self):
        self.assertRaises(pyrtl.PyrtlError, self.block.add_net, None )
        self.assertRaises(pyrtl.PyrtlError, self.block.add_net, 1 )
        self.assertRaises(pyrtl.PyrtlError, self.block.add_net, "hi" )

    def test_sanity_check(self): 
        testmissing()


class TestWireVector(unittest.TestCase):

    def setUp(self):
        self.block = pyrtl.Block()
    
    def tearDown(self):
        pass

    def test_assignment(self):
        testmissing()
    def test_logic_operatons(self):
        testmissing()
    def test_slice(self):
        testmissing()
    def test_zero_extend(self):
        testmissing()
    def test_sign_extend(self):
        testmissing()

if __name__ == "__main__":
  unittest.main()


