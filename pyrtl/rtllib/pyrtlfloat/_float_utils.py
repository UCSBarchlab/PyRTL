import pyrtl

from ._types import FPTypeProperties


def _fp_wire_struct(num_exp_bits, num_mant_bits):
    """Creates a wire_struct class for an IEEE 754 floating point number.

    The returned class has three fields: sign (1 bit), exponent, and mantissa.

    :param num_exp_bits: Number of exponent bits.
    :param num_mant_bits: Number of mantissa bits.
    :return: A wire_struct class with sign, exponent, and mantissa fields.
    """

    @pyrtl.wire_struct
    class FP:
        sign: 1
        exponent: num_exp_bits
        mantissa: num_mant_bits

    return FP


@pyrtl.wire_struct
class _GRS:
    """Guard, round, and sticky bits used for RNE rounding."""

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


class _RawResult:
    """Groups the exponent and mantissa WireVectors of a result."""

    def __init__(
        self,
        exponent: pyrtl.WireVector,
        mantissa: pyrtl.WireVector,
    ):
        self.exponent = exponent
        self.mantissa = mantissa


class _RawResultGRS(_RawResult):
    """Groups the exponent, mantissa, and GRS WireVectors of a result."""

    def __init__(
        self,
        exponent: pyrtl.WireVector,
        mantissa: pyrtl.WireVector,
        grs: pyrtl.WireVector,
    ):
        super().__init__(exponent, mantissa)
        self.grs = grs


def check_kinds(fp) -> _FPKinds:
    """
    Returns an _FPKinds wire struct indicating the kind of the given floating point
    number.

    :param fp: FP wire_struct instance.
    :return: _FPKinds instance.
    """
    kinds = _FPKinds(is_nan=None, is_inf=None, is_zero=None, is_denormalized=None)
    max_exp = (1 << fp.exponent.bitwidth) - 1
    all_ones_exp = fp.exponent == max_exp
    zero_exp = fp.exponent == 0
    zero_mant = fp.mantissa == 0
    kinds.is_nan <<= all_ones_exp & ~zero_mant
    kinds.is_inf <<= all_ones_exp & zero_mant
    kinds.is_zero <<= zero_exp & zero_mant
    kinds.is_denormalized <<= zero_exp & ~zero_mant
    return kinds


def make_denormals_zero(
    fp_prop: FPTypeProperties, wire: pyrtl.WireVector
) -> pyrtl.WireVector:
    """
    Returns zero if denormalized, else original number.
    https://en.wikipedia.org/wiki/Subnormal_number

    :param fp_prop: Floating point type properties.
    :param wire: WireVector holding the floating point number.
    :return: WireVector holding the resulting floating point number.
    """
    FP = _fp_wire_struct(fp_prop.num_exponent_bits, fp_prop.num_mantissa_bits)
    fp = FP(FP=wire)
    out = pyrtl.WireVector(
        bitwidth=fp_prop.num_mantissa_bits + fp_prop.num_exponent_bits + 1
    )
    with pyrtl.conditional_assignment:
        with fp.exponent == 0:
            out |= pyrtl.concat(
                fp.sign,
                fp.exponent,
                pyrtl.Const(0, bitwidth=fp_prop.num_mantissa_bits),
            )
        with pyrtl.otherwise:
            out |= wire
    return out


def make_inf(fp_props: FPTypeProperties) -> tuple:
    """
    Returns (exponent, mantissa) WireVectors representing infinity.

    :param fp_props: Floating point type properties.
    :return: Tuple of (exponent, mantissa) WireVectors.
    """
    num_exp_bits = fp_props.num_exponent_bits
    num_mant_bits = fp_props.num_mantissa_bits
    return (
        pyrtl.Const((1 << num_exp_bits) - 1, bitwidth=num_exp_bits),
        pyrtl.Const(0, bitwidth=num_mant_bits),
    )


def make_nan(fp_props: FPTypeProperties) -> tuple:
    """
    Returns (exponent, mantissa) WireVectors representing NaN.

    :param fp_props: Floating point type properties.
    :return: Tuple of (exponent, mantissa) WireVectors.
    """
    num_exp_bits = fp_props.num_exponent_bits
    num_mant_bits = fp_props.num_mantissa_bits
    return (
        pyrtl.Const((1 << num_exp_bits) - 1, bitwidth=num_exp_bits),
        pyrtl.Const(1 << (num_mant_bits - 1), bitwidth=num_mant_bits),
    )


def make_zero(fp_props: FPTypeProperties) -> tuple:
    """
    Returns (exponent, mantissa) WireVectors representing zero.

    :param fp_props: Floating point type properties.
    :return: Tuple of (exponent, mantissa) WireVectors.
    """
    num_exp_bits = fp_props.num_exponent_bits
    num_mant_bits = fp_props.num_mantissa_bits
    return (
        pyrtl.Const(0, bitwidth=num_exp_bits),
        pyrtl.Const(0, bitwidth=num_mant_bits),
    )


def make_largest_finite_number(fp_props: FPTypeProperties) -> tuple:
    """
    Returns (exponent, mantissa) WireVectors representing the largest finite number.

    :param fp_props: Floating point type properties.
    :return: Tuple of (exponent, mantissa) WireVectors.
    """
    num_exp_bits = fp_props.num_exponent_bits
    num_mant_bits = fp_props.num_mantissa_bits
    return (
        pyrtl.Const((1 << num_exp_bits) - 2, bitwidth=num_exp_bits),
        pyrtl.Const((1 << num_mant_bits) - 1, bitwidth=num_mant_bits),
    )


def _round_rne(
    raw_result: _RawResult,
    raw_grs: pyrtl.WireVector,
) -> tuple:
    """
    Round the floating point result using round to nearest, ties to even (RNE).

    Uses the GRS bits to determine if the result needs to be rounded up.

    :param raw_result: Pre-rounding result as a _RawResult.
    :param raw_grs: GRS bits of the raw result before rounding (guard=MSB, sticky=LSB).
    :return: Tuple of (rounded _RawResult, rounding_exponent_incremented).
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
