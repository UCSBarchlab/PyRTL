"""Shared Float16 test utilities: constants, encoding helpers, and assertions."""

import unittest

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
FLOAT16_HALF = 0x3800  # 0.5
FLOAT16_ONE_POINT_FIVE = 0x3E00  # 1.5
FLOAT16_LARGEST_NORMAL = 0x7BFF  # Largest normal number (~65504)
FLOAT16_DENORMALIZED = 0x0001  # Smallest denormalized number


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
        expected_sign, expected_exponent, expected_mantissa = decode_float16(
            expected
        )
        test_case.fail(
            f"{output_name}: expected {expected:#06x} sign: {expected_sign}, "
            f"exponent: {expected_exponent}, mantissa: {expected_mantissa};\n"
            f"got {actual:#06x} sign: {actual_sign}, exponent: {actual_exponent}, "
            f"mantissa: {actual_mantissa}"
        )
