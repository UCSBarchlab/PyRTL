import unittest
import pyrtl
import pyrtl.core
import pyrtl.wire
import pyrtl.passes

from helperfunctions import testmissing


class TestPasses(unittest.TestCase):
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
        self.assertTrue(len(block.logic) == 3)
        self.assertTrue(len(block.wirevector_set) == 6)
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
        self.assertTrue(len(block.logic) == 3)
        self.assertTrue(len(block.wirevector_set) == 6)
        # # self.assertTrue(result.startswith("tmp7/3O <-- w -- tmp4/3I"))

    def test_const_folding_basic_one_var_op_1(self):
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()

        outwire <<= ~constwire
        pyrtl.synthesize()
        pyrtl.optimize()

        block = pyrtl.working_block(None)
        self.assertTrue(self.num_net_of_type('~', block) == 0)
        self.assertTrue(self.num_net_of_type('w', block) == 1)
        self.assertTrue(len(block.logic) == 1)
        self.assertTrue(len(block.wirevector_set) == 2)
        self.assertTrue(self.num_wire_of_type(pyrtl.wire.Const, block) == 1)

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
        self.assertTrue(self.num_net_of_type('w', block) == 1)
        self.assertTrue(len(block.logic) == 1)
        self.assertTrue(len(block.wirevector_set) == 2)
        self.assertTrue(self.num_wire_of_type(pyrtl.wire.Const, block) == 1)
        self.assertTrue(self.num_wire_of_type(pyrtl.wire.Output, block) == 1)

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
        self.assertTrue(self.num_net_of_type('w', block) == 1)
        self.assertTrue(len(block.logic) == 3)
        self.assertTrue(len(block.wirevector_set) == 4)
        self.assertTrue(self.num_wire_of_type(pyrtl.wire.Const, block) == 0)
        self.assertTrue(self.num_wire_of_type(pyrtl.wire.Output, block) == 1)

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
        self.assertTrue(self.num_net_of_type('&', block) == 0)
        self.assertTrue(self.num_net_of_type('w', block) == 1)
        self.assertTrue(len(block.logic) == 1)
        self.assertTrue(len(block.wirevector_set) == 2)
        self.assertTrue(self.num_wire_of_type(pyrtl.wire.Const, block) == 1)

    def test_const_folding_basic_two_var_op_2(self):
        inwire = pyrtl.Input(bitwidth=1)
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()

        outwire <<= inwire | constwire
        pyrtl.optimize()
        # should remove the and block and replace it with a
        # wire net (to separate the const from the output)
        block = pyrtl.working_block(None)
        self.assertTrue(self.num_net_of_type('|', block) == 0)
        self.assertTrue(self.num_net_of_type('w', block) == 1)
        self.assertTrue(len(block.logic) == 1)
        self.assertTrue(len(block.wirevector_set) == 2)
        self.assertTrue(self.num_wire_of_type(pyrtl.wire.Const, block) == 0)

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
        self.assertTrue(self.num_net_of_type('|', block) == 0)
        self.assertTrue(self.num_net_of_type('w', block) == 1)
        self.assertTrue(len(block.logic) == 1)
        self.assertTrue(len(block.wirevector_set) == 2)
        self.assertTrue(self.num_wire_of_type(pyrtl.wire.Const, block) == 1)

    def test_sanity_check(self):
        testmissing()

    def test_const_folding_complex_1(self):
        output = pyrtl.Output(bitwidth=3, name='output')
        counter = pyrtl.Register(bitwidth=3, name='counter')
        counter.next <<= counter + 1
        output <<= counter

        # just to check that something like this will run properly
        pyrtl.synthesize()
        pyrtl.optimize()
        block = pyrtl.working_block()
        timing_map = pyrtl.timing_analysis(block)
        timing_map_2 = pyrtl.quick_timing_analysis(block)
        block_max_time = pyrtl.timing_max_length(timing_map)
        block_max_time_2 = pyrtl.timing_max_length(timing_map_2)

    def test_timing_basic_1(self):
        inwire = pyrtl.Input(bitwidth=1)
        inwire2 = pyrtl.Input(bitwidth=1)
        outwire = pyrtl.Output()

        outwire <<= inwire | inwire2
        pyrtl.synthesize()
        pyrtl.optimize()
        block = pyrtl.working_block()
        timing_map = pyrtl.timing_analysis(block)
        block_max_time = pyrtl.timing_max_length(timing_map)
        self.assertTrue(block_max_time == 1)
        # should remove the and block and replace it with a

    def test_timing_basic_2(self):
        inwire = pyrtl.Input(bitwidth=1)
        inwire2 = pyrtl.Input(bitwidth=1)
        inwire3 = pyrtl.Input(bitwidth=1)
        tempwire = pyrtl.WireVector()
        tempwire2 = pyrtl.WireVector()
        outwire = pyrtl.Output()

        tempwire <<= inwire | inwire2
        tempwire2 <<= ~tempwire
        outwire <<= tempwire2 & inwire3
        pyrtl.synthesize()
        pyrtl.optimize()
        block = pyrtl.working_block()
        timing_map = pyrtl.timing_analysis(block)
        timing_map_2 = pyrtl.quick_timing_analysis(block)
        block_max_time = pyrtl.timing_max_length(timing_map)
        block_max_time_2 = pyrtl.timing_max_length(timing_map_2)
        self.assertTrue(block_max_time == 3)

        # this is because a stelth wire block gets added to the logic net
        self.assertTrue(block_max_time_2 == 4)
        pyrtl.timing_critical_path(timing_map)

    def test_timing_normal_adv_case_1(self):
        inwire1 = pyrtl.Input(bitwidth=3, name="input1")
        inwire2 = pyrtl.Input(bitwidth=3, name="input2")
        outwire = pyrtl.Output(bitwidth=4, name="output")

        outwire <<= inwire1 + inwire2

        # testing that this actually properly executes
        pyrtl.synthesize()
        pyrtl.optimize()
        block = pyrtl.working_block()
        timing_map = pyrtl.timing_analysis(block)
        block_max_time = pyrtl.timing_max_length(timing_map)
        pyrtl.timing_critical_path(timing_map)

    def test_timing_error(self):
        inwire = pyrtl.Input(bitwidth=1)
        inwire2 = pyrtl.Input(bitwidth=1)
        tempwire = pyrtl.WireVector(bitwidth=1)
        tempwire2 = pyrtl.WireVector(bitwidth=1)
        outwire = pyrtl.Output()

        tempwire <<= ~(inwire & tempwire2)
        tempwire2 <<= ~(inwire2 & tempwire)
        outwire <<= tempwire

        def doAllOps():
            pyrtl.synthesize()
            pyrtl.optimize()
            block = pyrtl.working_block()
            timing_map = pyrtl.timing_analysis(block)
            timing_map_2 = pyrtl.quick_timing_analysis(block)
            block_max_time = pyrtl.timing_max_length(timing_map)
            block_max_time_2 = pyrtl.timing_max_length(timing_map_2)

        self.assertRaises(pyrtl.PyrtlError, doAllOps)

    def test_synth_optimization_and_timing_1(self):
        inwire = pyrtl.Input(bitwidth=1)
        tempwire0 = pyrtl.WireVector(bitwidth=1)
        tempwire1 = pyrtl.WireVector(bitwidth=1)
        tempwire2 = pyrtl.WireVector(bitwidth=1)
        outwire = pyrtl.Output()

        tempwire0 <<= inwire
        tempwire1 <<= tempwire0
        tempwire2 <<= tempwire1
        outwire <<= ~tempwire2
        pyrtl.synthesize()
        pyrtl.optimize()
        block = pyrtl.working_block()
        # TODO: fix the function for wire deletion so that len(..) ==1
        self.assertTrue(len(block.logic) == 2)
        timing_map = pyrtl.timing_analysis(block)
        block_max_time = pyrtl.timing_max_length(timing_map)
        self.assertTrue(block_max_time == 1)

    def test_timing_normal_synth_adder(self):
        inwire1 = pyrtl.Input(bitwidth=3)
        inwire2 = pyrtl.Input(bitwidth=3)
        outwire = pyrtl.Output(bitwidth=4)

        outwire <<= inwire1 + inwire2

        # testing that this actually properly executes
        pyrtl.synthesize()
        pyrtl.optimize()
        block = pyrtl.working_block()
        timing_map = pyrtl.timing_analysis(block)
        block_max_time = pyrtl.timing_max_length(timing_map)

    def test_timing_advanced_1(self):
        inwire = pyrtl.Input(bitwidth=1)
        inwire2 = pyrtl.Input(bitwidth=1)
        inwire3 = pyrtl.Input(bitwidth=1)
        tempwire = pyrtl.WireVector()
        tempwire2 = pyrtl.WireVector()
        outwire = pyrtl.Output()

        tempwire <<= inwire | inwire2
        tempwire2 <<= ~tempwire
        outwire <<= tempwire2 & inwire3
        block = pyrtl.working_block()
        timing_map = pyrtl.advanced_timing_analysis(block)
        timing_max_length = pyrtl.timing_max_length(timing_map)
        self.assertTrue(timing_max_length == 3)
        critical_path = pyrtl.timing_critical_path(timing_map)

        pyrtl.synthesize()
        pyrtl.optimize()

        block = pyrtl.working_block()
        timing_map = pyrtl.advanced_timing_analysis(block)
        timing_max_length = pyrtl.timing_max_length(timing_map)
        self.assertTrue(timing_max_length == 3)
        critical_path = pyrtl.timing_critical_path(timing_map)

    def test_timing_adv_synth_adder(self):
        inwire1 = pyrtl.Input(bitwidth=3)
        inwire2 = pyrtl.Input(bitwidth=3)
        outwire = pyrtl.Output(bitwidth=4)

        outwire <<= inwire1 + inwire2
        block = pyrtl.working_block()
        timing_map = pyrtl.advanced_timing_analysis(block)
        timing_max_length = pyrtl.timing_max_length(timing_map)
        critical_path = pyrtl.timing_critical_path(timing_map)

        pyrtl.synthesize()
        pyrtl.optimize()

        block = pyrtl.working_block()
        timing_map = pyrtl.advanced_timing_analysis(block)
        timing_max_length = pyrtl.timing_max_length(timing_map)
        critical_path = pyrtl.timing_critical_path(timing_map)



if __name__ == "__main__":
    unittest.main()
