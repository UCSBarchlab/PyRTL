import pyrtl
from pyrtl.rtllib.float.types import FloatType, RoundingMode
from pyrtl.rtllib.float.utils import (
    _RawResult,
    _RawResultGRS,
    _round_rne,
    check_kinds,
    get_default_rounding_mode,
    make_denormals_zero,
    make_inf_like,
    make_largest_finite_number_like,
    make_nan_like,
)


def add(
    operand_a: FloatType, operand_b: FloatType, rounding_mode: RoundingMode = None
) -> FloatType:
    """Performs floating point addition.

    The two operands must share the same ``Float`` type. Adding different floating point
    types is not supported.

    Denormalized numbers are not supported. Denormalized numbers will be flushed to
    zero.

    The return value's ``Float`` type will match the operand ``Float`` type. For
    example, if you ``add`` two :class:`~.Float16`, the result will be a
    :class:`~.Float16`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    The following example computes ``1.0 + 2.0``. This is a bare-metal example, directly
    manipulating the raw ``sign``, ``exponent``, and ``mantissa`` in IEEE 754 16-bit
    floating point representation. See `IEEE 754 Internal Representation
    <https://en.wikipedia.org/wiki/Floating-point_arithmetic#Internal_representation>`_
    for more details::

        >>> import pyrtl.rtllib.float as rtlfloat

        >>> a = rtlfloat.Float16(name="a", component_type=pyrtl.Input)
        >>> b = rtlfloat.Float16(name="b", component_type=pyrtl.Input)

        >>> sum = rtlfloat.Float16(name="sum", Float16=None)
        >>> sum <<= rtlfloat.add(a, b)

        >>> # IEEE 754 numbers are stored as a sign bit, mantissa, and exponent. The
        >>> # represented number's absolute value is 1.{mantissa} * 2 ** {exponent}
        >>> #
        >>> # All mantissas have this implied `1` before the binary point. {mantissa}
        >>> # only stores the bits after this implied `1` and binary point.
        >>> #
        >>> # IEEE 754 exponents are stored with a bias to simplify comparisons. An
        >>> # exponent {x} is stored as {x + exponent_bias}.
        >>> exponent_bias = 2 ** (sum.exponent.bitwidth - 1) - 1

        >>> # Create a=1.0, represented as 1.0 * 2 ** 0.
        >>> a_one = {"a.sign": 0, "a.exponent": 0 + exponent_bias, "a.mantissa": 0}

        >>> # Create b=2.0, represented as 1.0 * 2 ** 1.
        >>> b_two = {"b.sign": 0, "b.exponent": 1 + exponent_bias, "b.mantissa": 0}

        >>> sim = pyrtl.Simulation()
        >>> sim.step(a_one | b_two)

        >>> # The sum should be 3.0, represented as 0b1.1 * 2 ** 1.
        >>> # Note that this 0b1.1 is in binary! Multiplying by 2 is equivalent to
        >>> # left-shifting by 1, and 0b1.1 << 1 == 0b11, which is 3 in decimal.
        >>> sim.inspect("sum.sign")
        0
        >>> sim.inspect("sum.exponent") - exponent_bias
        1
        >>> bin(sim.inspect("sum.mantissa"))
        '0b1000000000'
        >>> bin(1 << (sum.mantissa.bitwidth - 1))
        '0b1000000000'

    :param operand_a:
    :param operand_b:
    :param rounding_mode: Rounding mode, defaults to :attr:`~.RoundingMode.RNE`. The
        default can be changed with :func:`.set_default_rounding_mode`.

    :return: The sum, as an instance of the operand ``Float`` type.
    """
    if rounding_mode is None:
        rounding_mode = get_default_rounding_mode()

    if type(operand_a) is not type(operand_b):
        msg = (
            f"Different operand types ({type(operand_a)}, {type(operand_b)}) are not "
            "supported."
        )
        raise pyrtl.PyrtlError(msg)

    # Denormalized numbers are not supported, so we flush them to zero.
    operands = tuple(make_denormals_zero(op) for op in (operand_a, operand_b))
    sorted_operands = _sort_operands(operands)
    del operands

    # Align mantissas and compute both the addition and subtraction results.
    smaller_mantissa_shifted_grs, larger_mantissa_extended = _align_mantissa(
        sorted_operands
    )
    sum_result, sum_carry = _add_operands(
        sorted_operands[1].exponent,
        smaller_mantissa_shifted_grs,
        larger_mantissa_extended,
    )
    difference_result, num_leading_zeros = _sub_operands(
        operand_a.mantissa.bitwidth,
        sorted_operands[1].exponent,
        smaller_mantissa_shifted_grs,
        larger_mantissa_extended,
    )
    del smaller_mantissa_shifted_grs, larger_mantissa_extended

    # Select the correct result based on operand signs, then round if needed.
    raw_result, rounding_exponent_incremented = _select_and_round(
        sorted_operands,
        sum_result,
        difference_result,
        rounding_mode,
    )
    del sum_result, difference_result

    return _handle_special_cases(
        sorted_operands,
        raw_result,
        sum_carry,
        num_leading_zeros,
        rounding_mode,
        rounding_exponent_incremented,
    )


def sub(
    operand_a: FloatType, operand_b: FloatType, rounding_mode: RoundingMode = None
) -> FloatType:
    """Performs floating point subtraction.

    The two operands must share the same ``Float`` type. Subtracting different floating
    point types is not supported.

    Denormalized numbers are not supported. Denormalized numbers will be flushed to
    zero.

    The return value's ``Float`` type will match the operand ``Float`` type. For
    example, if you ``sub`` two :class:`~.Float16`, the result will be a
    :class:`~.Float16`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    The following example computes ``1.0 - 2.0``. This is a bare-metal example, directly
    manipulating the raw ``sign``, ``exponent``, and ``mantissa`` in IEEE 754 16-bit
    floating point representation. See the documentation for :func:`add` and `IEEE 754
    Internal Representation
    <https://en.wikipedia.org/wiki/Floating-point_arithmetic#Internal_representation>`_
    for more details::

        >>> import pyrtl.rtllib.float as rtlfloat

        >>> a = rtlfloat.Float16(name="a", component_type=pyrtl.Input)
        >>> b = rtlfloat.Float16(name="b", component_type=pyrtl.Input)

        >>> difference = rtlfloat.Float16(name="difference", Float16=None)
        >>> difference <<= rtlfloat.sub(a, b)

        >>> # See the `add` example for IEEE 754 representation background.
        >>> exponent_bias = 2 ** (difference.exponent.bitwidth - 1) - 1

        >>> # Create a=1.0, represented as 1.0 * 2 ** 0.
        >>> a_one = {"a.sign": 0, "a.exponent": 0 + exponent_bias, "a.mantissa": 0}

        >>> # Create b=2.0, represented as 1.0 * 2 ** 1.
        >>> b_two = {"b.sign": 0, "b.exponent": 1 + exponent_bias, "b.mantissa": 0}

        >>> sim = pyrtl.Simulation()
        >>> sim.step(a_one | b_two)

        >>> # The difference should be -1.0, represented as -1.0 * 2 ** 0.
        >>> sim.inspect("difference.sign")
        1
        >>> sim.inspect("difference.exponent") - exponent_bias
        0
        >>> sim.inspect("difference.mantissa")
        0

    :param operand_a:
    :param operand_b:
    :param rounding_mode: Rounding mode, defaults to :attr:`~.RoundingMode.RNE`. The
        default can be changed with :func:`.set_default_rounding_mode`.

    :return: The difference, as an instance of the operand ``Float`` type.
    """
    operand_b_negated = type(operand_b)(
        sign=~operand_b.sign,
        exponent=operand_b.exponent,
        mantissa=operand_b.mantissa,
    )
    return add(operand_a, operand_b_negated, rounding_mode)


def _sort_operands(
    operands: tuple[FloatType, FloatType],
) -> tuple[FloatType, FloatType]:
    """Sorts ``operands`` by absolute value.

    :param operands: Tuple of two operand ``Floats`` with denormals flushed to zero.

    :return: Tuple of ``(smaller_operand, larger_operand)``, as instances of the operand
             type.
    """
    sorted_operands = [
        pyrtl.WireVector(bitwidth=operands[0].bitwidth) for _ in range(2)
    ]
    with pyrtl.conditional_assignment:
        # Compare the concatenated exponents and mantissas to determine the operand with
        # the smaller absolute value.
        with pyrtl.concat(operands[0].exponent, operands[0].mantissa) < pyrtl.concat(
            operands[1].exponent, operands[1].mantissa
        ):
            sorted_operands[0] |= operands[0]
            sorted_operands[1] |= operands[1]
        with pyrtl.otherwise:
            sorted_operands[0] |= operands[1]
            sorted_operands[1] |= operands[0]
    return tuple(type(operands[0])(_value=op) for op in sorted_operands)


def _align_mantissa(
    sorted_operands: tuple[FloatType, FloatType],
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    """Aligns the smaller mantissa to the larger operand's exponent and computes the
    guard, round, and sticky (``GRS``) bits for ``RNE`` rounding.

    :param sorted_operands: Tuple of ``(smaller_operand, larger_operand)`` ``Floats``.

    :return: Tuple of ``(smaller_mantissa_shifted_grs, larger_mantissa_extended)``.
    """
    num_mant_bits = sorted_operands[0].mantissa.bitwidth
    mantissas_with_leading_1 = tuple(
        pyrtl.concat(pyrtl.Const(1), operand.mantissa) for operand in sorted_operands
    )

    # Align mantissas by shifting the smaller one to match the larger's exponent.
    # Shifting the mantissa right by one divides the value by two, while adding
    # one to the exponent multiplies the value by two. Doing both simultaneously
    # preserves the value while matching the operands' exponents for addition.
    shift_amount = sorted_operands[1].exponent - sorted_operands[0].exponent
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
    sorted_operands: tuple[FloatType, FloatType],
    sum_result: _RawResultGRS,
    diff_result: _RawResultGRS,
    rounding_mode: RoundingMode,
) -> tuple:
    """Selects the addition or subtraction result based on operand signs, then applies
    ``RNE`` rounding if configured.

    :param sorted_operands: Tuple of ``(smaller_operand, larger_operand)`` as
        ``Floats``.
    :param sum_result: ``_RawResultGRS`` from addition.
    :param diff_result: ``_RawResultGRS`` from subtraction.
    :param rounding_mode: The rounding mode to apply.

    :return: Tuple of ``(_RawResult, rounding_exponent_incremented)``. The second
             element is ``None`` for ``RTZ`` rounding mode.
    """
    num_exp_bits = sorted_operands[0].exponent.bitwidth
    num_mant_bits = sorted_operands[0].mantissa.bitwidth

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
        with sorted_operands[0].sign == sorted_operands[1].sign:
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
    sorted_operands: tuple[FloatType, FloatType],
    raw_result: _RawResult,
    sum_carry: pyrtl.WireVector,
    num_leading_zeros: pyrtl.WireVector,
    rounding_mode: RoundingMode,
    rounding_exponent_incremented,
) -> FloatType:
    """Handles special cases: NaN, infinity, zero, overflow, and underflow.

    :param sorted_operands: Tuple of ``(smaller_operand, larger_operand)`` as
        ``Floats``.
    :param raw_result: Pre-rounding result as a ``_RawResult``.
    :param sum_carry: Carry bit from addition.
    :param num_leading_zeros: Leading zero count from the subtraction normalization.
    :param rounding_mode: The rounding mode being used.
    :param rounding_exponent_incremented: Whether rounding incremented the exponent
        (``None`` for ``RTZ`` mode).

    :return: The final sum or difference, as an instance of the ``sorted_operand``
             ``Float`` type.
    """
    num_exp_bits = sorted_operands[0].exponent.bitwidth

    operand_kinds = tuple(check_kinds(operand) for operand in sorted_operands)

    # Pre-compute special value constants for use inside conditional_assignment.
    final_result = type(sorted_operands[0])(sign=None, exponent=None, mantissa=None)
    nan_exp, nan_mant = make_nan_like(sorted_operands[0])
    inf_exp, inf_mant = make_inf_like(sorted_operands[0])
    largest_exp, largest_mant = make_largest_finite_number_like(sorted_operands[0])

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
                & (sorted_operands[1].sign != sorted_operands[0].sign)
            )
        ):
            final_result.sign |= sorted_operands[1].sign
            final_result.exponent |= nan_exp
            final_result.mantissa |= nan_mant

        # If either operand is infinity, result is infinity with that sign.
        with operand_kinds[0].is_inf:
            final_result.sign |= sorted_operands[1].sign
            final_result.exponent |= inf_exp
            final_result.mantissa |= inf_mant
        with operand_kinds[1].is_inf:
            final_result.sign |= sorted_operands[1].sign
            final_result.exponent |= inf_exp
            final_result.mantissa |= inf_mant

        # If operands are equal in magnitude but opposite in sign, the result is +0.
        with (
            (sorted_operands[0].mantissa == sorted_operands[1].mantissa)
            & (sorted_operands[0].exponent == sorted_operands[1].exponent)
            & (sorted_operands[1].sign != sorted_operands[0].sign)
        ):
            final_result.sign |= 0
            final_result.exponent |= 0
            final_result.mantissa |= 0

        # If either operand is zero, the result is the other operand.
        with operand_kinds[0].is_zero:
            final_result.sign |= sorted_operands[1].sign
            final_result.mantissa |= sorted_operands[1].mantissa
            final_result.exponent |= sorted_operands[1].exponent
        with operand_kinds[1].is_zero:
            final_result.sign |= sorted_operands[0].sign
            final_result.mantissa |= sorted_operands[0].mantissa
            final_result.exponent |= sorted_operands[0].exponent

        # Checks if an addition was performed and the result overflowed.
        with (sorted_operands[0].sign == sorted_operands[1].sign) & (
            sorted_operands[1].exponent > exponent_max_value
        ):
            final_result.sign |= sorted_operands[1].sign
            # IEEE 754 Section 7.4: On overflow, RNE rounds to infinity,
            # while truncation rounds to the largest finite number.
            if rounding_mode == RoundingMode.RNE:
                final_result.exponent |= inf_exp
                final_result.mantissa |= inf_mant
            else:
                final_result.exponent |= largest_exp
                final_result.mantissa |= largest_mant

        # Checks if a subtraction was performed and the result underflowed.
        with (sorted_operands[0].sign != sorted_operands[1].sign) & (
            sorted_operands[1].exponent < exponent_min_value
        ):
            final_result.sign |= sorted_operands[1].sign
            final_result.exponent |= 0
            final_result.mantissa |= 0
        # Otherwise no special cases apply: this is the common case.
        with pyrtl.otherwise:
            final_result.sign |= sorted_operands[1].sign
            final_result.exponent |= raw_result.exponent
            final_result.mantissa |= raw_result.mantissa

    return final_result


def _add_operands(
    larger_operand_exponent: pyrtl.WireVector,
    smaller_mantissa_shifted_grs: pyrtl.WireVector,
    larger_mantissa_extended: pyrtl.WireVector,
) -> tuple[_RawResultGRS, pyrtl.WireVector]:
    """Helper function for performing addition of two floating point mantissas.

    :param larger_operand_exponent: Exponent of the larger operand.
    :param smaller_mantissa_shifted_grs: Mantissa of the smaller operand shifted to
        align with the larger operand and concatenated with ``GRS``.
    :param larger_mantissa_extended: Larger mantissa with three zeros.

    :return: Tuple of ``(_RawResultGRS, carry_bit)``.
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
    return _RawResultGRS(
        exponent=sum_exponent, mantissa=sum_mantissa, grs=sum_grs
    ), sum_carry


def _sub_operands(
    num_mant_bits: int,
    larger_operand_exponent: pyrtl.WireVector,
    smaller_mantissa_shifted_grs: pyrtl.WireVector,
    larger_mantissa_extended: pyrtl.WireVector,
) -> tuple[_RawResultGRS, pyrtl.WireVector]:
    """Helper function for performing subtraction of two floating point mantissas.

    :param num_mant_bits: Number of mantissa bits.
    :param larger_operand_exponent: Exponent of the larger operand.
    :param smaller_mantissa_shifted_grs: Mantissa of the smaller operand shifted to
        align with the larger operand and concatenated with ``GRS``.
    :param larger_mantissa_extended: Larger mantissa with three zeros.

    :return: Tuple of ``(_RawResultGRS, num_leading_zeros)``.
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
        exponent=difference_exponent, mantissa=difference_mantissa, grs=difference_grs
    ), num_leading_zeros
