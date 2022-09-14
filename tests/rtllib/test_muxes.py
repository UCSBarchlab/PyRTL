import unittest
import pyrtl
from pyrtl.rtllib import testingutils as utils
from pyrtl.rtllib import muxes

gen_in = utils.an_input_and_vals


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


def pri_mux_actual(sels, vals):
    # python version of the pri mux hardware
    assert len(sels) == len(vals)
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


class TestIsEquivalent(unittest.TestCase):
    def test_equivalent_const(self):
        a = pyrtl.Const(1)
        b = pyrtl.Const(1)
        c = pyrtl.Const(1, 2)
        d = pyrtl.Const(3)
        self.assertTrue(muxes._is_equivalent(a, a))
        self.assertTrue(muxes._is_equivalent(a, b))
        self.assertFalse(muxes._is_equivalent(a, c))
        self.assertFalse(muxes._is_equivalent(a, d))

    def test_equivalent(self):
        a = pyrtl.WireVector(2)
        b = pyrtl.Const(2, 2)
        c = pyrtl.Output()

        self.assertTrue(muxes._is_equivalent(a, a))
        self.assertTrue(muxes._is_equivalent(c, c))
        self.assertFalse(muxes._is_equivalent(a, b))
        self.assertFalse(muxes._is_equivalent(a, c))


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


class TestSmartMux(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_two_vals(self):
        sel, sel_vals = gen_in(1)
        a1, a1_vals = gen_in(3)
        a2, a2_vals = gen_in(3)
        res = pyrtl.Output(name="output")

        res <<= muxes.sparse_mux(sel, {0: a1, 1: a2})
        in_vals = [sel_vals, a1_vals, a2_vals]
        out_res = utils.sim_and_ret_out(res, [sel, a1, a2], in_vals)

        expected_out = [e2 if sel else e1 for sel, e1, e2 in zip(*in_vals)]
        self.assertEqual(out_res, expected_out)

    def test_two_vals_big(self):
        sel = pyrtl.Input(3)
        a1, a1_vals = gen_in(3)
        a2, a2_vals = gen_in(3)
        res = pyrtl.Output(name="output")

        sel_vals = [utils.uniform_dist(1) for i in range(20)]
        real_sel = [6 if s else 2 for s in sel_vals]
        res <<= muxes.sparse_mux(sel, {2: a1, 6: a2})
        out_res = utils.sim_and_ret_out(res, [sel, a1, a2], [real_sel, a1_vals, a2_vals])

        expected_out = [e2 if sel else e1 for sel, e1, e2 in zip(sel_vals, a1_vals, a2_vals)]
        self.assertEqual(out_res, expected_out)

    def test_multiple_bitwidths(self):
        sel = pyrtl.Input(3)
        a1, a1_vals = gen_in(3)
        a2, a2_vals = gen_in(8)
        a3, a3_vals = gen_in(5)
        res = pyrtl.Output(name="output")

        m = muxes.sparse_mux(sel, {2: a1, 3: a2, 6: a3})
        self.assertEqual(len(m), 8)  # the biggest one

    def test_two_big_close(self):
        sel = pyrtl.Input(3)
        a1, a1_vals = gen_in(3)
        a2, a2_vals = gen_in(3)
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
        sel, sel_vals = gen_in(3)
        a1, a1_vals = gen_in(3)
        a2, a2_vals = gen_in(3)
        default, default_vals = gen_in(3)
        res = pyrtl.Output(name="output")

        res <<= muxes.sparse_mux(sel, {5: a1, 6: a2, muxes.SparseDefault: default})
        out_res = utils.sim_and_ret_out(res, [sel, a1, a2, default],
                                        [sel_vals, a1_vals, a2_vals, default_vals])

        expected_out = [e2 if sel == 6 else e1 if sel == 5 else d
                        for sel, e1, e2, d in zip(sel_vals, a1_vals, a2_vals, default_vals)]
        self.assertEqual(out_res, expected_out)


class TestMultiSelector(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_value_already_set(self):
        sel = pyrtl.Input(1)
        wire = pyrtl.WireVector(8)
        i1_out = pyrtl.Output(name="i1_out")
        i2_out = pyrtl.Output(name="i2_out")
        with muxes.MultiSelector(sel, i1_out, i2_out) as mul_sel:
            mul_sel.option(0, wire, wire)
            with self.assertRaises(pyrtl.PyrtlError):
                mul_sel.option(0, wire, wire)

    def test_incorrect_number_of_wires(self):
        sel = pyrtl.Input(1)
        wire = pyrtl.WireVector(8)
        i1_out = pyrtl.Output(name="i1_out")
        i2_out = pyrtl.Output(name="i2_out")
        with muxes.MultiSelector(sel, i1_out, i2_out) as mul_sel:
            mul_sel.option(0, wire, wire)
            with self.assertRaises(pyrtl.PyrtlError):
                mul_sel.option(1, wire, wire, wire)

    def test_incorrect_number_of_wires_2(self):
        sel = pyrtl.Input(1)
        wire = pyrtl.WireVector(8)
        i1_out = pyrtl.Output(name="i1_out")
        i2_out = pyrtl.Output(name="i2_out")
        i3_out = pyrtl.Output(name="i3_out")
        mul_sel = muxes.MultiSelector(sel, i1_out, i2_out, i3_out)
        with self.assertRaises(pyrtl.PyrtlError):
            mul_sel.option(0, wire, wire)


class TestMultiSelectorSim(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_really_simple(self):
        sel, sel_vals = gen_in(1)

        i1_0, i1_0_vals = gen_in(8)
        i2_0, i2_0_vals = gen_in(8)
        i1_1, i1_1_vals = gen_in(8)
        i2_1, i2_1_vals = gen_in(8)

        i1_out = pyrtl.Output(name="i1_out")
        i2_out = pyrtl.Output(name="i2_out")

        with muxes.MultiSelector(sel, i1_out, i2_out) as mul_sel:
            mul_sel.option(0, i1_0, i2_0)
            mul_sel.option(1, i1_1, i2_1)

        actual_outputs =\
            utils.sim_and_ret_outws([sel, i1_0, i1_1, i2_0, i2_1],
                                    [sel_vals, i1_0_vals, i1_1_vals, i2_0_vals, i2_1_vals])
        expected_i1_out = [v1 if s else v0 for s, v0, v1 in zip(sel_vals, i1_0_vals, i1_1_vals)]
        expected_i2_out = [v1 if s else v0 for s, v0, v1 in zip(sel_vals, i2_0_vals, i2_1_vals)]

        self.assertEqual(actual_outputs[i1_out.name], expected_i1_out)
        self.assertEqual(actual_outputs[i2_out.name], expected_i2_out)

    def test_simple(self):
        sel, sel_vals = gen_in(2)

        x1s, x1_vals = (list(x) for x in zip(*(gen_in(8) for i in range(4))))
        x2s, x2_vals = (list(x) for x in zip(*(gen_in(8) for i in range(4))))
        x3s, x3_vals = (list(x) for x in zip(*(gen_in(8) for i in range(4))))

        i1_out = pyrtl.Output(name="i1_out")
        i2_out = pyrtl.Output(name="i2_out")
        i3_out = pyrtl.Output(name="i3_out")

        with muxes.MultiSelector(sel, i1_out, i2_out, i3_out) as mu:
            for i in range(4):
                mu.option(i, x1s[i], x2s[i], x3s[i])

        wires = [sel] + x1s + x2s + x3s
        vals = [sel_vals] + x1_vals + x2_vals + x3_vals
        actual_outputs = utils.sim_and_ret_outws(wires, vals)

        expected_i1_out = [v[s] for s, v in zip(sel_vals, zip(*x1_vals))]
        expected_i2_out = [v[s] for s, v in zip(sel_vals, zip(*x2_vals))]
        expected_i3_out = [v[s] for s, v in zip(sel_vals, zip(*x3_vals))]

        self.assertEqual(actual_outputs[i1_out.name], expected_i1_out)
        self.assertEqual(actual_outputs[i2_out.name], expected_i2_out)
        self.assertEqual(actual_outputs[i3_out.name], expected_i3_out)


class TestDemux(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_simple_demux(self):
        in_w, in_vals = utils.an_input_and_vals(2)
        outs = (pyrtl.Output(name="output_" + str(i)) for i in range(4))
        demux_outs = pyrtl.rtllib.muxes.demux(in_w)
        for out_w, demux_out in zip(outs, demux_outs):
            out_w <<= demux_out
        traces = utils.sim_and_ret_outws((in_w,), (in_vals,))

        for cycle in range(20):
            for i, out_wire in enumerate(outs):
                self.assertEqual(in_vals[i] == i, traces[out_wire][cycle])

    def test_demux_2(self):
        in_w, in_vals = utils.an_input_and_vals(1)
        outs = (pyrtl.Output(name="output_" + str(i)) for i in range(2))
        demux_outs = pyrtl.rtllib.muxes._demux_2(in_w)
        for out_w, demux_out in zip(outs, demux_outs):
            out_w <<= demux_out
        traces = utils.sim_and_ret_outws((in_w,), (in_vals,))

        for cycle in range(20):
            for i, out_wire in enumerate(outs):
                self.assertEqual(in_vals[i] == i, traces[out_wire][cycle])

    def test_large_demux(self):
        in_w, in_vals = utils.an_input_and_vals(5)
        outs = (pyrtl.Output(name="output_" + str(i)) for i in range(32))
        demux_outs = pyrtl.rtllib.muxes.demux(in_w)
        for out_w, demux_out in zip(outs, demux_outs):
            self.assertEqual(len(demux_out), 1)
            out_w <<= demux_out
        traces = utils.sim_and_ret_outws((in_w,), (in_vals,))

        for cycle in range(20):
            for i, out_wire in enumerate(outs):
                self.assertEqual(in_vals[i] == i, traces[out_wire][cycle])
