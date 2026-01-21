import pyrtl

from ._add_sub import add, sub
from ._multiplication import mul
from ._types import FloatingPointType, PyrtlFloatConfig, RoundingMode


def _validate_operand_bitwidths(
    config: PyrtlFloatConfig,
    operand_a: pyrtl.WireVector,
    operand_b: pyrtl.WireVector,
) -> None:
    """Validate that operand bitwidths match the floating point config."""
    fp_props = config.fp_type_properties
    expected_bitwidth = fp_props.num_exponent_bits + fp_props.num_mantissa_bits + 1
    if operand_a.bitwidth != expected_bitwidth:
        msg = (
            f"operand_a bitwidth {operand_a.bitwidth} does not match expected "
            f"bitwidth {expected_bitwidth} for floating point type"
        )
        raise pyrtl.PyrtlError(msg)
    if operand_b.bitwidth != expected_bitwidth:
        msg = (
            f"operand_b bitwidth {operand_b.bitwidth} does not match expected "
            f"bitwidth {expected_bitwidth} for floating point type"
        )
        raise pyrtl.PyrtlError(msg)


class FloatOperations:
    """
    The rounding mode used for typed floating-point operations.
    To change it, set this variable to the desired RoundingMode value.
    """

    default_rounding_mode = RoundingMode.RNE

    @staticmethod
    def mul(
        config: PyrtlFloatConfig,
        operand_a: pyrtl.WireVector,
        operand_b: pyrtl.WireVector,
    ) -> pyrtl.WireVector:
        """
        Performs floating point multiplication of two WireVectors. The bitwidth of
        the operands must be num_exponent_bits + num_mantissa_bits + 1, where
        num_exponent_bits and num_mantissa_bits are defined in the config.

        :param config: Configuration for the floating point type and rounding mode.
        :param operand_a: The first floating point operand as a WireVector.
        :param operand_b: The second floating point operand as a WireVector.
        :return: The result of the multiplication as a WireVector.
        :raises PyrtlError: If operand bitwidths don't match config.
        """
        _validate_operand_bitwidths(config, operand_a, operand_b)
        return mul(config, operand_a, operand_b)

    @staticmethod
    def add(
        config: PyrtlFloatConfig,
        operand_a: pyrtl.WireVector,
        operand_b: pyrtl.WireVector,
    ) -> pyrtl.WireVector:
        """
        Performs floating point addition of two WireVectors. The bitwidth of
        the operands must be num_exponent_bits + num_mantissa_bits + 1, where
        num_exponent_bits and num_mantissa_bits are defined in the config.

        :param config: Configuration for the floating point type and rounding mode.
        :param operand_a: The first floating point operand as a WireVector.
        :param operand_b: The second floating point operand as a WireVector.
        :return: The result of the addition as a WireVector.
        :raises PyrtlError: If operand bitwidths don't match config.
        """
        _validate_operand_bitwidths(config, operand_a, operand_b)
        return add(config, operand_a, operand_b)

    @staticmethod
    def sub(
        config: PyrtlFloatConfig,
        operand_a: pyrtl.WireVector,
        operand_b: pyrtl.WireVector,
    ) -> pyrtl.WireVector:
        """
        Performs floating point subtraction of two WireVectors. The bitwidth of
        the operands must be num_exponent_bits + num_mantissa_bits + 1, where
        num_exponent_bits and num_mantissa_bits are defined in the config.

        :param config: Configuration for the floating point type and rounding mode.
        :param operand_a: The first floating point operand as a WireVector.
        :param operand_b: The second floating point operand as a WireVector.
        :return: The result of the subtraction as a WireVector.
        :raises PyrtlError: If operand bitwidths don't match config.
        """
        _validate_operand_bitwidths(config, operand_a, operand_b)
        return sub(config, operand_a, operand_b)


class _BaseTypedFloatOperations:
    _fp_type: FloatingPointType = None

    @classmethod
    def mul(
        cls, operand_a: pyrtl.WireVector, operand_b: pyrtl.WireVector
    ) -> pyrtl.WireVector:
        """
        Performs floating point multiplication of two WireVectors. The bitwidth of
        the operands must match the bitwidth of the floating point type of this class.

        :param operand_a: The first floating point operand as a WireVector.
        :param operand_b: The second floating point operand as a WireVector.
        :return: The result of the multiplication as a WireVector.
        """
        return FloatOperations.mul(cls._get_config(), operand_a, operand_b)

    @classmethod
    def add(
        cls, operand_a: pyrtl.WireVector, operand_b: pyrtl.WireVector
    ) -> pyrtl.WireVector:
        """
        Performs floating point addition of two WireVectors. The bitwidth of
        the operands must match the bitwidth of the floating point type of this class.

        :param operand_a: The first floating point operand as a WireVector.
        :param operand_b: The second floating point operand as a WireVector.
        :return: The result of the addition as a WireVector.
        """
        return FloatOperations.add(cls._get_config(), operand_a, operand_b)

    @classmethod
    def sub(
        cls, operand_a: pyrtl.WireVector, operand_b: pyrtl.WireVector
    ) -> pyrtl.WireVector:
        """
        Performs floating point subtraction of two WireVectors. The bitwidth of
        the operands must match the bitwidth of the floating point type of this class.

        :param operand_a: The first floating point operand as a WireVector.
        :param operand_b: The second floating point operand as a WireVector.
        :return: The result of the subtraction as a WireVector.
        """
        return FloatOperations.sub(cls._get_config(), operand_a, operand_b)

    @classmethod
    def _get_config(cls) -> PyrtlFloatConfig:
        return PyrtlFloatConfig(
            cls._fp_type.value, FloatOperations.default_rounding_mode
        )


class BFloat16Operations(_BaseTypedFloatOperations):
    """
    Operations for BFloat16 floating point type.
    """

    _fp_type = FloatingPointType.BFLOAT16


class Float16Operations(_BaseTypedFloatOperations):
    """
    Operations for Float16 floating point type.
    """

    _fp_type = FloatingPointType.FLOAT16


class Float32Operations(_BaseTypedFloatOperations):
    """
    Operations for Float32 floating point type.
    """

    _fp_type = FloatingPointType.FLOAT32


class Float64Operations(_BaseTypedFloatOperations):
    """
    Operations for Float64 floating point type.
    """

    _fp_type = FloatingPointType.FLOAT64
