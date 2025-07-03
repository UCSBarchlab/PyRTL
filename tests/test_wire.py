import doctest
import unittest

import pyrtl


class TestDocTests(unittest.TestCase):
    """Test documentation examples."""

    def test_doctests(self):
        failures, tests = doctest.testmod(
            m=pyrtl.wire, optionflags=doctest.IGNORE_EXCEPTION_DETAIL
        )
        self.assertGreater(tests, 0)
        self.assertEqual(failures, 0)


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
        return pyrtl.wire.next_tempvar_name(s) == s

    def test_invalid_name(self):
        self.assertFalse(self.is_valid_str(""))
        with self.assertRaises(pyrtl.PyrtlError):
            self.is_valid_str("clock")

    def test_valid_names(self):
        self.assertTrue(self.is_valid_str("xxx"))
        self.assertTrue(self.is_valid_str("h"))
        self.assertTrue(self.is_valid_str(" "))
        self.assertTrue(self.is_valid_str("#$)(*&#@_+!#)("))

    def check_name_setter(self, ns):
        """test name setter in wire.py.

        Keyword arguments:

        ns -- new name of WireVector to be set
        """
        test = pyrtl.WireVector(1, "test")
        test.name = ns
        self.assertTrue(test.name == ns)

    def test_invalid_name_setter(self):
        """test invalid name data types and expect PyrtlError."""
        with self.assertRaises(pyrtl.PyrtlError):
            self.check_name_setter(24)
        with self.assertRaises(pyrtl.PyrtlError):
            self.check_name_setter(True)
        with self.assertRaises(pyrtl.PyrtlError):
            self.check_name_setter(3.14)

    def test_valid_name_setter(self):
        """test string names and expect no error."""
        self.check_name_setter("24")
        self.check_name_setter(str(24))
        self.check_name_setter("twenty_four")


class TestWireVectorFail(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_undef_wirevector_length(self):
        x = pyrtl.WireVector()
        with self.assertRaises(pyrtl.PyrtlError):
            _ = len(x)

    def test_bad_bitwidth(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _ = pyrtl.WireVector(bitwidth="happy")
        with self.assertRaises(pyrtl.PyrtlError):
            _ = pyrtl.WireVector(bitwidth=-1)
        with self.assertRaises(pyrtl.PyrtlError):
            _ = pyrtl.WireVector(bitwidth=0)

        y = pyrtl.WireVector(1)
        with self.assertRaises(pyrtl.PyrtlError):
            _ = pyrtl.WireVector(y)

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


class TestWireVectorSlicing(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def invalid_empty_slice(self, bitwidth, slice):
        w = pyrtl.Input(bitwidth)
        with self.assertRaises(pyrtl.PyrtlError):
            _ = w[slice]

    def invalid_slice_index(self, bitwidth, slice):
        w = pyrtl.Input(bitwidth)
        with self.assertRaises(IndexError):
            _ = w[slice]

    def valid_slice(self, bitwidth, slice):
        w = pyrtl.Input(bitwidth)
        _ = w[slice]

    def test_wire_wo_bitwidth_fails(self):
        w = pyrtl.WireVector()
        with self.assertRaises(pyrtl.PyrtlError):
            _ = w[2]
        with self.assertRaises(pyrtl.PyrtlError):
            _ = w[3:5]

    def test_valid_indicies(self):
        self.valid_slice(4, 2)
        self.valid_slice(4, 0)
        self.valid_slice(4, -1)
        pyrtl.working_block().sanity_check()

    def test_valid_slices(self):
        self.valid_slice(8, slice(6))
        self.valid_slice(8, slice(1, 4))
        self.valid_slice(
            8, slice(1, 8)
        )  # Yes, supplying a end index out of bounds is valid python
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
            _ = self.r or True

    def test_register_assignment_not_next(self):
        with self.assertRaises(pyrtl.PyrtlError):
            self.r <<= 1

    def test_connect_next(self):
        w = pyrtl.WireVector(bitwidth=1)
        with self.assertRaises(pyrtl.PyrtlError):
            w <<= self.r.next

    def test_next_logic_operations(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _ = self.r.next or True

    def test_reset_value_is_none(self):
        self.assertIsNone(self.r.reset_value)

    def test_reset_value_is_correct(self):
        r = pyrtl.Register(4, reset_value=1)
        self.assertEqual(r.reset_value, 1)

    def test_reset_value_as_string(self):
        r = pyrtl.Register(4, reset_value="2'd1")
        self.assertEqual(r.reset_value, 1)

    def test_invalid_reset_value_too_large(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _ = pyrtl.Register(4, reset_value=16)

    def test_invalid_reset_value_too_large_as_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _ = pyrtl.Register(4, reset_value="5'd16")

    def test_negative_reset_value(self):
        r = pyrtl.Register(4, reset_value=-4)
        self.assertEqual(pyrtl.val_to_signed_integer(r.reset_value, r.bitwidth), -4)

    def test_negative_reset_value_as_string(self):
        r = pyrtl.Register(4, reset_value="-4'd1")
        self.assertEqual(pyrtl.val_to_signed_integer(r.reset_value, r.bitwidth), -1)

    def test_invalid_negative_reset_value_as_string(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _ = pyrtl.Register(2, reset_value="-4'd1")

    def test_extending_negative_reset_value_as_string(self):
        r = pyrtl.Register(4, reset_value="-3'd3")
        self.assertEqual(pyrtl.val_to_signed_integer(r.reset_value, r.bitwidth), -3)

    def test_invalid_reset_value_not_an_integer(self):
        with self.assertRaises(pyrtl.PyrtlError):
            _ = pyrtl.Register(4, reset_value="hello")


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
        self.check_const("16'xff", 0xFF, 16)
        self.check_const("17'xff", 0xFF, 17)
        self.check_const("16'hff", 0xFF, 16)
        self.check_const("17'hff", 0xFF, 17)
        self.check_const("5'b011", 3, 5)
        self.check_const("5'b0_11", 3, 5)
        self.check_const("5'02_1", 21, 5)
        self.check_const("16'HFF", 0xFF, 16)

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
            _ = pyrtl.Const(*args, **kwargs)


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
            _ = w & o

    def test_slice_output(self):
        o = pyrtl.Output(2)
        with self.assertRaises(pyrtl.PyrtlInternalError):
            _ = o[0]


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
            _ = wire.init_call_stack

    def test_get_call_stack(self):
        pyrtl.set_debug_mode(True)
        wire = pyrtl.WireVector()
        call_stack = wire.init_call_stack
        self.assertIsInstance(call_stack, list)


class TestWrappedWireVector(unittest.TestCase):
    def setUp(self):
        pyrtl.reset_working_block()

    def test_attr(self):
        reg = pyrtl.Register(bitwidth=1, name="reg")
        wrapped_reg = pyrtl.wire.WrappedWireVector(reg)
        # Check __setattr__ forwarding.
        wrapped_reg.next <<= True

        # Check __getattr__ forwarding.
        self.assertEqual(wrapped_reg.bitwidth, 1)
        self.assertEqual(wrapped_reg.name, "reg")

        sim = pyrtl.Simulation()
        sim.step()
        self.assertEqual(sim.inspect("reg"), False)
        sim.step()
        self.assertEqual(sim.inspect("reg"), True)

    def test_ops(self):
        # Check special method forwarding.
        for a_val in range(16):
            for b_val in range(16):
                pyrtl.reset_working_block()

                a = pyrtl.Const(bitwidth=4, val=a_val)
                wrapped_a = pyrtl.wire.WrappedWireVector(a)
                b = pyrtl.Const(bitwidth=4, val=b_val)
                wrapped_b = pyrtl.wire.WrappedWireVector(b)

                self.assertEqual(hash(a), hash(wrapped_a))
                self.assertEqual(str(a), str(wrapped_a))
                self.assertEqual(repr(a), repr(wrapped_a))
                self.assertEqual(len(a), len(wrapped_a))

                a_and_b = pyrtl.WireVector(name="a_and_b", bitwidth=4)
                a_and_b <<= wrapped_a & wrapped_b
                a_rand_b = pyrtl.WireVector(name="a_rand_b", bitwidth=4)
                a_rand_b <<= wrapped_a.val & wrapped_b
                a_or_b = pyrtl.WireVector(name="a_or_b", bitwidth=4)
                a_or_b <<= wrapped_a | wrapped_b
                a_ror_b = pyrtl.WireVector(name="a_ror_b", bitwidth=4)
                a_ror_b <<= wrapped_a.val | wrapped_b
                a_xor_b = pyrtl.WireVector(name="a_xor_b", bitwidth=4)
                a_xor_b <<= wrapped_a ^ wrapped_b
                a_rxor_b = pyrtl.WireVector(name="a_rxor_b", bitwidth=4)
                a_rxor_b <<= wrapped_a.val ^ wrapped_b
                a_add_b = pyrtl.WireVector(name="a_add_b", bitwidth=5)
                a_add_b <<= wrapped_a + wrapped_b
                a_radd_b = pyrtl.WireVector(name="a_radd_b", bitwidth=5)
                a_radd_b <<= wrapped_a.val + wrapped_b
                a_sub_b = pyrtl.WireVector(name="a_sub_b", bitwidth=4)
                a_sub_b <<= wrapped_a - wrapped_b
                a_rsub_b = pyrtl.WireVector(name="a_rsub_b", bitwidth=4)
                a_rsub_b <<= wrapped_a.val - wrapped_b
                a_mul_b = pyrtl.WireVector(name="a_mul_b", bitwidth=8)
                a_mul_b <<= wrapped_a * wrapped_b
                a_rmul_b = pyrtl.WireVector(name="a_rmul_b", bitwidth=8)
                a_rmul_b <<= wrapped_a.val * wrapped_b
                a_lt_b = pyrtl.WireVector(name="a_lt_b", bitwidth=1)
                a_lt_b <<= wrapped_a < wrapped_b
                a_le_b = pyrtl.WireVector(name="a_le_b", bitwidth=1)
                a_le_b <<= wrapped_a <= wrapped_b
                a_eq_b = pyrtl.WireVector(name="a_eq_b", bitwidth=1)
                a_eq_b <<= wrapped_a == wrapped_b
                a_ne_b = pyrtl.WireVector(name="a_ne_b", bitwidth=1)
                a_ne_b <<= wrapped_a != wrapped_b
                a_gt_b = pyrtl.WireVector(name="a_gt_b", bitwidth=1)
                a_gt_b <<= wrapped_a > wrapped_b
                a_ge_b = pyrtl.WireVector(name="a_ge_b", bitwidth=1)
                a_ge_b <<= wrapped_a >= wrapped_b
                a_invert = pyrtl.WireVector(name="a_invert", bitwidth=4)
                a_invert <<= ~wrapped_a
                a_high = pyrtl.WireVector(name="a_high", bitwidth=2)
                a_high <<= wrapped_a[2:4]
                a_low = pyrtl.WireVector(name="a_low", bitwidth=2)
                a_low <<= wrapped_a[0:2]

                x = pyrtl.WireVector(name="x", bitwidth=4)
                wrapped_x = pyrtl.wire.WrappedWireVector(x)
                wrapped_x <<= a_val
                self.assertEqual(type(wrapped_x), pyrtl.wire.WrappedWireVector)

                sim = pyrtl.Simulation()
                sim.step()
                self.assertEqual(sim.inspect("a_and_b"), a.val & b.val)
                self.assertEqual(sim.inspect("a_rand_b"), a.val & b.val)
                self.assertEqual(sim.inspect("a_or_b"), a.val | b.val)
                self.assertEqual(sim.inspect("a_ror_b"), a.val | b.val)
                self.assertEqual(sim.inspect("a_xor_b"), a.val ^ b.val)
                self.assertEqual(sim.inspect("a_rxor_b"), a.val ^ b.val)
                self.assertEqual(sim.inspect("a_add_b"), a.val + b.val)
                self.assertEqual(sim.inspect("a_radd_b"), a.val + b.val)
                # Mask with 0xF to convert from signed to unsigned value.
                self.assertEqual(sim.inspect("a_sub_b"), (a.val - b.val) & 0xF)
                self.assertEqual(sim.inspect("a_rsub_b"), (a.val - b.val) & 0xF)
                self.assertEqual(sim.inspect("a_mul_b"), a.val * b.val)
                self.assertEqual(sim.inspect("a_rmul_b"), a.val * b.val)
                self.assertEqual(sim.inspect("a_lt_b"), a.val < b.val)
                self.assertEqual(sim.inspect("a_le_b"), a.val <= b.val)
                self.assertEqual(sim.inspect("a_eq_b"), a.val == b.val)
                self.assertEqual(sim.inspect("a_ne_b"), a.val != b.val)
                self.assertEqual(sim.inspect("a_gt_b"), a.val > b.val)
                self.assertEqual(sim.inspect("a_ge_b"), a.val >= b.val)
                # Mask with 0xF to convert from signed to unsigned value.
                self.assertEqual(sim.inspect("a_invert"), ~a.val & 0xF)
                self.assertEqual(sim.inspect("a_high"), a.val >> 2)
                self.assertEqual(sim.inspect("a_low"), a.val & 0x3)

                self.assertEqual(sim.inspect("x"), a.val)

    def test_conditional_assignment(self):
        # Check forwarding for __ior__, __enter__, __exit__.
        select = pyrtl.Input(name="select", bitwidth=1)
        wrapped_select = pyrtl.wire.WrappedWireVector(select)
        x = pyrtl.WireVector(name="x", bitwidth=4)
        wrapped_x = pyrtl.wire.WrappedWireVector(x)
        with pyrtl.conditional_assignment:
            with wrapped_select:
                wrapped_x |= 0xA
            with ~wrapped_select:
                wrapped_x |= 0xB
        self.assertEqual(type(wrapped_x), pyrtl.wire.WrappedWireVector)

        sim = pyrtl.Simulation()
        sim.step(provided_inputs={select: True})
        self.assertEqual(sim.inspect("x"), 0xA)
        sim.step(provided_inputs={select: False})
        self.assertEqual(sim.inspect("x"), 0xB)

    def test_exceptions(self):
        # Check forwarding for special methods that throw exceptions.
        a = pyrtl.Const(bitwidth=4, val=0xA)
        wrapped_a = pyrtl.wire.WrappedWireVector(a)
        b = pyrtl.Const(bitwidth=4, val=0xB)
        wrapped_b = pyrtl.wire.WrappedWireVector(b)

        with self.assertRaises(pyrtl.PyrtlError):
            bool(wrapped_a)
        with self.assertRaises(pyrtl.PyrtlError):
            wrapped_a &= wrapped_b
        with self.assertRaises(pyrtl.PyrtlError):
            wrapped_a ^= wrapped_b
        with self.assertRaises(pyrtl.PyrtlError):
            wrapped_a += wrapped_b
        with self.assertRaises(pyrtl.PyrtlError):
            wrapped_a -= wrapped_b
        with self.assertRaises(pyrtl.PyrtlError):
            wrapped_a *= wrapped_b
        with self.assertRaises(pyrtl.PyrtlError):
            wrapped_a << wrapped_b
        with self.assertRaises(pyrtl.PyrtlError):
            wrapped_a >> wrapped_b
        with self.assertRaises(pyrtl.PyrtlError):
            wrapped_a % wrapped_b


if __name__ == "__main__":
    unittest.main()
