import doctest
import unittest

import pyrtl


class TestDocTests(unittest.TestCase):
    """Test documentation examples."""

    def test_doctests(self):
        failures, tests = doctest.testmod(m=pyrtl.gate_graph)
        self.assertGreater(tests, 0)
        self.assertEqual(failures, 0)


class TestGateGraph(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_gate_retrieval(self):
        a = pyrtl.Input(name="a", bitwidth=1)
        b = pyrtl.Input(name="b", bitwidth=1)
        c = pyrtl.Input(name="c", bitwidth=2)
        ab = a + b
        ab.name = "ab"
        abc = ab - c
        abc.name = "abc"

        gate_graph = pyrtl.GateGraph()

        self.assertEqual(
            sorted([gate.dest_name for gate in gate_graph.gates]),
            ["a", "ab", "abc", "b", "c"],
        )

        self.assertEqual(
            sorted([gate.dest_name for gate in gate_graph.sources]), ["a", "b", "c"]
        )

        self.assertEqual(sorted([gate.dest_name for gate in gate_graph.sinks]), ["abc"])

        self.assertEqual(gate_graph.get_gate("foo"), None)

        gate_ab = gate_graph.get_gate("ab")
        self.assertEqual(gate_ab.dest_name, "ab")
        self.assertEqual(gate_ab.op, "+")

        gate_abc = gate_graph.get_gate("abc")
        self.assertEqual(gate_abc.dest_name, "abc")
        self.assertEqual(gate_abc.op, "-")

    def test_gate_attrs(self):
        a = pyrtl.Input(name="a", bitwidth=4)
        b = pyrtl.Const(name="b", bitwidth=2, val=1)
        bit_slice = a[2:4]
        bit_slice.name = "bit_slice"
        ab = bit_slice + b
        ab.name = "ab"

        output = pyrtl.Output(name="output", bitwidth=3)
        output <<= b + b

        gate_graph = pyrtl.GateGraph()

        a_gate = gate_graph.get_gate("a")
        self.assertEqual(a_gate.op, "I")

        b_gate = gate_graph.get_gate("b")
        self.assertEqual(b_gate.op, "C")
        self.assertEqual(b_gate.op_param, (1,))

        bit_slice_gate = gate_graph.get_gate("bit_slice")
        self.assertEqual(bit_slice_gate.op, "s")

        self.assertEqual(bit_slice_gate.op_param, (2, 3))

        self.assertEqual(bit_slice_gate.args, [a_gate])

        self.assertEqual(bit_slice_gate.dest_name, "bit_slice")
        self.assertEqual(bit_slice_gate.dest_bitwidth, 2)

        ab_gate = gate_graph.get_gate("ab")
        self.assertEqual(ab_gate.op, "+")

        self.assertEqual(ab_gate.args, [bit_slice_gate, b_gate])

        self.assertEqual(ab_gate.dest_name, "ab")
        self.assertEqual(ab_gate.dest_bitwidth, 3)
        self.assertFalse(ab_gate.dest_is_output)

        output_gate = gate_graph.get_gate("output")
        self.assertEqual(output_gate.op, "w")
        self.assertTrue(output_gate.dest_is_output)

        self.assertEqual(len(output_gate.args), 1)
        output_add_gate = output_gate.args[0]

        self.assertEqual(output_add_gate.args, [b_gate, b_gate])

        self.assertEqual(len(b_gate.dest_fanout), 3)
        num_ab_gates = 0
        num_output_add_gates = 0
        for dest_gate in b_gate.dest_fanout:
            if dest_gate is ab_gate:
                num_ab_gates += 1
            elif dest_gate is output_add_gate:
                num_output_add_gates += 1
        self.assertEqual(num_ab_gates, 1)
        self.assertEqual(num_output_add_gates, 2)

    def test_register_gate_forward(self):
        counter = pyrtl.Register(name="counter", bitwidth=3)
        one = pyrtl.Const(name="one", bitwidth=3, val=1)
        counter.next <<= counter + one

        gate_graph = pyrtl.GateGraph()

        # Traverse the GateGraph forward, following ``dest_fanout`` references, from
        # ``counter``. We should end up back at ``counter``.
        counter_gate = gate_graph.get_gate("counter")
        self.assertEqual(len(counter_gate.dest_fanout), 1)

        plus_gate = counter_gate.dest_fanout[0]
        self.assertEqual(plus_gate.op, "+")
        self.assertEqual(len(plus_gate.dest_fanout), 1)

        # Implicit truncation from 4-bit sum to 3-bit register input.
        slice_gate = plus_gate.dest_fanout[0]
        self.assertEqual(slice_gate.op, "s")
        self.assertEqual(len(slice_gate.dest_fanout), 1)

        self.assertEqual(slice_gate.dest_fanout[0], counter_gate)

    def test_register_gate_backward(self):
        counter = pyrtl.Register(name="counter", bitwidth=3)
        one = pyrtl.Const(name="one", bitwidth=3, val=1)
        counter.next <<= counter + one

        gate_graph = pyrtl.GateGraph()

        # Traverse the GateGraph backward, following ``args`` references, from
        # ``counter``. We should end up back at ``counter``.
        counter_gate = gate_graph.get_gate("counter")
        self.assertEqual(len(counter_gate.args), 1)

        # Implicit truncation from 4-bit sum to 3-bit register input.
        slice_gate = counter_gate.args[0]
        self.assertEqual(slice_gate.op, "s")
        self.assertEqual(len(slice_gate.args), 1)

        plus_gate = slice_gate.args[0]
        self.assertEqual(plus_gate.op, "+")
        self.assertEqual(len(plus_gate.args), 2)

        self.assertEqual(plus_gate.args[0], counter_gate)

    def test_memblock(self):
        mem = pyrtl.MemBlock(name="mem", bitwidth=8, addrwidth=2)

        write_addr = pyrtl.Input(name="write_addr", bitwidth=2)
        write_data = pyrtl.Input(name="write_data", bitwidth=8)
        write_enable = pyrtl.Input(name="write_enable", bitwidth=1)
        mem[write_addr] <<= pyrtl.MemBlock.EnabledWrite(
            data=write_data, enable=write_enable
        )

        read_addr = pyrtl.Input(name="read_addr", bitwidth=2)
        read_data = mem[read_addr]
        read_data.name = "read_data"

        gate_graph = pyrtl.GateGraph()

        read_addr_gate = gate_graph.get_gate("read_addr")
        read_gate = gate_graph.get_gate("read_data")
        self.assertEqual(read_gate.op, "m")
        self.assertEqual(read_gate.args, [read_addr_gate])
        self.assertEqual(read_gate.op_param, (mem.id, mem))
        self.assertEqual(read_gate.dest_bitwidth, 8)

        write_addr_gate = gate_graph.get_gate("write_addr")
        write_data_gate = gate_graph.get_gate("write_data")
        write_enable_gate = gate_graph.get_gate("write_enable")
        write_gate = write_data_gate.dest_fanout[0]
        self.assertEqual(write_gate.op, "@")
        self.assertEqual(read_gate.op_param, (mem.id, mem))
        self.assertEqual(
            write_gate.args, [write_addr_gate, write_data_gate, write_enable_gate]
        )
        self.assertEqual(write_gate.dest_name, None)
        self.assertEqual(write_gate.dest_bitwidth, None)
        self.assertEqual(write_gate.dest_fanout, [])


if __name__ == "__main__":
    unittest.main()
