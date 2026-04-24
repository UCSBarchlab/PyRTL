# This file should be named `mult.py` for symmetry with `add_sub.py`, but is instead
# named `multiplication.py` so the module has a name.

# `__init__.py` creates `pyrtl.rtllib.float.mult`, collides with this module's name, if
# this file were named `mult.py`.
#
# This module currently needs to be named to run its `doctest`s.

import pyrtl
from pyrtl.rtllib.float.types import FloatType, RoundingMode
from pyrtl.rtllib.float.utils import (
    _RawResult,
    _round_rne,
    check_kinds,
    get_default_rounding_mode,
    make_denormals_zero,
    make_inf_like,
    make_largest_finite_number_like,
    make_nan_like,
)


def mult(
    operand_a: FloatType, operand_b: FloatType, rounding_mode: RoundingMode = None
) -> FloatType:
    """Performs floating point multiplication.

    The two operands must share the same ``Float`` type. Multiplying different floating
    point types is not supported.

    Denormalized numbers are not supported. Denormalized numbers will be flushed to
    zero.

    The return value's ``Float`` type will match the operand ``Float`` type. For
    example, if you ``mult`` two :class:`~.Float16`, the result will be a
    :class:`~.Float16`.

    .. doctest only::

        >>> import pyrtl
        >>> pyrtl.reset_working_block()

    The following example computes ``2.0 * 4.0``. This is a bare-metal example, directly
    manipulating the raw ``sign``, ``exponent``, and ``mantissa`` in IEEE 754 16-bit
    floating point representation. See the documentation for :func:`add` and `IEEE 754
    Internal Representation
    <https://en.wikipedia.org/wiki/Floating-point_arithmetic#Internal_representation>`_
    for more details::

        >>> import pyrtl.rtllib.float as rtlfloat

        >>> a = rtlfloat.Float16(name="a", component_type=pyrtl.Input)
        >>> b = rtlfloat.Float16(name="b", component_type=pyrtl.Input)

        >>> product = rtlfloat.Float16(name="product", Float16=None)
        >>> product <<= rtlfloat.mult(a, b)

        >>> # See the `add` example for IEEE 754 representation background.
        >>> exponent_bias = 2 ** (product.exponent.bitwidth - 1) - 1

        >>> # Create a=2.0, represented as 1.0 * 2 ** 1.
        >>> a_two = {"a.sign": 0, "a.exponent": 1 + exponent_bias, "a.mantissa": 0}

        >>> # Create b=4.0, represented as 1.0 * 2 ** 2.
        >>> b_four = {"b.sign": 0, "b.exponent": 2 + exponent_bias, "b.mantissa": 0}

        >>> sim = pyrtl.Simulation()
        >>> sim.step(a_two | b_four)

        >>> # The product should be 8.0, represented as 1.0 * 2 ** 3.
        >>> sim.inspect("product.sign")
        0
        >>> sim.inspect("product.exponent") - exponent_bias
        3
        >>> sim.inspect("product.mantissa")
        0

    :param operand_a:
    :param operand_b:
    :param rounding_mode: Rounding mode, defaults to :attr:`~.RoundingMode.RNE`. The
        default can be changed with :func:`.set_default_rounding_mode`.

    :return: The product, as an instance of the operand ``Float`` type.
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

    result_sign = operands[0].sign ^ operands[1].sign

    # Compute the product exponent and mantissa.
    operand_exponent_sums, product_exponent, product_mantissa = _multiply(operands)

    # Normalize the product and perform rounding.
    raw_result, need_to_normalize, exponent_incremented = _normalize_and_round(
        product_exponent,
        product_mantissa,
        operand_a.exponent.bitwidth,
        operand_a.mantissa.bitwidth,
        rounding_mode,
    )
    del product_mantissa, product_exponent

    return _handle_special_cases(
        operands,
        result_sign,
        raw_result,
        operand_exponent_sums,
        need_to_normalize,
        exponent_incremented,
        rounding_mode,
    )


def _multiply(
    operands: tuple,
) -> tuple[pyrtl.WireVector, pyrtl.WireVector, pyrtl.WireVector]:
    """Computes the sum of operand exponents, the product exponent, and the raw product
    mantissa.

    :param operands: Tuple of ``Floats`` for the two operands.

    :return: Tuple of ``(operand_exponent_sums, product_exponent, product_mantissa)``.
    """
    # IEEE-754 floating point numbers have a bias:
    # https://en.wikipedia.org/wiki/Exponent_bias
    # stored_exponent = real_exponent + bias
    # The sum of the stored exponents of the operands is (real0 + bias) + (real1 + bias)
    # = real0 + real1 + 2*bias.
    # Subtracting bias gives the stored exponent of the product: real0 + real1 + bias.
    operand_exponent_sums = operands[0].exponent + operands[1].exponent
    exponent_bias = 2 ** (operands[0].exponent.bitwidth - 1) - 1
    product_exponent = operand_exponent_sums - pyrtl.Const(exponent_bias)

    # Extract the mantissa of both operands and add the implicit leading 1.
    mantissas = tuple(
        pyrtl.concat(pyrtl.Const(1), operand.mantissa) for operand in operands
    )
    product_mantissa = mantissas[0] * mantissas[1]

    return operand_exponent_sums, product_exponent, product_mantissa


def _normalize_and_round(
    product_exponent: pyrtl.WireVector,
    product_mantissa: pyrtl.WireVector,
    num_exp_bits: int,
    num_mant_bits: int,
    rounding_mode: RoundingMode,
) -> tuple:
    """Normalizes the product mantissa and applies rounding if configured.

    :param product_exponent: The product exponent (sum of operand exponents minus bias).
    :param product_mantissa: Raw product of the two mantissas (with implicit 1s).
    :param rounding_mode: The rounding mode to apply.

    :return: Tuple of ``(_RawResult, need_to_normalize, exponent_incremented)``.
             ``exponent_incremented`` is ``None`` for ``RTZ`` rounding mode.
    """
    # We're multiplying two numbers that both have the form 1.<something> in
    # binary. The product's binary point sits just after its second-most
    # significant bit, giving the form ab.cdef... where each letter is one bit.
    #
    # Either a (the MSB) or b (the bit after the MSB) must be 1 because the
    # product of two 1.<something> numbers is always in [1, 4): the smallest
    # is 1.0... * 1.0... = 01.0... and the largest is 1.111... * 1.111...
    # = 11.111... Therefore, there must be one or two bits to the left of the
    # binary point.
    #
    # A properly normalized result must have the form 1.<something>, so:
    # - If a (the MSB) is 1, the product is 1.bcdef... so we increment the
    #   exponent to reinterpret the result as 1.bcdef... and the mantissa is
    #   correct as is.
    # - If a is 0, the product is 0b.cdef... = 01.cdef... (b must be 1 since a
    #   is 0), so we shift the mantissa left by 1 to reinterpret the result
    #   as 1.cdef... and the exponent is correct as is.
    pyrtl.rtl_assert(
        product_mantissa[-1] | product_mantissa[-2],
        AssertionError("product mantissa MSB or the bit after the MSB must be 1"),
    )
    need_to_normalize = product_mantissa[-1]
    aligned_mantissa = pyrtl.WireVector(bitwidth=product_mantissa.bitwidth)
    normalized_product_exponent = pyrtl.WireVector(bitwidth=product_exponent.bitwidth)
    with pyrtl.conditional_assignment:
        with need_to_normalize:
            aligned_mantissa |= product_mantissa
            normalized_product_exponent |= product_exponent + 1
        with pyrtl.otherwise:
            aligned_mantissa |= pyrtl.concat(
                product_mantissa[:-1], pyrtl.Const(0, bitwidth=1)
            )
            normalized_product_exponent |= product_exponent

    # Strip the implicit leading 1 to get the stored mantissa bits.
    normalized_product_mantissa = pyrtl.WireVector(bitwidth=num_mant_bits)
    normalized_product_mantissa <<= aligned_mantissa[-num_mant_bits - 1 :]

    if rounding_mode == RoundingMode.RNE:
        # Extract guard, round, and sticky bits for rounding.
        # https://drilian.com/posts/2023.01.10-floating-point-numbers-and-rounding/
        guard = aligned_mantissa[-num_mant_bits - 2]
        round_bit = aligned_mantissa[-num_mant_bits - 3]
        sticky = aligned_mantissa[: -num_mant_bits - 3] != 0

        raw_product = _RawResult(
            exponent=normalized_product_exponent,
            mantissa=normalized_product_mantissa,
        )
        raw_grs = pyrtl.concat(guard, round_bit, sticky)
        rounded_product, exponent_incremented = _round_rne(raw_product, raw_grs)
        raw_result = _RawResult(
            exponent=rounded_product.exponent[:num_exp_bits],
            mantissa=rounded_product.mantissa,
        )
        return raw_result, need_to_normalize, exponent_incremented
    raw_result = _RawResult(
        exponent=normalized_product_exponent[:num_exp_bits],
        mantissa=normalized_product_mantissa,
    )
    return raw_result, need_to_normalize, None


def _handle_special_cases(
    operands: tuple,
    result_sign: pyrtl.WireVector,
    raw_result: _RawResult,
    operand_exponent_sums: pyrtl.WireVector,
    need_to_normalize: pyrtl.WireVector,
    exponent_incremented,
    rounding_mode: RoundingMode,
):
    """Handles special cases: NaN, infinity, zero, overflow, and underflow.

    :param operands: Tuple of ``Floats`` for the two operands.
    :param result_sign: Sign bit of the result.
    :param raw_result: Normalized (and possibly rounded) result as a ``_RawResult``.
    :param operand_exponent_sums: Sum of the two operand exponents.
    :param need_to_normalize: Whether the product mantissa required normalization.
    :param exponent_incremented: Whether rounding incremented the exponent (``None`` for
        ``RTZ`` mode).
    :param rounding_mode: The rounding mode being used.

    :return: The final product, as an instance of the operand ``Float`` type.
    """
    num_exp_bits = operands[0].exponent.bitwidth
    exponent_bias = 2 ** (num_exp_bits - 1) - 1

    # Check whether operands are special: NaN, infinity, zero, or denormalized.
    operand_kinds = tuple(check_kinds(operand) for operand in operands)

    # Pre-compute special value constants for use inside conditional_assignment.
    result = type(operands[0])(sign=None, exponent=None, mantissa=None)
    result.sign <<= result_sign
    nan_exp, nan_mant = make_nan_like(operands[0])
    inf_exp, inf_mant = make_inf_like(operands[0])
    largest_exp, largest_mant = make_largest_finite_number_like(operands[0])

    # We check for overflow and underflow by computing max and min exponent
    # values of the sum of operands' exponent before rounding and normalization.
    # These values depend on the operands. If the result requires
    # normalization, the exponent is incremented by 1. Additionally, rounding
    # may further increase the exponent. Therefore, we subtract these
    # potential increments from the base maximum exponent, which is one
    # less than the all-1s exponent (reserved for inf/NaN) plus bias.
    # Similarly, we subtract these increments from the base minimum
    # exponent, which is 1 plus the exponent bias. However, instead of performing
    # subtractions in hardware, we use conditional assignments to determine the
    # appropriate maximum and minimum exponent values. Since we are merely
    # selecting among three possible values, instantiating a subtractor
    # would be overkill.
    base_exponent_max_value = 2**num_exp_bits - 2 + exponent_bias
    base_exponent_min_value = 1 + exponent_bias
    exponent_max_value = pyrtl.WireVector(bitwidth=operand_exponent_sums.bitwidth)
    exponent_min_value = pyrtl.WireVector(bitwidth=operand_exponent_sums.bitwidth)
    if rounding_mode == RoundingMode.RNE:
        with pyrtl.conditional_assignment:
            with exponent_incremented & need_to_normalize:
                exponent_max_value |= base_exponent_max_value - 2
                exponent_min_value |= base_exponent_min_value - 2
            with exponent_incremented | need_to_normalize:
                exponent_max_value |= base_exponent_max_value - 1
                exponent_min_value |= base_exponent_min_value - 1
            with pyrtl.otherwise:
                exponent_max_value |= base_exponent_max_value
                exponent_min_value |= base_exponent_min_value
    else:
        with pyrtl.conditional_assignment:
            with need_to_normalize:
                exponent_max_value |= base_exponent_max_value - 1
                exponent_min_value |= base_exponent_min_value - 1
            with pyrtl.otherwise:
                exponent_max_value |= base_exponent_max_value
                exponent_min_value |= base_exponent_min_value

    with pyrtl.conditional_assignment:
        # If either operand is NaN, or if one operand is infinity and the other is
        # zero, the result is NaN.
        with (
            operand_kinds[0].is_nan
            | operand_kinds[1].is_nan
            | (operand_kinds[0].is_inf & operand_kinds[1].is_zero)
            | (operand_kinds[0].is_zero & operand_kinds[1].is_inf)
        ):
            result.exponent |= nan_exp
            result.mantissa |= nan_mant
        # If either operand is infinity, the result is infinity.
        with operand_kinds[0].is_inf | operand_kinds[1].is_inf:
            result.exponent |= inf_exp
            result.mantissa |= inf_mant
        # Detect overflow.
        with operand_exponent_sums > exponent_max_value:
            if rounding_mode == RoundingMode.RNE:
                result.exponent |= inf_exp
                result.mantissa |= inf_mant
            else:
                result.exponent |= largest_exp
                result.mantissa |= largest_mant
        # If either operand is zero, if underflow occurred, or if either operand is
        # denormalized, the result is zero.
        with (
            operand_kinds[0].is_zero
            | operand_kinds[1].is_zero
            | (operand_exponent_sums < exponent_min_value)
            | operand_kinds[0].is_denormalized
            | operand_kinds[1].is_denormalized
        ):
            result.exponent |= 0
            result.mantissa |= 0
        # Otherwise no special cases apply: this is the common case.
        with pyrtl.otherwise:
            result.exponent |= raw_result.exponent
            result.mantissa |= raw_result.mantissa

    return result
