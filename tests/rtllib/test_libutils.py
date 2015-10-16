import unittest
import pyrtl
from pyrtl.rtllib import libutils
import random
import t_utils as utils


class TestMuxes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        random.seed(8492049)

    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_simple_mux_1(self):
        self.mux_t_subprocess(4, 18)

    def test_simple_mux_2(self):
        self.mux_t_subprocess(6, 32)

    def test_simple_mux_3(self):
        self.mux_t_subprocess(8, 64)

    def mux_t_subprocess(self, addr_width, val_width):
        mux_ins, vals = utils.make_consts(num_wires=2**addr_width, exact_bitwidth=val_width)
        control, testctrl = utils.generate_in_wire_and_values(addr_width, 40, "mux_ctrl")

        out = pyrtl.Output(val_width, "mux_out")
        out <<= libutils.basic_n_bit_mux(control, mux_ins)

        true_result = [vals[i] for i in testctrl]
        mux_result = utils.sim_and_ret_out(out, (control,), (testctrl,))
        self.assertEqual(mux_result, true_result)


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

