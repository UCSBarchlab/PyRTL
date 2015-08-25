import unittest
import random
import pyrtl

from helperfunctions import testmissing


class TestBlock(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_add_wirevector_simple(self):
        w = pyrtl.WireVector(name='testwire', bitwidth=3)
        pyrtl.working_block().add_wirevector(w)
        self.assertTrue(w in pyrtl.working_block().wirevector_set)
        self.assertTrue('testwire' in pyrtl.working_block().wirevector_by_name)

    def test_add_net(self):
        self.assertRaises(pyrtl.PyrtlInternalError, pyrtl.working_block().add_net, None)
        self.assertRaises(pyrtl.PyrtlInternalError, pyrtl.working_block().add_net, 1)
        self.assertRaises(pyrtl.PyrtlInternalError, pyrtl.working_block().add_net, "hi")

    def test_undriven_net(self):
        w = pyrtl.WireVector(name='testwire', bitwidth=3)
        self.assertRaises(pyrtl.PyrtlError, pyrtl.working_block().sanity_check)

    def test_sanity_check(self):
        testmissing()

    def test_block_iterators(self):
        # testing to see that it properly runs a trivial case
        inwire = pyrtl.Input(bitwidth=1, name="inwire1")
        inwire2 = pyrtl.Input(bitwidth=1)
        inwire3 = pyrtl.Input(bitwidth=1)
        tempwire = pyrtl.WireVector()
        tempwire2 = pyrtl.WireVector()
        outwire = pyrtl.Output()

        tempwire <<= inwire | inwire2
        tempwire2 <<= ~tempwire
        outwire <<= tempwire2 & inwire3

        block = pyrtl.working_block()

        i = 0
        for net in block:
            self.assertFalse(i > 100, "Too many iterations happened")
            i += 1
            print str(net)

        for net in block.logic:
            print net


class TestMemAsyncCheck(unittest.TestCase):
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

    def test_async_check_should_pass(self):
        memory = pyrtl.MemBlock(
                    bitwidth=self.bitwidth, 
                    addrwidth=self.addrwidth,
                    name='memory')
        self.output1 <<= memory[self.mem_read_address1]
        memory[self.mem_write_address] <<= self.mem_write_data
        pyrtl.working_block().sanity_check

    def test_async_check_should_pass_with_select(self):
        memory = pyrtl.MemBlock(
                    bitwidth=self.bitwidth, 
                    addrwidth=self.addrwidth-1,
                    name='memory')
        self.output1 <<= memory[self.mem_read_address1[0:-1]]
        pyrtl.working_block().sanity_check

    def test_async_check_should_pass_with_cat(self):
        memory = pyrtl.MemBlock(
                    bitwidth=self.bitwidth, 
                    addrwidth=self.addrwidth,
                    name='memory')
        addr = pyrtl.concat(self.mem_read_address1[0], self.mem_read_address2[0:-1])
        self.output1 <<= memory[addr]
        memory[self.mem_write_address] <<= self.mem_write_data
        pyrtl.working_block().sanity_check

    def test_async_check_should_notpass_with_add(self):
        pyrtl.set_debug_mode()
        memory = pyrtl.MemBlock(
                    bitwidth=self.bitwidth, 
                    addrwidth=self.addrwidth,
                    name='memory')
        addr = pyrtl.WireVector(self.bitwidth)
        addr <<= self.mem_read_address1 + self.mem_read_address2
        self.output1 <<= memory[addr]
        print pyrtl.working_block()
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.working_block().sanity_check()


if __name__ == "__main__":
    unittest.main()
