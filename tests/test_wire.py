import unittest
import pyrtl

from .helperfunctions import *


class TestWireVector(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def tearDown(self):
        pyrtl.reset_working_block()

    def test_basic_assignment(self):
        x = pyrtl.WireVector(1)
        y = pyrtl.WireVector(1)
        y <<= x

    def test_unset_bitwidth(self):
        x = pyrtl.Input()
        y = pyrtl.WireVector(1)
        with self.assertRaises(pyrtl.PyrtlError):
            y <<= x

    def test_assign_to_value(self):
        x = pyrtl.WireVector(1)
        y = 1337
        with self.assertRaises(TypeError):
            y <<= x

    def test_slice(self):
        testmissing()

    def test_zero_extend(self):
        testmissing()

    def test_sign_extend(self):
        testmissing()

    def test_truncating(self):
        testmissing()


class TestInput(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_assignment(self):
        x = pyrtl.WireVector(1)
        y = pyrtl.Input(1)
        with self.assertRaises(pyrtl.PyrtlError):
            y <<= x


class TestRegister(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_assignment_small(self):
        c = pyrtl.Register(bitwidth=3)
        c.next <<= pyrtl.Const(1, bitwidth=3)

    def test_assignment_unspec_width(self):
        c = pyrtl.Register(bitwidth=3)
        c.next <<= pyrtl.Const(1)

    def test_assignment_raw(self):
        c = pyrtl.Register(bitwidth=3)
        c.next <<= 1

    def test_assignment_large(self):
        c = pyrtl.Register(bitwidth=3)
        c.next <<= pyrtl.Const(202)

    def test_register_assignment_direct(self):
        c = pyrtl.Register(bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            c.next = 1

    def test_register_assignment_not_next(self):
        c = pyrtl.Register(bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            c <<= 1

    def test_logic_operations(self):
        c = pyrtl.Register(bitwidth=1)
        with self.assertRaises(pyrtl.PyrtlError):
            c.next <<= c or True


# -------------------------------------------------------------------
class TestConst(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_const_integers(self):
        self.check_const(1, 1, 1)
        self.check_const(5, 5, 3)
        self.check_const(1, 1, 5, bitwidth=5)

    def test_const_neg_integers(self):
        self.check_const(-1, 0b11111, 5, bitwidth=5)
        self.check_const(-2, 0b110, 3, bitwidth=3)
        self.check_const(-5, 0b1011, 4, bitwidth=4)

    def test_const_too_big(self):
        self.assert_bad_const(5, 2)

    def test_invalid_bitwidth(self):
        self.assert_bad_const(1, 0)
        self.assert_bad_const(1, -1)

    def test_const_bad_neg_integers(self):
        # check that bitwidth is required
        self.assert_bad_const(-4)
        self.assert_bad_const(-4, 2)

    def test_const_string(self):
        self.check_const("1'1", 1, 1)
        self.check_const("5'3", 3, 5)
        self.check_const("5'b11", 3, 5)
        self.check_const("16'xff", 0xff, 16)
        self.check_const("17'xff", 0xff, 17)
        self.check_const("5'b011", 3, 5)

    def test_const_badstring(self):
        self.assert_bad_const("1")
        self.assert_bad_const("-1")
        self.assert_bad_const("1bx")
        self.assert_bad_const("1ba")
        self.assert_bad_const("1'bx")
        self.assert_bad_const("1'ba")
        self.assert_bad_const("1'b10")
        self.assert_bad_const("1'-b10")
        self.assert_bad_const("-1'b10")
        self.assert_bad_const("5'b111111'")
        self.assert_bad_const("'")
        self.assert_bad_const("'1")

    @unittest.skip
    def test_const_badstring_broken(self):
        self.assert_bad_const("1'")

    def test_const_bool(self):
        testmissing()

    def test_const_badbool(self):
        testmissing()

    def test_const_badtype(self):
        self.assert_bad_const(pyrtl.Const(123))
        self.assert_bad_const([])

    def test_const_assignment(self):
        testmissing()

    def check_const(self, val_in, expected_val, expected_bitwidth, **kargs):
        c = pyrtl.Const(val_in, **kargs)
        self.assertEqual(c.val, expected_val)
        self.assertEqual(c.bitwidth, expected_bitwidth)

    def assert_bad_const(self, *args, **kwargs):
        with self.assertRaises(pyrtl.PyrtlError):
            c = pyrtl.Const(*args, **kwargs)


class TestOutput(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    @unittest.skip  # this is not expected to pass
    def test_assign_output(self):
        o = pyrtl.Output(1)
        w = pyrtl.WireVector(1)
        with self.assertRaises(pyrtl.PyrtlError):
            w <<= o


# -------------------------------------------------------------------
class TestRTLAdderDesign(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_complete_adders(self):
        for bitwidth in range(9, 10):
            r = pyrtl.Register(bitwidth=bitwidth, name='r')
            const_one = pyrtl.Const(1)
            addby = const_one.zero_extended(bitwidth)
            sum, cout = generate_full_adder(r, addby)
            r.next <<= sum

            self.assertTrue(isinstance(r, pyrtl.Register))
            self.assertTrue(isinstance(cout, pyrtl.WireVector))
            pyrtl.reset_working_block()
