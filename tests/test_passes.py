from __future__ import print_function
from __future__ import unicode_literals

import unittest
import pyrtl
import pyrtl.core
import pyrtl.wire
import pyrtl.passes
import io

from .helperfunctions import testmissing


class TestSynthesis(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.bitwidth = 3
        self.r = pyrtl.Register(bitwidth=self.bitwidth, name='r')

    def tearDown(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        # should all these tests still work post synthesis?
        # pyrtl.synthesize()
        # pyrtl.optimize()
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

    def test_minus_simulationx(self):
        self.r.next <<= self.r - pyrtl.Const(1, bitwidth=self.bitwidth)
        self.check_trace('r 07654321\n')

    def test_const_nobitwidth_simulation(self):
        self.r.next <<= self.r - pyrtl.Const(1)
        self.check_trace('r 07654321\n')


class TestOptimization(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def num_net_of_type(self, netOp, block):
        return len([net for net in block.logic if net[0] == netOp])

    def num_wire_of_type(self, wiretype, block):
        return len([wire for wire in block.wirevector_set if isinstance(wire, wiretype)])

    def test_wire_net_removal_1(self):
        inwire = pyrtl.Input(bitwidth=3)
        tempwire = pyrtl.WireVector()
        outwire = pyrtl.Output()
        tempwire <<= inwire
        outwire <<= tempwire

        pyrtl.synthesize()
        pyrtl.optimize()
        block = pyrtl.working_block(None)
        # should remove the middle wire but keep the input
        self.assertEqual(len(block.logic), 5)
        self.assertEqual(len(block.wirevector_set), 6)
        # # self.assertTrue(result.startswith("tmp3/3O <-- w -- tmp1/3I"))

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
        block = pyrtl.working_block(None)
        self.assertEqual(len(block.logic), 5)
        self.assertEqual(len(block.wirevector_set), 6)
        # # self.assertTrue(result.startswith("tmp7/3O <-- w -- tmp4/3I"))

    def test_const_folding_basic_one_var_op_1(self):
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()

        outwire <<= ~constwire
        pyrtl.synthesize()
        pyrtl.optimize()

        block = pyrtl.working_block(None)
        self.assertEqual(self.num_net_of_type('~', block), 0)
        self.assertEqual(self.num_net_of_type('w', block), 1)
        self.assertEqual(len(block.logic), 1)
        self.assertEqual(len(block.wirevector_set), 2)
        self.assertEqual(self.num_wire_of_type(pyrtl.wire.Const, block), 1)

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
        self.assertEqual(self.num_net_of_type('w', block), 1)
        self.assertEqual(len(block.logic), 1)
        self.assertEqual(len(block.wirevector_set), 2)
        self.assertEqual(self.num_wire_of_type(pyrtl.wire.Const, block), 1)
        self.assertEqual(self.num_wire_of_type(pyrtl.wire.Output, block), 1)

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
        self.assertEqual(self.num_net_of_type('w', block), 1)
        self.assertEqual(len(block.logic), 4)
        self.assertEqual(len(block.wirevector_set), 5)
        self.assertEqual(self.num_wire_of_type(pyrtl.wire.Const, block), 0)
        self.assertEqual(self.num_wire_of_type(pyrtl.wire.Output, block), 1)

    def test_const_folding_basic_two_var_op_1(self):
        inwire = pyrtl.Input(bitwidth=1)
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()

        outwire <<= inwire & constwire
        print()
        print(str(pyrtl.working_block()))
        pyrtl.synthesize()
        pyrtl.optimize()
        # should remove the or block and replace it with a
        # wire net (to separate the const from the output)
        block = pyrtl.working_block(None)
        self.assertEqual(self.num_net_of_type('&', block), 0)
        self.assertEqual(self.num_net_of_type('w', block), 1)
        print()
        print(str(pyrtl.working_block()))
        self.assertEqual(len(block.logic), 2)
        self.assertEqual(1,0)
        self.assertEqual(len(block.wirevector_set), 4)
        self.assertEqual(self.num_wire_of_type(pyrtl.wire.Const, block), 1)

    def test_const_folding_basic_two_var_op_2(self):
        inwire = pyrtl.Input(bitwidth=1)
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()

        outwire <<= inwire | constwire
        pyrtl.optimize()
        # should remove the and block and replace it with a
        # wire net (to separate the const from the output)
        block = pyrtl.working_block(None)
        self.assertEqual(self.num_net_of_type('|', block), 0)
        self.assertEqual(self.num_net_of_type('w', block), 1)
        self.assertEqual(len(block.logic), 1)
        self.assertEqual(len(block.wirevector_set), 2)
        self.assertEqual(self.num_wire_of_type(pyrtl.wire.Const, block), 0)

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
        self.assertEqual(self.num_net_of_type('|', block), 0)
        self.assertEqual(self.num_net_of_type('w', block), 1)
        self.assertEqual(len(block.logic), 1)
        self.assertEqual(len(block.wirevector_set), 2)
        self.assertEqual(self.num_wire_of_type(pyrtl.wire.Const, block), 1)


class TestSynthOptTiming(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_sanity_check(self):
        testmissing()

    def num_net_of_type(self, netOp, block):
        return len([net for net in block.logic if net[0] == netOp])

    def everything_t_procedure(self, timing_val=None, opt_timing_val=None):
        # if there is a nondefault timing val supplied, then it will check
        # to make sure that the timing matches
        # this is a subprocess to do the synth and timing
        block = pyrtl.working_block()
        timing_map = pyrtl.timing_analysis(block)
        timing_max_length = pyrtl.timing_max_length(timing_map)
        if timing_val is not None:
            self.assertEqual(timing_max_length, timing_val)
        critical_path = pyrtl.timing_critical_path(timing_map)

        pyrtl.synthesize()
        pyrtl.optimize()

        block = pyrtl.working_block()
        timing_map = pyrtl.timing_analysis(block)
        timing_max_length = pyrtl.timing_max_length(timing_map)
        if opt_timing_val is not None:
            self.assertEqual(timing_max_length, opt_timing_val)
        critical_path = pyrtl.timing_critical_path(timing_map)

        pyrtl.and_inverter_synth()
        pyrtl.optimize()

        block = pyrtl.working_block()
        timing_map = pyrtl.timing_analysis(block)
        timing_max_length = pyrtl.timing_max_length(timing_map)
        self.assertEqual(self.num_net_of_type('|', block), 0)
        self.assertEqual(self.num_net_of_type('^', block), 0)

        pyrtl.nand_synth()
        pyrtl.optimize()

        block = pyrtl.working_block()
        timing_map = pyrtl.timing_analysis(block)
        timing_max_length = pyrtl.timing_max_length(timing_map)
        block.sanity_check()
        self.assertEqual(self.num_net_of_type('|', block), 0)
        self.assertEqual(self.num_net_of_type('&', block), 0)
        self.assertEqual(self.num_net_of_type('^', block), 0)

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
        self.everything_t_procedure(3, 3)

    def test_timing_error(self):
        inwire, inwire2 = pyrtl.Input(bitwidth=1), pyrtl.Input(bitwidth=1)
        tempwire, tempwire2 = pyrtl.WireVector(1), pyrtl.WireVector(1)
        outwire = pyrtl.Output()

        tempwire <<= ~(inwire & tempwire2)
        tempwire2 <<= ~(inwire2 & tempwire)
        outwire <<= tempwire

        def doAllOps():
            pyrtl.synthesize()
            pyrtl.optimize()
            block = pyrtl.working_block()
            timing_map = pyrtl.timing_analysis(block)
            block_max_time = pyrtl.timing_max_length(timing_map)

        self.assertRaises(pyrtl.PyrtlError, doAllOps)

    def test_wirevector_1(self):
        inwire = pyrtl.Input(bitwidth=1)
        tempwire0, tempwire1 = pyrtl.WireVector(bitwidth=1), pyrtl.WireVector(bitwidth=1)
        tempwire2 = pyrtl.WireVector(bitwidth=1)
        outwire = pyrtl.Output()

        tempwire0 <<= inwire
        tempwire1 <<= tempwire0
        tempwire2 <<= tempwire1
        outwire <<= ~tempwire2
        self.everything_t_procedure(1, 1)
        block = pyrtl.working_block()
        self.assertEqual(len(block.logic), 3)

    def test_combo_1(self):
        inwire, inwire2 = pyrtl.Input(bitwidth=1), pyrtl.Input(bitwidth=1)
        tempwire, tempwire2 = pyrtl.WireVector(), pyrtl.WireVector()
        inwire3 = pyrtl.Input(bitwidth=1)
        outwire = pyrtl.Output()

        tempwire <<= inwire | inwire2
        tempwire2 <<= ~tempwire
        outwire <<= tempwire2 & inwire3
        self.everything_t_procedure(3, 3)

    def test_adder(self):
        inwire1, inwire2 = pyrtl.Input(bitwidth=3), pyrtl.Input(bitwidth=3)
        outwire = pyrtl.Output(bitwidth=4)

        outwire <<= inwire1 + inwire2
        self.everything_t_procedure()

    def test_all_mem_1(self):
        readAdd1, readAdd2 = pyrtl.Input(bitwidth=3), pyrtl.Input(bitwidth=3)
        writeAdd1, writeAdd2 = pyrtl.Input(bitwidth=3), pyrtl.Input(bitwidth=3)
        readData1, readData2 = pyrtl.Input(bitwidth=3), pyrtl.Input(bitwidth=3)

        dataOut = pyrtl.Output(bitwidth=3)

        memory = pyrtl.MemBlock(3, 3, asynchronous=True)

        memory[readAdd1 & readAdd2] <<= readData1 ^ readData2
        dataOut <<= memory[writeAdd1 | writeAdd2]
        self.everything_t_procedure()


if __name__ == "__main__":
    unittest.main()
