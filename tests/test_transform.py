import unittest
import pyrtl
from pyrtl import transform
# this code needs mocking from python 3's unittests to work


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


class TestCopyBlock(NetWireNumTestCases):
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

