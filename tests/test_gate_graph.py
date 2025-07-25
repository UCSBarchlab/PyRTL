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
            sorted(gate.name for gate in gate_graph),
            ["a", "ab", "abc", "b", "c"],
        )

        self.assertEqual(
            sorted([gate.name for gate in gate_graph.gates]),
            ["a", "ab", "abc", "b", "c"],
        )

        self.assertEqual(
            sorted([gate.name for gate in gate_graph.sources]), ["a", "b", "c"]
        )

        self.assertEqual(sorted([gate.name for gate in gate_graph.sinks]), ["abc"])

        gate_ab = gate_graph.get_gate("ab")
        self.assertEqual(gate_ab.name, "ab")
        self.assertEqual(gate_ab.op, "+")

        gate_abc = gate_graph.get_gate("abc")
        self.assertEqual(gate_abc.name, "abc")
        self.assertEqual(gate_abc.op, "-")

    def test_get_gate(self):
        _ = pyrtl.Input(name="a", bitwidth=4)

        gate_graph = pyrtl.GateGraph()
        a_gate = gate_graph.get_gate("a")
        self.assertEqual(a_gate.name, "a")

        self.assertEqual(gate_graph.get_gate("q"), None)

    def test_select_gate(self):
        a = pyrtl.Input(name="a", bitwidth=4)
        b = pyrtl.Input(name="b", bitwidth=4)
        s = pyrtl.Input(name="s", bitwidth=1)

        output = pyrtl.select(s, a, b)
        output.name = "output"

        gate_graph = pyrtl.GateGraph()
        select_gate = gate_graph.get_gate("output")
        self.assertEqual(select_gate.op, "x")
        self.assertEqual(select_gate.op_param, None)
        a_gate = gate_graph.get_gate("a")
        b_gate = gate_graph.get_gate("b")
        s_gate = gate_graph.get_gate("s")
        self.assertEqual(select_gate.args, [s_gate, b_gate, a_gate])
        self.assertEqual(select_gate.name, "output")
        self.assertEqual(select_gate.bitwidth, 4)
        self.assertEqual(select_gate.dests, [])
        self.assertEqual(str(select_gate), "output/4 = s/1 ? a/4 : b/4")

    def test_gate_attrs(self):
        a = pyrtl.Input(name="a", bitwidth=4)
        b = pyrtl.Const(name="b", bitwidth=2, val=1)
        bit_slice = a[2:4]
        bit_slice.name = "bit_slice"
        ab = bit_slice + b
        ab.name = "ab"

        output = pyrtl.Output(name="output", bitwidth=3)
        bb = b + b
        bb.name = "bb"
        output <<= bb

        gate_graph = pyrtl.GateGraph()

        a_gate = gate_graph.get_gate("a")
        self.assertEqual(a_gate.op, "I")
        self.assertEqual(a_gate.args, [])

        b_gate = gate_graph.get_gate("b")
        self.assertEqual(b_gate.op, "C")
        self.assertEqual(b_gate.op_param, (1,))

        self.assertEqual(str(b_gate), "b/2 = Const(1)")

        bit_slice_gate = gate_graph.get_gate("bit_slice")
        self.assertEqual(bit_slice_gate.op, "s")

        self.assertEqual(bit_slice_gate.op_param, (2, 3))

        self.assertEqual(bit_slice_gate.args, [a_gate])

        self.assertEqual(bit_slice_gate.name, "bit_slice")
        self.assertEqual(bit_slice_gate.bitwidth, 2)

        self.assertEqual(str(bit_slice_gate), "bit_slice/2 = slice(a/4) [sel=(2, 3)]")

        ab_gate = gate_graph.get_gate("ab")
        self.assertEqual(ab_gate.op, "+")

        self.assertEqual(ab_gate.args, [bit_slice_gate, b_gate])

        self.assertEqual(ab_gate.name, "ab")
        self.assertEqual(ab_gate.bitwidth, 3)
        self.assertFalse(ab_gate.is_output)

        output_gate = gate_graph.get_gate("output")
        self.assertEqual(output_gate.op, "w")
        self.assertTrue(output_gate.is_output)
        self.assertEqual(str(output_gate), "output/3 [Output] = bb/3")

        self.assertEqual(len(output_gate.args), 1)
        output_add_gate = output_gate.args[0]

        self.assertEqual(output_add_gate.args, [b_gate, b_gate])

        self.assertEqual(len(b_gate.dests), 3)
        num_ab_gates = 0
        num_output_add_gates = 0
        for dest_gate in b_gate.dests:
            if dest_gate is ab_gate:
                num_ab_gates += 1
            elif dest_gate is output_add_gate:
                num_output_add_gates += 1
        self.assertEqual(num_ab_gates, 1)
        self.assertEqual(num_output_add_gates, 2)

    def test_register_gate_forward(self):
        counter = pyrtl.Register(name="counter", bitwidth=3)
        one = pyrtl.Const(name="one", bitwidth=3, val=1)
        truncated = (counter + one).truncate(3)
        truncated.name = "truncated"
        counter.next <<= truncated

        gate_graph = pyrtl.GateGraph()

        # Traverse the ``GateGraph`` forward, following ``dests`` references, from
        # ``counter``. We should end up back at ``counter``.
        counter_gate = gate_graph.get_gate("counter")
        self.assertEqual(len(counter_gate.dests), 1)
        self.assertEqual(
            str(counter_gate), "counter/3 = reg(truncated/3) [reset_value=0]"
        )

        plus_gate = counter_gate.dests[0]
        self.assertEqual(plus_gate.op, "+")
        self.assertEqual(len(plus_gate.dests), 1)

        slice_gate = plus_gate.dests[0]
        self.assertEqual(slice_gate.op, "s")
        self.assertEqual(len(slice_gate.dests), 1)

        self.assertEqual(slice_gate.dests[0], counter_gate)

    def test_register_gate_backward(self):
        counter = pyrtl.Register(name="counter", bitwidth=3, reset_value=2)
        one = pyrtl.Const(name="one", bitwidth=3, val=1)
        counter.next <<= counter + one

        gate_graph = pyrtl.GateGraph()

        # Traverse the ``GateGraph`` backward, following ``args`` references, from
        # ``counter``. We should end up back at ``counter``.
        counter_gate = gate_graph.get_gate("counter")
        self.assertEqual(len(counter_gate.args), 1)
        self.assertEqual(counter_gate.op_param, (2,))

        # Implicit truncation from 4-bit sum to 3-bit register input.
        slice_gate = counter_gate.args[0]
        self.assertEqual(slice_gate.op, "s")
        self.assertEqual(len(slice_gate.args), 1)

        plus_gate = slice_gate.args[0]
        self.assertEqual(plus_gate.op, "+")
        self.assertEqual(len(plus_gate.args), 2)

        self.assertEqual(plus_gate.args[0], counter_gate)

    def test_register_self_loop(self):
        """Test a register that sets its next value directly from itself.

        This is an unusual case that creates a self-loop in the ``GateGraph``.
        """
        r = pyrtl.Register(name="r", bitwidth=1)
        r.next <<= r

        gate_graph = pyrtl.GateGraph()
        r_gate = gate_graph.get_gate("r")
        self.assertEqual(r_gate.args[0], r_gate)
        self.assertEqual(r_gate.dests[0], r_gate)
        self.assertEqual(str(r_gate), "r/1 = reg(r/1) [reset_value=0]")

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
        self.assertEqual(read_gate.bitwidth, 8)
        self.assertEqual(
            str(read_gate),
            f"read_data/8 = read(addr=read_addr/2) [memid={mem.id} mem=mem]",
        )

        write_addr_gate = gate_graph.get_gate("write_addr")
        write_data_gate = gate_graph.get_gate("write_data")
        write_enable_gate = gate_graph.get_gate("write_enable")
        write_gate = write_data_gate.dests[0]
        self.assertEqual(write_gate.op, "@")
        self.assertEqual(read_gate.op_param, (mem.id, mem))
        self.assertEqual(
            write_gate.args, [write_addr_gate, write_data_gate, write_enable_gate]
        )
        self.assertEqual(write_gate.name, None)
        self.assertEqual(write_gate.bitwidth, None)
        self.assertEqual(write_gate.dests, [])
        self.assertEqual(
            str(write_gate),
            "write(addr=write_addr/2, data=write_data/8, enable=write_enable/1) "
            f"[memid={mem.id} mem=mem]",
        )

    def test_gate_sets(self):
        a = pyrtl.Input(name="a", bitwidth=1)
        b = pyrtl.Input(name="b", bitwidth=1)

        c = pyrtl.Const(name="c", bitwidth=1, val=0)
        d = pyrtl.Const(name="d", bitwidth=1, val=1)

        x = pyrtl.Output(name="x", bitwidth=1)
        y = pyrtl.Output(name="y", bitwidth=1)

        r = pyrtl.Register(name="r", bitwidth=1)
        s = pyrtl.Register(name="s", bitwidth=1)

        mem = pyrtl.MemBlock(name="mem", bitwidth=1, addrwidth=1)

        x <<= a + c

        r.next <<= r + c
        s.next <<= r + d

        mem[a] <<= pyrtl.MemBlock.EnabledWrite(data=c, enable=d)
        read = mem[b]
        read.name = "read"
        y <<= read + d

        gate_graph = pyrtl.GateGraph()

        self.assertEqual(sorted(gate.name for gate in gate_graph.inputs), ["a", "b"])
        self.assertEqual(sorted(gate.name for gate in gate_graph.consts), ["c", "d"])
        self.assertEqual(sorted(gate.name for gate in gate_graph.outputs), ["x", "y"])
        self.assertEqual(sorted(gate.name for gate in gate_graph.registers), ["r", "s"])
        self.assertEqual(sorted(gate.name for gate in gate_graph.mem_reads), ["read"])
        mem_writes = gate_graph.mem_writes
        # Check the MemBlock write.
        self.assertEqual(len(mem_writes), 1)
        write_gate = next(iter(mem_writes))
        self.assertTrue(write_gate is not None)
        self.assertEqual(write_gate.op, "@")
        # MemBlock write has no name.
        self.assertEqual(write_gate.name, None)

        self.assertEqual(
            sorted(gate.name for gate in gate_graph.sources),
            ["a", "b", "c", "d", "r", "s"],
        )
        sinks = set(gate_graph.sinks)
        self.assertEqual(
            sorted(str(gate.name) for gate in sinks), ["None", "r", "s", "x", "y"]
        )


if __name__ == "__main__":
    unittest.main()
