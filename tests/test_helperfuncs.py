import unittest
import pyrtl
import io

# ---------------------------------------------------------------


class TestAnyAll(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output)
        print(output.getvalue())
        self.assertEqual(output.getvalue(), correct_string)

    def test_any_only_on_1_bit_vectors(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.rtl_any(a, b)

    def test_all_only_on_1_bit_vectors(self):
        a = pyrtl.WireVector(name='a', bitwidth=1)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.rtl_all(a, b, c)

    def test_any_works_with_consts(self):
        a = pyrtl.WireVector(name='a', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        r = pyrtl.rtl_any(a, 1, c)

    def test_all_works_with_consts(self):
        a = pyrtl.WireVector(name='a', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        r = pyrtl.rtl_all(a, 1, c)

    def test_any_does_simulation_correct(self):
        r = pyrtl.Register(3, 'r')
        r.next <<= r + 1
        a, b, c = r[0], r[1], r[2]
        o = pyrtl.Output(name='o')
        o <<= pyrtl.rtl_any(a, b, c)
        self.check_trace('o 01111111\nr 01234567\n')

    def test_all_does_simulation_correct(self):
        r = pyrtl.Register(3, 'r')
        r.next <<= r + 1
        a, b, c = r[0], r[1], r[2]
        o = pyrtl.Output(name='o')
        o <<= pyrtl.rtl_all(a, b, c)
        self.check_trace('o 00000001\nr 01234567\n')


class TestMux(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in range(8):
            sim.step({})
        output = io.StringIO()
        sim_trace.print_trace(output)
        print(output.getvalue())
        self.assertEqual(output.getvalue(), correct_string)

    def test_mux_too_many_inputs(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=1)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.mux(s, a, b, c)

    def test_mux_not_enough_inputs(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.mux(s, a, b, c)

    def test_mux_not_enough_inputs_but_default(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        r = pyrtl.mux(s, a, b, default=0)

    def test_mux_enough_inputs_with_default(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        d = pyrtl.WireVector(name='d', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        r = pyrtl.mux(s, a, b, c, d, default=0)

    def test_mux_too_many_inputs_with_default(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        c = pyrtl.WireVector(name='c', bitwidth=1)
        d = pyrtl.WireVector(name='d', bitwidth=1)
        e = pyrtl.WireVector(name='e', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.mux(s, a, b, c, d, e, default=0)

    def test_mux_too_many_inputs_with_default(self):
        a = pyrtl.WireVector(name='a', bitwidth=3)
        b = pyrtl.WireVector(name='b', bitwidth=1)
        s = pyrtl.WireVector(name='s', bitwidth=2)
        with self.assertRaises(pyrtl.PyrtlError):
            r = pyrtl.mux(s, a, b, default=0, foo=1)


class TestLoopDetection(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
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

    def test_edge_case_1(self):
        in_1 = pyrtl.Input(10)
        in_2 = pyrtl.Input(9)
        fake_loop_wire = pyrtl.WireVector(1)
        comp_wire = pyrtl.concat(in_2[0:4], fake_loop_wire, in_2[4:9])
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
        comp_wire = pyrtl.concat(in_2[0:6], fake_loop_wire, in_2[6:9])
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
