import unittest
import pyrtl
import pyrtl.core
import pyrtl.wire

from helperfunctions import testmissing


class TestPasses(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        pyrtl.set_debug_mode(True)

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
        pyrtl.optimize()
        # should remove the middle wire but keep the input
        block = pyrtl.working_block(None)
        self.assertTrue(len(block.logic) == 1)
        self.assertTrue(len(block.wirevector_set) == 2)
        # # self.assertTrue(result.startswith("tmp3/3O <-- w -- tmp1/3I"))

    def test_wire_net_removal_2(self):
        inwire = pyrtl.Input(bitwidth=3)
        tempwire = pyrtl.WireVector()
        tempwire2 = pyrtl.WireVector()
        outwire = pyrtl.Output()
        tempwire <<= inwire
        tempwire2 <<= tempwire
        outwire <<= tempwire
        pyrtl.optimize()
        # should remove the middle wires but keep the input
        block = pyrtl.working_block(None)
        self.assertTrue(len(block.logic) == 1)
        self.assertTrue(len(block.wirevector_set) == 2)
        # # self.assertTrue(result.startswith("tmp7/3O <-- w -- tmp4/3I"))

    def test_const_folding_basic_one_var_op_1(self):
        constwire = pyrtl.Const(0, 1)
        outwire = pyrtl.Output()

        outwire <<= ~constwire
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


if __name__ == "__main__":
    unittest.main()
