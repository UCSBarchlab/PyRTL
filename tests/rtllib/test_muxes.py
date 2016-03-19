import unittest
import pyrtl
from pyrtl.rtllib import testingutils as utils
from pyrtl.rtllib import muxes


class TestPrioritizedMuxTrivial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pyrtl.reset_working_block()

    def test_empty(self):
        with self.assertRaises(pyrtl.PyrtlError):
            x = muxes.prioritized_mux([], [])

    def test_different_sel_and_val_lengths(self):
        a = pyrtl.WireVector(1)
        with self.assertRaises(pyrtl.PyrtlError):
            x = muxes.prioritized_mux([a], [a, a])

    def test_invalid_select_width(self):
        a = pyrtl.WireVector(2)
        b = pyrtl.WireVector(2)
        c = pyrtl.WireVector(10)
        with self.assertRaises(pyrtl.PyrtlError):
            x = muxes.prioritized_mux([a, b], [c, c])

    def test_one_wire(self):
        a = pyrtl.WireVector(1)
        b = pyrtl.WireVector(10)
        x = muxes.prioritized_mux([a], [b])
        self.assertIs(b, x)


def pri_mux_actual(sels , vals):
    # python version of the pri mux hardware
    assert(len(sels) == len(vals))
    for index, s in enumerate(sels):
        if s:
            return vals[index]
    return vals[-1]


class TestPrioritizedMuxSim(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_select_with_2_wires(self):
        val_width = 5
        sels, sel_vals = utils.make_inputs_and_values(2, exact_bitwidth=1)
        mux_ins, vals = utils.make_inputs_and_values(2, exact_bitwidth=val_width)

        out = pyrtl.Output(val_width, "out")
        out <<= muxes.prioritized_mux(sels, mux_ins)
        actual = utils.sim_and_ret_out(out, sels + mux_ins, sel_vals + vals)
        expected = [pri_mux_actual(sel, val) for sel, val in zip(zip(*sel_vals), zip(*vals))]
        self.assertEqual(actual, expected)

    def test_select_with_5_wires(self):
        val_width = 5
        sels, sel_vals = utils.make_inputs_and_values(5, exact_bitwidth=1, test_vals=50)
        mux_ins, vals = utils.make_inputs_and_values(5, exact_bitwidth=val_width, test_vals=50)

        out = pyrtl.Output(val_width, "out")
        out <<= muxes.prioritized_mux(sels, mux_ins)
        actual = utils.sim_and_ret_out(out, sels + mux_ins, sel_vals + vals)
        expected = [pri_mux_actual(sel, val) for sel, val in zip(zip(*sel_vals), zip(*vals))]
        self.assertEqual(actual, expected)


class TestIsEquivelent(unittest.TestCase):
    def test_equivalent_const(self):
        a = pyrtl.Const(1)
        b = pyrtl.Const(1)
        c = pyrtl.Const(1, 2)
        d = pyrtl.Const(3)
        self.assertTrue(muxes._is_equivelent(a, a))
        self.assertTrue(muxes._is_equivelent(a, b))
        self.assertFalse(muxes._is_equivelent(a, c))
        self.assertFalse(muxes._is_equivelent(a, d))

    def test_equivalent(self):
        a = pyrtl.WireVector(2)
        b = pyrtl.Const(2, 2)
        c = pyrtl.Output()

        self.assertTrue(muxes._is_equivelent(a, a))
        self.assertTrue(muxes._is_equivelent(c, c))
        self.assertFalse(muxes._is_equivelent(a, b))
        self.assertFalse(muxes._is_equivelent(a, c))


class TestSmartMuxTrivial(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_one_value(self):
        sel = pyrtl.WireVector(3)
        a = pyrtl.WireVector(1)
        self.assertIs(muxes.sparse_mux(sel, {6: a}), a)

    def test_dup_value(self):
        sel = pyrtl.WireVector(3)
        a = pyrtl.WireVector(1)
        self.assertIs(muxes.sparse_mux(sel, {6: a, 2: a}), a)

    def test_dup_consts1(self):
        sel = pyrtl.WireVector(1)
        c1 = pyrtl.Const(4)
        c2 = pyrtl.Const(4)
        res = muxes.sparse_mux(sel, {0: c1, 1: c2})
        self.assertIsInstance(res, pyrtl.Const)
        self.assertEqual(res.val, 4)

    def test_dup_consts2(self):
        sel = pyrtl.WireVector(3)
        c1 = pyrtl.Const(4)
        c2 = pyrtl.Const(4)
        res = muxes.sparse_mux(sel, {6: c1, 2: c2})
        self.assertIsInstance(res, pyrtl.Const)
        self.assertEqual(res.val, 4)

    def test_no_dup_2(self):
        sel = pyrtl.WireVector(3)
        c1 = pyrtl.Const(4)
        c2 = pyrtl.Const(6)
        res = muxes.sparse_mux(sel, {6: c1, 2: c2})
        self.assertNotIsInstance(res, pyrtl.Const)

    def test_no_dup(self):
        sel = pyrtl.WireVector(3)
        a = pyrtl.WireVector(3)
        b = pyrtl.WireVector(3)
        res = muxes.sparse_mux(sel, {6: a, 2: b})
        self.assertIsNot(res, a)
        self.assertIsNot(res, b)


gen_in = utils.generate_in_wire_and_values


class TestSmartMux(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_two_vals(self):
        sel, sel_vals = gen_in(1, random_dist=utils.uniform_dist)
        a1, a1_vals = gen_in(3, random_dist=utils.uniform_dist)
        a2, a2_vals = gen_in(3, random_dist=utils.uniform_dist)
        res = pyrtl.Output(name="output")

        res <<= muxes.sparse_mux(sel, {0: a1, 1: a2})
        in_vals = [sel_vals, a1_vals, a2_vals]
        out_res = utils.sim_and_ret_out(res, [sel, a1, a2], in_vals)

        expected_out = [e2 if sel else e1 for sel, e1, e2 in zip(*in_vals)]
        self.assertEqual(out_res, expected_out)

    def test_two_vals_big(self):
        sel = pyrtl.Input(3)
        a1, a1_vals = gen_in(3, random_dist=utils.uniform_dist)
        a2, a2_vals = gen_in(3, random_dist=utils.uniform_dist)
        res = pyrtl.Output(name="output")

        sel_vals = [utils.uniform_dist(1) for i in range(20)]
        real_sel = [6 if s else 2 for s in sel_vals]
        res <<= muxes.sparse_mux(sel, {2: a1, 6: a2})
        out_res = utils.sim_and_ret_out(res, [sel, a1, a2], [real_sel, a1_vals, a2_vals])

        expected_out = [e2 if sel else e1 for sel, e1, e2 in zip(sel_vals, a1_vals, a2_vals)]
        self.assertEqual(out_res, expected_out)

    def test_two_big_close(self):
        sel = pyrtl.Input(3)
        a1, a1_vals = gen_in(3, random_dist=utils.uniform_dist)
        a2, a2_vals = gen_in(3, random_dist=utils.uniform_dist)
        res = pyrtl.Output(name="output")

        sel_vals = [utils.uniform_dist(1) for i in range(20)]
        real_sel = [6 if s else 5 for s in sel_vals]
        res <<= muxes.sparse_mux(sel, {5: a1, 6: a2})
        out_res = utils.sim_and_ret_out(res, [sel, a1, a2], [real_sel, a1_vals, a2_vals])

        expected_out = [e2 if sel else e1 for sel, e1, e2 in zip(sel_vals, a1_vals, a2_vals)]
        self.assertEqual(out_res, expected_out)


class TestSmartMuxDefault(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_default(self):
        sel, sel_vals = gen_in(3, random_dist=utils.uniform_dist)
        a1, a1_vals = gen_in(3, random_dist=utils.uniform_dist)
        a2, a2_vals = gen_in(3, random_dist=utils.uniform_dist)
        default, default_vals = gen_in(3, random_dist=utils.uniform_dist)
        res = pyrtl.Output(name="output")

        res <<= muxes.sparse_mux(sel, {5: a1, 6: a2, muxes.SparseDefault: default})
        out_res = utils.sim_and_ret_out(res, [sel, a1, a2, default],
                                         [sel_vals, a1_vals, a2_vals, default_vals])

        expected_out = [e2 if sel == 6 else e1 if sel == 5 else d
                        for sel, e1, e2, d in zip(sel_vals, a1_vals, a2_vals, default_vals)]
        self.assertEqual(out_res, expected_out)
