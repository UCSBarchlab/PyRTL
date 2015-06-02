import unittest
import pyrtl
import rtllib
from rtllib import libutils
import random

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
        vals = [random.randint(1, 2**val_width) for _ in range(2**addr_width)]
        mux_ins = [pyrtl.Const(i) for i in vals]
        control = pyrtl.Input(addr_width, "mux_ctrl")
        out = pyrtl.Output(val_width, "mux_out")

        out <<= libutils.basic_n_bit_mux(control, mux_ins)

        testctrl = [random.randint(0, 2**addr_width - 1) for _ in range(40)]

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for ctrl_val in testctrl:
            sim.step({control: ctrl_val})

        true_result = [vals[i] for i in testctrl]
        mux_result = sim_trace.trace[out]
        sim_trace.render_trace(symbol_len=12)
        assert (mux_result == true_result)
        print "test passed!"
