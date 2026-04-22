import pyrtl

from ._float_utils import (
    _fp_wire_struct,
    _RawResult,
    _RawResultGRS,
    _round_rne,
    check_kinds,
    make_denormals_zero,
    make_inf,
    make_largest_finite_number,
    make_nan,
    make_zero,
)
from ._types import FPTypeProperties, PyrtlFloatConfig, RoundingMode


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
    FP = _fp_wire_struct(num_exp_bits, num_mant_bits)

    # Denormalized numbers are not supported, so we flush them to zero.
    operands = tuple(
        make_denormals_zero(fp_type_props, op) for op in (operand_a, operand_b)
    )
    fps = _sort_operands(FP, operands)
    del operands

    # Align mantissas and compute both the addition and subtraction results.
    smaller_mantissa_shifted_grs, larger_mantissa_extended = _align_mantissa(fps)
    sum_result, sum_carry = _add_operands(
        fps[1].exponent, smaller_mantissa_shifted_grs, larger_mantissa_extended
    )
    difference_result, num_leading_zeros = _sub_operands(
        num_mant_bits,
        fps[1].exponent,
        smaller_mantissa_shifted_grs,
        larger_mantissa_extended,
    )
    del smaller_mantissa_shifted_grs, larger_mantissa_extended

    # Select the correct result based on operand signs, then round if needed.
    raw_result, rounding_exponent_incremented = _select_and_round(
        fp_type_props,
        fps,
        sum_result,
        difference_result,
        rounding_mode,
    )
    del sum_result, difference_result

    return _handle_special_cases(
        FP,
        fp_type_props,
        fps,
        raw_result,
        sum_carry,
        num_leading_zeros,
        rounding_mode,
        rounding_exponent_incremented,
    )


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


def _sort_operands(
    FP,
    operands: tuple,
) -> tuple:
    """
    Sorts operands by absolute value.

    :param FP: The FP wire_struct class for the current floating point type.
    :param operands: Tuple of two operand WireVectors with denormals flushed to zero.
    :return: Tuple of (smaller_fp, larger_fp) as FP wire_struct instances.
    """
    total_bits = operands[0].bitwidth
    sorted_operands = [pyrtl.WireVector(bitwidth=total_bits) for _ in range(2)]
    with pyrtl.conditional_assignment:
        # Compare the lower (total_bits - 1) bits, which excludes the sign bit,
        # to determine the operand with the smaller absolute value.
        with operands[0][: total_bits - 1] < operands[1][: total_bits - 1]:
            sorted_operands[0] |= operands[0]
            sorted_operands[1] |= operands[1]
        with pyrtl.otherwise:
            sorted_operands[0] |= operands[1]
            sorted_operands[1] |= operands[0]
    return tuple(FP(FP=op) for op in sorted_operands)


def _align_mantissa(
    fps: tuple,
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    """
    Aligns the smaller mantissa to the larger operand's exponent and computes
    the guard, round, and sticky (GRS) bits for RNE rounding.

    :param fps: Tuple of (smaller_fp, larger_fp) as FP wire_struct instances.
    :return: Tuple of (smaller_mantissa_shifted_grs, larger_mantissa_extended).
    """
    num_mant_bits = fps[0].mantissa.bitwidth
    mantissas_with_leading_1 = tuple(
        pyrtl.concat(pyrtl.Const(1), fp.mantissa) for fp in fps
    )

    # Align mantissas by shifting the smaller one to match the larger's exponent.
    # Shifting the mantissa right by one divides the value by two, while adding
    # one to the exponent multiplies the value by two. Doing both simultaneously
    # preserves the value while matching the operands' exponents for addition.
    shift_amount = fps[1].exponent - fps[0].exponent
    smaller_mantissa_shifted = pyrtl.shift_right_logical(
        mantissas_with_leading_1[0], shift_amount
    )

    # RNE rounding uses the guard, round, and sticky bits.
    # When shifting the smaller mantissa to the right, some bits are shifted out.
    # The most significant bit to the right of the mantissa after shifting becomes
    # the guard bit, the next bit becomes the round bit, and any remaining bits
    # are ORed together to form the sticky bit.
    # https://drilian.com/posts/2023.01.10-floating-point-numbers-and-rounding/
    grs = pyrtl.WireVector(bitwidth=3)
    with pyrtl.conditional_assignment:
        # If the smaller mantissa is shifted by 2 or more, the two most
        # significant bits shifted out are the guard and round bits, and the
        # sticky bit is the OR of all remaining bits.
        with shift_amount >= 2:
            guard_and_round = pyrtl.shift_right_logical(
                mantissas_with_leading_1[0], shift_amount - 2
            )[:2]
            # Mask with the least significant (shift_amount - 2) bits set to 1
            mask = (
                pyrtl.shift_left_logical(
                    pyrtl.Const(1, bitwidth=num_mant_bits),
                    shift_amount - 2,
                )
                - 1
            )
            sticky = (mantissas_with_leading_1[0] & mask) != 0
            grs |= pyrtl.concat(guard_and_round, sticky)
        # If the smaller mantissa is shifted by 1, the single bit shifted out
        # is the guard bit; the round bit and sticky bit are both 0.
        with shift_amount == 1:
            grs |= pyrtl.concat(
                mantissas_with_leading_1[0][0], pyrtl.Const(0, bitwidth=2)
            )
        # If not shifted, guard, round, and sticky bits are all 0.
        with pyrtl.otherwise:
            grs |= 0

    # Concatenate the shifted smaller mantissa with the GRS bits, and extend
    # the larger mantissa with three zeros to align it with the smaller mantissa.
    smaller_mantissa_shifted_grs = pyrtl.concat(smaller_mantissa_shifted, grs)
    larger_mantissa_extended = pyrtl.concat(
        mantissas_with_leading_1[1], pyrtl.Const(0, bitwidth=3)
    )
    return smaller_mantissa_shifted_grs, larger_mantissa_extended


def _select_and_round(
    fp_type_props: FPTypeProperties,
    fps: tuple,
    sum_result: _RawResultGRS,
    diff_result: _RawResultGRS,
    rounding_mode: RoundingMode,
) -> tuple:
    """
    Selects the addition or subtraction result based on operand signs, then
    applies RNE rounding if configured.

    :param fp_type_props: Floating point type properties.
    :param fps: Tuple of (smaller_fp, larger_fp) as FP wire_struct instances.
    :param sum_result: _RawResultGRS from the addition operation.
    :param diff_result: _RawResultGRS from the subtraction operation.
    :param rounding_mode: The rounding mode to apply.
    :return: Tuple of (_RawResult, rounding_exponent_incremented). The second
        element is None for RTZ rounding mode.
    """
    num_exp_bits = fp_type_props.num_exponent_bits
    num_mant_bits = fp_type_props.num_mantissa_bits

    raw_result = _RawResult(
        exponent=pyrtl.WireVector(bitwidth=num_exp_bits),
        mantissa=pyrtl.WireVector(bitwidth=num_mant_bits),
    )
    if rounding_mode == RoundingMode.RNE:
        raw_grs = pyrtl.WireVector(bitwidth=3)

    # Determine whether we need to add or subtract the operands.
    with pyrtl.conditional_assignment:
        # If the operands have the same sign, we perform addition.
        # For example, (+a) + (+b) or (-a) + (-b).
        with fps[0].sign == fps[1].sign:
            raw_result.exponent |= sum_result.exponent
            raw_result.mantissa |= sum_result.mantissa
            if rounding_mode == RoundingMode.RNE:
                raw_grs |= sum_result.grs
        # If the operands have different signs, we perform subtraction.
        # For example, (+a) + (-b) or (-a) + (+b).
        with pyrtl.otherwise:
            raw_result.exponent |= diff_result.exponent
            raw_result.mantissa |= diff_result.mantissa
            if rounding_mode == RoundingMode.RNE:
                raw_grs |= diff_result.grs

    if rounding_mode == RoundingMode.RNE:
        return _round_rne(raw_result, raw_grs)
    # No additional rounding logic needed for RTZ rounding mode
    return raw_result, None


def _handle_special_cases(
    FP,
    fp_type_props,
    fps: tuple,
    raw_result: _RawResult,
    sum_carry: pyrtl.WireVector,
    num_leading_zeros: pyrtl.WireVector,
    rounding_mode: RoundingMode,
    rounding_exponent_incremented,
):
    """
    Handles special cases: NaN, infinity, zero, overflow, and underflow.

    :param FP: The FP wire_struct class for the current floating point type.
    :param fp_type_props: Floating point type properties.
    :param fps: Tuple of (smaller_fp, larger_fp) as FP wire_struct instances.
    :param raw_result: Pre-rounding result as a _RawResult.
    :param sum_carry: Carry bit from the addition operation.
    :param num_leading_zeros: Leading zero count from the subtraction normalization.
    :param rounding_mode: The rounding mode being used.
    :param rounding_exponent_incremented: Whether rounding incremented the exponent
        (None for RTZ mode).
    :return: The final FP wire_struct result.
    """
    num_exp_bits = fp_type_props.num_exponent_bits

    operand_kinds = tuple(check_kinds(fp) for fp in fps)

    # Pre-compute special value constants for use inside conditional_assignment.
    final_result = FP(sign=None, exponent=None, mantissa=None)
    nan_exp, nan_mant = make_nan(fp_type_props)
    inf_exp, inf_mant = make_inf(fp_type_props)
    zero_exp, zero_mant = make_zero(fp_type_props)
    largest_exp, largest_mant = make_largest_finite_number(fp_type_props)

    # Check for overflow on addition.
    # We check for overflow by calculating the max value of the larger
    # operand's exponent. This value can vary depending on the operands.
    # If there was a carry out from the addition, the result exponent is
    # incremented by 1. Additionally, if rounding causes the exponent to
    # increment, we need to account for that as well. Therefore, we
    # subtract these increments from the absolute maximum exponent, which
    # is one less than the all-1s exponent (reserved for infinity/NaN).
    # However, instead of performing subtractions in hardware, we use
    # conditional assignments to determine the appropriate maximum exponent
    # value. Since we are merely selecting among three possible values,
    # instantiating a subtractor would be overkill.
    base_exponent_max_value = 2**num_exp_bits - 2
    exponent_max_value = pyrtl.WireVector(bitwidth=num_exp_bits)
    if rounding_mode == RoundingMode.RNE:
        with pyrtl.conditional_assignment:
            with rounding_exponent_incremented & sum_carry:
                exponent_max_value |= base_exponent_max_value - 2
            with rounding_exponent_incremented | sum_carry:
                exponent_max_value |= base_exponent_max_value - 1
            with pyrtl.otherwise:
                exponent_max_value |= base_exponent_max_value
    else:
        with pyrtl.conditional_assignment:
            with sum_carry:
                exponent_max_value |= base_exponent_max_value - 1
            with pyrtl.otherwise:
                exponent_max_value |= base_exponent_max_value

    # Check for underflow on subtraction.
    # We check for underflow by computing the min value of the larger
    # operand's exponent. As with overflow, this value can vary depending
    # on the operands. We subtract the number of leading zeros from the
    # larger exponent to obtain the subtraction exponent. Additionally,
    # if rounding causes the exponent to increment, we need to account
    # for that. Therefore, we add the number of leading zeros and
    # subtract the rounding increment from the absolute minimum exponent,
    # which is one greater than the all-0s exponent (reserved for
    # zero and denormals). Similarly to overflow checking, we use a
    # combinational assignment to account for the rounding increment,
    # avoiding the need to instantiate an adder.
    base_exponent_min_value = pyrtl.WireVector(bitwidth=num_exp_bits)
    if rounding_mode == RoundingMode.RNE:
        with pyrtl.conditional_assignment:
            with rounding_exponent_incremented:
                base_exponent_min_value |= 0
            with pyrtl.otherwise:
                base_exponent_min_value |= 1
    else:
        base_exponent_min_value <<= 1
    exponent_min_value = num_leading_zeros + base_exponent_min_value

    with pyrtl.conditional_assignment:
        # If either operand is NaN, or if both operands are infinities with
        # opposite signs, the result is NaN.
        with (
            operand_kinds[0].is_nan
            | operand_kinds[1].is_nan
            | (
                operand_kinds[0].is_inf
                & operand_kinds[1].is_inf
                & (fps[1].sign != fps[0].sign)
            )
        ):
            final_result.sign |= fps[1].sign
            final_result.exponent |= nan_exp
            final_result.mantissa |= nan_mant

        # If either operand is infinity, result is infinity with that sign.
        with operand_kinds[0].is_inf:
            final_result.sign |= fps[1].sign
            final_result.exponent |= inf_exp
            final_result.mantissa |= inf_mant
        with operand_kinds[1].is_inf:
            final_result.sign |= fps[1].sign
            final_result.exponent |= inf_exp
            final_result.mantissa |= inf_mant

        # If operands are equal in magnitude but opposite in sign, the result is +0.
        with (
            (fps[0].mantissa == fps[1].mantissa)
            & (fps[0].exponent == fps[1].exponent)
            & (fps[1].sign != fps[0].sign)
        ):
            final_result.sign |= 0
            final_result.exponent |= zero_exp
            final_result.mantissa |= zero_mant

        # If either operand is zero, the result is the other operand.
        with operand_kinds[0].is_zero:
            final_result.sign |= fps[1].sign
            final_result.mantissa |= fps[1].mantissa
            final_result.exponent |= fps[1].exponent
        with operand_kinds[1].is_zero:
            final_result.sign |= fps[0].sign
            final_result.mantissa |= fps[0].mantissa
            final_result.exponent |= fps[0].exponent

        # Checks if an addition was performed and the result overflowed.
        with (fps[0].sign == fps[1].sign) & (fps[1].exponent > exponent_max_value):
            final_result.sign |= fps[1].sign
            # IEEE 754 Section 7.4: On overflow, RNE rounds to infinity,
            # while truncation rounds to the largest finite number.
            if rounding_mode == RoundingMode.RNE:
                final_result.exponent |= inf_exp
                final_result.mantissa |= inf_mant
            else:
                final_result.exponent |= largest_exp
                final_result.mantissa |= largest_mant

        # Checks if a subtraction was performed and the result underflowed.
        with (fps[0].sign != fps[1].sign) & (fps[1].exponent < exponent_min_value):
            final_result.sign |= fps[1].sign
            final_result.exponent |= zero_exp
            final_result.mantissa |= zero_mant
        # Otherwise no special cases apply: this is the common case.
        with pyrtl.otherwise:
            final_result.sign |= fps[1].sign
            final_result.exponent |= raw_result.exponent
            final_result.mantissa |= raw_result.mantissa

    return final_result


def _add_operands(
    larger_operand_exponent: pyrtl.WireVector,
    smaller_mantissa_shifted_grs: pyrtl.WireVector,
    larger_mantissa_extended: pyrtl.WireVector,
) -> tuple[_RawResultGRS, pyrtl.WireVector]:
    """
    Helper function for performing addition of two floating point mantissas.

    :param larger_operand_exponent: Exponent of the larger operand.
    :param smaller_mantissa_shifted_grs: Mantissa of the smaller operand
        shifted to align with the larger operand and concatenated with GRS.
    :param larger_mantissa_extended: Larger mantissa with three zeros.
    :return: Tuple of (_RawResultGRS, carry bit).
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
    return _RawResultGRS(sum_exponent, sum_mantissa, sum_grs), sum_carry


def _sub_operands(
    num_mant_bits: int,
    larger_operand_exponent: pyrtl.WireVector,
    smaller_mantissa_shifted_grs: pyrtl.WireVector,
    larger_mantissa_extended: pyrtl.WireVector,
) -> tuple[_RawResultGRS, pyrtl.WireVector]:
    """
    Helper function for performing subtraction of two floating point mantissas.

    :param num_mant_bits: Number of mantissa bits.
    :param larger_operand_exponent: Exponent of the larger operand.
    :param smaller_mantissa_shifted_grs: Mantissa of the smaller operand
        shifted to align with the larger operand and concatenated with GRS.
    :param larger_mantissa_extended: Larger mantissa with three zeros.
    :return: Tuple of (_RawResultGRS, num leading zeros).
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

    difference_mantissa_grs = pyrtl.WireVector(bitwidth=num_mant_bits + 4)
    difference_mantissa_grs <<= larger_mantissa_extended - smaller_mantissa_shifted_grs
    # Normalize result by shifting left until leading 1 is in position.
    num_leading_zeros = leading_zero_priority_encoder(
        difference_mantissa_grs, num_mant_bits + 1
    )
    difference_mantissa_grs_shifted = pyrtl.shift_left_logical(
        difference_mantissa_grs, num_leading_zeros
    )
    difference_mantissa = difference_mantissa_grs_shifted[3:]
    difference_grs = difference_mantissa_grs_shifted[:3]
    # Adjust the exponent by subtracting the number of leading zeros.
    difference_exponent = larger_operand_exponent - num_leading_zeros
    return _RawResultGRS(
        difference_exponent, difference_mantissa, difference_grs
    ), num_leading_zeros
