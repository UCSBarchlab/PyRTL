import unittest
import random

import pyrtl
import pyrtl.rtllib.testingutils as utils

from operator import add
from pyrtl.rtllib import libutils
from pyrtl.rtllib.adders import kogge_stone


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


class TestTwosComp(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.in1, self.in2 = (pyrtl.Input(8, "in"+str(i)) for i in range(1, 3))
        self.out = pyrtl.Output(9, "out")

    def test_inverse_functionality(self):
        for i in range(20):
            self.assertEquals(i*3, libutils.rev_twos_comp_repr(
                libutils.twos_comp_repr(i*3, 16), 16))

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
                'in2': libutils.twos_comp_repr(-2*i, 8)
            })
            self.assertEquals(-i, libutils.rev_twos_comp_repr(sim.inspect('out'), 8))


class TestAddOverflowDetect(unittest.TestCase):
    def setUp(self):
        random.seed(123456789)
        self.in1_vals = [a if a != 8 else 0 for a in [random.randint(0, 15) for i in range(30)]]
        self.in2_vals = [a if a != 8 else 0 for a in [random.randint(0, 15) for i in range(30)]]

        pyrtl.reset_working_block()
        self.in1, self.in2 = (pyrtl.Input(4, 'in%d' % i) for i in range(1, 3))
        self.res_s, self.res_ns = (pyrtl.Output(5, 'res_%s' % s) for s in ('s', 'ns'))
        self.overflow_s, self.overflow_ns = (pyrtl.Output(1, 'overflow_%s' % s) for s in ('s', 'ns'))

        # test decorator functionality with parameter
        @libutils.detect_add_overflow(signed=True)
        def checked_add_signed(in1, in2):
            return kogge_stone(in1, in2)

        _res_s, _ov_s = checked_add_signed(self.in1, self.in2)
        _res_ns, _ov_ns = libutils.detect_add_overflow(add, signed=False)(self.in1, self.in2)
        self.res_s <<= _res_s
        self.overflow_s <<= _ov_s
        self.res_ns <<= _res_ns
        self.overflow_ns <<= _ov_ns

        self.sim_trace = pyrtl.SimulationTrace()
        self.sim = pyrtl.Simulation(tracer=self.sim_trace)

    def test_overflow(self):
        for in1, in2 in zip(self.in1_vals, self.in2_vals):
            self.sim.step({self.in1: in1, self.in2: in2})
            self.assertEqual(self.sim.inspect(self.overflow_s), int(libutils.rev_twos_comp_repr(in1, 4) +
                                                                    libutils.rev_twos_comp_repr(in2, 4)
                                                                    not in range(-7, 8)))
            self.assertEqual(self.sim.inspect(self.overflow_ns), int(in1 + in2 not in range(0, 32)))
