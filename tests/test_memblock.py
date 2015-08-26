import unittest
import random
import pyrtl

from helperfunctions import *


# -------------------------------------------------------------------
class TestRTLMemBlockDesign(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.addrwidth = 5
        self.output1 = pyrtl.Output(self.bitwidth, "output1")
        self.output2 = pyrtl.Output(self.bitwidth, "output2")
        self.mem_read_address1 = pyrtl.Input(self.addrwidth, name='mem_read_address1')
        self.mem_read_address2 = pyrtl.Input(self.addrwidth, name='mem_read_address2')
        self.mem_write_address = pyrtl.Input(self.addrwidth, name='mem_write_address')
        self.mem_write_data = pyrtl.Input(self.bitwidth, name='mem_write_data')

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_memblock_simple(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth, name='memory')
        self.output1 <<= memory[self.mem_read_address1]
        self.output2 <<= memory[self.mem_read_address2]
        memory[self.mem_write_address] <<= self.mem_write_data

    def test_memblock_assign_with_extention(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth, name='memory')
        big_output = pyrtl.Output(self.bitwidth+1, "big_output")
        big_output <<= memory[self.mem_read_address1]
        self.output1 <<= 1
        self.output2 <<= 2
        memory[self.mem_write_address] <<= self.mem_write_data
        pyrtl.working_block().sanity_check()

    def test_memblock_with_write_enable_with_equalsign(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth, name='memory')
        we = pyrtl.Const(1, bitwidth=1)
        self.output1 <<= memory[self.mem_read_address1]
        self.output2 <<= memory[self.mem_read_address2]
        memory[self.mem_write_address] <<= \
            pyrtl.MemBlock.EnabledWrite(self.mem_write_data, enable=we)

    def test_memblock_direct_assignment_error(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth, name='memory')
        with self.assertRaises(pyrtl.PyrtlError):
            memory[self.mem_write_address] = self.mem_write_data

    def test_memblock_direct_assignment_error(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth, name='memory')
        memory[self.mem_write_address] <<= 5

    # test does not check functionality, just that it will generate hardware
    def test_memblock_to_memblock_direct_operation(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth, addrwidth=self.addrwidth, name='memory')
        temp = (memory[self.mem_read_address1] == memory[self.mem_read_address2])
        temp = (memory[self.mem_read_address1] != memory[self.mem_read_address2])
        temp = (memory[self.mem_read_address1] & memory[self.mem_read_address2])
        temp = (memory[self.mem_read_address1] | memory[self.mem_read_address2])
        temp = (memory[self.mem_read_address1] + memory[self.mem_read_address2])
        temp = (memory[self.mem_read_address1] - memory[self.mem_read_address2])
        temp = (memory[self.mem_read_address1] * memory[self.mem_read_address2])
        self.output1 <<= temp


if __name__ == "__main__":
    unittest.main()
