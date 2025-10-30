import pyrtl

from ._add_sub import AddSubHelper
from ._multiplication import MultiplicationHelper
from ._types import FloatingPointType, PyrtlFloatConfig, RoundingMode


class FloatOperations:
    default_rounding_mode = RoundingMode.RNE

    @staticmethod
    def mul(
        config: PyrtlFloatConfig,
        operand_a: pyrtl.WireVector,
        operand_b: pyrtl.WireVector,
    ) -> pyrtl.WireVector:
        return MultiplicationHelper.multiply(config, operand_a, operand_b)

    @staticmethod
    def add(
        config: PyrtlFloatConfig,
        operand_a: pyrtl.WireVector,
        operand_b: pyrtl.WireVector,
    ) -> pyrtl.WireVector:
        return AddSubHelper.add(config, operand_a, operand_b)

    @staticmethod
    def sub(
        config: PyrtlFloatConfig,
        operand_a: pyrtl.WireVector,
        operand_b: pyrtl.WireVector,
    ) -> pyrtl.WireVector:
        return AddSubHelper.sub(config, operand_a, operand_b)


class _BaseTypedFloatOperations:
    _fp_type: FloatingPointType = None

    @classmethod
    def mul(
        cls, operand_a: pyrtl.WireVector, operand_b: pyrtl.WireVector
    ) -> pyrtl.WireVector:
        return FloatOperations.mul(cls._get_config(), operand_a, operand_b)

    @classmethod
    def add(
        cls, operand_a: pyrtl.WireVector, operand_b: pyrtl.WireVector
    ) -> pyrtl.WireVector:
        return FloatOperations.add(cls._get_config(), operand_a, operand_b)

    @classmethod
    def sub(
        cls, operand_a: pyrtl.WireVector, operand_b: pyrtl.WireVector
    ) -> pyrtl.WireVector:
        return FloatOperations.sub(cls._get_config(), operand_a, operand_b)

    @classmethod
    def _get_config(cls) -> PyrtlFloatConfig:
        return PyrtlFloatConfig(
            cls._fp_type.value, FloatOperations.default_rounding_mode
        )


class BFloat16Operations(_BaseTypedFloatOperations):
    _fp_type = FloatingPointType.BFLOAT16


class Float16Operations(_BaseTypedFloatOperations):
    _fp_type = FloatingPointType.FLOAT16


class Float32Operations(_BaseTypedFloatOperations):
    _fp_type = FloatingPointType.FLOAT32


class Float64Operations(_BaseTypedFloatOperations):
    _fp_type = FloatingPointType.FLOAT64
