import doctest
import random
import unittest

import pyrtl
import pyrtl.rtllib.testingutils as utils
from pyrtl.rtllib import adders, multipliers


class TestDocTests(unittest.TestCase):
    """Test documentation examples."""

    def test_doctests(self):
        failures, tests = doctest.testmod(m=pyrtl.rtllib.multipliers)
        self.assertGreater(tests, 0)
        self.assertEqual(failures, 0)


class TestSimpleMult(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_trivial_case(self):
        self.mult_t_base(1, 5)

    def test_trivial_case_2(self):
        self.mult_t_base(2, 1)

    def test_trivial_case_3(self):
        self.mult_t_base(1, 1)

    def test_simple_mult_1(self):
        self.mult_t_base(5, 7)

    def test_simple_mult_2(self):
        self.mult_t_base(2, 9)

    def mult_t_base(self, len_a, len_b):
        a, b, reset = (
            pyrtl.Input(len_a, "a"),
            pyrtl.Input(len_b, "b"),
            pyrtl.Input(1, "reset"),
        )
        product, done = pyrtl.Output(name="product"), pyrtl.Output(name="done")
        m_prod, m_done = multipliers.simple_mult(a, b, reset)
        product <<= m_prod
        done <<= m_done
        self.assertEqual(len(product), len_a + len_b)

        xvals = [int(random.uniform(0, 2**len_a - 1)) for i in range(20)]
        yvals = [int(random.uniform(0, 2**len_b - 1)) for i in range(20)]
        true_result = [i * j for i, j in zip(xvals, yvals)]
        mult_results = []

        for x_val, y_val in zip(xvals, yvals):
            sim = pyrtl.Simulation()
            sim.step({a: x_val, b: y_val, reset: 1})
            while not sim.inspect("done"):
                sim.step({a: 0, b: 0, reset: 0})

            # Extracting the values and verifying correctness
            mult_results.append(sim.inspect("product"))
        self.assertEqual(mult_results, true_result)


class TestComplexMult(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_trivial_case(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.mult_t_base(1, 5, 2)

    def test_trivial_case_2(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.mult_t_base(2, 1, 5)

    def test_trivial_case_3(self):
        self.mult_t_base(1, 1, 1)

    def test_complex_mult_1(self):
        self.mult_t_base(5, 7, 3)

    def test_complex_mult_2(self):
        self.mult_t_base(10, 12, 3)

    def test_complex_mult_3(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.mult_t_base(2, 9, 4)

    def test_complex_mult_4(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.mult_t_base(8, 4, 6)

    def mult_t_base(self, len_a, len_b, shifts):
        a, b = pyrtl.Input(len_a, "a"), pyrtl.Input(len_b, "b")
        reset = pyrtl.Input(1, "reset")
        product, done = pyrtl.Output(name="product"), pyrtl.Output(name="done")
        m_prod, m_done = multipliers.complex_mult(a, b, shifts, reset)
        product <<= m_prod
        done <<= m_done
        self.assertEqual(len(product), len_a + len_b)

        xvals = [int(random.uniform(0, 2**len_a - 1)) for i in range(20)]
        yvals = [int(random.uniform(0, 2**len_b - 1)) for i in range(20)]
        true_result = [i * j for i, j in zip(xvals, yvals)]
        mult_results = []

        for x_val, y_val in zip(xvals, yvals):
            sim = pyrtl.Simulation()
            sim.step({a: x_val, b: y_val, reset: 1})
            while not sim.inspect("done"):
                sim.step({a: 0, b: 0, reset: 0})

            # Extracting the values and verifying correctness
            mult_results.append(sim.inspect("product"))
        self.assertEqual(mult_results, true_result)


class TestWallace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # this is to ensure reproducibility
        random.seed(777906376)

    def setUp(self):
        pyrtl.reset_working_block()

    def mult_t_base(self, len_a, len_b, **mult_args):
        # Creating the logic nets
        a, b = pyrtl.Input(len_a, "a"), pyrtl.Input(len_b, "b")
        product = pyrtl.Output(name="product")
        product <<= multipliers.tree_multiplier(a, b, **mult_args)

        self.assertEqual(len(product), len_a + len_b)

        # creating the testing values and the correct results
        xvals = [int(random.uniform(0, 2**len_a - 1)) for i in range(20)]
        yvals = [int(random.uniform(0, 2**len_b - 1)) for i in range(20)]
        true_result = [i * j for i, j in zip(xvals, yvals)]

        # Setting up and running the tests
        sim = pyrtl.Simulation()
        for cycle in range(len(xvals)):
            sim.step({a: xvals[cycle], b: yvals[cycle]})

        # Extracting the values and verifying correctness
        multiplier_result = sim.tracer.trace[product.name]
        self.assertEqual(multiplier_result, true_result)

    def test_trivial_case(self):
        self.mult_t_base(1, 5)

    def test_trivial_case_2(self):
        self.mult_t_base(2, 1)

    def test_trivial_case_3(self):
        self.mult_t_base(1, 1)

    def test_wallace_tree_1(self):
        self.mult_t_base(5, 7)

    def test_wallace_tree_2(self):
        self.mult_t_base(2, 9)

    def test_dada_tree(self):
        self.mult_t_base(5, 10, reducer=adders.dada_reducer)

    def test_fma_1(self):
        wires, vals = utils.make_inputs_and_values(
            exact_bitwidth=10, num_wires=3, dist=utils.inverse_power_dist
        )
        test_w = multipliers.fused_multiply_adder(
            wires[0],
            wires[1],
            wires[2],
            False,
            reducer=adders.dada_reducer,
            adder_func=adders.ripple_add,
        )
        self.assertEqual(len(test_w), 20)
        outwire = pyrtl.Output(21, "test")
        outwire <<= test_w

        out_vals = utils.sim_and_ret_out(outwire, wires, vals)
        true_result = [
            vals[0][cycle] * vals[1][cycle] + vals[2][cycle]
            for cycle in range(len(vals[0]))
        ]
        self.assertEqual(out_vals, true_result)

    def test_gen_fma_1(self):
        wires, vals = utils.make_inputs_and_values(
            max_bitwidth=8, num_wires=8, dist=utils.inverse_power_dist
        )
        # mixing tuples and lists solely for readability purposes
        mult_pairs = [(wires[0], wires[1]), (wires[2], wires[3]), (wires[4], wires[5])]
        add_wires = (wires[6], wires[7])

        outwire = pyrtl.Output(name="test")
        outwire <<= multipliers.generalized_fma(mult_pairs, add_wires, signed=False)

        out_vals = utils.sim_and_ret_out(outwire, wires, vals)
        true_result = [
            vals[0][cycle] * vals[1][cycle]
            + vals[2][cycle] * vals[3][cycle]
            + vals[4][cycle] * vals[5][cycle]
            + vals[6][cycle]
            + vals[7][cycle]
            for cycle in range(len(vals[0]))
        ]
        self.assertEqual(out_vals, true_result)


class TestSignedTreeMult(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # this is to ensure reproducibility
        random.seed(777906375)

    def setUp(self):
        pyrtl.reset_working_block()

    def mult_t_base(self, len_a, len_b, **mult_args):
        # Creating the logic nets
        a, b = pyrtl.Input(len_a, "a"), pyrtl.Input(len_b, "b")
        product = pyrtl.Output(name="product")
        product <<= multipliers.signed_tree_multiplier(a, b, **mult_args)

        self.assertEqual(len(product), len_a + len_b)

        # creating the testing values and the correct results
        bound_a = 2 ** (len_a - 1) - 1
        bound_b = 2 ** (len_b - 1) - 1
        xvals = [int(random.uniform(-bound_a, bound_a)) for i in range(20)]
        yvals = [int(random.uniform(-bound_b, bound_b)) for i in range(20)]
        true_result = [i * j for i, j in zip(xvals, yvals)]

        # Setting up and running the tests
        sim = pyrtl.Simulation()
        for cycle in range(len(xvals)):
            sim.step({a: xvals[cycle], b: yvals[cycle]})

        # Extracting the values and verifying correctness
        multiplier_result = [
            pyrtl.val_to_signed_integer(p, len(product))
            for p in sim.tracer.trace[product.name]
        ]
        self.assertEqual(multiplier_result, true_result)

    def test_small_bitwidth_error(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.mult_t_base(1, 1)

    def test_trivial_case(self):
        self.mult_t_base(2, 3)

    def test_trivial_case_2(self):
        self.mult_t_base(4, 4)

    def test_trivial_case_3(self):
        self.mult_t_base(3, 4)

    def test_wallace_tree_1(self):
        self.mult_t_base(10, 3)

    def test_wallace_tree_2(self):
        self.mult_t_base(8, 8)

    def test_dada_tree(self):
        self.mult_t_base(5, 10, reducer=adders.dada_reducer)


if __name__ == "__main__":
    unittest.main()
