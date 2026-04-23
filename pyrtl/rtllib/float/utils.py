from dataclasses import dataclass

import pyrtl
from pyrtl.rtllib.float.types import FloatType, RoundingMode

_default_rounding_mode = RoundingMode.RNE


def set_default_rounding_mode(rounding_mode: RoundingMode) -> None:
    """Use ``rounding_mode`` by default for all future floating point operations.

    :param rounding_mode:
    """
    global _default_rounding_mode
    _default_rounding_mode = rounding_mode


def get_default_rounding_mode() -> RoundingMode:
    """Return the current default rounding mode for floating point operations.

    :returns:
    """
    return _default_rounding_mode


@pyrtl.wire_struct
class _GRS:
    """Guard, round, and sticky (``GRS``) bits used for ``RNE`` rounding."""

    guard: 1
    round: 1
    sticky: 1


@pyrtl.wire_struct
class _FPKinds:
    """Bits indicating the kind of a floating-point number."""

    is_nan: 1
    is_inf: 1
    is_zero: 1
    is_denormalized: 1


@dataclass
class _RawResult:
    """Groups the ``exponent`` and ``mantissa`` ``WireVectors`` of a result."""

    exponent: pyrtl.WireVector
    mantissa: pyrtl.WireVector


@dataclass
class _RawResultGRS:
    """
    Groups the ``exponent``, ``mantissa``, and ``GRS`` ``WireVectors`` of a result.
    """

    exponent: pyrtl.WireVector
    mantissa: pyrtl.WireVector
    grs: pyrtl.WireVector


def check_kinds(fp: FloatType) -> _FPKinds:
    """Returns a ``_FPKinds`` ``wire_struct`` indicating the kind of the given floating
    point number.
    """
    max_exp = (1 << fp.exponent.bitwidth) - 1
    all_ones_exp = fp.exponent == max_exp
    zero_exp = fp.exponent == 0
    zero_mant = fp.mantissa == 0
    return _FPKinds(
        is_nan=all_ones_exp & ~zero_mant,
        is_inf=all_ones_exp & zero_mant,
        is_zero=zero_exp & zero_mant,
        is_denormalized=zero_exp & ~zero_mant,
    )


def make_denormals_zero(operand: FloatType) -> FloatType:
    """Returns zero if ``operand`` is denormalized, otherwise returns ``operand``.
    https://en.wikipedia.org/wiki/Subnormal_number
    """
    out = type(operand)(sign=operand.sign, exponent=operand.exponent, mantissa=None)
    with pyrtl.conditional_assignment:
        with operand.exponent == 0:
            out.mantissa |= 0
        with pyrtl.otherwise:
            out.mantissa |= operand.mantissa

    return out


def make_inf_like(operand: FloatType) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    """Returns ``(exponent, mantissa)`` ``WireVectors`` representing infinity, with
    bitwidths matching ``operand``.

    :param operand: A ``Float`` that determines the exponent and mantissa bitwidths.

    :return: Tuple of ``(exponent, mantissa)`` ``WireVectors``.
    """
    num_exp_bits = operand.exponent.bitwidth
    num_mant_bits = operand.mantissa.bitwidth
    return (
        pyrtl.Const((1 << num_exp_bits) - 1, bitwidth=num_exp_bits),
        pyrtl.Const(0, bitwidth=num_mant_bits),
    )


def make_nan_like(operand: FloatType) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    """Returns ``(exponent, mantissa)`` ``WireVectors`` representing NaN, with
    bitwidths matching ``operand``.

    :param operand: A ``Float`` that determines the exponent and mantissa bitwidths.

    :return: Tuple of ``(exponent, mantissa)`` ``WireVectors``.
    """
    num_exp_bits = operand.exponent.bitwidth
    num_mant_bits = operand.mantissa.bitwidth
    return (
        pyrtl.Const((1 << num_exp_bits) - 1, bitwidth=num_exp_bits),
        pyrtl.Const(1 << (num_mant_bits - 1), bitwidth=num_mant_bits),
    )


def make_largest_finite_number_like(
    operand: FloatType,
) -> tuple[pyrtl.WireVector, pyrtl.WireVector]:
    """Returns ``(exponent, mantissa)`` ``WireVectors`` representing the largest finite
    number, with bitwidths matching ``operand``.

    :param operand: A ``Float`` that determines the exponent and mantissa bitwidths.

    :return: Tuple of ``(exponent, mantissa)`` ``WireVectors``.
    """
    num_exp_bits = operand.exponent.bitwidth
    num_mant_bits = operand.mantissa.bitwidth
    return (
        pyrtl.Const((1 << num_exp_bits) - 2, bitwidth=num_exp_bits),
        pyrtl.Const((1 << num_mant_bits) - 1, bitwidth=num_mant_bits),
    )


def _round_rne(
    raw_result: _RawResult,
    raw_grs: pyrtl.WireVector,
) -> tuple:
    """Round the floating point result using round to nearest, ties to even (``RNE``).

    Uses the ``GRS`` bits to determine if the result needs to be rounded up.

    :param raw_result: Pre-rounding result as a ``_RawResult``.
    :param raw_grs: ``GRS`` bits of the raw result before rounding (guard=MSB,
        sticky=LSB).

    :return: Tuple of ``(rounded _RawResult, rounding_exponent_incremented)``.
    """
    num_mant_bits = raw_result.mantissa.bitwidth
    num_exp_bits = raw_result.exponent.bitwidth
    grs = _GRS(_GRS=raw_grs)
    last = raw_result.mantissa[0]
    # If guard bit is not set, number is closer to smaller value: no round up.
    # If guard bit is set and round or sticky is set, round up.
    # If guard bit is set but round and sticky are not set, value is exactly
    # halfway. Following round-to-nearest ties-to-even, round up if last bit
    # of mantissa is 1 (to make it even); otherwise do not round up.
    # https://drilian.com/posts/2023.01.10-floating-point-numbers-and-rounding/
    round_up = grs.guard & (last | grs.round | grs.sticky)
    rounded = _RawResult(
        exponent=pyrtl.WireVector(bitwidth=num_exp_bits),
        mantissa=pyrtl.WireVector(bitwidth=num_mant_bits),
    )
    # Whether exponent was incremented due to rounding (for overflow check).
    rounding_exponent_incremented = pyrtl.WireVector(bitwidth=1)
    with pyrtl.conditional_assignment:
        with round_up:
            # If rounding causes a mantissa overflow, we need to increment the exponent.
            with raw_result.mantissa == (1 << num_mant_bits) - 1:
                rounded.mantissa |= 0
                rounded.exponent |= raw_result.exponent + 1
                rounding_exponent_incremented |= 1
            with pyrtl.otherwise:
                rounded.mantissa |= raw_result.mantissa + 1
                rounded.exponent |= raw_result.exponent
                rounding_exponent_incremented |= 0
        with pyrtl.otherwise:
            rounded.mantissa |= raw_result.mantissa
            rounded.exponent |= raw_result.exponent
            rounding_exponent_incremented |= 0
    return rounded, rounding_exponent_incremented
