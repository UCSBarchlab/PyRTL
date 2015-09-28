import unittest
import random
import pyrtl
from pyrtl.rtllib import adders
import t_utils as utils


class TestAdders(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        random.seed(8492049)

    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def adder2_t_base_1(self, adder_func):
        wires, vals = utils.make_wires_and_values(max_bitwidth=35, num_wires=2)
        sum = pyrtl.Output(36, "sum")
        sum <<= adder_func(*wires)

        adder_result = utils.sim_and_ret_out(sum, wires, vals)
        true_result = [c + d for c, d in zip(*vals)]
        self.assertEqual(adder_result, true_result)

    def test_kogge_stone_1(self):
        self.adder2_t_base_1(adders.kogge_stone)

    def test_ripple_1(self):
        self.adder2_t_base_1(adders.ripple_add)

    def test_carry_save_1(self):
        a, b, c = pyrtl.Input(32, "a"), pyrtl.Input(32, "b"), pyrtl.Input(32, "c")
        sum = pyrtl.Output(34, "sum")
        sum <<= adders.carrysave_adder(a, b, c)

        # x = [int(random.uniform(0, 2**32-1)) for i in range(20)]
        # y = [int(random.uniform(0, 2**32-1)) for i in range(20)]

        x = [3759516320, 973033565, 4120989505, 199451263, 3625363122, 1115190551, 2207055453,
             2946555493, 760932817, 1072117699, 3456362420, 2369715268, 341973812, 1822482086,
             1000917448, 3736696910, 1952403941, 766232820, 3355093416, 3068692689]
        y = [637240484, 2996140373, 4171443642, 500315891, 2908097029, 3899747324, 1198363687,
             2707178015, 1873950916, 1166457082, 321919507, 1480307297, 2704513799, 1502918399,
             895718745, 1215430802, 3917621196, 3157183468, 14334859, 1254750152]
        z = [637240484, 2996140373, 4171443642, 500315891, 2908097029, 3899747324, 1198363687,
             2707178015, 1873950916, 1166457082, 321919507, 1480307297, 2704513799, 1502918399,
             895718745, 1215430802, 3917621196, 3157183468, 14334859, 1254750152]

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)

        for cycle in range(len(x)):
            sim.step({
                a: x[cycle],
                b: y[cycle],
                c: z[cycle],
            })
        true_result = [a + b + c for a, b, c in zip(x, y, z)]
        adder_result = sim_trace.trace[sum]
        sim_trace.render_trace()
        assert (adder_result == true_result)

    def test_fast_group_adder_1(self):
        wires, vals = utils.make_wires_and_values(max_bitwidth=12, num_wires=7)
        outwire = pyrtl.Output(name="test")
        outwire <<= adders.fast_group_adder(wires)

        out_vals = utils.sim_and_ret_out(outwire, wires, vals)
        true_result = [sum(val[cycle] for val in vals) for cycle in range(len(vals[0]))]
        self.assertEqual(out_vals, true_result)
