import unittest
import pyrtl

from .helperfunctions import *


class TestWireVector(unittest.TestCase):
    def setUp(self):
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

    def test_zero_extend(self):
        testmissing()

    def test_sign_extend(self):
        testmissing()

    def test_truncating(self):
        testmissing()


class TestWireVectorFail(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_undef_wirevector_length(self):
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector()
            y = len(x)

    def test_bad_bitwidth(self):
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth='happy')
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth=-1)
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth=0)

    def test_no_immed_operators(self):
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth=3)
            x &= 2
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth=3)
            x ^= 2
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth=3)
            x += 2
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth=3)
            x -= 2
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth=3)
            x *= 2

    def test_sign_and_zero_extend_only_increase_bitwidth(self):
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth=3)
            x.zero_extended(2)


class TestWirevectorSlicing(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def invalid_empty_slice(self, bitwidth, slice):
        w = pyrtl.Input(bitwidth)
        with self.assertRaises(pyrtl.PyrtlError):
            x = w[slice]

    def invalid_slice_index(self, bitwidth, slice):
        w = pyrtl.Input(bitwidth)
        with self.assertRaises(IndexError):
            x = w[slice]

    def valid_slice(self, bitwidth, slice):
        w = pyrtl.Input(bitwidth)
        x = w[slice]

    def test_wire_wo_bitwidth_fails(self):
        w = pyrtl.WireVector()
        with self.assertRaises(pyrtl.PyrtlError):
            x = w[2]

    def test_valid_indicies(self):
        self.valid_slice(4, 2)
        self.valid_slice(4, 0)
        self.valid_slice(4, -1)
        pyrtl.working_block().sanity_check()

    def test_valid_slices(self):
        self.valid_slice(8, slice(6))
        self.valid_slice(8, slice(1, 4))
        self.valid_slice(8, slice(1, 8))  # Yes, supplying a end index out of bounds is valid python
        self.valid_slice(8, slice(1, 2, 2))
        self.valid_slice(8, slice(1, 4, 2))
        self.valid_slice(8, slice(7, 1, -2))
        self.valid_slice(8, slice(-2))
        self.valid_slice(8, slice(-6, -2, 3))
        pyrtl.working_block().sanity_check()

    def test_invalid_indicies(self):
        self.invalid_slice_index(4, 5)
        self.invalid_slice_index(4, -5)

    def test_invalid_slices(self):
        self.invalid_empty_slice(8, slice(1, 1))
        self.invalid_empty_slice(8, slice(7, 1))
        self.invalid_empty_slice(8, slice(-1, 1, 2))


class TestInput(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_no_assignment_to_inputs(self):
        x = pyrtl.WireVector(1)
        y = pyrtl.Input(1)
        with self.assertRaises(pyrtl.PyrtlError):
            y <<= x


class TestRegister(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.r = pyrtl.Register(bitwidth=3)

    def test_assignment_small(self):
        self.r.next <<= pyrtl.Const(1, bitwidth=3)

    def test_assignment_unspec_width(self):
        self.r.next <<= pyrtl.Const(1)

    def test_assignment_raw(self):
        self.r.next <<= 1

    def test_assignment_large(self):
        self.r.next <<= pyrtl.Const(202)

    def test_register_assignment_direct(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.r.next = 1

    def test_logic_operations(self):
        with self.assertRaises(pyrtl.PyrtlError):
            a = (self.r or True)

    def test_register_assignment_not_next(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.r <<= 1

    def test_assign_next(self):
        w = pyrtl.WireVector(bitwidth=1)
        with self.assertRaises(pyrtl.PyrtlError):
            w <<= self.r.next

    def test_next_logic_operations(self):
        with self.assertRaises(pyrtl.PyrtlError):
            a = (self.r.next or True)


# -------------------------------------------------------------------
class TestConst(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_integers(self):
        self.check_const(1, 1, 1)
        self.check_const(5, 5, 3)
        self.check_const(1, 1, 5, bitwidth=5)

    def test_neg_integers(self):
        self.check_const(-1, 0b11111, 5, bitwidth=5)
        self.check_const(-2, 0b110, 3, bitwidth=3)
        self.check_const(-5, 0b1011, 4, bitwidth=4)

    def test_too_big(self):
        self.assert_bad_const(5, 2)

    def test_invalid_bitwidth(self):
        self.assert_bad_const(1, 0)
        self.assert_bad_const(1, -1)

    def test_bad_neg_integers(self):
        # check that bitwidth is required
        self.assert_bad_const(-4)
        self.assert_bad_const(-4, 2)

    def test_string(self):
        self.check_const("1'1", 1, 1)
        self.check_const("5'3", 3, 5)
        self.check_const("5'b11", 3, 5)
        self.check_const("16'xff", 0xff, 16)
        self.check_const("17'xff", 0xff, 17)
        self.check_const("5'b011", 3, 5)

    def test_bad_string(self):
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
    def test_badstring_broken(self):
        self.assert_bad_const("1'")

    def test_bool(self):
        testmissing()

    def test_badbool(self):
        testmissing()

    def test_badtype(self):
        self.assert_bad_const(pyrtl.Const(123))
        self.assert_bad_const([])

    def test_assignment(self):
        with self.assertRaises(pyrtl.PyrtlError):
            c = pyrtl.Const(4)
            c <<= 3

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


class TestKeepingCallStack(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    @classmethod
    def tearDownClass(cls):
        pyrtl.set_debug_mode(False)

    def test_no_call_stack(self):
        pyrtl.set_debug_mode(False)
        wire = pyrtl.WireVector()
        with self.assertRaises(AttributeError):
            call_stack = wire.init_call_stack

    def test_get_call_stack(self):
        pyrtl.set_debug_mode(True)
        wire = pyrtl.WireVector()
        call_stack = wire.init_call_stack
        self.assertIsInstance(call_stack, list)
