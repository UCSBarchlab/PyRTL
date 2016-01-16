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
        wires, vals = utils.make_wires_and_values(exact_bitwidth=32, num_wires=1)
        out_wires = [pyrtl.Output(8, 'o' + str(i)) for i in range(4)]
        partitioned_w = libutils.partition_wire(wires[0], 8)
        for p_wire, o_wire in zip(partitioned_w, out_wires):
            o_wire <<= p_wire

        out_vals = utils.sim_and_ret_outws(wires, vals)
        partitioned_vals = [[(val >> i) & 0xff for i in (0, 8, 16, 24)] for val in vals[0]]
        true_vals = tuple(zip(*partitioned_vals))
        for index, wire in enumerate(out_wires):
            self.assertEqual(tuple(out_vals[wire]), true_vals[index])


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


class TestDemux(unittest.TestCase):

    def setUp(self):
        pyrtl.reset_working_block()

    def test_simple_demux(self):
        in_w, in_vals = utils.generate_in_wire_and_values(2)
        outs = (pyrtl.Output(name="output_" + str(i)) for i in range(4))
        demux_outs = libutils.demux(in_w)
        for out_w, demux_out in zip(outs, demux_outs):
            out_w <<= demux_out
        traces = utils.sim_and_ret_outws((in_w,), (in_vals,))

        for cycle in range(20):
            for i, out_wire in enumerate(outs):
                self.assertEqual(in_vals[i] == i, traces[out_wire][cycle])

    def test_demux_2(self):
        in_w, in_vals = utils.generate_in_wire_and_values(1)
        outs = (pyrtl.Output(name="output_" + str(i)) for i in range(2))
        demux_outs = libutils._demux_2(in_w)
        for out_w, demux_out in zip(outs, demux_outs):
            out_w <<= demux_out
        traces = utils.sim_and_ret_outws((in_w,), (in_vals,))

        for cycle in range(20):
            for i, out_wire in enumerate(outs):
                self.assertEqual(in_vals[i] == i, traces[out_wire][cycle])

    def test_large_demux(self):
        in_w, in_vals = utils.generate_in_wire_and_values(5)
        outs = (pyrtl.Output(name="output_" + str(i)) for i in range(32))
        demux_outs = libutils.demux(in_w)
        for out_w, demux_out in zip(outs, demux_outs):
            out_w <<= demux_out
        traces = utils.sim_and_ret_outws((in_w,), (in_vals,))

        for cycle in range(20):
            for i, out_wire in enumerate(outs):
                self.assertEqual(in_vals[i] == i, traces[out_wire][cycle])
