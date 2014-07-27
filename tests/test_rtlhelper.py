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
        for bitwidth in range(9,10):
            r = pyrtl.Register(bitwidth=bitwidth, name='r')
            const_one = pyrtl.Const(1)
            addby = const_one.zero_extended(bitwidth)
            r.next, cout = generate_full_adder(r, addby )
 
            self.assertTrue( isinstance(r,pyrtl.Register) )
            self.assertTrue( isinstance(cout,pyrtl.WireVector) )
            pyrtl.reset_working_block()

if __name__ == "__main__":
  unittest.main()

class TestRTLMemBlockDesign(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()
    
    def tearDown(self):
        pyrtl.reset_working_block()

    def test_simple_memblock(self):
        bitwidth = 3

        output1 = pyrtl.Output(bitwidth,"output1")
        output2 = pyrtl.Output(bitwidth,"output2")

        mem_read_address1 = pyrtl.Input(bitwidth,name='mem_read_address1')
        mem_read_address2 = pyrtl.Input(bitwidth,name='mem_read_address2')
        mem_write_address = pyrtl.Input(bitwidth,name='mem_write_address')
        mem_write_data = pyrtl.Input(bitwidth,name='mem_write_data')

        memory = pyrtl.MemBlock(bitwidth=bitwidth, addrwidth=bitwidth, name='adder_mem')

        output1 <<= memory[mem_read_address1]
        output2 <<= memory[mem_read_address2]
        memory[mem_write_address] = mem_write_data
