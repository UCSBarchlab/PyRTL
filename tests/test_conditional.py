import unittest
import pyrtl
import io


class TestConditional(unittest.TestCase):
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

    def test_basic_true_condition(self):
        c = pyrtl.Const(1)
        r = pyrtl.Register(bitwidth=2, name='r')
        with pyrtl.conditional_assignment:
            with c:
                r.next |= r + 1
        self.check_trace('r 01230123\n')

    def test_short_true_condition(self):
        c = pyrtl.Const(1)
        r = pyrtl.Register(bitwidth=2, name='r')
        with pyrtl.conditional_assignment:
            with c:
                r.next |= r + 1
        self.check_trace('r 01230123\n')

    def test_basic_false_condition(self):
        c = pyrtl.Const(0)
        r = pyrtl.Register(bitwidth=2, name='r')
        with pyrtl.conditional_assignment:
            with c:
                r.next |= r + 1
        self.check_trace('r 00000000\n')

    def test_basic_simple_condition_1(self):
        r = pyrtl.Register(bitwidth=2, name='r')
        with pyrtl.conditional_assignment:
            with r < 2:
                r.next |= r + 1
        self.check_trace('r 01222222\n')

    def test_two_seperate_conditions(self):
        c = pyrtl.Const(1)
        i = pyrtl.Register(bitwidth=2, name='i')
        r = pyrtl.Register(bitwidth=2, name='r')
        with pyrtl.conditional_assignment:
            with c:
                i.next |= i + 1
        with pyrtl.conditional_assignment:
            with i == 2:
                r.next |= r + 1
        self.check_trace('i 01230123\nr 00011112\n')

    def test_basic_two_conditions(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        i.next <<= i + 1
        r = pyrtl.Register(bitwidth=2, name='r')
        with pyrtl.conditional_assignment:
            with i == 2:
                r.next |= r + 1
            with i == 3:
                r.next |= r - 1
        self.check_trace('i 01230123\nr 00010001\n')

    def test_basic_default_condition(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        i.next <<= i + 1
        r = pyrtl.Register(bitwidth=2, name='r')
        with pyrtl.conditional_assignment:
            with i == 2:
                r.next |= r
            with i == 3:
                r.next |= r - 1
            with pyrtl.otherwise:
                r.next |= r + 1
        self.check_trace('i 01230123\nr 01221233\n')

    def test_basic_nested_condition(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        i.next <<= i + 1
        r = pyrtl.Register(bitwidth=3, name='r')
        with pyrtl.conditional_assignment:
            with (i == 2) | (i == 3):
                with r < 3:
                    r.next |= r + 2
                with pyrtl.otherwise:
                    r.next |= r + 1
        self.check_trace('i 01230123\nr 00024445\n')

    def test_nested_under_default_condition(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        i.next <<= i + 1
        r = pyrtl.Register(bitwidth=3, name='r')
        with pyrtl.conditional_assignment:
            with i < 2:
                r.next |= r + 2
            with pyrtl.otherwise:
                with r < 6:
                    r.next |= r - 1
        self.check_trace('i 01230123\nr 02432466\n')

    def test_two_signals_under_default_condition(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        i.next <<= i + 1
        r1 = pyrtl.Register(bitwidth=3, name='r1')
        r2 = pyrtl.Register(bitwidth=3, name='r2')
        with pyrtl.conditional_assignment:
            with i < 2:
                r1.next |= r1 + 1
            with i < 3:
                r2.next |= r2 + 1
            with pyrtl.otherwise:
                r2.next |= 3
        self.check_trace(' i 01230123\nr1 01222344\nr2 00013334\n')

    def test_default_value_for_wires(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        i.next <<= i + 1
        r1 = pyrtl.Register(bitwidth=3, name='r1')
        r2 = pyrtl.Register(bitwidth=3, name='r2')
        r3 = pyrtl.Register(bitwidth=3, name='r3')
        o = pyrtl.Output(bitwidth=3, name='o')
        with pyrtl.conditional_assignment(
            defaults={
                r1: r1 + 2,
                r2: 6,
                o: 3
            }
        ):
            with i < 2:
                r1.next |= r1 + 1
                # r2 will be updated to 6
                # r3 remains the same as previous cycle
                o |= i
            with i < 3:
                # r1 will be updated to r1 + 2
                r2.next |= r2 + 1
                # r3 remains the same as previous cycle
                # o will be updated to 3
            with pyrtl.otherwise:
                # r1 will be updated to r1 + 2
                # r2 will be updated to 6
                r3.next |= 2
                o |= 7
        self.check_trace(
            ' i 01230123\n'
            ' o 01370137\n'
            'r1 01246702\n'
            'r2 06676667\n'
            'r3 00002222\n'
        )

    def test_error_on_unconditioned_update_in_under_conditional(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        with pyrtl.conditional_assignment:
            with self.assertRaises(pyrtl.PyrtlError):
                i.next |= i + 1

    def test_error_on_conditional_assignment_not_under_conditional(self):
        c = pyrtl.Const(1)
        o = pyrtl.Register(bitwidth=2, name='i')
        with self.assertRaises(pyrtl.PyrtlError):
            o |= c

    def test_error_on_non_boolean(self):
        c = pyrtl.Const(2)
        r = pyrtl.Register(bitwidth=2, name='r')
        with self.assertRaises(pyrtl.PyrtlError):
            with pyrtl.conditional_assignment:
                with c:
                    pass

    def test_error_on_non_boolean_with_register(self):
        r = pyrtl.Register(bitwidth=4, name='r')
        with self.assertRaises(pyrtl.PyrtlError):
            with pyrtl.conditional_assignment:
                with r:
                    pass


# ---------------------------------------------------------------


class TestMemConditionalBlock(unittest.TestCase):
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

    def test_basic_true_condition_memwrite(self):
        m = pyrtl.MemBlock(addrwidth=2, bitwidth=2, name='m')
        i = pyrtl.Register(bitwidth=2, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        with pyrtl.conditional_assignment:
            with i <= 2:
                m[i] |= i
        o <<= m[i]
        self.check_trace('i 01230123\no 00000120\n')

    def test_basic_true_condition_memwrite_2(self):
        m = pyrtl.MemBlock(addrwidth=2, bitwidth=2, name='m')
        i = pyrtl.Register(bitwidth=2, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        with pyrtl.conditional_assignment:
            with m[i] != 0:
                m[i] <<= i
        o <<= m[i]
        self.check_trace('i 01230123\no 00000123\n')

    def test_basic_true_condition_memread(self):
        m = pyrtl.MemBlock(addrwidth=2, bitwidth=3, name='m')
        i = pyrtl.Register(bitwidth=3, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        addr = i[0:2]
        with pyrtl.conditional_assignment:
            with i < 4:
                m[addr] |= i
            with pyrtl.otherwise:
                with addr[0]:
                    # this should happen every time because no
                    # state is being updated!
                    o <<= m[addr]
        self.check_trace('i 01234567\no 00000123\n')

    def test_true_multi_condition_memread(self):
        m = pyrtl.MemBlock(addrwidth=2, bitwidth=3, name='m')
        i = pyrtl.Register(bitwidth=3, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        addr = i[0:2]
        with pyrtl.conditional_assignment:
            with i < 2:
                m[addr] |= i
            with (2 <= i) & (i < 4):
                m[addr] |= (i + 1)[:3]
            with pyrtl.otherwise:
                with addr[0]:
                    # this should happen every time because no
                    # state is being updated!
                    o <<= m[addr]
        self.check_trace('i 01234567\no 00000130\n')

# ---------------------------------------------------------------


class TestWireConditionalBlock(unittest.TestCase):
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

    def test_basic_condition_wire(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        with pyrtl.conditional_assignment:
            with i <= 2:
                o |= 1
            with pyrtl.otherwise:
                o |= 0
        self.check_trace('i 01230123\no 11101110\n')

    def test_boolean_assignment_condition_wire(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        with pyrtl.conditional_assignment:
            with i[0]:
                o |= 1
            with pyrtl.otherwise:
                o |= 0
        self.check_trace('i 01230123\no 01010101\n')

    def test_nested_condition_wire(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        with pyrtl.conditional_assignment:
            with i <= 2:
                with i == 0:
                    o |= 2
                with pyrtl.otherwise:
                    o |= 1
            with pyrtl.otherwise:
                o |= 0
        self.check_trace('i 01230123\no 21102110\n')

    def test_underspecified_condition_wire(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        with pyrtl.conditional_assignment:
            with i <= 2:
                o |= 1
            # default to zero
        self.check_trace('i 01230123\no 11101110\n')

    def test_condition_wire(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        with pyrtl.conditional_assignment:
            with i <= 2:
                o |= 1
        self.check_trace('i 01230123\no 11101110\n')

    def test_condition_nice_error_message_nested(self):
        with pyrtl.conditional_assignment:
            with self.assertRaises(pyrtl.PyrtlError):
                with pyrtl.conditional_assignment:
                    pass

    def test_condition_nice_error_message_nested2(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        with pyrtl.conditional_assignment:
            with i <= 2:
                with self.assertRaises(pyrtl.PyrtlError):
                    with pyrtl.conditional_assignment:
                        pass

    def test_condition_nice_error_message(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        with self.assertRaises(pyrtl.PyrtlError):
            with i <= 2:
                pass

    def test_condition_error_when_assigned_wire_has_unspecified_bitwidth(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        o = pyrtl.WireVector(name='o')
        with pyrtl.conditional_assignment:
            with i <= 2:
                with self.assertRaises(pyrtl.PyrtlError):
                    o |= 1

    def test_error_condition_connect_input(self):
        i = pyrtl.Input(bitwidth=2, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        with pyrtl.conditional_assignment:
            with i <= 2:
                with self.assertRaises(pyrtl.PyrtlError):
                    i |= o

    def test_error_condition_connect_const(self):
        i = pyrtl.Const(3, 2)
        o = pyrtl.WireVector(bitwidth=2, name='o')
        with pyrtl.conditional_assignment:
            with i <= 2:
                with self.assertRaises(pyrtl.PyrtlError):
                    i |= o


# ---------------------------------------------------------------

class TestNonExclusiveBlocks(unittest.TestCase):
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
        sim_trace.print_trace(output, compact=True)
        self.assertEqual(output.getvalue(), correct_string)

    def test_basic_nested_non_exclusive_condition(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        i.next <<= i + 1
        r1 = pyrtl.Register(bitwidth=3, name='r1')
        r2 = pyrtl.Register(bitwidth=3, name='r2')
        with pyrtl.conditional_assignment:
            with r1 < 3:
                r1.next |= r1 + 1
            with pyrtl.otherwise:
                pass
            with r2 < 3:
                r2.next |= r2 + 1
        self.check_trace(' i 01230123\nr1 01233333\nr2 01233333\n')

    def test_one_deep_nested_non_exclusive_condition(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        i.next <<= i + 1
        r1 = pyrtl.Register(bitwidth=3, name='r1')
        r2 = pyrtl.Register(bitwidth=3, name='r2')
        with pyrtl.conditional_assignment:
            with (i == 2) | (i == 3):
                with r1 < 3:
                    r1.next |= r1 + 2
                with pyrtl.otherwise:
                    pass
                with r2 < 3:
                    r2.next |= r2 + 2
        self.check_trace(' i 01230123\nr1 00024444\nr2 00024444\n')

    def test_overlaping_assignments_in_non_exclusive_assignments(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        i.next <<= i + 1
        r1 = pyrtl.Register(bitwidth=3, name='r1')
        r2 = pyrtl.Register(bitwidth=3, name='r2')
        with pyrtl.conditional_assignment:
            with r1 < 3:
                r1.next |= r1 + 1
            with pyrtl.otherwise:
                pass
            with r2 < 3:
                with self.assertRaises(pyrtl.PyrtlError):
                    r1.next |= r2 + 1

    def test_other_overlaping_assignments_in_non_exclusive_assignments(self):
        i = pyrtl.Register(bitwidth=2, name='i')
        i.next <<= i + 1
        r1 = pyrtl.Register(bitwidth=3, name='r1')
        r2 = pyrtl.Register(bitwidth=3, name='r2')
        with pyrtl.conditional_assignment:
            with r1 < 3:
                r1.next |= r1 + 1
            with pyrtl.otherwise:
                pass
            with r2 < 3:
                with i != 0:
                    with self.assertRaises(pyrtl.PyrtlError):
                        r1.next |= r2 + 1

# ---------------------------------------------------------------


class TestSuperWireConditionalBlock(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_super_stress_test(self):
        allin = [pyrtl.Input(1, n) for n in 'abxyijkmzcd']
        a, b, x, y, i, j, k, m, z, c, d = allin
        allout = [pyrtl.Output(4, 'var' + str(index)) for index in range(5)]
        var0, var1, var2, var3, var4 = allout

        """
         1  with a:  # a
         2  with b:  # not(a) and b
         3      with x:  # not(a) and b and x
         4      with otherwise:  # not(a) and b and not(x)
         5      with y:  # not(a) and b and y;  check(3,4)
         6          with i:  # not(a) and b and y and i;  check(3,4)
         7          with j:  # not(a) and b and y and not(i) and j;  check(3,4)
         8          with otherwise:  # not(a) and b and y and not(i) and not(j):  check(3,4)
         9          with k:  # not(a) and b and y and k;  check(3,4,6,7,8)
         8          with otherwise:  # not(a) and b and y and not(k):  check(?)
        10          with m:  # not(a) and b and y and m;  check(?)
        11  with otherwise:  #not(a) and not(b)
        12      with z: #not(a) and not(b) and z
        13  with c:  #c;  check(1,2,3,4,5,6,7,8,9,10,11,12)
        14  with d:  #not(c) and d;  check(1,2,3,4,5,6,7,8,9,10,11,12)
        """

        with pyrtl.conditional_assignment:
            with a:
                var0 |= 1
            with b:
                with x:
                    var0 |= 2
                with pyrtl.otherwise:
                    var0 |= 3

                with y:
                    with i:
                        var1 |= 1
                    with j:
                        var1 |= 2
                    with pyrtl.otherwise:
                        var1 |= 3

                    with k:
                        var2 |= 1
                    with pyrtl.otherwise:
                        var2 |= 2

                    with m:
                        var3 |= 3

            with pyrtl.otherwise:
                with z:
                    var0 |= 4

            with c:
                var4 |= 1
            with d:
                var4 |= 2

        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.FastSimulation(tracer=sim_trace)
        for cycle in range(2 ** len(allin)):
            inputs = {v: 0x1 & (cycle >> i) for i, v in enumerate(allin[::-1])}
            sim.step(inputs)

        for cycle in range(len(sim_trace)):
            t0, t1, t2, t3, t4 = 0, 0, 0, 0, 0

            def v(var):
                return sim_trace.trace[var][cycle]

            if v(a):
                t0 = 1
            elif v(b):
                if v(x):
                    t0 = 2
                else:
                    t0 = 3
                if v(y):
                    if v(i):
                        t1 = 1
                    elif v(j):
                        t1 = 2
                    else:
                        t1 = 3
                    if v(k):
                        t2 = 1
                    else:
                        t2 = 2
                    if v(m):
                        t3 = 3
            else:
                if v(z):
                    t0 = 4
            if v(c):
                t4 = 1
            elif v(d):
                t4 = 2
            self.assertEqual(v(var0), t0)
            self.assertEqual(v(var1), t1)
            self.assertEqual(v(var2), t2)
            self.assertEqual(v(var3), t3)
            self.assertEqual(v(var4), t4)


if __name__ == "__main__":
    unittest.main()
