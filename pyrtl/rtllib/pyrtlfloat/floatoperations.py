import pyrtl

from ._add_sub import AddSubHelper
from ._multiplication import MultiplicationHelper
from ._types import PyrtlFloatConfig, RoundingMode


class FloatOperations:
    default_rounding_mode = RoundingMode.RNE

    @staticmethod
    def multiply(
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
