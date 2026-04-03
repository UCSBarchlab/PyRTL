import unittest

import pyrtl
from pyrtl.rtllib.pyrtlfloat import Float16Operations, FloatOperations, RoundingMode

from .float16_test_utils import (
    FLOAT16_DENORMALIZED,
    FLOAT16_HALF,
    FLOAT16_LARGEST_NORMAL,
    FLOAT16_NAN,
    FLOAT16_NEG_INF,
    FLOAT16_NEG_ONE,
    FLOAT16_NEG_TWO,
    FLOAT16_NEG_ZERO,
    FLOAT16_ONE,
    FLOAT16_ONE_POINT_FIVE,
    FLOAT16_POS_INF,
    FLOAT16_POS_ZERO,
    FLOAT16_THREE,
    FLOAT16_TWO,
    assertFloat16Equal,
    float16_parts,
    is_nan,
)


class TestMultiplication(unittest.TestCase):
    """Tests for Float16 multiplication operations."""

    def setUp(self):
        pyrtl.reset_working_block()
        self.a = pyrtl.Input(bitwidth=16, name="a")
        self.b = pyrtl.Input(bitwidth=16, name="b")
        FloatOperations.default_rounding_mode = RoundingMode.RNE
        result_rne = pyrtl.Output(name="result_rne")
        result_rne <<= Float16Operations.mul(self.a, self.b)
        FloatOperations.default_rounding_mode = RoundingMode.RTZ
        result_rtz = pyrtl.Output(name="result_rtz")
        result_rtz <<= Float16Operations.mul(self.a, self.b)
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
