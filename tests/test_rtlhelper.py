import unittest
import random
import pyrtl

from helperfunctions import *

class TestRTLAdderDesign(unittest.TestCase):

    @staticmethod
    def one_bit_add(a,b,cin):
        """ Generates a one-bit full adder, returning type of signals """
        assert len(a) == len(b) == len(cin) == 1
        sum = a ^ b ^ cin
        cout = a & b | a & cin | b & cin
        return sum,cout

    @staticmethod
    def add( a, b, cin=pyrtl.Const(0,bitwidth=1) ):
        """ Generates a arbitrary bitwidth ripple-carry adder """
        assert len(a) == len(b)

        if len(a)==1:
            sumbits, cout = TestRTLAdderDesign.one_bit_add(a,b,cin)
        else:
            lsbit, ripplecarry = TestRTLAdderDesign.one_bit_add( a[0], b[0], cin )
            msbits, cout = TestRTLAdderDesign.add( a[1:], b[1:], ripplecarry )
            sumbits = pyrtl.concat(msbits,lsbit)
        return sumbits, cout


    def setUp(self):
        pass
    
    def tearDown(self):
        pass
        
    def test_complete_adders(self):
        import pyrtl.rtlhelper 
        for bitwidth in range(1,10):
            pyrtl.reset_working_block()
            r = pyrtl.Register(bitwidth=bitwidth, name='r')
            r.next, cout = TestRTLAdderDesign.add(r, pyrtl.Const(1).zero_extended(bitwidth) )
 
            self.assertTrue( isinstance(r,pyrtl.Register) )
            self.assertTrue( isinstance(cout,pyrtl.WireVector) )
            
            # NEED TO CLEAR BLOCK

        #self.assertRaises(TypeError, random.shuffle, (1,2,3))
        pass

if __name__ == "__main__":
  unittest.main()
