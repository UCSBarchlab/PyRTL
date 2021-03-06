from __future__ import print_function
import unittest
import six
import pyrtl


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

    def invalid_wire(self, *args):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.working_block().add_wirevector(*args)

    def test_add_wire(self):
        self.invalid_wire(None)
        self.invalid_wire("Hi John")
        self.invalid_wire(42)

    def test_undriven_net(self):
        w = pyrtl.WireVector(name='testwire', bitwidth=3)
        self.assertRaises(pyrtl.PyrtlError, pyrtl.working_block().sanity_check)
        pyrtl.reset_working_block()
        r = pyrtl.Register(3)
        self.assertRaises(pyrtl.PyrtlError, pyrtl.working_block().sanity_check)
        pyrtl.reset_working_block()
        o = pyrtl.Output(3)
        self.assertRaises(pyrtl.PyrtlError, pyrtl.working_block().sanity_check)

    def test_no_logic_net_comparisons(self):
        a = pyrtl.WireVector(bitwidth=3)
        b = pyrtl.WireVector(bitwidth=3)
        select = pyrtl.WireVector(bitwidth=3)
        outwire = pyrtl.WireVector(bitwidth=3)
        net1 = pyrtl.LogicNet(op='x', op_param=None, args=(select, a, b), dests=(outwire,))
        net2 = pyrtl.LogicNet(op='x', op_param=None, args=(select, b, a), dests=(outwire,))
        with self.assertRaises(pyrtl.PyrtlError):
            foo = net1 < net2
        with self.assertRaises(pyrtl.PyrtlError):
            foo = net1 <= net2
        with self.assertRaises(pyrtl.PyrtlError):
            foo = net1 > net2
        with self.assertRaises(pyrtl.PyrtlError):
            foo = net1 >= net2

    def test_logicsubset_no_op(self):
        w = pyrtl.WireVector(name='testwire1', bitwidth=1)
        v = pyrtl.WireVector(name='testwire2', bitwidth=1)
        sum = w & v
        block = pyrtl.working_block()
        self.assertEqual(block.logic_subset(None), block.logic)

    def test_sanity_check(self):
        pass

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

        output = six.StringIO()
        i = 0
        for net in block:
            self.assertFalse(i > 100, "Too many iterations happened")
            i += 1
            print(str(net), file=output)

        for net in block.logic:
            print(net, file=output)

    def test_no_memblocks(self):
        block = pyrtl.working_block()
        self.assertFalse(block.memblock_by_name)

    def test_bad_memblock_name_strict(self):
        block = pyrtl.working_block()
        with self.assertRaises(pyrtl.PyrtlError):
            _ = block.get_memblock_by_name('bad_mem', strict=True)

    def test_bad_memblock_name_none(self):
        block = pyrtl.working_block()
        mem = block.get_memblock_by_name('bad_mem')
        self.assertIsNone(mem)

    def test_same_memblock_referenced_across_multiple_operators(self):
        mem_name = 'mem'
        mem = pyrtl.MemBlock(32, 5, mem_name)
        x = mem[0]
        mem[1] <<= 42
        mem = pyrtl.working_block().get_memblock_by_name(mem_name)
        for net in pyrtl.working_block().logic:
            if net.op == 'm':
                self.assertIs(net.op_param[1], mem)
            if net.op == '@':
                self.assertIs(net.op_param[1], mem)


class TestSanityCheckNet(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def invalid_net(self, exp_message, *args):
        with self.assertRaisesRegexp(pyrtl.PyrtlInternalError, exp_message):
            pyrtl.working_block().add_net(*args)

    @staticmethod
    def new_net(op='&', op_param=None, args=None, dests=None):
        if args is None or isinstance(args, int):
            args = tuple(pyrtl.Input(2) for i in range(args if isinstance(args, int) else 2))
        if dests is None or isinstance(dests, int):
            def dest():
                return pyrtl.Register(2) if op == 'r' else pyrtl.Output(2)
            dests = tuple(dest() for i in range(dests if isinstance(dests, int) else 1))
        return pyrtl.LogicNet(op=op, op_param=op_param, args=args, dests=dests)

    def test_net_make_with_not_net(self):
        self.invalid_net("net must be of type LogicNet", None)
        self.invalid_net("net must be of type LogicNet", 1)
        self.invalid_net("net must be of type LogicNet", "hi")
        self.invalid_net("net must be of type LogicNet", pyrtl.Const(2))

    def test_net_no_tuples(self):
        net = self.new_net(args=(pyrtl.Const(2)))
        self.invalid_net("LogicNet args must be tuple", net)
        net = self.new_net(dests=(pyrtl.Const(2)))
        self.invalid_net("LogicNet dests must be tuple", net)

    def test_net_odd_wires(self):
        wire = pyrtl.WireVector(2, 'wire')
        net = self.new_net(args=(wire, wire))
        other_block = pyrtl.Block()
        wire._block = other_block
        self.invalid_net("net references different block", net)

        pyrtl.reset_working_block()
        wire = pyrtl.WireVector(2, 'wire')
        net = self.new_net(args=(wire,))
        pyrtl.working_block().remove_wirevector(wire)
        self.invalid_net("net with unknown source", net)

    def test_net_wrong_types(self):
        inp = pyrtl.Input(2)
        const = pyrtl.Const(2)
        outp = pyrtl.Output(2)
        net = self.new_net(dests=(inp,))
        self.invalid_net("Inputs, Consts cannot be destinations", net)
        net = self.new_net(dests=(const,))
        self.invalid_net("Inputs, Consts cannot be destinations", net)
        net = self.new_net(args=(outp, outp))
        self.invalid_net("Outputs cannot be arguments", net)

        wrong_ops = ('%', '!', 'a', 'f', '<<', '>>', '&&', '||', '==')
        for op in wrong_ops:
            net = self.new_net(op=op)
            self.invalid_net("not from acceptable set", net)

    def test_net_wrong_num_args(self):
        for op in 'w~rsm':
            net = self.new_net(op=op)
            self.invalid_net("op only allowed 1 argument", net)
        for op in '&|^n+-*<>=':
            net = self.new_net(op=op, args=3)
            self.invalid_net("op only allowed 2 arguments", net)
        for op in 'x@':
            net = self.new_net(op=op, args=4)
            self.invalid_net("op only allowed 3 arguments", net)

    def test_net_wrong_bitwidth(self):
        net = self.new_net(op='x', args=tuple(pyrtl.Input(i) for i in range(1, 4)))
        self.invalid_net("args have mismatched bitwidths", net)
        net = self.new_net(op='x', args=tuple(pyrtl.Input(2) for i in range(3)))
        self.invalid_net("mux select must be a single bit", net)

        for op in '&|^n+-*<>=':
            net = self.new_net(op=op, args=(tuple(pyrtl.Input(i) for i in range(2, 4))))
            self.invalid_net("args have mismatched bitwidths", net)

        net = self.new_net(op='m', op_param=(1234, pyrtl.MemBlock(2, 3)), args=1)
        self.invalid_net("mem addrwidth mismatch", net)

        net = self.new_net(op='@', op_param=(1234, pyrtl.MemBlock(2, 2)),
                           args=tuple(pyrtl.Input(i) for i in (4, 2, 1)))
        self.invalid_net("mem addrwidth mismatch", net)
        net = self.new_net(op='@', op_param=(1234, pyrtl.MemBlock(2, 2)),
                           args=tuple(pyrtl.Input(i) for i in (2, 4, 1)))
        self.invalid_net("mem bitwidth mismatch", net)
        net = self.new_net(op='@', op_param=(1234, pyrtl.MemBlock(2, 2)), args=3)
        self.invalid_net("mem write enable must be 1 bit", net)

    def test_net_wrong_num_op_params(self):
        for op in 'w~r':
            net = self.new_net(op=op, op_param=('hi', 'how', 'r', 'u'), args=1)
            self.invalid_net("op_param should be None", net)
        for op in '&|^n+-*<>=c':
            net = self.new_net(op=op, op_param=('hi', 'how', 'r', 'u'), args=2)
            self.invalid_net("op_param should be None", net)
        net = self.new_net(op='x', op_param=('hi', 'how', 'r', 'u'),
                           args=tuple(pyrtl.Input(i) for i in (1, 2, 2)))
        self.invalid_net("op_param should be None", net)

    def test_net_wrong_op_param_select(self):
        net = self.new_net(op='s', op_param='hi', args=1)
        self.invalid_net("select op requires tuple op_param", net)
        net = self.new_net(op='s', op_param=(-2,), args=1)
        self.invalid_net("op_param out of bounds", net)
        net = self.new_net(op='s', op_param=(10,), args=1)
        self.invalid_net("op_param out of bounds", net)
        net = self.new_net(op='s', op_param=(0, 1, 3), args=1)
        self.invalid_net("op_param out of bounds", net)
        net = self.new_net(op='s', op_param=(0, True, False, dict(), 'hi'), args=1)
        self.invalid_net("select op_param requires ints", net)

    def test_net_wrong_op_param_mem(self):
        for op in 'm@':
            net = self.new_net(op=op, op_param=[1234, pyrtl.MemBlock(1, 1)],
                               args=tuple(pyrtl.Input(1) for i in range(1 if op == 'm' else 3)))
            self.invalid_net("mem op requires tuple op_param", net)
        for op in 'm@':
            net = self.new_net(op=op, op_param=(1234, pyrtl.MemBlock(1, 1), 'hi'),
                               args=tuple(pyrtl.Input(1) for i in range(1 if op == 'm' else 3)))
            self.invalid_net("mem op requires 2 op_params in tuple", net)
        for op in 'm@':
            net = self.new_net(op=op, op_param=('hi', pyrtl.MemBlock(1, 1)),
                               args=tuple(pyrtl.Input(1) for i in range(1 if op == 'm' else 3)))
            self.invalid_net("mem op requires first operand as int", net)

        class NotMem:  # so that some earlier mem tests can work properly
            def __init__(self, bw=1, aw=1):
                self.bitwidth, self.addrwidth = bw, aw

        for op in 'm@':
            net = self.new_net(op=op, op_param=(1234, NotMem()),
                               args=tuple(pyrtl.Input(1) for i in range(1 if op == 'm' else 3)))
            self.invalid_net("mem op requires second operand of a memory type", net)

    def test_net_dest_wrong_arity_or_type(self):
        for op in 'w~&|^n+-*<>=cr':
            net = self.new_net(op=op, args=1 if op in 'w~r' else 2, dests=2)
            self.invalid_net("error, op only allowed 1 destination", net)
        net = self.new_net(op='s', op_param=(1,), args=1, dests=2)
        self.invalid_net("error, op only allowed 1 destination", net)
        net = self.new_net(op='x', args=(pyrtl.Input(1), pyrtl.Input(2), pyrtl.Input(2)), dests=2)
        self.invalid_net("error, op only allowed 1 destination", net)
        net = self.new_net(op='m', op_param=(1234, pyrtl.MemBlock(1, 2)), args=1, dests=2)
        self.invalid_net("error, op only allowed 1 destination", net)

        net = self.new_net(op='@', op_param=(1234, pyrtl.MemBlock(2, 2)),
                           args=tuple(pyrtl.Input(i) for i in (2, 2, 1)))
        self.invalid_net("mem write dest should be empty tuple", net)

        net = self.new_net(op='r', args=1, dests=(pyrtl.WireVector(2),))
        self.invalid_net("error, dest of next op should be a Register", net)

    def test_net_dest_wrong_bitwidth(self):
        for op in 'w~&|^n':
            net = self.new_net(op=op, args=1 if op in 'w~' else 2, dests=(pyrtl.Output(3),))
            self.invalid_net("upper bits of destination unassigned", net)
        net = self.new_net(op='r', args=1, dests=(pyrtl.Register(3),))
        self.invalid_net("upper bits of destination unassigned", net)
        for op in '<>=':
            net = self.new_net(op=op, dests=(pyrtl.Output(2),))
            self.invalid_net("destination should be of bitwidth=1", net)
        for op in '+-':
            net = self.new_net(op=op, dests=(pyrtl.Output(4),))
            self.invalid_net("upper bits of destination unassigned", net)
        net = self.new_net(op='*', dests=(pyrtl.Output(5),))
        self.invalid_net("upper bits of destination unassigned", net)
        net = self.new_net(op='x', args=tuple(pyrtl.Input(1) for i in range(3)))
        self.invalid_net("upper bits of mux output undefined", net)
        net = self.new_net(op='c', args=3, dests=(pyrtl.Output(7),))
        self.invalid_net("upper bits of concat output undefined", net)
        net = self.new_net(op='s', args=1, op_param=(1,))
        self.invalid_net("upper bits of select output undefined", net)
        net = self.new_net(op='m', op_param=(1234, pyrtl.MemBlock(3, 2)), args=1)
        self.invalid_net("mem read dest bitwidth mismatch", net)


class TestSetWorkingBlock(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.block_a = pyrtl.Block()
        self.block_b = pyrtl.Block()

    def test_normal(self):
        pyrtl.set_working_block(self.block_a)
        self.assertIs(pyrtl.working_block(), self.block_a)
        pyrtl.set_working_block(self.block_b)
        self.assertIs(pyrtl.working_block(), self.block_b)

    def test_with_block(self):
        pyrtl.set_working_block(self.block_a)
        self.assertIs(pyrtl.working_block(), self.block_a)
        with pyrtl.set_working_block(self.block_b):
            self.assertIs(pyrtl.working_block(), self.block_b)
        self.assertIs(pyrtl.working_block(), self.block_a)

    def test_with_block_nested(self):
        self.block_c = pyrtl.Block()
        pyrtl.set_working_block(self.block_a)
        self.assertIs(pyrtl.working_block(), self.block_a)
        with pyrtl.set_working_block(self.block_b):
            self.assertIs(pyrtl.working_block(), self.block_b)
            with pyrtl.set_working_block(self.block_c):
                self.assertIs(pyrtl.working_block(), self.block_c)
            self.assertIs(pyrtl.working_block(), self.block_b)
        self.assertIs(pyrtl.working_block(), self.block_a)

    def test_with_block_exception(self):
        pyrtl.set_working_block(self.block_a)
        with self.assertRaises(pyrtl.PyrtlInternalError):
            with pyrtl.set_working_block(self.block_b):
                self.assertIs(pyrtl.working_block(), self.block_b)
                raise pyrtl.PyrtlInternalError()
        self.assertIs(pyrtl.working_block(), self.block_a)

    def test_invalid_set_wb(self):
        x = pyrtl.WireVector()
        y = 1
        pyrtl.set_working_block(self.block_a)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.set_working_block(x)
        self.assertEqual(pyrtl.working_block(), self.block_a)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.set_working_block(y)
        self.assertEqual(pyrtl.working_block(), self.block_a)

    def test_invalid_with_set_wb(self):
        x = pyrtl.Input()
        y = True
        pyrtl.set_working_block(self.block_a)
        with self.assertRaises(pyrtl.PyrtlError):
            with pyrtl.set_working_block(x):
                pass
        self.assertEqual(pyrtl.working_block(), self.block_a)
        with self.assertRaises(pyrtl.PyrtlError):
            with pyrtl.set_working_block(y):
                pass
        self.assertEqual(pyrtl.working_block(), self.block_a)


class TestAsGraph(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def check_graph_correctness(self, w_src_graph, w_dst_graph, has_virtual=False):
        for wire, net in w_src_graph.items():
            if isinstance(wire, (pyrtl.Input, pyrtl.Const)):
                if has_virtual:
                    self.assertIs(wire, net)
                else:
                    self.fail("Input or Const, {} should not have a src".format(str(wire)))
            else:
                self.assertTrue(any(wire is w for w in net.dests))

        for wire, nets in w_dst_graph.items():
            if isinstance(wire, pyrtl.Output):
                if has_virtual:
                    self.assertEqual(len(nets), 1)
                    self.assertIs(wire, nets[0])
                else:
                    self.fail("Output, {} should not have a dst".format(str(wire)))
            else:
                for net in nets:
                    self.assertTrue(any(wire is w for w in net.args))
            self.assertEqual(len(nets), len(set(nets)))

        for net in pyrtl.working_block().logic:
            for wire in net.args:
                self.assertIn(net, w_dst_graph[wire])
            for wire in net.dests:
                self.assertIs(w_src_graph[wire], net)

    def test_as_graph_trivial(self):
        i = pyrtl.Input(1)
        o = pyrtl.Output(1)
        b = pyrtl.working_block()
        net = pyrtl.LogicNet('~', None, (i,), (o,))
        b.add_net(net)
        src_g, dst_g = b.net_connections(False)
        self.check_graph_correctness(src_g, dst_g)
        self.assertEqual(src_g[o], net)
        self.assertEqual(dst_g[i][0], net)
        self.assertEqual(len(dst_g[i]), 1)

        self.assertNotIn(i, src_g)
        self.assertNotIn(o, dst_g)

        src_g, dst_g = b.net_connections(True)
        self.check_graph_correctness(src_g, dst_g, True)
        self.assertEqual(src_g[o], net)
        self.assertEqual(dst_g[i][0], net)
        self.assertEqual(len(dst_g[i]), 1)

        self.assertIs(src_g[i], i)
        self.assertIs(dst_g[o][0], o)
        self.assertEqual(len(dst_g[o]), 1)

    def test_as_graph_2(self):
        a = pyrtl.Input(2)
        b = pyrtl.Input(2)
        c = pyrtl.Input(2)
        e = pyrtl.Output()
        f = pyrtl.Output()
        g = pyrtl.Output()

        d = a & c
        f <<= b & c
        e <<= d
        g <<= ~(d | b)

        b = pyrtl.working_block()
        src_g, dst_g = b.net_connections(False)
        self.check_graph_correctness(src_g, dst_g)

        src_g, dst_g = b.net_connections(True)
        self.check_graph_correctness(src_g, dst_g, True)

    def test_as_graph_memory(self):
        m = pyrtl.MemBlock(addrwidth=2, bitwidth=2, name='m', max_read_ports=None)
        i = pyrtl.Register(bitwidth=2, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        m[i] <<= pyrtl.mux((m[i] != 0), 0, m[i])
        o <<= m[i]

        b = pyrtl.working_block()
        src_g, dst_g = b.net_connections(False)
        self.check_graph_correctness(src_g, dst_g)

        src_g, dst_g = b.net_connections(True)
        self.check_graph_correctness(src_g, dst_g, True)

    def test_as_graph_duplicate_args(self):
        a = pyrtl.Input(3)
        x = pyrtl.Input(1)
        d = pyrtl.Output()
        b = a & a
        c = pyrtl.concat(a, a)
        m = pyrtl.MemBlock(addrwidth=3, bitwidth=3, name='m')
        m2 = pyrtl.MemBlock(addrwidth=1, bitwidth=1, name='m')
        d <<= m[a]
        m[a] <<= a
        m2[x] <<= pyrtl.MemBlock.EnabledWrite(x, x)

        b = pyrtl.working_block()
        src_g, dst_g = b.net_connections(False)
        self.check_graph_correctness(src_g, dst_g)

        src_g, dst_g = b.net_connections(True)
        self.check_graph_correctness(src_g, dst_g, True)


class TestSanityCheck(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def sanity_error(self, msg):
        with self.assertRaisesRegexp(pyrtl.PyrtlError, msg):
            pyrtl.working_block().sanity_check()

    def test_missing_bitwidth(self):
        inp = pyrtl.Input()
        out = pyrtl.Output(8)
        self.sanity_error("missing bitwidth")

    def test_duplicate_names(self):
        inp = pyrtl.Input(8, 'hi')
        out = pyrtl.Output(8, 'hi')
        out <<= inp
        self.sanity_error("Duplicate wire names")

    def test_unknown_wires(self):
        inp = pyrtl.Input(8, 'inp')
        out = pyrtl.Output(8, 'out')
        out <<= inp
        pyrtl.working_block().wirevector_set.discard(inp)
        with self.assertRaises(pyrtl.PyrtlInternalError):  # sanity_check_net()
            self.sanity_error("Unknown wires")

    def test_not_connected(self):
        inp = pyrtl.Input(8, 'inp')
        out = pyrtl.Output(8, 'out')
        self.sanity_error("declared but not connected")

    def test_not_driven(self):
        w = pyrtl.WireVector(8, 'w')
        out = pyrtl.Output(8, 'out')
        out <<= w
        self.sanity_error("used but never driven")


class TestLogicNets(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_string_format(self):
        net = pyrtl.LogicNet('+', 'xx', ("arg1", "arg2"), ("dest",))
        self.assertEqual(str(net), "dest <-- + -- arg1, arg2 (xx)")

    def test_net_with_wirevectors(self):
        pass

    def test_memory_read_print(self):
        pass

    def test_memory_write_print(self):
        pass

    def test_self_equals(self):
        a = pyrtl.WireVector()
        b = pyrtl.WireVector()
        c = pyrtl.WireVector()
        net = pyrtl.LogicNet('+', 'xx', (a, b), (c,))
        self.assertEqual(net, net)

    def test_comparison(self):
        net = pyrtl.LogicNet('+', 'xx', ("arg1", "arg2"), ("dest",))
        with self.assertRaises(pyrtl.PyrtlError):
            a = net < net
        with self.assertRaises(pyrtl.PyrtlError):
            a = net <= net
        with self.assertRaises(pyrtl.PyrtlError):
            a = net >= net
        with self.assertRaises(pyrtl.PyrtlError):
            a = net > net

    def test_equivelence_of_same_nets(self):
        a = pyrtl.WireVector(1)
        b = pyrtl.WireVector(1)
        c = pyrtl.WireVector(1)
        net = pyrtl.LogicNet('+', 'xx', (a, b), (c,))
        net2 = pyrtl.LogicNet('+', 'xx', (a, b), (c,))
        self.assertIsNot(net, net2)
        self.assertEqual(net, net2)

    def assertDifferentNets(self, net1, net2):
        self.assertIsNot(net1, net2)
        self.assertNotEqual(net1, net2)
        self.assertTrue(net1 != net2)  # to test the proper working of __ne__

    def test_equivelence_of_different_nets(self):
        a = pyrtl.WireVector()
        b = pyrtl.WireVector()
        c = pyrtl.WireVector()

        n = pyrtl.LogicNet('-', 'John', (a, b), (c,))
        net = pyrtl.LogicNet('+', 'John', (a, b), (c,))
        net2 = pyrtl.LogicNet('+', 'xx', (a, b), (c,))
        net3 = pyrtl.LogicNet('+', 'xx', (b, a), (c,))
        net4 = pyrtl.LogicNet('+', 'xx', (b, a, c), (c,))
        net5 = pyrtl.LogicNet('+', 'xx', (b, a, c), (c, a))
        net6 = pyrtl.LogicNet('+', 'xx', (b, a, c), (a,))

        self.assertDifferentNets(n, net)
        self.assertDifferentNets(net, net2)
        self.assertDifferentNets(net2, net3)
        self.assertDifferentNets(net3, net4)
        self.assertDifferentNets(net4, net5)
        self.assertDifferentNets(net4, net6)
        self.assertDifferentNets(net5, net6)

        # some extra edge cases to check
        netx_1 = pyrtl.LogicNet('+', 'John', (a, a), (c,))
        netx_2 = pyrtl.LogicNet('+', 'John', (a,), (c,))
        self.assertDifferentNets(netx_1, netx_2)


class TestMemAsyncCheck(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.addrwidth = 5
        self.output1 = pyrtl.Output(self.bitwidth, "output1")
        self.mem_read_address1 = pyrtl.Input(self.addrwidth, name='mem_read_address1')
        self.mem_read_address2 = pyrtl.Input(self.addrwidth, name='mem_read_address2')
        self.mem_write_address = pyrtl.Input(self.addrwidth, name='mem_write_address')
        self.mem_write_data = pyrtl.Input(self.bitwidth, name='mem_write_data')

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_async_check_should_pass(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth,
                                addrwidth=self.addrwidth,
                                name='memory')
        self.output1 <<= memory[self.mem_read_address1]
        memory[self.mem_write_address] <<= self.mem_write_data
        pyrtl.working_block().sanity_check()

    def test_async_check_should_pass_with_select(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth,
                                addrwidth=self.addrwidth - 1,
                                name='memory')
        self.output1 <<= memory[self.mem_read_address1[0:-1]]
        pyrtl.working_block().sanity_check()

    def test_async_check_should_pass_with_cat(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth,
                                addrwidth=self.addrwidth,
                                name='memory')
        addr = pyrtl.concat(self.mem_read_address1[0], self.mem_read_address2[0:-1])
        self.output1 <<= memory[addr]
        memory[self.mem_write_address] <<= self.mem_write_data
        pyrtl.working_block().sanity_check()

    def test_async_check_should_notpass_with_add(self):
        memory = pyrtl.MemBlock(bitwidth=self.bitwidth,
                                addrwidth=self.addrwidth,
                                name='memory')
        addr = pyrtl.WireVector(self.bitwidth)
        addr <<= self.mem_read_address1 + self.mem_read_address2
        self.output1 <<= memory[addr]
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.working_block().sanity_check()


if __name__ == "__main__":
    unittest.main()
