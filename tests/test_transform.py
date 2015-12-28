import unittest
import pyrtl
from pyrtl import transform


class NetWireNumTestCases(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def assert_num_net(self, num, block):
        self.assertEqual(len(block.logic), num)

    def assert_num_wires(self, num, block):
        self.assertEqual(len(block.wirevector_set), num)

    def num_net_of_type(self, netOp, num, block):
        self.assertEquals(len([net for net in block.logic if net.op == netOp]), num)

    def num_wire_of_type(self, wiretype, num, block):
        self.assertEquals(len(block.wirevector_subset(wiretype)), num)


def insert_random_inversions(rate=0.5):
    """
    an example transform that can be used for testing
    """

    import random

    def randomly_replace(wire):
        if random.random() < rate:
            new_src, new_dst = transform.clone_wire(wire), transform.clone_wire(wire)
            new_dst <<= ~new_src
            return new_src, new_dst
        return wire, wire

    transform.wire_transform(randomly_replace)


class TestWireTransform(NetWireNumTestCases):
    def test_randomly_replace(self):
        a, b = pyrtl.WireVector(3), pyrtl.WireVector(3)
        o = a & b
        insert_random_inversions(1)
        block = pyrtl.working_block()
        self.num_net_of_type('~', 3, block)
        self.num_net_of_type('&', 1, block)

        new_and_net = block.logic_subset('&').pop()
        for arg in new_and_net.args:
            self.assertIsNot(arg, a)
            self.assertIsNot(arg, b)
        self.assertIsNot(new_and_net.dests[0], o)


class TestCopyBlock(NetWireNumTestCases):
    def num_memories(self, mems_expected, block):
        memories = set()
        for net in block.logic_subset('m@'):
            memories.add(net.op_param[1])  # location of the memories object
        self.assertEqual(mems_expected, len(memories))

    def test_blank(self):
        block = transform.copy_block()
        self.assert_num_net(0, block)
        self.assert_num_wires(0, block)

    def test_block(self):
        a = pyrtl.Const(23)
        b = pyrtl.Input(5)
        o = pyrtl.Output(5)
        o <<= ~a & b

        old_block = pyrtl.working_block()
        old_block.sanity_check()
        self.assert_num_wires(5, old_block)
        self.assert_num_net(3, old_block)

        new_block = transform.copy_block()
        new_block.sanity_check()
        self.assert_num_wires(5, new_block)
        self.assert_num_net(3, old_block)

    def test_copy_mem(self):
        ins = [pyrtl.Input(5) for i in range(4)]
        out = pyrtl.Output(5)

        mem1 = pyrtl.MemBlock(5, 5)
        mem2 = pyrtl.MemBlock(5, 5)

        mem1_o1 = mem1[ins[0]]
        mem1[ins[1]] <<= ins[2]
        mem2_o2 = mem2[ins[3]]
        out <<= mem1_o1 & mem2_o2

        old_block = pyrtl.working_block()
        old_block.sanity_check()
        self.num_net_of_type('m', 2, old_block)
        self.num_net_of_type('@', 1, old_block)
        self.num_net_of_type('&', 1, old_block)
        self.num_memories(2, old_block)

        new_block = transform.copy_block()
        self.num_net_of_type('m', 2, new_block)
        self.num_net_of_type('@', 1, new_block)
        self.num_net_of_type('&', 1, new_block)
        self.num_memories(2, new_block)


# this code needs mocking from python 3's unittests to work
"""
@mock.patch('transform_examples.pyrtl.probe')
def test_probe(self, probe):
    # Note to readers, this is a rather contrived test
    # If you want to know how to probe a single wirevector, look at the
    # probe function in pyrtl core
    in_wire, in_wire2 = pyrtl.Input(3), pyrtl.Input(3)
    out_wire = pyrtl.Output()
    test_wire = ~(in_wire & in_wire2)
    out_wire <<= test_wire

    def probe_cond(wire):
        return wire is test_wire

    transform_examples.probe_wire_if(probe_cond)
    probe.assert_called_once_with(test_wire)
"""

