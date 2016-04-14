import unittest
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

    def invalid_net(self, *args):
        with self.assertRaises(pyrtl.PyrtlInternalError):
            pyrtl.working_block().add_net(*args)

    def test_add_net(self):
        self.invalid_net(None)
        self.invalid_net(1)
        self.invalid_net("hi")
        self.invalid_net(pyrtl.Const(2))

    def test_undriven_net(self):
        w = pyrtl.WireVector(name='testwire', bitwidth=3)
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

        i = 0
        for net in block:
            self.assertFalse(i > 100, "Too many iterations happened")
            i += 1
            print(str(net))

        for net in block.logic:
            print(net)


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

    def test_as_graph_trivial(self):
        i = pyrtl.Input(1)
        o = pyrtl.Output(1)
        b = pyrtl.working_block()
        net = pyrtl.LogicNet('~', None, (i,), (o,))
        b.add_net(net)
        src_g, dst_g = b.as_graph(False)
        self.check_graph_correctness(src_g, dst_g)
        self.assertEqual(src_g[o], net)
        self.assertEqual(dst_g[i][0], net)
        self.assertEqual(len(dst_g[i]), 1)

        self.assertNotIn(i, src_g)
        self.assertNotIn(o, dst_g)

        src_g, dst_g = b.as_graph(True)
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
        src_g, dst_g = b.as_graph(False)
        self.check_graph_correctness(src_g, dst_g)

        src_g, dst_g = b.as_graph(True)
        self.check_graph_correctness(src_g, dst_g, True)





class TestSanityCheck(unittest.TestCase):
    # TODO: We need to test all of sanity check
    pass


class TestLogicNets(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_basic_test(self):
        net = pyrtl.LogicNet('+', 'xx', ("arg1", "arg2"), ("dest",))
        self.assertEqual(str(net), "dest <-- + -- arg1, arg2 (xx)")

    def test_net_with_wirevectors(self):
        pass

    def test_memory_read_print(self):
        pass

    def test_memory_write_print(self):
        pass

    def test_self_equals(self):
        net = pyrtl.LogicNet('+', 'xx', ("arg1", "arg2"), ("dest",))
        self.assertEqual(net, net)

    def test_comparison(self):
        net = pyrtl.LogicNet('+', 'xx', ("arg1", "arg2"), ("dest",))
        with self.assertRaises(pyrtl.PyrtlError):
            a = net < net

    def test_equivelence_of_same_nets(self):
        net = pyrtl.LogicNet('+', 'xx', ("arg1", "arg2"), ("dest",))
        net2 = pyrtl.LogicNet('+', 'xx', ("arg1", "arg2"), ("dest",))
        self.assertIsNot(net, net2)
        self.assertEqual(net, net2)

    def test_equivelence_of_different_nets(self):
        net = pyrtl.LogicNet('+', 'John', ("arg1", "arg2"), ("dest",))
        net2 = pyrtl.LogicNet('+', 'xx', ("arg1", "arg2"), ("dest",))
        self.assertIsNot(net, net2)
        self.assertNotEqual(net, net2)


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
        memory = pyrtl.MemBlock(
                    bitwidth=self.bitwidth, 
                    addrwidth=self.addrwidth,
                    name='memory')
        self.output1 <<= memory[self.mem_read_address1]
        memory[self.mem_write_address] <<= self.mem_write_data
        pyrtl.working_block().sanity_check()

    def test_async_check_should_pass_with_select(self):
        memory = pyrtl.MemBlock(
                    bitwidth=self.bitwidth, 
                    addrwidth=self.addrwidth-1,
                    name='memory')
        self.output1 <<= memory[self.mem_read_address1[0:-1]]
        pyrtl.working_block().sanity_check()

    def test_async_check_should_pass_with_cat(self):
        memory = pyrtl.MemBlock(
                    bitwidth=self.bitwidth, 
                    addrwidth=self.addrwidth,
                    name='memory')
        addr = pyrtl.concat(self.mem_read_address1[0], self.mem_read_address2[0:-1])
        self.output1 <<= memory[addr]
        memory[self.mem_write_address] <<= self.mem_write_data
        pyrtl.working_block().sanity_check()

    def test_async_check_should_notpass_with_add(self):
        memory = pyrtl.MemBlock(
                    bitwidth=self.bitwidth, 
                    addrwidth=self.addrwidth,
                    name='memory')
        addr = pyrtl.WireVector(self.bitwidth)
        addr <<= self.mem_read_address1 + self.mem_read_address2
        self.output1 <<= memory[addr]
        print(pyrtl.working_block())
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.working_block().sanity_check()


if __name__ == "__main__":
    unittest.main()
