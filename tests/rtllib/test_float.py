import doctest
import unittest

import pyrtl
import pyrtl.rtllib.float as rtlfloat

# IEEE 754 Float16 special values
FLOAT16_POS_ZERO = 0x0000
FLOAT16_NEG_ZERO = 0x8000
FLOAT16_POS_INF = 0x7C00
FLOAT16_NEG_INF = 0xFC00
# Quiet NaN: https://en.wikipedia.org/wiki/NaN#Quiet_NaN
# Encoding: https://en.wikipedia.org/wiki/NaN#Encoding
FLOAT16_NAN = 0x7E00
FLOAT16_ONE = 0x3C00  # 1.0
FLOAT16_NEG_ONE = 0xBC00  # -1.0
FLOAT16_TWO = 0x4000  # 2.0
FLOAT16_NEG_TWO = 0xC000  # -2.0
FLOAT16_THREE = 0x4200  # 3.0
FLOAT16_QUARTER = 0x3400  # 0.25
FLOAT16_HALF = 0x3800  # 0.5
FLOAT16_ONE_POINT_FIVE = 0x3E00  # 1.5
FLOAT16_ONE_POINT_TWOFIVE = 0x3D00  # 1.25
FLOAT16_LARGEST_NORMAL = 0x7BFF  # Largest normal number (~65504)
FLOAT16_DENORMALIZED = 0x0001  # Smallest denormalized number


class TestDocTests(unittest.TestCase):
    """Test documentation examples."""

    def test_add_sub_doctests(self):
        failures, tests = doctest.testmod(m=rtlfloat.add_sub)
        self.assertGreater(tests, 0)
        self.assertEqual(failures, 0)

    def test_mult_doctests(self):
        failures, tests = doctest.testmod(m=rtlfloat.multiplication)
        self.assertGreater(tests, 0)
        self.assertEqual(failures, 0)


def float16_parts(sign, exp, mant):
    """Construct Float16 from sign, exponent, and mantissa."""
    assert sign in (0, 1), f"sign must be 0 or 1, got {sign}"
    assert 0 <= exp <= 31, f"exponent must be in [0, 31], got {exp}"
    assert 0 <= mant <= 1023, f"mantissa must be in [0, 1023], got {mant}"
    return (sign << 15) | (exp << 10) | mant


def decode_float16(bits):
    """Decode Float16 bits to (sign, exponent, mantissa)."""
    assert 0 <= bits <= 0xFFFF, f"bits must be a 16-bit value, got {bits:#06x}"
    return (bits >> 15) & 1, (bits >> 10) & 0x1F, bits & 0x3FF


def is_nan(bits):
    """Check if Float16 bits represent NaN."""
    _, exp, mant = decode_float16(bits)
    return exp == 0x1F and mant != 0


def assertFloat16Equal(test_case: unittest.TestCase, sim, output_name, expected):
    """Assert that a simulated Float16 output matches expected, with decoded info."""
    actual = sim.inspect(output_name)
    if actual != expected:
        actual_sign, actual_exponent, actual_mantissa = decode_float16(actual)
        expected_sign, expected_exponent, expected_mantissa = decode_float16(expected)
        test_case.fail(
            f"{output_name}: expected {expected:#06x} sign: {expected_sign}, "
            f"exponent: {expected_exponent}, mantissa: {expected_mantissa};\n"
            f"got {actual:#06x} sign: {actual_sign}, exponent: {actual_exponent}, "
            f"mantissa: {actual_mantissa}"
        )


class TestAddition(unittest.TestCase):
    """Tests for Float16 addition operations."""

    def setUp(self):
        pyrtl.reset_working_block()
        self.a = rtlfloat.Float16(name="a", concatenated_type=pyrtl.Input)
        self.b = rtlfloat.Float16(name="b", concatenated_type=pyrtl.Input)
        rtlfloat.set_default_rounding_mode(rtlfloat.RoundingMode.RNE)
        result_rne = pyrtl.Output(name="result_rne")
        result_rne <<= rtlfloat.add(self.a, self.b)
        rtlfloat.set_default_rounding_mode(rtlfloat.RoundingMode.RTZ)
        result_rtz = pyrtl.Output(name="result_rtz")
        result_rtz <<= rtlfloat.add(self.a, self.b)
        self.sim = pyrtl.Simulation()

    def assertFloat16Equal(self, output_name, expected):
        assertFloat16Equal(self, self.sim, output_name, expected)

    ############################
    # Normal cases.

    def test_add_one_plus_two(self):
        """Test 1.0 + 2.0 = 3.0"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_TWO})
        self.assertFloat16Equal("result_rne", FLOAT16_THREE)
        self.assertFloat16Equal("result_rtz", FLOAT16_THREE)

    def test_add_one_plus_half(self):
        """Test 1.0 + 0.5 = 1.5 (no rounding, GRS=000)"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_HALF})
        self.assertFloat16Equal("result_rne", FLOAT16_ONE_POINT_FIVE)
        self.assertFloat16Equal("result_rtz", FLOAT16_ONE_POINT_FIVE)

    def test_add_one_plus_quarter(self):
        """Test 1.0 + 0.25 = 1.25 (no rounding, shift by 2)"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_QUARTER})
        self.assertFloat16Equal("result_rne", FLOAT16_ONE_POINT_TWOFIVE)
        self.assertFloat16Equal("result_rtz", FLOAT16_ONE_POINT_TWOFIVE)

    def test_add_half_plus_half(self):
        """Test 0.5 + 0.5 = 1.0"""
        self.sim.step({"a": FLOAT16_HALF, "b": FLOAT16_HALF})
        self.assertFloat16Equal("result_rne", FLOAT16_ONE)
        self.assertFloat16Equal("result_rtz", FLOAT16_ONE)

    def test_add_with_carry(self):
        """Test 1.5 + 1.5 = 3.0 (carry propagates to exponent)"""
        self.sim.step({"a": FLOAT16_ONE_POINT_FIVE, "b": FLOAT16_ONE_POINT_FIVE})
        self.assertFloat16Equal("result_rne", FLOAT16_THREE)
        self.assertFloat16Equal("result_rtz", FLOAT16_THREE)

    def test_add_opposite_signs_equal_magnitude(self):
        """Test 1.0 + (-1.0) = 0"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_NEG_ONE})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_ZERO)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_ZERO)

    ############################
    # Error handling.

    def test_mismatched_types(self):
        pyrtl.reset_working_block()
        a = rtlfloat.Float16(name="a", concatenated_type=pyrtl.Input)
        b = rtlfloat.Float32(name="b", concatenated_type=pyrtl.Input)
        with self.assertRaises(pyrtl.PyrtlError):
            rtlfloat.add(a, b)

    ############################
    # Rounding tests.

    def test_rounding_g1_r0_s0_lsb0_tie_truncates(self):
        """Test G=1, R=0, S=0, LSB=0: tie, RNE truncates to even.

        a = 1.0 (exp=15, mant=0)
        b = 0.5 * (1 + 1/1024) = exp=14, mant=1
        Shift b by 1: G=1 (bit 0 of original), R=0, S=0
        Sum mantissa LSB = 0, so RNE truncates.
        Both RNE and RTZ produce same result.
        """
        a = float16_parts(0, 15, 0)  # 1.0
        b = float16_parts(0, 14, 1)  # 0.5 * (1 + 1/1024)
        expected = float16_parts(0, 15, 512)  # 1.5
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected)
        self.assertFloat16Equal("result_rtz", expected)

    def test_rounding_g1_r0_s0_lsb1_tie_rounds_up(self):
        """Test G=1, R=0, S=0, LSB=1: tie, RNE rounds up to even.

        a = 1.0 * (1 + 1/1024) = exp=15, mant=1
        b = 0.5 * (1 + 1/1024) = exp=14, mant=1
        Shift b by 1: G=1, R=0, S=0
        Sum mantissa = 1.1000000001, LSB = 1
        RNE: round up to make LSB even -> mant = 514
        RTZ: truncate -> mant = 513
        """
        a = float16_parts(0, 15, 1)  # 1.0 * (1 + 1/1024)
        b = float16_parts(0, 14, 1)  # 0.5 * (1 + 1/1024)
        expected_rne = float16_parts(0, 15, 514)
        expected_rtz = float16_parts(0, 15, 513)
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected_rne)
        self.assertFloat16Equal("result_rtz", expected_rtz)

    def test_rounding_g1_r1_s0_rounds_up(self):
        """Test G=1, R=1, S=0: greater than half ULP, RNE rounds up.

        a = 1.0 (exp=15, mant=0)
        b = 0.25 * (1 + 3/1024) = exp=13, mant=3
        Shift b by 2: G=1 (bit 1), R=1 (bit 0), S=0
        RNE: round up
        RTZ: truncate
        """
        a = float16_parts(0, 15, 0)  # 1.0
        b = float16_parts(0, 13, 3)  # 0.25 * (1 + 3/1024)
        expected_rne = float16_parts(0, 15, 257)
        expected_rtz = float16_parts(0, 15, 256)
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected_rne)
        self.assertFloat16Equal("result_rtz", expected_rtz)

    def test_rounding_g1_r0_s1_rounds_up(self):
        """Test G=1, R=0, S=1: greater than half ULP, RNE rounds up.

        a = 1.0 (exp=15, mant=0)
        b = 0.125 * (1 + 5/1024) = exp=12, mant=5 (binary: 101)
        Shift b by 3: G=1 (bit 2), R=0 (bit 1), S=1 (bit 0)
        RNE: round up
        RTZ: truncate
        """
        a = float16_parts(0, 15, 0)  # 1.0
        b = float16_parts(0, 12, 5)  # 0.125 * (1 + 5/1024)
        expected_rne = float16_parts(0, 15, 129)
        expected_rtz = float16_parts(0, 15, 128)
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected_rne)
        self.assertFloat16Equal("result_rtz", expected_rtz)

    def test_rounding_g0_r1_s1_truncates(self):
        """Test G=0, R=1, S=1: less than half ULP, RNE truncates.

        a = 1.0 (exp=15, mant=0)
        b = 0.125 * (1 + 3/1024) = exp=12, mant=3 (binary: 011)
        Shift b by 3: G=0 (bit 2), R=1 (bit 1), S=1 (bit 0)
        Both RNE and RTZ truncate.
        """
        a = float16_parts(0, 15, 0)  # 1.0
        b = float16_parts(0, 12, 3)  # 0.125 * (1 + 3/1024)
        expected = float16_parts(0, 15, 128)
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected)
        self.assertFloat16Equal("result_rtz", expected)

    ############################
    # Rounding with carry tests.

    def test_carry_g1_r0_s0_lsb1_tie_rounds_up(self):
        """Test carry with G=1, R=0, S=0, LSB=1: tie rounds up.

        a = 1.1111111110 (exp=15, mant=1022)
        b = 1.0000000001 (exp=15, mant=1)
        Sum = 10.1111111111 -> normalize to 1.01111111111
        After normalization: G=1 (shifted out bit), R=0, S=0
        Result mantissa = 0111111111 = 511, LSB = 1
        RNE: tie, LSB=1 -> round up to 512
        RTZ: truncate to 511
        """
        a = float16_parts(0, 15, 1022)
        b = float16_parts(0, 15, 1)
        expected_rne = float16_parts(0, 16, 512)  # Rounded up
        expected_rtz = float16_parts(0, 16, 511)  # Truncated
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected_rne)
        self.assertFloat16Equal("result_rtz", expected_rtz)

    def test_carry_g1_r0_s0_lsb0_tie_truncates(self):
        """Test carry with G=1, R=0, S=0, LSB=0: tie truncates.

        a = 1.1111111100 (exp=15, mant=1020)
        b = 1.0000000001 (exp=15, mant=1)
        After normalization and carry handling:
        Result mantissa = 510, LSB = 0
        Both RNE and RTZ truncate.
        """
        a = float16_parts(0, 15, 1020)
        b = float16_parts(0, 15, 1)
        expected = float16_parts(0, 16, 510)
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected)
        self.assertFloat16Equal("result_rtz", expected)

    ############################
    # Edge cases.

    def test_add_zero_to_number(self):
        """Test x + 0 = x"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_POS_ZERO})
        self.assertFloat16Equal("result_rne", FLOAT16_ONE)
        self.assertFloat16Equal("result_rtz", FLOAT16_ONE)

    def test_add_negative_zero_to_number(self):
        """Test x + (-0) = x"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_NEG_ZERO})
        self.assertFloat16Equal("result_rne", FLOAT16_ONE)
        self.assertFloat16Equal("result_rtz", FLOAT16_ONE)

    def test_add_infinity_to_number(self):
        """Test x + inf = inf"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_POS_INF})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_INF)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_INF)

    def test_add_negative_infinity_to_number(self):
        """Test x + (-inf) = -inf"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_NEG_INF})
        self.assertFloat16Equal("result_rne", FLOAT16_NEG_INF)
        self.assertFloat16Equal("result_rtz", FLOAT16_NEG_INF)

    def test_add_infinity_minus_infinity_is_nan(self):
        """Test inf + (-inf) = NaN"""
        self.sim.step({"a": FLOAT16_POS_INF, "b": FLOAT16_NEG_INF})
        self.assertTrue(is_nan(self.sim.inspect("result_rne")))
        self.assertTrue(is_nan(self.sim.inspect("result_rtz")))

    def test_add_nan_propagates(self):
        """Test x + NaN = NaN"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_NAN})
        self.assertTrue(is_nan(self.sim.inspect("result_rne")))
        self.assertTrue(is_nan(self.sim.inspect("result_rtz")))

    def test_add_denormalized_flushed_to_zero(self):
        """Test that denormalized inputs are flushed to zero."""
        self.sim.step({"a": FLOAT16_POS_ZERO, "b": FLOAT16_DENORMALIZED})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_ZERO)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_ZERO)

    ############################
    # Overflow tests.

    def test_overflow_rne_produces_infinity(self):
        """Test that overflow produces infinity with RNE."""
        self.sim.step({"a": FLOAT16_LARGEST_NORMAL, "b": FLOAT16_LARGEST_NORMAL})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_INF)

    def test_overflow_rtz_produces_largest_finite(self):
        """Test that overflow produces largest finite with RTZ."""
        self.sim.step({"a": FLOAT16_LARGEST_NORMAL, "b": FLOAT16_LARGEST_NORMAL})
        self.assertFloat16Equal("result_rtz", FLOAT16_LARGEST_NORMAL)


class TestSubtraction(unittest.TestCase):
    """Tests for Float16 subtraction operations."""

    def setUp(self):
        pyrtl.reset_working_block()
        self.a = rtlfloat.Float16(name="a", concatenated_type=pyrtl.Input)
        self.b = rtlfloat.Float16(name="b", concatenated_type=pyrtl.Input)
        rtlfloat.set_default_rounding_mode(rtlfloat.RoundingMode.RNE)
        result_rne = pyrtl.Output(name="result_rne")
        result_rne <<= rtlfloat.sub(self.a, self.b)
        rtlfloat.set_default_rounding_mode(rtlfloat.RoundingMode.RTZ)
        result_rtz = pyrtl.Output(name="result_rtz")
        result_rtz <<= rtlfloat.sub(self.a, self.b)
        self.sim = pyrtl.Simulation()

    def assertFloat16Equal(self, output_name, expected):
        assertFloat16Equal(self, self.sim, output_name, expected)

    ############################
    # Normal cases.

    def test_sub_three_minus_one(self):
        """Test 3.0 - 1.0 = 2.0"""
        self.sim.step({"a": FLOAT16_THREE, "b": FLOAT16_ONE})
        self.assertFloat16Equal("result_rne", FLOAT16_TWO)
        self.assertFloat16Equal("result_rtz", FLOAT16_TWO)

    def test_sub_one_point_five_minus_half(self):
        """Test 1.5 - 0.5 = 1.0"""
        self.sim.step({"a": FLOAT16_ONE_POINT_FIVE, "b": FLOAT16_HALF})
        self.assertFloat16Equal("result_rne", FLOAT16_ONE)
        self.assertFloat16Equal("result_rtz", FLOAT16_ONE)

    def test_sub_equal_numbers(self):
        """Test 1.0 - 1.0 = 0.0"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_ONE})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_ZERO)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_ZERO)

    def test_sub_from_zero(self):
        """Test 0 - 1.0 = -1.0"""
        self.sim.step({"a": FLOAT16_POS_ZERO, "b": FLOAT16_ONE})
        self.assertFloat16Equal("result_rne", FLOAT16_NEG_ONE)
        self.assertFloat16Equal("result_rtz", FLOAT16_NEG_ONE)

    def test_sub_two_minus_half(self):
        """Test 2.0 - 0.5 = 1.5"""
        self.sim.step({"a": FLOAT16_TWO, "b": FLOAT16_HALF})
        self.assertFloat16Equal("result_rne", FLOAT16_ONE_POINT_FIVE)
        self.assertFloat16Equal("result_rtz", FLOAT16_ONE_POINT_FIVE)

    def test_sub_double_negative(self):
        """Test x - (-y) = x + y: 1.0 - (-1.0) = 2.0"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_NEG_ONE})
        self.assertFloat16Equal("result_rne", FLOAT16_TWO)
        self.assertFloat16Equal("result_rtz", FLOAT16_TWO)

    ############################
    # Rounding tests.

    def test_sub_exact_no_rounding(self):
        """Test 1.5 - 0.25 = 1.25 (no rounding needed, exact result).

        a = 1.5 (exp=15, mant=512)
        b = 0.25 (exp=13, mant=0)
        Result fits exactly in mantissa, GRS=000.
        Both RNE and RTZ produce same result.
        """
        self.sim.step({"a": FLOAT16_ONE_POINT_FIVE, "b": FLOAT16_QUARTER})
        self.assertFloat16Equal("result_rne", FLOAT16_ONE_POINT_TWOFIVE)
        self.assertFloat16Equal("result_rtz", FLOAT16_ONE_POINT_TWOFIVE)

    def test_sub_rne_rounds_up(self):
        """Test subtraction where RNE rounds up and RTZ truncates.

        a = 1.0 * (1 + 512/1024) = exp=15, mant=512 (1.5)
        b = 0.25 * (1 + 2/1024) = exp=13, mant=2
        Shift b by 2 -> LSB=1, G=1, R=0, S=0
        RNE: rounds up to 256
        RTZ: truncates to 255
        """
        a = float16_parts(0, 15, 512)
        b = float16_parts(0, 13, 2)
        expected_rne = float16_parts(0, 15, 256)
        expected_rtz = float16_parts(0, 15, 255)
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected_rne)
        self.assertFloat16Equal("result_rtz", expected_rtz)

    ############################
    # Edge cases.

    def test_sub_zero_from_number(self):
        """Test x - 0 = x"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_POS_ZERO})
        self.assertFloat16Equal("result_rne", FLOAT16_ONE)
        self.assertFloat16Equal("result_rtz", FLOAT16_ONE)

    def test_sub_pos_zero_minus_pos_zero(self):
        """Test +0 - +0 = +0"""
        self.sim.step({"a": FLOAT16_POS_ZERO, "b": FLOAT16_POS_ZERO})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_ZERO)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_ZERO)

    def test_sub_neg_zero_minus_neg_zero(self):
        """Test -0 - -0 = +0"""
        self.sim.step({"a": FLOAT16_NEG_ZERO, "b": FLOAT16_NEG_ZERO})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_ZERO)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_ZERO)

    def test_sub_infinity_from_number(self):
        """Test x - inf = -inf"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_POS_INF})
        self.assertFloat16Equal("result_rne", FLOAT16_NEG_INF)
        self.assertFloat16Equal("result_rtz", FLOAT16_NEG_INF)

    def test_sub_infinity_from_infinity_is_nan(self):
        """Test inf - inf = NaN"""
        self.sim.step({"a": FLOAT16_POS_INF, "b": FLOAT16_POS_INF})
        self.assertTrue(is_nan(self.sim.inspect("result_rne")))
        self.assertTrue(is_nan(self.sim.inspect("result_rtz")))

    def test_sub_neg_infinity_from_pos_infinity(self):
        """Test inf - (-inf) = inf"""
        self.sim.step({"a": FLOAT16_POS_INF, "b": FLOAT16_NEG_INF})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_INF)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_INF)

    def test_sub_nan_propagates(self):
        """Test x - NaN = NaN"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_NAN})
        self.assertTrue(is_nan(self.sim.inspect("result_rne")))
        self.assertTrue(is_nan(self.sim.inspect("result_rtz")))

    def test_sub_denormalized_flushed_to_zero(self):
        """Test that denormalized operands are flushed to zero."""
        self.sim.step({"a": FLOAT16_DENORMALIZED, "b": FLOAT16_POS_ZERO})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_ZERO)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_ZERO)

    ############################
    # Overflow tests.

    def test_overflow_by_subtracting_negative(self):
        """Test overflow when subtracting large negative: large - (-large).

        RNE: overflow produces infinity
        RTZ: overflow produces largest finite
        """
        a = FLOAT16_LARGEST_NORMAL  # Large positive
        b = FLOAT16_LARGEST_NORMAL | 0x8000  # Same magnitude, negative
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_INF)
        self.assertFloat16Equal("result_rtz", FLOAT16_LARGEST_NORMAL)


class TestMultiplication(unittest.TestCase):
    """Tests for Float16 multiplication operations."""

    def setUp(self):
        pyrtl.reset_working_block()
        self.a = rtlfloat.Float16(name="a", concatenated_type=pyrtl.Input)
        self.b = rtlfloat.Float16(name="b", concatenated_type=pyrtl.Input)
        rtlfloat.set_default_rounding_mode(rtlfloat.RoundingMode.RNE)
        result_rne = pyrtl.Output(name="result_rne")
        result_rne <<= rtlfloat.mult(self.a, self.b)
        rtlfloat.set_default_rounding_mode(rtlfloat.RoundingMode.RTZ)
        result_rtz = pyrtl.Output(name="result_rtz")
        result_rtz <<= rtlfloat.mult(self.a, self.b)
        self.sim = pyrtl.Simulation()

    def assertFloat16Equal(self, output_name, expected):
        assertFloat16Equal(self, self.sim, output_name, expected)

    ############################
    # Normal cases.

    def test_mul_half_times_two(self):
        """Test 0.5 * 2.0 = 1.0"""
        self.sim.step({"a": FLOAT16_HALF, "b": FLOAT16_TWO})
        self.assertFloat16Equal("result_rne", FLOAT16_ONE)
        self.assertFloat16Equal("result_rtz", FLOAT16_ONE)

    def test_mul_one_point_five_times_two(self):
        """Test 1.5 * 2.0 = 3.0"""
        self.sim.step({"a": FLOAT16_ONE_POINT_FIVE, "b": FLOAT16_TWO})
        self.assertFloat16Equal("result_rne", FLOAT16_THREE)
        self.assertFloat16Equal("result_rtz", FLOAT16_THREE)

    def test_mul_opposite_signs(self):
        """Test -1.0 * 2.0 = -2.0"""
        self.sim.step({"a": FLOAT16_NEG_ONE, "b": FLOAT16_TWO})
        self.assertFloat16Equal("result_rne", FLOAT16_NEG_TWO)
        self.assertFloat16Equal("result_rtz", FLOAT16_NEG_TWO)

    def test_mul_both_negative(self):
        """Test -1.0 * -2.0 = 2.0"""
        self.sim.step({"a": FLOAT16_NEG_ONE, "b": FLOAT16_NEG_TWO})
        self.assertFloat16Equal("result_rne", FLOAT16_TWO)
        self.assertFloat16Equal("result_rtz", FLOAT16_TWO)

    def test_mul_one_point_five_times_one_point_five(self):
        """Test 1.5 * 1.5 = 2.25"""
        self.sim.step({"a": FLOAT16_ONE_POINT_FIVE, "b": FLOAT16_ONE_POINT_FIVE})
        expected = 0x4080  # 2.25 in float16
        self.assertFloat16Equal("result_rne", expected)
        self.assertFloat16Equal("result_rtz", expected)

    ############################
    # Error handling.

    def test_mismatched_types(self):
        pyrtl.reset_working_block()
        a = rtlfloat.Float16(name="a", concatenated_type=pyrtl.Input)
        b = rtlfloat.Float32(name="b", concatenated_type=pyrtl.Input)
        with self.assertRaises(pyrtl.PyrtlError):
            rtlfloat.mult(a, b)

    ############################
    # Rounding tests.

    def test_rounding_g0_s0_truncates(self):
        """Test Guard=0, Sticky=0: RNE truncates (exact result, no rounding needed).

        a = 1.0 (exp=15, mant=0)
        b = 1.0 (exp=15, mant=0)
        Product mantissa has Guard=0, Sticky=0.
        Both RNE and RTZ produce the same result.
        """
        a = float16_parts(0, 15, 0)  # 1.0
        b = float16_parts(0, 15, 0)  # 1.0
        expected = float16_parts(0, 15, 0)  # 1.0
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected)
        self.assertFloat16Equal("result_rtz", expected)

    def test_rounding_g0_s1_truncates(self):
        """Test Guard=0, Sticky=1: RNE truncates (less than half ULP).

        a = 1.0 * (1 + 1/1024) = exp=15, mant=1
        b = 1.0 * (1 + 1/1024) = exp=15, mant=1
        Product has Guard=0, Sticky=1, Last=0.
        Both RNE and RTZ truncate.
        """
        a = float16_parts(0, 15, 1)  # 1.0 * (1 + 1/1024)
        b = float16_parts(0, 15, 1)  # 1.0 * (1 + 1/1024)
        expected = float16_parts(0, 15, 2)
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected)
        self.assertFloat16Equal("result_rtz", expected)

    def test_rounding_g1_l0_s0_tie_truncates(self):
        """Test Guard=1, Last=0, Sticky=0: tie, RNE truncates (LSB already even).

        a = 1.0 * (1 + 2/1024) = exp=15, mant=2
        b = 1.0 * (1 + 256/1024) = exp=15, mant=256
        Product has Guard=1, Sticky=0, Last=0.
        RNE: LSB is 0 (even), so truncate.
        Both RNE and RTZ truncate.
        """
        a = float16_parts(0, 15, 2)  # 1.0 * (1 + 2/1024)
        b = float16_parts(0, 15, 256)  # 1.0 * (1 + 256/1024)
        expected = float16_parts(0, 15, 258)
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected)
        self.assertFloat16Equal("result_rtz", expected)

    def test_rounding_g1_l1_s0_tie_rounds_up(self):
        """Test Guard=1, Last=1, Sticky=0: tie, RNE rounds up (make LSB even).

        a = 1.0 * (1 + 1/1024) = exp=15, mant=1
        b = 1.0 * (1 + 512/1024) = exp=15, mant=512 (1.5)
        Product has Guard=1, Sticky=0, Last=1.
        RNE: LSB is 1 (odd), so round up to make it even.
        RTZ: truncates
        """
        a = float16_parts(0, 15, 1)  # 1.0 * (1 + 1/1024)
        b = float16_parts(0, 15, 512)  # 1.0 * (1 + 512/1024)
        expected_rne = float16_parts(0, 15, 514)
        expected_rtz = float16_parts(0, 15, 513)
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected_rne)
        self.assertFloat16Equal("result_rtz", expected_rtz)

    def test_rounding_g1_l0_s1_rounds_up(self):
        """Test Guard=1, Last=0, Sticky=1: greater than half ULP, RNE rounds up.

        a = 1.0 * (1 + 1/1024) = exp=15, mant=1
        b = 1.0 * (1 + 513/1024) = exp=15, mant=513
        Product has Guard=1, Sticky=1, Last=0.
        Greater than half ULP, so round up.
        RNE: rounds up
        RTZ: truncates
        """
        a = float16_parts(0, 15, 1)  # 1.0 * (1 + 1/1024)
        b = float16_parts(0, 15, 513)  # 1.0 * (1 + 513/1024)
        expected_rne = float16_parts(0, 15, 515)
        expected_rtz = float16_parts(0, 15, 514)
        self.sim.step({"a": a, "b": b})
        self.assertFloat16Equal("result_rne", expected_rne)
        self.assertFloat16Equal("result_rtz", expected_rtz)

    ############################
    # Edge cases.

    def test_mul_by_zero(self):
        """Test x * 0 = 0"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_POS_ZERO})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_ZERO)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_ZERO)

    def test_mul_by_negative_zero(self):
        """Test x * (-0) = -0"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_NEG_ZERO})
        self.assertFloat16Equal("result_rne", FLOAT16_NEG_ZERO)
        self.assertFloat16Equal("result_rtz", FLOAT16_NEG_ZERO)

    def test_mul_infinity_by_number(self):
        """Test inf * x = inf"""
        self.sim.step({"a": FLOAT16_POS_INF, "b": FLOAT16_TWO})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_INF)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_INF)

    def test_mul_neg_infinity_by_number(self):
        """Test -inf * x = -inf"""
        self.sim.step({"a": FLOAT16_NEG_INF, "b": FLOAT16_TWO})
        self.assertFloat16Equal("result_rne", FLOAT16_NEG_INF)
        self.assertFloat16Equal("result_rtz", FLOAT16_NEG_INF)

    def test_mul_infinity_by_zero_is_nan(self):
        """Test inf * 0 = NaN"""
        self.sim.step({"a": FLOAT16_POS_INF, "b": FLOAT16_POS_ZERO})
        self.assertTrue(is_nan(self.sim.inspect("result_rne")))
        self.assertTrue(is_nan(self.sim.inspect("result_rtz")))

    def test_mul_infinity_by_infinity(self):
        """Test inf * inf = inf"""
        self.sim.step({"a": FLOAT16_POS_INF, "b": FLOAT16_POS_INF})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_INF)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_INF)

    def test_mul_pos_infinity_by_neg_infinity(self):
        """Test inf * (-inf) = -inf"""
        self.sim.step({"a": FLOAT16_POS_INF, "b": FLOAT16_NEG_INF})
        self.assertFloat16Equal("result_rne", FLOAT16_NEG_INF)
        self.assertFloat16Equal("result_rtz", FLOAT16_NEG_INF)

    def test_mul_nan_propagates(self):
        """Test x * NaN = NaN"""
        self.sim.step({"a": FLOAT16_ONE, "b": FLOAT16_NAN})
        self.assertTrue(is_nan(self.sim.inspect("result_rne")))
        self.assertTrue(is_nan(self.sim.inspect("result_rtz")))

    def test_mul_denormalized_flushed_to_zero(self):
        """Test that denormalized operands are flushed to zero."""
        self.sim.step({"a": FLOAT16_DENORMALIZED, "b": FLOAT16_ONE})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_ZERO)
        self.assertFloat16Equal("result_rtz", FLOAT16_POS_ZERO)

    ############################
    # Overflow tests.

    def test_overflow_rne_produces_infinity(self):
        """Test that overflow produces infinity with RNE."""
        self.sim.step({"a": FLOAT16_LARGEST_NORMAL, "b": FLOAT16_TWO})
        self.assertFloat16Equal("result_rne", FLOAT16_POS_INF)

    def test_overflow_rtz_produces_largest_finite(self):
        """Test that overflow produces largest finite with RTZ."""
        self.sim.step({"a": FLOAT16_LARGEST_NORMAL, "b": FLOAT16_TWO})
        self.assertFloat16Equal("result_rtz", FLOAT16_LARGEST_NORMAL)

    def test_negative_overflow_rne_produces_neg_infinity(self):
        """Test that negative overflow produces -infinity with RNE."""
        neg_largest = FLOAT16_LARGEST_NORMAL | 0x8000
        self.sim.step({"a": neg_largest, "b": FLOAT16_TWO})
        self.assertFloat16Equal("result_rne", FLOAT16_NEG_INF)

    def test_negative_overflow_rtz_produces_neg_largest_finite(self):
        """Test that negative overflow produces -largest finite with RTZ."""
        neg_largest = FLOAT16_LARGEST_NORMAL | 0x8000
        self.sim.step({"a": neg_largest, "b": FLOAT16_TWO})
        expected = FLOAT16_LARGEST_NORMAL | 0x8000
        self.assertFloat16Equal("result_rtz", expected)


if __name__ == "__main__":
    unittest.main()
