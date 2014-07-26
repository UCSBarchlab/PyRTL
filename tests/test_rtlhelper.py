import unittest
import random
import pyrtl

from helperfunctions import *

class TestRTLAdderDesign(unittest.TestCase):

    def setUp(self):
        pass
    
    def tearDown(self):
        pass
        
    def test_complete_adders(self):
        import pyrtl.rtlhelper 
        for bitwidth in range(1,10):
            pyrtl.reset_working_block()
            r = pyrtl.Register(bitwidth=bitwidth, name='r')
            r.next, cout = generate_full_adder(r, pyrtl.Const(1).zero_extended(bitwidth) )
 
            self.assertTrue( isinstance(r,pyrtl.Register) )
            self.assertTrue( isinstance(cout,pyrtl.WireVector) )

if __name__ == "__main__":
  unittest.main()
