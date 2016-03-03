from __future__ import print_function, unicode_literals, absolute_import
from .test_transform import NetWireNumTestCases
from pyrtl.wire import Const,  Output
from pyrtl.analysis import estimate

import unittest
import pyrtl
import io


class TestSynthesis(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.r = pyrtl.Register(bitwidth=self.bitwidth)
        self.output = pyrtl.Output(bitwidth=self.bitwidth, name='r')
        self.output <<= self.r

    def check_trace(self, correct_string):
        pyrtl.synthesize()
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output)
        self.assertEqual(output.getvalue(), correct_string)

    def test_not_simulation(self):
        self.r.next <<= ~ self.r
        self.check_trace('r 07070707\n')

    def test_and_simulation(self):
        self.r.next <<= (~ self.r) & pyrtl.Const(6, bitwidth=self.bitwidth)
        self.check_trace('r 06060606\n')

    def test_or_simulation(self):
        result = self.r | pyrtl.Const(4, bitwidth=self.bitwidth)
        self.r.next <<= result
        self.assertEqual(len(result), self.bitwidth)
        self.check_trace('r 04444444\n')

    def test_xor_simulation(self):
        self.r.next <<= self.r ^ pyrtl.Const(4, bitwidth=self.bitwidth)
        self.check_trace('r 04040404\n')

    def test_plus_simulation(self):
        self.r.next <<= self.r + pyrtl.Const(2, bitwidth=self.bitwidth)
        self.check_trace('r 02460246\n')

    def test_minus_simulation(self):
        self.r.next <<= self.r - pyrtl.Const(1, bitwidth=self.bitwidth)
        self.check_trace('r 07654321\n')

    def test_minus_simulation2(self):
        self.r.next <<= self.r - pyrtl.Const(3, bitwidth=self.bitwidth)
        self.check_trace('r 05274163\n')

    def test_const_nobitwidth_simulation(self):
        self.r.next <<= self.r - pyrtl.Const(1)
        self.check_trace('r 07654321\n')


class TestOptimization(NetWireNumTestCases):

    def test_wire_net_removal_1(self):
        inwire = pyrtl.Input(bitwidth=3)
        tempwire = pyrtl.WireVector()
        outwire = pyrtl.Output()
        tempwire <<= inwire
        outwire <<= tempwire

        pyrtl.synthesize()
        pyrtl.optimize()
        block = pyrtl.working_block()
        # should remove the middle wire but keep the input
        self.assert_num_net(5, block)
        self.assert_num_wires(6, block)

    def test_wire_net_removal_2(self):
        inwire = pyrtl.Input(bitwidth=3)
        tempwire = pyrtl.WireVector()
        tempwire2 = pyrtl.WireVector()
        outwire = pyrtl.Output()
        tempwire <<= inwire
        tempwire2 <<= tempwire
        outwire <<= tempwire
        pyrtl.synthesize()
        pyrtl.optimize()
        # should remove the middle wires but keep the input
        block = pyrtl.working_block()
        self.assert_num_net(5, block)
        self.assert_num_wires(6, block)

    def test_const_folding_basic_one_var_op_1(self):
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()

        outwire <<= ~constwire
        pyrtl.synthesize()
        pyrtl.optimize()

        block = pyrtl.working_block()
        self.num_net_of_type('~', 0, block)
        self.num_net_of_type('w', 1, block)
        self.assertEqual(len(block.logic), 1)
        self.assertEqual(len(block.wirevector_set), 2)
        self.num_wire_of_type(Const, 1, block)

    def test_const_folding_adv_one_var_op_1(self):
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()
        tempwire = pyrtl.WireVector()
        reg = pyrtl.Register(1, 'test register')

        tempwire <<= ~constwire
        reg.next <<= tempwire
        outwire <<= reg
        pyrtl.synthesize()
        pyrtl.optimize()

        block = pyrtl.working_block(None)
        self.num_net_of_type('w', 1, block)
        self.assert_num_net(1, block)
        self.assert_num_wires(2, block)
        self.num_wire_of_type(Const, 1, block)
        self.num_wire_of_type(Output, 1, block)

    def test_const_folding_adv_one_var_op_2(self):
        # this one tests to see that an input wirevector is properly preserved

        inwire = pyrtl.Input(bitwidth=1)
        outwire = pyrtl.Output()
        tempwire = pyrtl.WireVector()
        reg = pyrtl.Register(1, 'test register')

        tempwire <<= ~inwire
        reg.next <<= tempwire
        outwire <<= reg
        pyrtl.synthesize()
        pyrtl.optimize()
        # should remove the and block and replace it with a
        # wire net (to separate the input from the output)
        block = pyrtl.working_block(None)

        # Note: the current implementation still sticks a wire net between
        # a register 'nextsetter' wire and the output wire
        self.num_net_of_type('w', 1, block)
        self.assert_num_net(4, block)
        self.assert_num_wires(5, block)
        self.num_wire_of_type(Const, 0, block)
        self.num_wire_of_type(Output, 1, block)

    def test_const_folding_basic_two_var_op_1(self):
        inwire = pyrtl.Input(bitwidth=1)
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()

        outwire <<= inwire & constwire
        pyrtl.synthesize()
        pyrtl.optimize()
        # should remove the or block and replace it with a
        # wire net (to separate the const from the output)
        block = pyrtl.working_block(None)
        self.num_net_of_type('&', 0, block)
        self.num_net_of_type('w', 1, block)
        self.assert_num_net(2, block)
        self.assert_num_wires(4, block)
        self.num_wire_of_type(Const, 1, block)

    def test_const_folding_basic_two_var_op_2(self):
        inwire = pyrtl.Input(bitwidth=1)
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()

        outwire <<= inwire | constwire
        pyrtl.optimize()
        # should remove the and block and replace it with a
        # wire net (to separate the const from the output)
        block = pyrtl.working_block(None)
        self.num_net_of_type('|', 0, block)
        self.num_net_of_type('w', 1, block)
        self.assert_num_net(1, block)
        self.assert_num_wires(2, block)
        self.num_wire_of_type(Const, 0, block)

    def test_const_folding_basic_two_var_op_3(self):
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()

        # playing with edge cases
        outwire <<= constwire ^ constwire
        pyrtl.synthesize()
        pyrtl.optimize()
        # should remove the and block and replace it with a
        # wirevector (to separate the input from the output)
        block = pyrtl.working_block(None)
        self.num_net_of_type('|', 0, block)
        self.num_net_of_type('w', 1, block)
        self.assert_num_net(1, block)
        self.assert_num_wires(2, block)
        self.num_wire_of_type(Const, 1, block)


class TestSynthOptTiming(NetWireNumTestCases):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_sanity_check(self):
        pass

    def everything_t_procedure(self, timing_val=None, opt_timing_val=None):
        # if there is a nondefault timing val supplied, then it will check
        # to make sure that the timing matches
        # this is a subprocess to do the synth and timing
        block = pyrtl.working_block()
        timing_map = estimate.timing_analysis(block)
        timing_max_length = estimate.timing_max_length(timing_map)
        if timing_val is not None:
            self.assertEqual(timing_max_length, timing_val)
        critical_path = estimate.timing_critical_path(timing_map)

        pyrtl.synthesize()
        pyrtl.optimize()

        block = pyrtl.working_block()
        timing_map = estimate.timing_analysis(block)
        timing_max_length = estimate.timing_max_length(timing_map)
        if opt_timing_val is not None:
            self.assertEqual(timing_max_length, opt_timing_val)
        critical_path = estimate.timing_critical_path(timing_map)

        pyrtl.and_inverter_synth()
        pyrtl.optimize()

        block = pyrtl.working_block()
        timing_map = estimate.timing_analysis(block)
        timing_max_length = estimate.timing_max_length(timing_map)
        self.num_net_of_type('|', 0, block)
        self.num_net_of_type('^', 0, block)

        pyrtl.nand_synth()
        pyrtl.optimize()

        block = pyrtl.working_block()
        timing_map = estimate.timing_analysis(block)
        timing_max_length = estimate.timing_max_length(timing_map)
        block.sanity_check()
        self.num_net_of_type('|', 0, block)
        self.num_net_of_type('^', 0, block)
        self.num_net_of_type('&', 0, block)

    def test_const_folding_complex_1(self):
        output = pyrtl.Output(bitwidth=3, name='output')
        counter = pyrtl.Register(bitwidth=3, name='counter')
        counter.next <<= counter + 1
        output <<= counter

        # just to check that something like this will run properly
        self.everything_t_procedure()

    def test_timing_basic_2(self):
        inwire, inwire2 = pyrtl.Input(bitwidth=1), pyrtl.Input(bitwidth=1)
        inwire3 = pyrtl.Input(bitwidth=1)
        tempwire, tempwire2 = pyrtl.WireVector(), pyrtl.WireVector()
        outwire = pyrtl.Output()

        tempwire <<= inwire | inwire2
        tempwire2 <<= ~tempwire
        outwire <<= tempwire2 & inwire3
        self.everything_t_procedure(252.3, 252.3)

    def test_timing_error(self):
        inwire, inwire2 = pyrtl.Input(bitwidth=1), pyrtl.Input(bitwidth=1)
        tempwire, tempwire2 = pyrtl.WireVector(1), pyrtl.WireVector(1)
        outwire = pyrtl.Output()

        tempwire <<= ~(inwire & tempwire2)
        tempwire2 <<= ~(inwire2 & tempwire)
        outwire <<= tempwire

        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.synthesize()
            pyrtl.optimize()
            block = pyrtl.working_block()
            timing_map = estimate.timing_analysis(block)
            block_max_time = estimate.timing_max_length(timing_map)

    def test_wirevector_1(self):
        inwire = pyrtl.Input(bitwidth=1)
        tempwire0, tempwire1 = pyrtl.WireVector(bitwidth=1), pyrtl.WireVector(bitwidth=1)
        tempwire2 = pyrtl.WireVector(bitwidth=1)
        outwire = pyrtl.Output()

        tempwire0 <<= inwire
        tempwire1 <<= tempwire0
        tempwire2 <<= tempwire1
        outwire <<= ~tempwire2
        self.everything_t_procedure(48.5, 48.5)
        block = pyrtl.working_block()
        self.assert_num_net(3, block)

    def test_combo_1(self):
        inwire, inwire2 = pyrtl.Input(bitwidth=1), pyrtl.Input(bitwidth=1)
        tempwire, tempwire2 = pyrtl.WireVector(), pyrtl.WireVector()
        inwire3 = pyrtl.Input(bitwidth=1)
        outwire = pyrtl.Output()

        tempwire <<= inwire | inwire2
        tempwire2 <<= ~tempwire
        outwire <<= tempwire2 & inwire3
        self.everything_t_procedure(252.3, 252.3)

    def test_adder(self):
        inwire1, inwire2 = pyrtl.Input(bitwidth=3), pyrtl.Input(bitwidth=3)
        outwire = pyrtl.Output(bitwidth=4)

        outwire <<= inwire1 + inwire2
        self.everything_t_procedure()

    def test_all_mem_1(self):
        readAdd1, readAdd2, writeAdd1, writeAdd2, readData1, readData2 = \
            (pyrtl.Input(bitwidth=3) for i in range(6))

        dataOut = pyrtl.Output(bitwidth=3)

        memory = pyrtl.MemBlock(3, 3, asynchronous=True)

        memory[readAdd1 & readAdd2] <<= readData1 ^ readData2
        dataOut <<= memory[writeAdd1 | writeAdd2]
        self.everything_t_procedure()


if __name__ == "__main__":
    unittest.main()
