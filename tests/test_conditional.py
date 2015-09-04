import unittest
import random
import pyrtl
import StringIO

from helperfunctions import testmissing

# ---------------------------------------------------------------

class TestConditionalUpdateRemoved(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_old_conditionupdate_provides_notice(self):
        c = pyrtl.Const(1)
        r = pyrtl.Register(bitwidth=2, name='r')
        with self.assertRaises(pyrtl.PyrtlError):
            with pyrtl.ConditionalUpdate() as condition:
                with condition(c):
                    r.next |= r + 1

    def test_old_shortcut_form_of_conditionalupdate_provides_notice(self):
        c = pyrtl.Const(1)
        r = pyrtl.Register(bitwidth=2, name='r')
        with self.assertRaises(pyrtl.PyrtlError):
            with pyrtl.ConditionalUpdate(c):
                r.next |= r + 1


class TestConditional(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in xrange(8):
            sim.step({})
        output = StringIO.StringIO()
        sim_trace.print_trace(output)
        print output.getvalue()
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

    def test_two_seperate_conditions(self):
        c = pyrtl.Const(1)
        i = pyrtl.Register(bitwidth=2, name='i')
        r = pyrtl.Register(bitwidth=2, name='r')
        with pyrtl.conditional_assignment:
            with c:
                i.next |= i + 1
        with pyrtl.conditional_assignment:
            with i==2:
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
 
 
    def test_error_on_unconditioned_update_in_under_conditional(self):
        with self.assertRaises(pyrtl.PyrtlError):
            c = pyrtl.Const(1)
            i = pyrtl.Register(bitwidth=2, name='i')
            with pyrtl.conditional_assignment:
                i.next |= i + 1
                with c:
                    i.next |= 2

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
                    r.next |= r + 1

# ---------------------------------------------------------------


class TestMemConditionalBlock(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in xrange(8):
            sim.step({})
        output = StringIO.StringIO()
        sim_trace.print_trace(output)
        print output.getvalue()
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

    def test_basic_true_condition_memwrite(self):
        m = pyrtl.MemBlock(addrwidth=2, bitwidth=2, name='m')
        i = pyrtl.Register(bitwidth=2, name='i')
        o = pyrtl.WireVector(bitwidth=2, name='o')
        i.next <<= i + 1
        with pyrtl.conditional_assignment:
            with m[i]:
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

# ---------------------------------------------------------------


class TestWireConditionalBlock(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def check_trace(self, correct_string):
        sim_trace = pyrtl.SimulationTrace()
        sim = pyrtl.Simulation(tracer=sim_trace)
        for i in xrange(8):
            sim.step({})
        output = StringIO.StringIO()
        sim_trace.print_trace(output)
        print output.getvalue()
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
            with i[0] == True:
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
        with self.assertRaises(pyrtl.PyrtlError):
            i = pyrtl.Register(bitwidth=2, name='i')
            o = pyrtl.WireVector(bitwidth=2, name='o')
            i.next <<= i + 1
            with pyrtl.conditional_assignment:
                with i <= 2:
                    with i == 0:
                        o |= 2
                    with i == 1:
                        o |= 1
                with pyrtl.conditional_assignment:
                    o |= 0

    def test_condition_nice_error_message(self):
        with self.assertRaises(pyrtl.PyrtlError):
            i = pyrtl.Register(bitwidth=2, name='i')
            o = pyrtl.WireVector(bitwidth=2, name='o')
            i.next <<= i + 1
            with i <= 2:
                o |= 1

    def test_condition_error_when_assigned_wire_has_unspecified_bitwidth(self):
        with self.assertRaises(pyrtl.PyrtlError):
            i = pyrtl.Register(bitwidth=2, name='i')
            o = pyrtl.WireVector(name='o')
            i.next <<= i + 1
            with pyrtl.conditional_assignment:
                with i <= 2:
                    o |= 1
                with pyrtl.otherwise:
                    o |= 0

if __name__ == "__main__":
    unittest.main()
