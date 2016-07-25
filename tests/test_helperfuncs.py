import io
import random
import unittest

import pyrtl
import pyrtl.corecircuits
from pyrtl import helperfuncs
from pyrtl.rtllib import testingutils as utils


# ---------------------------------------------------------------


class TestAnyAll(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output, compact=True)
        self.assertEqual(output.getvalue(), correct_string)

    def test_any_only_on_1_bit_vectors(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.rtl_any(a, b)

    def test_all_only_on_1_bit_vectors(self):
        a = pyrtl.WireVector(name='a', bitwidth=1)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.rtl_all(a, b, c)

    def test_any_works_with_consts(self):
        a = pyrtl.WireVector(name='a', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        r = pyrtl.corecircuits.rtl_any(a, 1, c)

    def test_all_works_with_consts(self):
        a = pyrtl.WireVector(name='a', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        r = pyrtl.corecircuits.rtl_all(a, 1, c)

    def test_any_does_simulation_correct(self):
        r = pyrtl.Register(3, 'r')
        r.next <<= r + 1
        a, b, c = r[0], r[1], r[2]
        o = pyrtl.Output(name='o')
        o <<= pyrtl.corecircuits.rtl_any(a, b, c)
        self.check_trace('o 01111111\nr 01234567\n')

    def test_all_does_simulation_correct(self):
        r = pyrtl.Register(3, 'r')
        r.next <<= r + 1
        a, b, c = r[0], r[1], r[2]
        o = pyrtl.Output(name='o')
        o <<= pyrtl.corecircuits.rtl_all(a, b, c)
        self.check_trace('o 00000001\nr 01234567\n')


class TestXorAllBits(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output, compact=True)
        self.assertEqual(output.getvalue(), correct_string)

    def test_one_wirevector(self):
        r = pyrtl.Register(3, 'r')
        r.next <<= r + 1
        o = pyrtl.Output(name='o')
        o <<= pyrtl.corecircuits.xor_all_bits(r)
        self.check_trace('o 01101001\nr 01234567\n')

    def test_list_of_one_bit_wires(self):
        r = pyrtl.Register(2, 'r')
        r.next <<= r + 1
        o = pyrtl.Output(name='o')
        o <<= pyrtl.corecircuits.xor_all_bits([r[0], r[1]])
        self.check_trace('o 01100110\nr 01230123\n')

    def test_list_of_long_wires(self):
        in_wires, vals = utils.make_inputs_and_values(4, exact_bitwidth=13)
        out = pyrtl.Output(name='o')
        out <<= pyrtl.corecircuits.xor_all_bits(in_wires)
        expected = [v1 ^ v2 ^ v3 ^ v4 for v1, v2, v3, v4 in zip(*vals)]
        self.assertEqual(expected, utils.sim_and_ret_out(out, in_wires, vals))


class TestMux(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_mux_too_many_inputs(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=1)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.mux(s, a, b, c)

    def test_mux_not_enough_inputs(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.mux(s, a, b, c)

    def test_mux_not_enough_inputs_but_default(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        r = pyrtl.corecircuits.mux(s, a, b, default=0)

    def test_mux_enough_inputs_with_default(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        d = pyrtl.WireVector(name='d', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        r = pyrtl.corecircuits.mux(s, a, b, c, d, default=0)

    def test_mux_too_many_inputs_with_default(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        d = pyrtl.WireVector(name='d', bitwidth=1)
        e = pyrtl.WireVector(name='e', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.mux(s, a, b, c, d, e, default=0)

    def test_mux_too_many_inputs_with_extra_kwarg(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.corecircuits.mux(s, a, b, default=0, foo=1)


class TestMuxSimulation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        random.seed(8492049)

    def setUp(self):
        pyrtl.reset_working_block()

    def test_simple_mux_1(self):
        self.mux_t_subprocess(4, 16)

    def test_simple_mux_2(self):
        self.mux_t_subprocess(6, 7)

    def mux_t_subprocess(self, addr_width, val_width):
        mux_ins, vals = utils.make_consts(num_wires=2**addr_width, exact_bitwidth=val_width)
        control, testctrl = utils.an_input_and_vals(addr_width, 40, "mux_ctrl")

        out = pyrtl.Output(val_width, "mux_out")
        out <<= pyrtl.corecircuits.mux(control, *mux_ins)

        true_result = [vals[i] for i in testctrl]
        mux_result = utils.sim_and_ret_out(out, (control,), (testctrl,))
        self.assertEqual(mux_result, true_result)

    def test_mux_with_default(self):
        addr_width = 5
        val_width = 9
        default_val = 170  # arbitrary value under 2**val_width
        num_defaults = 5
        mux_ins, vals = utils.make_consts(num_wires=2**addr_width - num_defaults,
                                          exact_bitwidth=val_width, random_dist=utils.uniform_dist)
        control, testctrl = utils.an_input_and_vals(addr_width, 40, "mux_ctrl", utils.uniform_dist)

        for i in range(5):
            vals.append(default_val)

        out = pyrtl.Output(val_width, "mux_out")
        out <<= pyrtl.corecircuits.mux(control, *mux_ins, default=pyrtl.Const(default_val))

        true_result = [vals[i] for i in testctrl]
        mux_result = utils.sim_and_ret_out(out, (control,), (testctrl,))
        self.assertEqual(mux_result, true_result)

    def test_select(self):
        vals = 12, 27
        mux_ins = [pyrtl.Const(x) for x in vals]
        control, testctrl = utils.an_input_and_vals(1, 40, "sel_ctrl", utils.uniform_dist)

        out = pyrtl.Output(5, "mux_out")
        out <<= pyrtl.corecircuits.select(control, falsecase=mux_ins[0], truecase=mux_ins[1])

        true_result = [vals[i] for i in testctrl]
        mux_result = utils.sim_and_ret_out(out, (control,), (testctrl,))
        self.assertEqual(mux_result, true_result)

    def test_select_no_pred(self):
        vals = 12, 27
        mux_ins = [pyrtl.Const(x) for x in vals]
        control, testctrl = utils.an_input_and_vals(1, 40, "sel_ctrl", utils.uniform_dist)

        out = pyrtl.Output(5, "mux_out")
        out <<= pyrtl.corecircuits.select(control, mux_ins[1], mux_ins[0])

        true_result = [vals[i] for i in testctrl]
        mux_result = utils.sim_and_ret_out(out, (control,), (testctrl,))
        self.assertEqual(mux_result, true_result)


class TestRtlProbe(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_bad_probe_wire(self):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.probe(5)
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.probe('a')

    def test_simple_probe(self):
        i = pyrtl.Input(1)
        o = pyrtl.Output(1)
        o <<= pyrtl.probe(i + 1)

    def test_probe_wire(self):
        i = pyrtl.Input(1)
        x = pyrtl.probe(i)
        self.assertIs(x, i)

    def test_simple_probe_debug(self):
        pyrtl.set_debug_mode()
        i = pyrtl.Input(1)
        o = pyrtl.Output(1)
        o <<= pyrtl.probe(i + 1)
        pyrtl.set_debug_mode(False)


class TestBasicMult(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def mult_t_base(self, len_a, len_b):
        # Creating the logic nets
        a, b = pyrtl.Input(len_a, "a"), pyrtl.Input(len_b, "b")
        product = pyrtl.Output(name="product")
        product <<= pyrtl.corecircuits._basic_mult(a, b)

        self.assertEquals(len(product), len_a + len_b)

        # creating the testing values and the correct results
        xvals = [int(random.uniform(0, 2**len_a-1)) for i in range(20)]
        yvals = [int(random.uniform(0, 2**len_b-1)) for i in range(20)]
        true_result = [i * j for i, j in zip(xvals, yvals)]

        # Setting up and running the tests
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for cycle in range(len(xvals)):
            sim.step({a: xvals[cycle], b: yvals[cycle]})

        # Extracting the values and verifying correctness
        multiplier_result = sim_trace.trace[product]
        self.assertEqual(multiplier_result, true_result)

    def test_mult_1(self):
        self.mult_t_base(1, 7)

    def test_mult_1_1(self):
        self.mult_t_base(2, 1)

    def test_mult_2(self):
        self.mult_t_base(5, 4)

    def test_mult_3(self):
        self.mult_t_base(5, 2)


class TestRtlAssert(unittest.TestCase):

    class RTLSampleException(Exception):
        pass

    def setUp(self):
        pyrtl.reset_working_block()

    def bad_rtl_assert(self, *args, **kwargs):
        with self.assertRaises(pyrtl.PyrtlError):
            pyrtl.rtl_assert(*args, **kwargs)

    def test_bad_type(self):
        self.bad_rtl_assert(True, self.RTLSampleException())
        self.bad_rtl_assert(1, self.RTLSampleException())

    def test_wrong_len(self):
        w = pyrtl.Input(2)
        w2 = pyrtl.Input()

        self.bad_rtl_assert(w, self.RTLSampleException())
        self.bad_rtl_assert(w2, self.RTLSampleException())

    def test_invalid_exception_type(self):
        w = pyrtl.Input(1)

        self.bad_rtl_assert(w, 1)
        self.bad_rtl_assert(w, "")
        self.bad_rtl_assert(w, w)
        self.bad_rtl_assert(w, KeyError())

    def test_duplicate_assert(self):
        w = pyrtl.Input(1)
        pyrtl.rtl_assert(w, self.RTLSampleException())
        pyrtl.rtl_assert(w, self.RTLSampleException())

    def test_wire_from_another_block(self):
        w = pyrtl.Input(1)
        pyrtl.reset_working_block()
        self.bad_rtl_assert(w, self.RTLSampleException())

    def test_wire_outside_block(self):
        w = pyrtl.Input(1)
        block = pyrtl.working_block()
        block.wirevector_set.clear()
        self.bad_rtl_assert(w, self.RTLSampleException())

    def test_create_assert(self):
        w = pyrtl.WireVector(1)
        pyrtl.rtl_assert(w, self.RTLSampleException('testing rtl assert'))

    def test_assert_simulation(self):
        i = pyrtl.Input(1)
        o = pyrtl.rtl_assert(i, self.RTLSampleException('test assertion failed'))

        sim = pyrtl.Simulation()
        sim.step({i: 1})
        self.assertEquals(sim.inspect(o), 1)

        with self.assertRaises(self.RTLSampleException):
            sim.step({i: 0})

    def test_assert_fastsimulation(self):
        i = pyrtl.Input(1)
        o = pyrtl.rtl_assert(i, self.RTLSampleException('test assertion failed'))

        sim = pyrtl.FastSimulation()
        sim.step({i: 1})
        self.assertEquals(sim.inspect(o), 1)

        with self.assertRaises(self.RTLSampleException):
            sim.step({i: 0})


class TestLoopDetection(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def assert_no_loop(self):
        self.assertEqual(pyrtl.find_loop(), None)
        pyrtl.synthesize()
        self.assertEqual(pyrtl.find_loop(), None)
        pyrtl.optimize()
        self.assertEqual(pyrtl.find_loop(), None)

    def assert_has_loop(self):
        self.assertNotEqual(pyrtl.find_loop(), None)
        pyrtl.synthesize()
        self.assertNotEqual(pyrtl.find_loop(), None)
        pyrtl.optimize()
        self.assertNotEqual(pyrtl.find_loop(), None)

    def test_no_loop_1(self):
        ins = [pyrtl.Input(8) for i in range(8)]
        outs = [pyrtl.Output(8) for i in range(3)]
        x_1 = ins[0] & ins[1]
        x_2 = ins[3] & ins[4]
        x_3 = ins[0] | ins[4]
        x_4 = ins[6] ^ ins[7]
        x_5 = ~ ins[2]
        x_6 = ~ x_2
        x_7 = x_1 ^ x_3 & x_6
        outs[0] <<= x_4
        outs[2] <<= x_5 | x_7
        outs[1] <<= (x_1 & x_7) ^ x_3

        self.assert_no_loop()

    def test_loop_1(self):
        ins = [pyrtl.Input(8) for i in range(8)]
        outs = [pyrtl.Output(8) for i in range(3)]
        x_1 = ins[0] & ins[1]
        x_2 = ins[3] & ins[4]
        x_3 = ins[0] | ins[4]
        x_4 = ins[6] ^ ins[7]
        x_5 = ~ ins[2]
        x_6 = ~ x_2
        l_1 = pyrtl.WireVector(8)
        l_0 = x_6 & l_1
        l_1 <<= (l_0 | x_5) & x_2

        x_7 = x_1 ^ x_3 & l_0
        outs[0] <<= x_4
        outs[2] <<= x_5 | l_1
        outs[1] <<= (x_1 & x_7) ^ x_3

        self.assert_has_loop()

    def test_no_loop_special_ops(self):
        mem1 = pyrtl.MemBlock(4, 4)
        ins = [pyrtl.Input(4) for i in range(8)]
        outs = [pyrtl.Output(4) for i in range(3)]
        reg = pyrtl.Register(4)

        x_1 = ins[4] < reg
        x_2 = ins[1] * x_1
        x_3 = pyrtl.corecircuits.mux(x_1, ins[1], ins[2])
        # x_4 = pyrtl.as_wires(mem1[ins[6]])
        x_4 = mem1[ins[6]]
        x_5 = reg + ins[7]
        x_9 = pyrtl.as_wires(x_4)
        mem1[pyrtl.as_wires(x_4)] <<= x_9
        outs[0] <<= x_2 == x_1
        reg.next <<= x_5 & ins[1]
        outs[1] <<= reg
        outs[2] <<= pyrtl.corecircuits.concat(x_1, x_5[:7])

        self.assert_no_loop()

    def test_edge_case_1(self):
        in_1 = pyrtl.Input(10)
        in_2 = pyrtl.Input(9)
        fake_loop_wire = pyrtl.WireVector(1)
        comp_wire = pyrtl.corecircuits.concat(in_2[0:4], fake_loop_wire, in_2[4:9])
        r_wire = in_1 & comp_wire
        fake_loop_wire <<= r_wire[3]
        out = pyrtl.Output(10)
        out <<= fake_loop_wire

        # Yes, because we only check loops on a net level, this will still be
        # a loop pre synth
        self.assertNotEqual(pyrtl.find_loop(), None)
        pyrtl.synthesize()

        # Because synth separates the individual wires, it also resolves the loop
        self.assertEqual(pyrtl.find_loop(), None)
        pyrtl.optimize()
        self.assertEqual(pyrtl.find_loop(), None)

    def test_loop_2(self):
        in_1 = pyrtl.Input(10)
        in_2 = pyrtl.Input(9)
        fake_loop_wire = pyrtl.WireVector(1)
        # Note the slight difference from the last test case on the next line
        comp_wire = pyrtl.corecircuits.concat(in_2[0:6], fake_loop_wire, in_2[6:9])
        r_wire = in_1 & comp_wire
        fake_loop_wire <<= r_wire[3]
        out = pyrtl.Output(10)
        out <<= fake_loop_wire

        # It causes there to be a real loop
        self.assert_has_loop()

    def test_no_loop_reg_1(self):
        reg = pyrtl.Register(8)
        in_w = pyrtl.Input(8)
        res = reg + in_w
        reg.next <<= res
        self.assert_no_loop()
