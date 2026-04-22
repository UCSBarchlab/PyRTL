from dataclasses import dataclass
from enum import Enum


class RoundingMode(Enum):
    """
    Enum representing different rounding modes.

    Attributes:
        RTZ (int): Round towards zero (truncate).
        RNE (int): Round to nearest, ties to even (default mode).
    """

    RTZ = 1
    RNE = 2


@dataclass(frozen=True)
class FPTypeProperties:
    """
    Data class representing properties of a floating-point type.

    Attributes:
        num_exponent_bits (int): Number of bits used for the exponent.
        num_mantissa_bits (int): Number of bits used for the mantissa.
    """

    num_exponent_bits: int
    num_mantissa_bits: int


class FloatingPointType(Enum):
    """
    Enum representing different floating-point types.

    Attributes:
        BFLOAT16 (FPTypeProperties): BFloat16 type properties.
        FLOAT16 (FPTypeProperties): Float16 type properties.
        FLOAT32 (FPTypeProperties): Float32 type properties.
        FLOAT64 (FPTypeProperties): Float64 type properties.
    """

    BFLOAT16 = FPTypeProperties(num_exponent_bits=8, num_mantissa_bits=7)
    FLOAT16 = FPTypeProperties(num_exponent_bits=5, num_mantissa_bits=10)
    FLOAT32 = FPTypeProperties(num_exponent_bits=8, num_mantissa_bits=23)
    FLOAT64 = FPTypeProperties(num_exponent_bits=11, num_mantissa_bits=52)


@dataclass(frozen=True)
class PyrtlFloatConfig:
    """
    Data class representing the configuration for PyrtlFloat operations (floating point
    type properties and rounding mode).

    Attributes:
        fp_type_properties (FPTypeProperties): Properties of the floating-point type.
        rounding_mode (RoundingMode): Rounding mode to be used.
    """

    fp_type_properties: FPTypeProperties
    rounding_mode: RoundingMode
