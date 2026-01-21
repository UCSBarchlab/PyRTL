import pyrtl

from ._float_utills import (
    get_exponent,
    get_mantissa,
    get_sign,
    is_denormalized,
    is_inf,
    is_nan,
    is_zero,
    make_denormals_zero,
    make_inf,
    make_largest_finite_number,
    make_nan,
    make_zero,
)
from ._types import PyrtlFloatConfig, RoundingMode


def mul(
    config: PyrtlFloatConfig,
    operand_a: pyrtl.WireVector,
    operand_b: pyrtl.WireVector,
) -> pyrtl.WireVector:
    """
    Performs floating point multiplication of two WireVectors.

    :param config: Configuration for the floating point type and rounding mode.
    :param operand_a: The first floating point operand as a WireVector.
    :param operand_b: The second floating point operand as a WireVector.
    :return: The result of the multiplication as a WireVector.
    """
    fp_type_props = config.fp_type_properties
    rounding_mode = config.rounding_mode
    num_exp_bits = fp_type_props.num_exponent_bits
    num_mant_bits = fp_type_props.num_mantissa_bits

    # Denormalized numbers are not supported, so we flush them to zero.
    operands = (operand_a, operand_b)
    operands_daz = tuple(make_denormals_zero(fp_type_props, op) for op in operands)

    # Extract the sign and exponent of both operands.
    signs = tuple(get_sign(fp_type_props, op) for op in operands_daz)
    exponents = tuple(get_exponent(fp_type_props, op) for op in operands_daz)

    result_sign = signs[0] ^ signs[1]

    # IEEE-754 floating point numbers have a bias:
    # https://en.wikipedia.org/wiki/Exponent_bias
    # real_exponent = stored_exponent - bias, so stored_exponent = real + bias
    # Therefore, stored_exponent_product = real_exponent_product + bias
    # = (real_exponent_a + real_exponent_b) + bias
    # = (stored_exponent_a - bias + stored_exponent_b - bias) + bias
    # = stored_exponent_a + stored_exponent_b - bias
    operand_exponent_sums = exponents[0] + exponents[1]
    exponent_bias = 2 ** (fp_type_props.num_exponent_bits - 1) - 1
    product_exponent = operand_exponent_sums - pyrtl.Const(exponent_bias)

    # Extract the mantissa of both operands and add the implicit leading 1.
    mantissas = tuple(
        pyrtl.concat(pyrtl.Const(1), get_mantissa(fp_type_props, op))
        for op in operands_daz
    )
    product_mantissa = mantissas[0] * mantissas[1]

    normalized_product_exponent = pyrtl.WireVector(bitwidth=num_exp_bits + 1)
    normalized_product_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)

    # We need to normalize (shift right) if the leading bit is 1.
    # https://numeral-systems.com/ieee-754-multiply/
    need_to_normalize = product_mantissa[-1]

    if rounding_mode == RoundingMode.RNE:
        guard = pyrtl.WireVector(bitwidth=1)
        sticky = pyrtl.WireVector(bitwidth=1)
        last = pyrtl.WireVector(bitwidth=1)  # Last bit of the mantissa before rounding.

    # Assign the normalized mantissa, exponent, guard, sticky, and last bits
    # based on whether normalization is needed.
    with pyrtl.conditional_assignment:
        with need_to_normalize:
            normalized_product_mantissa |= product_mantissa[-num_mant_bits - 1 :]
            normalized_product_exponent |= product_exponent + 1
            if rounding_mode == RoundingMode.RNE:
                guard |= product_mantissa[-num_mant_bits - 2]
                sticky |= product_mantissa[: -num_mant_bits - 2] != 0
                last |= product_mantissa[-num_mant_bits - 1]
        with pyrtl.otherwise:
            normalized_product_mantissa |= product_mantissa[-num_mant_bits - 2 : -1]
            normalized_product_exponent |= product_exponent
            if rounding_mode == RoundingMode.RNE:
                guard |= product_mantissa[-num_mant_bits - 3]
                sticky |= product_mantissa[: -num_mant_bits - 3] != 0
                last |= product_mantissa[-num_mant_bits - 2]

    if rounding_mode == RoundingMode.RNE:
        rounded_product_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)
        rounded_product_exponent = pyrtl.WireVector(bitwidth=num_exp_bits + 1)
        # Whether exponent was incremented due to rounding (for overflow check).
        exponent_incremented = pyrtl.WireVector(bitwidth=1)
        # If guard bit is not set, number is closer to smaller value: no round.
        # If guard and sticky are set, round up.
        # If guard is set but sticky is not, value is exactly halfway.
        # Following round-to-nearest ties-to-even, round up if last bit is 1.
        round_up = guard & (last | sticky)
        with pyrtl.conditional_assignment:
            with round_up:
                with normalized_product_mantissa == (1 << num_mant_bits) - 1:
                    rounded_product_mantissa |= 0
                    rounded_product_exponent |= normalized_product_exponent + 1
                    exponent_incremented |= 1
                with pyrtl.otherwise:
                    rounded_product_mantissa |= normalized_product_mantissa + 1
                    rounded_product_exponent |= normalized_product_exponent
                    exponent_incremented |= 0
            with pyrtl.otherwise:
                rounded_product_mantissa |= normalized_product_mantissa
                rounded_product_exponent |= normalized_product_exponent
                exponent_incremented |= 0

    result_exponent = pyrtl.WireVector(bitwidth=num_exp_bits)
    result_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)

    # Check whether operands are special: NaN, infinity, zero, or denormalized.
    operand_nans = tuple(is_nan(fp_type_props, op) for op in operands_daz)
    operand_infs = tuple(is_inf(fp_type_props, op) for op in operands_daz)
    operand_zeros = tuple(is_zero(fp_type_props, op) for op in operands_daz)
    operand_denorms = tuple(is_denormalized(fp_type_props, op) for op in operands_daz)

    # We check for overflow and underflow by computing max and min exponent
    # values of the sum of operands before rounding and normalization.
    # These values depend on the operands. If the result requires
    # normalization, the exponent is incremented by 1. Additionally, rounding
    # may further increase the exponent. Therefore, we subtract these
    # potential increments from the absolute maximum exponent, which is one
    # less than the all-1s exponent (reserved for inf/NaN) plus bias.
    # Similarly, we subtract these increments from the absolute minimum
    # exponent, which is 1 plus the exponent bias.
    sum_exponent_max_value = pyrtl.Const(2**num_exp_bits - 2 + exponent_bias)
    sum_exponent_min_value = pyrtl.Const(1 + exponent_bias)
    if rounding_mode == RoundingMode.RNE:
        exponent_max_value = (
            sum_exponent_max_value - need_to_normalize - exponent_incremented
        )
        exponent_min_value = (
            sum_exponent_min_value - need_to_normalize - exponent_incremented
        )
    else:
        exponent_max_value = sum_exponent_max_value - need_to_normalize
        exponent_min_value = sum_exponent_min_value - need_to_normalize

    # Assign the raw result's exponent and mantissa depending on whether RNE rounding
    # is used. The calculated exponent WireVector has an extra bit due to the carry-out
    # from addition, so we take only the lower num_exp_bits to remove this extra bit.
    if rounding_mode == RoundingMode.RNE:
        raw_result_exponent = rounded_product_exponent[:num_exp_bits]
        raw_result_mantissa = rounded_product_mantissa
    else:
        raw_result_exponent = normalized_product_exponent[:num_exp_bits]
        raw_result_mantissa = normalized_product_mantissa

    with pyrtl.conditional_assignment:
        # If either operand is NaN, or if one operand is infinity and the other is
        # zero, the result is NaN.
        with (
            operand_nans[0]
            | operand_nans[1]
            | (operand_infs[0] & operand_zeros[1])
            | (operand_zeros[0] & operand_infs[1])
        ):
            make_nan(fp_type_props, result_exponent, result_mantissa)
        # If either operand is infinity, the result is infinity.
        with operand_infs[0] | operand_infs[1]:
            make_inf(fp_type_props, result_exponent, result_mantissa)
        # Detect overflow.
        with operand_exponent_sums > exponent_max_value:
            if rounding_mode == RoundingMode.RNE:
                make_inf(fp_type_props, result_exponent, result_mantissa)
            else:
                make_largest_finite_number(
                    fp_type_props, result_exponent, result_mantissa
                )
        # If either operand is zero, if underflow occurred, or if either operand is
        # denormalized, the result is zero.
        with (
            operand_zeros[0]
            | operand_zeros[1]
            | (operand_exponent_sums < exponent_min_value)
            | operand_denorms[0]
            | operand_denorms[1]
        ):
            make_zero(result_exponent, result_mantissa)
        with pyrtl.otherwise:
            result_exponent |= raw_result_exponent
            result_mantissa |= raw_result_mantissa

    return pyrtl.concat(result_sign, result_exponent, result_mantissa)
