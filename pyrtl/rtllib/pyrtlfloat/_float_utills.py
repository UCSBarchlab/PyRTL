import pyrtl

from ._types import FPTypeProperties


def get_sign(fp_prop: FPTypeProperties, wire: pyrtl.WireVector) -> pyrtl.WireVector:
    """
    Returns the sign bit of floating point number.

    :param fp_prop: Floating point type properties.
    :param wire: WireVector holding the floating point number.
    :return: WireVector holding the sign bit.
    """
    return wire[fp_prop.num_mantissa_bits + fp_prop.num_exponent_bits]


def get_exponent(fp_prop: FPTypeProperties, wire: pyrtl.WireVector) -> pyrtl.WireVector:
    """
    Returns the exponent bits of floating point number.

    :param fp_prop: Floating point type properties.
    :param wire: WireVector holding the floating point number.
    :return: WireVector holding the exponent bits.
    """
    return wire[
        fp_prop.num_mantissa_bits : fp_prop.num_mantissa_bits
        + fp_prop.num_exponent_bits
    ]


def get_mantissa(fp_prop: FPTypeProperties, wire: pyrtl.WireVector) -> pyrtl.WireVector:
    """
    Returns the mantissa bits of floating point number.

    :param fp_prop: Floating point type properties.
    :param wire: WireVector holding the floating point number.
    :return: WireVector holding the mantissa bits.
    """
    return wire[: fp_prop.num_mantissa_bits]


def is_zero(fp_prop: FPTypeProperties, wire: pyrtl.WireVector) -> pyrtl.WireVector:
    """
    Returns whether the floating point number is zero.

    :param fp_prop: Floating point type properties.
    :param wire: WireVector holding the floating point number.
    :return: 1-bit WireVector indicating whether the number is zero.
    """
    return (get_mantissa(fp_prop, wire) == 0) & (get_exponent(fp_prop, wire) == 0)


def is_inf(fp_prop: FPTypeProperties, wire: pyrtl.WireVector) -> pyrtl.WireVector:
    """
    Returns whether the floating point number is infinity.

    :param fp_prop: Floating point type properties.
    :param wire: WireVector holding the floating point number.
    :return: 1-bit WireVector indicating whether the number is infinity.
    """
    return (get_mantissa(fp_prop, wire) == 0) & (
        get_exponent(fp_prop, wire) == (1 << fp_prop.num_exponent_bits) - 1
    )


def is_denormalized(
    fp_prop: FPTypeProperties, wire: pyrtl.WireVector
) -> pyrtl.WireVector:
    """
    Returns whether the floating point number is denormalized.

    :param fp_prop: Floating point type properties.
    :param wire: WireVector holding the floating point number.
    :return: 1-bit WireVector indicating whether the number is denormalized.
    """
    return (get_mantissa(fp_prop, wire) != 0) & (get_exponent(fp_prop, wire) == 0)


def is_nan(fp_prop: FPTypeProperties, wire: pyrtl.WireVector) -> pyrtl.WireVector:
    """
    Returns whether the floating point number is NaN.

    :param fp_prop: Floating point type properties.
    :param wire: WireVector holding the floating point number.
    :return: 1-bit WireVector indicating whether the number is NaN.
    """
    return (get_mantissa(fp_prop, wire) != 0) & (
        get_exponent(fp_prop, wire) == (1 << fp_prop.num_exponent_bits) - 1
    )


def make_denormals_zero(
    fp_prop: FPTypeProperties, wire: pyrtl.WireVector
) -> pyrtl.WireVector:
    """
    Returns zero if denormalized, else original number.

    :param fp_prop: Floating point type properties.
    :param wire: WireVector holding the floating point number.
    :return: WireVector holding the resulting floating point number.
    """
    out = pyrtl.WireVector(
        bitwidth=fp_prop.num_mantissa_bits + fp_prop.num_exponent_bits + 1
    )
    with pyrtl.conditional_assignment:
        with get_exponent(fp_prop, wire) == 0:
            out |= pyrtl.concat(
                get_sign(fp_prop, wire),
                get_exponent(fp_prop, wire),
                pyrtl.Const(0, bitwidth=fp_prop.num_mantissa_bits),
            )
        with pyrtl.otherwise:
            out |= wire
    return out


def make_inf(
    fp_prop: FPTypeProperties,
    exponent: pyrtl.WireVector,
    mantissa: pyrtl.WireVector,
) -> None:
    """
    Sets the exponent and mantissa to represent infinity.

    :param fp_prop: Floating point type properties.
    :param exponent: WireVector to set the exponent bits.
    :param mantissa: WireVector to set the mantissa bits.
    """
    exponent |= (1 << fp_prop.num_exponent_bits) - 1
    mantissa |= 0


def make_nan(
    fp_prop: FPTypeProperties,
    exponent: pyrtl.WireVector,
    mantissa: pyrtl.WireVector,
) -> None:
    """
    Sets the exponent and mantissa to represent NaN.

    :param fp_prop: Floating point type properties.
    :param exponent: WireVector to set the exponent bits.
    :param mantissa: WireVector to set the mantissa bits.
    """
    exponent |= (1 << fp_prop.num_exponent_bits) - 1
    mantissa |= 1 << (fp_prop.num_mantissa_bits - 1)


def make_zero(exponent: pyrtl.WireVector, mantissa: pyrtl.WireVector) -> None:
    """
    Sets the exponent and mantissa to represent zero.

    :param exponent: WireVector to set the exponent bits.
    :param mantissa: WireVector to set the mantissa bits.
    """
    exponent |= 0
    mantissa |= 0


def make_largest_finite_number(
    fp_prop: FPTypeProperties,
    exponent: pyrtl.WireVector,
    mantissa: pyrtl.WireVector,
) -> None:
    """
    Sets the exponent and mantissa to represent the largest finite number.

    :param fp_prop: Floating point type properties.
    :param exponent: WireVector to set the exponent bits.
    :param mantissa: WireVector to set the mantissa bits.
    """
    exponent |= (1 << fp_prop.num_exponent_bits) - 2
    mantissa |= (1 << fp_prop.num_mantissa_bits) - 1
