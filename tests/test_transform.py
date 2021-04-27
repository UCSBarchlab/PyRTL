from pyrtl.core import set_working_block
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
            new_src = transform.clone_wire(wire, pyrtl.wire.next_tempvar_name())
            new_dst = transform.clone_wire(wire, pyrtl.wire.next_tempvar_name())
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

    def test_replace_input(self):

        def f(wire):
            if wire.name == 'a':
                w = pyrtl.clone_wire(wire, 'w2')
            else:
                w = pyrtl.clone_wire(wire, 'w3')
            return wire, w

        a, b = pyrtl.input_list('a/1 b/1')
        w1 = a & b
        o = pyrtl.Output(1, 'o')
        o <<= w1

        src_nets, dst_nets = pyrtl.working_block().net_connections()
        self.assertEqual(src_nets[w1], pyrtl.LogicNet('&', None, (a, b), (w1,)))
        self.assertIn(a, dst_nets)
        self.assertIn(b, dst_nets)

        transform.wire_transform(f, select_types=pyrtl.Input, exclude_types=tuple())

        w2 = pyrtl.working_block().get_wirevector_by_name('w2')
        w3 = pyrtl.working_block().get_wirevector_by_name('w3')
        src_nets, dst_nets = pyrtl.working_block().net_connections()
        self.assertEqual(src_nets[w1], pyrtl.LogicNet('&', None, (w2, w3), (w1,)))
        self.assertNotIn(a, dst_nets)
        self.assertNotIn(b, dst_nets)

    def test_replace_output(self):

        def f(wire):
            w = pyrtl.clone_wire(wire, 'w2')
            return w, wire

        a, b = pyrtl.input_list('a/1 b/1')
        w1 = a & b
        o = pyrtl.Output(1, 'o')
        o <<= w1

        src_nets, dst_nets = pyrtl.working_block().net_connections()
        self.assertEqual(dst_nets[w1], [pyrtl.LogicNet('w', None, (w1,), (o,))])
        self.assertIn(o, src_nets)

        transform.wire_transform(f, select_types=pyrtl.Output, exclude_types=tuple())

        w2 = pyrtl.working_block().get_wirevector_by_name('w2')
        src_nets, dst_nets = pyrtl.working_block().net_connections()
        self.assertEqual(dst_nets[w1], [pyrtl.LogicNet('w', None, (w1,), (w2,))])
        self.assertNotIn(o, src_nets)


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

    def test_replace_only_src_wire(self):
        a, b, c, d = pyrtl.input_list('a/1 b/1 c/1 d/1')
        w1 = a & b
        w1.name = 'w1'
        w2 = c | d
        w2.name = 'w2'
        w3 = w1 ^ w2
        w3.name = 'w3'
        o = pyrtl.Output(1, 'o')
        o <<= w3

        w4 = pyrtl.WireVector(1, 'w4')
        src_nets, dst_nets = pyrtl.working_block().net_connections()

        w1_src_net = src_nets[w1]
        w1_dst_net = dst_nets[w1][0]
        self.assertEqual(w1_src_net.args, (a, b))
        self.assertEqual(w1_src_net.dests, (w1,))
        self.assertEqual(w1_dst_net.args, (w1, w2))
        self.assertEqual(w1_dst_net.dests, (w3,))
        self.assertNotIn(w4, src_nets)

        pyrtl.transform.replace_wire_fast(w1, w4, w1, src_nets, dst_nets)

        self.assertNotIn(w1, src_nets)  # The maps have been updated...
        self.assertEqual(dst_nets[w1], [w1_dst_net])
        w4_src_net = src_nets[w4]  # ...but the net can't be, so new updated versions were created
        self.assertEqual(w4_src_net.args, w1_src_net.args)
        self.assertEqual(w4_src_net.dests, (w4,))

    def test_replace_only_dst_wire(self):
        a, b, c, d = pyrtl.input_list('a/1 b/1 c/1 d/1')
        w1 = a & b
        w1.name = 'w1'
        w2 = c | d
        w2.name = 'w2'
        w3 = w1 ^ w2
        w3.name = 'w3'
        o = pyrtl.Output(1, 'o')
        o <<= w3

        w4 = pyrtl.WireVector(1, 'w4')
        src_nets, dst_nets = pyrtl.working_block().net_connections()

        w1_src_net = src_nets[w1]
        w1_dst_net = dst_nets[w1][0]
        self.assertEqual(w1_src_net.args, (a, b))
        self.assertEqual(w1_src_net.dests, (w1,))
        self.assertEqual(w1_dst_net.args, (w1, w2))
        self.assertEqual(w1_dst_net.dests, (w3,))
        self.assertNotIn(w4, src_nets)

        pyrtl.transform.replace_wire_fast(w1, w1, w4, src_nets, dst_nets)

        self.assertNotIn(w1, dst_nets)  # The maps have been updated...
        self.assertEqual(src_nets[w1], w1_src_net)
        w4_dst_net = dst_nets[w4][0]  # ...but the net can't be, so new versions were created
        self.assertEqual(w4_dst_net.args, (w4, w2))
        self.assertEqual(w4_dst_net.dests, w1_dst_net.dests)


class TestCloning(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_same_type(self):
        for ix, cls in enumerate([pyrtl.WireVector, pyrtl.Register, pyrtl.Input, pyrtl.Output]):
            w1 = cls(4, 'w%d' % ix)
            w2 = pyrtl.clone_wire(w1, 'y%d' % ix)
            self.assertIsInstance(w2, cls)
            self.assertEqual(w1.bitwidth, w2.bitwidth)

    def test_clone_wire_no_name_same_block(self):
        a = pyrtl.WireVector(1, 'a')
        with self.assertRaises(pyrtl.PyrtlError) as error:
            pyrtl.clone_wire(a)
        self.assertEqual(
            str(error.exception),
            "Must provide a name for the newly cloned wire "
            "when cloning within the same block."
        )

    def test_clone_wire_same_name_same_block(self):
        a = pyrtl.WireVector(1, 'a')
        with self.assertRaises(pyrtl.PyrtlError) as error:
            pyrtl.clone_wire(a, 'a')
        self.assertEqual(
            str(error.exception),
            "Cannot give a newly cloned wire the same name as an existing wire."
        )

    def test_clone_wire_different_name_same_block(self):
        a = pyrtl.WireVector(1, 'a')
        self.assertEqual(a.name, 'a')
        self.assertEqual(pyrtl.working_block().wirevector_set, {a})
        self.assertIs(pyrtl.working_block().wirevector_by_name['a'], a)

        w = pyrtl.clone_wire(a, name='w')
        self.assertEqual(w.name, 'w')
        self.assertEqual(a.name, 'a')
        self.assertIs(pyrtl.working_block().wirevector_by_name['w'], w)
        self.assertIs(pyrtl.working_block().wirevector_by_name['a'], a)
        self.assertEqual(pyrtl.working_block().wirevector_set, {a, w})

        pyrtl.working_block().remove_wirevector(a)
        self.assertEqual(pyrtl.working_block().wirevector_set, {w})

    def test_clone_wire_no_or_same_name_different_block(self):
        for clone_name in (None, 'a'):
            a = pyrtl.WireVector(1, 'a')
            b = pyrtl.Block()
            with pyrtl.set_working_block(b):
                w = pyrtl.clone_wire(a, name=clone_name)

            self.assertEqual(a.name, 'a')
            self.assertIs(pyrtl.working_block().wirevector_by_name['a'], a)
            self.assertEqual(pyrtl.working_block().wirevector_set, {a})

            self.assertEqual(w.name, 'a')
            self.assertIs(b.wirevector_by_name['a'], w)
            self.assertEqual(b.wirevector_set, {w})
            pyrtl.reset_working_block()

    def test_clone_wire_different_name_different_block(self):
        a = pyrtl.WireVector(1, 'a')
        b = pyrtl.Block()
        with set_working_block(b):
            w = pyrtl.clone_wire(a, 'w')
        self.assertEqual(a.name, 'a')
        self.assertEqual(w.name, 'w')
        self.assertIs(pyrtl.working_block().wirevector_by_name['a'], a)
        self.assertEqual(pyrtl.working_block().wirevector_set, {a})
        self.assertIs(b.wirevector_by_name['w'], w)
        self.assertEqual(b.wirevector_set, {w})


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
