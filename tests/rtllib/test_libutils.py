import unittest

import pyrtl
import pyrtl.rtllib.testingutils as utils
from pyrtl.rtllib import libutils


class TestPartitionWire(unittest.TestCase):

    def test_successful_partition(self):
        w = pyrtl.WireVector(24)
        partitioned_w = libutils.partition_wire(w, 4)
        self.assertEqual(len(partitioned_w), 6)
        for wire in partitioned_w:
            self.assertIsInstance(wire, pyrtl.WireVector)

    def test_failing_partition(self):
        w = pyrtl.WireVector(14)
        with self.assertRaises(pyrtl.PyrtlError):
            partitioned_w = libutils.partition_wire(w, 4)

    def test_partition_sim(self):
        pyrtl.reset_working_block()
        wires, vals = utils.make_inputs_and_values(exact_bitwidth=32, num_wires=1)
        out_wires = [pyrtl.Output(8, 'o' + str(i)) for i in range(4)]
        partitioned_w = libutils.partition_wire(wires[0], 8)
        for p_wire, o_wire in zip(partitioned_w, out_wires):
            o_wire <<= p_wire

        out_vals = utils.sim_and_ret_outws(wires, vals)
        partitioned_vals = [[(val >> i) & 0xff for i in (0, 8, 16, 24)] for val in vals[0]]
        true_vals = tuple(zip(*partitioned_vals))
        for index, wire in enumerate(out_wires):
            self.assertEqual(tuple(out_vals[wire.name]), true_vals[index])


class TestStringConversion(unittest.TestCase):

    def test_simple_conversion(self):
        self.assertEqual([0xa7, 0x23], libutils.str_to_int_array("a7 23"))

    def test_binary_conversion(self):
        result = libutils.str_to_int_array("0100 0110 010", base=2)
        self.assertEqual(result, [4, 6, 2])

    def test_empty(self):
        result = libutils.str_to_int_array("")
        self.assertEqual(result, [])

    def test_multiline(self):
        text = """
        374 1c
        a
        34 76"""
        result = libutils.str_to_int_array(text)
        self.assertEqual([0x374, 0x1c, 0xa, 0x34, 0x76], result)

    def test_invalid_str(self):
        with self.assertRaises(ValueError):
            libutils.str_to_int_array("hello")

    def test_invalid_bin_str(self):
        with self.assertRaises(ValueError):
            libutils.str_to_int_array("0313", 2)

    def test_no_override(self):
        with self.assertRaises(ValueError):
            libutils.str_to_int_array("0x0313", 2)


class TestTwosComp(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.in1, self.in2 = (pyrtl.Input(8, "in" + str(i)) for i in range(1, 3))
        self.out = pyrtl.Output(9, "out")

    def test_inverse_functionality(self):
        for i in range(20):
            self.assertEqual(i * 3, libutils.rev_twos_comp_repr(
                libutils.twos_comp_repr(i * 3, 16), 16))

    def test_low_bw_error(self):
        with self.assertRaises(pyrtl.PyrtlError):
            libutils.twos_comp_repr(-40, 6)
        with self.assertRaises(pyrtl.PyrtlError):
            libutils.rev_twos_comp_repr(88, 6)
        with self.assertRaises(pyrtl.PyrtlError):
            libutils.rev_twos_comp_repr(8, 4)

    def test_twos_comp_sim(self):
        self.out <<= self.in1 + self.in2
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(10):
            sim.step({
                'in1': i,
                'in2': libutils.twos_comp_repr(-2 * i, 8)
            })
            self.assertEqual(-i, libutils.rev_twos_comp_repr(sim.inspect('out'), 8))
