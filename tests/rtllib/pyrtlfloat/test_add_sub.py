import unittest

import pyrtl
from pyrtl.rtllib.pyrtlfloat import Float16Operations, FloatOperations, RoundingMode

from .float16_test_utils import (
    FLOAT16_DENORMALIZED,
    FLOAT16_LARGEST_NORMAL,
    FLOAT16_NAN,
    FLOAT16_NEG_INF,
    FLOAT16_NEG_ONE,
    FLOAT16_NEG_ZERO,
    FLOAT16_ONE,
    FLOAT16_POS_INF,
    FLOAT16_POS_ZERO,
    FLOAT16_THREE,
    FLOAT16_TWO,
    assertFloat16Equal,
    float16_parts,
    is_nan,
)

# Additional Float16 constants used only in add/sub tests
FLOAT16_QUARTER = 0x3400  # 0.25
FLOAT16_HALF = 0x3800  # 0.5
FLOAT16_ONE_POINT_FIVE = 0x3E00  # 1.5
FLOAT16_ONE_POINT_TWOFIVE = 0x3D00  # 1.25
FLOAT16_SMALLEST_NORMAL = 0x0400  # Smallest normal number (2^-14)


class TestAddition(unittest.TestCase):
    """Tests for Float16 addition operations."""

    def setUp(self):
        pyrtl.reset_working_block()
        self.a = pyrtl.Input(bitwidth=16, name="a")
        self.b = pyrtl.Input(bitwidth=16, name="b")
        FloatOperations.default_rounding_mode = RoundingMode.RNE
        result_rne = pyrtl.Output(name="result_rne")
        result_rne <<= Float16Operations.add(self.a, self.b)
        FloatOperations.default_rounding_mode = RoundingMode.RTZ
        result_rtz = pyrtl.Output(name="result_rtz")
        result_rtz <<= Float16Operations.add(self.a, self.b)
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
        self.a = pyrtl.Input(bitwidth=16, name="a")
        self.b = pyrtl.Input(bitwidth=16, name="b")
        FloatOperations.default_rounding_mode = RoundingMode.RNE
        result_rne = pyrtl.Output(name="result_rne")
        result_rne <<= Float16Operations.sub(self.a, self.b)
        FloatOperations.default_rounding_mode = RoundingMode.RTZ
        result_rtz = pyrtl.Output(name="result_rtz")
        result_rtz <<= Float16Operations.sub(self.a, self.b)
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


if __name__ == "__main__":
    unittest.main()
