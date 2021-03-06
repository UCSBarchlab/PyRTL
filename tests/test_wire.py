import unittest
import six
import pyrtl
from pyrtl import wire


class TestWireVector(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_wirevector_length(self):
        x = pyrtl.WireVector(1)
        y = pyrtl.WireVector(13)
        self.assertEqual(len(x), 1)
        self.assertEqual(len(y), 13)

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
        pass

    def test_sign_extend(self):
        pass

    def test_truncating(self):
        pass

    def test_rename(self):
        block = pyrtl.working_block()
        w = pyrtl.WireVector(1, "test1")
        self.assertIn("test1", block.wirevector_by_name)
        self.assertIn(w, block.wirevector_set)
        w.name = "testJohn"
        self.assertNotIn("test1", block.wirevector_by_name)
        self.assertIn("testJohn", block.wirevector_by_name)
        self.assertIn(w, block.wirevector_set)


class TestWireVectorNames(unittest.TestCase):
    def is_valid_str(self, s):
        return wire.next_tempvar_name(s) == s

    def test_invalid_name(self):
        self.assertFalse(self.is_valid_str(''))
        with self.assertRaises(pyrtl.PyrtlError):
            self.is_valid_str('clock')

    def test_valid_names(self):
        self.assertTrue(self.is_valid_str('xxx'))
        self.assertTrue(self.is_valid_str('h'))
        self.assertTrue(self.is_valid_str(' '))
        self.assertTrue(self.is_valid_str('#$)(*&#@_+!#)('))


class TestWireVectorFail(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_undef_wirevector_length(self):
        x = pyrtl.WireVector()
        with self.assertRaises(pyrtl.PyrtlError):
            y = len(x)

    def test_bad_bitwidth(self):
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth='happy')
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth=-1)
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(bitwidth=0)
        y = pyrtl.WireVector(1)
        with self.assertRaises(pyrtl.PyrtlError):
            x = pyrtl.WireVector(y)

    def test_no_immed_operators(self):
        x = pyrtl.WireVector(bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            x &= 2
        with self.assertRaises(pyrtl.PyrtlError):
            x ^= 2
        with self.assertRaises(pyrtl.PyrtlError):
            x += 2
        with self.assertRaises(pyrtl.PyrtlError):
            x -= 2
        with self.assertRaises(pyrtl.PyrtlError):
            x *= 2

    def test_sign_and_zero_extend_only_increase_bitwidth(self):
        x = pyrtl.WireVector(bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            x.zero_extended(2)

    def test_truncate_only_reduces_bitwidth(self):
        x = pyrtl.WireVector(bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            x.truncate(5)

    def test_truncate_only_takes_integers(self):
        x = pyrtl.WireVector(bitwidth=3)
        y = pyrtl.WireVector(bitwidth=3)
        with self.assertRaises(pyrtl.PyrtlError):
            x.truncate(y)


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
        with self.assertRaises(pyrtl.PyrtlError):
            x = w[3:5]

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

    def test_no_connection_to_inputs(self):
        x = pyrtl.WireVector(1)
        y = pyrtl.Input(1)
        with self.assertRaises(pyrtl.PyrtlError):
            y <<= x


class TestRegister(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()
        self.r = pyrtl.Register(bitwidth=3)

    def test_connection_small(self):
        self.r.next <<= pyrtl.Const(1, bitwidth=3)

    def test_connection_unspec_width(self):
        self.r.next <<= pyrtl.Const(1)

    def test_connection_raw(self):
        self.r.next <<= 1

    def test_connection_large(self):
        self.r.next <<= pyrtl.Const(202)

    def test_register_assignment(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.r.next = 1

    def test_logic_operations(self):
        with self.assertRaises(pyrtl.PyrtlError):
            a = (self.r or True)

    def test_register_assignment_not_next(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.r <<= 1

    @unittest.skip("I don't think this is fixable")
    def test_assign_next(self):
        # I really don't know how we can fix this - John
        w = pyrtl.WireVector(bitwidth=1)
        with self.assertRaises(pyrtl.PyrtlError):
            a = self.r.next

    def test_connect_next(self):
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
        self.check_const(0, 0b0, 1)
        self.check_const(0, 0b0, 1, signed=True)
        self.check_const(1, 0b01, 2, signed=True)
        self.check_const(2, 0b010, 3, signed=True)
        self.check_const(3, 0b011, 3, signed=True)
        self.check_const(4, 0b0100, 4, signed=True)
        self.check_const(5, 0b0101, 4, signed=True)

    def test_neg_integers(self):
        self.check_const(-1, 0b11111, 5, bitwidth=5)
        self.check_const(-2, 0b110, 3, bitwidth=3)
        self.check_const(-5, 0b1011, 4, bitwidth=4)
        self.check_const(-1, 0b1, 1, signed=True)
        self.check_const(-2, 0b10, 2, signed=True)
        self.check_const(-3, 0b101, 3, signed=True)
        self.check_const(-4, 0b100, 3, signed=True)
        self.check_const(-5, 0b1011, 4, signed=True)

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
        self.check_const("-5'b11", 29, 5)
        self.check_const("16'xff", 0xff, 16)
        self.check_const("17'xff", 0xff, 17)
        self.check_const("16'hff", 0xff, 16)
        self.check_const("17'hff", 0xff, 17)
        self.check_const("5'b011", 3, 5)
        self.check_const("5'b0_11", 3, 5)
        self.check_const("5'02_1", 21, 5)
        self.check_const("16'HFF", 0xff, 16)

    def test_bad_string(self):
        self.assert_bad_const("1")
        self.assert_bad_const("-1")
        self.assert_bad_const("1bx")
        self.assert_bad_const("1ba")
        self.assert_bad_const("1'bx")
        self.assert_bad_const("1'z0")
        self.assert_bad_const("1'ba")
        self.assert_bad_const("1'b10")
        self.assert_bad_const("4'h12")
        self.assert_bad_const("-'h1")
        self.assert_bad_const("-2'b10")
        self.assert_bad_const("1'-b10")
        self.assert_bad_const("-1'b10")
        self.assert_bad_const("5'b111111'")
        self.assert_bad_const("'")
        self.assert_bad_const("'1")
        self.assert_bad_const("2'b01", bitwidth=3)
        self.assert_bad_const("1'")

    def test_bool(self):
        self.check_const(True, 1, 1)
        self.check_const(False, 0, 1, bitwidth=1)

    def test_badbool(self):
        self.assert_bad_const(False, bitwidth=2)
        self.assert_bad_const(True, bitwidth=0)

    def test_badtype(self):
        self.assert_bad_const(pyrtl.Const(123))
        self.assert_bad_const([])

    def test_assignment(self):
        with self.assertRaises(pyrtl.PyrtlError):
            c = pyrtl.Const(4)
            c <<= 3

    def test_named(self):
        block = pyrtl.working_block()
        c = pyrtl.Const(20, name="archid")
        self.assertIn("archid", block.wirevector_by_name)
        self.assertIn(c, block.wirevector_set)
        self.assertEqual(c.val, 20)
        c.name = "vendorid"
        self.assertNotIn("archid", block.wirevector_by_name)
        self.assertIn("vendorid", block.wirevector_by_name)
        self.assertIn(c, block.wirevector_set)
        self.assertEqual(c.val, 20)

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

    def test_assign_output(self):
        o = pyrtl.Output(1)
        w = pyrtl.WireVector(1)
        with self.assertRaises(pyrtl.PyrtlInternalError):
            w <<= o

    def test_log_op_output(self):
        o = pyrtl.Output(1)
        w = pyrtl.WireVector(1)
        with self.assertRaises(pyrtl.PyrtlInternalError):
            x = w & o

    def test_slice_output(self):
        o = pyrtl.Output(2)
        with self.assertRaises(pyrtl.PyrtlInternalError):
            x = o[0]


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


if __name__ == "__main__":
    unittest.main()
