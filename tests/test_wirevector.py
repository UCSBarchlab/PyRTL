import unittest
import random
import pyrtl

from helperfunctions import *

class TestWireVector(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()    
    
    def tearDown(self):
        pyrtl.reset_working_block()    

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

class TestConst(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

    def test_const_integers(self):
        c = pyrtl.Const(1)
        self.assertTrue( c.val == 1 )
        self.assertTrue( c.bitwidth == 1 )

        c = pyrtl.Const(5)
        self.assertTrue( c.val == 5 )
        self.assertTrue( c.bitwidth == 3 )

        c = pyrtl.Const(1,bitwidth=5)
        self.assertTrue( c.val == 1 )
        self.assertTrue( c.bitwidth == 5 )

    def test_const_string(self):
        c = pyrtl.Const("1'1")
        self.assertTrue( c.val == 1 )
        self.assertTrue( c.bitwidth == 1 )

        c = pyrtl.Const("5'3")
        self.assertTrue( c.val == 3 )
        self.assertTrue( c.bitwidth == 5 )

        c = pyrtl.Const("5'b11")
        self.assertTrue( c.val == 3 )
        self.assertTrue( c.bitwidth == 5 )

        c = pyrtl.Const("16'xff")
        self.assertTrue( c.val == 0xff )
        self.assertTrue( c.bitwidth == 16 )

        c = pyrtl.Const("17'xff")
        self.assertTrue( c.val == 0xff )
        self.assertTrue( c.bitwidth == 17 )

        c = pyrtl.Const("5'b011")
        self.assertTrue( c.val == 3 )
        self.assertTrue( c.bitwidth == 5 )

    def test_const_badstring(self):
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1" )
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "-1" )
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1bx" )
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1ba" )
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1'bx" )
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1'ba" )
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1'b10" )
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "1'-b10" )
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "-1'b10" )
        self.assertRaises(pyrtl.PyrtlError, pyrtl.Const, "5'b111111'" )


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


class TestRTLMemBlockDesign(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.addrwidth = 5
        self.output1 = pyrtl.Output(self.bitwidth,"output1")
        self.output2 = pyrtl.Output(self.bitwidth,"output2")
        self.mem_read_address1 = pyrtl.Input(self.addrwidth,name='mem_read_address1')
        self.mem_read_address2 = pyrtl.Input(self.addrwidth,name='mem_read_address2')
        self.mem_write_address = pyrtl.Input(self.addrwidth,name='mem_write_address')
        self.mem_write_data = pyrtl.Input(self.bitwidth,name='mem_write_data')
    
    def tearDown(self):
        pyrtl.reset_working_block()

    def test_memblock_simple(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth, name='memory')
        self.output1 <<= memory[self.mem_read_address1]
        self.output2 <<= memory[self.mem_read_address2]
        memory[self.mem_write_address] = self.mem_write_data

    def test_memblock_with_write_enable_with_equalsign(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth, name='memory')
        we = pyrtl.Const(1,bitwidth=1)
        self.output1 <<= memory[self.mem_read_address1]
        self.output2 <<= memory[self.mem_read_address2]
        memory[self.mem_write_address] = pyrtl.DataWithEnable(self.mem_write_data, enable=we)

    def test_memblock_with_write_enable_with_shiftset(self):
        testmissing()

if __name__ == "__main__":
  unittest.main()


