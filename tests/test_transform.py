import unittest
import pyrtl
from pyrtl import transform


class NetWireNumTestCases(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def assert_num_net(self, num, block=None):
        block = pyrtl.working_block(block)
        self.assertEqual(len(block.logic), num)

    def assert_num_wires(self, num, block=None):
        block = pyrtl.working_block(block)
        self.assertEqual(len(block.wirevector_set), num)

    def num_net_of_type(self, netOp, num, block=None):
        block = pyrtl.working_block(block)
        self.assertEquals(len([net for net in block.logic if net.op == netOp]), num)

    def num_wire_of_type(self, wiretype, num, block=None):
        block = pyrtl.working_block(block)
        self.assertEquals(len(block.wirevector_subset(wiretype)), num)


class WireMemoryNameTestCases(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def name_wires(self, names, block=None):
        block = pyrtl.working_block()
        names = set(names.split(' '))
        for n in names:
            self.assertIn(n, block.wirevector_by_name)

    def name_memories(self, names, block=None):
        block = pyrtl.working_block()
        names = set(names.split(' '))
        for n in names:
            self.assertIn(n, block.memblock_by_name)


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


class TestCopyBlock(NetWireNumTestCases, WireMemoryNameTestCases):
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
        a = pyrtl.Const(23, name='a')
        b = pyrtl.Input(5, name='b')
        o = pyrtl.Output(5, name='o')
        o <<= ~a & b

        old_block = pyrtl.working_block()
        old_block.sanity_check()
        self.assert_num_wires(5, old_block)
        self.assert_num_net(3, old_block)

        self.name_wires('a b o', old_block)

        new_block = transform.copy_block()
        new_block.sanity_check()
        self.assert_num_wires(5, new_block)
        self.assert_num_net(3, new_block)

        self.name_wires('a b o', new_block)

    def test_copy_mem(self):
        ins = [pyrtl.Input(5) for i in range(4)]
        out = pyrtl.Output(5)

        mem1 = pyrtl.MemBlock(5, 5, name='mem1')
        mem2 = pyrtl.MemBlock(5, 5, name='mem2')

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

        self.name_memories('mem1 mem2', old_block)

        new_block = transform.copy_block()
        self.num_net_of_type('m', 2, new_block)
        self.num_net_of_type('@', 1, new_block)
        self.num_net_of_type('&', 1, new_block)
        self.num_memories(2, new_block)

        self.name_memories('mem1 mem2', new_block)


class TestFastWireReplace(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_replace_multiple_wires(self):
        j, n = pyrtl.Input(8), pyrtl.Output(8)
        o, h = pyrtl.WireVector(), pyrtl.WireVector()
        x, y = pyrtl.WireVector(8), pyrtl.WireVector(8)

        o <<= j
        h <<= o
        n <<= h
        block = pyrtl.working_block()
        src_nets, dst_nets = block.net_connections()
        transform.replace_wire_fast(o, x, x, src_nets, dst_nets)
        transform.replace_wire_fast(h, y, y, src_nets, dst_nets)
        for old_wire in (o, h):
            self.assertNotIn(old_wire, src_nets)
            self.assertNotIn(old_wire, dst_nets)
            self.assertNotIn(old_wire, block.wirevector_set)
        block.sanity_check()

    def test_replace_multiple_wires_2(self):
        j, n = pyrtl.Input(8), pyrtl.Output(8)
        o = pyrtl.WireVector()
        x, y, z = pyrtl.WireVector(8), pyrtl.WireVector(8), pyrtl.WireVector(8)

        o <<= j
        p = ~ j
        h = o & p
        n <<= h
        block = pyrtl.working_block()
        src_nets, dst_nets = block.net_connections()
        transform.replace_wire_fast(o, x, x, src_nets, dst_nets)
        transform.replace_wire_fast(p, z, z, src_nets, dst_nets)
        transform.replace_wire_fast(h, y, y, src_nets, dst_nets)
        for old_wire in (o, h, p):
            self.assertNotIn(old_wire, src_nets)
            self.assertNotIn(old_wire, dst_nets)
            self.assertNotIn(old_wire, block.wirevector_set)
        block.sanity_check()

    def test_wire_used_in_multiple_places(self):
        j, k = pyrtl.Input(8), pyrtl.Input(8)
        n, o = pyrtl.Output(8), pyrtl.Output(8)
        x = pyrtl.WireVector(8)

        r = j & k
        n <<= j | r
        o <<= r ^ k

        block = pyrtl.working_block()
        src_nets, dst_nets = block.net_connections()
        transform.replace_wire_fast(r, x, x, src_nets, dst_nets)

        for old_wire in (r,):
            self.assertNotIn(old_wire, src_nets)
            self.assertNotIn(old_wire, dst_nets)
            self.assertNotIn(old_wire, block.wirevector_set)
        block.sanity_check()


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

if __name__ == "__main__":
    unittest.main()
