from dataclasses import dataclass
from enum import Enum


class RoundingMode(Enum):
    RTZ = 1  # round towards zero (truncate)
    RNE = 2  # round to nearest, ties to even (default mode)


@dataclass(frozen=True)
class FPTypeProperties:
    num_exponent_bits: int
    num_mantissa_bits: int


class FloatingPointType(Enum):
    BFLOAT16 = FPTypeProperties(num_exponent_bits=8, num_mantissa_bits=7)
    FLOAT16 = FPTypeProperties(num_exponent_bits=5, num_mantissa_bits=10)
    FLOAT32 = FPTypeProperties(num_exponent_bits=8, num_mantissa_bits=23)
    FLOAT64 = FPTypeProperties(num_exponent_bits=11, num_mantissa_bits=52)


@dataclass(frozen=True)
class PyrtlFloatConfig:
    fp_type_properties: FPTypeProperties
    rounding_mode: RoundingMode


class PyrtlFloatException(Exception):
    pass
