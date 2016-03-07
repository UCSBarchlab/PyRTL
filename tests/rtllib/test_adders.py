import random
import unittest

import pyrtl
import pyrtl.rtllib.testingutils as utils
from pyrtl.rtllib import adders


class TestAdders(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        random.seed(8492049)

    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def adder2_t_base_1(self, adder_func):
        self.adder_t_base(adder_func, max_bitwidth=34, num_wires=2)

    def adder_t_base(self, adder_func, **kwargs):
        wires, vals = utils.make_inputs_and_values(dist=utils.inverse_power_dist, **kwargs)
        outwire = pyrtl.Output(name="test")
        outwire <<= adder_func(*wires)

        out_vals = utils.sim_and_ret_out(outwire, wires, vals)
        true_result = [sum(cycle_vals) for cycle_vals in zip(*vals)]
        self.assertEqual(out_vals, true_result)

    def test_kogge_stone_1(self):
        self.adder2_t_base_1(adders.kogge_stone)

    def test_ripple_1(self):
        self.adder2_t_base_1(adders.ripple_add)

    def test_carrylookahead_1(self):
        self.adder2_t_base_1(adders.cla_adder)

    def test_carry_save_1(self):
        self.adder_t_base(adders.carrysave_adder, exact_bitwidth=32, num_wires=3)

    def test_fast_group_adder_1(self):
        wires, vals = utils.make_inputs_and_values(max_bitwidth=12, num_wires=7,
                                                   dist=utils.inverse_power_dist)
        outwire = pyrtl.Output(name="test")
        outwire <<= adders.fast_group_adder(wires)

        out_vals = utils.sim_and_ret_out(outwire, wires, vals)
        true_result = [sum(cycle_vals) for cycle_vals in zip(*vals)]
        self.assertEqual(out_vals, true_result)
