from enum import Enum

import pyrtl


class RoundingMode(Enum):
    """Enum representing different rounding modes."""

    RTZ = 1
    """Round towards zero (truncate)."""

    RNE = 2
    """Round to nearest, ties to even (default mode)."""


@pyrtl.wire_struct
class BFloat16:
    """:class:`~pyrtl.wire_struct` representation of Google's ``bfloat16`` 16-bit
    floating point format.

    :ivar sign: 1 bit
    :ivar exponent: 8 bits
    :ivar mantissa: 7 bits
    """

    sign: 1
    exponent: 8
    mantissa: 7


@pyrtl.wire_struct
class Float16:
    """:class:`~pyrtl.wire_struct` representation of IEEE 754 16-bit floating point
    format.

    :ivar sign: 1 bit
    :ivar exponent: 5 bits
    :ivar mantissa: 10 bits
    """

    sign: 1
    exponent: 5
    mantissa: 10


@pyrtl.wire_struct
class Float32:
    """:class:`~pyrtl.wire_struct` representation of IEEE 754 32-bit floating point
    format.

    :ivar sign: 1 bit
    :ivar exponent: 8 bits
    :ivar mantissa: 23 bits
    """

    sign: 1
    exponent: 8
    mantissa: 23


@pyrtl.wire_struct
class Float64:
    """:class:`~pyrtl.wire_struct` representation of IEEE 754 64-bit floating point
    format.

    :ivar sign: 1 bit
    :ivar exponent: 11 bits
    :ivar mantissa: 52 bits
    """

    sign: 1
    exponent: 11
    mantissa: 52


FloatType = BFloat16 | Float16 | Float32 | Float64
"""Type alias for any floating point type."""
