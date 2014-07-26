import unittest
import random
import pyrtl

from helperfunctions import *

class TestRTLAdderDesign(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()
    
    def tearDown(self):
        pyrtl.reset_working_block()
        
    def test_complete_adders(self):
        for bitwidth in range(1,10):
            r = pyrtl.Register(bitwidth=bitwidth, name='r')
            r.next, cout = generate_full_adder(r, pyrtl.Const(1).zero_extended(bitwidth) )
 
            self.assertTrue( isinstance(r,pyrtl.Register) )
            self.assertTrue( isinstance(cout,pyrtl.WireVector) )
            pyrtl.reset_working_block()

if __name__ == "__main__":
  unittest.main()

class TestRTLMemBlockDesign(unittest.TestCase):

    """
    TODO: get mem test integrated into new class
    def memUnit(address,readWire,writeSelect,bitwidth):
        "generates a functioning memory unit"
        #write select wire is high when you want to write an low when reading
    
    inDataIncrement = rtl.Input(3,"InDataIncrement")
    addressIncrement = rtl.Input(3,"addressIncrement")
    outAddressIncrement = rtl.Input(3,"outAddressIncrement")

    output = rtl.Output(3,"Output")


    bitwidth = 3
    memInData = rtl.Register(bitwidth=bitwidth,name='memInData')
    memInData.next, cout = add(memInData, inDataIncrement )

    memAddress =rtl.Register(bitwidth=bitwidth,name='memAddress')
    memAddress.next, cout = add(memAddress, addressIncrement )

    memOutAddress =rtl.Register(bitwidth=bitwidth,name='memOutAddress')
    memOutAddress.next, cout = add(memOutAddress, outAddressIncrement )
   
    adderMem = rtl.MemBlock(bitwidth = bitwidth,addrwidth = bitwidth,name ='adderMem')
    output <<= adderMem[memOutAddress]
    adderMem[memAddress] = memInData
    """

    pass

