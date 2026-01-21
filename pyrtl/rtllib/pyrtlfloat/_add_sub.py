import pyrtl

from ._float_utills import (
    get_exponent,
    get_mantissa,
    get_sign,
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


def add(
    config: PyrtlFloatConfig,
    operand_a: pyrtl.WireVector,
    operand_b: pyrtl.WireVector,
) -> pyrtl.WireVector:
    """
    Performs floating point addition of two WireVectors.

    :param config: Configuration for the floating point type and rounding mode.
    :param operand_a: The first floating point operand as a WireVector.
    :param operand_b: The second floating point operand as a WireVector.
    :return: The result of the addition as a WireVector.
    """
    fp_type_props = config.fp_type_properties
    rounding_mode = config.rounding_mode
    num_exp_bits = fp_type_props.num_exponent_bits
    num_mant_bits = fp_type_props.num_mantissa_bits
    total_bits = num_exp_bits + num_mant_bits + 1

    # Denormalized numbers are not supported, so we flush them to zero.
    operand_a_daz = make_denormals_zero(fp_type_props, operand_a)
    operand_b_daz = make_denormals_zero(fp_type_props, operand_b)

    # operand_smaller is the operand with the smaller absolute value and
    # operand_larger is the operand with the larger absolute value.
    operand_smaller = pyrtl.WireVector(bitwidth=total_bits)
    operand_larger = pyrtl.WireVector(bitwidth=total_bits)

    # Determine which operand is smaller/larger, then assign operand_smaller and
    # operand_larger accordingly.
    with pyrtl.conditional_assignment:
        exponent_and_mantissa_len = num_mant_bits + num_exp_bits
        with (
            operand_a_daz[:exponent_and_mantissa_len]
            < operand_b_daz[:exponent_and_mantissa_len]
        ):
            operand_smaller |= operand_a_daz
            operand_larger |= operand_b_daz
        with pyrtl.otherwise:
            operand_smaller |= operand_b_daz
            operand_larger |= operand_a_daz

    # Extract the sign, exponent, and mantissa of both operands.
    smaller_operand_sign = get_sign(fp_type_props, operand_smaller)
    larger_operand_sign = get_sign(fp_type_props, operand_larger)
    smaller_operand_exponent = get_exponent(fp_type_props, operand_smaller)
    larger_operand_exponent = get_exponent(fp_type_props, operand_larger)
    smaller_operand_mantissa = pyrtl.concat(
        pyrtl.Const(1), get_mantissa(fp_type_props, operand_smaller)
    )
    larger_operand_mantissa = pyrtl.concat(
        pyrtl.Const(1), get_mantissa(fp_type_props, operand_larger)
    )

    # Align mantissas by shifting the smaller one to match the larger's exponent.
    smaller_mantissa_shift_amount = larger_operand_exponent - smaller_operand_exponent
    smaller_mantissa_shifted = pyrtl.shift_right_logical(
        smaller_operand_mantissa, smaller_mantissa_shift_amount
    )

    # RNE rounding uses the guard, round, and sticky bits.
    # When shifting the smaller mantissa to the right, some bits are shifted out.
    # The first bit shifted out becomes the guard bit, the second becomes the round bit,
    # and any remaining bits are ORed together to form the sticky bit.
    # https://drilian.com/posts/2023.01.10-floating-point-numbers-and-rounding/
    grs = pyrtl.WireVector(bitwidth=3)  # guard, round, sticky bits
    with pyrtl.conditional_assignment:
        # If the smaller mantissa is shifted by 2 or more, the first two bits
        # shifted out are the guard and round bits, and the sticky bit is
        # the OR of all remaining bits.
        with smaller_mantissa_shift_amount >= 2:
            guard_and_round = pyrtl.shift_right_logical(
                smaller_operand_mantissa, smaller_mantissa_shift_amount - 2
            )[:2]
            # Mask with the least significant (shift_amount - 2) bits set to 1
            mask = (
                pyrtl.shift_left_logical(
                    pyrtl.Const(1, bitwidth=num_mant_bits),
                    smaller_mantissa_shift_amount - 2,
                )
                - 1
            )
            sticky = (smaller_operand_mantissa & mask) != 0
            grs |= pyrtl.concat(guard_and_round, sticky)
        # If the smaller mantissa is shifted by 1, the first bit shifted out
        # is the guard bit, the round bit and sticky bit are both 0.
        with smaller_mantissa_shift_amount == 1:
            grs |= pyrtl.concat(smaller_operand_mantissa[0], pyrtl.Const(0, bitwidth=2))
        # If not shifted, guard, round, and sticky bits are all 0.
        with pyrtl.otherwise:
            grs |= 0

    # Concatenate the shifted smaller mantissa with the guard, round, and sticky bits.
    smaller_mantissa_shifted_grs = pyrtl.concat(smaller_mantissa_shifted, grs)

    # Extend the larger mantissa by concatenating three zeros so it aligns with the
    # smaller mantissa, which was extended with GRS bits.
    larger_mantissa_extended = pyrtl.concat(
        larger_operand_mantissa, pyrtl.Const(0, bitwidth=3)
    )

    # Perform addition of operands.
    sum_exponent, sum_mantissa, sum_grs, sum_carry = _add_operands(
        larger_operand_exponent,
        smaller_mantissa_shifted_grs,
        larger_mantissa_extended,
    )

    # Perform subtraction of operands.
    sub_exponent, sub_mantissa, sub_grs, num_leading_zeros = _sub_operands(
        num_mant_bits,
        larger_operand_exponent,
        smaller_mantissa_shifted_grs,
        larger_mantissa_extended,
    )

    # Exponent and mantissa for raw addition or subtraction result, before
    # rounding and handling special cases.
    raw_result_exponent = pyrtl.WireVector(bitwidth=num_exp_bits)
    raw_result_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)
    if rounding_mode == RoundingMode.RNE:
        raw_result_grs = pyrtl.WireVector(bitwidth=3)

    # Determine whether we need to add or subtract the operands.
    with pyrtl.conditional_assignment:
        # If the operands have the same sign, we perform addition.
        # For example, (+a) + (+b) or (-a) + (-b).
        with smaller_operand_sign == larger_operand_sign:
            raw_result_exponent |= sum_exponent
            raw_result_mantissa |= sum_mantissa
            if rounding_mode == RoundingMode.RNE:
                raw_result_grs |= sum_grs
        # If the operands have different signs, we perform subtraction.
        # For example, (+a) + (-b) or (-a) + (+b).
        with pyrtl.otherwise:
            raw_result_exponent |= sub_exponent
            raw_result_mantissa |= sub_mantissa
            if rounding_mode == RoundingMode.RNE:
                raw_result_grs |= sub_grs

    # Round the result if using RNE rounding mode.
    if rounding_mode == RoundingMode.RNE:
        (
            raw_result_rounded_exponent,
            raw_result_rounded_mantissa,
            rounding_exponent_incremented,
        ) = _round(
            num_mant_bits,
            num_exp_bits,
            raw_result_exponent,
            raw_result_mantissa,
            raw_result_grs,
        )

    # Check whether the operands are special cases: NaN, infinity, or zero.
    smaller_operand_nan = is_nan(fp_type_props, operand_smaller)
    larger_operand_nan = is_nan(fp_type_props, operand_larger)
    smaller_operand_inf = is_inf(fp_type_props, operand_smaller)
    larger_operand_inf = is_inf(fp_type_props, operand_larger)
    smaller_operand_zero = is_zero(fp_type_props, operand_smaller)
    larger_operand_zero = is_zero(fp_type_props, operand_larger)

    # WireVectors for the final result after handling special cases.
    final_result_sign = pyrtl.WireVector(bitwidth=1)
    final_result_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)
    final_result_exponent = pyrtl.WireVector(bitwidth=num_exp_bits)

    # Handle special cases.
    with pyrtl.conditional_assignment:
        # If either operand is NaN, or if both operands are infinities with
        # opposite signs, the result is NaN.
        with (
            smaller_operand_nan
            | larger_operand_nan
            | (
                smaller_operand_inf
                & larger_operand_inf
                & (larger_operand_sign != smaller_operand_sign)
            )
        ):
            final_result_sign |= larger_operand_sign
            make_nan(fp_type_props, final_result_exponent, final_result_mantissa)

        # If either operand is infinity, result is infinity with that sign.
        with smaller_operand_inf:
            final_result_sign |= larger_operand_sign
            make_inf(fp_type_props, final_result_exponent, final_result_mantissa)
        with larger_operand_inf:
            final_result_sign |= larger_operand_sign
            make_inf(fp_type_props, final_result_exponent, final_result_mantissa)

        # If operands are equal in magnitude but opposite in sign, the result is +0.
        with (
            (smaller_operand_mantissa == larger_operand_mantissa)
            & (smaller_operand_exponent == larger_operand_exponent)
            & (larger_operand_sign != smaller_operand_sign)
        ):
            final_result_sign |= 0
            make_zero(final_result_exponent, final_result_mantissa)

        # If either operand is zero, the result is the other operand.
        with smaller_operand_zero:
            final_result_sign |= larger_operand_sign
            final_result_mantissa |= larger_operand_mantissa
            final_result_exponent |= larger_operand_exponent
        with larger_operand_zero:
            final_result_sign |= smaller_operand_sign
            final_result_mantissa |= smaller_operand_mantissa
            final_result_exponent |= smaller_operand_exponent

        # Check for overflow on addition.
        # We check for overflow by calculating the max value of the larger
        # operand's exponent. This value can vary depending on the operands.
        # If there was a carry out from the addition, the result exponent is
        # incremented by 1. Additionally, if rounding causes the exponent to
        # increment, we need to account for that as well. Therefore, we
        # subtract these increments from the absolute maximum exponent, which
        # is one less than the all-1s exponent (reserved for infinity/NaN).
        initial_larger_exponent_max_value = pyrtl.Const(2**num_exp_bits - 2)
        if rounding_mode == RoundingMode.RNE:
            larger_exponent_max_value = (
                initial_larger_exponent_max_value
                - sum_carry
                - rounding_exponent_incremented
            )
        else:
            larger_exponent_max_value = initial_larger_exponent_max_value - sum_carry
        # Checks if an addition was performed and the result overflowed.
        with (smaller_operand_sign == larger_operand_sign) & (
            larger_operand_exponent > larger_exponent_max_value
        ):
            final_result_sign |= larger_operand_sign
            if rounding_mode == RoundingMode.RNE:
                make_inf(fp_type_props, final_result_exponent, final_result_mantissa)
            else:
                make_largest_finite_number(
                    fp_type_props, final_result_exponent, final_result_mantissa
                )

        # Check for underflow on subtraction.
        # We check for underflow by computing the min value of the larger
        # operand's exponent. As with overflow, this value can vary depending
        # on the operands. We subtract the number of leading zeros from the
        # larger exponent to obtain the subtraction exponent. Additionally,
        # if rounding causes the exponent to increment, we need to account
        # for that. Therefore, we add the number of leading zeros and
        # subtract the rounding increment from the absolute minimum exponent,
        # which is one greater than the all-0s exponent (reserved for
        # zero and denormals).
        initial_larger_exponent_min_value = pyrtl.Const(1)
        if rounding_mode == RoundingMode.RNE:
            larger_exponent_min_value = (
                initial_larger_exponent_min_value
                + num_leading_zeros
                - rounding_exponent_incremented
            )
        else:
            larger_exponent_min_value = (
                initial_larger_exponent_min_value + num_leading_zeros
            )
        # Checks if a subtraction was performed and the result underflowed.
        with (smaller_operand_sign != larger_operand_sign) & (
            larger_operand_exponent < larger_exponent_min_value
        ):
            final_result_sign |= larger_operand_sign
            make_zero(final_result_exponent, final_result_mantissa)
        with pyrtl.otherwise:
            final_result_sign |= larger_operand_sign
            if rounding_mode == RoundingMode.RNE:
                final_result_exponent |= raw_result_rounded_exponent
                final_result_mantissa |= raw_result_rounded_mantissa
            else:
                final_result_exponent |= raw_result_exponent
                final_result_mantissa |= raw_result_mantissa

    return pyrtl.concat(final_result_sign, final_result_exponent, final_result_mantissa)


def sub(
    config: PyrtlFloatConfig,
    operand_a: pyrtl.WireVector,
    operand_b: pyrtl.WireVector,
) -> pyrtl.WireVector:
    """
    Performs floating point subtraction of two WireVectors.

    :param config: Configuration for the floating point type and rounding mode.
    :param operand_a: The first floating point operand as a WireVector.
    :param operand_b: The second floating point operand as a WireVector.
    :return: The result of the subtraction as a WireVector.
    """
    num_exp_bits = config.fp_type_properties.num_exponent_bits
    num_mant_bits = config.fp_type_properties.num_mantissa_bits
    operand_b_negated = operand_b ^ pyrtl.concat(
        pyrtl.Const(1, bitwidth=1),
        pyrtl.Const(0, bitwidth=num_exp_bits + num_mant_bits),
    )
    return add(config, operand_a, operand_b_negated)


def _add_operands(
    larger_operand_exponent: pyrtl.WireVector,
    smaller_mantissa_shifted_grs: pyrtl.WireVector,
    larger_mantissa_extended: pyrtl.WireVector,
) -> tuple[pyrtl.WireVector, pyrtl.WireVector, pyrtl.WireVector, pyrtl.WireVector]:
    """
    Helper function for performing addition of two floating point mantissas.

    :param larger_operand_exponent: Exponent of the larger operand.
    :param smaller_mantissa_shifted_grs: Mantissa of the smaller operand
        shifted to align with the larger operand and concatenated with GRS.
    :param larger_mantissa_extended: Larger mantissa with three zeros.
    :return: Tuple of (exponent, mantissa, GRS bits, carry bit).
    """
    sum_mantissa_grs = pyrtl.WireVector()
    sum_mantissa_grs <<= larger_mantissa_extended + smaller_mantissa_shifted_grs
    sum_carry = sum_mantissa_grs[-1]
    # Pick the correct bits for the mantissa and GRS based on carry out.
    sum_mantissa = pyrtl.select(sum_carry, sum_mantissa_grs[4:], sum_mantissa_grs[3:-1])
    sum_grs = pyrtl.select(
        sum_carry,
        pyrtl.concat(sum_mantissa_grs[2:4], sum_mantissa_grs[:2] != 0),
        sum_mantissa_grs[:3],
    )
    # Increment the exponent if there was a carry out.
    sum_exponent = pyrtl.select(
        sum_carry, larger_operand_exponent + 1, larger_operand_exponent
    )
    return sum_exponent, sum_mantissa, sum_grs, sum_carry


def _sub_operands(
    num_mant_bits: int,
    larger_operand_exponent: pyrtl.WireVector,
    smaller_mantissa_shifted_grs: pyrtl.WireVector,
    larger_mantissa_extended: pyrtl.WireVector,
) -> tuple[pyrtl.WireVector, pyrtl.WireVector, pyrtl.WireVector, pyrtl.WireVector]:
    """
    Helper function for performing subtraction of two floating point mantissas.

    :param num_mant_bits: Number of mantissa bits.
    :param larger_operand_exponent: Exponent of the larger operand.
    :param smaller_mantissa_shifted_grs: Mantissa of the smaller operand
        shifted to align with the larger operand and concatenated with GRS.
    :param larger_mantissa_extended: Larger mantissa with three zeros.
    :return: Tuple of (exponent, mantissa, GRS bits, num leading zeros).
    """

    # Priority encoder that counts the number of leading zeros in a WireVector.
    def leading_zero_priority_encoder(wire: pyrtl.WireVector, length: int):
        out = pyrtl.WireVector(
            bitwidth=pyrtl.infer_val_and_bitwidth(length - 1).bitwidth
        )
        with pyrtl.conditional_assignment:
            for i in range(wire.bitwidth - 1, wire.bitwidth - length - 1, -1):
                with wire[i]:
                    out |= wire.bitwidth - i - 1
        return out

    sub_mantissa_grs = pyrtl.WireVector(bitwidth=num_mant_bits + 4)
    sub_mantissa_grs <<= larger_mantissa_extended - smaller_mantissa_shifted_grs
    # Normalize result by shifting left until leading 1 is in position.
    num_leading_zeros = leading_zero_priority_encoder(
        sub_mantissa_grs, num_mant_bits + 1
    )
    sub_mantissa_grs_shifted = pyrtl.shift_left_logical(
        sub_mantissa_grs, num_leading_zeros
    )
    sub_mantissa = sub_mantissa_grs_shifted[3:]
    sub_grs = sub_mantissa_grs_shifted[:3]
    # Adjust the exponent by subtracting the number of leading zeros.
    sub_exponent = larger_operand_exponent - num_leading_zeros
    return sub_exponent, sub_mantissa, sub_grs, num_leading_zeros


def _round(
    num_mant_bits: int,
    num_exp_bits: int,
    raw_result_exponent: pyrtl.WireVector,
    raw_result_mantissa: pyrtl.WireVector,
    raw_result_grs: pyrtl.WireVector,
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    """
    Round the floating point result using round to nearest, ties to even (RNE).

    Uses the GRS bits to determine if the result needs to be rounded up.

    :param num_mant_bits: Number of mantissa bits.
    :param num_exp_bits: Number of exponent bits.
    :param raw_result_exponent: Exponent of the raw result before rounding.
    :param raw_result_mantissa: Mantissa of the raw result before rounding.
    :param raw_result_grs: GRS bits of the raw result before rounding.
    :return: Tuple of (rounded exponent, rounded mantissa, exponent
        incremented flag).
    """
    last = raw_result_mantissa[0]
    guard = raw_result_grs[2]
    round = raw_result_grs[1]
    sticky = raw_result_grs[0]
    # If guard bit is not set, number is closer to smaller value: no round up.
    # If guard bit is set and round or sticky is set, round up.
    # If guard bit is set but round and sticky are not set, value is exactly
    # halfway. Following round-to-nearest ties-to-even, round up if last bit
    # of mantissa is 1 (to make it even); otherwise do not round up.
    round_up = guard & (last | round | sticky)
    raw_result_rounded_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)
    raw_result_rounded_exponent = pyrtl.WireVector(bitwidth=num_exp_bits)
    # Whether exponent was incremented due to rounding (for overflow check).
    rounding_exponent_incremented = pyrtl.WireVector(bitwidth=1)
    with pyrtl.conditional_assignment:
        with round_up:
            # If rounding causes a mantissa overflow, we need to increment the exponent.
            with raw_result_mantissa == (1 << num_mant_bits) - 1:
                raw_result_rounded_mantissa |= 0
                raw_result_rounded_exponent |= raw_result_exponent + 1
                rounding_exponent_incremented |= 1
            with pyrtl.otherwise:
                raw_result_rounded_mantissa |= raw_result_mantissa + 1
                raw_result_rounded_exponent |= raw_result_exponent
                rounding_exponent_incremented |= 0
        with pyrtl.otherwise:
            raw_result_rounded_mantissa |= raw_result_mantissa
            raw_result_rounded_exponent |= raw_result_exponent
            rounding_exponent_incremented |= 0
    return (
        raw_result_rounded_exponent,
        raw_result_rounded_mantissa,
        rounding_exponent_incremented,
    )
